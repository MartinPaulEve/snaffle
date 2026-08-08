"""CrossRef search plugin: query the public CrossRef REST API by author."""

from __future__ import annotations

from snaffle.models import Publication
from snaffle.plugins.base import Plugin, SearchCapability
from snaffle.plugins.public._helpers import first_year, map_work_type

API = "https://api.crossref.org/works"


def parse_crossref_items(payload: dict) -> list[Publication]:
    """Convert a CrossRef ``/works`` JSON response into Publications."""
    items = payload.get("message", {}).get("items", [])
    pubs = []
    for item in items:
        titles = item.get("title") or []
        if not titles:
            continue
        authors = [
            " ".join(part for part in (a.get("given"), a.get("family")) if part).strip()
            for a in item.get("author", [])
        ]
        date_parts = (item.get("issued", {}).get("date-parts") or [[None]])[0]
        year = date_parts[0] if date_parts and date_parts[0] else first_year(item.get("created"))
        containers = item.get("container-title") or []
        pubs.append(
            Publication(
                title=titles[0],
                authors=[a for a in authors if a],
                year=year,
                venue=containers[0] if containers else None,
                publisher=item.get("publisher"),
                doi=item.get("DOI"),
                url=item.get("URL"),
                type=map_work_type(item.get("type")),
                volume=item.get("volume"),
                issue=item.get("issue"),
                pages=item.get("page"),
                issn=(item.get("ISSN") or [None])[0],
                sources=["crossref"],
            )
        )
    return pubs


class CrossRefPlugin(Plugin, SearchCapability):
    name = "crossref"
    description = "CrossRef DOI metadata API"

    def search(self, academic: str) -> list[Publication]:
        params = {"rows": 100}
        resolver = self.ctx.orcid_resolver
        orcid = resolver.resolve(academic) if resolver else None
        if orcid:
            # Author-asserted ORCID: the reliable disambiguator for same-name
            # authors (unlike inferred author-name search).
            params["filter"] = f"orcid:{orcid}"
        else:
            params["query.author"] = academic
        mailto = self.ctx.config.get("crossref_mailto")
        if mailto:
            params["mailto"] = mailto
        response = self.ctx.http.get(API, params=params)
        response.raise_for_status()
        return parse_crossref_items(response.json())
