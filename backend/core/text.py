"""Small text cleanup helpers shared by ingestion and retrieval.

PDFs often contain control characters, private-use glyphs (for example the
Symbol-font bullet ``\\uf0b7``), and hyphenated line breaks. Cleaning them
keeps embeddings, logs, and LLM context consistent.
"""

from __future__ import annotations

import re

_SPACES_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_PRIVATE_USE_RE = re.compile(r"[\ue000-\uf8ff]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HYPHEN_LINEBREAK_RE = re.compile(r"(?<=\w)-\n(?=\w)")
_BULLET_ONLY_LINE_RE = re.compile(r"(?m)^\s*[•·▪◦●○–—-]+\s*$\n?")


def normalize_text(text: str) -> str:
    """Clean extracted PDF text without changing its medical meaning."""
    if not text:
        return ""

    text = text.replace("\uf0b7", "-")  # common Symbol-font bullet
    text = _PRIVATE_USE_RE.sub(" ", text)
    text = _CONTROL_RE.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _HYPHEN_LINEBREAK_RE.sub("", text)
    text = _BULLET_ONLY_LINE_RE.sub("", text)
    text = _SPACES_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


def display_title(title: str) -> str:
    """Make an all-lowercase filename title easier to read."""
    title = (title or "").strip()
    return title.title() if title.islower() else title
