import os, requests
from dotenv import load_dotenv

load_dotenv()



SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
USER_ID = os.getenv("USER_ID")
print("SUPABASE_URL =", SUPABASE_URL)
print("KEY starts with =", (SERVICE_KEY or "")[:8])
print("USER_ID =", USER_ID)
headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

AGENT_INSTRUCTIONS = """You are a Power Automate helper and optimizer.
You must output:
1) What the flow does
2) Problems found (what + why)
3) Exact fixes (settings / expressions)
4) Questions needed (max 4)
Rules: advisory only, no secrets, no bypass, be practical.
"""

def rpc(fn_name: str, payload: dict):
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn_name}"
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def insert_message(role: str, content: str, metadata=None):
    url = f"{SUPABASE_URL}/rest/v1/messages"
    body = [{
        "user_id": USER_ID,
        "role": role,
        "content": content,
        "metadata": metadata or {}
    }]
    r = requests.post(url, headers=headers, json=body, timeout=60)
    r.raise_for_status()
    return r.json()[0]["id"]

def build_context(question: str):
    # uses your function: search_user_messages(search_query, user_uuid, max_results)
    memories = rpc("search_user_messages", {
        "search_query": question,
        "user_uuid": USER_ID,
        "max_results": 5
    })

    if not memories:
        return "(no relevant memories found)"

    # keep small
    lines = []
    for m in memories:
        c = (m.get("content") or "")[:300].replace("\n", " ")
        lines.append("- " + c)
    return "\n".join(lines)

def main():
    print("=== Power Automate Helper Agent (Memory Demo) ===")
    question = input("Ask your question: ").strip()

    # 1) store user message
    qid = insert_message("user", question, {"type": "agent_input"})
    print("Saved user message:", qid)

    # 2) retrieve memory
    context = build_context(question)

    # 3) create the prompt (this is what would be sent to an LLM)
    prompt = f"""{AGENT_INSTRUCTIONS}

Relevant memory from Supabase:
{context}

User question:
{question}
"""

    print("\n--- PROMPT PREVIEW (what an LLM would receive) ---\n")
    print(prompt[:2000])
    print("\n--- END PREVIEW ---\n")

    # 4) placeholder "agent response"
    answer = (
        "DEMO MODE: memory retrieval + logging works.\n"
        "Next step: connect an LLM (Azure/OpenAI) to generate real recommendations.\n"
        "The prompt above shows that the agent receives memory context.\n"
    )

    # 5) store agent output
    aid = insert_message("assistant", answer, {"type": "agent_output", "mode": "demo"})
    print("Saved agent output:", aid)

if __name__ == "__main__":
    main()
