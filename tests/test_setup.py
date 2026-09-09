from pathlib import Path

from social_lead_hunter.config import load_config
from social_lead_hunter.setup import setup_local


def test_setup_creates_safe_config_and_sqlite_database(tmp_path: Path):
    config_path = tmp_path / ".config" / "social-lead-hunter" / "config.yaml"
    result = setup_local(str(config_path))

    assert config_path.exists()
    cfg = load_config(str(config_path))
    assert cfg.runtime.dry_run is True
    assert Path(cfg.storage_path).exists()
    assert result.created_config is True
    assert "THREADS_ACCESS_TOKEN" in result.missing_environment


def test_setup_does_not_overwrite_existing_config_without_force(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "business:\n  description: Existing configuration\nsearch:\n  keywords: [existing]\nruntime:\n  dry_run: true\n",
        encoding="utf-8",
    )
    original = config_path.read_text(encoding="utf-8")

    result = setup_local(str(config_path))

    assert result.created_config is False
    assert config_path.read_text(encoding="utf-8") == original


def test_setup_force_replaces_config_with_safe_template(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("broken: true\n", encoding="utf-8")

    result = setup_local(str(config_path), force=True)

    cfg = load_config(str(config_path))
    assert result.created_config is True
    assert cfg.runtime.dry_run is True
