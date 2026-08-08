from pathlib import Path

import httpx

from snaffle.registry import (
    discover_plugin_classes,
    download_plugins,
    instantiate_plugins,
    search_plugins,
)
from snaffle.services import ServiceContext

FAKE_DIR = Path(__file__).parent / "fixtures" / "fakeplugins"


def _mock_client():
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))


def ctx():
    return ServiceContext(http=_mock_client())


def test_discovery_finds_plugin_classes_only():
    classes = discover_plugin_classes([FAKE_DIR])
    names = {c.__name__ for c in classes}
    assert "AlphaPlugin" in names
    assert "BetaPlugin" in names
    assert "NotAPlugin" not in names


def test_instantiate_all_by_default():
    classes = discover_plugin_classes([FAKE_DIR])
    plugins = instantiate_plugins(classes, ctx())
    assert {p.name for p in plugins} == {"alpha", "beta"}


def test_instantiate_only_filter():
    classes = discover_plugin_classes([FAKE_DIR])
    plugins = instantiate_plugins(classes, ctx(), only=["alpha"])
    assert {p.name for p in plugins} == {"alpha"}


def test_instantiate_disable_filter():
    classes = discover_plugin_classes([FAKE_DIR])
    plugins = instantiate_plugins(classes, ctx(), disable=["alpha"])
    assert {p.name for p in plugins} == {"beta"}


def test_search_plugins_selects_search_capable():
    classes = discover_plugin_classes([FAKE_DIR])
    plugins = instantiate_plugins(classes, ctx())
    assert {p.name for p in search_plugins(plugins)} == {"alpha", "beta"}


def test_download_plugins_selects_and_orders_by_priority():
    classes = discover_plugin_classes([FAKE_DIR])
    plugins = instantiate_plugins(classes, ctx())
    dls = download_plugins(plugins)
    # Only alpha is download-capable.
    assert [p.name for p in dls] == ["alpha"]
