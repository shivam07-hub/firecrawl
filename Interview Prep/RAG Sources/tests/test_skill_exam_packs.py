from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_skill_exams import validate_skill_exam_packs


REPO_ROOT = Path(__file__).resolve().parent.parent


def _question(skill_id: str, level: int, index: int = 1) -> dict:
    return {
        "id": f"{skill_id}-l{level}-q{index:03d}",
        "type": "mcq",
        "prompt": "Which option best matches the required behavior?",
        "choices": ["A clear correct option", "A plausible distractor", "An unrelated option"],
        "answer": "A clear correct option",
        "explanation": "The correct option satisfies the stated behavior.",
        "source_refs": [],
    }


def _pack(skill_id: str = "sample-skill") -> dict:
    return {
        "skill_id": skill_id,
        "skill_name": "Sample Skill",
        "status": "draft_pending_review",
        "source_status": "source_intake_required",
        "generation_attribution": {
            "generated_by": "Codex",
            "generated_at": "2026-06-25",
            "reviewed_by": None,
            "review_status": "draft_pending_review",
        },
        "source_ids": [],
        "reference_ids": [],
        "target_users": ["Interview prep users"],
        "core_topics": ["Foundations", "Applied practice"],
        "exam_levels": [
            {
                "level": level,
                "name": name,
                "description": description,
                "outcomes": [f"Outcome {level}"],
                "question_mix": {"mcq": 2, "short_answer": 1, "scenario": 1},
                "questions": [_question(skill_id, level, 1), _question(skill_id, level, 2)],
            }
            for level, name, description in [
                (1, "Foundation", "Concepts and definitions"),
                (2, "Applied", "Problem solving"),
                (3, "Interview", "Scenario judgment"),
                (4, "Advanced", "Tradeoffs and capstone work"),
            ]
        ],
    }


class SkillExamPackValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "skill-exams" / "packs").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_pack(self, pack: dict) -> None:
        path = self.root / "skill-exams" / "packs" / f"{pack['skill_id']}.json"
        path.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")

    def test_valid_pack_passes(self) -> None:
        self.write_pack(_pack())
        self.assertEqual(validate_skill_exam_packs(self.root), [])

    def test_requires_exactly_four_exam_levels(self) -> None:
        pack = _pack()
        pack["exam_levels"] = pack["exam_levels"][:3]
        self.write_pack(pack)
        errors = validate_skill_exam_packs(self.root)
        self.assertTrue(any("must define levels 1, 2, 3, and 4" in error for error in errors))

    def test_requires_generation_attribution(self) -> None:
        pack = _pack()
        pack.pop("generation_attribution")
        self.write_pack(pack)
        errors = validate_skill_exam_packs(self.root)
        self.assertTrue(any("missing fields: generation_attribution" in error for error in errors))

    def test_question_answer_must_match_a_choice_for_mcq(self) -> None:
        pack = _pack()
        pack["exam_levels"][0]["questions"][0]["answer"] = "Not one of the choices"
        self.write_pack(pack)
        errors = validate_skill_exam_packs(self.root)
        self.assertTrue(any("answer must match one of choices" in error for error in errors))

    def test_catalog_pack_paths_must_exist(self) -> None:
        self.write_pack(_pack("sample-skill"))
        catalog = {
            "version": "v1",
            "build_order": ["sample-skill", "missing-skill"],
            "skills": [
                {
                    "skill_id": "sample-skill",
                    "skill_name": "Sample Skill",
                    "pack_path": "skill-exams/packs/sample-skill.json",
                },
                {
                    "skill_id": "missing-skill",
                    "skill_name": "Missing Skill",
                    "pack_path": "skill-exams/packs/missing-skill.json",
                },
            ],
        }
        (self.root / "skill-exams" / "skills.json").write_text(
            json.dumps(catalog, indent=2) + "\n",
            encoding="utf-8",
        )
        errors = validate_skill_exam_packs(self.root)
        self.assertTrue(any("catalog pack_path does not exist" in error for error in errors))


class RealSkillExamPackTests(unittest.TestCase):
    def test_repo_skill_exam_packs_are_complete(self) -> None:
        errors = validate_skill_exam_packs(REPO_ROOT)
        self.assertEqual(errors, [])

        pack_dir = REPO_ROOT / "skill-exams" / "packs"
        packs = sorted(pack_dir.glob("*.json"))
        self.assertGreaterEqual(len(packs), 5)
        self.assertEqual(
            {path.stem for path in packs},
            {
                "backend-api-system-design",
                "business-analytics-statistics",
                "data-analytics-sql",
                "frontend-engineering",
                "python-programming",
            },
        )


if __name__ == "__main__":
    unittest.main()
