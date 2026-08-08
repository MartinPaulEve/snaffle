import httpx

from snaffle.models import WorkType
from snaffle.plugins.public.orcid import OrcidPlugin, parse_orcid_works
from snaffle.services import ServiceContext


class FakeResolver:
    def __init__(self, orcid):
        self._orcid = orcid

    def resolve(self, name):
        return self._orcid

WORKS = {
    "group": [
        {
            "work-summary": [
                {
                    "put-code": 1,
                    "title": {"title": {"value": "Literature Against Criticism"}},
                    "journal-title": {"value": "Open Book Publishers"},
                    "type": "BOOK",
                    "publication-date": {"year": {"value": "2016"}},
                    "external-ids": {
                        "external-id": [
                            {"external-id-type": "doi", "external-id-value": "10.11647/obp.0102"}
                        ]
                    },
                }
            ]
        },
        {
            "work-summary": [
                {
                    "put-code": 2,
                    "title": {"title": {"value": "Open Access and the Humanities"}},
                    "type": "JOURNAL-ARTICLE",
                    "publication-date": {"year": {"value": "2014"}},
                    "external-ids": {"external-id": []},
                }
            ]
        },
    ]
}


def test_parse_orcid_works_maps_fields_and_marks_verified():
    pubs = parse_orcid_works(WORKS)
    assert len(pubs) == 2
    book = pubs[0]
    assert book.title == "Literature Against Criticism"
    assert book.year == 2016
    assert book.doi == "10.11647/obp.0102"
    assert book.type == WorkType.BOOK
    assert "orcid" in book.sources
    assert book.extra.get("orcid_verified") is True


def test_orcid_plugin_fetches_the_discovered_record():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["accept"] = request.headers.get("Accept")
        return httpx.Response(200, json=WORKS)

    ctx = ServiceContext(
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        orcid_resolver=FakeResolver("0000-0002-5589-8511"),
    )
    pubs = OrcidPlugin(ctx).search("Martin Paul Eve")
    assert "0000-0002-5589-8511/works" in seen["url"]
    assert "json" in (seen["accept"] or "").lower()
    assert {p.title for p in pubs} == {
        "Literature Against Criticism",
        "Open Access and the Humanities",
    }


def test_orcid_plugin_noop_when_orcid_not_discovered():
    ctx = ServiceContext(
        http=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))),
        orcid_resolver=FakeResolver(None),
    )
    assert OrcidPlugin(ctx).search("Martin Paul Eve") == []


def test_orcid_plugin_noop_without_resolver():
    ctx = ServiceContext(
        http=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))),
    )
    assert OrcidPlugin(ctx).search("Martin Paul Eve") == []
