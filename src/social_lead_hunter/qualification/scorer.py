from __future__ import annotations

from datetime import datetime, timezone

from social_lead_hunter.config import AppConfig
from social_lead_hunter.models import QualificationResult, SocialPost

_DIRECT_INTENT = (
    "looking for", "need", "cari", "recommend", "recommendation", "supplier",
    "quotation", "quote", "siapa boleh", "anyone can", "urgent",
)
_SPECIFICITY = ("quantity", "qty", "moq", "size", "budget", "deadline", "urgent", "price")
_PROMOTION = ("we provide", "kami menyediakan", "our service", "dm us", "contact us for")
_RECRUITMENT = ("job vacancy", "hiring", "vacancy", "kerja kosong", "recruiting")
_SPAM = ("giveaway", "free money", "airdrop", "click link", "win prize")


def _contains_any(text: str, terms: tuple[str, ...] | list[str]) -> str | None:
    for term in terms:
        if term.lower() in text:
            return term
    return None


def qualify_post(post: SocialPost, config: AppConfig, own_username: str | None = None) -> QualificationResult:
    text = post.text.lower()
    reasons: list[str] = []

    if own_username and post.username.lower() == own_username.lower():
        return QualificationResult(0, False, True, ["own account"], intent="self")

    negative = _contains_any(text, [x.lower() for x in config.search.negative_keywords])
    if negative:
        return QualificationResult(0, False, True, [f"negative keyword: {negative}"], intent="excluded")

    recruitment = _contains_any(text, _RECRUITMENT)
    if recruitment:
        return QualificationResult(0, False, True, [f"recruitment signal: {recruitment}"], intent="excluded")

    spam = _contains_any(text, _SPAM)
    if spam:
        return QualificationResult(0, False, True, [f"spam signal: {spam}"], intent="excluded")

    score = 0
    intent = "discussion"

    direct = _contains_any(text, _DIRECT_INTENT)
    if direct:
        score += 35
        reasons.append(f"direct request signal: {direct}")
        intent = "buying"

    service_detected = _contains_any(text, [x.lower() for x in config.business.services])
    if service_detected:
        score += 25
        reasons.append(f"service match: {service_detected}")

    specific = _contains_any(text, _SPECIFICITY)
    if specific:
        score += 15
        reasons.append(f"requirement detail: {specific}")

    location_detected = _contains_any(text, [x.lower() for x in config.search.target_locations])
    if config.search.target_locations and location_detected:
        score += 10
        reasons.append(f"location match: {location_detected}")

    now = datetime.now(timezone.utc)
    ts = post.timestamp if post.timestamp.tzinfo else post.timestamp.replace(tzinfo=timezone.utc)
    age_hours = max(0.0, (now - ts.astimezone(timezone.utc)).total_seconds() / 3600)
    if age_hours <= 6:
        score += 10
        reasons.append("very recent post")
    elif age_hours <= 24:
        score += 5
        reasons.append("recent post")

    promotion = _contains_any(text, _PROMOTION)
    if promotion:
        score -= 40
        reasons.append(f"seller promotion signal: {promotion}")

    score = max(0, min(100, score))
    excluded = promotion is not None and score < config.search.min_score
    qualified = not excluded and score >= config.search.min_score
    return QualificationResult(
        score=score,
        qualified=qualified,
        excluded=excluded,
        reasons=reasons,
        intent=intent,
        location_detected=location_detected,
        service_detected=service_detected,
    )
