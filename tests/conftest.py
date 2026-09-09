import pytest

from social_lead_hunter.config import AppConfig, BusinessConfig, RuntimeConfig, SearchConfig


@pytest.fixture
def app_config():
    return AppConfig(
        business=BusinessConfig(
            description="generic local service provider",
            services=["custom labels", "custom service"],
            reply_style="helpful, concise, contextual",
            cta="",
        ),
        search=SearchConfig(
            keywords=["looking for supplier", "need custom service"],
            freshness_hours=24,
            min_score=80,
            target_locations=["Malaysia"],
            negative_keywords=["job vacancy", "giveaway"],
        ),
        runtime=RuntimeConfig(),
    )
