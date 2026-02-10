-- Supabase (PostgreSQL) schema for an AI agent with memory
-- Tables: sessions, messages, user_facts
-- Requirements met:
-- - UUID for all IDs
-- - user_id references auth.users(id)
-- - timestamptz timestamps
-- - indexes for common queries
-- - jsonb metadata where it makes sense

-- 0) Extensions (for gen_random_uuid())
create extension if not exists pgcrypto;

-- 1) Sessions: session management
create table if not exists public.sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

comment on table public.sessions is 'Conversation sessions per user.';
comment on column public.sessions.metadata is 'Optional session metadata (agent version, channel, settings, etc.).';

-- Common query: list a user's sessions by recency
create index if not exists idx_sessions_user_started_at
  on public.sessions (user_id, started_at desc);

-- Optional: quickly find active sessions (ended_at is null)
create index if not exists idx_sessions_user_active
  on public.sessions (user_id)
  where ended_at is null;

-- 2) Messages: conversation history
create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  session_id uuid references public.sessions(id) on delete set null,
  role text not null check (role in ('user', 'assistant', 'system', 'tool')),
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

comment on table public.messages is 'Conversation message history for an agent.';
comment on column public.messages.role is 'Message role: user | assistant | system | tool.';
comment on column public.messages.metadata is 'Optional per-message metadata (tokens, model, tool name, attachments, etc.).';

-- Common queries:
-- - Fetch messages in a session ordered by time
create index if not exists idx_messages_session_created_at
  on public.messages (session_id, created_at);

-- - Fetch a user's recent messages
create index if not exists idx_messages_user_created_at
  on public.messages (user_id, created_at desc);

-- 3) User facts: structured memory about the user
create table if not exists public.user_facts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  fact_type text not null,
  fact_value jsonb not null,
  confidence numeric not null default 0.5 check (confidence >= 0 and confidence <= 1),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.user_facts is 'Facts (memory) about a user for personalization and recall.';
comment on column public.user_facts.fact_type is 'Category/key of the fact (e.g., preferred_language, role, timezone).';
comment on column public.user_facts.fact_value is 'Value of the fact stored as JSONB (string/number/object).';
comment on column public.user_facts.confidence is '0..1 confidence score of the fact.';

-- Enforce one fact per (user_id, fact_type) so you can UPSERT by type.
create unique index if not exists uq_user_facts_user_type
  on public.user_facts (user_id, fact_type);

-- Common query: fetch a user's most confident facts
create index if not exists idx_user_facts_user_confidence
  on public.user_facts (user_id, confidence desc);

-- Optional: enable searching inside JSON fact_value if you need it
create index if not exists idx_user_facts_fact_value_gin
  on public.user_facts using gin (fact_value jsonb_path_ops);

-- 4) Updated_at trigger for user_facts
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_user_facts_set_updated_at on public.user_facts;

create trigger trg_user_facts_set_updated_at
before update on public.user_facts
for each row
execute function public.set_updated_at();

-- (Optional) Helpful FK index
create index if not exists idx_messages_user_session
  on public.messages (user_id, session_id);

-- Done.
-- Checkpoint: In Supabase Table Editor you should see:
-- - sessions
-- - messages
-- - user_facts
