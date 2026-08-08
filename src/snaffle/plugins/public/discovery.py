"""Full-text discovery via Kagi search.

Rather than being told where an academic's repositories live, this plugin
*discovers* full text: it asks Kagi for the work by title and author, filters
the results to likely full-text files, and downloads the best one. This is how
snaffle finds eprints, publisher, and open-repository copies that no
DOI-resolver knows about.
"""

from __future__ import annotations

from pathlib import Path

from snaffle.matching import parse_name
from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin

# Domains/paths that signal a publisher's version of record.
_PUBLISHER_HINTS = (
    "openbookpublishers.com",
    "doi.org",
    "cambridge.org",
    "oup.com",
    "tandfonline.com",
    "sagepub.com",
    "springer.com",
    "wiley.com",
    "ucpress.edu",
    "jhu.edu",
)
# Domains/paths that signal an author manuscript / repository copy.
_REPOSITORY_HINTS = (
    "eprints",
    "repository",
    "dspace",
    "bitstream",
    ".ac.uk",
    "hcommons.org",
    "openedition.org",
    "zenodo.org",
    "figshare",
    "/handle/",
)


def _first_author_surname(pub: Publication) -> str:
    if pub.authors:
        return parse_name(pub.authors[0]).surname
    return ""


def build_queries(pub: Publication) -> list[str]:
    """Search-query variants, most specific first."""
    surname = _first_author_surname(pub).title()
    title = pub.title
    queries = [f'"{title}" {surname} filetype:pdf']
    if pub.doi:
        queries.append(f"{pub.doi} pdf")
    queries.append(f'"{title}" {surname} full text pdf')
    return queries


def classify_source(url: str, pub: Publication) -> CopyQuality:
    """Guess the copy quality a URL will yield."""
    lowered = url.lower()
    if any(hint in lowered for hint in _PUBLISHER_HINTS):
        return CopyQuality.FINAL
    if any(hint in lowered for hint in _REPOSITORY_HINTS):
        return CopyQuality.PREPRINT
    return CopyQuality.OTHER


def _looks_like_fulltext(url: str, pub: Publication) -> bool:
    lowered = url.lower()
    if lowered.endswith(".pdf") or ".pdf" in lowered:
        return True
    return any(h in lowered for h in _PUBLISHER_HINTS + _REPOSITORY_HINTS)


def select_candidates(results: list[dict], pub: Publication) -> list[dict]:
    """Filter to likely full-text URLs, best quality first."""
    candidates = []
    seen = set()
    for row in results:
        url = row.get("url", "")
        if not url or url in seen or not _looks_like_fulltext(url, pub):
            continue
        seen.add(url)
        candidates.append({"url": url, "quality": classify_source(url, pub)})
    # FINAL before PREPRINT before OTHER; stable within a tier.
    candidates.sort(key=lambda c: -int(c["quality"]))
    return candidates


def _extension_for(url: str, content_type: str) -> str:
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        return "pdf"
    if "msword" in content_type or url.lower().endswith((".doc", ".docx")):
        return "docx"
    return "pdf"


class DiscoveryPlugin(Plugin, DownloadCapability):
    name = "discovery"
    description = "Full-text discovery via Kagi web search"
    priority = 25  # discovered copies are reliable; try before DOI resolvers

    def can_download(self, publication: Publication) -> bool:
        return bool(self.ctx.kagi) and bool(publication.title)

    def download(self, publication: Publication, dest: Path) -> DownloadResult:
        candidates: list[dict] = []
        seen = set()
        for query in build_queries(publication):
            for cand in select_candidates(self.ctx.kagi.search(query), publication):
                if cand["url"] not in seen:
                    seen.add(cand["url"])
                    candidates.append(cand)

        last_error = "no full-text copy discovered"
        for cand in candidates:
            try:
                response = self.ctx.http.get(cand["url"])
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                continue
            if response.status_code != 200 or not response.content:
                last_error = f"HTTP {response.status_code}"
                continue
            content_type = response.headers.get("content-type", "")
            is_pdf = "pdf" in content_type or response.content[:5].startswith(b"%PDF")
            if not is_pdf:
                last_error = "candidate was not a downloadable document"
                continue
            ext = _extension_for(cand["url"], content_type)
            target = dest.with_suffix("." + ext)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(response.content)
            return DownloadResult(success=True, path=target, quality=cand["quality"])

        return DownloadResult(success=False, error=last_error)
