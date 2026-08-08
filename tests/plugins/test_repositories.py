"""Parser tests for repository-style plugins."""

from snaffle.models import WorkType
from snaffle.plugins.public.digitalcommons import parse_bepress_author_page
from snaffle.plugins.public.eprints import parse_eprints_export
from snaffle.plugins.public.inveniordm import parse_invenio_hits
from snaffle.plugins.public.openlibrary import parse_openlibrary_search
from snaffle.plugins.public.pure import parse_pure_results

INVENIO = {
    "hits": {
        "hits": [
            {
                "metadata": {
                    "title": "Repository Deposit One",
                    "publication_date": "2026-02-01",
                    "creators": [{"person_or_org": {"name": "Lovelace, Ada"}}],
                },
                "files": {"entries": {"paper.pdf": {"links": {"content": "https://repo/paper.pdf"}}}},
            }
        ]
    }
}


def test_parse_invenio_hits():
    pubs = parse_invenio_hits(INVENIO)
    assert pubs[0].title == "Repository Deposit One"
    assert pubs[0].year == 2026
    assert pubs[0].pdf_url == "https://repo/paper.pdf"
    assert "inveniordm" in pubs[0].sources


EPRINTS = [
    {
        "title": "An EPrints Item",
        "date": "2021-06-30",
        "creators": [{"name": {"given": "Ada", "family": "Lovelace"}}],
        "documents": [{"files": [{"url": "https://eprints/item.pdf"}]}],
    }
]


def test_parse_eprints_export():
    pubs = parse_eprints_export(EPRINTS)
    assert pubs[0].title == "An EPrints Item"
    assert pubs[0].year == 2021
    assert pubs[0].pdf_url == "https://eprints/item.pdf"


BEPRESS_HTML = """
<html><body>
<div class="article-listing">
  <a href="https://commons.example/article/1">A Bepress Article</a>
</div>
<div class="article-listing">
  <a href="https://commons.example/article/2">Another Deposit</a>
</div>
</body></html>
"""


def test_parse_bepress_author_page():
    pubs = parse_bepress_author_page(BEPRESS_HTML)
    titles = {p.title for p in pubs}
    assert "A Bepress Article" in titles
    assert "Another Deposit" in titles


PURE = {
    "items": [
        {
            "title": {"value": "A Pure Output"},
            "publicationStatuses": [{"publicationDate": {"year": 2018}}],
            "type": {"term": {"text": [{"value": "Book"}]}},
        }
    ]
}


def test_parse_pure_results():
    pubs = parse_pure_results(PURE)
    assert pubs[0].title == "A Pure Output"
    assert pubs[0].year == 2018
    assert pubs[0].type == WorkType.BOOK


OPENLIB = {
    "docs": [
        {
            "title": "A Scholarly Book",
            "first_publish_year": 2005,
            "author_name": ["Ada Lovelace"],
            "isbn": ["9780134685991"],
            "publisher": ["Academic Press"],
        }
    ]
}


def test_parse_openlibrary_search_returns_books():
    pubs = parse_openlibrary_search(OPENLIB)
    assert pubs[0].title == "A Scholarly Book"
    assert pubs[0].year == 2005
    assert pubs[0].isbn == "9780134685991"
    assert pubs[0].type == WorkType.BOOK
