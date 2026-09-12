# Job feed publication

Source snapshots of company career listings, published into the live job feed.

## Language

**Source snapshot**:
The scrape-owned fields of a job from one complete run date — title, JD, location, apply URL, seniority, career band, and a first-fill extractive card summary.
_Avoid_: dump, scrape blob, raw JSON

**Source snapshot writer**:
The module that writes a **Source snapshot** and then closes the feed. Callers do not know PostgREST column-union or the retire RPC page size.
_Avoid_: importer internals, upsert helper, lifecycle hook

**Model-owned field**:
A column the open-weight enrichment pass upgrades (`job_summary` once filled, `role_domain`, enrichment hashes/status). A **Source snapshot** must not NULL or overwrite a non-empty one.
_Avoid_: enrichment payload, LLM columns

**Feed close**:
After a complete source write: presence evidence (seen / missing), drain of already-closed listings, and on a full-scope run the 30-day age backstop.
_Avoid_: delist, deactivate, retire (those are steps inside **Feed close**)

## Relationships

- A **Source snapshot writer** publishes one **Source snapshot** per company in the run, then performs **Feed close**
- A **Model-owned field** is never written by a **Source snapshot** except first-fill empty `job_summary`
- `--company` canaries skip the age step of **Feed close**; presence retire still drains

## Example dialogue

> **Dev:** "Can the importer omit `job_summary` on rows that already have an LLM card so we don't overwrite them?"
> **Domain expert:** "Omit is the **Source snapshot** policy. The **Source snapshot writer** must make omit safe: PostgREST treats a missing key in a mixed batch as NULL, which wipes a **Model-owned field**."

## Flagged ambiguities

- "retire" in logs means the `retire_closed_jobs` drain inside **Feed close**, not the 30-day age backstop and not `--deactivate-missing`
