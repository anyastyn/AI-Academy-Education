import os
import re
import csv
import time
import warnings
from typing import List, Dict, Any

from dotenv import load_dotenv
import requests
import httpx
from openai import OpenAI

# Hide SSL warning spam (because you're using verify=False)
from urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter("ignore", InsecureRequestWarning)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not all([SUPABASE_URL, SERVICE_KEY, OPENAI_API_KEY]):
    raise SystemExit("Missing env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY")

# OpenAI client (verify=False needed in your environment)
http_client = httpx.Client(verify=False, timeout=60.0)
client = OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json"
}

# Paths (match your repo)
GOLDEN_MD_PATH = os.path.join("docs", "day8_golden_questions.md")
OUTPUT_CSV_PATH = os.path.join("Supabase DB", "day8_rag_results.csv")

# Day 8 canonical categories (what your dashboard should use)
EXPECTED_SECTIONS = ["factual", "inferential", "procedural", "out_of_scope", "adversarial"]

# -----------------------------
# Supabase + Embeddings
# -----------------------------
def rpc(fn_name: str, payload: Dict[str, Any]) -> Any:
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn_name}"
    r = requests.post(url, headers=headers, json=payload, verify=False, timeout=60)
    r.raise_for_status()
    return r.json()

def embed(text: str) -> List[float]:
    emb = client.embeddings.create(model="text-embedding-3-small", input=[text])
    return emb.data[0].embedding

# -----------------------------
# Parsing Golden Questions
# -----------------------------
def normalize_section(raw: str) -> str:
    """
    Maps headings to Day 8 canonical categories.
    Supports both:
      - Factual/Inferential/Procedural/Out-of-scope/Adversarial (preferred)
      - In-Scope/Out-of-Scope/Tricky (legacy)
    """
    s = (raw or "").strip().lower()

    # Preferred Day 8 headings
    if "factual" in s:
        return "factual"
    if "inferential" in s:
        return "inferential"
    if "procedural" in s:
        return "procedural"
    if "out" in s and "scope" in s:
        return "out_of_scope"
    if "adversarial" in s or "prompt injection" in s or "attack" in s:
        return "adversarial"

    # Legacy headings (map to closest Day 8 category)
    if "in-scope" in s or "in scope" in s:
        # If you didn’t categorize yet, treat these as "factual" by default
        return "factual"
    if "tricky" in s or "edge" in s:
        # Tricky ≈ inferential (usually needs careful reasoning)
        return "inferential"

    return "factual"  # safe default

def parse_questions_from_md(md_path: str) -> List[Dict[str, Any]]:
    """
    Reads questions from markdown file.

    Detects sections from headings like:
      ## Factual
      ## Inferential
      ## Procedural
      ## Out-of-scope
      ## Adversarial

    Also supports legacy headings:
      ## In-Scope
      ## Out-of-Scope
      ## Tricky

    Questions are lines like:
      1) Question text
      1. Question text

    Returns:
      {id:int, question:str, section:str}
    """
    if not os.path.exists(md_path):
        raise SystemExit(f"Could not find {md_path}. Create it first.")

    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_section = "factual"
    questions: List[Dict[str, Any]] = []

    for line in lines:
        line_stripped = line.strip()

        # Heading detection (markdown headings)
        if re.match(r"^#{1,6}\s+", line_stripped):
            current_section = normalize_section(line_stripped)
            continue

        # Question detection: "12) blah" or "12. blah"
        m = re.match(r"^(\d+)[\)\.]\s+(.*)$", line_stripped)
        if m:
            q_id = int(m.group(1))
            q_text = m.group(2).strip()
            if q_text:
                questions.append({"id": q_id, "question": q_text, "section": current_section})

    if not questions:
        raise SystemExit("No questions found. Use lines like '1) ...' under section headings.")

    return questions

# -----------------------------
# Retrieval + Scoring
# -----------------------------
def run_retrieval(question: str, k: int = 5) -> List[Dict[str, Any]]:
    q_emb = embed(question)
    results = rpc("search_knowledge_chunks", {
        "query_embedding": q_emb,
        "match_count": k
    })
    return results

def preview(text: str, n: int = 140) -> str:
    return (text or "").replace("\n", " ")[:n]

def found_by_threshold(results: List[Dict[str, Any]], min_score: float = 0.55) -> bool:
    """
    Heuristic: treat as found if top score >= threshold.
    NOTE: 0.60 was too strict in your examples (you had many ~0.57).
    """
    if not results:
        return False
    top_score = results[0].get("score")
    if top_score is None:
        return False
    try:
        return float(top_score) >= min_score
    except Exception:
        return False

def expected_found_for_section(section: str) -> bool:
    """
    For retrieval testing:
      - out_of_scope: should NOT retrieve relevant content (expect not found)
      - adversarial: should retrieve policy/governance chunks (expect found)
      - factual/inferential/procedural: expect found
    """
    return section in {"factual", "inferential", "procedural", "adversarial"}

# -----------------------------
# Main
# -----------------------------
def main():
    print("=== Day 8: Golden Test Set Retrieval Run ===")
    print(f"Reading questions from: {GOLDEN_MD_PATH}")

    questions = parse_questions_from_md(GOLDEN_MD_PATH)
    print(f"Found {len(questions)} questions.\n")

    # Create output folder if needed
    out_dir = os.path.dirname(OUTPUT_CSV_PATH)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    started = time.time()
    pass_count = 0

    for item in sorted(questions, key=lambda x: x["id"]):
        q_id = item["id"]
        q_text = item["question"]
        section = item["section"]

        # Always enforce canonical sections
        if section not in EXPECTED_SECTIONS:
            section = normalize_section(section)

        t0 = time.time()
        results = run_retrieval(q_text, k=5)
        latency_s = round(time.time() - t0, 3)

        top_score = float(results[0].get("score")) if results and results[0].get("score") is not None else None
        top_preview = preview(results[0].get("content", "")) if results else ""
        second_preview = preview(results[1].get("content", "")) if len(results) > 1 else ""

        found = found_by_threshold(results, min_score=0.55)
        expected_found = expected_found_for_section(section)

        passed = (found == expected_found)
        if passed:
            pass_count += 1

        rows.append({
            "id": q_id,
            "section": section,
            "question": q_text,
            "expected": "found" if expected_found else "not_found",
            "found_by_score_threshold": 1 if found else 0,
            "passed_retrieval_check": 1 if passed else 0,
            "top_score": top_score if top_score is not None else "",
            "latency_s": latency_s,
            "top_chunk_preview": top_preview,
            "second_chunk_preview": second_preview
        })

        print(f"{q_id}) [{section}] {q_text}")
        print(f"   top_score={top_score} latency={latency_s}s expected={'found' if expected_found else 'not_found'} found={found} => {'✅PASS' if passed else '❌FAIL'}")
        print(f"   top_preview: {top_preview}...")
        print()

    total = len(rows)
    elapsed = round(time.time() - started, 2)

    # Write CSV (IMPORTANT: numbers not strings)
    with open(OUTPUT_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("=== Summary ===")
    print(f"Saved results CSV: {OUTPUT_CSV_PATH}")
    print(f"Retrieval pass rate: {pass_count}/{total} = {round(pass_count/total*100, 1)}%")
    print(f"Total runtime: {elapsed}s")
    print("\nNext step: Refresh your Streamlit dashboard — the charts should now work correctly.")

if __name__ == "__main__":
    main()
