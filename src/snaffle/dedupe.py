"""Deduplicate publications gathered from multiple sources."""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from snaffle.models import Publication

_PUNCT = re.compile(r"[^\w\s]")
_WS = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation and collapse whitespace for comparison."""
    text = _PUNCT.sub(" ", (title or "").lower())
    return _WS.sub(" ", text).strip()


def publication_key(pub: Publication) -> str | None:
    """Return a strong identity key (DOI/ISBN) if the publication has one."""
    if pub.doi:
        return "doi:" + pub.doi.strip().lower()
    if pub.isbn:
        digits = re.sub(r"[^0-9xX]", "", pub.isbn).lower()
        if digits:
            return "isbn:" + digits
    return None


def _authors_compatible(a: Publication, b: Publication) -> bool:
    """True unless both list authors and none of their surnames overlap."""
    from snaffle.matching import parse_name

    if not a.authors or not b.authors:
        return True
    surnames_a = {parse_name(x).surname for x in a.authors}
    surnames_b = {parse_name(x).surname for x in b.authors}
    return bool(surnames_a & surnames_b)


def are_duplicates(a: Publication, b: Publication) -> bool:
    """True if two publications describe the same work despite metadata drift."""
    ka, kb = publication_key(a), publication_key(b)
    if ka and kb:
        return ka == kb
    # Fall back to fuzzy title match, constrained by year when both known.
    if a.year and b.year and a.year != b.year:
        return False
    na, nb = normalize_title(a.title), normalize_title(b.title)
    if fuzz.token_sort_ratio(na, nb) >= 90:
        return True
    # Subtitle case: one title is essentially contained in the other (e.g. the
    # same book with and without its subtitle). Guard against merging on a short
    # generic opening phrase by requiring a substantial shared portion and
    # compatible authorship.
    shorter, longer = sorted((na, nb), key=len)
    if len(shorter) >= 20 and fuzz.partial_ratio(shorter, longer) >= 95:
        return _authors_compatible(a, b)
    return False


def _richer(a, b):
    """Pick the non-empty value, preferring a's when both are set."""
    return a if a not in (None, "", [], {}) else b


def merge_publications(a: Publication, b: Publication) -> Publication:
    """Merge two duplicate publications, keeping the richest metadata."""
    scalar_fields = [
        "title", "year", "venue", "publisher", "doi", "isbn", "issn",
        "url", "pdf_url", "volume", "issue", "pages", "abstract",
    ]
    merged = Publication(title=a.title or b.title)
    for field in scalar_fields:
        setattr(merged, field, _richer(getattr(a, field), getattr(b, field)))
    # Keep the more specific work type (anything over the ARTICLE default).
    from snaffle.models import WorkType

    merged.type = a.type if a.type != WorkType.ARTICLE else b.type
    merged.authors = a.authors if len(a.authors) >= len(b.authors) else b.authors
    merged.sources = list(dict.fromkeys([*a.sources, *b.sources]))
    merged.extra = {**b.extra, **a.extra}
    return merged


def deduplicate(publications: list[Publication]) -> list[Publication]:
    """Collapse a list of publications so each real work appears once."""
    result: list[Publication] = []
    for pub in publications:
        for i, existing in enumerate(result):
            if are_duplicates(existing, pub):
                result[i] = merge_publications(existing, pub)
                break
        else:
            result.append(pub)
    return result
