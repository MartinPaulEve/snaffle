"""Elsevier Pure plugin: search a Pure research-portal API for outputs."""

from __future__ import annotations

from snaffle.models import Publication
from snaffle.plugins.base import Plugin, SearchCapability
from snaffle.plugins.public._helpers import first_year, map_work_type


def _pure_type(item: dict) -> str | None:
    try:
        return item["type"]["term"]["text"][0]["value"]
    except (KeyError, IndexError, TypeError):
        return None


def _pure_year(item: dict) -> int | None:
    for status in item.get("publicationStatuses", []):
        year = (status.get("publicationDate") or {}).get("year")
        if year:
            return first_year(year)
    return None


def parse_pure_results(payload: dict) -> list[Publication]:
    pubs = []
    for item in payload.get("items", []):
        title = (item.get("title") or {}).get("value")
        if not title:
            continue
        pubs.append(
            Publication(
                title=title,
                year=_pure_year(item),
                doi=(item.get("electronicVersions", [{}])[0] or {}).get("doi"),
                type=map_work_type(_pure_type(item)),
                sources=["pure"],
            )
        )
    return pubs


class PurePlugin(Plugin, SearchCapability):
    name = "pure"
    description = "Elsevier Pure research portal"

    def search(self, academic: str) -> list[Publication]:
        base = self.ctx.config.get("pure_base")
        if not base:
            return []
        response = self.ctx.http.get(
            f"{base.rstrip('/')}/ws/api/research-outputs",
            params={"q": academic},
        )
        response.raise_for_status()
        return parse_pure_results(response.json())
