from __future__ import annotations

from datetime import datetime, timedelta, timezone

from social_lead_hunter.config import AppConfig
from social_lead_hunter.models import RunSummary
from social_lead_hunter.qualification.scorer import qualify_post
from social_lead_hunter.replies.generator import generate_reply
from social_lead_hunter.safety.policy import can_publish


def run_cycle(config: AppConfig, adapter, storage, llm=None) -> RunSummary:
    summary = RunSummary()
    since = datetime.now(timezone.utc) - timedelta(hours=config.search.freshness_hours)
    reply_capability = None
    identity_result = None
    if hasattr(adapter, "validate_identity"):
        identity_result = adapter.validate_identity()
        if not identity_result.ok and not config.runtime.dry_run:
            summary.failed += 1
            return summary
    own_username = getattr(adapter, "own_username", None)
    seen_this_cycle: set[tuple[str, str]] = set()

    for keyword in config.search.keywords:
        posts = adapter.search_recent(keyword, limit=50, since=since)
        for post in posts:
            summary.scanned += 1
            key = (post.platform, post.external_id)
            if key in seen_this_cycle:
                continue
            seen_this_cycle.add(key)
            if storage.has_post(post.platform, post.external_id):
                summary.duplicates += 1
                continue

            storage.save_raw_post(post.platform, post.external_id, post.username, post.text, post.permalink, post.timestamp)
            summary.new_posts += 1
            result = qualify_post(post, config, own_username=own_username)
            if not result.qualified:
                storage.save_candidate(post, result, None, "rejected")
                summary.rejected += 1
                continue

            summary.qualified += 1
            draft = generate_reply(post, result, config, llm=llm)
            storage.save_candidate(post, result, draft, "drafted")
            summary.drafted += 1

            if config.runtime.dry_run:
                continue

            if reply_capability is None:
                reply_capability = adapter.validate_reply_capability()
            if not reply_capability.ok:
                storage.save_candidate(post, result, draft, "failed")
                summary.failed += 1
                continue

            decision = can_publish(config, storage, post.username)
            if not decision.allowed:
                storage.save_candidate(post, result, draft, "blocked")
                continue

            try:
                reply_id = adapter.publish_reply(post.external_id, draft)
                storage.mark_replied(post.platform, post.external_id, reply_id)
                summary.replied += 1
            except Exception:
                storage.save_candidate(post, result, draft, "failed")
                summary.failed += 1

    return summary
