"""Open Library plugin: find books (which frequently lack DOIs) by author."""

from __future__ import annotations

from snaffle.models import Publication, WorkType
from snaffle.plugins.base import Plugin, SearchCapability

API = "https://openlibrary.org/search.json"


def parse_openlibrary_search(payload: dict) -> list[Publication]:
    pubs = []
    for doc in payload.get("docs", []):
        title = doc.get("title")
        if not title:
            continue
        isbns = doc.get("isbn") or []
        publishers = doc.get("publisher") or []
        pubs.append(
            Publication(
                title=title,
                authors=doc.get("author_name", []),
                year=doc.get("first_publish_year"),
                isbn=isbns[0] if isbns else None,
                publisher=publishers[0] if publishers else None,
                type=WorkType.BOOK,
                url=f"https://openlibrary.org{doc['key']}" if doc.get("key") else None,
                sources=["openlibrary"],
            )
        )
    return pubs


class OpenLibraryPlugin(Plugin, SearchCapability):
    name = "openlibrary"
    description = "Open Library book catalogue"

    def search(self, academic: str) -> list[Publication]:
        response = self.ctx.http.get(API, params={"author": academic, "limit": 100})
        response.raise_for_status()
        return parse_openlibrary_search(response.json())
