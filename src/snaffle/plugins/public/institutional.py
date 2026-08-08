"""Institutional download plugin: harvest paywalled PDFs via a logged-in session.

Relies on an :class:`~snaffle.services.institutional.InstitutionalHarvester`
placed on the context after the user has completed institutional login in the
browser. It resolves a work's DOI through EZProxy and downloads the PDF the
publisher advertises via ``citation_pdf_url``.
"""

from __future__ import annotations

from pathlib import Path

from snaffle.fetch import looks_like_pdf
from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin


class InstitutionalPlugin(Plugin, DownloadCapability):
    name = "institutional"
    description = "Paywalled PDF via institutional login (EZProxy)"
    priority = 45  # after open access, before Unpaywall

    def can_download(self, publication: Publication) -> bool:
        return bool(self.ctx.institutional) and bool(publication.doi)

    def download(self, publication: Publication, dest: Path) -> DownloadResult:
        data = self.ctx.institutional.fetch_pdf_by_doi(publication.doi)
        if not data or not looks_like_pdf(data):
            return DownloadResult(success=False, error="no institutional PDF")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return DownloadResult(success=True, path=dest, quality=CopyQuality.FINAL)
