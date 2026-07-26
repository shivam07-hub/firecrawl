from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_corpus import validate_repository


class ValidateCorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "manifests").mkdir()
        (self.root / "sources" / "machine-learning").mkdir(parents=True)
        (self.root / ".gitattributes").write_text(
            "*.pdf filter=lfs diff=lfs merge=lfs -text\n",
            encoding="utf-8",
        )
        self.source_path = self.root / "sources" / "machine-learning" / "seed.pdf"
        self.source_path.write_bytes(b"approved source")
        self.imported_from = "Study Material/seed.pdf"
        (self.root / "manifests" / "import-allowlist.txt").write_text(
            f"{self.imported_from}\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def record(self, **overrides):
        data = {
            "source_id": "ml-seed",
            "path": "sources/machine-learning/seed.pdf",
            "title": "Machine Learning Seed",
            "publisher": "Example University",
            "source_url": "https://example.edu/seed",
            "retrieved_at": "2026-06-13",
            "sha256": hashlib.sha256(b"approved source").hexdigest(),
            "mime_type": "application/pdf",
            "bytes": len(b"approved source"),
            "skills": ["Machine Learning"],
            "topics": ["Regression"],
            "authority_tier": 2,
            "rights": "private_reference_only",
            "redistributable": False,
            "review_status": "approved_private",
            "imported_from": self.imported_from,
        }
        data.update(overrides)
        return data

    def write_manifest(self, *records) -> None:
        content = "".join(json.dumps(record) + "\n" for record in records)
        (self.root / "manifests" / "sources.jsonl").write_text(
            content,
            encoding="utf-8",
        )

    def test_valid_manifest_passes(self) -> None:
        self.write_manifest(self.record())
        self.assertEqual(validate_repository(self.root), [])

    def test_duplicate_source_id_fails(self) -> None:
        self.write_manifest(self.record(), self.record(path="sources/machine-learning/other.pdf"))
        errors = validate_repository(self.root)
        self.assertTrue(any("duplicate source_id" in error for error in errors))

    def test_missing_file_fails(self) -> None:
        self.write_manifest(self.record(path="sources/machine-learning/missing.pdf"))
        errors = validate_repository(self.root)
        self.assertTrue(any("source file missing" in error for error in errors))

    def test_checksum_mismatch_fails(self) -> None:
        self.write_manifest(self.record(sha256="0" * 64))
        errors = validate_repository(self.root)
        self.assertTrue(any("sha256 mismatch" in error for error in errors))

    def test_source_must_be_allowlisted(self) -> None:
        (self.root / "manifests" / "import-allowlist.txt").write_text("", encoding="utf-8")
        self.write_manifest(self.record())
        errors = validate_repository(self.root)
        self.assertTrue(any("not allowlisted" in error for error in errors))

    def test_sensitive_import_path_fails(self) -> None:
        sensitive = "Personal CVs/Shivam CV.pdf"
        (self.root / "manifests" / "import-allowlist.txt").write_text(
            f"{sensitive}\n",
            encoding="utf-8",
        )
        self.write_manifest(self.record(imported_from=sensitive))
        errors = validate_repository(self.root)
        self.assertTrue(any("sensitive import path" in error for error in errors))

    def test_binary_extension_requires_lfs_rule(self) -> None:
        (self.root / ".gitattributes").write_text("", encoding="utf-8")
        self.write_manifest(self.record())
        errors = validate_repository(self.root)
        self.assertTrue(any("missing Git LFS rule" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
