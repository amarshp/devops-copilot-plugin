"""
llm_call_template.py — GitHub Copilot LLM client used across all skills.

Reads COPILOT_TOKEN and COPILOT_MODEL from config (which reads from .env).
Any skill script that needs LLM calls imports this module.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Dict, List

import requests

# Allow running from any skill's scripts/ directory — find canonical config
_SHARED = Path(__file__).resolve().parents[2] / "devops-setup" / "scripts"
if _SHARED.exists() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

try:
    import config as _cfg
    DEFAULT_MODEL = _cfg.COPILOT_MODEL
    DEFAULT_URL = _cfg.COPILOT_CHAT_URL
except (ImportError, AttributeError):
    # Standalone use without config module on path
    import os
    DEFAULT_MODEL = os.environ.get("COPILOT_MODEL", "claude-sonnet-4.6")
    DEFAULT_URL = os.environ.get(
        "COPILOT_CHAT_URL",
        "https://api.business.githubcopilot.com/chat/completions",
    )
    _cfg = None  # type: ignore[assignment]

DEFAULT_TIMEOUT = 180
DEFAULT_MAX_RETRIES = 4
DEFAULT_RETRY_DELAY_SECONDS = 5

_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class CopilotClient:
    def __init__(self, model: str = DEFAULT_MODEL):
        import os
        token = (getattr(_cfg, "COPILOT_TOKEN", None) or os.environ.get("COPILOT_TOKEN", ""))
        if not token:
            raise RuntimeError(
                "COPILOT_TOKEN not set. Add it to your .env file: COPILOT_TOKEN=ghp_..."
            )
        self.token = token
        self.model = model
        self.url = DEFAULT_URL

    def _should_retry(self, response: requests.Response | None, body: str) -> bool:
        if response is not None and response.status_code in _RETRYABLE_STATUS:
            return True
        low = body.lower()
        return "model_not_supported" in low or "temporarily unavailable" in low

    def chat(self, messages: List[Dict], temperature: float = 0.1) -> str:
        last_error: Exception | None = None
        for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
            r = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "messages": messages, "temperature": temperature},
                timeout=DEFAULT_TIMEOUT,
            )
            try:
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except requests.HTTPError as exc:
                body = r.text[:4000]
                last_error = requests.HTTPError(
                    f"{exc}\nBody:\n{body}", response=r
                )
                if attempt >= DEFAULT_MAX_RETRIES or not self._should_retry(r, body):
                    raise last_error from exc
                time.sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
        raise last_error or RuntimeError("LLM request failed")


def call_llm(messages: List[Dict], model: str = DEFAULT_MODEL, temperature: float = 0.1) -> str:
    """Convenience wrapper — call and return the text response."""
    return CopilotClient(model=model).chat(messages, temperature=temperature)
