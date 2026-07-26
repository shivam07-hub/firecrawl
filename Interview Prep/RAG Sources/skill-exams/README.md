# Skill Exam Packs

Draft V1 user-facing exam packs for skills beyond the original pilot corpus.
Each pack lives in `skill-exams/packs/*.json` and uses the same four-level
progression:

1. Foundation: concepts and definitions.
2. Applied: problem solving and execution.
3. Interview: scenario judgment.
4. Advanced: tradeoffs, debugging, and capstone work.

The live app ladder has five visible levels and expects 10 active MCQs per
level. The runtime bridge is `scripts/publish_skill_exams.py`, which renders the
five new skills into that L1-L5 shape for `public.skills` and
`public.skill_questions`.

## Source Status

- `approved_private_sources`: grounded in files listed in `manifests/sources.jsonl`.
- `public_references_curated`: grounded in public bookmarks listed in
  `manifests/reference-links.jsonl`, not imported originals.
- `source_intake_required`: original draft structure exists, but approved sources
  must be added before the pack is treated as reviewed or authoritative.

## Validation

Run:

```bash
python3 scripts/validate_skill_exams.py
python3 scripts/publish_skill_exams.py --check
python3 -m unittest tests/test_skill_exam_packs.py -v
python3 -m unittest tests/test_publish_skill_exams.py -v
```
