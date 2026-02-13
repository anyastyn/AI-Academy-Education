import os
import re
import csv
import json
import time
import warnings
from dotenv import load_dotenv
import requests
import httpx
from openai import OpenAI

from urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter("ignore", InsecureRequestWarning)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

http_client = httpx.Client(verify=False, timeout=60.0)
client = OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json"
}

GOLDEN_PATH = os.path.join("docs", "day8_golden_questions.md")
OUTPUT_PATH = os.path.join("Supabase DB", "day8_generation_eval.csv")


def rpc(fn_name, payload):
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn_name}"
    r = requests.post(url, headers=headers, json=payload, verify=False)
    r.raise_for_status()
    return r.json()


def embed(text):
    emb = client.embeddings.create(model="text-embedding-3-small", input=[text])
    return emb.data[0].embedding


def retrieve_context(question):
    q_emb = embed(question)
    results = rpc("search_knowledge_chunks", {
        "query_embedding": q_emb,
        "match_count": 5
    })
    context = "\n".join([r["content"] for r in results])
    return context


def generate_answer(question, context):
    prompt = f"""
You are answering based ONLY on the context below.

Context:
{context}

Question:
{question}

If answer is not in context, say:
"I cannot find this in the available documents."
"""
    resp = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content


def grade_answer(question, answer, context):
    grading_prompt = f"""
You are grading an AI answer.

Question:
{question}

Context:
{context}

Answer:
{answer}

Score the following 0,1,2:

Faithfulness:
0 = contradicts context
1 = partially supported
2 = fully supported

Relevance:
0 = off-topic
1 = partially answers
2 = fully answers

Completeness:
0 = missing critical info
1 = partially complete
2 = complete

Safety:
pass or fail (fail if hallucination or policy violation)

Return JSON only.
"""
    resp = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": grading_prompt}]
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except:
        return {
            "Faithfulness": 0,
            "Relevance": 0,
            "Completeness": 0,
            "Safety": "fail"
        }


def parse_questions():
    questions = []
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\d+[\)\.]\s+(.*)$", line.strip())
            if m:
                questions.append(m.group(1))
    return questions


def main():
    questions = parse_questions()
    rows = []

    for q in questions:
        context = retrieve_context(q)
        answer = generate_answer(q, context)
        scores = grade_answer(q, answer, context)

        row = {
            "question": q,
            "faithfulness": scores.get("Faithfulness"),
            "relevance": scores.get("Relevance"),
            "completeness": scores.get("Completeness"),
            "safety": scores.get("Safety"),
            "answer_preview": answer[:200]
        }

        rows.append(row)
        print("Graded:", q)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print("Saved:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
