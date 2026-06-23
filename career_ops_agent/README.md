# Career Ops Agent

A lean, permanent agent that runs the **Career Ops** brain over the jobs that the
`firecrawl_Supabase` pipeline has scraped + enriched into Supabase, and ranks them
against a candidate's CV. Built for personal job-hunting ("survival mode").

It is the engine half of the `career-ops-modified_frontend` Next.js app — the
evaluation/tailoring prompts were ported from that app's `src/lib/claude.ts`, but
this agent talks **directly to the real firecrawl Supabase schema** (`job_title`,
`company_name`, `job_description`, `role_domain`, `main_skills`, …) instead of the
frontend's separate schema, and adds a free deterministic prefilter so the LLM only
deep-evaluates a focused shortlist.

## Why a new sub-repo (not building on the frontend)

| | This agent | The Next.js frontend |
|---|---|---|
| Data source | live firecrawl Supabase schema | a *different* schema (`jobs.title`, `profiles`, `evaluations`, `user_job_scores`) that doesn't exist in your project |
| Weight | one file of `requests` calls | auth, quota, tiers, Railway PDF, RLS |
| Time to first ranked list | minutes | days of schema-mapping |

So: the frontend stays as the eventual **UI**; this agent is the **engine**. They
can be wired together later by pointing the frontend at the same tables.

## The journey it reuses

```
KNOWN_PORTALS.md → scraper/main.py + providers/ → enricher.py (LM Studio) → csv_importer.py → Supabase
                                                                                                  │
                                                                            career_ops_agent ◄────┘
                          prefilter (free)  →  OpenRouter deep eval  →  ranked report + tailored CV
```

## Setup

```bash
cd career_ops_agent
cp .env.example .env          # add your OPENROUTER_API_KEY
# Supabase creds are auto-read from ../scraper/.env — nothing to copy.
```

Edit `cv.md` (your CV in markdown) and `profile.yaml` (targets, location, deal-breakers).
Shivam's are pre-filled.

## Run

```bash
# 1. Free heuristic shortlist — no API key, no spend. Validates the wiring.
python agent.py --dry-run --top 30

# 2. Deep-evaluate the shortlist with the Career Ops brain (you supply the key).
python agent.py --rank --top 20 --api-key sk-or-... --model anthropic/claude-sonnet-4

# Restrict to one scrape batch (e.g. the NCR gold set loaded 2026-05-27):
python agent.py --rank --batch-date 20260527 --top 25

# Build application packets for the top jobs (tailored CV + PDF + brief each):
python agent.py --tailor-top --top 30 --api-key sk-or-...

# Tailor your CV for a specific job:
python agent.py --tailor <job_id> --api-key sk-or-...

# Rank YOUR LinkedIn connections as referral targets for the job set:
python agent.py --referrals --connections ~/Downloads/Connections.csv
# (add --api-key for LLM-drafted asks instead of templates)
```

### LinkedIn referrals — how & why this shape

LinkedIn's official API has **no people-search** for third-party apps; the Myro
`w_member_social` / `r_profile_basicinfo` scopes are self-only (post as you, read your
own profile). So we **cannot** search "recruiters at company X" via API, and scraping
violates LinkedIn ToS. Instead `--referrals` ranks **your own exported connections**
(a member's legal data-export right) against the companies that have open roles, scoring
each by: at-target-company + recruiter/TA title + seniority + function overlap + reachable
email. Export: LinkedIn → Settings → Data Privacy → *Get a copy of your data* →
Connections → `Connections.csv`.

Outputs land in `out/` (git-ignored):
- `shortlist_<ts>.csv` — heuristic prefilter
- `ranked_<ts>.md / .csv / .json` — full Career Ops evaluation, sorted by score
- `cv_<company>_<ts>.md` — tailored CV

## Files

| File | Role |
|---|---|
| `config.py` | env loading (local `.env` → `../scraper/.env`) |
| `supabase_client.py` | reads `jobs` via PostgREST, requests-only |
| `prefilter.py` | free deterministic ranker → shortlist; profile-tunable weights |
| `prompts.py` | Career Ops system + tailoring prompts (ported from `claude.ts`) |
| `openrouter_client.py` | OpenAI-compatible chat over OpenRouter |
| `agent.py` | CLI orchestrator: `--dry-run` / `--rank` / `--tailor` |
| `cv.md`, `profile.yaml` | the candidate inputs — edit these |

## Notes
- Only dep is `requests` (already in the scraper env).
- The OpenRouter key is never committed; pass it per run or keep it in the git-ignored `.env`.
- `--dry-run` costs nothing and works offline-ish (only needs Supabase) — use it to sanity-check before spending on LLM calls.
