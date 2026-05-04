#!/usr/bin/env python3
"""
Compatibility entrypoint for Phase 3 uploads.

The canonical implementation now lives in:
    scraper/csv_importer.py

This shim keeps older commands working (`python csv_importer.py`) while
preventing schema drift between duplicate importer implementations.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    scraper_dir = repo_root / "scraper"
    target = scraper_dir / "csv_importer.py"
    if not target.exists():
        raise SystemExit(f"Missing canonical importer: {target}")

    # Ensure `scraper/` local imports (config.py, schema.py, etc.) resolve.
    sys.path.insert(0, str(scraper_dir))
    try:
        runpy.run_path(str(target), run_name="__main__")
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing Python dependency while starting scraper/csv_importer.py. "
            "Install scraper requirements first (for example: `pip install -r scraper/requirements.txt`). "
            f"Original error: {exc}"
        ) from exc


if __name__ == "__main__":
    main()
