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

    def __init__(self, pages, cookies=None):
        self.pages = pages  # {url substring: html}
        self._cookies = cookies or {}
        self.visited = []

    def get(self, url):
        self.visited.append(url)
        self._current = url

    @property
    def page_source(self):
        for key, html in self.pages.items():
            if key in self._current:
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
