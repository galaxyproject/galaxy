from galaxy.managers.citations import (
    BibtexCitation,
    CitationCollection,
    parse_citation,
)
from galaxy.util import parse_xml_string

EXAMPLE_BIBTEX_CITATION = """<citation type="bibtex">@article{goecks2010galaxy,
    title={Galaxy: a comprehensive approach for supporting accessible, reproducible, and transparent computational research in the life sciences},
    author={Goecks, Jeremy and Nekrutenko, Anton and Taylor, James and The Galaxy Team},
    journal={Genome Biol},
    volume={11},
    number={8},
    pages={R86},
    year={2010}
}</citation>"""


def test_parse_citation():
    xml_text = EXAMPLE_BIBTEX_CITATION
    citation_elem = parse_xml_string(xml_text)
    citation = parse_citation(citation_elem, None)
    bibtex = citation.to_bibtex()
    assert "title={Galaxy" in bibtex


def test_citation_collection():
    citation_collection = CitationCollection()
    assert len(citation_collection) == 0
    cite1 = QuickBibtexCitation("@article{'test1'}")
    cite1dup = QuickBibtexCitation("@article{'test1'}")
    cite2 = QuickBibtexCitation("@article{'test2'}")
    assert citation_collection.add(cite1)
    assert not citation_collection.add(cite1dup)
    assert citation_collection.add(cite2)
    assert len(citation_collection) == 2


class QuickBibtexCitation(BibtexCitation):
    def __init__(self, raw_bibtex):
        self.raw_bibtex = raw_bibtex
