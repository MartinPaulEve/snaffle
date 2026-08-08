from pathlib import Path

import pytest

from snaffle.manifest import read_manifest, write_manifest
from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.output import publication_path
from snaffle.pipeline import (
    download_from_manifest,
    download_one,
    download_phase,
    run,
    run_search,
    search_phase,
)


class FakeSearch:
    def __init__(self, name, pubs):
        self.name = name
        self._pubs = pubs

    def search(self, academic):
        return self._pubs


class RecordingDownloader:
    def __init__(self, name, priority, succeeds, quality=CopyQuality.FINAL, ext="pdf"):
        self.name = name
        self.priority = priority
        self.succeeds = succeeds
        self.quality = quality
        self.ext = ext
        self.calls = 0

    def can_download(self, publication):
        return True

    def download(self, publication, dest: Path):
        self.calls += 1
        if not self.succeeds:
            return DownloadResult(success=False, error="no copy")
        dest = dest.with_suffix("." + self.ext)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"%PDF fake")
        return DownloadResult(success=True, path=dest, quality=self.quality)


def test_run_search_merges_and_dedupes():
    p = Publication(title="Shared Work", year=2026, doi="10.1/x")
    p2 = Publication(title="shared work", year=2026, sources=["b"])
    plugins = [FakeSearch("a", [p]), FakeSearch("b", [p2])]
    result = run_search(plugins, "Ada Lovelace")
    assert len(result) == 1


def test_run_search_drops_author_mismatches():
    real = Publication(
        title="Literature Against Criticism",
        authors=["Martin Paul Eve"],
        year=2016,
    )
    false_positive = Publication(
        title="Relationship between Number of Medical Conditions and Quality of Care",
        authors=["Eve A. Kerr", "Martín Roland", "Paul G Shekelle"],
        year=2007,
    )
    plugins = [FakeSearch("crossref", [real, false_positive])]
    result = run_search(plugins, "Martin Paul Eve")
    titles = [p.title for p in result]
    assert "Literature Against Criticism" in titles
    assert all("Medical Conditions" not in t for t in titles)


def test_run_search_keeps_authorless_results():
    # A homepage/repository hit with no author list is trusted.
    pub = Publication(title="Some Book", authors=[], year=2010)
    result = run_search([FakeSearch("homepage", [pub])], "Martin Paul Eve")
    assert [p.title for p in result] == ["Some Book"]


def test_run_search_keeps_orcid_verified_even_with_mismatched_authors():
    # An ORCID-record work is authoritative; keep it even if the author string
    # would otherwise fail name matching.
    pub = Publication(
        title="A Genuine Work",
        authors=["Someone Else"],
        year=2016,
        extra={"orcid_verified": True},
    )
    result = run_search([FakeSearch("orcid", [pub])], "Martin Paul Eve")
    assert [p.title for p in result] == ["A Genuine Work"]


def test_download_one_stops_at_first_success(tmp_path: Path):
    pub = Publication(title="T", venue="V", year=2026)
    early = RecordingDownloader("early", priority=10, succeeds=True)
    late = RecordingDownloader("late", priority=90, succeeds=True)
    result = download_one([early, late], pub, tmp_path, "Ada Lovelace")
    assert result.success is True
    assert early.calls == 1
    assert late.calls == 0  # blocked by the first success


def test_download_one_falls_through_to_next_on_failure(tmp_path: Path):
    pub = Publication(title="T", venue="V", year=2026)
    failing = RecordingDownloader("f", priority=10, succeeds=False)
    working = RecordingDownloader("w", priority=20, succeeds=True)
    result = download_one([failing, working], pub, tmp_path, "Ada Lovelace")
    assert result.success is True
    assert failing.calls == 1
    assert working.calls == 1


def test_run_skips_already_downloaded(tmp_path: Path):
    pub = Publication(title="Existing", venue="V", year=2026)
    existing = publication_path(tmp_path, "Ada Lovelace", pub, "pdf")
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"%PDF already here")

    dl = RecordingDownloader("d", priority=10, succeeds=True)
    report = run(
        "Ada Lovelace",
        tmp_path,
        search_plugins=[FakeSearch("s", [pub])],
        download_plugins=[dl],
    )
    assert dl.calls == 0  # incremental: not re-downloaded
    assert pub.title in [p.title for p in report.downloaded]


def test_run_records_failures(tmp_path: Path):
    pub = Publication(title="Unfindable", venue="V", year=2026)
    dl = RecordingDownloader("d", priority=10, succeeds=False)
    report = run(
        "Ada Lovelace",
        tmp_path,
        search_plugins=[FakeSearch("s", [pub])],
        download_plugins=[dl],
    )
    assert [p.title for p in report.failed] == ["Unfindable"]
    assert report.downloaded == []


def test_run_writes_bibliography_and_failure_report(tmp_path: Path):
    found = Publication(title="Found", venue="V", year=2026)
    missing = Publication(title="Missing", venue="V", year=2025)

    def dl_can(pub):
        return pub.title == "Found"

    class Selective(RecordingDownloader):
        def can_download(self, publication):
            return publication.title == "Found"

    dl = Selective("d", priority=10, succeeds=True)
    run(
        "Ada Lovelace",
        tmp_path,
        search_plugins=[FakeSearch("s", [found, missing])],
        download_plugins=[dl],
    )
    author_dir = tmp_path / "Ada Lovelace"
    assert (author_dir / "bibliography.html").exists()
    failures = (author_dir / "failures.txt").read_text(encoding="utf-8")
    assert "Missing" in failures
    assert "Found" not in failures


def test_search_phase_writes_manifest_and_bibliography_without_downloading(tmp_path: Path):
    pub = Publication(title="A Work", venue="V", year=2026, authors=["Ada Lovelace"])
    report = search_phase("Ada Lovelace", tmp_path, [FakeSearch("s", [pub])])

    author_dir = tmp_path / "Ada Lovelace"
    assert (author_dir / "bibliography.html").exists()
    saved = read_manifest(tmp_path, "Ada Lovelace")
    assert [p.title for p in saved] == ["A Work"]
    # A pure search neither downloads nor writes a failure report.
    assert report.downloaded == []
    assert not (author_dir / "failures.txt").exists()


def test_failed_downloads_leave_no_empty_year_directory(tmp_path: Path):
    pub = Publication(title="Unfindable", venue="V", year=2026)
    dl = RecordingDownloader("d", priority=10, succeeds=False)
    download_phase("Ada Lovelace", tmp_path, [dl], [pub])
    # A work that could not be downloaded must not leave an empty year folder.
    assert not (tmp_path / "Ada Lovelace" / "2026").exists()


def test_download_phase_downloads_the_supplied_list(tmp_path: Path):
    pub = Publication(title="A Work", venue="V", year=2026)
    dl = RecordingDownloader("d", priority=10, succeeds=True)
    report = download_phase("Ada Lovelace", tmp_path, [dl], [pub])
    assert dl.calls == 1
    assert [p.title for p in report.downloaded] == ["A Work"]


def test_download_from_manifest_reads_saved_list(tmp_path: Path):
    pub = Publication(title="Saved Work", venue="V", year=2026)
    write_manifest(tmp_path, "Ada Lovelace", [pub])
    dl = RecordingDownloader("d", priority=10, succeeds=True)
    report = download_from_manifest("Ada Lovelace", tmp_path, [dl])
    assert [p.title for p in report.downloaded] == ["Saved Work"]


def test_download_from_manifest_errors_without_a_manifest(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        download_from_manifest("Never Searched", tmp_path, [])
