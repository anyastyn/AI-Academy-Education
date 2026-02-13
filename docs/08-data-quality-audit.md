# Data Quality Audit — RAG Pipeline
# Author: Anna Styn
# Role: AI-DS
# Date: 2026-02-XX

## 1. Overview

This audit evaluates the RAG pipeline used in the Power Automate Helper Agent.
The system uses:

- User memory (Supabase messages)
- Document RAG (files from "RAG Data" folder)
- OpenAI embeddings + GPT model

The objective is to determine whether the system can be trusted in production.

---

# 2. 5 Dimensions of Data Quality

| Dimension | Rating | Evidence | Risk Level |
|------------|--------|----------|------------|
| Completeness | ⚠ | Only governance and connector documents ingested. No DLP error guide, no environment lifecycle document, no expense policy. | Medium |
| Accuracy | ✅ | Spot-checked 5 chunks (e.g., SharePoint row) against original Excel. Correct extraction and chunking. | Low |
| Freshness | ⚠ | No `last_modified` tracking for documents. No alert if documents outdated. | Medium |
| Relevance | ✅ | Hybrid retrieval returns correct chunks for connector-related queries (e.g., SharePoint). | Low |
| Consistency | ⚠ | No automated check for contradictory rules across documents. | Medium |

---

# 3. Retrieval Testing

## Test Queries

| Question | Expected Behavior | Result | Retrieval Correct? |
|------------|------------------|--------|-------------------|
| Are SharePoint connectors allowed? | Return SharePoint row | Correct row retrieved | ✅ |
| Is ARB required for GitHub? | Return GitHub ARB value | Correct | ✅ |
| What is expense reimbursement policy? | Say "not found" | Correctly said not found | ✅ |
| What is a connector? | Retrieve definition chunk | Correct | ✅ |

### Observation
Retrieval improved significantly after:
- Row-based Excel chunking
- Hybrid (vector + keyword) search

Precision@K visually estimated > 80%.

---

# 4. Answer Quality Evaluation

| Metric | Observation | Rating |
|--------|------------|--------|
| Faithfulness | Answers align with retrieved chunk content | ✅ |
| Hallucination | System says "I cannot find this..." when appropriate | ✅ |
| Overconfidence | Confidence score shown; sometimes conservative | ⚠ |
| Clarity | Q&A mode now concise and readable | ✅ |

---

# 5. 5 Automated Checks (Daily)

1. **Completeness Check**
   - Maintain expected topic list.
   - Alert if topic missing from knowledge base.

2. **Freshness Check**
   - Add `last_modified` column.
   - Alert if document older than 90 days.

3. **Retrieval Precision Check**
   - Run 5 fixed test queries.
   - Confirm expected keyword appears in top 5 chunks.

4. **Hallucination Check**
   - Ask a known out-of-scope question.
   - Ensure system says "I cannot find this in the available documents."

5. **Duplicate Detection**
   - Check for duplicate `source` values in `knowledge_documents`.

---

# 6. KPI Dashboard (Minimal Production View)

## Retrieval Quality
- Precision@5 > 80%
- Recall@5 > 70%

## Answer Quality
- Faithfulness > 90%
- Hallucination rate < 5%

## Operational
- Latency < 5 sec
- Cost per query < $0.05

## Business
- Deflection rate > 60%
- CSAT > 4/5

---

# 7. Security Risk Assessment

| Risk | Status | Mitigation |
|------|--------|------------|
| PII Leakage | Controlled | Secret detection implemented |
| Data Poisoning | ⚠ | No approval workflow before ingestion |
| Access Control | ⚠ | Shared KB for all users |
| Audit Trail | Partial | Sessions + messages logged |
| Data Exfiltration | ⚠ | No rate limiting |

---

# 8. Key Insight

Most RAG failures are data failures, not model failures.
The system is technically correct, but completeness and freshness are the main production risks.

---

# 9. Next Improvements

1. Add document lifecycle tracking (`last_modified`).
2. Add ingestion approval workflow.
3. Implement automated Precision@K test script.
4. Add monitoring for retrieval drift.
