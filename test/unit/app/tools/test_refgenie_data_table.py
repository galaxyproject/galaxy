import pytest

from galaxy import util
from galaxy.tool_util.data import ToolDataTableConfigSource
from galaxy.tools.data import (
    RefgenieToolDataTable,
    TabularToolDataTable,
    ToolDataTableManager,
)

REFGENIE_CONFIG = """config_version: 0.4
genome_folder: /tmp/refgenie
genome_servers:
 - http://refgenomes.databio.org
genomes: null
"""

TOOL_DATA_TABLE_CONF_XML = """<tables>
  <table name="__dbkeys__" type="refgenie" asset="fasta">
    <file from_config="refgenie_config_file" />
    <field name="value" template="true">${{__REFGENIE_GENOME__}}</field>
    <field name="name" template="true">${{__REFGENIE_DISPLAY_NAME__}}</field>
    <field name="len_path" template="true">${{__REFGENIE_SEEK_KEY__('chrom_sizes')}}</field>
  </table>
  <table name="__dbkeys__" comment_char="#">
    <columns>value, name, len_path</columns>
    <file path="{loc_path}" />
  </table>
</tables>
"""


def test_entries_are_not_persisted_to_refgenie_config(tmp_path):
    refgenie_config = tmp_path / "refgenie.yml"
    refgenie_config.write_text(REFGENIE_CONFIG)
    loc_path = tmp_path / "dbkeys.loc"
    loc_path.write_text("")
    conf = tmp_path / "tool_data_table_conf.xml"
    conf.write_text(TOOL_DATA_TABLE_CONF_XML.format(loc_path=loc_path))
    tool_data_tables = ToolDataTableManager(
        tmp_path, str(conf), other_config_dict={"refgenie_config_file": str(refgenie_config)}
    )
    table = tool_data_tables["__dbkeys__"]

    table.add_entry(["dm7", "dm7", "dm7.len"], persist=True)

    assert refgenie_config.read_text() == REFGENIE_CONFIG
    assert loc_path.read_text() == "dm7\tdm7\tdm7.len\n"
    table.reload_from_files()
    assert table.data == [["dm7", "dm7", "dm7.len"]]

    table.remove_entry(["dm7", "dm7", "dm7.len"])
    assert refgenie_config.read_text() == REFGENIE_CONFIG
    assert table.data == []


@pytest.mark.parametrize("managed_first", [False, True])
def test_register_tabular_source_for_refgenie_table(tmp_path, managed_first):
    refgenie_config = tmp_path / "refgenie.yml"
    refgenie_config.write_text(REFGENIE_CONFIG)
    loc_path = tmp_path / "dbkeys.loc"
    loc_path.write_text("")
    refgenie_table, tabular_table = util.parse_xml_string(TOOL_DATA_TABLE_CONF_XML.format(loc_path=loc_path)).findall(
        "table"
    )
    refgenie_source = tmp_path / "refgenie.xml"
    refgenie_source.write_text(f"<tables>{util.xml_to_string(refgenie_table)}</tables>")
    incoming = tmp_path / "incoming.xml"
    incoming.write_text(f"<tables>{util.xml_to_string(tabular_table)}</tables>")
    managed = tmp_path / "managed.xml"
    managed.write_text("<tables />")
    sources = [ToolDataTableConfigSource(refgenie_source), ToolDataTableConfigSource(managed, from_shed_config=True)]
    if managed_first:
        sources.reverse()

    def make_manager():
        return ToolDataTableManager(
            str(tmp_path), config_sources=sources, other_config_dict={"refgenie_config_file": str(refgenie_config)}
        )

    manager = make_manager()
    peer = make_manager()
    table = manager["__dbkeys__"]
    peer_table = peer["__dbkeys__"]
    version = table._loaded_content_version
    elements, error = manager.add_new_entries_from_config_file(incoming, None, managed, persist=True)
    assert not error
    assert elements
    assert manager["__dbkeys__"] is table
    assert not table.is_current_version(version)
    expected_type = TabularToolDataTable if managed_first else RefgenieToolDataTable
    assert type(table) is expected_type

    table.add_entry(["dm7", "dm7", "dm7.len"], persist=True)
    assert loc_path.read_text() == "dm7\tdm7\tdm7.len\n"
    assert refgenie_config.read_text() == REFGENIE_CONFIG
    peer.reload_tables(["__dbkeys__"])
    assert peer["__dbkeys__"] is peer_table
    assert type(peer_table) is expected_type
    table.reload_from_files()
    restarted = make_manager()["__dbkeys__"]
    assert type(restarted) is expected_type
    assert table.data == peer_table.data == restarted.data == [["dm7", "dm7", "dm7.len"]]

    managed.write_text("<tables />")
    manager.reload_tables(["__dbkeys__"])
    assert manager["__dbkeys__"] is table
    assert type(table) is RefgenieToolDataTable
    table.reload_from_files()
    assert table.data == []
    assert refgenie_config.read_text() == REFGENIE_CONFIG
