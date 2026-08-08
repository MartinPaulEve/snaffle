"""InvenioRDM plugin: search a configurable InvenioRDM repository REST API."""

from __future__ import annotations

from pathlib import Path

from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin, SearchCapability
from snaffle.plugins.public._helpers import first_year


def _first_pdf(files: dict) -> str | None:
    for name, entry in (files or {}).get("entries", {}).items():
        if name.lower().endswith(".pdf"):
            return entry.get("links", {}).get("content")
    return None


def parse_invenio_hits(payload: dict) -> list[Publication]:
    pubs = []
    for hit in payload.get("hits", {}).get("hits", []):
        meta = hit.get("metadata", {})
        title = meta.get("title")
        if not title:
            continue
        authors = [c.get("person_or_org", {}).get("name", "") for c in meta.get("creators", [])]
        pubs.append(
            Publication(
                title=title,
                authors=[a for a in authors if a],
                year=first_year(meta.get("publication_date")),
                doi=(hit.get("pids", {}).get("doi", {}) or {}).get("identifier"),
                pdf_url=_first_pdf(hit.get("files", {})),
                url=hit.get("links", {}).get("self_html"),
                sources=["inveniordm"],
            )
        )
    return pubs


class InvenioRDMPlugin(Plugin, SearchCapability, DownloadCapability):
    name = "inveniordm"
    description = "InvenioRDM repository (e.g. Zenodo-style)"
    priority = 60

    def _base(self) -> str | None:
        return self.ctx.config.get("inveniordm_base")

    def search(self, academic: str) -> list[Publication]:
        base = self._base()
        if not base:
            return []
        response = self.ctx.http.get(f"{base.rstrip('/')}/api/records", params={"q": academic})
        response.raise_for_status()
        return parse_invenio_hits(response.json())

    def can_download(self, publication: Publication) -> bool:
        return bool(publication.pdf_url) and "inveniordm" in publication.sources

    def download(self, publication: Publication, dest: Path) -> DownloadResult:
        if not publication.pdf_url:
            return DownloadResult(success=False, error="no file")
        response = self.ctx.http.get(publication.pdf_url)
        if response.status_code != 200 or not response.content:
            return DownloadResult(success=False, error=f"HTTP {response.status_code}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
        return DownloadResult(success=True, path=dest, quality=CopyQuality.PREPRINT)
