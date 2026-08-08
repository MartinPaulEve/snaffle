from snaffle.exclude import is_excluded, parse_exclusions
from snaffle.models import Publication


def test_parse_exclusions_splits_and_normalizes():
    env = {"SNAFFLE_EXCLUDE": "Front Matter, eve.gd , unknown"}
    assert parse_exclusions(env) == ["front matter", "eve.gd", "unknown"]


def test_parse_exclusions_empty_when_unset():
    assert parse_exclusions({}) == []
    assert parse_exclusions({"SNAFFLE_EXCLUDE": "  "}) == []


def test_excludes_by_publisher():
    pub = Publication(title="A blog post", publisher="Front Matter")
    assert is_excluded(pub, ["front matter"]) is True


def test_excludes_by_url_domain():
    pub = Publication(title="A note", url="https://www.eve.gd/2020/some-post")
    assert is_excluded(pub, ["eve.gd"]) is True


def test_unknown_token_excludes_items_without_venue_or_publisher():
    assert is_excluded(Publication(title="X"), ["unknown"]) is True
    assert is_excluded(Publication(title="X", venue="A Journal"), ["unknown"]) is False
    assert is_excluded(Publication(title="X", publisher="A Press"), ["unknown"]) is False


def test_not_excluded_when_no_term_matches():
    pub = Publication(title="Real article", venue="Journal of Software", publisher="Elsevier")
    assert is_excluded(pub, ["front matter", "eve.gd", "unknown"]) is False


def test_no_terms_excludes_nothing():
    assert is_excluded(Publication(title="X"), []) is False
