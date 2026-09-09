from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SocialPost:
    platform: str
    external_id: str
    username: str
    text: str
    permalink: str
    timestamp: datetime
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class QualificationResult:
    score: int
    qualified: bool
    excluded: bool
    reasons: list[str] = field(default_factory=list)
    intent: str = "unknown"
    location_detected: str | None = None
    service_detected: str | None = None


@dataclass
class CapabilityResult:
    name: str
    ok: bool
    detail: str


@dataclass
class SafetyDecision:
    allowed: bool
    reason: str


@dataclass
class RunSummary:
    scanned: int = 0
    new_posts: int = 0
    qualified: int = 0
    rejected: int = 0
    duplicates: int = 0
    drafted: int = 0
    replied: int = 0
    failed: int = 0
