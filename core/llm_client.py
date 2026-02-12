"""Lightweight OpenAI chat-completion client using only stdlib.

Replaces the ``openai`` package with a single function that POSTs to the
OpenAI chat completions endpoint via ``urllib.request``.
"""

from __future__ import annotations

import json
import ssl
import urllib.request
from typing import Any, Dict, List, Tuple

_API_URL = "https://api.openai.com/v1/chat/completions"


def chat_completion(
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
) -> Tuple[str, int]:
    """Call the OpenAI chat completions API.

    Returns:
        A tuple of (content_string, total_tokens).
    """
    payload = json.dumps({
        "model": model,
        "temperature": temperature,
        "messages": messages,
    }).encode()

    req = urllib.request.Request(
        _API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
        body: Dict[str, Any] = json.loads(resp.read())

    content = body["choices"][0]["message"]["content"] or ""
    tokens = body.get("usage", {}).get("total_tokens", 0)
    return content, tokens
