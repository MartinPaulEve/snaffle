import httpx

from snaffle.services.kagi import KagiClient

SEARCH_RESPONSE = {
    "meta": {"id": "abc"},
    "data": [
        {
            "t": 0,
            "rank": 1,
            "url": "https://eprints.bbk.ac.uk/id/eprint/15945/1/Eve.pdf",
            "title": "Literature Against Criticism",
            "snippet": "Full text PDF",
        },
        {
            "t": 0,
            "rank": 2,
            "url": "https://www.openbookpublishers.com/books/10.11647/obp.0102",
            "title": "Literature Against Criticism - Open Book Publishers",
            "snippet": "Download",
        },
        {"t": 1, "list": ["related search one", "related search two"]},
    ],
}


def _client(handler):
    return KagiClient("secret-key", http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_search_sends_bot_authorization_and_query():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("Authorization")
        seen["q"] = request.url.params.get("q")
        return httpx.Response(200, json=SEARCH_RESPONSE)

    _client(handler).search("Literature Against Criticism Eve")
    assert seen["auth"] == "Bot secret-key"
    assert seen["q"] == "Literature Against Criticism Eve"


def test_search_returns_only_result_rows():
    results = _client(lambda r: httpx.Response(200, json=SEARCH_RESPONSE)).search("q")
    # The t==1 "related searches" row is not a result.
    assert len(results) == 2
    assert results[0]["url"].endswith("Eve.pdf")
    assert results[0]["title"] == "Literature Against Criticism"


def test_search_empty_on_error_status():
    results = _client(lambda r: httpx.Response(401, json={"error": "bad key"})).search("q")
    assert results == []
