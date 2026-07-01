from unittest import mock

import pytest

from galaxy.tool_util.data import (
    DataTableColumnMismatch,
    ToolDataPathFiles,
    ToolDataTableManager,
)

MULTI_TABLE_CONF_XML = """<tables>
  <table name="t1" comment_char="#">
    <columns>value, name, path</columns>
    <file path="{here}/t1.loc" />
  </table>
  <table name="t2" comment_char="#">
    <columns>value, name, path</columns>
    <file path="{here}/t2.loc" />
  </table>
  <table name="t3" comment_char="#">
    <columns>value, name, path</columns>
    <file path="{here}/t3.loc" />
  </table>
</tables>
"""

LOC_ALPHA_CONTENTS_V2 = """
data1	data1name	${__HERE__}/data1/entry.txt
data2	data2name	${__HERE__}/data2/entry.txt
data3	data3name	${__HERE__}/data3/entry.txt
"""

COLUMN_DIVERGENT_TABLE_CONF_XML = """<tables>
  <table name="testalpha" comment_char="#">
    <columns>value, name, path, extra</columns>
    <file path="{loc_path}" />
  </table>
</tables>
"""


def test_data_tables_as_dictionary(tdt_manager):
    assert "testalpha" in tdt_manager.data_tables
    assert "testdelta" not in tdt_manager.data_tables


def test_to_dict(tdt_manager):
    as_dict = tdt_manager.to_dict()
    assert "testalpha" in as_dict
    assert "testdelta" not in as_dict
    testalpha_as_dict = as_dict["testalpha"]
    assert "columns" in testalpha_as_dict


def test_index(tdt_manager):
    index = tdt_manager.index()
    assert len(index.root) >= 1
    entry = index.find_entry("testalpha")
    assert entry
    entry = index.find_entry("testomega")
    assert not entry


def test_reload(tdt_manager, tmp_path):
    assert len(tdt_manager["testalpha"].data) == 2
    loc1 = tmp_path / "testalpha.loc"
    loc1.write_text(LOC_ALPHA_CONTENTS_V2)
    tdt_manager.reload_tables()
    assert len(tdt_manager["testalpha"].data) == 3


def test_reload_by_path(tdt_manager, tmp_path):
    assert len(tdt_manager["testalpha"].data) == 2
    loc1 = tmp_path / "testalpha.loc"
    loc1.write_text(LOC_ALPHA_CONTENTS_V2)
    tdt_manager.reload_tables(path=str(loc1))
    assert len(tdt_manager["testalpha"].data) == 3


def test_reload_by_name(tdt_manager, tmp_path):
    assert len(tdt_manager["testalpha"].data) == 2
    loc1 = tmp_path / "testalpha.loc"
    loc1.write_text(LOC_ALPHA_CONTENTS_V2)
    tdt_manager.reload_tables("testalpha")
    assert len(tdt_manager["testalpha"].data) == 3


def test_merging_tables(merged_tdt_manager):
    assert len(merged_tdt_manager["testbeta"].data) == 2


def test_to_json(merged_tdt_manager, tmp_path):
    json_path = tmp_path / "as_json.json"
    assert not json_path.exists()
    merged_tdt_manager.to_json(json_path)
    assert json_path.exists()


def test_assert_data_table_consistency_accepts_new_table(tdt_manager):
    tdt_manager.assert_data_table_consistency(
        "brand_new_table",
        {"value": 0, "name": 1, "path": 2},
    )


def test_assert_data_table_consistency_accepts_matching_redefinition(tdt_manager):
    existing = tdt_manager["testalpha"]
    tdt_manager.assert_data_table_consistency("testalpha", existing.columns)


def test_assert_data_table_consistency_raises_column_mismatch(tdt_manager):
    with pytest.raises(DataTableColumnMismatch) as exc_info:
        tdt_manager.assert_data_table_consistency(
            "testalpha",
            {"value": 0, "name": 1, "path": 2, "extra": 3},
        )
    assert exc_info.value.table_name == "testalpha"


def test_get_filename_for_source_falls_back_to_shared_filename(tdt_manager):
    table = tdt_manager["testalpha"]
    [shared_filename] = list(table.filenames)
    assert table.filenames[shared_filename].get("tool_shed_repository") is None
    source_with_unknown_repo = {
        "tool_shed": "tool-shed",
        "repository_name": "repo",
        "repository_owner": "owner",
        "installed_changeset_revision": "abc",
    }
    assert table.get_filename_for_source(source_with_unknown_repo) == shared_filename


def test_get_filename_for_source_prefers_exact_repo_match_over_shared(tdt_manager):
    table = tdt_manager["testalpha"]
    [shared_filename] = list(table.filenames)
    legacy_info = {
        "tool_shed": "tool-shed",
        "repository_name": "legacy",
        "repository_owner": "owner",
        "installed_changeset_revision": "deadbeef",
    }
    legacy_filename = f"{shared_filename}.legacy"
    table.filenames[legacy_filename] = dict(
        found=True,
        filename=legacy_filename,
        from_shed_config=True,
        tool_data_path=None,
        config_element=None,
        tool_shed_repository=legacy_info,
        errors=[],
    )
    assert table.get_filename_for_source(legacy_info) == legacy_filename
    other_info = dict(legacy_info, repository_name="unknown")
    assert table.get_filename_for_source(other_info) == shared_filename


def test_append_entries_with_attribution_appends_and_dedupes(tdt_manager):
    table = tdt_manager["testalpha"]
    [loc_filename] = list(table.filenames)
    initial_rows = len(table.data)
    new_entries = [
        ["data3", "data3name", "${__HERE__}/data3/entry.txt"],
        ["data1", "data1name", "${__HERE__}/data1/entry.txt"],  # duplicate, must be skipped
    ]
    table.append_entries_with_attribution(new_entries, "added by owner/foo@rev1")
    with open(loc_filename) as fh:
        contents = fh.read()
    assert "# added by owner/foo@rev1" in contents
    assert contents.count("data3\tdata3name") == 1
    assert contents.count("data1\tdata1name") == 1
    assert len(table.data) == initial_rows + 1


def test_append_entries_with_attribution_noop_when_all_duplicates(tdt_manager):
    table = tdt_manager["testalpha"]
    [loc_filename] = list(table.filenames)
    with open(loc_filename) as fh:
        before = fh.read()
    rows_before = list(table.data)
    table.append_entries_with_attribution(
        [["data1", "data1name", "${__HERE__}/data1/entry.txt"]],
        "added by owner/foo@rev1",
    )
    with open(loc_filename) as fh:
        after = fh.read()
    assert after == before
    assert table.data == rows_before


def _write_multi_table_conf(tmp_path):
    for name in ("t1", "t2", "t3"):
        (tmp_path / f"{name}.loc").write_text(f"{name}\t{name}name\t/irrelevant\n")
    conf = tmp_path / "tool_data_table_conf.xml"
    conf.write_text(MULTI_TABLE_CONF_XML.format(here=str(tmp_path)))
    return conf


def test_directory_walked_once_per_load_pass(tmp_path):
    # Regression: the tool-data tree must be walked once per load pass, not once
    # per exists() check. update_files() is the sole os.walk site, so counting
    # its calls counts walks; exists() (many calls, one per table) must not add
    # walks. Guards ToolDataPathFiles.cached() against the old per-call re-walk.
    conf = _write_multi_table_conf(tmp_path)

    walks = 0
    exists_lookups = 0
    real_update = ToolDataPathFiles.update_files
    real_exists = ToolDataPathFiles.exists

    def counting_update(self):
        nonlocal walks
        walks += 1
        return real_update(self)

    def counting_exists(self, path):
        nonlocal exists_lookups
        exists_lookups += 1
        return real_exists(self, path)

    with (
        mock.patch.object(ToolDataPathFiles, "update_files", counting_update),
        mock.patch.object(ToolDataPathFiles, "exists", counting_exists),
    ):
        manager = ToolDataTableManager(tmp_path, conf)

    assert {"t1", "t2", "t3"}.issubset(manager.data_tables)
    # One exists() per table (at least), but the tree is walked exactly once.
    assert exists_lookups >= 3
    assert walks == 1, f"expected one walk per load pass, got {walks}"


def test_reload_walks_once_regardless_of_table_count(tmp_path):
    conf = _write_multi_table_conf(tmp_path)
    manager = ToolDataTableManager(tmp_path, conf)

    walks = 0
    real_update = ToolDataPathFiles.update_files

    def counting_update(self):
        nonlocal walks
        walks += 1
        return real_update(self)

    with mock.patch.object(ToolDataPathFiles, "update_files", counting_update):
        manager.reload_tables()
    assert walks == 1, f"expected one walk per reload pass, got {walks}"


def test_exists_outside_load_pass_does_not_walk(tmp_path):
    # Outside a load pass nothing is cached, so exists() falls back to
    # os.path.exists() and never walks -- the listing can't outlive disk state.
    conf = _write_multi_table_conf(tmp_path)
    manager = ToolDataTableManager(tmp_path, conf)
    tdpf = manager.tool_data_path_files

    walks = 0
    real_update = ToolDataPathFiles.update_files

    def counting_update(self):
        nonlocal walks
        walks += 1
        return real_update(self)

    with mock.patch.object(ToolDataPathFiles, "update_files", counting_update):
        assert tdpf.exists(str(tmp_path / "t1.loc")) is True
        assert tdpf.exists(str(tmp_path / "missing.loc")) is False
    assert walks == 0, f"exists() outside a load pass must not walk, got {walks}"
    assert tdpf._tool_data_path_files is None
