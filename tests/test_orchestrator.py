from datetime import datetime, timezone

from social_lead_hunter.models import CapabilityResult, SocialPost
from social_lead_hunter.orchestrator import run_cycle


class FakeAdapter:
    def __init__(self, posts=None, reply_ok=True):
        self.posts = posts or []
        self.publish_calls = []
        self.reply_ok = reply_ok
        self.own_username = "owner"

    def search_recent(self, query, limit=50, since=None):
        return list(self.posts)

    def validate_reply_capability(self):
        return CapabilityResult("reply", self.reply_ok, "ok" if self.reply_ok else "missing scope")

    def publish_reply(self, post_id, text):
        self.publish_calls.append((post_id, text))
        return "reply-1"


class FakeStorage:
    def __init__(self):
        self.posts = set()
        self.candidates = {}
        self.replies = []

    def has_post(self, platform, external_id):
        return (platform, external_id) in self.posts

    def save_raw_post(self, platform, external_id, username, text, permalink, timestamp):
        self.posts.add((platform, external_id))

    def save_candidate(self, post, result, draft_reply, status):
        self.candidates[(post.platform, post.external_id)] = (result, draft_reply, status)

    def mark_replied(self, platform, external_id, reply_id):
        self.replies.append((platform, external_id, reply_id))

    def replies_since(self, since):
        return []

    def last_reply_to_user(self, username):
        return None


def high_intent_post(pid="p1"):
    return SocialPost(
        platform="threads",
        external_id=pid,
        username="buyer",
        text="Looking for custom labels in Malaysia, need quotation urgently qty 1000",
        permalink="x",
        timestamp=datetime.now(timezone.utc),
    )


def test_dry_run_never_calls_publish(app_config):
    app_config.runtime.dry_run = True
    adapter = FakeAdapter([high_intent_post()])
    storage = FakeStorage()
    summary = run_cycle(app_config, adapter, storage)
    assert summary.qualified >= 1
    assert summary.drafted >= 1
    assert adapter.publish_calls == []


def test_duplicate_is_skipped(app_config):
    adapter = FakeAdapter([high_intent_post()])
    storage = FakeStorage()
    storage.posts.add(("threads", "p1"))
    summary = run_cycle(app_config, adapter, storage)
    assert summary.duplicates == 1
    assert summary.new_posts == 0


def test_live_mode_refuses_without_reply_capability(app_config):
    app_config.runtime.dry_run = False
    adapter = FakeAdapter([high_intent_post()], reply_ok=False)
    storage = FakeStorage()
    summary = run_cycle(app_config, adapter, storage)
    assert adapter.publish_calls == []
    assert summary.failed == 1


def test_orchestrator_uses_adapter_identity_for_self_exclusion(app_config):
    class IdentityAdapter(FakeAdapter):
        def __init__(self, posts):
            super().__init__(posts)
            self.own_username = None

        def validate_identity(self):
            self.own_username = "owner"
            return CapabilityResult("identity", True, "ok")

    post = high_intent_post("self1")
    post.username = "owner"
    adapter = IdentityAdapter([post])
    storage = FakeStorage()
    summary = run_cycle(app_config, adapter, storage)
    assert summary.rejected == 1
    assert summary.qualified == 0
