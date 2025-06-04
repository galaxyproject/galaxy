from pathlib import Path

import pytest

from galaxy.util import (
    LXML_AVAILABLE,
    parse_xml,
)

if not LXML_AVAILABLE:
    pytest.skip("LXML is not available", allow_module_level=True)


@pytest.fixture
def local_entity_file(tmp_path: Path):
    entity = tmp_path / "entity.txt"
    entity.write_text("Hello from entity!")
    return entity


@pytest.fixture
def external_entity_file(tmp_path: Path):
    # Put it outside tmp_path to trigger the block
    outside_file = tmp_path.parent / "external.txt"
    outside_file.write_text("Should be blocked")
    yield outside_file
    outside_file.unlink(missing_ok=True)


def test_parse_xml_allows_local_entity(tmp_path: Path, local_entity_file: Path):
    xml = f"""<?xml version="1.0"?>
    <!DOCTYPE root [
        <!ENTITY local SYSTEM "{local_entity_file.name}">
    ]>
    <root>&local;</root>
    """
    doc_path = tmp_path / "doc.xml"
    doc_path.write_text(xml)

    tree = parse_xml(doc_path)
    root_text = tree.getroot().text
    assert root_text
    assert root_text.strip() == "Hello from entity!"


def test_parse_xml_blocks_external_entity(tmp_path: Path, external_entity_file: Path):
    xml = f"""<?xml version="1.0"?>
    <!DOCTYPE root [
        <!ENTITY ext SYSTEM "{external_entity_file.resolve()}">
    ]>
    <root>&ext;</root>
    """
    doc_path = tmp_path / "doc.xml"
    doc_path.write_text(xml)

    with pytest.raises(OSError, match="Blocked external entity"):
        parse_xml(doc_path)
