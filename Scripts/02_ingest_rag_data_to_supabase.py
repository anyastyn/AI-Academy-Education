import os
import glob
import requests
from dotenv import load_dotenv
from openai import OpenAI

# For DOCX/XLSX parsing
from docx import Document
from openpyxl import load_workbook

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not all([SUPABASE_URL, SERVICE_KEY, OPENAI_API_KEY]):
    raise SystemExit("Missing env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

RAG_FOLDER = "RAG Data"  # root folder; keep exact spelling + space

def insert_row(table: str, row: dict) -> dict:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = requests.post(url, headers=headers, json=[row], timeout=60)
    r.raise_for_status()
    return r.json()[0]

def to_pgvector(vec):
    return "[" + ",".join(str(x) for x in vec) + "]"

def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120):
    text = (text or "").strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks

def embed_texts(texts):
    emb = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [d.embedding for d in emb.data]

def read_docx(path: str) -> str:
    doc = Document(path)
    parts = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts)

def read_xlsx(path: str) -> str:
    wb = load_workbook(path, data_only=True)
    parts = []
    for sheet in wb.worksheets:
        parts.append(f"# Sheet: {sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c).strip() for c in row if c is not None and str(c).strip() != ""]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)

def load_file_as_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return read_docx(path)
    if ext == ".xlsx":
        return read_xlsx(path)
    raise ValueError(f"Unsupported file type: {ext}")

def main():
    if not os.path.isdir(RAG_FOLDER):
        raise SystemExit(f"Folder not found: '{RAG_FOLDER}'. Create it at repo root and add files.")

    docx_paths = glob.glob(os.path.join(RAG_FOLDER, "*.docx"))
    xlsx_paths = glob.glob(os.path.join(RAG_FOLDER, "*.xlsx"))
    paths = sorted(docx_paths + xlsx_paths)

    if not paths:
        raise SystemExit(f"No .docx/.xlsx files found in '{RAG_FOLDER}'")

    print(f"=== Ingesting knowledge files from: {RAG_FOLDER}/ ===")
    print(f"Found {len(paths)} files.")

    for path in paths:
        filename = os.path.basename(path)
        print(f"\n--- {filename} ---")

        text = load_file_as_text(path).strip()
        if not text:
            print("⚠️ Skipping empty file.")
            continue

        # 1) create knowledge_document row
        doc_row = insert_row("knowledge_documents", {
            "title": filename,
            "source": path,
            "metadata": {"folder": RAG_FOLDER, "type": os.path.splitext(filename)[1].lower()}
        })
        doc_id = doc_row["id"]

        # 2) chunk + embed
        chunks = chunk_text(text)
        if not chunks:
            print("⚠️ No chunks created (empty after cleaning).")
            continue

        embeddings = embed_texts(chunks)

        # 3) insert chunks
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            insert_row("knowledge_chunks", {
                "document_id": doc_id,
                "chunk_index": i,
                "content": chunk,
                "embedding": to_pgvector(emb),
                "metadata": {"filename": filename}
            })

        print(f"✅ Ingested {filename}: {len(chunks)} chunks")

    print("\n🎉 Done. Knowledge base is ready for RAG.")

if __name__ == "__main__":
    main()
