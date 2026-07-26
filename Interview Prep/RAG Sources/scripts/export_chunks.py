#!/usr/bin/env python3
"""
export_chunks.py — Mentor retriever STEP 3 (rag-sources side).

Turns authored Myro Playbook markdown (playbooks/*.md) into the chunk JSONL that
the True_Yodha publish pipeline (publish_playbook.py, step 4) embeds and loads
into Supabase `playbook_chunks`.

Deterministic, stdlib-only, NO LLM and NO network — V1 authoring stays interactive
(AGENTS.md); this is only the mechanical chunk + serialise step.

One markdown `## ` heading == one self-contained, citable retrieval unit. The
chunk text is the heading plus its body so a retrieved passage reads on its own.

Chunk contract (one JSON object per line in derived/chunks/playbook_chunks.jsonl):
    {
      "chunk_id":      "<source_id>::<slug-of-heading>",  # stable across reruns
      "source_id":     "<frontmatter source_id>",
      "shelf":         "cv" | "interview" | "strategy" | "pedagogy",
      "source_title":  "<human title for citation>",
      "source_url":    "<canonical url or null>",
      "redistributable": true | false,
      "text":          "<heading>\\n\\n<body>",
      "tags":          ["...", "..."]
    }

The publish pipeline is idempotent on a content hash, so re-exporting unchanged
playbooks and re-running publish is a safe no-op.

Usage:
    python3 scripts/export_chunks.py                 # all playbooks/*.md
    python3 scripts/export_chunks.py --check         # validate only, write nothing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAYBOOKS_DIR = REPO_ROOT / "playbooks"
OUT_PATH = REPO_ROOT / "derived" / "chunks" / "playbook_chunks.jsonl"

VALID_SHELVES = {"cv", "interview", "strategy", "pedagogy"}
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HEADING_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)


class ExportError(Exception):
    pass


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "chunk"


def _parse_frontmatter(raw: str, path: Path) -> tuple[dict, str]:
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        raise ExportError(f"{path.name}: missing `---` frontmatter block")
    meta: dict = {}
    for line in m.group(1).splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    body = raw[m.end():]
    return meta, body


def _normalise_text(block: str) -> str:
    """Collapse a passage body to clean prose: drop comments, join wrapped lines
    within a paragraph, keep paragraph breaks."""
    block = _COMMENT_RE.sub("", block)
    paragraphs = [
        " ".join(part.split())
        for part in re.split(r"\n\s*\n", block)
        if part.strip()
    ]
    return "\n\n".join(paragraphs).strip()


def chunk_playbook(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(raw, path)

    source_id = meta.get("source_id")
    shelf = meta.get("shelf")
    title = meta.get("source_title")
    if not source_id:
        raise ExportError(f"{path.name}: frontmatter missing source_id")
    if shelf not in VALID_SHELVES:
        raise ExportError(f"{path.name}: shelf {shelf!r} not in {sorted(VALID_SHELVES)}")
    if not title:
        raise ExportError(f"{path.name}: frontmatter missing source_title")

    url = meta.get("source_url") or None
    redistributable = str(meta.get("redistributable", "")).lower() == "true"
    tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]

    body = _COMMENT_RE.sub("", body)
    headings = list(_HEADING_RE.finditer(body))
    if not headings:
        raise ExportError(f"{path.name}: no `## ` passage headings found")

    chunks: list[dict] = []
    seen_ids: set[str] = set()
    for i, h in enumerate(headings):
        heading = h.group(1).strip()
        start = h.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        passage_body = _normalise_text(body[start:end])
        if not passage_body:
            raise ExportError(f"{path.name}: passage {heading!r} has no body text")
        chunk_id = f"{source_id}::{_slug(heading)}"
        if chunk_id in seen_ids:
            raise ExportError(f"{path.name}: duplicate heading slug for {heading!r}")
        seen_ids.add(chunk_id)
        chunks.append({
            "chunk_id": chunk_id,
            "source_id": source_id,
            "shelf": shelf,
            "source_title": title,
            "source_url": url,
            "redistributable": redistributable,
            "text": f"{heading}\n\n{passage_body}",
            "tags": tags,
        })
    return chunks


def export_all(playbooks_dir: Path = PLAYBOOKS_DIR) -> list[dict]:
    files = sorted(playbooks_dir.glob("*.md"))
    if not files:
        raise ExportError(f"no playbooks found in {playbooks_dir}")
    all_chunks: list[dict] = []
    for path in files:
        all_chunks.extend(chunk_playbook(path))
    return all_chunks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Export authored playbooks to chunk JSONL.")
    ap.add_argument("--check", action="store_true", help="validate only; write nothing")
    args = ap.parse_args(argv)

    try:
        chunks = export_all()
    except ExportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    by_shelf: dict[str, int] = {}
    for c in chunks:
        by_shelf[c["shelf"]] = by_shelf.get(c["shelf"], 0) + 1

    if args.check:
        print(f"OK (check): {len(chunks)} chunks, shelves={by_shelf}")
        return 0

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Wrote {len(chunks)} chunks → {OUT_PATH.relative_to(REPO_ROOT)} (shelves={by_shelf})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
