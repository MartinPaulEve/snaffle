import httpx

from snaffle.plugins.public.kcworks import KCWorksPlugin
from snaffle.services import ServiceContext

INVENIO = {
    "hits": {
        "hits": [
            {
                "metadata": {
                    "title": "A Knowledge Commons Deposit",
                    "publication_date": "2021-05-01",
                    "creators": [{"person_or_org": {"name": "Eve, Martin Paul"}}],
                },
                "files": {"entries": {"paper.pdf": {"links": {"content": "https://works/paper.pdf"}}}},
            }
        ]
    }
}


def test_kcworks_searches_hcommons_records_api():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["host"] = request.url.host
        seen["q"] = request.url.params.get("q")
        return httpx.Response(200, json=INVENIO)

    ctx = ServiceContext(http=httpx.Client(transport=httpx.MockTransport(handler)))
    pubs = KCWorksPlugin(ctx).search("Martin Paul Eve")
    assert "hcommons.org" in seen["host"]
    assert seen["q"] == "Martin Paul Eve"
    assert pubs[0].title == "A Knowledge Commons Deposit"
    assert pubs[0].pdf_url == "https://works/paper.pdf"
    assert "kcworks" in pubs[0].sources
