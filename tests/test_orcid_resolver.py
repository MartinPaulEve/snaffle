import httpx

from snaffle.services.orcid_resolver import OrcidResolver, build_query


def test_build_query_is_field_scoped_and_covers_misrecording():
    q = build_query("Martin Paul Eve")
    # Strategy A: survives a middle name kept in the given-names field.
    assert "given-names:martin" in q
    assert "family-name:eve" in q
    # Strategy B: survives the middle name being misfiled into the family name.
    assert 'given-and-family-names:"martin paul eve"' in q
    assert " OR " in q


def test_resolve_uses_structured_query_not_freetext():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["q"] = request.url.params.get("q")
        row = {"orcid-id": "0000-0002-5589-8511", "given-names": "Martin", "family-names": "Eve"}
        return httpx.Response(200, json={"expanded-result": [row], "num-found": 1})

    resolver = OrcidResolver(http=httpx.Client(transport=httpx.MockTransport(handler)))
    resolver.resolve("Martin Paul Eve")
    assert "family-name:eve" in seen["q"]
    assert "given-names:martin" in seen["q"]


def _resolver(handler, override=None):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return OrcidResolver(http=http, override=override)


def _response(results, num=None):
    return {"expanded-result": results, "num-found": num if num is not None else len(results)}


def test_resolves_unique_name_match():
    result = _response(
        [{"orcid-id": "0000-0002-5589-8511", "given-names": "Martin Paul", "family-names": "Eve"}]
    )
    r = _resolver(lambda req: httpx.Response(200, json=result))
    assert r.resolve("Martin Paul Eve") == "0000-0002-5589-8511"


def test_matches_when_middle_name_lands_in_family_field():
    # ORCID sometimes misrecords "Martin Paul Eve" as given="Martin",
    # family="Paul Eve". Verification is by last-token surname, so it still
    # matches and resolves.
    result = _response(
        [{"orcid-id": "0000-0002-5589-8511", "given-names": "Martin", "family-names": "Paul Eve"}]
    )
    r = _resolver(lambda req: httpx.Response(200, json=result))
    assert r.resolve("Martin Paul Eve") == "0000-0002-5589-8511"


def test_matches_when_middle_name_in_given_field():
    result = _response(
        [{"orcid-id": "0000-0002-5589-8511", "given-names": "Martin Paul", "family-names": "Eve"}]
    )
    r = _resolver(lambda req: httpx.Response(200, json=result))
    assert r.resolve("Martin Paul Eve") == "0000-0002-5589-8511"


def test_picks_the_only_name_matching_candidate():
    result = _response(
        [
            {"orcid-id": "0000-0001-0000-0001", "given-names": "Sarah", "family-names": "Eve"},
            {"orcid-id": "0000-0002-5589-8511", "given-names": "Martin", "family-names": "Eve"},
        ]
    )
    r = _resolver(lambda req: httpx.Response(200, json=result))
    assert r.resolve("Martin Paul Eve") == "0000-0002-5589-8511"


def test_ambiguous_same_name_returns_none():
    # Two different ORCIDs whose names both match the target: do NOT guess.
    result = _response(
        [
            {"orcid-id": "0000-0000-0000-0001", "given-names": "Martin", "family-names": "Eve"},
            {"orcid-id": "0000-0000-0000-0002", "given-names": "Martin P", "family-names": "Eve"},
        ]
    )
    r = _resolver(lambda req: httpx.Response(200, json=result))
    assert r.resolve("Martin Paul Eve") is None


def test_no_match_returns_none():
    result = _response(
        [{"orcid-id": "0000-0000-0000-0009", "given-names": "Jane", "family-names": "Doe"}]
    )
    r = _resolver(lambda req: httpx.Response(200, json=result))
    assert r.resolve("Martin Paul Eve") is None


def test_override_short_circuits_without_http():
    def handler(req):
        raise AssertionError("must not call the network when overridden")

    r = _resolver(handler, override="0000-0002-5589-8511")
    assert r.resolve("Martin Paul Eve") == "0000-0002-5589-8511"


def test_result_is_cached():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        row = {"orcid-id": "0000-0002-5589-8511", "given-names": "Martin", "family-names": "Eve"}
        return httpx.Response(200, json=_response([row]))

    r = _resolver(handler)
    assert r.resolve("Martin Paul Eve") == "0000-0002-5589-8511"
    assert r.resolve("Martin Paul Eve") == "0000-0002-5589-8511"
    assert calls["n"] == 1


def test_network_error_returns_none():
    def handler(req):
        raise httpx.ConnectError("down")

    assert _resolver(handler).resolve("Martin Paul Eve") is None
