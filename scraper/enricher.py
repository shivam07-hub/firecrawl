"""
LM Studio enrichment — all LLM calls go through a local OpenAI-compatible
endpoint (http://localhost:1234/v1). No cloud API is called.

Single responsibility (v2, Dump 4+):
  enrich_job(job)
      Read job_title + job_description from canonical job dict.
      Ask LM Studio to extract:
        - role_domain  (functional area classification)
        - skills       (Lightcast L3 skills with is_primary + required_level)
      Skills that do not match an L3 entry in lightcast_skills_taxonomy.json are dropped.
      L1 and L2 taxonomy levels are derivable from L3 via the taxonomy JSON — not stored here.
      Back-compat fields main_skills and side_skills are still populated.
      Writes into the job dict in-place and returns it.
      Safe to call if job_description is empty (returns job unchanged).
"""
from __future__ import annotations

import re
from pathlib import Path
from openai import OpenAI
from config import LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY, LM_STUDIO_MODEL, _speed as _MODEL_SPEED
from rag_skills import retrieve as _retrieve_skills
from normalizer import match_to_taxonomy, parse_json_response, clean_jd_for_llm

# Singleton — None until first use
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY)
    return _client

# ── Controlled vocabularies ────────────────────────────────────────────────────

_ROLE_DOMAIN_VALUES = {
    "Software Engineering",
    "Data & Analytics",
    "Finance",
    "Strategy & Consulting",
    "HR & People",
    "Sales & Marketing",
    "Operations",
    "Legal & Compliance",
    "Product Management",
    "Research & Science",
    "IT & Infrastructure",
    "Risk & Compliance",
    "General Management",
    "Supply Chain",
    "Manufacturing",
}

# ── Prompt ────────────────────────────────────────────────────────────────────


_ENRICH_PROMPT = """\
Job Title: {title}

Job Description:
{jd}

Approved skill vocabulary (you MUST choose ONLY names from this list):
{skills_list}

━━━ LEVEL SCALE (required_level integer 1-4) ━━━
L1 - Awareness / Basic
    Signals: "familiar with", "exposure to", "knowledge of", "nice to have",
             "a plus", "preferred", "awareness of", "understanding of"

L2 - Working Proficiency
    Signals: "experience with", "working knowledge", "1-3 years", "proficient",
             "hands-on", "comfortable with", "able to use"

L3 - Advanced / Practitioner
    Signals: "strong experience", "3-5 years", "advanced", "deep knowledge",
             "lead", "architect", "design and implement", "own the"

L4 - Expert / Authority
    Signals: "expert", "5+ years", "mastery", "authority", "strategic ownership",
             "deep expertise", "principal", "staff-level", "drive the vision"

If no level signal is present for a needed skill, default to L2 (working proficiency).
Never assign L4 unless the JD explicitly demands expert or 5+ years.

Return a JSON object with EXACTLY these three keys:

1. job_summary: A neutral, factual summary of the ROLE in 100 words or fewer.
   Cover: what the person does, the core responsibilities, and the key skills/experience required.
   Plain prose, 1 short paragraph. NO company marketing/boilerplate, NO navigation text,
   NO "apply here", NO dates, NO location, NO requisition IDs, NO bullet symbols, NO markdown.
   Write it so a candidate instantly understands the job. Hard limit: 100 words.

2. role_domain: The functional area of this role. MUST be exactly one of:
   "Software Engineering" | "Data & Analytics" | "Finance" | "Strategy & Consulting" |
   "HR & People" | "Sales & Marketing" | "Operations" | "Legal & Compliance" |
   "Product Management" | "Research & Science" | "IT & Infrastructure" |
   "Risk & Compliance" | "General Management" | "Supply Chain" | "Manufacturing"
   Pick the single best match. Do not invent new values.

3. skills: JSON array, max 10 items. Each item:
   {{
     "name": "<exact name from approved vocabulary>",
     "required_level": 1 | 2 | 3 | 4
   }}
   List every skill the JD genuinely requires. There is NO must-have vs nice-to-have
   split — a skill is either needed for the role or it is not. The required_level (1-4)
   captures HOW deeply the JD needs it (see the LEVEL SCALE above); a "preferred" or
   "a plus" skill is still a needed skill, just at L1.
   Skills absent from the approved vocabulary MUST be omitted entirely.
   Do not invent skill names. Do not include duplicates.
   Do not fill the quota. Return fewer skills if the JD does not clearly support them.
   Never select a skill just because it appears in the approved vocabulary.
   Prefer 3-7 skills; return more only when the JD explicitly supports them.

Return ONLY valid JSON:
{{"job_summary": "", "role_domain": null, "skills": []}}"""


# ── Public function ───────────────────────────────────────────────────────────

def enrich_job(job: dict) -> dict:
    """
    Extract role_domain and structured skills from job_description via LM Studio.
    Only runs if job_description is non-empty and skills are not already set.
    Mutates and returns the job dict.
    """
    jd = (job.get('job_description') or '').strip()
    if not jd:
        return job

    # Skip if already fully enriched with levels, a controlled role_domain, and a summary.
    if (job.get('skills') and job.get('main_skills')
            and job.get('role_domain') in _ROLE_DOMAIN_VALUES
            and job.get('job_summary')):
        return job

    title  = (job.get('job_title') or '').strip()
    # Clean a COPY of the JD for the LLM (raw job_description is left untouched).
    jd_clean = clean_jd_for_llm(jd)
    candidates = _retrieve_skills(title + " " + jd_clean[:400], k=15)
    skills_list = ", ".join(candidates)
    # Summary needs broader context than skills extraction → feed more of the JD.
    prompt = _ENRICH_PROMPT.format(title=title, jd=jd_clean[:1500], skills_list=skills_list)
    extracted = _llm_json(prompt, default={})
    if extracted:
        extracted = _validate_enrichment(extracted)
        if not job.get('job_summary'):
            job['job_summary'] = extracted.get('job_summary') or ''
        if job.get('role_domain') not in _ROLE_DOMAIN_VALUES:
            job['role_domain'] = extracted.get('role_domain') or ''
        if not job.get('skills'):
            job['skills'] = extracted.get('skills', [])
        if not job.get('main_skills'):
            job['main_skills'] = extracted.get('main_skills', [])
        if not job.get('side_skills'):
            job['side_skills'] = extracted.get('side_skills', [])

    return job


# ── Internal helpers ──────────────────────────────────────────────────────────

def _validate_enrichment(data: dict) -> dict:
    """
    Validate LLM output:
    - role_domain must be in the controlled vocabulary.
    - skills is ONE flat list of needed skills, each matched against the Lightcast
      L3 taxonomy and carrying a required_level (1-4). There is no primary/side
      split — importance is expressed through required_level. The canonical
      taxonomy name is used (not the LLM's raw string); the list is capped at 10.
    - main_skills mirrors the full canonical skill-name list (back-compat column
      True_Yodha still reads for chips); side_skills is always [] (deprecated).
    """
    rd = data.get('role_domain')
    data['role_domain'] = rd if rd in _ROLE_DOMAIN_VALUES else None

    # job_summary: clean prose, hard-capped at 100 words (sentence-aware trim as safety net).
    summary = (data.get('job_summary') or '').strip()
    if summary:
        words = summary.split()
        if len(words) > 100:
            trimmed = ' '.join(words[:100])
            # prefer ending on the last full sentence within the cap
            cut = max(trimmed.rfind('. '), trimmed.rfind('! '), trimmed.rfind('? '))
            summary = (trimmed[:cut + 1] if cut > 40 else trimmed).strip()
    data['job_summary'] = summary

    raw_skills = data.get('skills') or []
    # Back-compat: flatten any legacy main_skills/side_skills input into the single list.
    if not raw_skills and (data.get('main_skills') or data.get('side_skills')):
        raw_skills = [
            {"name": skill, "required_level": 2} for skill in (data.get('main_skills') or [])
        ] + [
            {"name": skill, "required_level": 1} for skill in (data.get('side_skills') or [])
        ]
    if not isinstance(raw_skills, list):
        raw_skills = []

    validated: list[dict] = []
    seen: set[str] = set()
    for item in raw_skills:
        if isinstance(item, dict):
            name, level = item.get('name'), item.get('required_level')
        elif isinstance(item, str):
            name, level = item, None
        else:
            continue
        canonical = match_to_taxonomy(name or '')
        if not canonical or canonical in seen:
            continue
        if not isinstance(level, int) or level not in (1, 2, 3, 4):
            level = 2
        if len(validated) >= 10:
            break
        validated.append({'name': canonical, 'required_level': level})
        seen.add(canonical)

    data['skills'] = validated
    data['main_skills'] = [s['name'] for s in validated]   # all needed skills (one bucket)
    data['side_skills'] = []                                # deprecated; always empty
    return data


def _llm_json(prompt: str, default):
    """Call LM Studio and parse the response as JSON. Returns default on any failure."""
    # deepseek-r1 (quality) emits a reasoning_content block before the answer;
    # needs 2048 to guarantee JSON output after thinking tokens.
    # Fast models now emit structured skill objects; 512 gives headroom without
    # burning decode budget on preamble. Assistant prefill forces decode to start at {.
    _max_tokens = 2048 if _MODEL_SPEED == "quality" else 768
    try:
        resp = _get_client().chat.completions.create(
            model=LM_STUDIO_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise job data extractor. Start your response with { immediately. No preamble, no markdown."},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "{"},
            ],
            temperature=0.0,
            max_tokens=_max_tokens,
        )
        text = resp.choices[0].message.content or ''
        # Restore the assistant prefill "{" — the API returns only the continuation.
        if text and not text.lstrip().startswith('{'):
            text = '{' + text
        return parse_json_response(text) if text else default
    except Exception as e:
        print(f"    [LLM ERROR]: {e}")
        return default
