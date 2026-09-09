from datetime import datetime, timezone

from social_lead_hunter.models import QualificationResult, SocialPost
from social_lead_hunter.replies.generator import generate_reply


def make_post():
    return SocialPost(
        platform="threads",
        external_id="p1",
        username="buyer",
        text="Looking for custom labels, need quotation urgently",
        permalink="x",
        timestamp=datetime.now(timezone.utc),
    )


def make_result():
    return QualificationResult(
        score=90,
        qualified=True,
        excluded=False,
        reasons=["direct request signal", "service match"],
        intent="buying",
        service_detected="custom labels",
    )


def test_fallback_reply_is_short_and_contextual(app_config):
    reply = generate_reply(make_post(), make_result(), app_config, llm=None)
    assert 1 <= len(reply.splitlines()) <= 3
    assert len(reply) <= 500
    assert "custom labels" in reply.lower()
    assert "Hi kami menyediakan" not in reply


def test_cta_is_not_added_when_blank(app_config):
    app_config.business.cta = ""
    reply = generate_reply(make_post(), make_result(), app_config, llm=None)
    assert "contact" not in reply.lower()


class UnsafeLLM:
    def complete_json(self, system, user):
        return {"reply": "Buy now", "safe": False, "reason": "unsafe"}


def test_unsafe_llm_output_falls_back(app_config):
    reply = generate_reply(make_post(), make_result(), app_config, llm=UnsafeLLM())
    assert reply != "Buy now"
