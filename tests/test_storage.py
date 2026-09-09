from datetime import datetime, timezone

from social_lead_hunter.storage.sqlite import SQLiteStorage


def test_post_dedupe(tmp_path):
    db = SQLiteStorage(str(tmp_path / "lead.db"))
    db.save_raw_post("threads", "abc", "user", "text", "url", datetime.now(timezone.utc))
    assert db.has_post("threads", "abc") is True
    assert db.has_post("threads", "different") is False


def test_same_platform_id_is_unique(tmp_path):
    db = SQLiteStorage(str(tmp_path / "lead.db"))
    now = datetime.now(timezone.utc)
    db.save_raw_post("threads", "abc", "u", "x", "url", now)
    db.save_raw_post("threads", "abc", "u", "x", "url", now)
    assert db.count_posts() == 1


def test_supabase_mark_replied_carries_username(monkeypatch):
    from social_lead_hunter.storage.supabase import SupabaseStorage

    calls = []

    class Response:
        status_code = 200
        def __init__(self, payload=None):
            self.payload = payload if payload is not None else []
        def raise_for_status(self):
            return None
        def json(self):
            return self.payload

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if method == "GET" and url.endswith("/social_leads"):
            return Response([{"username": "buyer"}])
        return Response([])

    monkeypatch.setattr("requests.request", fake_request)
    db = SupabaseStorage(url="https://example.invalid", key="secret")
    db.mark_replied("threads", "abc", "reply1")
    reply_posts = [c for c in calls if c[0] == "POST" and c[1].endswith("/social_lead_replies")]
    assert reply_posts
    assert reply_posts[0][2]["json"]["username"] == "buyer"


def test_supabase_upsert_merges_prefer_header(monkeypatch):
    from social_lead_hunter.models import QualificationResult, SocialPost
    from social_lead_hunter.storage.supabase import SupabaseStorage

    calls = []

    class Response:
        def raise_for_status(self):
            return None
        def json(self):
            return []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return Response()

    monkeypatch.setattr("requests.request", fake_request)
    db = SupabaseStorage(url="https://example.invalid", key="secret")
    now = datetime.now(timezone.utc)
    db.save_raw_post("threads", "abc", "buyer", "text", "url", now)
    post = SocialPost("threads", "abc", "buyer", "text", "url", now)
    result = QualificationResult(90, True, False, ["test"])
    db.save_candidate(post, result, "draft", "drafted")

    assert calls[0][2]["headers"]["Prefer"] == "resolution=ignore-duplicates"
    assert calls[1][2]["headers"]["Prefer"] == "resolution=merge-duplicates"
    assert calls[0][2]["headers"]["Authorization"].startswith("Bearer ")
