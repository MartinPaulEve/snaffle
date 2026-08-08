"""JSTOR and Project MUSE reject non-browser HTTP, so their search must skip
cleanly (no exception, no network) when no real browser session is available."""

import httpx

from snaffle.plugins.public.jstor import JstorPlugin
from snaffle.plugins.public.projectmuse import ProjectMusePlugin
from snaffle.services import ServiceContext


def _ctx_that_fails_if_called():
    def handler(request):
        raise AssertionError("must not make an HTTP search request without a browser")

    return ServiceContext(http=httpx.Client(transport=httpx.MockTransport(handler)), browser=None)


def test_jstor_search_skips_without_browser():
    assert JstorPlugin(_ctx_that_fails_if_called()).search("Martin Paul Eve") == []


def test_projectmuse_search_skips_without_browser():
    assert ProjectMusePlugin(_ctx_that_fails_if_called()).search("Martin Paul Eve") == []
