"""Unit tests for scripts/export_chunks.py (Mentor retriever step 3)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.export_chunks import ExportError, chunk_playbook, export_all  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

_GOOD = """---
source_id: test-pb
shelf: cv
source_title: Test Playbook
source_url:
redistributable: true
tags: a, b
---

<!-- a comment -->

## First rule

Body of the first rule
wrapped across lines.

## Second rule

Body two.
"""


def _write(tmp: Path, text: str) -> Path:
    p = tmp / "pb.md"
    p.write_text(text, encoding="utf-8")
    return p


class ChunkPlaybookTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._dir.name)

    def tearDown(self):
        self._dir.cleanup()

    def test_splits_one_chunk_per_heading(self):
        chunks = chunk_playbook(_write(self.tmp, _GOOD))
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["chunk_id"], "test-pb::first-rule")
        self.assertEqual(chunks[1]["chunk_id"], "test-pb::second-rule")

    def test_carries_citation_metadata(self):
        c = chunk_playbook(_write(self.tmp, _GOOD))[0]
        self.assertEqual(c["source_id"], "test-pb")
        self.assertEqual(c["shelf"], "cv")
        self.assertEqual(c["source_title"], "Test Playbook")
        self.assertIsNone(c["source_url"])          # empty frontmatter url -> null
        self.assertTrue(c["redistributable"])
        self.assertEqual(c["tags"], ["a", "b"])

    def test_text_joins_wrapped_lines_and_keeps_heading(self):
        c = chunk_playbook(_write(self.tmp, _GOOD))[0]
        self.assertTrue(c["text"].startswith("First rule\n\n"))
        self.assertIn("wrapped across lines.", c["text"])
        self.assertNotIn("\n", c["text"].split("\n\n", 1)[1])  # body is one line
        self.assertNotIn("comment", c["text"])                  # html comment stripped

    def test_bad_shelf_rejected(self):
        bad = _GOOD.replace("shelf: cv", "shelf: nonsense")
        with self.assertRaises(ExportError):
            chunk_playbook(_write(self.tmp, bad))

    def test_missing_frontmatter_rejected(self):
        with self.assertRaises(ExportError):
            chunk_playbook(_write(self.tmp, "## No frontmatter\n\nbody"))

    def test_no_headings_rejected(self):
        body = _GOOD.split("## First", 1)[0] + "Just prose, no headings.\n"
        with self.assertRaises(ExportError):
            chunk_playbook(_write(self.tmp, body))


class RealPlaybookTests(unittest.TestCase):
    def test_repo_playbooks_export_cleanly(self):
        chunks = export_all(REPO_ROOT / "playbooks")
        self.assertGreater(len(chunks), 0)
        ids = [c["chunk_id"] for c in chunks]
        self.assertEqual(len(ids), len(set(ids)), "chunk_ids must be unique")
        cv = [c for c in chunks if c["shelf"] == "cv"]
        self.assertGreaterEqual(len(cv), 5, "CV shelf needs real seed content for #32")

    def test_cv_rewrite_chunk_separates_final_rewrite_from_thinking(self):
        chunks = export_all(REPO_ROOT / "playbooks")
        text = "\n\n".join(c["text"].lower() for c in chunks if c["shelf"] == "cv")

        self.assertIn("final rewrite", text)
        self.assertIn("thinking", text)
        self.assertIn("accept", text)


if __name__ == "__main__":
    unittest.main()
