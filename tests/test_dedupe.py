from snaffle.dedupe import (
    are_duplicates,
    deduplicate,
    merge_publications,
    normalize_title,
    publication_key,
)
from snaffle.models import Publication


def test_normalize_title_strips_punctuation_and_case():
    assert normalize_title("On the Origin, of Testing!") == normalize_title(
        "on   the origin of testing"
    )


def test_publication_key_prefers_doi():
    pub = Publication(title="X", doi="10.1/AbC")
    assert publication_key(pub) == "doi:10.1/abc"


def test_publication_key_uses_isbn_when_no_doi():
    pub = Publication(title="A Book", isbn="978-0-13-468599-1")
    assert publication_key(pub) == "isbn:9780134685991"


def test_publication_key_none_without_identifiers():
    assert publication_key(Publication(title="X")) is None


def test_duplicates_by_matching_doi():
    a = Publication(title="One title", doi="10.1/x")
    b = Publication(title="A completely different title", doi="10.1/X")
    assert are_duplicates(a, b) is True


def test_duplicates_by_fuzzy_title_and_year_without_doi():
    a = Publication(title="On the Origin of Testing", year=2026, authors=["Ada Lovelace"])
    b = Publication(title="On the origin of testing.", year=2026, authors=["A. Lovelace"])
    assert are_duplicates(a, b) is True


def test_not_duplicates_when_titles_differ():
    a = Publication(title="Alpha paper", year=2020)
    b = Publication(title="Beta paper", year=2020)
    assert are_duplicates(a, b) is False


def test_same_work_with_different_dois_still_merges():
    # A publisher DOI and a repository-deposit DOI for the same book must merge;
    # differing DOIs are not proof of different works.
    publisher = Publication(
        title="Literature Against Criticism",
        authors=["Martin Paul Eve"],
        year=2016,
        doi="10.11647/obp.0102",
    )
    deposit = Publication(
        title="Literature Against Criticism: University English and Contemporary Fiction",
        authors=["Eve, Martin Paul"],
        year=2016,
        doi="10.17613/M6DW4B",
    )
    assert are_duplicates(publisher, deposit) is True


def test_different_works_with_different_dois_stay_separate():
    a = Publication(title="Alpha study", authors=["Ada Lovelace"], year=2016, doi="10.1/a")
    b = Publication(title="Beta study", authors=["Ada Lovelace"], year=2016, doi="10.1/b")
    assert are_duplicates(a, b) is False


def test_duplicates_across_subtitle_variants():
    # The same book surfaced with and without its subtitle, from sources with
    # compatible authors and the same year — this must merge.
    a = Publication(
        title="Literature Against Criticism",
        authors=["Martin Paul Eve"],
        year=2016,
    )
    b = Publication(
        title="Literature Against Criticism: University English and Contemporary Fiction",
        authors=["Eve, Martin Paul"],
        year=2016,
    )
    assert are_duplicates(a, b) is True


def test_short_generic_prefixes_do_not_over_merge():
    # A short shared opening word must NOT merge two different works.
    a = Publication(title="Introduction", authors=["Ada Lovelace"], year=2019)
    b = Publication(title="Introduction to Analytical Engines", authors=["Ada Lovelace"], year=2019)
    assert are_duplicates(a, b) is False


def test_subtitle_variant_needs_compatible_authors():
    a = Publication(
        title="Open Access and the Humanities",
        authors=["Someone Unrelated"],
        year=2014,
    )
    b = Publication(
        title="Open Access and the Humanities: Contexts, Controversies and the Future",
        authors=["Different Person"],
        year=2014,
    )
    assert are_duplicates(a, b) is False


def test_merge_prefers_richer_metadata_and_unions_sources():
    a = Publication(title="On the Origin of Testing", year=2026, sources=["crossref"])
    b = Publication(
        title="On the Origin of Testing",
        year=2026,
        doi="10.1/x",
        venue="Journal of Software",
        sources=["openalex"],
    )
    merged = merge_publications(a, b)
    assert merged.doi == "10.1/x"
    assert merged.venue == "Journal of Software"
    assert set(merged.sources) == {"crossref", "openalex"}


def test_deduplicate_collapses_and_merges():
    pubs = [
        Publication(title="On the Origin of Testing", year=2026, sources=["crossref"]),
        Publication(
            title="on the origin of testing", year=2026, doi="10.1/x", sources=["homepage"]
        ),
        Publication(title="A separate work", year=2019, sources=["crossref"]),
    ]
    result = deduplicate(pubs)
    assert len(result) == 2
    merged = next(p for p in result if p.year == 2026)
    assert merged.doi == "10.1/x"
    assert set(merged.sources) == {"crossref", "homepage"}
