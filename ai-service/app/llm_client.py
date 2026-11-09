"""One place to resolve and call the configured LLM.

Every provider is reached through the OpenAI-compatible API. Precedence:
LLM_BASE_URL (Ollama, vLLM, ...), then Gemini, then OpenAI. With none of them
configured `resolve_llm` returns None and callers use extractive answers.
"""
import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


@dataclass
class LLM:
    client: Any
    model: str
    provider: str
    extra_params: Dict[str, Any] = field(default_factory=dict)


def _usable(key: str) -> bool:
    key = (key or "").strip()
    return bool(key) and not key.startswith("your_")


def _client(api_key: str, base_url: Optional[str] = None) -> OpenAI:
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=settings.LLM_TIMEOUT_S,
        max_retries=3,
    )


def resolve_llm() -> Optional[LLM]:
    if settings.LLM_BASE_URL.strip() and settings.LLM_MODEL.strip():
        return LLM(
            client=_client(settings.LLM_API_KEY or "local", settings.LLM_BASE_URL.strip()),
            model=settings.LLM_MODEL.strip(),
            provider="openai-compatible",
        )
    if _usable(settings.GEMINI_API_KEY):
        return LLM(
            client=_client(settings.GEMINI_API_KEY.strip(), GEMINI_BASE_URL),
            model=settings.GEMINI_MODEL,
            provider="gemini",
            extra_params={"reasoning_effort": settings.GEMINI_REASONING_EFFORT},
        )
    if _usable(settings.OPENAI_API_KEY):
        return LLM(
            client=_client(settings.OPENAI_API_KEY.strip()),
            model=settings.OPENAI_MODEL,
            provider="openai",
        )
    return None


_throttle_lock = threading.Lock()
_next_call_at = 0.0


def _wait_for_slot() -> None:
    global _next_call_at
    interval = settings.LLM_MIN_INTERVAL_S
    if interval <= 0:
        return
    with _throttle_lock:
        now = time.monotonic()
        wait = max(0.0, _next_call_at - now)
        _next_call_at = max(now, _next_call_at) + interval
    if wait:
        time.sleep(wait)


def chat_completion(
    llm: LLM,
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
) -> str:
    """Return the reply text; an empty reply raises so callers can fall back."""
    _wait_for_slot()
    completion = llm.client.chat.completions.create(
        model=llm.model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
        **llm.extra_params,
    )
    content = (completion.choices[0].message.content or "").strip()
    if not content:
        raise ValueError(f"Empty LLM reply (finish_reason={completion.choices[0].finish_reason})")
    return content


def parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """Read the first JSON object from a reply that may be wrapped in prose."""
    match = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None
