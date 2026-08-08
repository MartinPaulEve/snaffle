import httpx

from snaffle.plugins.public.kcworks import KCWorksPlugin
from snaffle.services import ServiceContext

RECORD = {
    "hits": {
        "hits": [
            {
                "links": {"self": "https://works.hcommons.org/api/records/8pgtg-6ta28"},
                "metadata": {
                    "title": "A Knowledge Commons Deposit",
                    "publication_date": "2021-05-01",
                    "creators": [{"person_or_org": {"name": "Eve, Martin Paul"}}],
                },
                "files": {"entries": {"paper.pdf": {"ext": "pdf", "key": "paper.pdf"}}},
            }
        ]
    }
}


class FakeResolver:
    def __init__(self, orcid):
        self._orcid = orcid

    def resolve(self, name):
        return self._orcid


def test_kcworks_queries_by_orcid_when_known():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["q"] = request.url.params.get("q")
        return httpx.Response(200, json=RECORD)

    ctx = ServiceContext(
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        orcid_resolver=FakeResolver("0000-0002-5589-8511"),
    )
    pubs = KCWorksPlugin(ctx).search("Martin Paul Eve")
    assert "identifier:0000-0002-5589-8511" in seen["q"]
    assert pubs[0].title == "A Knowledge Commons Deposit"
    assert pubs[0].pdf_url == (
        "https://works.hcommons.org/api/records/8pgtg-6ta28/files/paper.pdf/content"
    )
    assert "kcworks" in pubs[0].sources


def test_kcworks_falls_back_to_name_query():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["q"] = request.url.params.get("q")
        return httpx.Response(200, json=RECORD)

    ctx = ServiceContext(
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        orcid_resolver=FakeResolver(None),
    )
    KCWorksPlugin(ctx).search("Martin Paul Eve")
    assert seen["q"] == '"Martin Paul Eve"'


def test_kcworks_downloads_via_presigned_url(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if "/content" in request.url.path:
            return httpx.Response(200, content=b"https://s3.amazonaws.com/kc/data?sig=1")
        if request.url.host == "s3.amazonaws.com":
            return httpx.Response(200, content=b"%PDF-1.4 deposit")
        return httpx.Response(404)

    from snaffle.models import Publication

    ctx = ServiceContext(http=httpx.Client(transport=httpx.MockTransport(handler)))
    pub = Publication(
        title="X",
        pdf_url="https://works.hcommons.org/api/records/1/files/x.pdf/content",
        sources=["kcworks"],
    )
    result = KCWorksPlugin(ctx).download(pub, tmp_path / "out.pdf")
    assert result.success is True
    assert result.path.read_bytes().startswith(b"%PDF")
