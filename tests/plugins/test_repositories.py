"""Parser tests for repository-style plugins."""

from snaffle.models import WorkType
from snaffle.plugins.public.digitalcommons import parse_bepress_author_page
from snaffle.plugins.public.eprints import parse_eprints_export
from snaffle.plugins.public.inveniordm import parse_invenio_hits
from snaffle.plugins.public.openlibrary import parse_openlibrary_search
from snaffle.plugins.public.pure import parse_pure_results

# Shaped like a real InvenioRDM/KCWorks record: file entries carry no
# links.content, so the download URL must be built from the record self-link.
INVENIO = {
    "hits": {
        "hits": [
            {
                "links": {
                    "self": "https://works.hcommons.org/api/records/8pgtg-6ta28",
                    "self_html": "https://works.hcommons.org/records/8pgtg-6ta28",
                },
                "metadata": {
                    "title": "Repository Deposit One",
                    "publication_date": "2026-02-01",
                    "creators": [{"person_or_org": {"name": "Lovelace, Ada"}}],
                },
                "pids": {"doi": {"identifier": "10.59348/xyz"}},
                "files": {
                    "entries": {
                        "notes.md": {"ext": "md", "key": "notes.md"},
                        "paper one.pdf": {"ext": "pdf", "key": "paper one.pdf",
                                          "mimetype": "application/pdf"},
                    }
                },
            }
        ]
    }
}


def test_parse_invenio_hits_builds_content_url_and_picks_pdf():
    pubs = parse_invenio_hits(INVENIO)
    assert pubs[0].title == "Repository Deposit One"
    assert pubs[0].year == 2026
    # The PDF entry is chosen over the markdown one, and the download URL is the
    # record's file-content endpoint (space in the key percent-encoded).
    assert pubs[0].pdf_url == (
        "https://works.hcommons.org/api/records/8pgtg-6ta28/files/paper%20one.pdf/content"
    )
    assert pubs[0].doi == "10.59348/xyz"
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
