"""Unpaywall download plugin: resolve a DOI to a legal open-access PDF.

Unpaywall is a useful last resort but is frequently wrong (it points at the
wrong file, or none), so it runs *late* — after discovery and publisher
sources. It also 422s on anything that is not a bare DOI, so the DOI is
normalised before the request and a 422/404 is treated as "no copy" rather than
an error.
"""

from __future__ import annotations

from pathlib import Path

from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin

API = "https://api.unpaywall.org/v2/"


def is_real_email(email: str) -> bool:
    """Unpaywall 422s on missing or placeholder emails, so gate on a real one."""
    email = (email or "").strip().lower()
    if "@" not in email:
        return False
    domain = email.rsplit("@", 1)[1]
    return domain not in ("example.com", "example.org", "example.net")


def normalize_doi(doi: str) -> str:
    """Reduce any DOI form to the bare ``10.xxxx/yyyy`` string Unpaywall wants."""
    cleaned = (doi or "").strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:"):
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    return cleaned.strip()


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
    priority = 70  # frequently wrong; run after discovery and publisher sources

    def can_download(self, publication: Publication) -> bool:
        return bool(publication.doi) and is_real_email(self.ctx.config.get("unpaywall_email", ""))

    def download(self, publication: Publication, dest: Path) -> DownloadResult:
        doi = normalize_doi(publication.doi)
        if not doi:
            return DownloadResult(success=False, error="no usable DOI")
        email = self.ctx.config.get("unpaywall_email", "")
        if not is_real_email(email):
            return DownloadResult(success=False, error="set a real SNAFFLE_UNPAYWALL_EMAIL")
        meta = self.ctx.http.get(f"{API}{doi}", params={"email": email})
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
