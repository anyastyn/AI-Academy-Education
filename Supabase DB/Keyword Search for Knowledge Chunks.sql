create or replace function public.search_knowledge_chunks_keyword(
  keyword text,
  match_count int default 10
)
returns table (
  id uuid,
  document_id uuid,
  chunk_index int,
  content text
)
language sql stable
as $$
  select
    kc.id,
    kc.document_id,
    kc.chunk_index,
    kc.content
  from public.knowledge_chunks kc
  where kc.content ilike ('%' || keyword || '%')
  order by kc.created_at desc
  limit match_count;
$$;
