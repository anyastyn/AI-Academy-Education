import os, requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
USER_ID = os.getenv("USER_ID")

oa = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}

def to_pgvector(vec):
    # pgvector expects "[0.1,0.2,...]"
    return "[" + ",".join(str(x) for x in vec) + "]"

# 1) Fetch messages with NULL embedding for this user
# Supabase PostgREST filter: embedding=is.null
select_cols = "id,content"
url = f"{SUPABASE_URL}/rest/v1/messages?select={select_cols}&user_id=eq.{USER_ID}&embedding=is.null&order=created_at.asc&limit=20"

resp = requests.get(url, headers=headers, timeout=60)
resp.raise_for_status()
rows = resp.json()

if not rows:
    print("✅ No NULL embeddings found for this user.")
    raise SystemExit(0)

texts = [r["content"] for r in rows]

# 2) Create embeddings
emb = oa.embeddings.create(
    model="text-embedding-3-small",
    input=texts
)

# 3) Update each row with embedding
for r, d in zip(rows, emb.data):
    msg_id = r["id"]
    emb_str = to_pgvector(d.embedding)

    patch_url = f"{SUPABASE_URL}/rest/v1/messages?id=eq.{msg_id}"
    patch_body = {"embedding": emb_str}

    patch = requests.patch(
        patch_url,
        headers={**headers, "Prefer": "return=minimal"},
        json=patch_body,
        timeout=60
    )
    patch.raise_for_status()
    print("✅ Embedded:", msg_id)

print("Done ✅")
