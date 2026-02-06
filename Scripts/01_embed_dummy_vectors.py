import os, random, requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
USER_ID = os.getenv("USER_ID")

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}

def random_vector(dim=1536):
    # create a stable dummy vector
    return [random.random() for _ in range(dim)]

def to_pgvector(vec):
    return "[" + ",".join(str(x) for x in vec) + "]"

# 1) get messages with NULL embedding
url = (
    f"{SUPABASE_URL}/rest/v1/messages"
    f"?select=id,content"
    f"&user_id=eq.{USER_ID}"
    f"&embedding=is.null"
)

resp = requests.get(url, headers=headers, timeout=60)
resp.raise_for_status()
rows = resp.json()

if not rows:
    print("✅ No NULL embeddings found.")
    raise SystemExit(0)

# 2) update each row with dummy vector
for row in rows:
    emb = random_vector()
    emb_str = to_pgvector(emb)

    patch_url = f"{SUPABASE_URL}/rest/v1/messages?id=eq.{row['id']}"
    patch = requests.patch(
        patch_url,
        headers={**headers, "Prefer": "return=minimal"},
        json={"embedding": emb_str},
        timeout=60,
    )
    patch.raise_for_status()
    print("✅ Dummy embedding saved for", row["id"])

print("🎉 Dummy embeddings inserted.")
