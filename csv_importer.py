"""
csv_importer.py — Supabase upserter for Dump 4+ schema

Walks All_CSV_Outputs_thru_firecrawl/, picks the latest jobs.json per company,
quality-gates, then upserts into Supabase `jobs` table.

Schema (jobs table):
    job_id, job_title, job_description, company_name, Industry, Location,
    apply_url, main_skills TEXT[], side_skills TEXT[], batch_date INTEGER

Run from firecrawl_Supabase/ root:
    python3 csv_importer.py              # upload all valid non-placeholder rows
    python3 csv_importer.py --dry-run    # quality report only, no upload
    python3 csv_importer.py --min-score 1  # optional: enforce minimal quality gate
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

# ── Config ─────────────────────────────────────────────────────────────────────

_HERE     = Path(__file__).resolve().parent          # firecrawl_Supabase/

# Pull shared constants from scraper/ package
sys.path.insert(0, str(_HERE / "scraper"))
from schema import CANONICAL_FIELDS, LEGACY_FIELD_ALIASES  # noqa: E402
from validation import (  # noqa: E402
    is_placeholder_title,
    is_valid,
    quality_score,
    LOW_COUNT_THRESHOLD,
)
ENV_FILE  = _HERE / "scraper" / ".env"
LOGS_DIR  = _HERE / "logs"
BATCH_SIZE = 200
TABLE     = "jobs"
JOB_VERSIONS_TABLE = os.getenv("JOB_VERSIONS_TABLE", "job_versions")
_MEANINGFUL_FIELDS = ("job_title", "job_description", "location", "apply_url")

load_dotenv(ENV_FILE)
_DEFAULT_OUTPUT_BASE = _HERE / "All_CSV_Outputs_thru_firecrawl"
_CONFIGURED_OUTPUT_BASE = Path(os.getenv("OUTPUT_BASE", str(_DEFAULT_OUTPUT_BASE)))
OUTPUT_BASE = _CONFIGURED_OUTPUT_BASE
if not OUTPUT_BASE.exists() and _DEFAULT_OUTPUT_BASE.exists():
    OUTPUT_BASE = _DEFAULT_OUTPUT_BASE


# ── File discovery ─────────────────────────────────────────────────────────────

def discover_json_files(base: Path) -> list[Path]:
    """Return the latest jobs.json for each company folder."""
    found = []
    for company_dir in sorted(base.iterdir()):
        if not company_dir.is_dir():
            continue
        outputs_dir = company_dir / "Outputs"
        if not outputs_dir.is_dir():
            continue
        date_dirs = sorted(d for d in outputs_dir.iterdir() if d.is_dir())
        if not date_dirs:
            continue
        json_path = date_dirs[-1] / "jobs.json"
        if json_path.exists():
            found.append(json_path)
    return found


def infer_batch_date(json_path: Path) -> int:
    """
    Prefer batch date from folder name: .../Outputs/YYYY_MM_DD/jobs.json.
    Fall back to today's date if folder name is not parseable.
    """
    try:
        dt = datetime.strptime(json_path.parent.name, "%Y_%m_%d")
        return int(dt.strftime("%Y%m%d"))
    except Exception:
        return int(datetime.now().strftime("%Y%m%d"))


def _first_non_empty(job: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        val = job.get(key)
        if val is None:
            continue
        if isinstance(val, str):
            s = val.strip()
            if s:
                return s
            continue
        return str(val)
    return default


def _normalize_skills(value: object) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [s.strip() for s in value.split(",") if s.strip()]
    return []


def normalize_job(job: dict, default_batch_date: int) -> dict:
    """Normalize canonical and legacy raw schemas into one canonical job dict."""
    return {
        "job_id": _first_non_empty(job, "job_id"),
        "job_title": _first_non_empty(job, "job_title", "title"),
        "job_description": _first_non_empty(job, "job_description", "raw_jd_text"),
        "company_name": _first_non_empty(job, "company_name"),
        "industry": _first_non_empty(job, "industry", "Industry", "Industry_name"),
        "location": _first_non_empty(job, "location", "Location", "location_city", "location_country", default="India"),
        "apply_url": _first_non_empty(job, "apply_url", "job_url", "url"),
        "main_skills": _normalize_skills(job.get("main_skills") or job.get("skills_required")),
        "side_skills": _normalize_skills(job.get("side_skills") or job.get("skills_preferred")),
        "batch_date": int(job.get("batch_date") or default_batch_date),
    }


# is_placeholder_title, is_valid, quality_score imported from scraper/validation.py


def _truthy_env(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _meaningful_payload(row: dict) -> dict:
    return {k: str(row.get(k) or "").strip() for k in _MEANINGFUL_FIELDS}


def _fingerprint(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _changed_fields(old_payload: dict, new_payload: dict) -> list[str]:
    return [k for k in _MEANINGFUL_FIELDS if (old_payload.get(k) or "") != (new_payload.get(k) or "")]


# ── Quality gate ───────────────────────────────────────────────────────────────
# quality_score imported from scraper/validation.py


def preprocess(jobs: list[dict], min_score: int, default_batch_date: int) -> tuple[list[dict], int, int, int, int]:
    """
    Normalize + quality-gate.
    Returns (clean_jobs, n_invalid, n_dupes, n_quality_drop, n_placeholders).
    """
    normalized = [normalize_job(j, default_batch_date) for j in jobs]

    valid = [j for j in normalized if is_valid(j)]
    n_invalid = len(normalized) - len(valid)

    without_placeholders = [j for j in valid if not is_placeholder_title(j.get("job_title", ""))]
    n_placeholders = len(valid) - len(without_placeholders)

    seen: dict[str, dict] = {}
    for job in without_placeholders:
        jid = str(job["job_id"])
        prev = seen.get(jid)
        # Keep the richer row when duplicate IDs appear in mixed-schema dumps.
        if prev is None or quality_score(job) >= quality_score(prev):
            seen[jid] = job
    n_dupes = len(without_placeholders) - len(seen)

    passed = [j for j in seen.values() if quality_score(j) >= min_score]
    n_quality = len(seen) - len(passed)

    return list(passed), n_invalid, n_dupes, n_quality, n_placeholders


# ── Schema conformance ─────────────────────────────────────────────────────────

_SUPABASE_REQUIRED = frozenset({
    "job_id", "job_title", "job_description", "company_name",
    "industry", "location", "apply_url", "main_skills", "side_skills", "batch_date",
})


def validate_row(row: dict) -> list[str]:
    """Return list of field errors. Empty list = row is conformant."""
    errors = []
    for f in _SUPABASE_REQUIRED:
        if f not in row:
            errors.append(f"missing:{f}")
    if not isinstance(row.get("main_skills"), list):
        errors.append("type:main_skills must be list")
    if not isinstance(row.get("side_skills"), list):
        errors.append("type:side_skills must be list")
    return errors


# ── Row builder ────────────────────────────────────────────────────────────────

def build_row(job: dict) -> dict:
    """Map a canonical job dict → Supabase `jobs` table row."""
    skills_main = _normalize_skills(job.get("main_skills"))
    skills_side = _normalize_skills(job.get("side_skills"))

    return {
        "job_id":          str(job["job_id"]),
        "job_title":       str(job["job_title"]),
        "job_description": str(job.get("job_description") or ""),
        "company_name":    str(job.get("company_name") or ""),
        "industry":        str(job.get("industry") or job.get("Industry") or ""),
        "location":        str(job.get("location") or job.get("Location") or "India"),
        "apply_url":       str(job.get("apply_url") or "") or None,
        "main_skills":     skills_main,
        "side_skills":     skills_side,
        "batch_date":      job.get("batch_date") or int(datetime.now().strftime("%Y%m%d")),
    }


# ── Supabase I/O ───────────────────────────────────────────────────────────────

def upsert_batch(supabase: Client, batch: list[dict]) -> None:
    supabase.table(TABLE).upsert(batch, on_conflict="job_id").execute()


def supports_lifecycle_columns(supabase: Client) -> bool:
    try:
        supabase.table(TABLE).select("job_id,first_seen,last_seen,is_active,change_fingerprint").limit(1).execute()
        return True
    except Exception:
        return False


def supports_table(supabase: Client, table: str) -> bool:
    try:
        supabase.table(table).select("*").limit(1).execute()
        return True
    except Exception:
        return False


def fetch_company_existing(supabase: Client, company: str) -> tuple[dict[str, dict], set[str]]:
    """
    Return:
      existing_by_id: all known rows for company
      active_ids: currently active job ids for company
    """
    existing_by_id: dict[str, dict] = {}
    active_ids: set[str] = set()
    resp = supabase.table(TABLE).select(
        "job_id,first_seen,is_active,change_fingerprint,job_title,job_description,location,apply_url"
    ).eq("company_name", company).execute()
    for row in (resp.data or []):
        jid = str(row.get("job_id") or "")
        if not jid:
            continue
        existing_by_id[jid] = row
        if bool(row.get("is_active")):
            active_ids.add(jid)
    return existing_by_id, active_ids


def deactivate_jobs(supabase: Client, job_ids: list[str]) -> None:
    for chunk in _chunks(job_ids, BATCH_SIZE):
        supabase.table(TABLE).update({"is_active": False}).in_("job_id", chunk).execute()


def insert_version_events(supabase: Client, events: list[dict], table: str = JOB_VERSIONS_TABLE) -> None:
    for chunk in _chunks(events, BATCH_SIZE):
        supabase.table(table).insert(chunk).execute()


# ── Reports ────────────────────────────────────────────────────────────────────

def print_quality_report(json_files: list[Path], min_score: int) -> None:
    print(f"\n{'─'*72}")
    print(f"  QUALITY REPORT  (gate: min_score >= {min_score}/3)   table → {TABLE}")
    print(f"{'─'*72}")
    print(f"  {'Company':<35} {'Total':>6} {'Pass':>6} {'Drop':>6} {'PH':>4} {'JD%':>5} {'Skl%':>5}")
    print(f"  {'─'*35} {'─'*6} {'─'*6} {'─'*6} {'─'*4} {'─'*5} {'─'*5}")

    grand_total = grand_pass = grand_drop = grand_ph = 0
    for json_path in json_files:
        company = json_path.parts[-4]
        try:
            jobs = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        file_batch_date = infer_batch_date(json_path)
        normalized = [normalize_job(j, file_batch_date) for j in jobs]

        valid_rows = [j for j in normalized if j.get("job_id") and j.get("job_title")]
        n_ph = sum(1 for j in valid_rows if is_placeholder_title(j.get("job_title", "")))

        valid = {}
        for job in valid_rows:
            if is_placeholder_title(job.get("job_title", "")):
                continue
            jid = str(job["job_id"])
            prev = valid.get(jid)
            if prev is None or quality_score(job) >= quality_score(prev):
                valid[jid] = job

        passed = [j for j in valid.values() if quality_score(j) >= min_score]

        has_jd   = sum(1 for j in valid.values() if j.get("job_description"))
        has_skl  = sum(1 for j in valid.values() if j.get("main_skills"))
        jd_pct   = round(100 * has_jd  / len(valid)) if valid else 0
        skl_pct  = round(100 * has_skl / len(valid)) if valid else 0

        print(f"  {company:<35} {len(valid):>6} {len(passed):>6} {len(valid)-len(passed):>6} {n_ph:>4} {jd_pct:>4}% {skl_pct:>4}%")
        grand_total += len(valid); grand_pass += len(passed); grand_drop += len(valid) - len(passed)
        grand_ph += n_ph

    print(f"  {'─'*35} {'─'*6} {'─'*6} {'─'*6} {'─'*4}")
    print(f"  {'TOTAL':<35} {grand_total:>6} {grand_pass:>6} {grand_drop:>6} {grand_ph:>4}")
    print(f"{'─'*72}\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=f"Upsert scraped jobs into Supabase `{TABLE}`")
    parser.add_argument("--dry-run",    action="store_true", help="Quality report only — no Supabase writes")
    parser.add_argument("--min-score",  type=int, default=0, metavar="N",
                        help="Min quality score 0-3 (default 0). 0 = upload every non-placeholder valid row.")
    args = parser.parse_args()

    json_files = discover_json_files(OUTPUT_BASE)
    if not json_files:
        print(f"ERROR: No jobs.json files found under {OUTPUT_BASE}")
        sys.exit(1)
    print(f"Found {len(json_files)} company file(s) under {OUTPUT_BASE}")

    print_quality_report(json_files, args.min_score)

    if args.dry_run:
        print("Dry-run mode — no data written to Supabase.")
        return

    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not supabase_key:
        print(f"ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in {ENV_FILE}")
        sys.exit(1)

    supabase: Client = create_client(supabase_url, supabase_key)

    lifecycle_requested = _truthy_env("ENABLE_JOB_LIFECYCLE", "1")
    versions_requested = _truthy_env("ENABLE_JOB_VERSIONS", "1")
    lifecycle_enabled = lifecycle_requested and supports_lifecycle_columns(supabase)
    versions_enabled = versions_requested and supports_table(supabase, JOB_VERSIONS_TABLE)

    if lifecycle_requested and not lifecycle_enabled:
        print(f"WARNING: lifecycle columns not found on `{TABLE}`. Run scraper/sql/create_job_lifecycle.sql")
    if versions_requested and not versions_enabled:
        print(f"WARNING: version table `{JOB_VERSIONS_TABLE}` not found. Run scraper/sql/create_job_lifecycle.sql")

    batch: list[dict] = []
    total_uploaded = total_dropped = 0
    total_deactivated = 0
    version_events: list[dict] = []

    for json_path in json_files:
        company = json_path.parts[-4]
        try:
            jobs = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  SKIP {company}: could not read file — {e}")
            continue

        file_batch_date = infer_batch_date(json_path)
        clean, n_invalid, n_dupes, n_quality, n_placeholders = preprocess(jobs, args.min_score, file_batch_date)
        dropped = n_invalid + n_dupes + n_quality + n_placeholders
        total_dropped += dropped

        flags = []
        if n_invalid: flags.append(f"{n_invalid} invalid")
        if n_dupes:   flags.append(f"{n_dupes} dupes")
        if n_quality: flags.append(f"{n_quality} below gate")
        if n_placeholders: flags.append(f"{n_placeholders} placeholders")
        suffix = f"  [{', '.join(flags)} dropped]" if flags else ""
        print(f"  {company}: {len(clean)} jobs → {TABLE}{suffix}")

        existing_by_id: dict[str, dict] = {}
        active_ids: set[str] = set()
        current_ids: set[str] = {str(j.get("job_id")) for j in clean if j.get("job_id")}
        if lifecycle_enabled or versions_enabled:
            try:
                existing_by_id, active_ids = fetch_company_existing(supabase, company)
            except Exception as e:
                print(f"  WARN {company}: could not fetch existing rows for lifecycle/versioning — {e}")
                existing_by_id, active_ids = {}, set()

        if lifecycle_enabled:
            # Inactive after 1 miss: any currently-active job not present in this run
            # for the same company is marked inactive immediately.
            to_deactivate = sorted(active_ids - current_ids)
            if to_deactivate:
                deactivate_jobs(supabase, to_deactivate)
                total_deactivated += len(to_deactivate)
                if versions_enabled:
                    for jid in to_deactivate:
                        old = existing_by_id.get(jid, {})
                        old_payload = _meaningful_payload(old)
                        version_events.append({
                            "job_id": jid,
                            "company_name": company,
                            "batch_date": file_batch_date,
                            "change_type": "deactivate",
                            "changed_fields": [],
                            "old_fingerprint": old.get("change_fingerprint") or _fingerprint(old_payload),
                            "new_fingerprint": None,
                            "old_snapshot": old_payload,
                            "new_snapshot": None,
                        })

        for job in clean:
            row = build_row(job)
            jid = str(row["job_id"])

            if lifecycle_enabled:
                old = existing_by_id.get(jid)
                row["first_seen"] = int(old.get("first_seen")) if (old and old.get("first_seen")) else int(row["batch_date"])
                row["last_seen"] = int(row["batch_date"])
                row["is_active"] = True
                new_payload = _meaningful_payload(row)
                row["change_fingerprint"] = _fingerprint(new_payload)

            if versions_enabled:
                old = existing_by_id.get(jid)
                new_payload = _meaningful_payload(row)
                new_fp = _fingerprint(new_payload)
                if not old:
                    version_events.append({
                        "job_id": jid,
                        "company_name": company,
                        "batch_date": file_batch_date,
                        "change_type": "insert",
                        "changed_fields": list(_MEANINGFUL_FIELDS),
                        "old_fingerprint": None,
                        "new_fingerprint": new_fp,
                        "old_snapshot": None,
                        "new_snapshot": new_payload,
                    })
                else:
                    old_payload = _meaningful_payload(old)
                    old_fp = old.get("change_fingerprint") or _fingerprint(old_payload)
                    if old_fp != new_fp:
                        version_events.append({
                            "job_id": jid,
                            "company_name": company,
                            "batch_date": file_batch_date,
                            "change_type": "update",
                            "changed_fields": _changed_fields(old_payload, new_payload),
                            "old_fingerprint": old_fp,
                            "new_fingerprint": new_fp,
                            "old_snapshot": old_payload,
                            "new_snapshot": new_payload,
                        })

            errs = validate_row(row)
            if errs:
                print(f"  WARN schema violation for {row.get('job_id')}: {errs}")

            batch.append(row)
            total_uploaded += 1
            if len(batch) >= BATCH_SIZE:
                upsert_batch(supabase, batch)
                batch = []

    if batch:
        upsert_batch(supabase, batch)

    if version_events and versions_enabled:
        insert_version_events(supabase, version_events, table=JOB_VERSIONS_TABLE)

    print(f"\n✅  {total_uploaded} rows upserted into `{TABLE}`  ({total_dropped} dropped)")
    if lifecycle_enabled:
        print(f"Lifecycle: {total_deactivated} rows marked inactive (missed in latest company run)")
    if versions_enabled:
        print(f"Versions: {len(version_events)} job version event(s) written to `{JOB_VERSIONS_TABLE}`")

    LOGS_DIR.mkdir(exist_ok=True)
    summary_path = LOGS_DIR / f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    summary_path.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "table": TABLE,
        "output_base": str(OUTPUT_BASE),
        "companies": len(json_files),
        "uploaded": total_uploaded,
        "dropped": total_dropped,
        "deactivated": total_deactivated,
        "version_events": len(version_events),
        "lifecycle_enabled": lifecycle_enabled,
        "versions_enabled": versions_enabled,
    }, indent=2))
    print(f"Log → {summary_path}\n")


if __name__ == "__main__":
    main()
