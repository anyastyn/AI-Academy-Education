# Architecture – Power Automate Helper Agent (Week 1 + Day 7 RAG)

## Goal (simple)
An advisory agent that reviews Power Automate flows and suggests improvements.
It uses:
- Memory (Supabase messages)
- Document RAG (Day 7: retrieve from docs)
- LLM (OpenAI) to generate the final answer
- Governance guardrails (no secrets, no bypass, humans decide)

---

## Components
1) **User**
   - Pastes flow JSON export or description (+ optional screenshots/logs)

2) **Agent**
   - Runs Planning + ReAct reasoning flow
   - Calls tools:
     - Supabase search in messages (memory)
     - Supabase search in knowledge docs (document RAG)
     - LLM for final response

3) **Supabase**
   - `sessions`: groups a conversation
   - `messages`: saves user and assistant turns + embeddings
   - `user_facts`: saves small stable facts (optional)
   - `knowledge_documents` + `knowledge_chunks`: shared docs (Day 7 RAG)

4) **OpenAI**
   - Chat model: generates structured recommendations
   - Embedding model: creates embeddings for semantic search

---

## What gets saved to Supabase (and when)
### sessions
- Create at start of a chat run
- Update ended_at at end (optional)

### messages
- Save every user input and assistant output
- Attach session_id
- Save embeddings later (batch script) or immediately

### user_facts (optional learning)
- After assistant response:
  - extract 1–3 stable facts (preferences/common connectors)
  - upsert into user_facts

### knowledge_documents + knowledge_chunks (Day 7)
- Ingest docs once (chunk + embed + store)
- Reuse for all users (shared KB)

---

## Agent workflow (this is the “algorithm” reviewers want)

### 0) Safety input check
- Scan for secrets/tokens/passwords
- If found: stop, warn user, do NOT store raw text

### 1) Planning (Planning pattern)
Agent prints the plan (6 steps):
1) Inputs check
2) Trigger & filtering
3) Connectors & throttling
4) Loops & concurrency
5) Error handling & reliability
6) Governance + final recommendations + confidence

### 2) ReAct execution (ReAct pattern)
For each plan step:
- Parse: extract relevant fields from JSON/description
- Retrieve:
  - user memory from messages (search_user_messages)
  - doc chunks from knowledge base (search_knowledge_chunks)
- Reason: apply checks and create findings
- If key info missing or confidence < 70: ask up to 4 questions and STOP

### 3) Generation (LLM)
Send to the LLM:
- system prompt (rules + output format)
- retrieved context (memory + doc chunks)
- user input

LLM returns:
- Findings (what + why)
- Fixes (exact settings and examples)
- Questions (if needed)
- Confidence + human review checklist

### 4) Logging
Save:
- user input (or redacted placeholder)
- assistant answer
- metadata: confidence + retrieval info + secret flag

---

## Day 7 match
Day 7 RAG pipeline = load docs → chunk → embed → store → retrieve → generate. :contentReference[oaicite:3]{index=3}
We implement the same, but store vectors in Supabase instead of ChromaDB. :contentReference[oaicite:4]{index=4}

