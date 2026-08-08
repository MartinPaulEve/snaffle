"""KCWorks plugin: Knowledge Commons Works, a hosted InvenioRDM repository.

A concrete, always-available scholarly repository (not an institution-specific
endpoint that has to be configured). Where the academic's ORCID is known, the
records are queried by ORCID for a clean, complete list; otherwise by name.
Deposits here are frequently the only open copy of blog posts and talks.
"""

from __future__ import annotations

from pathlib import Path

from snaffle.fetch import fetch_document, looks_like_pdf
from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin, SearchCapability
from snaffle.plugins.public.inveniordm import parse_invenio_hits

BASE = "https://works.hcommons.org"
_ORCID_FIELD = "metadata.creators.person_or_org.identifiers.identifier"


class KCWorksPlugin(Plugin, SearchCapability, DownloadCapability):
    name = "kcworks"
    description = "Knowledge Commons Works (InvenioRDM)"
    priority = 30  # author's own deposits: reliable open copies, try early

    def _query(self, academic: str) -> str:
        resolver = self.ctx.orcid_resolver
        orcid = resolver.resolve(academic) if resolver else None
        # An ORCID-scoped query returns only this person's deposits; a name
        # query returns a large, noisy full-text result set.
        return f"{_ORCID_FIELD}:{orcid}" if orcid else f'"{academic}"'

    def search(self, academic: str) -> list[Publication]:
        response = self.ctx.http.get(
            f"{BASE}/api/records",
            params={"q": self._query(academic), "size": 100},
        )
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
        data = fetch_document(self.ctx.http, publication.pdf_url)
        if not data or not looks_like_pdf(data):
            return DownloadResult(success=False, error="no PDF at file URL")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return DownloadResult(success=True, path=dest, quality=CopyQuality.PREPRINT)
