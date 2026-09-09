from __future__ import annotations

import json
import os
import requests


class OpenAICompatibleClient:
    def __init__(self, api_base: str | None = None, api_key: str | None = None, model: str | None = None, timeout: float = 30.0):
        self.api_base = (api_base or os.getenv("LLM_API_BASE") or "").rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY") or ""
        self.model = model or os.getenv("LLM_MODEL") or ""
        self.timeout = timeout
        if not self.api_base or not self.api_key or not self.model:
            raise ValueError("LLM_API_BASE, LLM_API_KEY and LLM_MODEL are required when LLM is enabled")

    def complete_json(self, system: str, user: str) -> dict:
        response = requests.post(
            f"{self.api_base}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"LLM request failed ({response.status_code})")
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)
