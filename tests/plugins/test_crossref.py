import httpx

from snaffle.models import WorkType
from snaffle.plugins.public.crossref import CrossRefPlugin, parse_crossref_items
from snaffle.services import ServiceContext

SAMPLE = {
    "message": {
        "items": [
            {
                "title": ["On the Origin of Testing"],
                "author": [
                    {"given": "Ada", "family": "Lovelace"},
                    {"given": "Charles", "family": "Babbage"},
                ],
                "issued": {"date-parts": [[2026, 3]]},
                "container-title": ["Journal of Software"],
                "publisher": "Test Press",
                "DOI": "10.1234/abc.def",
                "type": "journal-article",
                "volume": "12",
                "issue": "3",
                "page": "45-67",
            },
            {
                "title": ["A Monograph"],
                "author": [{"given": "Ada", "family": "Lovelace"}],
                "issued": {"date-parts": [[2020]]},
                "publisher": "Book Press",
                "DOI": "10.1234/book",
                "type": "monograph",
            },
        ]
    }
}


def test_parse_crossref_items_maps_fields():
    pubs = parse_crossref_items(SAMPLE)
    assert len(pubs) == 2
    art = pubs[0]
    assert art.title == "On the Origin of Testing"
    assert art.authors == ["Ada Lovelace", "Charles Babbage"]
    assert art.year == 2026
    assert art.venue == "Journal of Software"
    assert art.doi == "10.1234/abc.def"
    assert art.volume == "12"
    assert art.pages == "45-67"
    assert art.type == WorkType.ARTICLE
    assert "crossref" in art.sources


def test_parse_crossref_maps_book_type():
    pubs = parse_crossref_items(SAMPLE)
    assert pubs[1].type == WorkType.BOOK


def test_crossref_search_hits_api_and_parses():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "crossref.org" in request.url.host
        assert "Ada+Lovelace" in str(request.url) or "Ada%20Lovelace" in str(request.url)
        return httpx.Response(200, json=SAMPLE)

    ctx = ServiceContext(http=httpx.Client(transport=httpx.MockTransport(handler)))
    plugin = CrossRefPlugin(ctx)
    pubs = plugin.search("Ada Lovelace")
    assert {p.title for p in pubs} == {"On the Origin of Testing", "A Monograph"}
