from __future__ import annotations

from datetime import datetime, timezone
import os
import requests

from social_lead_hunter.models import QualificationResult, SocialPost


class SupabaseStorage:
    def __init__(self, url: str | None = None, key: str | None = None, timeout: float = 20.0):
        self.url = (url or os.getenv("SUPABASE_URL") or "").rstrip("/")
        self.key = key or os.getenv("SUPABASE_KEY") or ""
        self.timeout = timeout
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY are required for Supabase storage")

    @property
    def _headers(self) -> dict[str, str]:
        return {"apikey": self.key, "Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}

    def _request(self, method: str, table: str, **kwargs):
        headers = dict(self._headers)
        headers.update(kwargs.pop("headers", {}) or {})
        response = requests.request(method, f"{self.url}/rest/v1/{table}", headers=headers, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response

    def has_post(self, platform: str, external_id: str) -> bool:
        r = self._request("GET", "social_lead_posts", params={"select": "external_id", "platform": f"eq.{platform}", "external_id": f"eq.{external_id}", "limit": "1"})
        return bool(r.json())

    def save_raw_post(self, platform: str, external_id: str, username: str, text: str, permalink: str, timestamp: datetime) -> None:
        self._request("POST", "social_lead_posts", params={"on_conflict": "platform,external_id"}, headers={**self._headers, "Prefer": "resolution=ignore-duplicates"}, json={
            "platform": platform,
            "external_id": external_id,
            "username": username,
            "text": text,
            "permalink": permalink,
            "post_timestamp": timestamp.astimezone(timezone.utc).isoformat() if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc).isoformat(),
        })

    def save_candidate(self, post: SocialPost, result: QualificationResult, draft_reply: str | None, status: str) -> None:
        self._request("POST", "social_leads", params={"on_conflict": "platform,external_id"}, headers={**self._headers, "Prefer": "resolution=merge-duplicates"}, json={
            "platform": post.platform,
            "external_id": post.external_id,
            "username": post.username,
            "score": result.score,
            "reasons": result.reasons,
            "draft_reply": draft_reply,
            "status": status,
        })

    def mark_replied(self, platform: str, external_id: str, reply_id: str) -> None:
        lead_response = self._request(
            "GET",
            "social_leads",
            params={"select": "username", "platform": f"eq.{platform}", "external_id": f"eq.{external_id}", "limit": "1"},
        )
        lead_rows = lead_response.json()
        username = str(lead_rows[0].get("username") or "unknown") if lead_rows else "unknown"
        self._request("PATCH", "social_leads", params={"platform": f"eq.{platform}", "external_id": f"eq.{external_id}"}, json={"status": "replied"})
        self._request("POST", "social_lead_replies", json={"platform": platform, "external_id": external_id, "username": username, "reply_id": reply_id, "replied_at": datetime.now(timezone.utc).isoformat()})

    def last_reply_to_user(self, username: str) -> datetime | None:
        r = self._request("GET", "social_lead_replies", params={"select": "replied_at", "username": f"eq.{username}", "order": "replied_at.desc", "limit": "1"})
        rows = r.json()
        return datetime.fromisoformat(rows[0]["replied_at"]) if rows else None

    def replies_since(self, since: datetime) -> list[datetime]:
        s = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
        r = self._request("GET", "social_lead_replies", params={"select": "replied_at", "replied_at": f"gte.{s.astimezone(timezone.utc).isoformat()}", "order": "replied_at.asc"})
        return [datetime.fromisoformat(row["replied_at"]) for row in r.json()]
