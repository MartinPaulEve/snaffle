"""Project MUSE plugin: search source and authenticated download source."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin, SearchCapability
from snaffle.plugins.public._helpers import first_year


def parse_muse_search(html: str) -> list[Publication]:
    soup = BeautifulSoup(html, "html.parser")
    pubs = []
    for item in soup.select(".result, .card"):
        title_el = item.select_one(".title, a.title")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue
        venue_el = item.select_one(".journal, .source")
        pubs.append(
            Publication(
                title=title,
                venue=venue_el.get_text(strip=True) if venue_el else None,
                year=first_year(item.get_text(" ", strip=True)),
                url=title_el.get("href"),
                sources=["projectmuse"],
            )
        )
    return pubs


class ProjectMusePlugin(Plugin, SearchCapability, DownloadCapability):
    name = "projectmuse"
    description = "Project MUSE (search + authenticated download)"
    priority = 40

    def search(self, academic: str) -> list[Publication]:
        response = self.ctx.http.get(
            "https://muse.jhu.edu/search",
            params={"action": "search", "query": academic},
        )
        response.raise_for_status()
        return parse_muse_search(response.text)

    def can_download(self, publication: Publication) -> bool:
        url = publication.url or ""
        return "muse.jhu.edu" in url and bool(self.ctx.credentials)

    def download(self, publication: Publication, dest: Path) -> DownloadResult:
        if not self.can_download(publication):
            return DownloadResult(success=False, error="no Project MUSE access configured")
        response = self.ctx.http.get(publication.url)
        content_type = response.headers.get("content-type", "")
        if response.status_code != 200 or "pdf" not in content_type:
            return DownloadResult(success=False, error="no PDF returned (login/captcha?)")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
        return DownloadResult(success=True, path=dest, quality=CopyQuality.FINAL)
