"""Plugin interface contracts.

A plugin is a class inheriting from :class:`Plugin` plus one or both of the
capability mixins. Any such class defined in a module inside a scanned plugin
directory is registered automatically — no manual registration step.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from snaffle.models import DownloadResult, Publication

if TYPE_CHECKING:
    from snaffle.services import ServiceContext


class Plugin:
    """Base class for all plugins."""

    #: Unique machine name, used by --only/--disable on the CLI.
    name: str = ""
    #: Human-readable description shown by --list-plugins.
    description: str = ""

    def __init__(self, ctx: ServiceContext) -> None:
        self.ctx = ctx


class SearchCapability:
    """Mixin: the plugin can build a list of an academic's outputs."""

    def search(self, academic: str) -> list[Publication]:
        raise NotImplementedError


class DownloadCapability:
    """Mixin: the plugin can fetch a digital copy of a publication."""

    #: Lower runs earlier. Sources likely to hold the version of record
    #: should be below 50; preprint servers should be above.
    priority: int = 50

    def can_download(self, publication: Publication) -> bool:
        raise NotImplementedError

    def download(self, publication: Publication, dest: Path) -> DownloadResult:
        raise NotImplementedError


def is_search_plugin(obj: object) -> bool:
    """True if ``obj`` (class or instance) provides the search capability."""
    cls = obj if isinstance(obj, type) else type(obj)
    return issubclass(cls, Plugin) and issubclass(cls, SearchCapability)


def is_download_plugin(obj: object) -> bool:
    """True if ``obj`` (class or instance) provides the download capability."""
    cls = obj if isinstance(obj, type) else type(obj)
    return issubclass(cls, Plugin) and issubclass(cls, DownloadCapability)
