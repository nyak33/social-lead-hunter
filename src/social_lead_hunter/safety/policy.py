from __future__ import annotations

from datetime import datetime, timedelta, timezone

from social_lead_hunter.config import AppConfig
from social_lead_hunter.models import SafetyDecision


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def can_publish(config: AppConfig, storage, username: str, now: datetime | None = None) -> SafetyDecision:
    current = _utc(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if config.runtime.dry_run:
        return SafetyDecision(False, "dry-run mode blocks live publishing")

    start_day = current.replace(hour=0, minute=0, second=0, microsecond=0)
    replies_today = storage.replies_since(start_day)
    if len(replies_today) >= config.runtime.max_replies_per_day:
        return SafetyDecision(False, "daily reply limit reached")

    if replies_today:
        latest = max(_utc(x).astimezone(timezone.utc) for x in replies_today)
        gap = timedelta(minutes=config.runtime.min_reply_gap_minutes)
        if current - latest < gap:
            return SafetyDecision(False, "minimum reply gap has not elapsed")

    last_user = storage.last_reply_to_user(username)
    if last_user is not None:
        cooldown = timedelta(days=config.runtime.same_user_cooldown_days)
        if current - _utc(last_user).astimezone(timezone.utc) < cooldown:
            return SafetyDecision(False, "same-user cooldown is active")

    return SafetyDecision(True, "publishing allowed")
