import httpx

from snaffle.models import Publication
from snaffle.plugins.public.unpaywall import UnpaywallPlugin, extract_oa_pdf_url
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
