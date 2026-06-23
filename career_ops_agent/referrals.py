"""
Referral target ranker — compliant, personalised, no scraping.

Input: the candidate's OWN LinkedIn connections export
(Settings → Data Privacy → Get a copy of your data → Connections → Connections.csv).
That file is the member's legal right to export; we never scrape LinkedIn.

Logic: match each connection's current Company against the companies that have
open roles in the firecrawl Supabase `jobs` set, then rank by referral value
(at-company + recruiter/TA title + seniority + function overlap + reachable email).
Output: per-company ranked referrers + a personalised ask draft per top contact.

LinkedIn Connections.csv has a 2-3 line "Notes:" preamble before the real header:
    First Name,Last Name,URL,Email Address,Company,Position,Connected On
"""
from __future__ import annotations

import csv
import io
from typing import Any

# ── company-name normalization ───────────────────────────────────────────────
_STRIP_TOKENS = {
    "pvt", "private", "ltd", "limited", "llp", "inc", "incorporated", "corp",
    "corporation", "co", "company", "technologies", "technology", "tech",
    "solutions", "services", "consulting", "india", "global", "group", "the",
    "and", "&", "gcc", "labs", "systems", "international",
}


# Canonical aliases — both sides normalize to the same key.
_ALIASES = {
    "boston consulting": "bcg", "bcg": "bcg",
    "ernst young": "ey", "ey": "ey",
    "pricewaterhousecoopers": "pwc", "pwc": "pwc",
    "mckinsey": "mckinsey",
    "deloitte": "deloitte", "monitor deloitte": "deloitte",
    "publicis sapient": "publicis", "sapient": "publicis",
    "tata consultancy": "tcs", "tcs": "tcs",
    "hcl": "hcl",
}


def norm_company(name: str | None) -> str:
    if not name:
        return ""
    s = name.lower()
    for ch in ".,/()-_":
        s = s.replace(ch, " ")
    cleaned = " ".join(s.split())
    # alias check before token-stripping (so "boston consulting group" → bcg)
    for phrase, canon in _ALIASES.items():
        if phrase in cleaned:
            return canon
    toks = [t for t in cleaned.split() if t and t not in _STRIP_TOKENS]
    base = " ".join(toks)
    return _ALIASES.get(base, base)


# ── title signals ─────────────────────────────────────────────────────────────
_RECRUITER_KW = ("talent", "recruit", "hiring", "staffing", "acquisition",
                 "people", "hr ", "human resources", "ta ", "sourcer")
_SENIOR_KW = ("head", "director", "vp", "vice president", "principal", "partner",
              "lead", "manager", "chief", "founder", "president", "senior")
# Function overlap with the candidate's lanes (edit per profile)
_FUNCTION_KW = ("gtm", "go-to-market", "business development", "sales", "strategy",
                "consult", "analytics", "data", "product", "growth", "marketing",
                "solution", "pre-sales", "presales", "advisory", "transformation")


def _has(text: str, kws) -> bool:
    t = f" {text.lower()} "
    return any(k in t for k in kws)


def load_connections(path) -> list[dict[str, str]]:
    """Parse a LinkedIn Connections.csv, skipping the Notes preamble."""
    raw = open(path, "r", encoding="utf-8-sig").read()
    lines = raw.splitlines()
    # find the header row (starts with 'First Name')
    start = 0
    for i, ln in enumerate(lines):
        if ln.lower().startswith("first name"):
            start = i
            break
    reader = csv.DictReader(io.StringIO("\n".join(lines[start:])))
    out = []
    for row in reader:
        out.append({(k or "").strip(): (v or "").strip() for k, v in row.items()})
    return out


def score_connection(conn: dict[str, str], in_target: bool) -> tuple[int, list[str]]:
    pos = conn.get("Position", "")
    score, why = 0, []
    if in_target:
        score += 20
        why.append("at target company")
    if _has(pos, _RECRUITER_KW):
        score += 9
        why.append("recruiter/TA")
    if _has(pos, _SENIOR_KW):
        score += 5
        why.append("senior")
    if _has(pos, _FUNCTION_KW):
        score += 5
        why.append("function overlap")
    if conn.get("Email Address"):
        score += 3
        why.append("email available")
    return score, why


def rank_referrers(
    connections: list[dict[str, str]],
    jobs: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Return {target_company_display: [ranked connection dicts]}."""
    # build target-company index: normalized -> display name (+ a sample job)
    target: dict[str, dict[str, Any]] = {}
    for j in jobs:
        n = norm_company(j.get("company_name"))
        if not n:
            continue
        if n not in target:
            target[n] = {"display": j.get("company_name"), "jobs": []}
        target[n]["jobs"].append(j)

    by_company: dict[str, list[dict[str, Any]]] = {}
    for conn in connections:
        cn = norm_company(conn.get("Company"))
        if not cn:
            continue
        # match on normalized equality or token containment
        hit = None
        if cn in target:
            hit = cn
        else:
            for tn in target:
                if tn and (tn in cn or cn in tn) and len(tn) > 3:
                    hit = tn
                    break
        if not hit:
            continue
        sc, why = score_connection(conn, in_target=True)
        disp = target[hit]["display"]
        sample = target[hit]["jobs"][0]
        by_company.setdefault(disp, []).append({
            "name": f"{conn.get('First Name','')} {conn.get('Last Name','')}".strip(),
            "position": conn.get("Position", ""),
            "url": conn.get("URL", ""),
            "email": conn.get("Email Address", ""),
            "score": sc,
            "why": why,
            "sample_job": sample.get("job_title"),
            "sample_apply_url": sample.get("apply_url"),
        })
    for disp in by_company:
        by_company[disp].sort(key=lambda c: -c["score"])
    return dict(sorted(by_company.items(), key=lambda kv: -max(c["score"] for c in kv[1])))


def template_ask(conn: dict[str, Any], company: str, profile: dict[str, Any]) -> str:
    """Deterministic referral-ask draft (used when no LLM key)."""
    first = (conn["name"].split() or ["there"])[0]
    return (
        f"Hi {first}, hope you're doing well! I'm exploring {company} — I saw the "
        f"\"{conn['sample_job']}\" role and it lines up closely with my background "
        f"({profile.get('superpower','').strip().splitlines()[0] if profile.get('superpower') else 'GTM + Data & AI'}). "
        f"Would you be open to a quick chat or a referral if it's a fit? Happy to send my CV. "
        f"Role: {conn['sample_apply_url']}"
    )
