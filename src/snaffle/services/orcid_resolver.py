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

    A field-scoped query returns the handful of genuine matches, unlike a
    free-text ``q`` which returns tens of thousands of relevance hits whose
    noise defeats disambiguation. Two strategies are ORed so that messy records
    are still found, because a name like "Martin Paul Eve" may be stored in
    several ways:

    * ``family-name:eve AND given-names:martin`` — survives a middle name kept
      in the given-names field (``given-names`` matches any of its tokens); and
    * ``given-and-family-names:"martin paul eve"`` — survives the middle name
      being misfiled, e.g. the family name wrongly recorded as "Paul Eve",
      because the combined field still reads the full name.

    Whatever the query returns is still verified by name afterwards, so breadth
    here costs precision nothing.
    """
    parsed = parse_name(name)
    strict = []
    if parsed.given_names:
        strict.append(f"given-names:{parsed.given_names[0]}")
    if parsed.surname:
        strict.append(f"family-name:{parsed.surname}")

    parts = []
    if strict:
        parts.append("(" + " AND ".join(strict) + ")")
    full = normalize_name(name)
    if full:
        parts.append(f'given-and-family-names:"{full}"')
    return " OR ".join(parts)


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
