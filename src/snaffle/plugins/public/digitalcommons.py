"""Digital Commons (bepress) plugin: search a bepress repository author page."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin, SearchCapability


def parse_bepress_author_page(html: str) -> list[Publication]:
    soup = BeautifulSoup(html, "html.parser")
    pubs = []
    for listing in soup.select(".article-listing"):
        link = listing.find("a")
        if not link:
            continue
        title = link.get_text(strip=True)
        if not title:
            continue
        pubs.append(
            Publication(title=title, url=link.get("href"), sources=["digitalcommons"])
        )
    return pubs


class DigitalCommonsPlugin(Plugin, SearchCapability, DownloadCapability):
    name = "digitalcommons"
    description = "Digital Commons (bepress) repository"
    priority = 60

    def search(self, academic: str) -> list[Publication]:
        url = self.ctx.config.get("digitalcommons_author_url")
        if not url:
            return []
        response = self.ctx.http.get(url)
        response.raise_for_status()
        return parse_bepress_author_page(response.text)

    def can_download(self, publication: Publication) -> bool:
        return bool(publication.pdf_url) and "digitalcommons" in publication.sources

    def download(self, publication: Publication, dest: Path) -> DownloadResult:
        if not publication.pdf_url:
            return DownloadResult(success=False, error="no PDF url")
        response = self.ctx.http.get(publication.pdf_url)
        if response.status_code != 200 or not response.content:
            return DownloadResult(success=False, error=f"HTTP {response.status_code}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
        return DownloadResult(success=True, path=dest, quality=CopyQuality.FINAL)
