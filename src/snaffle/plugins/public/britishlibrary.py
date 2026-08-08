"""British Library plugin: search the BL catalogue (books, theses) via SRU."""

from __future__ import annotations

from defusedxml import ElementTree as ET

from snaffle.models import Publication, WorkType
from snaffle.plugins.base import Plugin, SearchCapability

_MARC = "{http://www.loc.gov/MARC21/slim}"


def _subfield(datafield, code: str) -> str | None:
    for sub in datafield.findall(f"{_MARC}subfield"):
        if sub.get("code") == code:
            return (sub.text or "").strip()
    return None


def _datafield(record, tag: str):
    for df in record.findall(f"{_MARC}datafield"):
        if df.get("tag") == tag:
            return df
    return None


def _clean(value: str | None) -> str | None:
    return value.rstrip(" :,.;/").strip() if value else value


def parse_sru_marcxml(xml: str) -> list[Publication]:
    """Parse an SRU MARCXML response into Publications (shared MARC helper)."""
    root = ET.fromstring(xml)
    pubs = []
    for record in root.iter(f"{_MARC}record"):
        title_df = _datafield(record, "245")
        if title_df is None:
            continue
        title_a = _clean(_subfield(title_df, "a")) or ""
        title_b = _clean(_subfield(title_df, "b"))
        title = f"{title_a}: {title_b}" if title_b else title_a
        if not title:
            continue

        author_df = _datafield(record, "100")
        authors = [_clean(_subfield(author_df, "a"))] if author_df is not None else []

        pub_df = _datafield(record, "260")
        if pub_df is None:
            pub_df = _datafield(record, "264")
        publisher = _clean(_subfield(pub_df, "b")) if pub_df is not None else None
        year = None
        if pub_df is not None:
            date_raw = _subfield(pub_df, "c") or ""
            digits = "".join(ch for ch in date_raw if ch.isdigit())[:4]
            year = int(digits) if len(digits) == 4 else None

        isbn_df = _datafield(record, "020")
        isbn = _clean(_subfield(isbn_df, "a")) if isbn_df is not None else None

        pubs.append(
            Publication(
                title=title,
                authors=[a for a in authors if a],
                year=year,
                publisher=publisher,
                isbn=isbn,
                type=WorkType.BOOK,
                sources=["britishlibrary"],
            )
        )
    return pubs


class BritishLibraryPlugin(Plugin, SearchCapability):
    name = "britishlibrary"
    description = "British Library catalogue (SRU/MARCXML)"
    sru_endpoint = "http://sru.bl.uk/SRU"

    def search(self, academic: str) -> list[Publication]:
        params = {
            "version": "1.2",
            "operation": "searchRetrieve",
            "recordSchema": "marcxml",
            "maximumRecords": 50,
            "query": f'dc.creator="{academic}"',
        }
        response = self.ctx.http.get(self.sru_endpoint, params=params)
        response.raise_for_status()
        pubs = parse_sru_marcxml(response.text)
        for p in pubs:
            p.sources = ["britishlibrary"]
        return pubs
