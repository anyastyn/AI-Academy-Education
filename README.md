# AI Academy – Power Automate Flow Reviewer & Optimizer Agent

## Project Overview

This project demonstrates a **bounded, enterprise-ready AI agent** that reviews and optimizes Microsoft Power Automate flows for a single customer tenant.

The agent is advisory-only:
- It analyzes flow JSON exports.
- It checks governance compliance.
- It recommends performance and reliability improvements.
- It never executes changes.
- Humans remain responsible for final decisions.

The design follows Kyndryl Agentic Framework (KAF) principles, includes Policy-as-Code runtime controls, and implements measurable quality and security monitoring.

---

## What the Agent Does

The agent supports three main use cases:

### 1. Flow Review & Optimization
- Explains what a flow does
- Detects performance issues (loops, pagination, concurrency)
- Identifies reliability gaps (run-after, retries, scopes)
- Suggests concrete, step-by-step improvements

### 2. Governance & Compliance Check
- Checks whether connectors are allowed
- Identifies ARB requirements
- Explains DLP and environment rules
- Grounds answers in tenant governance documents (RAG)

### 3. Safe Advisory Behavior
- Refuses prompt injection attempts
- Detects and blocks secret exposure
- Abstains on low-confidence retrieval
- Logs all safety events for audit

---

## Architecture Overview

User  
→ Python Runtime Agent  
→ RAG Retrieval (Supabase)  
→ OpenAI (LLM + embeddings)  
→ Structured Advisory Output  
→ Logging & Monitoring (Supabase + Dashboard)

---

## Core Components

### 1. Python Runtime (`Scripts/run_agent_memory_demo.py`)
- Mode detection (Q&A vs Flow Review)
- Secret scanning
- Prompt injection detection
- Out-of-scope protection
- Hybrid RAG retrieval
- Confidence gating
- Structured logging

### 2. Supabase (Tenant Data Layer)
Tables:
- `sessions`
- `messages`
- `user_facts`
- `knowledge_documents`
- `knowledge_chunks`

Supports:
- Memory retrieval
- Document RAG
- Audit logging
- Event metadata

### 3. RAG Knowledge Base
- Approved Connectors
- Governance rules
- DLP guidance
- Tenant-specific documentation

Ingested via:
- `Scripts/02_ingest_rag_data_to_supabase.py`

---

## Design Patterns Used

- Retrieval Augmented Generation (RAG)
- Tool Use (Supabase RPC)
- Planning + ReAct (for structured flow review)
- Policy-as-Code enforcement
- Human-in-the-Loop control

---

## Policy-as-Code (Runtime Guardrails)

The agent enforces runtime rules:

- Secret detection → refuse + redact + log
- Prompt injection detection → refuse + log
- Out-of-scope queries → refuse + log
- Low-confidence retrieval → abstain + log

All safety events are stored in `messages.metadata` for audit.

---

## Monitoring & Quality Control (AgentOps)

The system includes:

- Golden dataset (`docs/day8_golden_questions.md`)
- Retrieval testing (`Scripts/03_rag_quality_test.py`)
- Automated generation grading (`Scripts/04_generation_evaluation.py`)
- KPI dashboard (`Scripts/dashboard.py`)
- Release gating based on quality thresholds

Tracked metrics include:
- Retrieval pass rate
- Faithfulness / relevance scores
- Safety event rate
- Latency

---

## Governance Alignment

This project aligns with:

- Kyndryl Agentic Framework (KAF)
- Policy-as-Code runtime controls
- Human-in-the-Loop review
- EU AI Act Limited Risk transparency requirements
- OWASP Top 10 for LLM Applications (prompt injection, sensitive info disclosure, KB poisoning)

Documentation:
- `docs/02-architecture.md`
- `docs/03-governance.md`
- `docs/07-policy-as-code.md`
- `docs/08-kaf-mapping.md`
- `docs/09-ai-literacy-plan.md`
- `docs/10-eu-ai-act-classification.md`

---

## Security & Compliance

- Secrets are never stored.
- `.env` is excluded from version control.
- Supabase keys are rotated when needed.
- All risky interactions are logged.
- No production execution is allowed.

---

## Key Principle

**AI suggests — humans decide.**

This project demonstrates responsible enterprise AI agent design with measurable safety, governance, and monitoring controls.
