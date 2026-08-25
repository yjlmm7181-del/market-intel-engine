"""AI provider via any OpenAI-compatible chat-completions endpoint.

If no API key is configured, ``available`` is False and ``complete`` returns
None, so callers fall back to deterministic templates (see AIAnalyst and
SmsGenerator). Any request error also returns None rather than raising, so the
app keeps working without a reachable model.
"""

from typing import Optional

import httpx


class AIProvider:
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")
        self.model = model
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, system: str, user: str, max_tokens: int = 500) -> Optional[str]:
        if not self.available:
            return None
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }
        try:
            r = httpx.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self.timeout,
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            return None
