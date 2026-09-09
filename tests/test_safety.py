from datetime import datetime, timezone

from social_lead_hunter.safety.policy import can_publish


class FakeStorage:
    def __init__(self):
        self.reply_times = []
        self.last_user_reply = None

    def replies_since(self, since):
        return [x for x in self.reply_times if x >= since]

    def last_reply_to_user(self, username):
        return self.last_user_reply


def test_dry_run_blocks_publish(app_config):
    now = datetime.now(timezone.utc)
    app_config.runtime.dry_run = True
    decision = can_publish(app_config, FakeStorage(), "buyer", now)
    assert decision.allowed is False
    assert "dry" in decision.reason.lower()


def test_daily_limit_blocks_publish(app_config):
    now = datetime.now(timezone.utc)
    app_config.runtime.dry_run = False
    storage = FakeStorage()
    storage.reply_times = [now] * app_config.runtime.max_replies_per_day
    assert can_publish(app_config, storage, "buyer", now).allowed is False


def test_same_user_cooldown_blocks_publish(app_config):
    now = datetime.now(timezone.utc)
    app_config.runtime.dry_run = False
    storage = FakeStorage()
    storage.last_user_reply = now
    assert can_publish(app_config, storage, "buyer", now).allowed is False
