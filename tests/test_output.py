from pathlib import Path

from snaffle.models import Publication
from snaffle.output import (
    already_downloaded,
    build_filename,
    ensure_author_dir,
    nuke_author_dir,
    publication_path,
    sanitize_component,
)


def test_sanitize_component_removes_path_separators():
    assert "/" not in sanitize_component("a/b")
    assert "\\" not in sanitize_component("a\\b")


def test_sanitize_component_collapses_and_trims():
    assert sanitize_component("  Journal:  of   Software  ") == "Journal of Software"


def test_build_filename_uses_author_venue_year_title():
    pub = Publication(
        title="On the Origin of Testing",
        venue="Journal of Software",
        year=2026,
    )
    name = build_filename(pub, author="Ada Lovelace")
    assert name == "Ada Lovelace - Journal of Software - 2026 - On the Origin of Testing.pdf"


def test_build_filename_prefers_publisher_when_no_venue():
    pub = Publication(title="A Book", publisher="Test Press", year=2020, venue=None)
    name = build_filename(pub, author="Ada Lovelace")
    assert name == "Ada Lovelace - Test Press - 2020 - A Book.pdf"


def test_publication_path_groups_by_year(tmp_path: Path):
    pub = Publication(title="T", venue="V", year=2026)
    path = publication_path(tmp_path, "Ada Lovelace", pub, "pdf")
    assert path.parent == tmp_path / "Ada Lovelace" / "2026"
    assert path.name.endswith(".pdf")


def test_already_downloaded_true_when_file_exists(tmp_path: Path):
    pub = Publication(title="On the Origin of Testing", venue="Journal of Software", year=2026)
    path = publication_path(tmp_path, "Ada Lovelace", pub, "pdf")
    path.parent.mkdir(parents=True)
    path.write_bytes(b"%PDF-1.4 fake")
    assert already_downloaded(tmp_path, "Ada Lovelace", pub) is True


def test_already_downloaded_true_for_other_extension(tmp_path: Path):
    pub = Publication(title="On the Origin of Testing", venue="Journal of Software", year=2026)
    docx = publication_path(tmp_path, "Ada Lovelace", pub, "docx")
    docx.parent.mkdir(parents=True)
    docx.write_bytes(b"fake docx")
    assert already_downloaded(tmp_path, "Ada Lovelace", pub) is True


def test_already_downloaded_false_when_absent(tmp_path: Path):
    pub = Publication(title="Missing", venue="V", year=2000)
    assert already_downloaded(tmp_path, "Ada Lovelace", pub) is False


def test_nuke_removes_existing_author_dir(tmp_path: Path):
    author_dir = ensure_author_dir(tmp_path, "Ada Lovelace")
    (author_dir / "2020").mkdir()
    (author_dir / "2020" / "paper.pdf").write_bytes(b"%PDF")
    # A sibling academic must be untouched.
    other = ensure_author_dir(tmp_path, "Charles Babbage")

    assert nuke_author_dir(tmp_path, "Ada Lovelace") is True
    assert not author_dir.exists()
    assert other.exists()


def test_nuke_absent_returns_false(tmp_path: Path):
    assert nuke_author_dir(tmp_path, "Nobody") is False
