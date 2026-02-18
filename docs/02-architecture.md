# Architecture — Power Automate Flow Reviewer & Governance Agent

## 1. Purpose

This agent is an advisory system used by a single customer tenant.

It:
- Reviews Power Automate flow JSON exports
- Identifies optimization issues (performance, reliability, maintainability)
- Checks governance compliance (connectors, DLP, environments, ARB)
- Provides clear, actionable recommendations
- Never executes changes

It is a bounded, monitored, retrieval-grounded AI system.

---

## 2. High-Level Architecture

User  
→ Agent Runtime  
→ RAG Retrieval (Supabase)  
→ LLM (OpenAI)  
→ Structured Advisory Response  
→ Logging (Supabase)

---

## 3. Components

### 3.1 User
- Provides flow JSON export, description, or governance question
- Operates inside one tenant context

### 3.2 Agent Runtime (Python)
Responsible for:
- Input validation
- Mode detection (Q&A vs Flow Review)
- Secret scanning
- Prompt injection detection
- Out-of-scope detection
- Retrieval confidence gating
- Logging and audit metadata

### 3.3 Supabase (Tenant Data Layer)

Tables:
- `sessions` — conversation grouping
- `messages` — all inputs/outputs + metadata
- `user_facts` — stable reusable preferences (optional)
- `knowledge_documents` — approved governance documents
- `knowledge_chunks` — embedded document chunks for retrieval

### 3.4 AI Core (OpenAI)

- Embedding model → creates vector embeddings
- Chat model → generates structured, grounded answers

LLM always receives:
- System rules (04-agent-prompt.md)
- Retrieved governance context
- User memory context
- User input

---

## 4. Runtime Safety Pipeline

1. Input classification
   - Detect JSON (flow review) vs simple governance question

2. Security scan
   - Secret detection (tokens/passwords)
   - Prompt injection detection
   - Document exfiltration attempts

3. Scope enforcement
   - Refuse non–Power Automate topics

4. Retrieval (RAG)
   - Vector search over tenant governance docs
   - Optional keyword boost
   - Top-K chunks returned

5. Confidence gate
   - If top retrieval score < threshold → abstain
   - Prevent hallucination

6. Response generation
   - Q&A mode → short grounded answer
   - Flow Review mode → structured optimization report

7. Logging
   - Store input, output
   - Store event_type (if triggered)
   - Store top_score + threshold
   - Store mode (Q&A or Flow Review)

---

## 5. Optimization Checklist (Flow Review Mode)

The agent evaluates flows across 5 categories:

1. Performance
   - Pagination
   - Unnecessary loops
   - Large arrays

2. Reliability
   - Scopes
   - Run-after handling
   - Retry configuration

3. Cost & Throttling
   - Connector limits
   - Concurrency
   - High-volume triggers

4. Maintainability
   - Naming
   - Modularity
   - Variable reuse

5. Governance
   - Approved connectors
   - ARB requirements
   - Environment usage rules

---

## 6. Monitoring & AgentOps

Post-deployment monitoring includes:

- Golden test set evaluation
- Retrieval pass rate
- Faithfulness / relevance scoring
- Safety event logging
- Latency tracking
- Document freshness checks

Release gate:
If golden test set fails threshold → do not release updated version.
