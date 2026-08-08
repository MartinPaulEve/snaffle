"""OpenAlex search plugin: a large open catalogue of scholarly works."""

from __future__ import annotations

from snaffle.models import Publication
from snaffle.plugins.base import Plugin, SearchCapability
from snaffle.plugins.public._helpers import map_work_type

API = "https://api.openalex.org/works"


def _bare_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    return doi.replace("https://doi.org/", "").strip() or None


def parse_openalex_results(payload: dict) -> list[Publication]:
    pubs = []
    for work in payload.get("results", []):
        title = work.get("title") or work.get("display_name")
        if not title:
            continue
        source = ((work.get("primary_location") or {}).get("source") or {})
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in work.get("authorships", [])
        ]
        pubs.append(
            Publication(
                title=title,
                authors=[a for a in authors if a],
                year=work.get("publication_year"),
                venue=source.get("display_name"),
                publisher=source.get("host_organization_name"),
                doi=_bare_doi(work.get("doi")),
                type=map_work_type(work.get("type")),
                pdf_url=(work.get("best_oa_location") or {}).get("pdf_url"),
                url=work.get("id"),
                sources=["openalex"],
            )
        )
    return pubs


class OpenAlexPlugin(Plugin, SearchCapability):
    name = "openalex"
    description = "OpenAlex open scholarly catalogue"

    def search(self, academic: str) -> list[Publication]:
        params = {
            "filter": f"raw_author_name.search:{academic}",
            "per-page": 100,
        }
        mailto = self.ctx.config.get("crossref_mailto")
        if mailto:
            params["mailto"] = mailto
        response = self.ctx.http.get(API, params=params)
        response.raise_for_status()
        return parse_openalex_results(response.json())
