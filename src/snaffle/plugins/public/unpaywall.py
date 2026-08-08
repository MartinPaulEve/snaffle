"""Unpaywall download plugin: resolve a DOI to a legal open-access PDF."""

from __future__ import annotations

from pathlib import Path

from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin

API = "https://api.unpaywall.org/v2/"


def extract_oa_pdf_url(payload: dict) -> str | None:
    """Pull the best open-access PDF location from an Unpaywall response."""
    best = payload.get("best_oa_location")
    if best and best.get("url_for_pdf"):
        return best["url_for_pdf"]
    for loc in payload.get("oa_locations") or []:
        if loc.get("url_for_pdf"):
            return loc["url_for_pdf"]
    return None


class UnpaywallPlugin(Plugin, DownloadCapability):
    name = "unpaywall"
    description = "Unpaywall open-access PDF locator"
    priority = 20  # legal OA version of record, run early

    def can_download(self, publication: Publication) -> bool:
        return bool(publication.doi)

    def download(self, publication: Publication, dest: Path) -> DownloadResult:
        email = self.ctx.config.get("unpaywall_email") or "info@example.com"
        meta = self.ctx.http.get(f"{API}{publication.doi}", params={"email": email})
        if meta.status_code != 200:
            return DownloadResult(success=False, error=f"unpaywall HTTP {meta.status_code}")
        pdf_url = extract_oa_pdf_url(meta.json())
        if not pdf_url:
            return DownloadResult(success=False, error="no open-access copy")
        pdf = self.ctx.http.get(pdf_url)
        if pdf.status_code != 200 or not pdf.content:
            return DownloadResult(success=False, error=f"pdf HTTP {pdf.status_code}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(pdf.content)
        return DownloadResult(success=True, path=dest, quality=CopyQuality.FINAL)
