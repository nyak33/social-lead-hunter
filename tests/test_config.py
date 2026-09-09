from pathlib import Path
import pytest

from social_lead_hunter.config import load_config, mask_secret


def test_default_dry_run_is_true(tmp_path: Path):
    p = tmp_path / "config.yaml"
    p.write_text("business:\n  description: generic service provider\nsearch:\n  keywords: [service]\n", encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg.runtime.dry_run is True


def test_missing_keywords_is_rejected(tmp_path: Path):
    p = tmp_path / "config.yaml"
    p.write_text("business:\n  description: test\n", encoding="utf-8")
    with pytest.raises(ValueError, match="keywords"):
        load_config(str(p))


def test_mask_secret_never_returns_full_value():
    secret = "abcd1234SUPERSECRET"
    masked = mask_secret(secret)
    assert secret not in masked
    assert masked.endswith("CRET")
