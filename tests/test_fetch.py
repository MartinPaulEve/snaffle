import httpx

from snaffle.fetch import fetch_document, looks_like_pdf


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_looks_like_pdf():
    assert looks_like_pdf(b"%PDF-1.7 ...") is True
    assert looks_like_pdf(b"<html>") is False
    assert looks_like_pdf(b"") is False


def test_fetch_returns_pdf_bytes_directly():
    http = _client(lambda r: httpx.Response(200, content=b"%PDF-1.4 hello"))
    assert fetch_document(http, "https://x/paper.pdf") == b"%PDF-1.4 hello"


def test_fetch_follows_presigned_url_body():
    # KCWorks/Invenio: the /content endpoint returns a presigned S3 URL as its
    # body; the real file lives one hop further on.
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "works.hcommons.org":
            return httpx.Response(200, content=b"https://s3.amazonaws.com/bucket/data?X-Amz-Sig=abc")
        if request.url.host == "s3.amazonaws.com":
            return httpx.Response(200, content=b"%PDF-1.4 real file")
        return httpx.Response(404)

    http = _client(handler)
    data = fetch_document(http, "https://works.hcommons.org/api/records/1/files/x.pdf/content")
    assert data == b"%PDF-1.4 real file"


def test_fetch_encodes_unsafe_characters_in_url():
    # OA URLs sometimes contain literal spaces (e.g. ".../FULL TEXT PDF.pdf").
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["raw"] = request.url.raw_path.decode()
        return httpx.Response(200, content=b"%PDF-1.4 book")

    data = fetch_document(_client(handler), "https://sup.org/files/FULL TEXT PDF.pdf")
    assert data == b"%PDF-1.4 book"
    assert "%20" in seen["raw"] and " " not in seen["raw"]


def test_fetch_does_not_double_encode():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["raw"] = str(request.url)
        return httpx.Response(200, content=b"%PDF-1.4")

    fetch_document(_client(handler), "https://x/a%20b.pdf")
    # An already-encoded %20 must not become %2520.
    assert "%2520" not in seen["raw"]


def test_fetch_none_on_error_status():
    assert fetch_document(_client(lambda r: httpx.Response(404)), "https://x/y") is None


def test_fetch_does_not_treat_html_as_url():
    html = b"<html><body>not a file</body></html>"
    http = _client(lambda r: httpx.Response(200, content=html))
    assert fetch_document(http, "https://x/page") == html
