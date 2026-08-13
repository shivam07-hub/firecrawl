# Backlog — carry into the next run

Written 2026-08-13, after the 2026-08-08 full India scrape (28,957 published) and
the dashboard data audit that followed it.

Every item below is either **measured** or **reproduced**. Where a number appears,
it came from a query against prod, not an estimate. Items are ordered by what
costs the user most, not by effort.

Two repos are involved. `FC` = `firecrawl_Supabase`, `TY` = `True_Yodha`.

---

## DONE in this session (context, not work)

| Fix | Where | State |
|---|---|---|
| Resolver dropped provenance when the model didn't run | FC `source_matching_facts.py` | committed `5e803b040` |
| `claim_job_embeddings` defeated its partial index (1499ms → 5ms) | FC `sql/fix_job_embedding_claim_index_usage.sql` | applied to prod + committed |
| Every Data Scientist mis-banded out of the technical keep-set | FC `job_career_band.py` | committed |
| Skill-floor count detoasted ~386 MB per call | TY `20260808_skill_floor_count_stops_detoasting.sql` | applied + committed |
| Resolver CSV didn't flatten `locations` | FC `source_matching_facts.py` | committed |
| Two local-inference workers could collide / model TTL expiry stalled drains | FC `lm_worker_lock.py`, `daily_cycle`, `enrichment_worker` | committed |
| Skill-demand snapshot 22 days stale | prod refresh run — 19 cities / 374 rows | data fixed, **trigger not** → see #2 |
| `Requisition` etc. surviving the demand guards | TY `20260813_skill_demand_skill_deny.sql` | applied to prod |

---

## P0 — the pipeline cannot run unattended

### 1. ✅ DONE — `daily_cycle` survives a run crossing midnight
**Evidence.** The 2026-08-07 run scraped 23:28 → 08:26 and exited 2 at the publish
step: `No complete jobs.json files found for source-only run date 20260807`.

**Cause.** `daily_poll` publishes every date a run spanned, but
`csv_importer._find_json_files` only considers each company's **newest** date
folder. A company that scrapes across midnight leaves an earlier-date folder that
can never be selected again.

**Also.** The pre-midnight folder has no `jobs.complete` marker, so its rows are
stranded until that company is next scraped — 1,380 Accenture jobs on 2026-08-08.

**Acceptance.** A run started before midnight completes all stages in one command,
and no folder from it is left unpublished. Decide explicitly whether a
markerless partial folder should ever publish (current contract says no — that is
defensible, but then the scrape must not split a company across two folders).

**Resolution (2026-08-13).** `daily_poll` now pins one logical run date into the
scrape command. Page flushes, the final completion marker, source-fact resolution,
and publication all use that date. `csv_importer` also selects an explicitly
requested date rather than first discarding everything except each company's
newest folder. Markerless partial folders remain unpublished. Focused regression
coverage and the full `scraper/tests` suite pass.

---

### 2. ✅ DONE — skill-demand / analytics refresh is durable and independently retryable
**Evidence.** Every publish logged
`Intel refresh failed (…/jobs/analytics/refresh-snapshot): Read timed out (read timeout=30)`.
The snapshot then sat at 2026-07-21 for 22 days while the UI kept rendering it.

**Three separate faults.**
1. The endpoint does analytics + skill demand + search index **synchronously inside
   the request**, and the scraper's client gives it 30s.
2. Skill demand is coupled to the analytics dirty-guard — it recomputes only when
   `summary["refreshed"]` is true. Once analytics is fresh and skill demand is not,
   nothing ever repairs it. That is the state prod was in.
3. The scraper's call is fire-and-forget (correctly — it must not fail an import),
   so nobody is paged when it fails every single time.

**Acceptance.** Freshness is enforced, not hoped for: the refresh runs
asynchronously or on its own schedule, each snapshot's staleness is observable,
and the panel refuses to render a snapshot older than N days rather than showing
a stale number with an apology label.

**Implemented 2026-08-13.** The scraper now sends `force=true`, accepts the
backend's asynchronous `202`, and waits at most 5 seconds. The backend persists
one refresh request before acknowledging, then claims analytics, skill demand,
and search independently; one failure is recorded without gating either sibling.
Prod now has per-product status/lease/error state plus staggered hourly SQL retry
crons for skill demand and global search. The existing daily analytics HTTP cron
was deliberately left unchanged until `Develop` is promoted. Skill-demand reads
suppress snapshots older than 48 hours while preserving `computed_at` for
operational diagnosis. Live ACL verification denies both API roles and permits
only `service_role`; Supabase advisors are clean for this subsystem. Focused
backend contracts, the full 326-test scraper suite, and transactional live RPC
smoke coverage pass.

---

### 3. `new_jobs_count` reports a torn, partial batch — and freezes it
**Evidence.** Dashboard showed **4,095 new roles**; the correct answer for that
account was **12,108**.

- `last_match_run_at` = 2026-07-28 12:37:59 (a genuine search).
- Active jobs with `ingested_at >` that: **12,108**.
- PostgREST `count=exact` returns 12,108 correctly — the primitive is fine.
- The 4,095 came from `user_notifications` id **619**, written 2026-08-10 11:18:52.
  At that instant 12,108 qualifying rows already existed and were active, and **0**
  landed afterwards — so it was wrong when written, not merely stale.
- 4,095 corresponds exactly to a baseline of **04:09–04:10 UTC on 2026-08-08** —
  mid-publish, when only 4,095 of that batch's 12,101 rows had been inserted.

**Cause.** The publish takes ~15 minutes to insert ~12k rows and nothing marks a
batch complete, so any consumer reading during that window sees a partial corpus.
Here the partial count was then persisted into a durable notification the UI
still renders days later.

**Acceptance.** A batch is atomic to readers, or counts are computed only from
completed batches. Separately: a persisted count must be re-derived or
invalidated rather than trusted indefinitely.

**Open question for the next session.** Exactly which caller computed it at
04:09 UTC. This account has no `user_job_matches` row on 2026-08-08 (nearest are
Aug 7 20:07 and Aug 10 11:19) and `last_match_run_at` is July 28, so neither
documented baseline path explains it. Worth 30 minutes with backend logs.

---

## P1 — data the user sees is wrong or missing

### 4. ~13% of every run is withheld and never reaches a user
4,289 of 33,246 on this run. Rule expansion recovered only **+242 of 4,501** —
the remainder either name no function (`IN-Expert`, `Fixed Term Appointment`,
bare ladder grades) or hide it behind an employer-private prefix
(`CBG:`, `WBCG:`, `DAS/MUM/…`).

Generic rules cannot reach these. The options are an employer-prefix map
(rejected once as too company-specific and high-maintenance), accepting the loss,
or a different resolution strategy entirely. **This needs a decision, not more
regex.** One in eight scraped jobs is currently invisible.

### 5. 54 companies failed to scrape
Includes a cluster that looks like a real route regression, not noise:
**six PCSX/Eightfold tenants now returning 403** — Qualcomm, NVIDIA, PayPal,
Infineon, Lam Research, Micron. Also Greenhouse Tekion 404, Lever Dream11 404,
Zwayam Persistent 503. The Docker-dependent Firecrawl portals failed only because
Docker was off, which is expected.

Run `diagnose.py --probe` and triage the 403 cluster first — six tenants failing
the same way on the same day is one cause, not six.

### 6. Generic soft skills dominate the demand rail — product decision
After the refresh, `Communication` ranks #1 in Gurugram (117 roles, 30 employers)
and appears in **15 cities / 4,157 roles**; `Collaboration` in 9 cities.

These are real extractions, not artefacts, so the denylist deliberately does not
touch them — whether "Communication" is useful market intelligence for a job
seeker is a judgement call. If the answer is no, the fix is a soft-skill class in
the taxonomy, not individual denies.

---

## P2 — dashboard design (from the 2026-08-12 critique)

### 7. Four scoring systems in one viewport
Myro Score 30, Worth It 76, Citibank 84%, "1/5 skills" — four scales, four
meanings, no stated relationship. Directly against the standardization-as-trust
principle. **Pick one, express it identically everywhere, delete the rest.**

### 8. The score removes status instead of conferring it
The page opens by telling a job seeker they are a **30 · Emerging**, with 40
labelled "Developing". That is a report card. If a human is going to be scored,
the number has to be something they would screenshot.

### 9. Ranking has no resolution
Both visible cards scored exactly **76**. Two significant figures of precision
the model does not have.

### 10. `× MoEngage` is listed as a missing skill on a MoEngage job
Company name leaking into the skill taxonomy — the same class of bug as
`Requisition`. Contradicts the principle that Myro indexes identifiable employers
and explains what *they* want. Check whether company names are enterable as
skills at all.

### 11. Smaller items
- `Practice Business To Bu…` — the most prominent CTA in the left rail is truncated.
- "Your next moves" ranks *practice* above an 84% match. Order by expected value.
- Job title `Senior Customer Success Manager -Gurugram` carries the location, and
  so does the location chip, and so does the filter pill — three statements of one
  fact, plus a missing space after the hyphen from dirty source text.
- "Company Signals" renders as an empty/blurred panel with no empty state.
- `Run Myro Search · **Free**` — saying "free" tells the user there is a price.

### 12. The visual identity is the AI default
Near-black + single acid-teal accent, one geometric sans doing display, body and
data. Nothing in the palette or type comes from hiring, careers, or the Indian job
market. The most differentiated fact on the page — **`Verified 1d ago`**, live
listing verification almost nobody does — is set in the smallest, dimmest type on
the card. That is the asset worth building an identity around.

---

## P3 — infrastructure

### 13. Supabase is materially degraded
A trivial REST root request measured **10.0s / 1.3s / 2.6s**. The second publish
took **3,127s vs 872s** for the first, and every worker hit repeated connection
resets and DNS failures. All three workers had to be run under retry loops.

`jobs` is ~611 MB. Check the instance size against the corpus, and whether the
8s `statement_timeout` inherited from `authenticator` is right for batch workers
(it is what broke skill-floor, item DONE above).

### 14. Two migrations applied to prod, one uncommitted
`TY/database/migrations/20260813_skill_demand_skill_deny.sql` is applied to prod
and written to disk but **not committed**. True_Yodha work belongs on `Develop`.
