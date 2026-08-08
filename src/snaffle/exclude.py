"""User-managed exclusions: drop publications from unwanted sources.

Configured via ``SNAFFLE_EXCLUDE`` (a comma-separated list) or ``--exclude`` on
the command line. Each term is matched case-insensitively against a
publication's venue, publisher, and URLs. The special term ``unknown`` matches
publications that have neither a venue nor a publisher (the ones that show as
"Unknown" in filenames).
"""

from __future__ import annotations

from snaffle.models import Publication

UNKNOWN = "unknown"


def parse_exclusions(env: dict) -> list[str]:
    raw = env.get("SNAFFLE_EXCLUDE", "") or ""
    return [term.strip().lower() for term in raw.split(",") if term.strip()]


def is_excluded(pub: Publication, terms: list[str]) -> bool:
    if not terms:
        return False
    haystacks = [pub.venue, pub.publisher, pub.url, pub.pdf_url]
    lowered = [h.lower() for h in haystacks if h]
    for term in terms:
        if term == UNKNOWN:
            if not (pub.venue or pub.publisher):
                return True
            continue
        if any(term in h for h in lowered):
            return True
    return False
