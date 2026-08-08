import httpx

from snaffle.models import CopyQuality, Publication
from snaffle.plugins.public.oa import OpenAccessPlugin
from snaffle.services import ServiceContext


def _ctx(handler):
    return ServiceContext(http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_can_download_requires_pdf_url():
    ctx = _ctx(lambda r: httpx.Response(404))
    plugin = OpenAccessPlugin(ctx)
    assert plugin.can_download(Publication(title="x", pdf_url="https://r/p.pdf")) is True
    assert plugin.can_download(Publication(title="x")) is False


def test_downloads_any_pdf_url(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"%PDF-1.5 open access")

    pub = Publication(title="A Gold OA Book", pdf_url="https://repo.example/book.pdf")
    result = OpenAccessPlugin(_ctx(handler)).download(pub, tmp_path / "out.pdf")
    assert result.success is True
    assert result.path.read_bytes().startswith(b"%PDF")


def test_publisher_pdf_is_final_quality(tmp_path):
    handler = lambda r: httpx.Response(200, content=b"%PDF-1.5")  # noqa: E731
    pub = Publication(title="X", pdf_url="https://www.openbookpublishers.com/x.pdf")
    result = OpenAccessPlugin(_ctx(handler)).download(pub, tmp_path / "o.pdf")
    assert result.quality == CopyQuality.FINAL


def test_repository_pdf_is_preprint_quality(tmp_path):
    handler = lambda r: httpx.Response(200, content=b"%PDF-1.5")  # noqa: E731
    pub = Publication(title="X", pdf_url="https://eprints.bbk.ac.uk/1/x.pdf")
    result = OpenAccessPlugin(_ctx(handler)).download(pub, tmp_path / "o.pdf")
    assert result.quality == CopyQuality.PREPRINT


def test_non_pdf_response_is_a_failure(tmp_path):
    handler = lambda r: httpx.Response(200, content=b"<html>login wall</html>")  # noqa: E731
    pub = Publication(title="X", pdf_url="https://paywall.example/x")
    result = OpenAccessPlugin(_ctx(handler)).download(pub, tmp_path / "o.pdf")
    assert result.success is False
