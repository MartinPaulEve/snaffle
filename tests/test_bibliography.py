from pathlib import Path

from snaffle.bibliography import (
    coins_span,
    format_citation,
    render_bibliography_html,
    render_failures,
    write_bibliography,
)
from snaffle.models import Publication


def a_pub():
    return Publication(
        title="On the Origin of Testing",
        authors=["Ada Lovelace"],
        year=2026,
        venue="Journal of Software",
        volume="12",
        issue="3",
        pages="45-67",
        doi="10.1234/abc",
    )


def test_format_citation_contains_key_fields():
    c = format_citation(a_pub(), style="chicago")
    assert "Lovelace" in c
    assert "On the Origin of Testing" in c
    assert "Journal of Software" in c
    assert "2026" in c


def test_coins_span_is_zotero_importable():
    span = coins_span(a_pub())
    # COinS uses a span with class Z3988 and an OpenURL ctx in the title attr.
    assert 'class="Z3988"' in span
    assert "rft.atitle=On+the+Origin+of+Testing" in span or "On%20the%20Origin" in span
    assert "info:doi/10.1234/abc" in span or "rft_id=info:doi/10.1234/abc" in span


def test_bibliography_html_lists_all_and_embeds_coins():
    pubs = [a_pub(), Publication(title="Second Work", authors=["Ada Lovelace"], year=2019)]
    html = render_bibliography_html("Ada Lovelace", pubs)
    assert "On the Origin of Testing" in html
    assert "Second Work" in html
    assert html.count('class="Z3988"') == 2
    assert "<html" in html.lower()


def test_write_bibliography_creates_file(tmp_path: Path):
    path = write_bibliography(tmp_path, "Ada Lovelace", [a_pub()], "chicago")
    assert path.exists()
    assert path.suffix == ".html"
    assert "On the Origin of Testing" in path.read_text(encoding="utf-8")


def test_render_failures_lists_titles():
    failed = [Publication(title="Cannot Find Me", year=2001)]
    report = render_failures(failed)
    assert "Cannot Find Me" in report
