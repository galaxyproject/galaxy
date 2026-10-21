from typing import cast

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.queue_worker import GalaxyQueueWorker
from galaxy.structured_app import StructuredApp
from galaxy.tools.data import ToolDataTableManager
from galaxy.tools.data_manager.manager import (
    DataManager,
    DataManagers,
)

TABLE_CONF_XML = """<tables>
  <table name="all_fasta" comment_char="#">
    <columns>value, name, path</columns>
    <file path="{loc_path}" />
  </table>
</tables>
"""


class RecordingQueueWorker(GalaxyQueueWorker):
    """Records control tasks instead of sending them to the other Galaxy processes."""

    def __init__(self):
        self.control_tasks = []

    def send_control_task(self, task, noop_self=False, get_response=False, routing_key="control.*", kwargs=None):
        self.control_tasks.append((task, noop_self, kwargs))


def _write_local_and_idc_tables(tmp_path) -> str:
    confs = []
    for name, contents in (("local", ""), ("idc", "hg38\tHuman (hg38)\t/idc/hg38.fa\n")):
        loc_path = tmp_path / f"{name}.loc"
        loc_path.write_text(contents)
        conf = tmp_path / f"{name}_tool_data_table_conf.xml"
        conf.write_text(TABLE_CONF_XML.format(loc_path=loc_path))
        confs.append(str(conf))
    return ",".join(confs)


def _data_manager(tool_data_tables: ToolDataTableManager) -> tuple[DataManager, RecordingQueueWorker]:
    mock_app = MockApp(data_manager_config_file=None, shed_data_manager_config_file=None)
    mock_app.tool_data_tables = tool_data_tables
    app = cast(StructuredApp, mock_app)
    queue_worker = RecordingQueueWorker()
    app.queue_worker = queue_worker
    return DataManager(DataManagers(app)), queue_worker


def test_reload_resolves_duplicate_values_like_other_processes(tmp_path):
    """A data manager adding a value that a later loaded table already provides must
    end up with the same entry order as processes reloading the table from files."""
    config_path = _write_local_and_idc_tables(tmp_path)
    tool_data_tables = ToolDataTableManager(tmp_path, config_path)
    table = tool_data_tables["all_fasta"]
    # what the data manager does when it adds an entry to the local loc file
    table.add_entry(
        ["hg38", "Human (hg38)", "/local/hg38.fa"], persist=True, tool_data_file_path=str(tmp_path / "local.loc")
    )
    assert table.data[0][2] == "/idc/hg38.fa"

    data_manager, queue_worker = _data_manager(tool_data_tables)
    data_manager._reload(["all_fasta"])

    peer_tool_data_tables = ToolDataTableManager(tmp_path, config_path)
    assert table.data == peer_tool_data_tables["all_fasta"].data
    assert table.data == [["hg38", "Human (hg38)", "/local/hg38.fa"]]
    assert queue_worker.control_tasks == [("reload_tool_data_tables", True, {"table_name": "all_fasta"})]


def test_reload_failure_still_notifies_other_processes(tmp_path):
    tool_data_tables = ToolDataTableManager(tmp_path, _write_local_and_idc_tables(tmp_path))
    # make reloading the table from files fail
    local_loc = tmp_path / "local.loc"
    local_loc.unlink()
    local_loc.mkdir()

    data_manager, queue_worker = _data_manager(tool_data_tables)
    data_manager._reload(["all_fasta"])

    assert queue_worker.control_tasks == [("reload_tool_data_tables", True, {"table_name": "all_fasta"})]
