"""OpenAlex search plugin: a large open catalogue of scholarly works."""

from __future__ import annotations

from snaffle.matching import normalize_name
from snaffle.models import Publication
from snaffle.plugins.base import Plugin, SearchCapability
from snaffle.plugins.public._helpers import map_work_type

API = "https://api.openalex.org/works"


def _bare_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    return doi.replace("https://doi.org/", "").strip() or None


def normalize_work_id(value: str) -> str:
    """Reduce an OpenAlex work id ('https://openalex.org/W123' or 'W123') to 'W123'."""
    return (value or "").rstrip("/").rsplit("/", 1)[-1].strip()


def _excluded_ids_for(academic: str, excludes: dict) -> set[str]:
    target = normalize_name(academic)
    ids: set[str] = set()
    for name, id_list in (excludes or {}).items():
        if normalize_name(name) == target:
            ids.update(normalize_work_id(i) for i in id_list)
    return ids


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
        pubs = parse_openalex_results(response.json())

        excluded = _excluded_ids_for(academic, self.ctx.config.get("openalex_excludes"))
        if excluded:
            pubs = [p for p in pubs if normalize_work_id(p.url) not in excluded]
        return pubs
