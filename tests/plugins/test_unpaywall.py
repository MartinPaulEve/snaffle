import httpx

from snaffle.models import Publication
from snaffle.plugins.public.unpaywall import (
    UnpaywallPlugin,
    extract_oa_pdf_url,
    normalize_doi,
)
from snaffle.services import ServiceContext

RESPONSE = {
    "best_oa_location": {"url_for_pdf": "https://repo.example/paper.pdf"},
    "oa_locations": [{"url_for_pdf": "https://repo.example/paper.pdf"}],
}


def test_extract_oa_pdf_url():
    assert extract_oa_pdf_url(RESPONSE) == "https://repo.example/paper.pdf"


def test_extract_oa_pdf_url_none_when_closed():
    assert extract_oa_pdf_url({"best_oa_location": None, "oa_locations": []}) is None


def test_unpaywall_can_download_requires_doi():
    ctx = ServiceContext(http=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404))))  # noqa: E501
    plugin = UnpaywallPlugin(ctx)
    assert plugin.can_download(Publication(title="x", doi="10.1/x")) is True
    assert plugin.can_download(Publication(title="x")) is False


def test_normalize_doi_strips_prefixes_and_whitespace():
    assert normalize_doi("  https://doi.org/10.11647/OBP.0102 ") == "10.11647/OBP.0102"
    assert normalize_doi("doi:10.1/x") == "10.1/x"
    assert normalize_doi("10.1/x\n") == "10.1/x"


def test_unpaywall_priority_is_late():
    ctx = ServiceContext(http=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404))))  # noqa: E501
    # Unpaywall is frequently wrong; it must run after discovery and publishers.
    assert UnpaywallPlugin(ctx).priority > 50


def test_unpaywall_queries_clean_doi_even_when_stored_as_url(tmp_path):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if "api.unpaywall.org" in request.url.host:
            seen["path"] = request.url.path
            return httpx.Response(200, json=RESPONSE)
        return httpx.Response(200, content=b"%PDF-1.5 oa copy")

    ctx = ServiceContext(
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        config={"unpaywall_email": "ada@example.com"},
    )
    pub = Publication(title="x", doi="https://doi.org/10.1234/abc")
    UnpaywallPlugin(ctx).download(pub, tmp_path / "out.pdf")
    # The DOI, not the URL form, must be in the request path (the 422 cause).
    assert seen["path"] == "/v2/10.1234/abc"


def test_unpaywall_422_is_clean_failure(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"error": True, "message": "Invalid DOI"})

    ctx = ServiceContext(
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        config={"unpaywall_email": "ada@example.com"},
    )
    result = UnpaywallPlugin(ctx).download(
        Publication(title="x", doi="10.1234/abc"), tmp_path / "out.pdf"
    )
    assert result.success is False
    assert result.error is not None


def test_unpaywall_download_fetches_pdf(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if "api.unpaywall.org" in request.url.host:
            return httpx.Response(200, json=RESPONSE)
        if request.url.host == "repo.example":
            return httpx.Response(200, content=b"%PDF-1.5 oa copy")
        return httpx.Response(404)

    ctx = ServiceContext(
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        config={"unpaywall_email": "ada@example.com"},
    )
    plugin = UnpaywallPlugin(ctx)
    pub = Publication(title="x", doi="10.1234/abc")
    result = plugin.download(pub, tmp_path / "out.pdf")
    assert result.success is True
    assert result.path.read_bytes().startswith(b"%PDF")
