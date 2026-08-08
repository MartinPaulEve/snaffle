"""arXiv plugin: search the arXiv API and download preprint PDFs.

Preprints are second-best copies, so the download capability advertises a high
priority number (runs late, after publisher sources).
"""

from __future__ import annotations

from pathlib import Path

from defusedxml import ElementTree as ET

from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin, SearchCapability
from snaffle.plugins.public._helpers import first_year

API = "https://export.arxiv.org/api/query"
_ATOM = "{http://www.w3.org/2005/Atom}"


def parse_arxiv_feed(atom_xml: str) -> list[Publication]:
    """Parse the arXiv Atom feed into Publications (with pdf_url set)."""
    root = ET.fromstring(atom_xml)
    pubs = []
    for entry in root.findall(f"{_ATOM}entry"):
        title = (entry.findtext(f"{_ATOM}title") or "").strip()
        if not title:
            continue
        authors = [
            (a.findtext(f"{_ATOM}name") or "").strip()
            for a in entry.findall(f"{_ATOM}author")
        ]
        pdf_url = None
        for link in entry.findall(f"{_ATOM}link"):
            if link.get("type") == "application/pdf" or link.get("title") == "pdf":
                pdf_url = link.get("href")
        pubs.append(
            Publication(
                title=title,
                authors=[a for a in authors if a],
                year=first_year(entry.findtext(f"{_ATOM}published")),
                venue="arXiv",
                url=entry.findtext(f"{_ATOM}id"),
                pdf_url=pdf_url,
                sources=["arxiv"],
            )
        )
    return pubs


class ArxivPlugin(Plugin, SearchCapability, DownloadCapability):
    name = "arxiv"
    description = "arXiv preprint server"
    priority = 80  # preprints are a fallback, not the version of record

    def search(self, academic: str) -> list[Publication]:
        params = {"search_query": f'au:"{academic}"', "max_results": 100}
        response = self.ctx.http.get(API, params=params)
        response.raise_for_status()
        return parse_arxiv_feed(response.text)

    def can_download(self, publication: Publication) -> bool:
        pdf = publication.pdf_url or ""
        return "arxiv.org" in pdf or "arxiv" in publication.sources

    def download(self, publication: Publication, dest: Path) -> DownloadResult:
        if not publication.pdf_url:
            return DownloadResult(success=False, error="no arXiv PDF url")
        response = self.ctx.http.get(publication.pdf_url)
        if response.status_code != 200 or not response.content:
            return DownloadResult(success=False, error=f"HTTP {response.status_code}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
        return DownloadResult(success=True, path=dest, quality=CopyQuality.PREPRINT)
