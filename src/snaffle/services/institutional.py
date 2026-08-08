"""Harvest paywalled PDFs through an authenticated institutional browser session.

The design avoids per-publisher scraping: once the browser is logged in through
the institution's EZProxy, navigating to a work's article page and reading its
``<meta name="citation_pdf_url">`` tag yields the direct PDF URL on almost every
scholarly platform (JSTOR, Project MUSE, Taylor & Francis, OUP, De Gruyter, …).
The file is then downloaded with the browser's session cookies.
"""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from snaffle.fetch import looks_like_pdf
from snaffle.services.ezproxy import build_proxied_url


def extract_citation_pdf_url(html: str) -> str | None:
    """Return the ``citation_pdf_url`` meta value, if the page declares one."""
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


class InstitutionalHarvester:
    """Uses a logged-in browser session to fetch PDFs behind a paywall."""

    def __init__(self, session, http, ezproxy_base: str) -> None:
        self.session = session
        self.http = http
        self.ezproxy_base = ezproxy_base

    def _proxied(self, url: str) -> str:
        return build_proxied_url(url, self.ezproxy_base)

    def _proxy_host(self) -> str:
        return urlparse(self.ezproxy_base).netloc

    def fetch_pdf_by_doi(self, doi: str) -> bytes | None:
        return self.fetch_pdf(f"https://doi.org/{doi}")

    def fetch_pdf(self, article_url: str) -> bytes | None:
        # Land on the article through EZProxy so the session is authorised.
        self.session.get(self._proxied(article_url))
        pdf_url = extract_citation_pdf_url(self.session.page_source)
        if not pdf_url:
            return None

        # Resolve relative links against the (proxied) article page, and only
        # add the proxy prefix when the URL is not already going through it.
        pdf_url = urljoin(self.session.current_url, pdf_url)
        proxy_host = self._proxy_host()
        if proxy_host and proxy_host in urlparse(pdf_url).netloc:
            fetch_url = pdf_url
        else:
            fetch_url = self._proxied(pdf_url)

        cookies = self.session.cookies()
        headers = {}
        if cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
        response = self.http.get(fetch_url, headers=headers)
        if response.status_code != 200 or not looks_like_pdf(response.content):
            return None
        return response.content
