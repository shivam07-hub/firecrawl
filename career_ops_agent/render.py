"""
Markdown -> PDF renderer.

Path: pandoc (md -> standalone HTML with embedded CSS) -> Chrome headless
(HTML -> PDF). No LaTeX needed. Falls back gracefully and reports what's missing.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSS = HERE / "cv_style.css"

_CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
]


def _chrome() -> str | None:
    for c in _CHROME_CANDIDATES:
        if c and Path(c).exists():
            return c
    return None


def have_renderer() -> tuple[bool, str]:
    if not shutil.which("pandoc"):
        return False, "pandoc not found (brew install pandoc)"
    if not _chrome():
        return False, "no Chrome/Chromium found for HTML->PDF"
    return True, "pandoc + Chrome ready"


def md_to_pdf(md_path: Path, pdf_path: Path) -> Path:
    """Render a markdown file to PDF. Returns the pdf path. Raises on failure."""
    pandoc = shutil.which("pandoc")
    chrome = _chrome()
    if not pandoc:
        raise RuntimeError("pandoc not installed")
    if not chrome:
        raise RuntimeError("no Chrome/Chromium for PDF print")

    md_path = md_path.resolve()
    pdf_path = pdf_path.resolve()
    html_path = pdf_path.with_suffix(".html")
    subprocess.run(
        [pandoc, str(md_path), "-s", "--embed-resources",
         "--css", str(CSS), "-o", str(html_path)],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        check=True, capture_output=True, text=True,
    )
    html_path.unlink(missing_ok=True)
    if not pdf_path.exists():
        raise RuntimeError("Chrome did not produce a PDF")
    return pdf_path
