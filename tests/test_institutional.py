import httpx

from snaffle.services.institutional import (
    InstitutionalHarvester,
    extract_citation_pdf_url,
)


def test_extract_citation_pdf_url_from_meta():
    html = """
    <html><head>
      <meta name="citation_title" content="A Paper">
      <meta name="citation_pdf_url" content="https://publisher/article/123.pdf">
    </head><body>...</body></html>
    """
    assert extract_citation_pdf_url(html) == "https://publisher/article/123.pdf"


def test_extract_citation_pdf_url_absent():
    assert extract_citation_pdf_url("<html><head></head></html>") is None


class FakeSession:
    """Stands in for a logged-in browser session."""

    def __init__(self, pages, cookies=None, landing_url=None):
        self.pages = pages  # {url substring: html}
        self._cookies = cookies or {}
        self.visited = []
        self._current = ""
        self._landing_url = landing_url

    def get(self, url):
        self.visited.append(url)
        # Simulate EZProxy landing the browser on a proxied article page.
        self._current = self._landing_url or url

    @property
    def current_url(self):
        return self._current

    @property
    def page_source(self):
        for key, html in self.pages.items():
            if key in self._current or key in (self.visited[-1] if self.visited else ""):
                return html
        return "<html></html>"

    def cookies(self):
        return self._cookies


def test_harvest_navigates_via_ezproxy_and_downloads_pdf():
    article_html = (
        '<html><head><meta name="citation_pdf_url" '
        'content="https://tandfonline.com/doi/pdf/10.1080/x.pdf"></head></html>'
    )
    session = FakeSession(
        pages={"ezproxy": article_html},
        cookies={"ezproxy_session": "abc"},
    )

    def http_handler(request: httpx.Request) -> httpx.Response:
        # The PDF request must carry the session cookie and be proxied.
        assert request.headers.get("cookie", "").find("ezproxy_session=abc") != -1
        return httpx.Response(200, content=b"%PDF-1.5 paywalled")

    http = httpx.Client(transport=httpx.MockTransport(http_handler))
    harvester = InstitutionalHarvester(session, http, ezproxy_base="https://ezproxy.bbk.ac.uk")
    data = harvester.fetch_pdf_by_doi("10.1080/x")
    assert data.startswith(b"%PDF")
    # It routed the DOI through EZProxy.
    assert any("ezproxy.bbk.ac.uk" in u for u in session.visited)


def test_harvest_returns_none_when_no_pdf_meta():
    session = FakeSession(pages={"ezproxy": "<html><head></head></html>"})
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    harvester = InstitutionalHarvester(session, http, ezproxy_base="https://ezproxy.bbk.ac.uk")
    assert harvester.fetch_pdf_by_doi("10.1/x") is None


def test_harvest_uses_already_proxied_pdf_url_directly():
    # EZProxy sometimes rewrites the citation_pdf_url to a proxied host; that
    # URL must be used as-is, not proxied again.
    proxied_pdf = "https://www-jstor-org.ezproxy.msu.edu/stable/pdf/123.pdf"
    article_html = (
        f'<html><head><meta name="citation_pdf_url" content="{proxied_pdf}">'
        "</head></html>"
    )
    session = FakeSession(
        pages={"ezproxy.msu.edu": article_html},
        cookies={"ezproxyl": "1"},
        landing_url="https://www-jstor-org.ezproxy.msu.edu/stable/123",
    )
    requested = {}

    def handler(request: httpx.Request) -> httpx.Response:
        requested["url"] = str(request.url)
        return httpx.Response(200, content=b"%PDF-1.5")

    http = httpx.Client(transport=httpx.MockTransport(handler))
    harvester = InstitutionalHarvester(session, http, ezproxy_base="https://ezproxy.msu.edu/login?url=")
    data = harvester.fetch_pdf_by_doi("10.2307/x")
    assert data.startswith(b"%PDF")
    # Not double-proxied.
    assert requested["url"] == proxied_pdf


def test_harvest_resolves_relative_pdf_url():
    article_html = (
        '<html><head><meta name="citation_pdf_url" content="/stable/pdf/9.pdf">'
        "</head></html>"
    )
    session = FakeSession(
        pages={"ezproxy.msu.edu": article_html},
        cookies={"ezproxyl": "1"},
        landing_url="https://www-jstor-org.ezproxy.msu.edu/stable/9",
    )
    requested = {}

    def handler(request: httpx.Request) -> httpx.Response:
        requested["url"] = str(request.url)
        return httpx.Response(200, content=b"%PDF-1.5")

    http = httpx.Client(transport=httpx.MockTransport(handler))
    harvester = InstitutionalHarvester(session, http, ezproxy_base="https://ezproxy.msu.edu/login?url=")
    harvester.fetch_pdf_by_doi("10.2307/x")
    assert requested["url"] == "https://www-jstor-org.ezproxy.msu.edu/stable/pdf/9.pdf"
