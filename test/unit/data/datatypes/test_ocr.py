import pytest

from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.datatypes.sniff import guess_ext
from galaxy.datatypes.text import (
    Hocr,
    Html,
)
from galaxy.datatypes.xml import (
    AbbyyXml,
    Alto,
    GenericXml,
    PageXml,
)

XML_FORMATS = [
    (
        PageXml,
        "PcGts",
        "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15",
    ),
    (
        PageXml,
        "PcGts",
        "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15",
    ),
    (Alto, "alto", "http://www.loc.gov/standards/alto/ns-v4#"),
    (Alto, "alto", "http://www.loc.gov/standards/alto/ns-v3#"),
    (Alto, "alto", "http://www.loc.gov/standards/alto/ns-v2#"),
    (Alto, "alto", "http://schema.ccs-gmbh.com/ALTO"),
    (
        AbbyyXml,
        "document",
        "http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml",
    ),
    (
        AbbyyXml,
        "document",
        "http://www.abbyy.com/FineReader_xml/FineReader6-schema-v1.xml",
    ),
]


def sniff_content(tmp_path, datatype, content):
    path = tmp_path / "input"
    path.write_text(content, encoding="utf-8")
    return datatype().sniff(str(path))


@pytest.mark.parametrize("datatype,root,namespace", XML_FORMATS)
@pytest.mark.parametrize("prefixed", [False, True])
@pytest.mark.parametrize("prolog", ["", '\ufeff<?xml version="1.0"?>\n<!-- OCR export -->\n'])
def test_xml_ocr_sniff(tmp_path, datatype, root, namespace, prefixed, prolog):
    tag = f"ocr:{root}" if prefixed else root
    xmlns = "xmlns:ocr" if prefixed else "xmlns"
    # A prefix may end inside the document; only the root start tag is needed.
    content = f"{prolog}<{tag}\n {xmlns}='{namespace}'>\n<unfinished"
    assert sniff_content(tmp_path, datatype, content)
    for other in (PageXml, Alto, AbbyyXml):
        if other is not datatype:
            assert not sniff_content(tmp_path, other, content)


@pytest.mark.parametrize("datatype,root,namespace", XML_FORMATS)
@pytest.mark.parametrize(
    "template",
    [
        "<{root}/>",
        '<{root} xmlns="urn:unrelated"/>',
        '<wrong xmlns="{namespace}"/>',
        '<outer><{root} xmlns="{namespace}"/></outer>',
        '<!-- <{root} xmlns="{namespace}"/> -->',
        '<{root} xmlns="{namespace}.invalid"/>',
        '<{root} xmlns="{namespace}"',
        'plain text <{root} xmlns="{namespace}"/>',
    ],
)
def test_xml_ocr_rejects_false_positives(tmp_path, datatype, root, namespace, template):
    assert not sniff_content(tmp_path, datatype, template.format(root=root, namespace=namespace))


@pytest.mark.parametrize(
    "content,expected",
    [
        (
            '<html><body><div class="ocr_page" title="bbox 0 0 100 100"></div></body></html>',
            True,
        ),
        (
            '<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><div class="ocr_page"/>',
            True,
        ),
        ("<!DOCTYPE html><HTML><DIV CLASS='extra ocr_page selected'>", True),
        ('<div\n class = "extra\tocr_page\nselected">', True),
        ("<div class=ocr_page>", True),
        ("<html><p>ocr_page</p></html>", False),
        ('<html><!-- <div class="ocr_page"> --></html>', False),
        (
            "<html><script>var example = '<div class=\"ocr_page\">';</script></html>",
            False,
        ),
        ('<div class="ocr_page_extra">', False),
        ('<div id="ocr_page">', False),
        ('<meta name="ocr-capabilities" content="ocr_page ocrx_word">', False),
        ('<div class="ocr_page', False),
        ("", False),
    ],
)
def test_hocr_sniff(tmp_path, content, expected):
    assert sniff_content(tmp_path, Hocr, content) is expected


@pytest.fixture(scope="module")
def registry():
    return example_datatype_registry_for_sample()


@pytest.mark.parametrize("datatype,root,namespace", XML_FORMATS)
def test_xml_ocr_registry(tmp_path, registry, datatype, root, namespace):
    path = tmp_path / "unknown.dat"
    path.write_text(f'<?xml version="1.0"?><{root} xmlns="{namespace}"/>')
    assert isinstance(registry.get_datatype_by_extension(datatype.file_ext), datatype)
    assert isinstance(registry.get_datatype_by_extension(datatype.file_ext), GenericXml)
    assert registry.get_mimetype_by_extension(datatype.file_ext) == "application/xml"
    assert guess_ext(str(path), registry.sniff_order) == datatype.file_ext


@pytest.mark.parametrize("prolog", ["", '<?xml version="1.0"?>'])
def test_hocr_registry(tmp_path, registry, prolog):
    path = tmp_path / "unknown.dat"
    path.write_text(f'{prolog}<html><body><div class="ocr_page"></div></body></html>')
    assert isinstance(registry.get_datatype_by_extension("hocr"), Hocr)
    assert isinstance(registry.get_datatype_by_extension("hocr"), Html)
    assert registry.get_mimetype_by_extension("hocr") == "text/html"
    assert guess_ext(str(path), registry.sniff_order) == "hocr"


@pytest.mark.parametrize(
    "content,extension",
    [
        ('<?xml version="1.0"?><document/>', "xml"),
        ("<html><body>ordinary HTML</body></html>", "html"),
        ("", "txt"),
    ],
)
def test_generic_fallback(tmp_path, registry, content, extension):
    path = tmp_path / "unknown.dat"
    path.write_text(content)
    assert guess_ext(str(path), registry.sniff_order) == extension
