import streamlit as st
import pandas as pd
import os
import math

st.set_page_config(page_title="RAG KPI Dashboard", layout="wide")
st.title("📊 RAG Quality Dashboard (Retrieval + Generation + Alerts)")

RETRIEVAL_CSV = os.path.join("Supabase DB", "day8_rag_results.csv")
GEN_CSV = os.path.join("Supabase DB", "day8_generation_eval.csv")

# -----------------------
# Helpers
# -----------------------
def to_bool(x):
    if pd.isna(x):
        return False
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    return s in ("true", "1", "yes", "y", "pass", "passed")

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def badge(label: str, status: str):
    """
    status: ok | warn | fail
    """
    colors = {
        "ok":   ("#1b5e20", "#c8e6c9"),
        "warn": ("#e65100", "#ffe0b2"),
        "fail": ("#b71c1c", "#ffcdd2"),
    }
    fg, bg = colors.get(status, colors["warn"])
    st.markdown(
        f"<span style='padding:6px 10px;border-radius:10px;background:{bg};color:{fg};font-weight:600;'>"
        f"{label}</span>",
        unsafe_allow_html=True
    )

def approx_tokens(text: str) -> int:
    # Rough token estimate (good enough for KPI dashboard)
    # Common approximation: 1 token ~ 4 chars in English
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))

# -----------------------
# Sidebar controls (thresholds + cost)
# -----------------------
st.sidebar.header("⚙ Dashboard Settings")

st.sidebar.subheader("Alert thresholds")
thr_retrieval_pass = st.sidebar.slider("Retrieval Pass % threshold", 0, 100, 80, 1)
thr_faithfulness = st.sidebar.slider("Faithfulness threshold (0–2)", 0.0, 2.0, 1.6, 0.05)
thr_safety_pass = st.sidebar.slider("Safety Pass % threshold", 0, 100, 95, 1)
thr_latency_p95 = st.sidebar.number_input("p95 latency threshold (seconds)", min_value=0.0, value=5.0, step=0.5)

st.sidebar.subheader("Cost per query (optional)")
st.sidebar.caption("Enter your own prices if you want cost estimates. If left blank/0, cost shows as N/A.")

# Using "per 1M tokens" inputs is easiest and common
price_embed_per_1m = st.sidebar.number_input("Embeddings price per 1M tokens ($)", min_value=0.0, value=0.0, step=0.1)
price_gen_in_per_1m = st.sidebar.number_input("Generation input price per 1M tokens ($)", min_value=0.0, value=0.0, step=0.1)
price_gen_out_per_1m = st.sidebar.number_input("Generation output price per 1M tokens ($)", min_value=0.0, value=0.0, step=0.1)
price_grade_in_per_1m = st.sidebar.number_input("Grading input price per 1M tokens ($)", min_value=0.0, value=0.0, step=0.1)
price_grade_out_per_1m = st.sidebar.number_input("Grading output price per 1M tokens ($)", min_value=0.0, value=0.0, step=0.1)

show_debug = st.sidebar.checkbox("Show debug sections", value=False)

# -----------------------
# Load retrieval results
# -----------------------
retrieval_df = None
if os.path.exists(RETRIEVAL_CSV):
    retrieval_df = pd.read_csv(RETRIEVAL_CSV)

    if "passed_retrieval_check" in retrieval_df.columns:
        retrieval_df["passed_retrieval_check"] = retrieval_df["passed_retrieval_check"].apply(to_bool)
    else:
        retrieval_df["passed_retrieval_check"] = False

    if "latency_s" in retrieval_df.columns:
        retrieval_df["latency_s"] = retrieval_df["latency_s"].apply(safe_float)
    else:
        retrieval_df["latency_s"] = 0.0

    if "section" not in retrieval_df.columns:
        retrieval_df["section"] = "unknown"

    if "question" not in retrieval_df.columns:
        # If your CSV uses different column name, fallback
        # (but your current script includes "question")
        retrieval_df["question"] = retrieval_df.get("q", "")
else:
    st.error(f"Retrieval results CSV not found: {RETRIEVAL_CSV}")
    st.stop()

# -----------------------
# Load generation eval results
# -----------------------
gen_df = None
if os.path.exists(GEN_CSV):
    gen_df = pd.read_csv(GEN_CSV)

    # Normalize columns
    if "question" not in gen_df.columns:
        st.error("Generation CSV must contain a 'question' column.")
        st.stop()

    for col in ["faithfulness", "relevance", "completeness"]:
        if col in gen_df.columns:
            gen_df[col] = gen_df[col].apply(safe_float)
        else:
            gen_df[col] = 0.0

    if "safety" in gen_df.columns:
        gen_df["safety_pass"] = gen_df["safety"].astype(str).str.strip().str.lower().isin(
            ["pass", "safe", "true", "1", "yes"]
        )
    else:
        gen_df["safety_pass"] = True

    if "answer_preview" not in gen_df.columns:
        gen_df["answer_preview"] = ""

else:
    st.warning(f"Generation eval CSV not found: {GEN_CSV}")
    st.info("Run: python Scripts/04_generation_evaluation.py to generate it.")
    gen_df = None

# -----------------------
# Merge (so we can chart by category/section)
# -----------------------
merged = retrieval_df.copy()
if gen_df is not None:
    merged = merged.merge(gen_df, on="question", how="left")

# -----------------------
# KPI Calculations
# -----------------------
total = len(retrieval_df)

retrieval_pass_rate = retrieval_df["passed_retrieval_check"].mean() * 100 if total else 0.0
avg_latency = retrieval_df["latency_s"].mean() if total else 0.0
p95_latency = retrieval_df["latency_s"].quantile(0.95) if total else 0.0

out_scope = retrieval_df[retrieval_df["section"] == "out_of_scope"]
out_scope_rate = out_scope["passed_retrieval_check"].mean() * 100 if len(out_scope) else 0.0

# Generation KPIs if available
avg_faithfulness = avg_relevance = avg_completeness = safety_rate = None
if gen_df is not None and len(gen_df) > 0:
    avg_faithfulness = gen_df["faithfulness"].mean()
    avg_relevance = gen_df["relevance"].mean()
    avg_completeness = gen_df["completeness"].mean()
    safety_rate = gen_df["safety_pass"].mean() * 100

# -----------------------
# Alerts / Status badges
# -----------------------
st.subheader("✅ KPI Summary + Alerts")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Retrieval Pass %", f"{retrieval_pass_rate:.1f}%")
c2.metric("Out-of-Scope Correct %", f"{out_scope_rate:.1f}%")
c3.metric("Avg Latency (s)", f"{avg_latency:.2f}")
c4.metric("p95 Latency (s)", f"{p95_latency:.2f}")

a1, a2, a3, a4 = st.columns(4)

with a1:
    if retrieval_pass_rate >= thr_retrieval_pass:
        badge("Retrieval: OK", "ok")
    elif retrieval_pass_rate >= thr_retrieval_pass - 10:
        badge("Retrieval: Warning", "warn")
    else:
        badge("Retrieval: FAIL", "fail")

with a2:
    if p95_latency <= thr_latency_p95:
        badge("Latency: OK", "ok")
    elif p95_latency <= thr_latency_p95 * 1.5:
        badge("Latency: Warning", "warn")
    else:
        badge("Latency: FAIL", "fail")

with a3:
    if gen_df is None:
        badge("Generation: N/A", "warn")
    else:
        if avg_faithfulness >= thr_faithfulness:
            badge("Faithfulness: OK", "ok")
        elif avg_faithfulness >= thr_faithfulness - 0.2:
            badge("Faithfulness: Warning", "warn")
        else:
            badge("Faithfulness: FAIL", "fail")

with a4:
    if gen_df is None:
        badge("Safety: N/A", "warn")
    else:
        if safety_rate >= thr_safety_pass:
            badge("Safety: OK", "ok")
        elif safety_rate >= thr_safety_pass - 5:
            badge("Safety: Warning", "warn")
        else:
            badge("Safety: FAIL", "fail")

# Friendly alert text
if retrieval_pass_rate < thr_retrieval_pass:
    st.warning("Retrieval pass rate is below threshold. Likely fixes: improve chunking, add more documents (completeness), or tune K/threshold.")
if p95_latency > thr_latency_p95:
    st.warning("Latency p95 is above threshold. Likely fixes: reduce K, reduce chunk size, cache embeddings, or reduce model calls.")
if gen_df is not None and avg_faithfulness < thr_faithfulness:
    st.error("Faithfulness below threshold. In enterprise RAG this is the #1 risk. Fix: stronger 'cite-or-silence', reduce context length, add verifier, improve retrieval precision.")
if gen_df is not None and safety_rate < thr_safety_pass:
    st.error("Safety pass rate below threshold. Fix: stronger refusal rules, document exfiltration protections, injection defenses.")

st.divider()

# -----------------------
# Cost estimate (optional)
# -----------------------
st.subheader("💰 Cost per Query (optional estimate)")

if gen_df is None:
    st.info("Cost estimate is most useful after generation eval exists (because it includes answer length).")
else:
    # We approximate token counts based on question + retrieved context + answer preview.
    # This is not billing-accurate but good enough for KPIs.
    # If prices are 0 -> show N/A.
    prices_ok = any([
        price_embed_per_1m > 0,
        price_gen_in_per_1m > 0,
        price_gen_out_per_1m > 0,
        price_grade_in_per_1m > 0,
        price_grade_out_per_1m > 0,
    ])

    if not prices_ok:
        st.info("Enter token prices in the sidebar to compute cost estimates. Otherwise shown as N/A.")
    else:
        tmp = merged.copy()

        # Make sure we have text to estimate tokens
        tmp["question_tokens"] = tmp["question"].fillna("").apply(approx_tokens)
        tmp["context_tokens_est"] = tmp.get("top_chunk_preview", "").fillna("").apply(approx_tokens) * 5  # rough guess
        tmp["answer_tokens_est"] = tmp.get("answer_preview", "").fillna("").apply(approx_tokens)

        # Embedding cost: question tokens only (your code embeds questions; doc embeddings happen during ingestion)
        tmp["cost_embed"] = (tmp["question_tokens"] / 1_000_000) * price_embed_per_1m

        # Generation cost: question + context as input, answer as output
        tmp["cost_gen_in"] = ((tmp["question_tokens"] + tmp["context_tokens_est"]) / 1_000_000) * price_gen_in_per_1m
        tmp["cost_gen_out"] = (tmp["answer_tokens_est"] / 1_000_000) * price_gen_out_per_1m

        # Grading cost: grading prompt includes question+context+answer (approx)
        tmp["grade_in_tokens_est"] = tmp["question_tokens"] + tmp["context_tokens_est"] + tmp["answer_tokens_est"]
        tmp["cost_grade_in"] = (tmp["grade_in_tokens_est"] / 1_000_000) * price_grade_in_per_1m
        tmp["cost_grade_out"] = (200 / 1_000_000) * price_grade_out_per_1m  # small fixed output JSON

        tmp["cost_total_est"] = tmp["cost_embed"] + tmp["cost_gen_in"] + tmp["cost_gen_out"] + tmp["cost_grade_in"] + tmp["cost_grade_out"]

        avg_cost = tmp["cost_total_est"].mean()
        p95_cost = tmp["cost_total_est"].quantile(0.95)

        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Avg cost/query ($)", f"{avg_cost:.4f}")
        cc2.metric("p95 cost/query ($)", f"{p95_cost:.4f}")
        cc3.metric("Queries in dataset", str(len(tmp)))

        if show_debug:
            st.caption("Cost breakdown preview (first 10 rows)")
            st.dataframe(tmp[["question", "cost_total_est", "cost_embed", "cost_gen_in", "cost_gen_out", "cost_grade_in", "cost_grade_out"]].head(10))

st.divider()

# -----------------------
# Retrieval charts
# -----------------------
st.subheader("🔎 Retrieval Metrics")

r1, r2 = st.columns(2)

with r1:
    st.caption("Latency per Question")
    if "id" not in retrieval_df.columns:
        retrieval_df["id"] = range(1, len(retrieval_df) + 1)
    st.line_chart(retrieval_df[["id", "latency_s"]].set_index("id"))

with r2:
    st.caption("Retrieval Pass Rate by Section (%)")
    section_summary = retrieval_df.groupby("section")["passed_retrieval_check"].mean() * 100
    st.bar_chart(section_summary)

st.divider()

# -----------------------
# Generation charts
# -----------------------
st.subheader("🧠 Generation Quality (LLM grading)")

if gen_df is None:
    st.info("Run generation evaluation first: python Scripts/04_generation_evaluation.py")
else:
    g1, g2 = st.columns(2)

    with g1:
        st.caption("Average score (0–2)")
        score_summary = pd.DataFrame({
            "faithfulness": [gen_df["faithfulness"].mean()],
            "relevance": [gen_df["relevance"].mean()],
            "completeness": [gen_df["completeness"].mean()],
        }).T
        score_summary.columns = ["avg"]
        st.bar_chart(score_summary)

    with g2:
        st.caption("Safety pass/fail")
        safety_counts = gen_df["safety_pass"].value_counts().rename(index={True: "PASS", False: "FAIL"})
        st.bar_chart(safety_counts)

    st.divider()

    st.subheader("📌 Scores by Category (Section)")
    # We need section from retrieval file; merged includes it
    if "section" in merged.columns:
        by_section = merged.groupby("section")[["faithfulness", "relevance", "completeness"]].mean()
        st.dataframe(by_section)
        st.bar_chart(by_section)
    else:
        st.info("No 'section' column found to group scores by category.")

st.divider()

# -----------------------
# Worst 5 questions (helpful for debugging)
# -----------------------
st.subheader("🚨 Worst 5 Questions (What to fix first)")

if gen_df is None:
    st.info("Worst-5 requires generation eval CSV.")
else:
    tmp = merged.copy()

    # Priority: safety failures first, then low faithfulness
    tmp["safety_fail"] = (~tmp.get("safety_pass", True)).astype(int)
    tmp["faithfulness"] = tmp.get("faithfulness", 0.0).fillna(0.0)
    tmp["relevance"] = tmp.get("relevance", 0.0).fillna(0.0)
    tmp["completeness"] = tmp.get("completeness", 0.0).fillna(0.0)

    tmp = tmp.sort_values(by=["safety_fail", "faithfulness", "relevance", "completeness"], ascending=[False, True, True, True])

    cols_to_show = [c for c in [
        "section",
        "question",
        "passed_retrieval_check",
        "top_score",
        "faithfulness",
        "relevance",
        "completeness",
        "safety_pass",
        "answer_preview",
        "top_chunk_preview",
    ] if c in tmp.columns]

    st.dataframe(tmp[cols_to_show].head(5))

st.divider()

# -----------------------
# Raw tables (expandable)
# -----------------------
with st.expander("📄 Raw Retrieval Results"):
    st.dataframe(retrieval_df)

with st.expander("📄 Raw Generation Evaluation Results"):
    if gen_df is not None:
        st.dataframe(gen_df)
    else:
        st.info("No generation CSV loaded.")
