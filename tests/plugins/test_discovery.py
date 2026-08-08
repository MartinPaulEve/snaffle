import httpx

from snaffle.models import CopyQuality, Publication
from snaffle.plugins.public.discovery import (
    DiscoveryPlugin,
    build_queries,
    classify_source,
    select_candidates,
)
from snaffle.services import ServiceContext
from snaffle.services.kagi import KagiClient


def a_pub():
    return Publication(
        title="Literature Against Criticism",
        authors=["Martin Paul Eve"],
        year=2016,
        publisher="Open Book Publishers",
        doi="10.11647/obp.0102",
    )


def test_build_queries_include_title_and_author_surname():
    queries = build_queries(a_pub())
    assert any("Literature Against Criticism" in q for q in queries)
    assert any("Eve" in q for q in queries)
    # At least one query targets a PDF explicitly.
    assert any("pdf" in q.lower() for q in queries)


def test_classify_source_ranks_publisher_over_repository():
    pub = a_pub()
    assert classify_source("https://www.openbookpublishers.com/x.pdf", pub) == CopyQuality.FINAL
    assert classify_source("https://eprints.bbk.ac.uk/15945/1/Eve.pdf", pub) == CopyQuality.PREPRINT


def test_select_candidates_prefers_pdfs_and_drops_junk():
    obp = "https://www.openbookpublishers.com/10.11647/obp.0102.pdf"
    results = [
        {"url": "https://random.blog/review", "title": "A review", "snippet": ""},
        {"url": "https://eprints.bbk.ac.uk/15945/1/Eve.pdf", "title": "PDF", "snippet": ""},
        {"url": obp, "title": "OBP", "snippet": ""},
    ]
    ordered = select_candidates(results, a_pub())
    urls = [c["url"] for c in ordered]
    # Both PDFs are kept; the unrelated blog is dropped.
    assert "https://random.blog/review" not in urls
    assert set(urls) == {
        "https://eprints.bbk.ac.uk/15945/1/Eve.pdf",
        "https://www.openbookpublishers.com/10.11647/obp.0102.pdf",
    }
    # Publisher (FINAL) is tried before the repository preprint.
    assert urls[0].startswith("https://www.openbookpublishers.com")


def _ctx(kagi_handler, fetch_handler):
    kagi = KagiClient("k", http=httpx.Client(transport=httpx.MockTransport(kagi_handler)))
    return ServiceContext(
        http=httpx.Client(transport=httpx.MockTransport(fetch_handler)),
        kagi=kagi,
    )


def test_can_download_requires_kagi_and_title():
    with_kagi = _ctx(lambda r: httpx.Response(200, json={"data": []}),
                     lambda r: httpx.Response(404))
    assert DiscoveryPlugin(with_kagi).can_download(a_pub()) is True
    plain = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    no_kagi = ServiceContext(http=plain)
    assert DiscoveryPlugin(no_kagi).can_download(a_pub()) is False


def test_download_fetches_first_working_pdf(tmp_path):
    eprint = "https://eprints.bbk.ac.uk/15945/1/Eve.pdf"
    kagi_json = {"data": {"search": [{"url": eprint, "title": "PDF", "snippet": ""}]}}

    def kagi_handler(request):
        return httpx.Response(200, json=kagi_json)

    def fetch_handler(request):
        if str(request.url).endswith(".pdf"):
            return httpx.Response(200, content=b"%PDF-1.5 real fulltext",
                                  headers={"content-type": "application/pdf"})
        return httpx.Response(404)

    plugin = DiscoveryPlugin(_ctx(kagi_handler, fetch_handler))
    result = plugin.download(a_pub(), tmp_path / "out.pdf")
    assert result.success is True
    assert result.quality == CopyQuality.PREPRINT
    assert result.path.read_bytes().startswith(b"%PDF")


def test_download_reports_failure_when_nothing_downloadable(tmp_path):
    plugin = DiscoveryPlugin(
        _ctx(lambda r: httpx.Response(200, json={"data": []}),
             lambda r: httpx.Response(404))
    )
    result = plugin.download(a_pub(), tmp_path / "out.pdf")
    assert result.success is False
