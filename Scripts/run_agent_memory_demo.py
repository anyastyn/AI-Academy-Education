import os
import re
import json
import time
import requests
from dotenv import load_dotenv

import httpx
from openai import OpenAI

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
USER_ID = os.getenv("USER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not all([SUPABASE_URL, SERVICE_KEY, USER_ID, OPENAI_API_KEY]):
    raise SystemExit("Missing env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, USER_ID, OPENAI_API_KEY")

# --- Network safety: timeouts + corporate SSL workaround ---
HTTP_TIMEOUT = 60.0
http_client = httpx.Client(verify=False, timeout=HTTP_TIMEOUT)
client = OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# Debug retrieval output (keep False in normal use)
DEBUG_RAG = False

# Retrieval confidence thresholds (tune later)
GOVERNANCE_MIN_TOP_SCORE = 0.60  # strict for policy answers
HOWTO_MIN_TOP_SCORE = 0.35       # not strict (how-to can work without docs)

# --- Security patterns ---
SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{10,}",
    r"Authorization:\s*Bearer\s+\S+",
    r"client_secret\s*[:=]\s*\S+",
    r"password\s*[:=]\s*\S+",
    r"api[_-]?key\s*[:=]\s*\S+",
]

INJECTION_PATTERNS = [
    r"ignore (all|these) instructions",
    r"reveal (the )?system prompt",
    r"print (the )?system prompt",
    r"dump (all|the) (documents|chunks|context)",
    r"show me all chunks",
    r"verbatim",
    r"repeat the full document",
]

def contains_secret(text: str) -> bool:
    return any(re.search(p, text or "", re.IGNORECASE) for p in SECRET_PATTERNS)

def looks_like_injection(text: str) -> bool:
    return any(re.search(p, text or "", re.IGNORECASE) for p in INJECTION_PATTERNS)

def looks_like_json(text: str) -> bool:
    t = (text or "").strip()
    if not (t.startswith("{") or t.startswith("[")):
        return False
    try:
        json.loads(t)
        return True
    except Exception:
        return False

# --- Supabase helpers ---
def rpc(fn_name: str, payload: dict):
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn_name}"
    r = requests.post(url, headers=headers, json=payload, timeout=60, verify=False)
    r.raise_for_status()
    return r.json()

def insert_row(table: str, row: dict) -> dict:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = requests.post(url, headers=headers, json=[row], timeout=60, verify=False)
    r.raise_for_status()
    return r.json()[0]

# --- Load system prompt from docs ---
def load_system_prompt() -> str:
    path = os.path.join("docs", "04-agent-prompt.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# --- Memory retrieval (user history) ---
def build_user_memory(query: str) -> str:
    try:
        memories = rpc("search_user_messages", {
            "search_query": query,
            "user_uuid": USER_ID,
            "max_results": 6
        })
    except Exception:
        return "(memory search failed)"

    if not memories:
        return "(no relevant user memory found)"

    lines = []
    for m in memories:
        c = (m.get("content") or "")[:300].replace("\n", " ")
        lines.append("- " + c)
    return "\n".join(lines)

# --- Doc RAG (hybrid) ---
def embed_query(text: str):
    emb = client.embeddings.create(model="text-embedding-3-small", input=[text])
    return emb.data[0].embedding

def extract_keywords(query: str):
    words = re.findall(r"[A-Za-z0-9]+", query)
    candidates = [w for w in words if len(w) >= 4]
    return candidates[:6]

def search_docs_hybrid(query: str):
    debug_lines = []
    merged = []
    seen = set()
    top_score = None

    # Vector search
    try:
        q_emb = embed_query(query)
        vect = rpc("search_knowledge_chunks", {
            "query_embedding": q_emb,
            "match_count": 12
        })
        if vect:
            top_score = float(vect[0].get("score") or 0)

        for c in (vect or []):
            txt = (c.get("content") or "").strip()
            if not txt:
                continue
            key = txt[:200]
            if key not in seen:
                seen.add(key)
                merged.append(txt)
                debug_lines.append(f"[VECTOR score={c.get('score')}] {txt[:220].replace(chr(10),' ')}")
    except Exception as e:
        debug_lines.append(f"(vector search failed: {e})")

    # Keyword search (optional RPC)
    for kw in extract_keywords(query):
        try:
            hits = rpc("search_knowledge_chunks_keyword", {
                "keyword": kw,
                "match_count": 6
            })
            for h in hits:
                txt = (h.get("content") or "").strip()
                if not txt:
                    continue
                key = txt[:200]
                if key not in seen:
                    seen.add(key)
                    merged.append(txt)
                    debug_lines.append(f"[KEYWORD kw={kw}] {txt[:220].replace(chr(10),' ')}")
        except Exception:
            pass

    if not merged:
        return "(no relevant docs found)", debug_lines, top_score

    merged = merged[:10]
    context_text = "\n".join([f"- {m[:650].replace(chr(10),' ')}" for m in merged])
    return context_text, debug_lines, top_score

# --- Intent detection (wider scope, not strict keywords) ---
def detect_intent(user_input: str) -> str:
    """
    Returns: FLOW_REVIEW | GOVERNANCE_QNA | HOWTO_QNA | OUT_OF_SCOPE
    """

    t = (user_input or "").lower()

    # 1) JSON => flow review
    if looks_like_json(user_input):
        return "FLOW_REVIEW"

    # 2) Explicit flow improvement request
    if any(w in t for w in ["optimize", "optimise", "review", "analyze", "analyse", "improve", "fix my flow", "doesn't work", "not working"]):
        return "FLOW_REVIEW"

    # 3) Governance/policy questions
    if any(w in t for w in ["dlp", "allowed", "approved", "blocked", "arb", "governance", "policy", "environment", "tenant"]):
        return "GOVERNANCE_QNA"

    # 4) Power Automate how-to questions (this is your missing piece)
    if any(w in t for w in ["power automate", "power platform", "flow", "trigger", "action", "outlook", "email", "attachment", "sharepoint", "excel"]):
        return "HOWTO_QNA"

    # 5) Otherwise out of scope
    return "OUT_OF_SCOPE"

# --- Style instructions per mode ---
QNA_GOV_STYLE = """
You are answering a GOVERNANCE question.
Be short and direct.

Format:
Answer: 1–3 sentences.
Evidence: 1–3 bullets quoting/paraphrasing only what is in retrieved docs.
If docs do not contain the answer -> say: "I cannot find this in the available documents for this tenant."
Then ask up to 2 clarifying questions.
"""

QNA_HOWTO_STYLE = """
You are answering a HOW-TO question about building or fixing a Power Automate flow.
Be practical and step-by-step.

Format:
1) Short answer (1–2 sentences)
2) Steps to do in Power Automate (bullets)
3) If needed: 1–2 questions to clarify

Important:
- If docs have relevant guidance, use them.
- If docs do not contain guidance, you MAY answer using general Power Automate knowledge.
- When using general knowledge, label it clearly:
  "General guidance (not from tenant governance docs): ..."
"""

FLOW_REVIEW_STYLE = """
You are in FLOW REVIEW mode.
Give a clear optimization report:

What it does (short)
Issues (what + why)
Fix steps (very specific)
Questions (max 3)
Confidence 0-100

Do NOT use academic A/B/C sections. Keep it actionable.
"""

# --- Main ---
def main():
    print("=== Power Automate Helper Agent (OpenAI + Supabase + Hybrid RAG) ===")
    user_input = input("Paste flow JSON or ask a question: ").strip()

    # Create a session
    session = insert_row("sessions", {"user_id": USER_ID, "metadata": {"channel": "cli"}})
    session_id = session["id"]

    # Security checks
    if contains_secret(user_input):
        print("\n⚠️ Input looks like it contains a secret (token/password/key). Please redact it and try again.\n")
        insert_row("messages", {
            "user_id": USER_ID,
            "session_id": session_id,
            "role": "user",
            "content": "[REDACTED: secret detected]",
            "metadata": {"event_type": "secret_detected", "secret_detected": True}
        })
        return

    if looks_like_injection(user_input):
        print("\n⚠️ That request looks like a prompt-injection / data-exfiltration attempt. I can’t help with that.\n")
        insert_row("messages", {
            "user_id": USER_ID,
            "session_id": session_id,
            "role": "user",
            "content": user_input,
            "metadata": {"event_type": "prompt_injection_attempt"}
        })
        return

    mode = detect_intent(user_input)

    if mode == "OUT_OF_SCOPE":
        print("\nI can help with Power Automate flow building/review and tenant governance (connectors/DLP/environments). Please rephrase your question in that area.\n")
        insert_row("messages", {
            "user_id": USER_ID,
            "session_id": session_id,
            "role": "user",
            "content": user_input,
            "metadata": {"event_type": "out_of_scope"}
        })
        return

    # Log user message
    insert_row("messages", {
        "user_id": USER_ID,
        "session_id": session_id,
        "role": "user",
        "content": user_input,
        "metadata": {"type": "agent_input", "mode": mode}
    })

    print("...retrieving memory")
    user_memory = build_user_memory(user_input)

    print("...retrieving documents (RAG)")
    doc_context, rag_debug, top_score = search_docs_hybrid(user_input)

    if DEBUG_RAG:
        print("\n--- RAG DEBUG (first 20) ---")
        for line in rag_debug[:20]:
            print(line)
        print("--- END RAG DEBUG ---\n")

    # Confidence handling (IMPORTANT FIX)
    # - For FLOW_REVIEW: do NOT block if docs are weak (flow JSON is the main source)
    # - For GOVERNANCE: be strict
    # - For HOWTO: allow general guidance even if docs weak
    event_type = None
    if mode == "GOVERNANCE_QNA":
        if top_score is None or top_score < GOVERNANCE_MIN_TOP_SCORE:
            event_type = "low_confidence_abstain"

    print("...building prompt")

    system_prompt = load_system_prompt()
    style = FLOW_REVIEW_STYLE if mode == "FLOW_REVIEW" else (QNA_GOV_STYLE if mode == "GOVERNANCE_QNA" else QNA_HOWTO_STYLE)

    # If governance is low confidence, we still call LLM, but instruct it to abstain + ask questions
    extra_rule = ""
    if event_type == "low_confidence_abstain":
        extra_rule = f"""
IMPORTANT: Retrieval top_score={top_score}. This is below the threshold ({GOVERNANCE_MIN_TOP_SCORE}).
You MUST abstain:
- Say you cannot find the answer in tenant documents
- Ask up to 2 clarifying questions
Do NOT guess.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": style + "\n" + extra_rule},
        {"role": "user", "content": f"""User memory:
{user_memory}

Document context (RAG from tenant knowledge):
{doc_context}

User input:
{user_input}
"""}
    ]

    print("...calling OpenAI (this may take a few seconds)")
    try:
        t0 = time.time()
        resp = client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages
        )
        latency = round(time.time() - t0, 2)
    except Exception as e:
        print("\n❌ OpenAI request failed:", str(e))
        insert_row("messages", {
            "user_id": USER_ID,
            "session_id": session_id,
            "role": "assistant",
            "content": f"[ERROR] OpenAI request failed: {e}",
            "metadata": {"event_type": "openai_error", "mode": mode}
        })
        return

    answer = resp.choices[0].message.content

    print("\n--- ANSWER ---\n")
    print(answer)

    # Log assistant answer + audit metadata
    insert_row("messages", {
        "user_id": USER_ID,
        "session_id": session_id,
        "role": "assistant",
        "content": answer,
        "metadata": {
            "type": "agent_output",
            "mode": mode,
            "model": "gpt-5-nano",
            "used_user_memory": True,
            "used_doc_rag": True,
            "rag_mode": "hybrid",
            "debug_rag": DEBUG_RAG,
            "top_score": top_score,
            "event_type": event_type,
            "latency_s": latency
        }
    })

if __name__ == "__main__":
    main()
