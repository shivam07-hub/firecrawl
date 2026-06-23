"""
Cheap, deterministic first-pass ranker. No LLM, no cost.

Purpose: cut the full job set down to the top-N most plausible matches so the
LLM only deep-evaluates a focused shortlist. Mirrors the heuristic Codex used
in ncr_gold_top_jobs_*.csv but with explicit profile-driven weights.
"""
from __future__ import annotations

from typing import Any

# Tunable weights — edit freely; this is the candidate's "lens".
PREFERRED_DOMAINS = {
    "Strategy & Consulting": 12,
    "Sales & Marketing": 9,
    "Data & Analytics": 9,
    "Product Management": 8,
    "Operations": 5,
    "Finance": 4,
    "Research & Science": 4,
}
TITLE_BONUS = {
    "gtm": 8, "go-to-market": 8, "business development": 7, "pre-sales": 8,
    "presales": 8, "solution": 6, "consult": 6, "strategy": 7, "growth": 6,
    "analyst": 4, "analytics": 5, "product": 5, "transformation": 5,
    "client": 4, "account": 4, "advisory": 5, "data & ai": 6, "ai": 3,
}
TITLE_PENALTY = {
    "tax": -10, "payroll": -10, "audit": -7, "statutory": -7,
    "embedded": -6, "firmware": -8, "qa engineer": -5, "sdet": -6,
    "devops": -5, "sre": -5, "network engineer": -6, "security engineer": -5,
    "intern": -3, "graduate trainee": -3,
}
# Skills pulled from Shivam's CV; overlap with job main_skills earns points.
CV_SKILLS = {
    "go-to-market", "gtm", "business development", "sales", "marketing",
    "digital marketing", "consulting", "strategy", "data", "analytics",
    "python", "sql", "snowflake", "tableau", "google analytics", "excel",
    "dashboard", "ai", "data & ai", "product", "growth", "pipeline",
    "stakeholder", "presales", "solution", "transformation", "b2b",
}
PREFERRED_CITIES = {"noida", "gurugram", "gurgaon", "delhi", "new delhi", "ncr"}
OK_CITIES = {"hyderabad", "bengaluru", "bangalore", "mumbai", "pune", "chennai"}


def _text(job: dict[str, Any], *keys: str) -> str:
    return " ".join(str(job.get(k) or "") for k in keys).lower()


def score_job(job: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    cues: list[str] = []

    domain = job.get("role_domain") or ""
    if domain in PREFERRED_DOMAINS:
        score += PREFERRED_DOMAINS[domain]
        cues.append(domain)

    title = (job.get("job_title") or "").lower()
    for kw, pts in TITLE_BONUS.items():
        if kw in title:
            score += pts
            cues.append(kw)
    for kw, pts in TITLE_PENALTY.items():
        if kw in title:
            score += pts  # negative

    blob = _text(job, "main_skills", "side_skills", "job_description")
    overlap = [s for s in CV_SKILLS if s in blob]
    score += min(len(overlap), 8) * 1.5
    cues.extend(sorted(set(overlap))[:5])

    loc = _text(job, "location", "location_city")
    if any(c in loc for c in PREFERRED_CITIES):
        score += 6
        cues.append("NCR")
    elif any(c in loc for c in OK_CITIES):
        score += 2

    # de-dupe cues, keep order
    seen = set()
    cues = [c for c in cues if not (c in seen or seen.add(c))]
    return round(score, 1), cues[:8]


def rank(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    for j in jobs:
        s, cues = score_job(j)
        scored.append({**j, "_prefilter_score": s, "_fit_cues": cues})
    scored.sort(key=lambda j: -j["_prefilter_score"])
    return scored
