"""Institutional-homepage plugin: scrape an academic's staff publication list."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from snaffle.models import Publication
from snaffle.plugins.base import Plugin, SearchCapability
from snaffle.plugins.public._helpers import first_year

_YEAR_PAREN = re.compile(r"\((1[5-9]\d{2}|20\d{2})\)")


def parse_publication_list(html: str, base_url: str = "") -> list[Publication]:
    """Heuristically extract publications from a staff-page HTML fragment.

    Looks for list items that look like citations: a year in parentheses plus
    a title. Deliberately permissive — homepages vary wildly.
    """
    soup = BeautifulSoup(html, "html.parser")
    pubs = []
    for li in soup.find_all("li"):
        text = " ".join(li.get_text(" ", strip=True).split())
        if not _YEAR_PAREN.search(text):
            continue
        year = first_year(text)
        title = _extract_title(text)
        if not title:
            continue
        venue = None
        italic = li.find("i") or li.find("em")
        if italic:
            venue = italic.get_text(strip=True)
        pubs.append(
            Publication(title=title, year=year, venue=venue, sources=["homepage"])
        )
    return pubs


def _extract_title(text: str) -> str | None:
    """Take the sentence after the year-in-parens as the title."""
    parts = _YEAR_PAREN.split(text, maxsplit=1)
    tail = parts[-1].lstrip(" .")
    # Title is up to the first full stop that ends a clause.
    title = re.split(r"\.\s", tail, maxsplit=1)[0].strip(" .")
    return title or None


class HomepagePlugin(Plugin, SearchCapability):
    name = "homepage"
    description = "Institutional staff homepage publication list"

    def search(self, academic: str) -> list[Publication]:
        url = self.ctx.config.get("homepage_url")
        if not url:
            return []
        response = self.ctx.http.get(url)
        response.raise_for_status()
        return parse_publication_list(response.text, base_url=url)
