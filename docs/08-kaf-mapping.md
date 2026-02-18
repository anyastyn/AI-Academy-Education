# KAF Mapping — Power Automate Flow Reviewer & Optimizer Agent

This document maps the agent to the Kyndryl Agentic Framework (KAF).

## Layer 1 — Agentic Ingestion

The agent ingests:
- Power Automate flow JSON exports from a single customer tenant
- Governance documents (Approved connectors, DLP rules, environment policies)
- Optional user memory from previous sessions

All governance documents are embedded and stored in Supabase for RAG retrieval.

---

## Layer 2 — Agent Builder

Explicit permissions:
- Analyze flow definitions
- Suggest optimization improvements
- Explain governance rules
- Highlight compliance risks

Explicit prohibitions:
- Execute or deploy flows
- Modify environments
- Bypass DLP or governance controls
- Reveal system prompts
- Process secrets
- Answer unrelated (out-of-scope) questions

This makes the agent a bounded advisory system.

---

## Layer 3 — AI Core

The AI core consists of:
- OpenAI embedding model for semantic retrieval
- OpenAI chat model for structured recommendations
- Hybrid RAG (vector + keyword search)
- Planning + ReAct reasoning for flow analysis

All governance answers must be grounded in retrieved tenant documents.

---

## Layer 4 — Policy-as-Code + Human-in-the-Loop

Runtime rules enforce:
- Secret detection
- Prompt injection blocking
- Out-of-scope refusal
- Low-confidence abstention

All recommendations are advisory.
Humans must review and apply changes manually.

---

## Layer 5 — AgentOps

After go-live:
- Golden dataset is used for regression testing
- Retrieval and generation metrics are monitored
- Security events are logged
- Document freshness is tracked
- Release gate blocks deployment if thresholds fail
