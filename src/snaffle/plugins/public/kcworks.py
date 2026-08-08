"""KCWorks plugin: Knowledge Commons Works, a hosted InvenioRDM repository.

A concrete, always-available scholarly repository (not an institution-specific
endpoint that has to be configured). It reuses the InvenioRDM record parser.
"""

from __future__ import annotations

from pathlib import Path

from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin, SearchCapability
from snaffle.plugins.public.inveniordm import parse_invenio_hits

BASE = "https://works.hcommons.org"


class KCWorksPlugin(Plugin, SearchCapability, DownloadCapability):
    name = "kcworks"
    description = "Knowledge Commons Works (InvenioRDM)"
    priority = 50

    def search(self, academic: str) -> list[Publication]:
        response = self.ctx.http.get(f"{BASE}/api/records", params={"q": academic})
        response.raise_for_status()
        pubs = parse_invenio_hits(response.json())
        for pub in pubs:
            pub.sources = ["kcworks"]
        return pubs

    def can_download(self, publication: Publication) -> bool:
        return bool(publication.pdf_url) and "kcworks" in publication.sources

    def download(self, publication: Publication, dest: Path) -> DownloadResult:
        if not publication.pdf_url:
            return DownloadResult(success=False, error="no file")
        response = self.ctx.http.get(publication.pdf_url)
        if response.status_code != 200 or not response.content:
            return DownloadResult(success=False, error=f"HTTP {response.status_code}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
        return DownloadResult(success=True, path=dest, quality=CopyQuality.PREPRINT)
