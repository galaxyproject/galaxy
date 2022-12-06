import os

from galaxy.tool_util.data.bundles.models import convert_data_tables_xml
from galaxy.util import (
    galaxy_directory,
    parse_xml,
)
from galaxy.util.resources import resource_path


TOOLS_DIRECTORY = os.path.abspath(os.path.join(galaxy_directory(), "test/functional/tools/"))


def test_xml_parsing() -> None:
    path = os.path.join(TOOLS_DIRECTORY, "sample_data_manager_conf.xml")
    tree = parse_xml(path)
    data_managers_el = tree.getroot()
    data_manager_el = data_managers_el.find("data_manager")
    description = convert_data_tables_xml(data_manager_el)
    assert not description.undeclared_tables
    assert len(description.data_tables) == 1
    data_table = description.data_tables[0]
    output = data_table.output
    columns = output.columns
    assert len(columns) == 2
    column1 = columns[0]
    assert column1.name == "value"
    assert column1.output_ref is None
    column2 = columns[1]
    assert column2.name == "path"
    assert column2.output_ref == "out_file"
    moves = column2.moves
    assert len(moves) == 1
    move = moves[0]
    assert move.type == "directory"
    assert move.relativize_symlinks is True
    assert move.target_base == "${GALAXY_DATA_MANAGER_DATA_PATH}"
    assert move.target_value == "testbeta/${value}"
    assert move.source_base is None
    assert move.source_value == ""


def test_parsing_manual() -> None:
    path = resource_path(__package__, "example_data_managers/manual.xml")
    tree = parse_xml(path)
    data_managers_el = tree.getroot()
    data_manager_el = data_managers_el.find("data_manager")
    description = convert_data_tables_xml(data_manager_el)
    assert description.undeclared_tables
    assert len(description.data_tables) == 0


def test_parsing_mothur() -> None:
    path = resource_path(__package__, "example_data_managers/mothur.xml")
    tree = parse_xml(path)
    data_managers_el = tree.getroot()
    data_manager_el = data_managers_el.find("data_manager")
    description = convert_data_tables_xml(data_manager_el)
    assert not description.undeclared_tables
    assert len(description.data_tables) == 4
