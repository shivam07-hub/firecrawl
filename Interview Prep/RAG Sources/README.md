# RAG Sources

Private authoritative source corpus for interview preparation, skill questions,
learning pages, and original case studies.

## Pilot Skills

- Machine Learning
- Product Strategy
- Management Consulting
- Financial Accounting

## User Skill Exam Packs

Draft V1 level-exam packs for the next user-facing skills live in
`skill-exams/`:

- Frontend Engineering
- Data Analytics and SQL
- Python Programming
- Business Analytics and Statistics
- Backend and API System Design

Runtime publishing uses the live app ladder shape: 5 levels, 10 active MCQs per
level. Generate or validate the Supabase seed with `scripts/publish_skill_exams.py`.

## Operating Rules

- Import only files listed in `manifests/import-allowlist.txt`.
- Keep third-party originals private.
- Never import personal, identity, payroll, credential, or confidential files.
- Store provenance and checksums in `manifests/sources.jsonl`.
- Use Claude and Codex interactively for V1 authoring and cross-review.
- Do not add cloud-LLM API keys or unattended model integrations.
- Publish only original reviewed work from `case-studies/approved/`.

## Validation

```bash
python3 scripts/validate_corpus.py
python3 scripts/validate_skill_exams.py
python3 scripts/publish_skill_exams.py --check
python3 -m unittest discover -s tests -v
```
