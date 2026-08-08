"""EPrints plugin: search an EPrints repository via its JSON export."""

from __future__ import annotations

from pathlib import Path

from snaffle.fetch import fetch_document, looks_like_pdf
from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin, SearchCapability
from snaffle.plugins.public._helpers import first_year, map_work_type


def _author_name(creator: dict) -> str:
    name = creator.get("name", {})
    if isinstance(name, str):
        return name
    return " ".join(part for part in (name.get("given"), name.get("family")) if part).strip()


def _first_document_url(documents: list) -> str | None:
    for doc in documents or []:
        for f in doc.get("files", []):
            if f.get("url"):
                return f["url"]
    return None


def parse_eprints_export(payload: list) -> list[Publication]:
    pubs = []
    for item in payload:
        title = item.get("title")
        if not title:
            continue
        pubs.append(
            Publication(
                title=title,
                authors=[_author_name(c) for c in item.get("creators", [])],
                year=first_year(item.get("date")),
                venue=item.get("publication"),
                publisher=item.get("publisher"),
                doi=item.get("doi"),
                type=map_work_type(item.get("type")),
                pdf_url=_first_document_url(item.get("documents", [])),
                url=item.get("uri"),
                sources=["eprints"],
            )
        )
    return pubs


class EPrintsPlugin(Plugin, SearchCapability, DownloadCapability):
    name = "eprints"
    description = "EPrints institutional repository"
    priority = 60

    def search(self, academic: str) -> list[Publication]:
        base = self.ctx.config.get("eprints_base")
        if not base:
            return []
        response = self.ctx.http.get(
            f"{base.rstrip('/')}/cgi/search",
            params={"q": academic, "output": "JSON"},
        )
        response.raise_for_status()
        return parse_eprints_export(response.json())

    def can_download(self, publication: Publication) -> bool:
        return bool(publication.pdf_url) and "eprints" in publication.sources

    def download(self, publication: Publication, dest: Path) -> DownloadResult:
        if not publication.pdf_url:
            return DownloadResult(success=False, error="no document")
        data = fetch_document(self.ctx.http, publication.pdf_url)
        if not data or not looks_like_pdf(data):
            return DownloadResult(success=False, error="document was not a PDF")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return DownloadResult(success=True, path=dest, quality=CopyQuality.PREPRINT)
