"""A fake search-only plugin used to test auto-discovery and ordering."""

from snaffle.models import Publication
from snaffle.plugins.base import Plugin, SearchCapability


class BetaPlugin(Plugin, SearchCapability):
    name = "beta"
    description = "fake beta"

    def search(self, academic):
        return [Publication(title=f"Beta work by {academic}", year=2019, sources=["beta"])]
