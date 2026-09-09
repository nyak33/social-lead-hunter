from datetime import datetime, timezone

from social_lead_hunter.models import SocialPost
from social_lead_hunter.qualification.scorer import qualify_post


def test_direct_request_scores_high(app_config):
    post = SocialPost(
        platform="threads",
        external_id="p1",
        username="buyer",
        text="Looking for a supplier for custom labels in Malaysia, need quotation urgently qty 1000",
        permalink="https://example.invalid/p1",
        timestamp=datetime.now(timezone.utc),
    )
    result = qualify_post(post, app_config)
    assert result.score >= 80
    assert result.qualified is True


def test_self_post_is_excluded(app_config):
    post = SocialPost(platform="threads", external_id="p2", username="myaccount", text="looking for custom service", permalink="x", timestamp=datetime.now(timezone.utc))
    result = qualify_post(post, app_config, own_username="myaccount")
    assert result.excluded is True
    assert result.score == 0


def test_supplier_advertisement_is_not_a_buying_lead(app_config):
    post = SocialPost(platform="threads", external_id="p3", username="vendor", text="We provide professional custom labels. DM us now.", permalink="x", timestamp=datetime.now(timezone.utc))
    result = qualify_post(post, app_config)
    assert result.excluded is True or result.score < app_config.search.min_score
