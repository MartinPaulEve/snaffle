"""Citation formatting, the HTML bibliography, and the failure report."""

from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import urlencode

from snaffle.models import Publication, WorkType


def _author_list(pub: Publication) -> str:
    if not pub.authors:
        return ""
    if len(pub.authors) == 1:
        return pub.authors[0]
    return ", ".join(pub.authors[:-1]) + ", and " + pub.authors[-1]


def format_citation(pub: Publication, style: str = "chicago") -> str:
    """Format one publication as a citation string in the given style."""
    authors = _author_list(pub)
    year = f"({pub.year})" if pub.year else "(n.d.)"
    bits: list[str] = []
    if authors:
        bits.append(f"{authors}.")
    bits.append(f"{year}.")
    bits.append(f"“{pub.title}.”" if pub.type != WorkType.BOOK else f"{pub.title}.")
    if pub.venue:
        vol = f" {pub.volume}" if pub.volume else ""
        issue = f", no. {pub.issue}" if pub.issue else ""
        pages = f": {pub.pages}" if pub.pages else ""
        bits.append(f"{pub.venue}{vol}{issue}{pages}.")
    elif pub.publisher:
        bits.append(f"{pub.publisher}.")
    if pub.doi:
        bits.append(f"https://doi.org/{pub.doi}")
    return " ".join(bits)


def coins_span(pub: Publication) -> str:
    """Return a COinS <span> (Zotero/OpenURL) encoding the publication."""
    is_book = pub.type == WorkType.BOOK
    fields: list[tuple[str, str]] = [
        ("ctx_ver", "Z39.88-2004"),
        ("rft_val_fmt", "info:ofi/fmt:kev:mtx:book" if is_book else "info:ofi/fmt:kev:mtx:journal"),
        ("rft.genre", "book" if is_book else "article"),
    ]
    if is_book:
        fields.append(("rft.btitle", pub.title))
    else:
        fields.append(("rft.atitle", pub.title))
        if pub.venue:
            fields.append(("rft.jtitle", pub.venue))
    if pub.year:
        fields.append(("rft.date", str(pub.year)))
    for attr, key in (("volume", "rft.volume"), ("issue", "rft.issue"), ("pages", "rft.pages")):
        val = getattr(pub, attr)
        if val:
            fields.append((key, val))
    if pub.publisher:
        fields.append(("rft.pub", pub.publisher))
    if pub.isbn:
        fields.append(("rft.isbn", pub.isbn))
    for author in pub.authors:
        fields.append(("rft.au", author))
    if pub.doi:
        fields.append(("rft_id", f"info:doi/{pub.doi}"))

    title_attr = urlencode(fields, quote_via=_plus_quote)
    return f'<span class="Z3988" title="{html.escape(title_attr, quote=True)}"></span>'


def _plus_quote(string, safe="", encoding=None, errors=None):
    from urllib.parse import quote_plus

    # Keep ':' and '/' literal so info: URIs (e.g. info:doi/...) stay readable.
    return quote_plus(string, safe + ":/", encoding, errors)


def render_bibliography_html(author: str, pubs: list[Publication], style: str = "chicago") -> str:
    """Full HTML page listing the publications, with embedded COinS metadata."""
    ordered = sorted(pubs, key=lambda p: (-(p.year or 0), p.title.lower()))
    items = []
    for pub in ordered:
        citation = html.escape(format_citation(pub, style))
        items.append(f"    <li>{citation}\n      {coins_span(pub)}\n    </li>")
    body = "\n".join(items)
    safe_author = html.escape(author)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>Publications of {safe_author}</title>\n"
        "</head>\n<body>\n"
        f"<h1>Publications of {safe_author}</h1>\n"
        f'<ol class="bibliography">\n{body}\n</ol>\n'
        "</body>\n</html>\n"
    )


def write_bibliography(output_dir: Path, author: str, pubs: list[Publication], style: str) -> Path:
    from snaffle.output import ensure_author_dir

    author_dir = ensure_author_dir(output_dir, author)
    path = author_dir / "bibliography.html"
    path.write_text(render_bibliography_html(author, pubs, style), encoding="utf-8")
    return path


def render_failures(failed: list[Publication]) -> str:
    """Plain-text report of publications whose full text could not be fetched."""
    if not failed:
        return "All publications were retrieved successfully.\n"
    lines = ["Publications whose full text could not be retrieved:", ""]
    for pub in sorted(failed, key=lambda p: (-(p.year or 0), p.title.lower())):
        year = pub.year or "n.d."
        doi = f" [doi:{pub.doi}]" if pub.doi else ""
        lines.append(f"- ({year}) {pub.title}{doi}")
    return "\n".join(lines) + "\n"


def write_failures(output_dir: Path, author: str, failed: list[Publication]) -> Path:
    from snaffle.output import ensure_author_dir

    author_dir = ensure_author_dir(output_dir, author)
    path = author_dir / "failures.txt"
    path.write_text(render_failures(failed), encoding="utf-8")
    return path
