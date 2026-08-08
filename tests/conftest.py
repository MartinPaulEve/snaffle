"""Shared fixtures. Network is always mocked via httpx.MockTransport."""

from __future__ import annotations

import httpx
import pytest

from snaffle.models import Publication, WorkType
from snaffle.services import ServiceContext


def make_client(handler) -> httpx.Client:
    """httpx.Client backed by a mock transport handler(request) -> Response."""
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture
def ctx_factory():
    def _factory(handler=None, **kwargs):
        if handler is None:
            def handler(request):  # noqa: ARG001
                return httpx.Response(404)
        return ServiceContext(http=make_client(handler), **kwargs)

    return _factory


@pytest.fixture
def sample_pub():
    return Publication(
        title="On the Origin of Testing",
        authors=["Ada Lovelace"],
        year=2026,
        venue="Journal of Software",
        publisher="Test Press",
        doi="10.1234/abc.def",
        type=WorkType.ARTICLE,
    )
