"""A fake search+download plugin used to test auto-discovery."""

from pathlib import Path

from snaffle.models import DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin, SearchCapability


class AlphaPlugin(Plugin, SearchCapability, DownloadCapability):
    name = "alpha"
    description = "fake alpha"
    priority = 10

    def search(self, academic):
        return [Publication(title=f"Alpha work by {academic}", year=2026, sources=["alpha"])]

    def can_download(self, publication):
        return True

    def download(self, publication, dest: Path):
        dest.write_bytes(b"%PDF-1.4 alpha")
        return DownloadResult(success=True, path=dest)


class NotAPlugin:
    """Should be ignored by discovery."""


def helper():
    return 1
