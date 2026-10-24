from typing import cast

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.managers.tool_data import ToolDataManager
from galaxy.structured_app import StructuredApp
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
