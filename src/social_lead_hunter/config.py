from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RuntimeConfig:
    dry_run: bool = True
    max_replies_per_day: int = 5
    min_reply_gap_minutes: int = 30
    same_user_cooldown_days: int = 7


@dataclass
class SearchConfig:
    keywords: list[str]
    freshness_hours: int = 24
    min_score: int = 80
    target_locations: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)


@dataclass
class BusinessConfig:
    description: str
    services: list[str] = field(default_factory=list)
    reply_style: str = "helpful, concise, contextual"
    cta: str = ""


@dataclass
class AppConfig:
    business: BusinessConfig
    search: SearchConfig
    runtime: RuntimeConfig
    storage_backend: str = "sqlite"
    storage_path: str = "social_leads.sqlite3"
    llm_enabled: bool = False


def mask_secret(value: str | None) -> str:
    if not value:
        return "<unset>"
    if len(value) <= 4:
        return "****"
    return "****" + value[-4:]


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("expected a list")
    return [str(v).strip() for v in value if str(v).strip()]


def load_config(path: str) -> AppConfig:
    raw = yaml.safe_load(Path(path).expanduser().read_text(encoding="utf-8")) or {}
    business_raw = raw.get("business") or {}
    search_raw = raw.get("search") or {}
    runtime_raw = raw.get("runtime") or {}
    storage_raw = raw.get("storage") or {}
    llm_raw = raw.get("llm") or {}

    description = str(business_raw.get("description") or "").strip()
    if not description:
        raise ValueError("business.description is required")

    keywords = _as_list(search_raw.get("keywords"))
    if not keywords:
        raise ValueError("search.keywords must contain at least one keyword")

    min_score = int(search_raw.get("min_score", 80))
    if not 0 <= min_score <= 100:
        raise ValueError("search.min_score must be between 0 and 100")

    runtime = RuntimeConfig(
        dry_run=bool(runtime_raw.get("dry_run", True)),
        max_replies_per_day=int(runtime_raw.get("max_replies_per_day", 5)),
        min_reply_gap_minutes=int(runtime_raw.get("min_reply_gap_minutes", 30)),
        same_user_cooldown_days=int(runtime_raw.get("same_user_cooldown_days", 7)),
    )
    if runtime.max_replies_per_day <= 0:
        raise ValueError("runtime.max_replies_per_day must be positive")
    if runtime.min_reply_gap_minutes < 0:
        raise ValueError("runtime.min_reply_gap_minutes cannot be negative")
    if runtime.same_user_cooldown_days < 0:
        raise ValueError("runtime.same_user_cooldown_days cannot be negative")

    search = SearchConfig(
        keywords=keywords,
        freshness_hours=int(search_raw.get("freshness_hours", 24)),
        min_score=min_score,
        target_locations=_as_list(search_raw.get("target_locations")),
        negative_keywords=_as_list(search_raw.get("negative_keywords")),
    )
    if search.freshness_hours <= 0:
        raise ValueError("search.freshness_hours must be positive")

    business = BusinessConfig(
        description=description,
        services=_as_list(business_raw.get("services")),
        reply_style=str(business_raw.get("reply_style") or "helpful, concise, contextual").strip(),
        cta=str(business_raw.get("cta") or "").strip(),
    )

    storage_path = str(storage_raw.get("path") or "social_leads.sqlite3").strip()
    storage_path = str(Path(storage_path).expanduser())

    return AppConfig(
        business=business,
        search=search,
        runtime=runtime,
        storage_backend=str(storage_raw.get("backend") or "sqlite").strip().lower(),
        storage_path=storage_path,
        llm_enabled=bool(llm_raw.get("enabled", False)),
    )
