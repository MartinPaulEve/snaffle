"""Parser tests for national-library SRU/MARCXML catalogue plugins."""

from snaffle.models import WorkType
from snaffle.plugins.public.britishlibrary import parse_sru_marcxml

MARCXML = """<?xml version="1.0"?>
<searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/">
  <records>
    <record>
      <recordData>
        <record xmlns="http://www.loc.gov/MARC21/slim">
          <controlfield tag="008">050101s2005    enk</controlfield>
          <datafield tag="100" ind1="1" ind2=" ">
            <subfield code="a">Lovelace, Ada</subfield>
          </datafield>
          <datafield tag="245" ind1="1" ind2="0">
            <subfield code="a">A Catalogued Book :</subfield>
            <subfield code="b">an academic monograph</subfield>
          </datafield>
          <datafield tag="260" ind1=" " ind2=" ">
            <subfield code="b">Academic Press,</subfield>
            <subfield code="c">2005.</subfield>
          </datafield>
          <datafield tag="020" ind1=" " ind2=" ">
            <subfield code="a">9780134685991</subfield>
          </datafield>
        </record>
      </recordData>
    </record>
  </records>
</searchRetrieveResponse>
"""


def test_parse_sru_marcxml_extracts_book():
    pubs = parse_sru_marcxml(MARCXML)
    assert len(pubs) == 1
    p = pubs[0]
    assert "A Catalogued Book" in p.title
    assert p.year == 2005
    assert p.isbn == "9780134685991"
    assert p.publisher == "Academic Press"
    assert p.type == WorkType.BOOK


def test_parse_sru_marcxml_empty_result():
    empty = """<searchRetrieveResponse><records></records></searchRetrieveResponse>"""
    assert parse_sru_marcxml(empty) == []
