"""Small parsing helpers shared by the public plugins."""

from __future__ import annotations

import re

from snaffle.models import WorkType

_YEAR = re.compile(r"(1[5-9]\d{2}|20\d{2})")

# CrossRef / Pure / generic type strings mapped onto our WorkType enum.
_TYPE_MAP = {
    "journal-article": WorkType.ARTICLE,
    "article": WorkType.ARTICLE,
    "proceedings-article": WorkType.ARTICLE,
    "book": WorkType.BOOK,
    "monograph": WorkType.BOOK,
    "book-chapter": WorkType.CHAPTER,
    "chapter": WorkType.CHAPTER,
    "dissertation": WorkType.THESIS,
    "thesis": WorkType.THESIS,
    "report": WorkType.REPORT,
    "dataset": WorkType.DATASET,
}


def first_year(*candidates) -> int | None:
    """Return the first plausible 4-digit year found in the candidates."""
    for candidate in candidates:
        if candidate is None:
            continue
        match = _YEAR.search(str(candidate))
        if match:
            return int(match.group(1))
    return None


def map_work_type(raw: str | None) -> WorkType:
    if not raw:
        return WorkType.ARTICLE
    return _TYPE_MAP.get(raw.strip().lower(), WorkType.OTHER)
