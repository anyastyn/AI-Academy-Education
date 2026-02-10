-- Day 7 Document RAG tables for Supabase (Postgres + pgvector)
-- Safe to run multiple times (IF NOT EXISTS / CREATE OR REPLACE)

-- 1) Extensions
create extension if not exists pgcrypto;
create extension if not exists vector;  -- pgvector

-- 2) Ensure messages has embedding (your DB screenshot shows it, but your pasted SQL didn't)
-- If you already have it, this does nothing.
alter table public.messages
  add column if not exists embedding vector(1536);

-- 3) Shared knowledge documents
create table if not exists public.knowledge_documents (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  source text not null,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

-- 4) Chunks with embeddings
create table if not exists public.knowledge_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.knowledge_documents(id) on delete cascade,
  chunk_index int not null,
  content text not null,
  embedding vector(1536),
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists idx_knowledge_chunks_doc_chunk
  on public.knowledge_chunks (document_id, chunk_index);

-- Optional: vector index (recommended once you have enough chunks)
-- Choose ivfflat lists by dataset size (example 100)
create index if not exists idx_knowledge_chunks_embedding
  on public.knowledge_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- 5) Vector search RPC for docs
create or replace function public.search_knowledge_chunks (
  query_embedding vector(1536),
  match_count int default 5
)
returns table (
  id uuid,
  document_id uuid,
  chunk_index int,
  content text,
  score float
)
language sql stable
as $$
  select
    kc.id,
    kc.document_id,
    kc.chunk_index,
    kc.content,
    1 - (kc.embedding <=> query_embedding) as score
  from public.knowledge_chunks kc
  where kc.embedding is not null
  order by kc.embedding <=> query_embedding
  limit match_count;
$$;
