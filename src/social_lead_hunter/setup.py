from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from social_lead_hunter.config import load_config
from social_lead_hunter.storage.sqlite import SQLiteStorage


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "social-lead-hunter" / "config.yaml"
DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "social-lead-hunter" / "social_leads.sqlite3"
REQUIRED_RUNTIME_ENV = ("THREADS_ACCESS_TOKEN",)


def _default_config_text(database_path: Path) -> str:
    return f'''business:
  description: "CHANGE_ME: describe what the business offers"
  services:
    - "CHANGE_ME: service or product"
  reply_style: "helpful, concise, contextual"
  cta: ""

search:
  keywords:
    - "CHANGE_ME: buyer-intent search phrase"
  negative_keywords: []
  target_locations: []
  freshness_hours: 24
  min_score: 80

runtime:
  dry_run: true
  max_replies_per_day: 5
  min_reply_gap_minutes: 30
  same_user_cooldown_days: 7

storage:
  backend: "sqlite"
  path: "{database_path.as_posix()}"

llm:
  enabled: false
'''


@dataclass(frozen=True)
class SetupResult:
    config_path: str
    storage_path: str | None
    created_config: bool
    missing_environment: list[str]


def setup_local(config_path: str | None = None, force: bool = False) -> SetupResult:
    path = Path(config_path or DEFAULT_CONFIG_PATH).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    created_config = False

    if force or not path.exists():
        db_path = DEFAULT_DB_PATH.expanduser().resolve()
        path.write_text(_default_config_text(db_path), encoding="utf-8")
        created_config = True

    try:
        cfg = load_config(str(path))
    except Exception as exc:
        raise ValueError(
            f"Existing config is invalid: {exc}. Fix it or rerun setup with --force to replace it."
        ) from exc

    storage_path: str | None = None
    if cfg.storage_backend == "sqlite":
        db_path = Path(cfg.storage_path).expanduser().resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        SQLiteStorage(str(db_path))
        storage_path = str(db_path)

    missing_environment = [name for name in REQUIRED_RUNTIME_ENV if not os.getenv(name)]
    return SetupResult(
        config_path=str(path),
        storage_path=storage_path,
        created_config=created_config,
        missing_environment=missing_environment,
    )
