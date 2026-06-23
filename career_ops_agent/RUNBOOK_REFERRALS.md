# Runbook — Referral Outreach (run when LinkedIn export arrives)

LinkedIn emails the data export in ~24h. Follow these steps once you have it.

## 1. Get `Connections.csv` out of the export
- Open the LinkedIn email → **Download** → you get a `.zip` (e.g. `Basic_LinkedInDataExport_….zip`).
- Unzip it. Inside, find **`Connections.csv`**.
- Note its path, e.g. `~/Downloads/Basic_LinkedInDataExport_2026-05-28/Connections.csv`.
- Sanity: the file's first ~3 lines are a "Notes:" preamble, then a header
  `First Name,Last Name,URL,Email Address,Company,Position,Connected On`. The agent handles the preamble.
  (Some rows have a blank Email Address — normal; those go via LinkedIn DM.)

## 2. (Optional) set the OpenRouter key for tailored ask drafts
```bash
cd /Users/incognito/firecrawl_Supabase/career_ops_agent
# either edit .env (OPENROUTER_API_KEY=sk-or-...) once, or pass --api-key per run.
# Without a key you still get template ask drafts.
```

## 3. Rank your connections as referrers
```bash
python3 agent.py --referrals \
  --connections ~/Downloads/<your-export-folder>/Connections.csv \
  --batch-date 20260527 \
  --per-company 3 \
  --api-key sk-or-...        # optional; omit for template asks
```
Output → `out/referrals_<ts>.md` (+ `.csv`):
per target company → ranked connections (recruiter/TA, senior, function overlap, email) + a
ready referral-ask draft citing a real open role + apply_url.

## 4. Build the CV you'll attach (so the ask has substance)
For the specific role a referrer can refer you to:
```bash
python3 agent.py --tailor <job_id> --api-key sk-or-...        # one job → out/cv_<company>_<ts>.md
# or build packets for the whole shortlist at once:
python3 agent.py --tailor-top --top 20 --api-key sk-or-...    # cv.pdf + brief.md per job
```
`job_id` is in the referrals report (and in `ranked_*.csv` if you ran `--rank`).

## 5. Send (manual, compliant — no automation)
For each top referrer in the report:
- **Has email →** email them: paste the ask draft, attach the tailored `cv.pdf`.
- **No email →** open their LinkedIn `URL`, send the ask draft as a connection note / DM (no attachment;
  offer to send CV on reply).
- Personalise the first line — never blast the identical template. One ask per person.

## 6. Track + follow up
- Log who you contacted, channel, date, response (the `referrals_*.csv` is a good base — add columns).
- No reply in ~5 business days → one polite follow-up, then stop.
- This is the manual version of Loop G outcome capture (see
  `True_Yodha/docs/FEATURE_LOOP_REGISTRY.md`). Response patterns tell you which angle converts.

## Notes / limits
- Only ranks people **already in your network**. New referrers at a company where you have no
  connection need manual LinkedIn search — not built (no compliant automation exists).
- Company matching uses aliases (BCG↔Boston Consulting Group, EY↔Ernst & Young, …) — if a known
  contact's employer doesn't match, add the alias in `referrals.py::_ALIASES`.
- Re-run anytime against a different `--batch-date` as new jobs land in Supabase.
