import pytest

from galaxy.app import MinimalGalaxyApplication
from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ConfigurationError
from galaxy.tool_util.data import DataTableColumnMismatch

TOOL_DATA_TABLE_CONF_XML = """<tables>
  <table name="testalpha" comment_char="#">
    <columns>value, name, path</columns>
    <file path="{tool_data_path}/testalpha.loc" />
  </table>
</tables>
"""

SHED_TOOL_DATA_TABLE_CONF_XML = """<tables>
  <table name="testalpha" comment_char="#">
    <columns>value, name, path, extra</columns>
    <file path="{tool_data_path}/testalpha_shed.loc" />
    <tool_shed_repository>
      <tool_shed>toolshed.g2.bx.psu.edu</tool_shed>
      <repository_name>data_manager_example</repository_name>
      <repository_owner>iuc</repository_owner>
      <installed_changeset_revision>abc123</installed_changeset_revision>
    </tool_shed_repository>
  </table>
</tables>
"""


class StubApp:
    def __init__(self, config):
        self.config = config

    def _tool_data_tables_registered(self, table_names):
        pass


@pytest.mark.parametrize("shed_first", [False, True])
def test_conflicting_shed_data_table_halts_startup_with_fix(tmp_path, shed_first):
    (tmp_path / "testalpha.loc").write_text("data1\tdata1name\t/data1\n")
    (tmp_path / "testalpha_shed.loc").write_text("data2\tdata2name\t/data2\textra2\n")
    tool_data_table_config = tmp_path / "tool_data_table_conf.xml"
    tool_data_table_config.write_text(TOOL_DATA_TABLE_CONF_XML.format(tool_data_path=tmp_path))
    shed_tool_data_table_config = tmp_path / "shed_tool_data_table_conf.xml"
    shed_tool_data_table_config.write_text(SHED_TOOL_DATA_TABLE_CONF_XML.format(tool_data_path=tmp_path))
    config_paths = [str(tool_data_table_config)]
    if shed_first:
        config_paths.insert(0, str(shed_tool_data_table_config))
    config = GalaxyAppConfiguration(
        override_tempdir=False,
        tool_data_path=str(tmp_path),
        tool_data_table_config_path=",".join(config_paths),
        shed_tool_data_table_config=str(shed_tool_data_table_config),
    )
    with pytest.raises(ConfigurationError) as exc_info:
        MinimalGalaxyApplication._configure_tool_data_tables(StubApp(config), from_shed_config=False)
    assert isinstance(exc_info.value.__cause__, DataTableColumnMismatch)
    message = str(exc_info.value)
    if not shed_first:
        assert "iuc/data_manager_example revision abc123" in message
    assert f"remove the <table name=\"testalpha\"> element from '{shed_tool_data_table_config}'" in message
