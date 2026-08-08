from snaffle.models import CopyQuality, Publication
from snaffle.plugins.public.institutional import InstitutionalPlugin
from snaffle.services import ServiceContext


class FakeHarvester:
    def __init__(self, pdf=b"%PDF-1.5 paywalled"):
        self.pdf = pdf
        self.calls = []

    def fetch_pdf_by_doi(self, doi):
        self.calls.append(doi)
        return self.pdf


def test_can_download_requires_session_and_doi():
    plugin = InstitutionalPlugin(ServiceContext(http=None, institutional=FakeHarvester()))
    assert plugin.can_download(Publication(title="x", doi="10.1/x")) is True
    assert plugin.can_download(Publication(title="x")) is False
    no_session = InstitutionalPlugin(ServiceContext(http=None, institutional=None))
    assert no_session.can_download(Publication(title="x", doi="10.1/x")) is False


def test_download_writes_the_harvested_pdf(tmp_path):
    harvester = FakeHarvester()
    ctx = ServiceContext(http=None, institutional=harvester)
    pub = Publication(title="A Paywalled Article", doi="10.1080/x")
    result = InstitutionalPlugin(ctx).download(pub, tmp_path / "out.pdf")
    assert result.success is True
    assert result.quality == CopyQuality.FINAL
    assert result.path.read_bytes().startswith(b"%PDF")
    assert harvester.calls == ["10.1080/x"]


def test_download_fails_when_harvest_returns_nothing(tmp_path):
    ctx = ServiceContext(http=None, institutional=FakeHarvester(pdf=None))
    result = InstitutionalPlugin(ctx).download(
        Publication(title="x", doi="10.1/x"), tmp_path / "out.pdf"
    )
    assert result.success is False
