"""Generic open-access downloader: fetch any publication that carries a file URL.

Most works discovered by the search plugins (OpenAlex OA locations, repository
deposits, arXiv, Kagi discovery) already know a direct ``pdf_url``. This plugin
simply downloads it, which is the single highest-yield download path — so it
runs first. Publisher URLs are treated as the version of record, repository
URLs as accepted manuscripts.
"""

from __future__ import annotations

from pathlib import Path

from snaffle.fetch import fetch_document, looks_like_pdf
from snaffle.models import DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin
from snaffle.plugins.public.discovery import classify_source


class OpenAccessPlugin(Plugin, DownloadCapability):
    name = "oa"
    description = "Direct open-access file download (any pdf_url)"
    priority = 15  # a known file URL is the most reliable source; try it first

    def can_download(self, publication: Publication) -> bool:
        return bool(publication.pdf_url)

    def download(self, publication: Publication, dest: Path) -> DownloadResult:
        data = fetch_document(self.ctx.http, publication.pdf_url)
        if not data or not looks_like_pdf(data):
            return DownloadResult(success=False, error="no PDF at pdf_url")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        quality = classify_source(publication.pdf_url, publication)
        return DownloadResult(success=True, path=dest, quality=quality)
