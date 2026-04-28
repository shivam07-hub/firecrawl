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
import json
import difflib
from pathlib import Path
from openai import OpenAI
from config import LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY, LM_STUDIO_MODEL, _speed as _MODEL_SPEED
from rag_skills import retrieve as _retrieve_skills

# Singletons — None until first use (lazy init keeps import side-effect free)
_client: OpenAI | None = None
_L3_INDEX: dict[str, str] | None = None
_L3_STRIPPED: dict[str, str] | None = None
_L3_KEYS: list[str] | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY)
    return _client


def _get_l3_index() -> tuple[dict[str, str], dict[str, str], list[str]]:
    global _L3_INDEX, _L3_STRIPPED, _L3_KEYS
    if _L3_INDEX is None:
        _L3_INDEX, _L3_STRIPPED = _build_l3_index()
        _L3_KEYS = list(_L3_INDEX.keys())
    return _L3_INDEX, _L3_STRIPPED, _L3_KEYS


# ── Lightcast L3 taxonomy index ────────────────────────────────────────────────

def _build_l3_index() -> tuple[dict[str, str], dict[str, str]]:
    """
    Load lightcast_skills_taxonomy.json and return two dicts:
      exact_index   — normalized skill name → canonical L3 skill name
      stripped_index — parenthetical-stripped name → canonical L3 name
                       (only includes unambiguous 1-to-1 mappings)

    Stripping logic: "Docker (Software)" → key "docker" → canonical "Docker (Software)"
    Ambiguous stripped keys (e.g. "UIKit" → both Apple and Web) are excluded.
    """
    taxonomy_path = Path(__file__).parent / "lightcast_skills_taxonomy.json"
    if not taxonomy_path.exists():
        print(f"  [WARN] lightcast_skills_taxonomy.json not found at {taxonomy_path}; skill validation disabled")
        return {}, {}
    with open(taxonomy_path, encoding="utf-8") as f:
        root = json.load(f)

    exact: dict[str, str] = {}
    stripped_multi: dict[str, list[str]] = {}  # key → [canonical, ...]

    for l1 in root.get("children", []):
        for l2 in l1.get("children", []):
            for l3 in l2.get("children", []):
                name = l3.get("name", "").strip()
                if not name:
                    continue
                exact[name.lower()] = name
                # Build stripped key: remove trailing " (anything)"
                base = re.sub(r"\s*\(.*\)\s*$", "", name).strip()
                if base and base.lower() != name.lower():
                    stripped_multi.setdefault(base.lower(), []).append(name)

    # Keep only unambiguous strippings
    stripped: dict[str, str] = {
        k: v[0] for k, v in stripped_multi.items() if len(v) == 1
    }
    return exact, stripped

# Indexes populated on first call to _get_l3_index()

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
    candidates = _retrieve_skills(title + " " + jd[:800], k=40)
    skills_list = ", ".join(candidates)
    prompt = _ENRICH_PROMPT.format(title=title, jd=jd[:1500], skills_list=skills_list)
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

def _match_to_taxonomy(skill: str) -> str | None:
    """
    Return the canonical L3 skill name from the Lightcast taxonomy that best
    matches the input string, or None if no confident match is found.

    Strategy (in order):
      1. Exact match (case-insensitive): "Machine Learning" → "Machine Learning"
      2. Stripped-parenthetical match: "Docker" → "Docker (Software)"
         Uses a pre-built unambiguous index so "Java" → "Java (Programming Language)"
         without matching "Java Foundation Classes" or other Java entries.
      3. Fuzzy match via difflib (cutoff=0.88, min input length 8 chars) — catches
         minor spelling differences (e.g. "Stakeholder Mgmt" → "Stakeholder Management").
         High cutoff + length guard prevents short-term false positives like
         "Python" → "Jython".

    If the taxonomy index is empty (file missing), passes the skill through unchanged.
    """
    l3_index, l3_stripped, l3_keys = _get_l3_index()

    if not l3_index:
        return skill if (isinstance(skill, str) and skill.strip()) else None

    normalized = skill.strip().lower()
    if not normalized:
        return None

    # 1. Exact
    if normalized in l3_index:
        return l3_index[normalized]

    # 2. Stripped-parenthetical (e.g. "Docker" → "Docker (Software)")
    if normalized in l3_stripped:
        return l3_stripped[normalized]

    # 3. Fuzzy — only for longer terms to avoid short-string false positives
    if len(normalized) >= 8:
        matches = difflib.get_close_matches(normalized, l3_keys, n=1, cutoff=0.88)
        if matches:
            return l3_index[matches[0]]

    return None


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
            canonical = _match_to_taxonomy(s)
            if canonical and canonical not in validated:
                validated.append(canonical)
        data[field] = validated[:8]
    return data


def _llm_json(prompt: str, default):
    """Call LM Studio and parse the response as JSON. Returns default on any failure."""
    # deepseek-r1 (quality) emits a reasoning_content block before the answer;
    # 150 tokens is exhausted in thinking — needs 2048 to guarantee JSON output.
    # Fast models (gemma) don't use reasoning tokens so 300 is sufficient.
    _max_tokens = 2048 if _MODEL_SPEED == "quality" else 300
    try:
        resp = _get_client().chat.completions.create(
            model=LM_STUDIO_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise job data extractor. Return a single valid JSON object. No explanation, no markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=_max_tokens,
        )
        text = resp.choices[0].message.content or ''
        return _parse_json(text) if text else default
    except Exception as e:
        print(f"    [LLM ERROR]: {e}")
        return default


def _parse_json(text: str):
    """
    Extract JSON from LLM output that may contain markdown fences or prose.
    Finds the first {...} or [...] block and parses it.
    """
    text = re.sub(r'```(?:json)?\s*', '', text).strip().rstrip('`').strip()

    for open_c, close_c in [('{', '}'), ('[', ']')]:
        start = text.find(open_c)
        end   = text.rfind(close_c)
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    return None
