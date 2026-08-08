import httpx

from snaffle.models import WorkType
from snaffle.plugins.public.openalex import (
    OpenAlexPlugin,
    normalize_work_id,
    parse_openalex_results,
)
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


def test_normalize_work_id_handles_url_and_bare_forms():
    assert normalize_work_id("https://openalex.org/W568507393") == "W568507393"
    assert normalize_work_id("W568507393") == "W568507393"


EXCLUDE_SAMPLE = {
    "results": [
        {
            "id": "https://openalex.org/W568507393",
            "title": "Background to contemporary Greece",
            "publication_year": 1990,
            "authorships": [{"author": {"display_name": "Martin Paul Eve"}}],
        },
        {
            "id": "https://openalex.org/W999",
            "title": "A Real Work",
            "publication_year": 2016,
            "authorships": [{"author": {"display_name": "Martin Paul Eve"}}],
        },
    ]
}


def _exclude_ctx(excludes):
    handler = lambda r: httpx.Response(200, json=EXCLUDE_SAMPLE)  # noqa: E731
    return ServiceContext(
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        config={"openalex_excludes": excludes},
    )


def test_search_drops_excluded_work_for_that_academic():
    ctx = _exclude_ctx({"Martin Paul Eve": ["W568507393"]})
    titles = [p.title for p in OpenAlexPlugin(ctx).search("Martin Paul Eve")]
    assert titles == ["A Real Work"]


def test_exclude_is_scoped_to_the_named_academic():
    # The same work is NOT excluded when searching for a different academic.
    ctx = _exclude_ctx({"Someone Else": ["W568507393"]})
    titles = [p.title for p in OpenAlexPlugin(ctx).search("Martin Paul Eve")]
    assert "Background to contemporary Greece" in titles
