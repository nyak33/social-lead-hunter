from pathlib import Path


def test_supabase_migration_enables_rls_for_all_runtime_tables():
    sql = Path("migrations/supabase.sql").read_text(encoding="utf-8").lower()
    for table in ("social_lead_posts", "social_leads", "social_lead_replies"):
        assert f"alter table public.{table} enable row level security" in sql


def test_supabase_migration_grants_server_role_not_public_clients():
    sql = Path("migrations/supabase.sql").read_text(encoding="utf-8").lower()
    assert "grant select, insert, update, delete on public.social_lead_posts to service_role" in sql
    assert "grant select, insert, update, delete on public.social_leads to service_role" in sql
    assert "grant select, insert, update, delete on public.social_lead_replies to service_role" in sql
    assert "revoke all on public.social_lead_posts from anon, authenticated" in sql
    assert "revoke all on public.social_leads from anon, authenticated" in sql
    assert "revoke all on public.social_lead_replies from anon, authenticated" in sql
