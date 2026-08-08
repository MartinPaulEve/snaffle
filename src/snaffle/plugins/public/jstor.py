"""JSTOR plugin: both a search source and an authenticated download source.

Demonstrates a plugin exposing *both* capabilities. Downloads need a logged-in
session (institutional credentials, possibly a CAPTCHA) via shared services.
"""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin, SearchCapability
from snaffle.plugins.public._helpers import first_year


def parse_jstor_search(html: str) -> list[Publication]:
    soup = BeautifulSoup(html, "html.parser")
    pubs = []
    for item in soup.select(".result-item, .search-result"):
        title_el = item.select_one(".title, a.title")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue
        venue_el = item.select_one(".journal, .venue")
        pubs.append(
            Publication(
                title=title,
                venue=venue_el.get_text(strip=True) if venue_el else None,
                year=first_year(item.get_text(" ", strip=True)),
                url=title_el.get("href"),
                sources=["jstor"],
            )
        )
    return pubs


class JstorPlugin(Plugin, SearchCapability, DownloadCapability):
    name = "jstor"
    description = "JSTOR (search + authenticated download)"
    priority = 40

    def search(self, academic: str) -> list[Publication]:
        response = self.ctx.http.get(
            "https://www.jstor.org/action/doBasicSearch",
            params={"Query": f"au:{academic}"},
        )
        response.raise_for_status()
        return parse_jstor_search(response.text)

    def can_download(self, publication: Publication) -> bool:
        url = publication.url or ""
        return "jstor.org" in url and bool(self.ctx.credentials)

    def download(self, publication: Publication, dest: Path) -> DownloadResult:
        # Real download drives the shared authenticated browser/EZproxy session.
        # Kept minimal here; institutional access is provided by ctx services.
        if not self.can_download(publication):
            return DownloadResult(success=False, error="no JSTOR access configured")
        response = self.ctx.http.get(publication.url)
        content_type = response.headers.get("content-type", "")
        if response.status_code != 200 or "pdf" not in content_type:
            return DownloadResult(success=False, error="no PDF returned (login/captcha?)")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
        return DownloadResult(success=True, path=dest, quality=CopyQuality.FINAL)
