from typing import cast
from unittest.mock import Mock

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.managers.tool_data import ToolDataManager
from galaxy.structured_app import StructuredApp
from galaxy.tool_util.data import ToolDataTableConfigSource
from galaxy.tools.data import ToolDataTableManager
from galaxy.work.context import WorkRequestContext


def test_field_api_preserves_first_entry_after_merge_and_reload(tmp_path):
    configs = []
    for source in ("local", "idc"):
        directory = tmp_path / source
        directory.mkdir()
        reference = directory / "hg38.2bit"
        reference.write_text(source)
        loc = directory / "twobit.loc"
        loc.write_text(f"hg38\tHuman (hg38)\t{reference}\n")
        config = directory / "tables.xml"
        config.write_text(f"""<tables>
  <table name="twobit">
    <columns>value, name, path</columns>
    <file path="{loc}" />
  </table>
</tables>""")
        configs.append(str(config))

    app = MockApp()
    app.tool_data_tables = ToolDataTableManager(tmp_path, ",".join(configs))
    manager = ToolDataManager(cast(StructuredApp, app))
    trans = WorkRequestContext(app=app)
    local_reference = tmp_path / "local" / "hg38.2bit"
    for reload in (False, True):
        if reload:
            app.tool_data_tables.reload_tables()
        assert len(app.tool_data_tables["twobit"].data) == 2
        field = manager.show_field("twobit", "hg38")
        assert field.fields_value["path"] == str(local_reference)
        assert manager.get_field_file_path(trans, "twobit", "hg38", "hg38.2bit") == local_reference


def test_reload_api_adopts_changed_definition_like_peers(tmp_path):
    for name in ("a", "b"):
        (tmp_path / f"{name}.loc").write_text(f"hg38\tHuman (hg38)\t/{name}/hg38.fa\n")
    config = tmp_path / "tables.xml"
    definition = """<tables><table name="all_fasta"><columns>value, name, path</columns>
      <file path="{loc}" /></table></tables>"""
    config.write_text(definition.format(loc=tmp_path / "a.loc"))
    app = MockApp()
    app.tool_data_tables = ToolDataTableManager(str(tmp_path), config_sources=[ToolDataTableConfigSource(config)])
    structured_app = cast(StructuredApp, app)
    structured_app.queue_worker = Mock()
    manager = ToolDataManager(structured_app)
    config.write_text(definition.format(loc=tmp_path / "b.loc"))
    manager.reload("all_fasta")
    peer = ToolDataTableManager(str(tmp_path), config_sources=[ToolDataTableConfigSource(config)])
    assert app.tool_data_tables["all_fasta"].data == peer["all_fasta"].data == [["hg38", "Human (hg38)", "/b/hg38.fa"]]
