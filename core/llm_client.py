"""Lightweight chat-completion client using only stdlib.

Supports OpenAI and any OpenAI-compatible API (e.g. Ollama) via
configurable ``base_url``.  Uses ``urllib.request`` for HTTP.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, List, Tuple

from core.errors import AgentError

_DEFAULT_API_URL = "https://api.openai.com/v1/chat/completions"


def _handle_http_error(exc: urllib.error.HTTPError) -> None:
    """Translate HTTP errors into AgentError with meaningful messages."""
    try:
        detail = json.loads(exc.read().decode())
        msg = detail.get("error", {}).get("message", str(detail))
    except Exception:
        msg = exc.reason

    if exc.code == 401:
        raise AgentError("llm_client", f"Authentication failed (401): {msg}") from exc
    elif exc.code == 429:
        raise AgentError("llm_client", f"Rate limit exceeded (429): {msg}") from exc
    elif exc.code >= 500:
        raise AgentError("llm_client", f"OpenAI server error ({exc.code}): {msg}") from exc
    else:
        raise AgentError("llm_client", f"HTTP {exc.code}: {msg}") from exc


def chat_completion(
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    base_url: str = "",
) -> Tuple[str, int]:
    """Call a chat completions API (OpenAI or compatible).

    Args:
        base_url: Custom API base URL (e.g. ``http://localhost:11434``
                  for Ollama).  Leave empty to use the OpenAI default.

    Returns:
        A tuple of (content_string, total_tokens).

    Raises:
        AgentError: On HTTP errors, network failures, or malformed responses.
    """
    # Resolve endpoint URL
    if base_url:
        url = base_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url = url + "/v1/chat/completions"
    else:
        url = _DEFAULT_API_URL

    payload = json.dumps({
        "model": model,
        "temperature": temperature,
        "messages": messages,
    }).encode()

    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
        method="POST",
    )

    ctx = ssl.create_default_context() if url.startswith("https") else None

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        _handle_http_error(exc)
    except urllib.error.URLError as exc:
        raise AgentError("llm_client", f"Network error: {exc.reason}") from exc
    except TimeoutError:
        raise AgentError("llm_client", "Request timed out after 120s") from None

    try:
        body: Dict[str, Any] = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise AgentError("llm_client", f"Invalid JSON in API response: {raw[:200]}") from exc

    try:
        content = body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise AgentError("llm_client", f"Unexpected response structure: {list(body.keys())}") from exc

    tokens = body.get("usage", {}).get("total_tokens", 0)
    return content, tokens
