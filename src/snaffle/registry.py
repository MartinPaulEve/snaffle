"""Automatic discovery of plugin classes in the public/private directories."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

from snaffle.plugins.base import (
    DownloadCapability,
    Plugin,
    SearchCapability,
    is_download_plugin,
    is_search_plugin,
)


def _load_module_from_path(path: Path):
    spec = importlib.util.spec_from_file_location(f"snaffle_plugin_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_plugin_classes(package_dirs: list[Path]) -> list[type]:
    """Import every module under the given dirs and return all plugin classes."""
    found: list[type] = []
    seen: set[str] = set()
    for directory in package_dirs:
        directory = Path(directory)
        if not directory.is_dir():
            continue
        for py in sorted(directory.glob("*.py")):
            if py.name.startswith("_"):
                continue
            module = _load_module_from_path(py)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj is Plugin or not issubclass(obj, Plugin):
                    continue
                if not (is_search_plugin(obj) or is_download_plugin(obj)):
                    continue
                key = f"{obj.__module__}.{obj.__name__}"
                if key not in seen:
                    seen.add(key)
                    found.append(obj)
    return found


def instantiate_plugins(
    classes: list[type],
    ctx,
    only: list[str] | None = None,
    disable: list[str] | None = None,
) -> list:
    """Instantiate selected plugin classes, applying --only/--disable filters."""
    only_set = set(only) if only else None
    disable_set = set(disable) if disable else set()
    plugins = []
    for cls in classes:
        name = getattr(cls, "name", "")
        if only_set is not None and name not in only_set:
            continue
        if name in disable_set:
            continue
        plugins.append(cls(ctx))
    return plugins


def search_plugins(plugins: list) -> list:
    """Return plugins that expose a search capability."""
    return [p for p in plugins if isinstance(p, SearchCapability)]


def download_plugins(plugins: list) -> list:
    """Return download-capable plugins ordered by ascending priority."""
    dls = [p for p in plugins if isinstance(p, DownloadCapability)]
    return sorted(dls, key=lambda p: getattr(p, "priority", 50))
