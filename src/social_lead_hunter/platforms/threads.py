from __future__ import annotations

from datetime import datetime, timezone
import os
import time
from typing import Any

import requests

from social_lead_hunter.models import CapabilityResult, SocialPost
from social_lead_hunter.platforms.base import AuthenticationError, PermissionError, ProviderError, RateLimitError


class ThreadsAdapter:
    REQUIRED_SEARCH_SCOPES = {"threads_basic", "threads_keyword_search"}
    REQUIRED_REPLY_SCOPES = {"threads_basic", "threads_content_publish"}

    def __init__(
        self,
        access_token: str | None = None,
        user_id: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        session: Any | None = None,
        timeout: float = 20.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.5,
    ):
        self.access_token = access_token or os.getenv("THREADS_ACCESS_TOKEN") or ""
        self.user_id = user_id or os.getenv("THREADS_USER_ID") or ""
        self.base_url = (base_url or os.getenv("THREADS_API_BASE") or "https://graph.threads.net").rstrip("/")
        self.api_version = (api_version or os.getenv("THREADS_API_VERSION") or "").strip().strip("/")
        self.session = session or requests.Session()
        self.timeout = timeout
        self.max_retries = int(max_retries)
        self.retry_backoff_seconds = float(retry_backoff_seconds)
        self.own_username: str | None = None
        if not self.access_token:
            raise ValueError("THREADS_ACCESS_TOKEN is required")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds cannot be negative")

    @property
    def api_root(self) -> str:
        return f"{self.base_url}/{self.api_version}" if self.api_version else self.base_url

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    def _wait_before_retry(self, attempt: int) -> None:
        if self.retry_backoff_seconds <= 0:
            return
        time.sleep(self.retry_backoff_seconds * (2 ** attempt))

    def _request(self, method: str, path: str, **kwargs):
        headers = dict(self.headers)
        headers.update(kwargs.pop("headers", {}) or {})
        url = f"{self.api_root}{path}"

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, headers=headers, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                if attempt >= self.max_retries:
                    raise ProviderError("Threads network request failed after bounded retries") from exc
                self._wait_before_retry(attempt)
                continue

            status = int(getattr(response, "status_code", 0))
            if status == 401:
                raise AuthenticationError("Threads authentication failed; token may be invalid or expired")
            if status == 403:
                raise PermissionError("Threads permission denied; required scope or app access may be missing")
            if status == 429:
                raise RateLimitError("Threads API rate limit reached")
            if status >= 500:
                if attempt < self.max_retries:
                    self._wait_before_retry(attempt)
                    continue
                raise ProviderError(f"Threads API provider error ({status}) after bounded retries")
            if status >= 400:
                raise ProviderError(f"Threads API request failed ({status})")

            try:
                return response.json()
            except Exception as exc:
                raise ProviderError("Threads API returned invalid JSON") from exc

        raise ProviderError("Threads API request failed")

    def _debug_token(self) -> dict[str, Any]:
        payload = self._request("GET", "/debug_token", params={"input_token": self.access_token})
        return payload.get("data") or {}

    def validate_identity(self) -> CapabilityResult:
        try:
            data = self._request("GET", "/me", params={"fields": "id,username"})
            username = data.get("username") or "unknown"
            self.own_username = None if username == "unknown" else str(username)
            return CapabilityResult("identity", bool(data.get("id")), f"authenticated as {username}")
        except Exception as exc:
            return CapabilityResult("identity", False, str(exc))

    def _validate_scopes(self, name: str, required: set[str]) -> CapabilityResult:
        try:
            data = self._debug_token()
            if not data.get("is_valid", False):
                return CapabilityResult(name, False, "access token is not valid")
            scopes = set(data.get("scopes") or [])
            missing = sorted(required - scopes)
            if missing:
                return CapabilityResult(name, False, "missing scopes: " + ", ".join(missing))
            return CapabilityResult(name, True, "required scopes are present")
        except Exception as exc:
            return CapabilityResult(name, False, str(exc))

    def validate_search_capability(self) -> CapabilityResult:
        scope_result = self._validate_scopes("keyword_search", self.REQUIRED_SEARCH_SCOPES)
        if not scope_result.ok:
            return scope_result
        try:
            self.search_recent("service", limit=1)
            return CapabilityResult("keyword_search", True, "keyword search request succeeded")
        except Exception as exc:
            return CapabilityResult("keyword_search", False, str(exc))

    def validate_reply_capability(self) -> CapabilityResult:
        return self._validate_scopes("reply", self.REQUIRED_REPLY_SCOPES)

    def search_recent(self, query: str, limit: int = 50, since: datetime | None = None) -> list[SocialPost]:
        params: dict[str, Any] = {
            "q": query,
            "search_type": "RECENT",
            "fields": "id,username,text,timestamp,permalink",
            "limit": int(limit),
        }
        if since is not None:
            since_utc = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
            params["since"] = since_utc.astimezone(timezone.utc).isoformat()
        payload = self._request("GET", "/keyword_search", params=params)
        posts: list[SocialPost] = []
        for item in payload.get("data") or []:
            timestamp_raw = item.get("timestamp")
            if not timestamp_raw:
                continue
            normalized = str(timestamp_raw).replace("Z", "+00:00")
            try:
                timestamp = datetime.fromisoformat(normalized)
            except ValueError:
                continue
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            posts.append(
                SocialPost(
                    platform="threads",
                    external_id=str(item.get("id") or ""),
                    username=str(item.get("username") or ""),
                    text=str(item.get("text") or ""),
                    permalink=str(item.get("permalink") or ""),
                    timestamp=timestamp,
                    raw=dict(item),
                )
            )
        return [p for p in posts if p.external_id]

    def publish_reply(self, post_id: str, text: str) -> str:
        payload = self._request(
            "POST",
            "/me/threads",
            params={
                "media_type": "TEXT",
                "text": text,
                "reply_to_id": post_id,
                "auto_publish_text": "true",
            },
        )
        reply_id = str(payload.get("id") or "")
        if not reply_id:
            raise ProviderError("Threads API reply response did not include an id")
        return reply_id
