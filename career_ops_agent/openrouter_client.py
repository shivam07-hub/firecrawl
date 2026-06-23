"""
OpenRouter chat client — OpenAI-compatible, requests only.
User supplies OPENROUTER_API_KEY at run time.
"""
from __future__ import annotations

import json
import re
from typing import Any

import requests

import config


class OpenRouterError(RuntimeError):
    pass


def chat(
    system: str,
    user: str,
    *,
    model: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.2,
) -> tuple[str, dict[str, Any]]:
    """Return (text, usage). Raises OpenRouterError on failure."""
    if not config.openrouter_ready():
        raise OpenRouterError(
            "OPENROUTER_API_KEY not set. Pass --api-key, export OPENROUTER_API_KEY, "
            "or add it to career_ops_agent/.env"
        )
    model = model or config.OPENROUTER_MODEL
    resp = requests.post(
        f"{config.OPENROUTER_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            # Optional attribution headers OpenRouter recommends:
            "HTTP-Referer": "https://github.com/career-ops-agent",
            "X-Title": "Career Ops Agent",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=120,
    )
    if resp.status_code != 200:
        raise OpenRouterError(f"OpenRouter {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise OpenRouterError(f"Unexpected response shape: {json.dumps(data)[:500]}") from e
    return text, data.get("usage", {})


def extract_json(text: str) -> dict[str, Any]:
    """Pull a JSON object out of a model response (handles ```json fences)."""
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text) or re.search(
        r"(\{[\s\S]*\})", text
    )
    if not m:
        raise OpenRouterError("Could not parse JSON from model response")
    return json.loads(m.group(1))
