import httpx

from snaffle.models import WorkType
from snaffle.plugins.public.openalex import OpenAlexPlugin, parse_openalex_results
from snaffle.services import ServiceContext

SAMPLE = {
    "results": [
        {
            "title": "Reconstructed Titles in Open Data",
            "publication_year": 2022,
            "type": "article",
            "doi": "https://doi.org/10.5555/xyz",
            "primary_location": {"source": {"display_name": "Open Journal"}},
            "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
            "best_oa_location": {"pdf_url": "https://oa.example/paper.pdf"},
        }
    ]
}


def test_parse_openalex_results_maps_fields():
    pubs = parse_openalex_results(SAMPLE)
    assert len(pubs) == 1
    p = pubs[0]
    assert p.title == "Reconstructed Titles in Open Data"
    assert p.year == 2022
    assert p.venue == "Open Journal"
    assert p.doi == "10.5555/xyz"  # bare DOI, not the URL form
    assert p.authors == ["Ada Lovelace"]
    assert p.pdf_url == "https://oa.example/paper.pdf"
    assert p.type == WorkType.ARTICLE
    assert "openalex" in p.sources


def test_openalex_search_hits_api():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "openalex.org" in request.url.host
        return httpx.Response(200, json=SAMPLE)

    ctx = ServiceContext(http=httpx.Client(transport=httpx.MockTransport(handler)))
    pubs = OpenAlexPlugin(ctx).search("Ada Lovelace")
    assert pubs[0].title == "Reconstructed Titles in Open Data"
