from __future__ import annotations

import unittest

from scripts.publish_skill_exams import build_runtime_seed, render_seed_sql


class PublishSkillExamsTests(unittest.TestCase):
    def test_runtime_seed_matches_live_ladder_shape(self) -> None:
        seed = build_runtime_seed()

        self.assertEqual(len(seed.skills), 5)
        for skill in seed.skills:
            self.assertEqual(sorted(skill.questions_by_level), [1, 2, 3, 4, 5])
            for level, questions in skill.questions_by_level.items():
                self.assertEqual(
                    len(questions),
                    10,
                    f"{skill.display_name} level {level} must have 10 runtime MCQs",
                )
                for question in questions:
                    self.assertEqual(len(question.options), 4)
                    self.assertGreaterEqual(question.correct_index, 0)
                    self.assertLess(question.correct_index, 4)
                    self.assertEqual(question.options[question.correct_index], question.answer)

    def test_rendered_sql_is_idempotent(self) -> None:
        sql = render_seed_sql(build_runtime_seed())

        self.assertIn("insert into public.skills", sql)
        self.assertIn("on conflict (taxonomy_key) do update", sql)
        self.assertIn("insert into public.skill_questions", sql)
        self.assertIn("on conflict (skill_id, level, dedupe_hash) do update", sql)
        self.assertIn("Frontend Engineering", sql)
        self.assertIn("Backend and API System Design", sql)


if __name__ == "__main__":
    unittest.main()
