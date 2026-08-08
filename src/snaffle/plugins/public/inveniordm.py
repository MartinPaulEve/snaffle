"""InvenioRDM plugin: search a configurable InvenioRDM repository REST API."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from snaffle.fetch import fetch_document, looks_like_pdf
from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin, SearchCapability
from snaffle.plugins.public._helpers import first_year


def _pdf_file_url(hit: dict) -> str | None:
    """Build the file-content download URL for a record's PDF file, if any.

    InvenioRDM search listings do not include per-file download links, so the
    URL is composed from the record's API self-link and the file key:
    ``{self}/files/{key}/content``. The PDF entry is preferred over any other
    attachment (markdown, video, dataset).
    """
    self_api = (hit.get("links") or {}).get("self")
    entries = (hit.get("files") or {}).get("entries") or {}
    if not self_api or not entries:
        return None
    pdf_key = None
    for key, entry in entries.items():
        is_pdf = (entry.get("ext") == "pdf") or key.lower().endswith(".pdf") or (
            entry.get("mimetype") == "application/pdf"
        )
        if is_pdf:
            pdf_key = entry.get("key", key)
            break
    if pdf_key is None:
        return None
    return f"{self_api.rstrip('/')}/files/{quote(pdf_key)}/content"


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
                pdf_url=_pdf_file_url(hit),
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
        data = fetch_document(self.ctx.http, publication.pdf_url)
        if not data or not looks_like_pdf(data):
            return DownloadResult(success=False, error="no PDF at file URL")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return DownloadResult(success=True, path=dest, quality=CopyQuality.PREPRINT)
