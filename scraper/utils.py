import re
import html as _html
import hashlib
from html.parser import HTMLParser

# ── India location filter ─────────────────────────────────────────────────────

_INDIA_KEYWORDS = {
    'india', 'bengaluru', 'bangalore', 'hyderabad', 'mumbai', 'pune',
    'chennai', 'delhi', 'new delhi', 'gurugram', 'gurgaon', 'noida',
    'kolkata', 'ahmedabad',
}
# US state codes / patterns that produce false positives
_EXCLUDE_PATTERNS = [
    r'indiana[,\s]+(?:usa|united states|us\b|in\b)',
    r'\bin\b[,\s]+(?:usa|united states)',
]

def is_india(location: str) -> bool:
    if not location:
        return False
    loc = location.lower()
    for pat in _EXCLUDE_PATTERNS:
        if re.search(pat, loc):
            return False
    return any(k in loc for k in _INDIA_KEYWORDS)


# ── HTML stripping ────────────────────────────────────────────────────────────

class _Stripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return re.sub(r'\s+', ' ', ' '.join(self._parts)).strip()


def strip_html(html: str) -> str:
    if not html:
        return ''
    # Greenhouse (and some others) entity-encode their HTML
    # (&lt;p&gt; …). Unescape first so the parser sees real tags.
    unescaped = _html.unescape(html)
    s = _Stripper()
    s.feed(unescaped)
    return s.get_text()


# ── Stable job ID ─────────────────────────────────────────────────────────────

def job_hash(title: str, url: str) -> str:
    return hashlib.md5(f"{title}|{url}".encode()).hexdigest()[:16]


# Requisition-id tail on a Workday externalPath / apply URL, e.g. "…_R01165624".
_REQ_TAIL = re.compile(r'_([A-Za-z]{1,5}\d{4,})$')


def workday_req_id(posting: dict, external_path: str) -> str | None:
    """Company requisition id for a Workday CXS posting.

    The CXS list endpoint does not return a ``jobReqId`` field; the real
    requisition id lives in ``bulletFields[0]`` and at the ``_R…`` tail of the
    posting's ``externalPath``. Precedence: bulletFields[0] -> path tail -> None.
    """
    bf = posting.get('bulletFields') or []
    if bf and isinstance(bf[0], str) and bf[0].strip():
        return bf[0].strip()
    m = _REQ_TAIL.search(external_path or '')
    return m.group(1) if m else None


# ── Company → folder name ─────────────────────────────────────────────────────

def company_slug(name: str) -> str:
    """'Goldman Sachs (alt)' → 'Goldman_Sachs'"""
    cleaned = re.sub(r'[^\w\s]', '', name).strip()
    return re.sub(r'\s+', '_', cleaned)
