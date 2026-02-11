import os
import re
import json
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

# Corporate SSL workaround
http_client = httpx.Client(verify=False, timeout=60.0)
client = OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# Toggle this when debugging retrieval. Keep False for normal user experience.
DEBUG_RAG = False

# -------- Security: basic secret detection --------
SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{10,}",
    r"Authorization:\s*Bearer\s+\S+",
    r"client_secret\s*[:=]\s*\S+",
    r"password\s*[:=]\s*\S+",
    r"api[_-]?key\s*[:=]\s*\S+",
]

def contains_secret(text: str) -> bool:
    return any(re.search(p, text or "", re.IGNORECASE) for p in SECRET_PATTERNS)

# -------- Supabase helpers (verify=False) --------
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

# -------- Load system prompt --------
def load_system_prompt() -> str:
    path = os.path.join("docs", "04-agent-prompt.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# -------- Memory RAG --------
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

# -------- Doc RAG (Hybrid) --------
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

    # Vector search
    try:
        q_emb = embed_query(query)
        vect = rpc("search_knowledge_chunks", {
            "query_embedding": q_emb,
            "match_count": 15
        })
        for c in vect:
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

    # Keyword search (works only if you created the RPC)
    for kw in extract_keywords(query):
        try:
            hits = rpc("search_knowledge_chunks_keyword", {
                "keyword": kw,
                "match_count": 8
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
        return "(no relevant docs found)", debug_lines

    # Keep prompt small
    merged = merged[:10]
    context_text = "\n".join([f"- {m[:650].replace(chr(10),' ')}" for m in merged])
    return context_text, debug_lines

# -------- Intent detection (Q&A vs Flow Review) --------
FLOW_KEYWORDS = [
    "power automate", "flow", "trigger", "actions", "runAfter", "apply_to_each",
    "foreach", "scope", "retry", "concurrency", "pagination", "connector", "http",
    "dataverse", "sharepoint", "onedrive", "condition", "compose"
]

def looks_like_json(text: str) -> bool:
    t = (text or "").strip()
    if not (t.startswith("{") or t.startswith("[")):
        return False
    try:
        json.loads(t)
        return True
    except Exception:
        return False

def detect_mode(user_input: str) -> str:
    """
    Returns:
      - "FLOW_REVIEW" if user likely wants analysis/optimization
      - "QNA" if user just asks a question
    """
    t = (user_input or "").lower()

    # If it is JSON, treat as flow review
    if looks_like_json(user_input):
        return "FLOW_REVIEW"

    # If user explicitly requests analyze/optimize
    if any(w in t for w in ["analyze", "optimise", "optimize", "review", "improve", "performance", "refactor"]):
        return "FLOW_REVIEW"

    # If user mentions flow-y keywords AND asks about "my flow" / "this flow"
    if ("my flow" in t or "this flow" in t or "flow json" in t) and any(k in t for k in FLOW_KEYWORDS):
        return "FLOW_REVIEW"

    # Otherwise default to Q&A
    return "QNA"

# -------- Mode instructions (this is the key improvement) --------
QNA_STYLE_INSTRUCTIONS = """
You are in Q&A mode.
Be short and direct.

Output format (always):
1) Answer (1–3 sentences)
2) Evidence (1–2 bullets from retrieved documents; do NOT invent)
3) If unclear: ask up to 2 questions (only if truly needed)

Do NOT print the long flow-review PLAN template unless user asked for analysis/optimization or provided flow JSON.
"""

FLOW_REVIEW_STYLE_INSTRUCTIONS = """
You are in FLOW REVIEW mode (Planning + ReAct).
Use the full structure from the system prompt:
- Show PLAN
- Findings (What/Why)
- Fixes
- Questions (max 4)
- Confidence
"""

def main():
    print("=== Power Automate Helper Agent (OpenAI + Supabase + Hybrid RAG) ===")
    user_input = input("Paste flow JSON or ask a question: ").strip()

    session = insert_row("sessions", {"user_id": USER_ID, "metadata": {"channel": "cli"}})
    session_id = session["id"]

    if contains_secret(user_input):
        print("\n⚠️ Input looks like it contains a secret. Please redact it and try again.\n")
        insert_row("messages", {
            "user_id": USER_ID,
            "session_id": session_id,
            "role": "user",
            "content": "[REDACTED: secret detected]",
            "metadata": {"secret_detected": True}
        })
        return

    mode = detect_mode(user_input)

    insert_row("messages", {
        "user_id": USER_ID,
        "session_id": session_id,
        "role": "user",
        "content": user_input,
        "metadata": {"type": "agent_input", "mode": mode}
    })

    user_memory = build_user_memory(user_input)
    doc_context, rag_debug = search_docs_hybrid(user_input)

    if DEBUG_RAG:
        print("\n--- RAG DEBUG: Retrieved chunks ---")
        for line in rag_debug[:25]:
            print(line)
        print("--- END RAG DEBUG ---\n")

    system_prompt = load_system_prompt()

    # Give the LLM explicit style instructions based on detected mode
    style = FLOW_REVIEW_STYLE_INSTRUCTIONS if mode == "FLOW_REVIEW" else QNA_STYLE_INSTRUCTIONS

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": style},
        {"role": "user", "content": f"""User memory:
{user_memory}

Document context (Hybrid RAG from 'RAG Data'):
{doc_context}

User input:
{user_input}
"""}
    ]

    resp = client.chat.completions.create(
        model="gpt-5-nano",
        messages=messages
    )
    answer = resp.choices[0].message.content

    print("\n--- ANSWER ---\n")
    print(answer)

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
            "debug_rag": DEBUG_RAG
        }
    })

if __name__ == "__main__":
    main()
