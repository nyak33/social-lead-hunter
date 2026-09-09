from __future__ import annotations

from social_lead_hunter.config import AppConfig
from social_lead_hunter.models import QualificationResult, SocialPost


def _fallback(post: SocialPost, result: QualificationResult, config: AppConfig) -> str:
    service = result.service_detected or (config.business.services[0] if config.business.services else "this request")
    text = post.text.lower()
    missing = []
    if not any(token in text for token in ("qty", "quantity", "moq", "pcs", "pieces")):
        missing.append("quantity")
    if "size" not in text and "mm" not in text and "cm" not in text:
        missing.append("size/spec")
    if not any(token in text for token in ("deadline", "urgent", "when", "date")):
        missing.append("deadline")

    if missing:
        detail = ", ".join(missing[:3])
        reply = f"For {service}, the useful details to check first are {detail}. If you share those, it’s easier to assess properly."
    else:
        reply = f"For {service}, those details are enough for an initial check. The next useful step is to confirm the exact requirement before quoting."

    if config.business.cta:
        reply = f"{reply} {config.business.cta}"
    return reply[:500]


def generate_reply(post: SocialPost, result: QualificationResult, config: AppConfig, llm=None) -> str:
    fallback = _fallback(post, result, config)
    if llm is None:
        return fallback

    system = (
        "Write one short contextual reply to a public social post. Do not invent pricing, availability, location coverage, "
        "certifications, or capabilities. Avoid generic spam introductions. Return JSON only with keys reply, safe, reason."
    )
    user = (
        f"Business: {config.business.description}\n"
        f"Services: {', '.join(config.business.services)}\n"
        f"Style: {config.business.reply_style}\n"
        f"Optional CTA: {config.business.cta}\n"
        f"Post: {post.text}\n"
        f"Detected service: {result.service_detected or ''}\n"
        f"Qualification reasons: {'; '.join(result.reasons)}"
    )
    try:
        data = llm.complete_json(system, user)
        reply = str(data.get("reply") or "").strip()
        safe = data.get("safe") is True
        if safe and 0 < len(reply) <= 500:
            return reply
    except Exception:
        pass
    return fallback
