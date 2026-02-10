import os, re, requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
USER_ID = os.getenv("USER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not all([SUPABASE_URL, SERVICE_KEY, USER_ID, OPENAI_API_KEY]):
    raise SystemExit("Missing env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, USER_ID, OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# --- Secret detection (simple) ---
SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{10,}",
    r"Authorization:\s*Bearer\s+\S+",
    r"client_secret\s*[:=]\s*\S+",
    r"password\s*[:=]\s*\S+",
    r"api[_-]?key\s*[:=]\s*\S+",
]

def contains_secret(text: str) -> bool:
    return any(re.search(p, text or "", re.IGNORECASE) for p in SECRET_PATTERNS)

def rpc(fn_name: str, payload: dict):
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn_name}"
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def insert_row(table: str, row: dict) -> dict:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = requests.post(url, headers=headers, json=[row], timeout=60)
    r.raise_for_status()
    return r.json()[0]

def build_user_memory(query: str) -> str:
    try:
        memories = rpc("search_user_messages", {
            "search_query": query,
            "user_uuid": USER_ID,
            "max_results": 5
        })
    except Exception:
        return "(memory search failed)"

    if not memories:
        return "(no relevant user memory found)"

    lines = []
    for m in memories:
        c = (m.get("content") or "")[:350].replace("\n", " ")
        lines.append("- " + c)
    return "\n".join(lines)

def embed_query(text: str):
    emb = client.embeddings.create(model="text-embedding-3-small", input=[text])
    return emb.data[0].embedding

def search_docs(query: str) -> str:
    """
    Day7 document RAG:
    - embed the query
    - retrieve top knowledge chunks from Supabase
    """
    try:
        q_emb = embed_query(query)
        chunks = rpc("search_knowledge_chunks", {
            "query_embedding": q_emb,
            "match_count": 5
        })
    except Exception:
        return "(doc search failed — did you run the Day7 SQL in Supabase?)"

    if not chunks:
        return "(no relevant docs found)"

    out = []
    for c in chunks:
        txt = (c.get("content") or "")[:500].replace("\n", " ")
        score = c.get("score")
        out.append(f"- (score {score:.3f}) {txt}" if score is not None else f"- {txt}")
    return "\n".join(out)

def load_system_prompt() -> str:
    path = os.path.join("docs", "04-agent-prompt.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def main():
    print("=== Power Automate Helper Agent (OpenAI + Supabase + Day7 RAG) ===")
    user_input = input("Paste flow JSON or ask a question: ").strip()

    # Create session row
    session = insert_row("sessions", {"user_id": USER_ID, "metadata": {"channel": "cli"}})
    session_id = session["id"]

    # Secret protection
    if contains_secret(user_input):
        print("\n⚠️ Your input looks like it contains a secret (token/password/key).")
        print("Please redact it and paste again. I will not store or process secrets.\n")
        insert_row("messages", {
            "user_id": USER_ID,
            "session_id": session_id,
            "role": "user",
            "content": "[REDACTED: secret detected]",
            "metadata": {"secret_detected": True}
        })
        return

    # Save user message
    insert_row("messages", {
        "user_id": USER_ID,
        "session_id": session_id,
        "role": "user",
        "content": user_input,
        "metadata": {"type": "agent_input", "mode": "review"}
    })

    # Retrieve context
    user_memory = build_user_memory(user_input)
    doc_context = search_docs(user_input)

    system_prompt = load_system_prompt()

    # Call LLM
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"""User memory:
{user_memory}

Document context (RAG from 'RAG Data'):
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

    # Save assistant message
    insert_row("messages", {
        "user_id": USER_ID,
        "session_id": session_id,
        "role": "assistant",
        "content": answer,
        "metadata": {
            "type": "agent_output",
            "mode": "review",
            "model": "gpt-5-nano",
            "used_user_memory": True,
            "used_doc_rag": True
        }
    })

if __name__ == "__main__":
    main()
