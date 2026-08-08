from snaffle.plugins.public.homepage import parse_publication_list

HTML = """
<html><body>
<h2>Publications</h2>
<ul class="publications">
  <li>Lovelace, A. (2026). On the Origin of Testing. <i>Journal of Software</i>.</li>
  <li>Lovelace, A. (2019). Notes on Analytical Engines. <i>Compute Quarterly</i>.</li>
</ul>
</body></html>
"""


def test_parse_publication_list_extracts_entries():
    pubs = parse_publication_list(HTML)
    titles = [p.title for p in pubs]
    assert any("On the Origin of Testing" in t for t in titles)
    assert any("Analytical Engines" in t for t in titles)


def test_parse_publication_list_captures_years():
    pubs = parse_publication_list(HTML)
    years = {p.year for p in pubs}
    assert 2026 in years
    assert 2019 in years


def test_parse_publication_list_tags_source():
    pubs = parse_publication_list(HTML)
    assert all("homepage" in p.sources for p in pubs)
