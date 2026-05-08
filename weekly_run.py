"""
    weekly_run.py — Weekly job scraping pipeline

Phase 1:   KNOWN_PORTALS provider scrape
Phase 2:   LM Studio enrichment (main_skills + side_skills)
Phase 3:   Supabase upsert

Usage:
    python3 weekly_run.py                  # full run
    python3 weekly_run.py --skip-enrich    # scrape + upload only
    python3 weekly_run.py --skip-upload    # scrape + enrich only
    python3 weekly_run.py --dry-run        # print commands, no writes
"""
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_HERE    = Path(__file__).resolve().parent
_SCRAPER = _HERE / "scraper" / "main.py"
_IMPORT  = _HERE / "csv_importer.py"
_PY      = sys.executable


def _run(label: str, cmd: list, cwd: Path = _HERE) -> bool:
    print(f"\n{'═' * 60}\n  {label}\n{'═' * 60}")
    ok = subprocess.run(cmd, cwd=str(cwd)).returncode == 0
    print(f"\n  → {'✅ DONE' if ok else '❌ FAILED'}")
    return ok


def main():
    p = argparse.ArgumentParser(description="Mirror weekly scraping pipeline")
    p.add_argument("--skip-enrich",  action="store_true")
    p.add_argument("--skip-upload",  action="store_true")
    p.add_argument("--dry-run",      action="store_true")
    args = p.parse_args()

    t0 = datetime.now()
    ok: dict[str, bool] = {}

    # Phase 1: provider scrape from KNOWN_PORTALS.md
    cmd = [_PY, str(_SCRAPER), "--skip-enrich", "--scope", "global", "--global-cap", "2000"]
    ok["scrape"] = _run(
        "Phase 1 — KNOWN_PORTALS provider scrape", cmd, _HERE / "scraper"
    ) if not args.dry_run else True

    # Phase 2: LM Studio enrichment
    if not args.skip_enrich:
        cmd = [_PY, str(_SCRAPER), "--enrich-only"]
        ok["enrich"] = _run(
            "Phase 2 — LM Studio enrichment", cmd, _HERE / "scraper"
        ) if not args.dry_run else True

    # Phase 3: Supabase upsert
    if not args.skip_upload:
        cmd = [_PY, str(_IMPORT)]
        ok["upload"] = _run("Phase 3 — Supabase upsert", cmd) if not args.dry_run else True

    print(f"\n{'═' * 60}")
    for phase, status in ok.items():
        print(f"  {'✅' if status else '❌'} {phase}")
    print(f"  Total: {datetime.now() - t0}\n{'═' * 60}")

    if not all(ok.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
