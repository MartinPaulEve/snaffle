import httpx

from snaffle.models import CopyQuality, Publication
from snaffle.plugins.public.arxiv import ArxivPlugin, parse_arxiv_feed
from snaffle.services import ServiceContext


def _ctx(handler=lambda r: httpx.Response(404)):
    return ServiceContext(http=httpx.Client(transport=httpx.MockTransport(handler)))


ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Deep Testing Networks</title>
    <published>2026-01-15T00:00:00Z</published>
    <author><name>Ada Lovelace</name></author>
    <link title="pdf" href="http://arxiv.org/pdf/2601.00001v1" type="application/pdf"/>
    <id>http://arxiv.org/abs/2601.00001v1</id>
  </entry>
</feed>
"""


def test_parse_arxiv_feed_sets_pdf_url():
    pubs = parse_arxiv_feed(ATOM)
    assert len(pubs) == 1
    p = pubs[0]
    assert p.title == "Deep Testing Networks"
    assert p.year == 2026
    assert p.pdf_url == "http://arxiv.org/pdf/2601.00001v1"
    assert "arxiv" in p.sources


def test_arxiv_priority_is_late():
    assert ArxivPlugin(_ctx()).priority > 50


def test_arxiv_download_writes_preprint(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if "pdf" in str(request.url):
            return httpx.Response(200, content=b"%PDF-1.4 arxiv preprint")
        return httpx.Response(404)

    plugin = ArxivPlugin(_ctx(handler))
    pub = Publication(
        title="Deep Testing Networks", year=2026, pdf_url="http://arxiv.org/pdf/2601.00001v1"
    )
    dest = tmp_path / "out.pdf"
    result = plugin.download(pub, dest)
    assert result.success is True
    assert result.quality == CopyQuality.PREPRINT
    assert result.path.read_bytes().startswith(b"%PDF")


def test_arxiv_cannot_download_without_pdf_url():
    plugin = ArxivPlugin(_ctx())
    assert plugin.can_download(Publication(title="x")) is False
