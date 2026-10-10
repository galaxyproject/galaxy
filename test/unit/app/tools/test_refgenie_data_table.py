from galaxy.tools.data import ToolDataTableManager

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
