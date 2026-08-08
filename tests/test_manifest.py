from snaffle.manifest import read_manifest, write_manifest
from snaffle.models import Publication, WorkType


def test_write_then_read_roundtrip(tmp_path):
    pubs = [
        Publication(
            title="Literature Against Criticism",
            authors=["Martin Paul Eve"],
            year=2016,
            venue="Open Book Publishers",
            doi="10.11647/obp.0102",
            type=WorkType.BOOK,
            sources=["orcid"],
            extra={"orcid_verified": True},
        ),
        Publication(title="A Second Work", year=2019),
    ]
    path = write_manifest(tmp_path, "Martin Paul Eve", pubs)
    assert path.exists()
    assert path.name == "publications.json"

    loaded = read_manifest(tmp_path, "Martin Paul Eve")
    assert [p.title for p in loaded] == ["Literature Against Criticism", "A Second Work"]
    book = loaded[0]
    assert book.type == WorkType.BOOK  # enum restored, not a bare string
    assert book.doi == "10.11647/obp.0102"
    assert book.authors == ["Martin Paul Eve"]
    assert book.extra == {"orcid_verified": True}


def test_read_missing_returns_none(tmp_path):
    assert read_manifest(tmp_path, "Nobody Here") is None


def test_manifest_path_matches_author_directory(tmp_path):
    write_manifest(tmp_path, "Ada Lovelace", [Publication(title="X")])
    assert (tmp_path / "Ada Lovelace" / "publications.json").exists()
