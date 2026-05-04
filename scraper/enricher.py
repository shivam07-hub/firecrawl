"""
LM Studio enrichment — all LLM calls go through a local OpenAI-compatible
endpoint (http://localhost:1234/v1). No cloud API is called.

Single responsibility (v2, Dump 4+):
  enrich_job(job)
      Read job_title + job_description from canonical job dict.
      Ask LM Studio to extract:
        - role_domain  (functional area classification)
        - main_skills  (top 5 must-have skills, validated against Lightcast L3 taxonomy)
        - side_skills  (nice-to-have skills, validated against Lightcast L3 taxonomy)
      Skills that do not match an L3 entry in lightcast_skills_taxonomy.json are dropped.
      L1 and L2 taxonomy levels are derivable from L3 via the taxonomy JSON — not stored here.
      Writes into the job dict in-place and returns it.
      Safe to call if job_description is empty (returns job unchanged).
"""
import re
from pathlib import Path
from openai import OpenAI
from config import LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY, LM_STUDIO_MODEL, _speed as _MODEL_SPEED
from rag_skills import retrieve as _retrieve_skills
from normalizer import match_to_taxonomy, parse_json_response

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

Approved skill vocabulary (choose ONLY from this list for main_skills and side_skills):
{skills_list}

Return a JSON object with EXACTLY these three keys:

1. role_domain: The functional area of this role. MUST be exactly one of:
   "Software Engineering" | "Data & Analytics" | "Finance" | "Strategy & Consulting" |
   "HR & People" | "Sales & Marketing" | "Operations" | "Legal & Compliance" |
   "Product Management" | "Research & Science" | "IT & Infrastructure" |
   "Risk & Compliance" | "General Management" | "Supply Chain" | "Manufacturing"
   Pick the single best match. Do not invent new values.

2. main_skills: JSON array of the top 5 MUST-HAVE technical/hard skills from the JD.
   - Choose ONLY names from the approved skill vocabulary above. Max 5 items.

3. side_skills: JSON array of nice-to-have or soft skills from the JD.
   - Choose ONLY names from the approved skill vocabulary above. Max 8 items.

Use [] for skills if none are mentioned. Use null for role_domain if truly unclear.
Return ONLY valid JSON:
{{"role_domain": null, "main_skills": [], "side_skills": []}}"""


# ── Public function ───────────────────────────────────────────────────────────

def enrich_job(job: dict) -> dict:
    """
    Extract role_domain, main_skills and side_skills from job_description via LM Studio.
    Only runs if job_description is non-empty and skills are not already set.
    Mutates and returns the job dict.
    """
    jd = (job.get('job_description') or '').strip()
    if not jd:
        return job

    # Skip if already fully enriched
    if job.get('main_skills') and job.get('role_domain'):
        return job

    title  = (job.get('job_title') or '').strip()
    candidates = _retrieve_skills(title + " " + jd[:400], k=15)
    skills_list = ", ".join(candidates)
    prompt = _ENRICH_PROMPT.format(title=title, jd=jd[:600], skills_list=skills_list)
    extracted = _llm_json(prompt, default={})
    if extracted:
        extracted = _validate_enrichment(extracted)
        if not job.get('role_domain'):
            job['role_domain'] = extracted.get('role_domain') or ''
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
    - Skills are matched against the Lightcast L3 taxonomy; unmatched skills are dropped.
      The canonical taxonomy name is used (not the LLM's raw string).
    """
    rd = data.get('role_domain')
    data['role_domain'] = rd if rd in _ROLE_DOMAIN_VALUES else None

    for field in ('main_skills', 'side_skills'):
        val = data.get(field)
        if not isinstance(val, list):
            data[field] = []
            continue
        validated = []
        for s in val:
            if not isinstance(s, str):
                continue
            canonical = match_to_taxonomy(s)
            if canonical and canonical not in validated:
                validated.append(canonical)
        data[field] = validated[:8]
    return data


def _llm_json(prompt: str, default):
    """Call LM Studio and parse the response as JSON. Returns default on any failure."""
    # deepseek-r1 (quality) emits a reasoning_content block before the answer;
    # needs 2048 to guarantee JSON output after thinking tokens.
    # Fast models (gemma) output ~60-80 real tokens; 120 gives headroom without
    # burning decode budget on preamble. Assistant prefill forces decode to start at {.
    _max_tokens = 2048 if _MODEL_SPEED == "quality" else 120
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


