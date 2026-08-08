from snaffle.matching import author_matches, normalize_name, parse_name


def test_normalize_strips_accents_and_case():
    assert normalize_name("Martín Rolánd") == "martin roland"


def test_parse_plain_order():
    parsed = parse_name("Martin Paul Eve")
    assert parsed.surname == "eve"
    assert parsed.given_initials == ["m", "p"]


def test_parse_comma_order():
    parsed = parse_name("Eve, Martin Paul")
    assert parsed.surname == "eve"
    assert parsed.given_initials == ["m", "p"]


def test_matches_exact_and_initialised_forms():
    target = "Martin Paul Eve"
    assert author_matches(target, ["Martin Paul Eve"])
    assert author_matches(target, ["M. P. Eve"])
    assert author_matches(target, ["Martin P. Eve"])
    assert author_matches(target, ["Eve, Martin"])


def test_rejects_when_no_author_shares_surname():
    # "Prentice Hall Literature" style: dozens of authors, none named Eve.
    target = "Martin Paul Eve"
    authors = [
        "Lawrence E. Berliner", "Eve Merriam", "Langston Hughes",
        "Ogden Nash", "Jane Yolen", "Mary MacLeod",
    ]
    assert author_matches(target, authors) is False


def test_rejects_scattered_name_parts():
    # Medical paper: "Martín Roland", "Eve A. Kerr", "Paul G Shekelle" —
    # the tokens Martin/Paul/Eve appear as SURNAMES of different people.
    target = "Martin Paul Eve"
    authors = [
        "Takahiro Higashi", "Neil S. Wenger", "Martín Roland",
        "Eve A. Kerr", "Paul G Shekelle",
    ]
    assert author_matches(target, authors) is False


def test_rejects_wrong_given_name_same_surname():
    # Same surname but incompatible first initial is a different person.
    assert author_matches("Martin Paul Eve", ["Sarah Eve"]) is False


def test_accepts_when_authors_unknown():
    # Sources searched *by* the author (homepages, repositories) may not list
    # authors; give those the benefit of the doubt rather than dropping them.
    assert author_matches("Martin Paul Eve", []) is True
