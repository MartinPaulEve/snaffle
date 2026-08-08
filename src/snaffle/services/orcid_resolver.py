"""Discover an academic's ORCID iD from their name at runtime.

The ORCID is a fact about the *current search*, not persistent configuration,
so it is discovered rather than hardcoded. Resolution is deliberately
conservative: if the name matches more than one distinct ORCID (two real people
with the same name), it returns ``None`` rather than guessing wrong.
"""

from __future__ import annotations

from snaffle.matching import author_matches, normalize_name, parse_name

_ENDPOINT = "https://pub.orcid.org/v3.0/expanded-search/"


def build_query(name: str) -> str:
    """A structured Lucene query for the ORCID registry.

    A field-scoped ``family-name`` / ``given-names`` query returns the handful
    of genuine matches, unlike a free-text ``q`` which returns tens of
    thousands of relevance hits whose noise defeats disambiguation.
    """
    parsed = parse_name(name)
    clauses = []
    if parsed.surname:
        clauses.append(f"family-name:{parsed.surname}")
    if parsed.given_names:
        clauses.append(f"given-names:{parsed.given_names[0]}")
    return " AND ".join(clauses)


class OrcidResolver:
    def __init__(self, http, override: str | None = None) -> None:
        self.http = http
        self.override = override
        self._cache: dict[str, str | None] = {}

    def resolve(self, name: str) -> str | None:
        """Return the academic's ORCID iD, or ``None`` if unknown/ambiguous."""
        if self.override:
            return self.override
        key = normalize_name(name)
        if key in self._cache:
            return self._cache[key]
        resolved = self._lookup(name)
        self._cache[key] = resolved
        return resolved

    def _lookup(self, name: str) -> str | None:
        query = build_query(name)
        if not query:
            return None
        try:
            response = self.http.get(
                _ENDPOINT,
                params={"q": query, "rows": 20},
                headers={"Accept": "application/json"},
            )
        except Exception:  # noqa: BLE001 - resolution is best-effort
            return None
        if response.status_code != 200:
            return None

        matches: set[str] = set()
        for row in response.json().get("expanded-result") or []:
            orcid = row.get("orcid-id")
            if not orcid:
                continue
            full = f"{row.get('given-names', '')} {row.get('family-names', '')}".strip()
            if full and author_matches(name, [full]):
                matches.add(orcid)
        # Exactly one distinct ORCID matches the name: trust it. Otherwise the
        # name is ambiguous (or absent) and we must not guess.
        return matches.pop() if len(matches) == 1 else None
