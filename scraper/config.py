import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ── LM Studio (local, no cloud) ───────────────────────────────────────────────
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
LM_STUDIO_API_KEY  = os.getenv("LM_STUDIO_API_KEY",  "lm-studio")

# MODEL_SPEED selects between fast (small, quick) and quality (larger, slower).
# Override via .env: MODEL_SPEED=fast|quality
# Or set LM_STUDIO_MODEL directly to bypass the preset logic.
_speed = os.getenv("MODEL_SPEED", "fast").lower()
_fast_model    = os.getenv("LM_STUDIO_MODEL_FAST",    "google/gemma-3-4b")
_quality_model = os.getenv("LM_STUDIO_MODEL_QUALITY", "deepseek-r1-0528-qwen3-8b-mlx")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL") or (
    _fast_model if _speed == "fast" else _quality_model
)

# ── Firecrawl — SDK-based. Set FIRECRAWL_URL=http://localhost:3002 for Docker.
# Defaults to cloud API (api.firecrawl.dev) if unset or set to the cloud URL.
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
FIRECRAWL_URL     = os.getenv("FIRECRAWL_URL", "")   # empty = cloud default
FIRECRAWL_CLOUD_API_KEY = os.getenv("FIRECRAWL_CLOUD_API_KEY", "")

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent          # firecrawl/

PORTALS_PATH = os.getenv(
    "PORTALS_PATH",
    str(_ROOT / "KNOWN_PORTALS.md"),
)
OUTPUT_BASE = os.getenv(
    "OUTPUT_BASE",
    str(_ROOT / "All_CSV_Outputs"),
)

# ── Scraper tuning ────────────────────────────────────────────────────────────
ENRICH_WORKERS         = int(os.getenv("ENRICH_WORKERS",         "4"))
WORKDAY_PAGE_SIZE      = int(os.getenv("WORKDAY_PAGE_SIZE",      "20"))
REQUEST_TIMEOUT        = int(os.getenv("REQUEST_TIMEOUT",        "30"))
WORKDAY_MAX_JOBS       = int(os.getenv("WORKDAY_MAX_JOBS",       "500"))
WORKDAY_JD_FETCH_LIMIT = int(os.getenv("WORKDAY_JD_FETCH_LIMIT", "500"))
