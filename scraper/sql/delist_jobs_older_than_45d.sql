-- Age-based delisting — set is_active=false for stale jobs (last_seen > 45 days).
--
-- Scraper = discovery; community = freshness. This adds an AGE backstop: any job
-- not seen in the last 45 days is delisted from the live feed, regardless of
-- whether its company appeared in the latest run. last_seen is an integer
-- YYYYMMDD (batch_date format).
--
-- SAFETY: run the PREVIEW first and sanity-check the count before the UPDATE.
-- Reactivation is possible (a future scrape sets last_seen + is_active on insert
-- only; an existing stale row stays inactive unless manually flipped), so treat
-- this as a deliberate, periodic operation.
--
-- Run manually in the Supabase SQL editor (project gipvxuugajkugntwkeiz).

-- ── 1. PREVIEW: how many active jobs would be delisted ──────────────────────────
WITH cutoff AS (SELECT to_char(current_date - 45, 'YYYYMMDD')::int AS d)
SELECT
    (SELECT d FROM cutoff)                                   AS cutoff_yyyymmdd,
    count(*) FILTER (WHERE is_active)                        AS active_total,
    count(*) FILTER (WHERE is_active
                     AND last_seen < (SELECT d FROM cutoff)) AS would_delist
FROM public.jobs;

-- Per-company breakdown of what would be delisted (review before committing):
WITH cutoff AS (SELECT to_char(current_date - 45, 'YYYYMMDD')::int AS d)
SELECT company_name, count(*) AS delist_count
FROM public.jobs
WHERE is_active AND last_seen < (SELECT d FROM cutoff)
GROUP BY company_name
ORDER BY delist_count DESC;

-- ── 2. APPLY: uncomment to delist (run only after reviewing the preview) ─────────
-- WITH cutoff AS (SELECT to_char(current_date - 45, 'YYYYMMDD')::int AS d)
-- UPDATE public.jobs
-- SET is_active = false
-- WHERE is_active AND last_seen < (SELECT d FROM cutoff);
