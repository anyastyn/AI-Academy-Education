# Architecture – Power Automate Helper Agent

## High-Level Architecture

User → Agent (ChatGPT Project)
        → Memory (Supabase PostgreSQL)
            - messages (conversation + flow exports)
            - user_facts (learned preferences / lessons)
        → Search
            - Full-text search (keywords)
            - Vector search (pgvector, dummy embeddings)
        → Response to user

## Components
- **Agent (LLM)**: Interprets flow JSON and produces analysis and recommendations.
- **Memory Database (Supabase)**: Stores conversations, flow summaries, and extracted insights.
- **Search Layer**:
  - Full-text search for exact terms (e.g., “trigger condition”, “Apply to each”).
  - Vector search for semantic similarity across past flows and recommendations.
- **External Knowledge**: Microsoft documentation and AI Academy materials (used as reference, not authoritative data).

## Pattern Used
- Tool-use + Retrieval-Augmented Generation (RAG)
- Human-in-the-loop for all execution decisions
