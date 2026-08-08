"""US Library of Congress plugin: search the LoC catalogue via SRU/MARCXML."""

from __future__ import annotations

from snaffle.models import Publication
from snaffle.plugins.base import Plugin, SearchCapability
from snaffle.plugins.public.britishlibrary import parse_sru_marcxml


class LibraryOfCongressPlugin(Plugin, SearchCapability):
    name = "loc"
    description = "US Library of Congress catalogue (SRU/MARCXML)"
    sru_endpoint = "http://lx2.loc.gov:210/lcdb"

    def search(self, academic: str) -> list[Publication]:
        params = {
            "version": "1.1",
            "operation": "searchRetrieve",
            "recordSchema": "marcxml",
            "maximumRecords": 50,
            "query": f'bath.author="{academic}"',
        }
        response = self.ctx.http.get(self.sru_endpoint, params=params)
        response.raise_for_status()
        pubs = parse_sru_marcxml(response.text)
        for p in pubs:
            p.sources = ["loc"]
        return pubs


__all__ = ["LibraryOfCongressPlugin", "parse_sru_marcxml"]
