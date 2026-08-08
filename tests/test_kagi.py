import httpx

from snaffle.services.kagi import KagiClient

# Kagi v1 /search response: results live under data.search.
SEARCH_RESPONSE = {
    "meta": {"id": "abc"},
    "data": {
        "search": [
            {
                "url": "https://eprints.bbk.ac.uk/id/eprint/15945/1/Eve.pdf",
                "title": "Literature Against Criticism",
                "snippet": "Full text PDF",
            },
            {
                "url": "https://www.openbookpublishers.com/books/10.11647/obp.0102",
                "title": "Literature Against Criticism - Open Book Publishers",
                "snippet": "Download",
            },
        ]
    },
}


def _client(handler):
    return KagiClient("secret-key", http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_search_posts_with_bearer_auth_and_json_query():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = request.content.decode()
        return httpx.Response(200, json=SEARCH_RESPONSE)

    _client(handler).search("Literature Against Criticism Eve")
    assert seen["method"] == "POST"
    assert seen["url"] == "https://kagi.com/api/v1/search"
    assert seen["auth"] == "Bearer secret-key"
    assert "Literature Against Criticism Eve" in seen["body"]


def test_search_returns_result_rows():
    results = _client(lambda r: httpx.Response(200, json=SEARCH_RESPONSE)).search("q")
    assert len(results) == 2
    assert results[0]["url"].endswith("Eve.pdf")
    assert results[0]["title"] == "Literature Against Criticism"


def test_search_empty_on_error_status():
    results = _client(lambda r: httpx.Response(401, json={"error": "bad key"})).search("q")
    assert results == []
