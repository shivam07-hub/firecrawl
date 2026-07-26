from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


REQUIRED_FIELDS = {
    "source_id",
    "path",
    "title",
    "publisher",
    "source_url",
    "retrieved_at",
    "sha256",
    "mime_type",
    "bytes",
    "skills",
    "topics",
    "authority_tier",
    "rights",
    "redistributable",
    "review_status",
    "imported_from",
}

SENSITIVE_TOKENS = {
    "passport",
    "pan card",
    "payslip",
    "signature",
    "cheque",
    "joining letter",
    "personal cv",
    "formal picture",
    "uan",
}

BINARY_SUFFIXES = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
    ".zip",
    ".mp3",
    ".mp4",
}


def _read_allowlist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _read_lfs_suffixes(path: Path) -> set[str]:
    if not path.exists():
        return set()
    suffixes: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "filter=lfs" not in line:
            continue
        pattern = line.split()[0]
        if pattern.startswith("*."):
            suffixes.add(pattern[1:].lower())
    return suffixes


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_words(value: str) -> str:
    return " ".join(
        value.lower().replace("_", " ").replace("-", " ").replace("/", " ").split()
    )


def _load_records(path: Path, errors: list[str]) -> list[dict]:
    if not path.exists():
        errors.append(f"manifest missing: {path.relative_to(path.parent.parent)}")
        return []

    records: list[dict] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            value = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            errors.append(f"sources.jsonl:{line_number}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"sources.jsonl:{line_number}: record must be an object")
            continue
        records.append(value)
    return records


def validate_repository(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    records = _load_records(root / "manifests" / "sources.jsonl", errors)
    allowlist = _read_allowlist(root / "manifests" / "import-allowlist.txt")
    lfs_suffixes = _read_lfs_suffixes(root / ".gitattributes")
    seen_ids: set[str] = set()

    for index, record in enumerate(records, 1):
        label = f"record {index}"
        missing = sorted(REQUIRED_FIELDS - record.keys())
        if missing:
            errors.append(f"{label}: missing fields: {', '.join(missing)}")
            continue

        source_id = record["source_id"]
        if not isinstance(source_id, str) or not source_id.strip():
            errors.append(f"{label}: source_id must be a non-empty string")
        elif source_id in seen_ids:
            errors.append(f"{label}: duplicate source_id: {source_id}")
        else:
            seen_ids.add(source_id)

        imported_from = record["imported_from"]
        if not isinstance(imported_from, str) or imported_from not in allowlist:
            errors.append(f"{label}: imported_from is not allowlisted: {imported_from!r}")
        if isinstance(imported_from, str):
            normalized = _normalized_words(imported_from)
            if any(token in normalized for token in SENSITIVE_TOKENS):
                errors.append(f"{label}: sensitive import path rejected: {imported_from}")

        relative_path = record["path"]
        if not isinstance(relative_path, str) or not relative_path.startswith("sources/"):
            errors.append(f"{label}: path must be inside sources/: {relative_path!r}")
            continue

        source_file = (root / relative_path).resolve()
        try:
            source_file.relative_to(root / "sources")
        except ValueError:
            errors.append(f"{label}: path escapes sources/: {relative_path}")
            continue

        suffix = source_file.suffix.lower()
        if suffix in BINARY_SUFFIXES and suffix not in lfs_suffixes:
            errors.append(f"{label}: missing Git LFS rule for {suffix}")

        if not source_file.is_file():
            errors.append(f"{label}: source file missing: {relative_path}")
            continue

        expected_bytes = record["bytes"]
        if not isinstance(expected_bytes, int) or isinstance(expected_bytes, bool):
            errors.append(f"{label}: bytes must be an integer")
        elif source_file.stat().st_size != expected_bytes:
            errors.append(
                f"{label}: byte size mismatch for {relative_path}: "
                f"expected {expected_bytes}, got {source_file.stat().st_size}"
            )

        expected_sha = record["sha256"]
        if not isinstance(expected_sha, str) or _sha256(source_file) != expected_sha.lower():
            errors.append(f"{label}: sha256 mismatch for {relative_path}")

        if record["authority_tier"] not in {1, 2, 3, 4}:
            errors.append(f"{label}: authority_tier must be 1-4")
        if not isinstance(record["redistributable"], bool):
            errors.append(f"{label}: redistributable must be boolean")
        if not isinstance(record["skills"], list) or not record["skills"]:
            errors.append(f"{label}: skills must be a non-empty list")
        if not isinstance(record["topics"], list) or not record["topics"]:
            errors.append(f"{label}: topics must be a non-empty list")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    errors = validate_repository(root)
    if errors:
        print("Corpus validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Corpus validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
