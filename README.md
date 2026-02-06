# AI-Academy-Education
# AI Academy – Power Automate Helper Agent

## Project Overview
This project was created as part of **AI Academy 2026 (Days 1–5)** and demonstrates the design of an **AI agent** that helps analyze and optimize **Microsoft Power Automate flows**.  
The agent is **advisory-only**: it reviews user-provided flow definitions and recommends improvements but does not execute changes.

The project focuses on:
- agent design patterns (RAG, Tool Use)
- governance and safety
- memory and search using Supabase
- clear separation between AI recommendations and human decisions

---

## Use Case
Power Automate flows often become inefficient or unreliable due to missing trigger filters, large loops, connector throttling, or missing error handling.  
The **Power Automate Helper Agent** analyzes flow JSON exports or descriptions and:
- explains what the flow does
- identifies problems and why they matter
- recommends concrete fixes using Power Automate settings and best practices

The agent supports learning, review, and optimization without modifying production systems.

---

## Agent Design Patterns
This agent uses a **combination of patterns** taught in AI Academy Day 5:

- **RAG (Retrieval Augmented Generation)**  
  The agent retrieves relevant past analyses and stored knowledge from Supabase (full-text and vector search) before generating recommendations.

- **Tool Use**  
  The agent interacts with external tools (Supabase database functions and memory storage).

The agent does **not** use Planning/Orchestration, as it does not coordinate multiple agents or execute multi-step workflows.

---

## Architecture (High Level)

User  
→ Agent (ChatGPT Project)  
→ Memory & Search (Supabase PostgreSQL)  
→ Response (analysis + recommendations)

**Components:**
- ChatGPT Project (agent prompt and prototype)
- Supabase PostgreSQL:
  - `messages` – conversation history and flow summaries
  - `user_facts` – extracted insights and preferences
  - `sessions` – session tracking
- Search:
  - Full-text search for keywords
  - Vector search (pgvector, dummy embeddings for learning)

---

## Memory and Search
- Agent conversations and summaries are stored in Supabase.
- Full-text search is used for exact terms (e.g. “Apply to each”, “trigger condition”).
- Vector search is implemented using `pgvector`.
- **Dummy embeddings** are used to validate architecture without external dependencies.
- The system is designed so real embeddings (Azure/OpenAI) can be added later without schema changes.

---

## Governance and Safety
Governance was designed first and then mapped to architecture, following AI Academy principles.

Key governance rules:
- Advisory-only agent (no execution)
- Clear trust boundaries (authoritative vs advisory data)
- Mandatory human review
- Explicit prohibited actions
- Failure handling and safe degradation
- Kill switch and ownership

Full governance details are documented here:
- [`docs/03-governance.md`](docs/03-governance.md)

---

## Documentation
Detailed documentation is available in the `docs/` folder:

- [`01-use-case.md`](docs/01-use-case.md) – Use case and value
- [`02-architecture.md`](docs/02-architecture.md) – Architecture and patterns
- [`03-governance.md`](docs/03-governance.md) – Governance and KAF mapping
- [`04-agent-prompt.md`](docs/04-agent-prompt.md) – Agent system instructions (prompt)

---

## Prototype Status
This project includes:
- A working **agent prototype** in a ChatGPT Project
- Supabase schema, search functions, and memory
- Local scripts demonstrating memory storage and retrieval

Execution of Power Automate changes is intentionally **out of scope** and left to humans.

---

## Security Notes
- Secrets are stored in `.env` files and are **not committed** to GitHub.
- Supabase keys were rotated after accidental exposure (learning outcome).
- `.venv` is excluded from version control by design.

---

## Limitations and Future Improvements
- Dummy embeddings are used instead of real semantic embeddings.
- No direct execution of Power Automate actions.
- Future improvements could include:
  - Azure OpenAI embeddings
  - confidence scoring
  - ReAct-style multi-step reasoning
  - approval workflows

---

## Key Principle
**AI suggests — humans decide.**

This project demonstrates responsible agent design aligned with AI Academy governance and KAF principles.

