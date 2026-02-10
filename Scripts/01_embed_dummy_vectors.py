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
}

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{10,}",
    r"Authorization:\s*Bearer\s+\S+",
    r"client_secret\s*[:=]\s*\S+",
    r"password\s*[:=]\s*\S+",
    r"api[_-]?key\s*[:=]\s*\S+",
]

def contains_secret(text: str) -> bool:
    return any(re.search(p, text or "", re.IGNORECASE) for p in SECRET_PATTERNS)

def to_pgvector(vec):
    return "[" + ",".join(str(x) for x in vec) + "]"

# Fetch messages needing embeddings
select_cols = "id,content"
url = (
    f"{SUPABASE_URL}/rest/v1/messages"
    f"?select={select_cols}"
    f"&user_id=eq.{USER_ID}"
    f"&embedding=is.null"
    f"&order=created_at.asc"
    f"&limit=50"
)

resp = requests.get(url, headers=headers, timeout=60)
resp.raise_for_status()
rows = resp.json()

if not rows:
    print("✅ No NULL embeddings found.")
    raise SystemExit(0)

# Filter out unsafe rows
safe_rows = []
safe_texts = []
for r in rows:
    txt = r.get("content") or ""
    if not txt.strip():
        continue
    if contains_secret(txt):
        # do not embed secrets
        print("⚠️ Skipping embedding (secret detected) for:", r["id"])
        continue
    # avoid embedding extremely large payloads (simple)
    if len(txt) > 15000:
        print("⚠️ Skipping embedding (too long) for:", r["id"])
        continue
    safe_rows.append(r)
    safe_texts.append(txt)

if not safe_rows:
    print("✅ No safe rows to embed.")
    raise SystemExit(0)

emb = client.embeddings.create(
    model="text-embedding-3-small",
    input=safe_texts
)

for r, d in zip(safe_rows, emb.data):
    msg_id = r["id"]
    emb_str = to_pgvector(d.embedding)

    patch_url = f"{SUPABASE_URL}/rest/v1/messages?id=eq.{msg_id}"
    patch = requests.patch(
        patch_url,
        headers={**headers, "Prefer": "return=minimal"},
        json={"embedding": emb_str},
        timeout=60
    )
    patch.raise_for_status()
    print("✅ Embedded:", msg_id)

print("🎉 Done. Real embeddings inserted.")
