"""ORCID plugin: the academic's *curated* works record — the disambiguation anchor.

Unlike bibliographic APIs that infer authorship (and sometimes bind the wrong
ORCID to junk metadata), the ORCID public record lists only works the academic
has claimed. Results are marked ``orcid_verified`` so matching trusts them.
"""

from __future__ import annotations

from snaffle.models import Publication
from snaffle.plugins.base import Plugin, SearchCapability
from snaffle.plugins.public._helpers import first_year, map_work_type

API = "https://pub.orcid.org/v3.0"


def _doi_from(summary: dict) -> str | None:
    ids = (summary.get("external-ids") or {}).get("external-id") or []
    for ident in ids:
        if (ident.get("external-id-type") or "").lower() == "doi":
            return ident.get("external-id-value")
    return None


def parse_orcid_works(payload: dict) -> list[Publication]:
    pubs = []
    for group in payload.get("group", []):
        summaries = group.get("work-summary") or []
        if not summaries:
            continue
        summary = summaries[0]
        title = (((summary.get("title") or {}).get("title")) or {}).get("value")
        if not title:
            continue
        year = first_year((summary.get("publication-date") or {}).get("year", {}).get("value"))
        pubs.append(
            Publication(
                title=title,
                year=year,
                venue=(summary.get("journal-title") or {}).get("value"),
                doi=_doi_from(summary),
                type=map_work_type(summary.get("type")),
                sources=["orcid"],
                extra={"orcid_verified": True},
            )
        )
    return pubs


class OrcidPlugin(Plugin, SearchCapability):
    name = "orcid"
    description = "ORCID curated works record (authoritative)"

    def search(self, academic: str) -> list[Publication]:
        resolver = self.ctx.orcid_resolver
        orcid = resolver.resolve(academic) if resolver else None
        if not orcid:
            return []
        response = self.ctx.http.get(
            f"{API}/{orcid}/works",
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return parse_orcid_works(response.json())
