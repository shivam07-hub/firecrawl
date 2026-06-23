"""
Career Ops Agent — configuration.

Zero heavy deps. Reads env from (in priority order):
  1. process environment
  2. career_ops_agent/.env
  3. ../scraper/.env   (reuses the firecrawl_Supabase Supabase creds — SUPABASE_URL / SUPABASE_SERVICE_KEY)

The LLM brain runs on OpenRouter. The user supplies OPENROUTER_API_KEY at run time
(env var, .env, or --api-key flag). No key is ever committed.
"""
from __future__ import annotations

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent  # firecrawl_Supabase/


def _load_env_file(path: Path) -> None:
    """Minimal .env loader — only sets keys not already in os.environ."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


# Load local .env first, then fall back to the scraper's .env for Supabase creds.
_load_env_file(HERE / ".env")
_load_env_file(REPO / "scraper" / ".env")


# ── Supabase (reused from scraper/.env) ──────────────────────────────────────
SUPABASE_URL = (os.getenv("SUPABASE_URL", "") or "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# ── OpenRouter (user-supplied at run time) ───────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
# Default model — override with OPENROUTER_MODEL or --model. Pick any OpenRouter slug.
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4")

# ── Paths ────────────────────────────────────────────────────────────────────
CV_PATH = Path(os.getenv("CV_PATH", str(HERE / "cv.md")))
PROFILE_PATH = Path(os.getenv("PROFILE_PATH", str(HERE / "profile.yaml")))
OUT_DIR = HERE / "out"


def supabase_ready() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def openrouter_ready() -> bool:
    return bool(OPENROUTER_API_KEY)
