-- ============================================================
-- Row Level Security (RLS) policies for Supabase
-- Tables: public.messages, public.user_facts, public.sessions
--
-- Rules:
-- 1) Users can only see/modify their OWN records
-- 2) user_id must equal auth.uid()
-- 3) INSERT must have user_id = auth.uid()
-- 4) Admin role can see everything
--
-- Notes:
-- - Supabase uses Postgres roles. Common roles:
--     * anon        (not logged in)
--     * authenticated (logged in)
--     * service_role (server/admin key; typically bypasses RLS)
-- - "Admin can see everything" is implemented here as:
--     a) service_role can do anything (typical Supabase admin/server)
--     b) OPTIONAL: support a custom JWT claim is_admin=true for authenticated users
--        (only if your Auth/JWT includes it). See the "OPTIONAL ADMIN" policies.
-- ============================================================

-- ----------------------------
-- 0) Enable RLS on all tables
-- ----------------------------

alter table public.sessions   enable row level security;
alter table public.messages   enable row level security;
alter table public.user_facts enable row level security;

comment on table public.sessions is 'RLS enabled: users can access only their own session rows.';
comment on table public.messages is 'RLS enabled: users can access only their own message rows.';
comment on table public.user_facts is 'RLS enabled: users can access only their own user_facts rows.';

-- ---------------------------------------------------------
-- 1) Helper: define "admin" condition (OPTIONAL)
-- ---------------------------------------------------------
-- If you want "admin users" (not just service_role) to see everything,
-- you need a reliable marker in JWT claims (e.g., is_admin = true).
--
-- Supabase JWT claims can be accessed via:
--   auth.jwt() -> returns JSON
-- Example:
--   (auth.jwt() ->> 'is_admin')::boolean = true
--
-- If you do NOT use custom JWT claims, ignore the OPTIONAL admin policies below.
-- service_role will still be able to do everything (typical admin path).

-- ---------------------------------------------------------
-- 2) SESSIONS policies
-- ---------------------------------------------------------

-- Clean up old policies if re-running (optional safety)
drop policy if exists "sessions_select_own" on public.sessions;
drop policy if exists "sessions_insert_own" on public.sessions;
drop policy if exists "sessions_update_own" on public.sessions;
drop policy if exists "sessions_delete_own" on public.sessions;

-- SELECT: Users can read only their own sessions
create policy "sessions_select_own"
on public.sessions
for select
to authenticated
using (
  user_id = auth.uid()
);
comment on policy "sessions_select_own" on public.sessions is
'Allows authenticated users to SELECT only sessions where sessions.user_id = auth.uid().';

-- INSERT: Users can create sessions only for themselves
create policy "sessions_insert_own"
on public.sessions
for insert
to authenticated
with check (
  user_id = auth.uid()
);
comment on policy "sessions_insert_own" on public.sessions is
'Allows authenticated users to INSERT sessions only if user_id equals auth.uid().';

-- UPDATE: Users can update only their own sessions,
-- and cannot change ownership (user_id must remain auth.uid()).
create policy "sessions_update_own"
on public.sessions
for update
to authenticated
using (
  user_id = auth.uid()
)
with check (
  user_id = auth.uid()
);
comment on policy "sessions_update_own" on public.sessions is
'Allows authenticated users to UPDATE only their own sessions; WITH CHECK prevents changing user_id away from auth.uid().';

-- DELETE: Users can delete only their own sessions
create policy "sessions_delete_own"
on public.sessions
for delete
to authenticated
using (
  user_id = auth.uid()
);
comment on policy "sessions_delete_own" on public.sessions is
'Allows authenticated users to DELETE only their own sessions.';

-- OPTIONAL ADMIN (custom claim): admins can read/modify all sessions
drop policy if exists "sessions_admin_all" on public.sessions;
create policy "sessions_admin_all"
on public.sessions
for all
to authenticated
using (
  coalesce((auth.jwt() ->> 'is_admin')::boolean, false) = true
)
with check (
  coalesce((auth.jwt() ->> 'is_admin')::boolean, false) = true
);
comment on policy "sessions_admin_all" on public.sessions is
'OPTIONAL: If JWT includes is_admin=true, allows admin users to SELECT/INSERT/UPDATE/DELETE any session row.';

-- ---------------------------------------------------------
-- 3) MESSAGES policies
-- ---------------------------------------------------------

drop policy if exists "messages_select_own" on public.messages;
drop policy if exists "messages_insert_own" on public.messages;
drop policy if exists "messages_update_own" on public.messages;
drop policy if exists "messages_delete_own" on public.messages;

-- SELECT: Users can read only their own messages
create policy "messages_select_own"
on public.messages
for select
to authenticated
using (
  user_id = auth.uid()
);
comment on policy "messages_select_own" on public.messages is
'Allows authenticated users to SELECT only messages where messages.user_id = auth.uid().';

-- INSERT: Users can create messages only for themselves
create policy "messages_insert_own"
on public.messages
for insert
to authenticated
with check (
  user_id = auth.uid()
);
comment on policy "messages_insert_own" on public.messages is
'Allows authenticated users to INSERT messages only if user_id equals auth.uid().';

-- UPDATE: Users can update only their own messages,
-- and cannot change ownership
create policy "messages_update_own"
on public.messages
for update
to authenticated
using (
  user_id = auth.uid()
)
with check (
  user_id = auth.uid()
);
comment on policy "messages_update_own" on public.messages is
'Allows authenticated users to UPDATE only their own messages; WITH CHECK prevents changing user_id away from auth.uid().';

-- DELETE: Users can delete only their own messages
create policy "messages_delete_own"
on public.messages
for delete
to authenticated
using (
  user_id = auth.uid()
);
comment on policy "messages_delete_own" on public.messages is
'Allows authenticated users to DELETE only their own messages.';

-- OPTIONAL ADMIN (custom claim): admins can read/modify all messages
drop policy if exists "messages_admin_all" on public.messages;
create policy "messages_admin_all"
on public.messages
for all
to authenticated
using (
  coalesce((auth.jwt() ->> 'is_admin')::boolean, false) = true
)
with check (
  coalesce((auth.jwt() ->> 'is_admin')::boolean, false) = true
);
comment on policy "messages_admin_all" on public.messages is
'OPTIONAL: If JWT includes is_admin=true, allows admin users to SELECT/INSERT/UPDATE/DELETE any message row.';

-- ---------------------------------------------------------
-- 4) USER_FACTS policies
-- ---------------------------------------------------------

drop policy if exists "user_facts_select_own" on public.user_facts;
drop policy if exists "user_facts_insert_own" on public.user_facts;
drop policy if exists "user_facts_update_own" on public.user_facts;
drop policy if exists "user_facts_delete_own" on public.user_facts;

-- SELECT: Users can read only their own facts
create policy "user_facts_select_own"
on public.user_facts
for select
to authenticated
using (
  user_id = auth.uid()
);
comment on policy "user_facts_select_own" on public.user_facts is
'Allows authenticated users to SELECT only facts where user_facts.user_id = auth.uid().';

-- INSERT: Users can create facts only for themselves
create policy "user_facts_insert_own"
on public.user_facts
for insert
to authenticated
with check (
  user_id = auth.uid()
);
comment on policy "user_facts_insert_own" on public.user_facts is
'Allows authenticated users to INSERT facts only if user_id equals auth.uid().';

-- UPDATE: Users can update only their own facts,
-- and cannot change ownership
create policy "user_facts_update_own"
on public.user_facts
for update
to authenticated
using (
  user_id = auth.uid()
)
with check (
  user_id = auth.uid()
);
comment on policy "user_facts_update_own" on public.user_facts is
'Allows authenticated users to UPDATE only their own facts; WITH CHECK prevents changing user_id away from auth.uid().';

-- DELETE: Users can delete only their own facts
create policy "user_facts_delete_own"
on public.user_facts
for delete
to authenticated
using (
  user_id = auth.uid()
);
comment on policy "user_facts_delete_own" on public.user_facts is
'Allows authenticated users to DELETE only their own facts.';

-- OPTIONAL ADMIN (custom claim): admins can read/modify all facts
drop policy if exists "user_facts_admin_all" on public.user_facts;
create policy "user_facts_admin_all"
on public.user_facts
for all
to authenticated
using (
  coalesce((auth.jwt() ->> 'is_admin')::boolean, false) = true
)
with check (
  coalesce((auth.jwt() ->> 'is_admin')::boolean, false) = true
);
comment on policy "user_facts_admin_all" on public.user_facts is
'OPTIONAL: If JWT includes is_admin=true, allows admin users to SELECT/INSERT/UPDATE/DELETE any user_facts row.';

-- ============================================================
-- Important:
-- - If you do not plan to use custom JWT admin claims, you can
--   delete the OPTIONAL *_admin_all policies.
-- - The Supabase service_role key (server-side only) can still
--   access everything (and typically bypasses RLS), which is the
--   standard way to implement admin/back-office operations.
-- ============================================================
