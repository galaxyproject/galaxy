"""Unit tests for shed-side data table install behavior."""

import os
from unittest import mock

import pytest

from galaxy.tool_shed.tools.data_table_manager import (
    DataTableColumnMismatch,
    ShedToolDataTableManager,
)
from galaxy.tool_util.data import (
    TabularToolDataTable,
    ToolDataTableManager,
)
from galaxy.util import (
    Element,
    SubElement,
)


class _FakeTableRegistry(ToolDataTableManager):
    def __init__(self):
        self.data_tables: dict = {}
        self.to_xml_calls: list = []

    def to_xml_file(self, shed_tool_data_table_config, new_elems=None, remove_elems=None):
        self.to_xml_calls.append((shed_tool_data_table_config, new_elems))
        with open(shed_tool_data_table_config, "wb") as fh:
            fh.write(b"<tables/>")


SAMPLE_TABLE_CONF = """\
<tables>
    <table name="all_fasta" comment_char="#">
        <columns>value, dbkey, name, path</columns>
        <file path="tool-data/all_fasta.loc" />
    </table>
</tables>
"""

LOC_SAMPLE_CONTENT = "# all_fasta.loc sample\n"


def _write(path: str, contents: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(contents)


def _make_stdtm(tmp_path):
    repo_dir = str(tmp_path / "repo")
    tool_data_path = str(tmp_path / "tool-data")
    shed_tool_data_path = str(tmp_path / "shed_tool_data")
    shed_tool_data_table_config = str(tmp_path / "shed_data_table_conf.xml")
    relative_target_dir = "owner/name/abc"

    os.makedirs(tool_data_path)
    os.makedirs(os.path.join(shed_tool_data_path, relative_target_dir))
    _write(os.path.join(repo_dir, "tool_data_table_conf.xml.sample"), SAMPLE_TABLE_CONF)
    _write(os.path.join(repo_dir, "tool-data", "all_fasta.loc.sample"), LOC_SAMPLE_CONTENT)

    app = mock.MagicMock(name="app")
    app.config.tool_data_path = tool_data_path
    app.config.shed_tool_data_path = shed_tool_data_path
    app.config.shed_tool_data_table_config = shed_tool_data_table_config
    registry = _FakeTableRegistry()
    app.tool_data_tables = registry
    captured = {"to_xml_calls": registry.to_xml_calls}

    stdtm = ShedToolDataTableManager(app)

    repo = mock.MagicMock(name="tool_shed_repository")
    repo.name = "data_manager_fetch_genome_dbkeys_all_fasta"
    repo.owner = "iuc"
    repo.installed_changeset_revision = "abc"
    repo.tool_shed = "tool-shed"
    repo.get_tool_relative_path.return_value = (repo_dir, relative_target_dir)

    sample_files = [
        "tool_data_table_conf.xml.sample",
        os.path.join("tool-data", "all_fasta.loc.sample"),
    ]
    return stdtm, repo, sample_files, captured, tool_data_path, shed_tool_data_path, relative_target_dir


def _registered_table(columns, filenames=None, type_key="tabular"):
    existing = mock.MagicMock(spec=TabularToolDataTable)
    existing.columns = columns
    existing.filenames = filenames or {}
    existing.type_key = type_key
    existing.parse_file_fields.return_value = []
    return existing


def _write_shed_config_with_entry(stdtm, table_name, file_path):
    """Pre-populate ``shed_tool_data_table_config`` with a single ``<table>`` matching ``elem``."""
    shed_config = stdtm.app.config.shed_tool_data_table_config
    contents = f"""<?xml version="1.0"?>
<tables>
    <table name="{table_name}" comment_char="#">
        <columns>value, dbkey, name, path</columns>
        <file path="{file_path}" />
    </table>
</tables>
"""
    with open(shed_config, "w") as fh:
        fh.write(contents)


def test_loc_file_lands_under_shed_subdir_not_per_revision(tmp_path):
    stdtm, repo, samples, captured, tool_data_path, shed_tool_data_path, _ = _make_stdtm(tmp_path)
    _, kept_elems = stdtm.install_tool_data_tables(repo, samples)

    shared_loc = os.path.join(tool_data_path, "shed", "all_fasta.loc")
    assert os.path.exists(shared_loc)
    # The loc file does NOT land at the tool_data_path root (which is for admin-configured loc
    # files) — Galaxy-managed shed loc files are isolated under tool_data_path/shed/.
    assert not os.path.exists(os.path.join(tool_data_path, "all_fasta.loc"))
    per_rev_loc = os.path.join(shed_tool_data_path, "owner/name/abc", "all_fasta.loc")
    assert not os.path.exists(per_rev_loc)

    assert len(kept_elems) == 1
    file_elems = list(kept_elems[0].findall("file"))
    assert len(file_elems) == 1
    assert file_elems[0].get("path") == shared_loc
    # New installs should not stamp a <tool_shed_repository> sub-element on the <table>:
    # the loc-file location is deterministic and DMs on legacy installs fall through to
    # the shared-no-repo_info match in get_filename_for_source.
    assert kept_elems[0].find("tool_shed_repository") is None


def test_existing_loc_file_is_not_overwritten(tmp_path):
    stdtm, repo, samples, _, tool_data_path, _, _ = _make_stdtm(tmp_path)
    shared_loc = os.path.join(tool_data_path, "shed", "all_fasta.loc")
    os.makedirs(os.path.dirname(shared_loc), exist_ok=True)
    _write(shared_loc, "preexisting DM-populated content\n")

    stdtm.install_tool_data_tables(repo, samples)

    with open(shared_loc) as fh:
        assert fh.read() == "preexisting DM-populated content\n"


def test_column_mismatch_raises(tmp_path):
    stdtm, repo, samples, captured, _, _, _ = _make_stdtm(tmp_path)
    stdtm.app.tool_data_tables.data_tables = {
        "all_fasta": _registered_table({"value": 0, "name": 1, "path": 2}),
    }

    with pytest.raises(DataTableColumnMismatch) as exc_info:
        stdtm.install_tool_data_tables(repo, samples)
    assert exc_info.value.table_name == "all_fasta"
    assert not captured["to_xml_calls"]


def test_column_match_first_install_writes_table_entry(tmp_path):
    """When a table is already registered in memory but has not yet been written to
    ``shed_tool_data_table_config``, we still write a (stamp-less) ``<table>`` entry so the
    shared loc file's association with the table survives reload."""
    stdtm, repo, samples, captured, tool_data_path, _, _ = _make_stdtm(tmp_path)
    matching_columns = {"value": 0, "dbkey": 1, "name": 2, "path": 3}
    stdtm.app.tool_data_tables.data_tables = {
        "all_fasta": _registered_table(matching_columns),
    }

    _, kept_elems = stdtm.install_tool_data_tables(repo, samples)

    assert len(kept_elems) == 1
    file_elems = list(kept_elems[0].findall("file"))
    assert len(file_elems) == 1
    assert file_elems[0].get("path") == os.path.join(tool_data_path, "shed", "all_fasta.loc")
    assert kept_elems[0].find("tool_shed_repository") is None


def test_column_match_subsequent_install_dedupes_shed_config_entry(tmp_path):
    """If shed_tool_data_table_config already has a ``<table>`` with the same name and same
    ``<file path>``, don't write another one."""
    stdtm, repo, samples, captured, tool_data_path, _, _ = _make_stdtm(tmp_path)
    matching_columns = {"value": 0, "dbkey": 1, "name": 2, "path": 3}
    stdtm.app.tool_data_tables.data_tables = {
        "all_fasta": _registered_table(matching_columns),
    }
    _write_shed_config_with_entry(stdtm, "all_fasta", os.path.join(tool_data_path, "shed", "all_fasta.loc"))

    _, kept_elems = stdtm.install_tool_data_tables(repo, samples)

    assert kept_elems == []
    assert not captured["to_xml_calls"]


def test_column_match_with_column_elements_writes_entry(tmp_path):
    stdtm, repo, _, captured, tool_data_path, _, _ = _make_stdtm(tmp_path)
    column_form_conf = """\
<tables>
    <table name="all_fasta" comment_char="#">
        <column name="value" index="0" />
        <column name="dbkey" index="1" />
        <column name="name" index="2" />
        <column name="path" index="3" />
        <file path="tool-data/all_fasta.loc" />
    </table>
</tables>
"""
    repo_dir, _ = repo.get_tool_relative_path.return_value
    _write(os.path.join(repo_dir, "tool_data_table_conf.xml.sample"), column_form_conf)
    stdtm.app.tool_data_tables.data_tables = {
        "all_fasta": _registered_table({"value": 0, "dbkey": 1, "name": 2, "path": 3}),
    }

    _, kept_elems = stdtm.install_tool_data_tables(
        repo,
        ["tool_data_table_conf.xml.sample", os.path.join("tool-data", "all_fasta.loc.sample")],
    )
    assert len(kept_elems) == 1
    assert kept_elems[0].find("tool_shed_repository") is None


def test_second_install_merges_loc_sample_rows_with_attribution(tmp_path):
    stdtm, repo, samples, captured, tool_data_path, _, _ = _make_stdtm(tmp_path)
    matching_columns = {"value": 0, "dbkey": 1, "name": 2, "path": 3}
    existing = _registered_table(matching_columns)
    incoming_rows = [["hg19", "hg19", "human (hg19)", "/data/hg19.fa"]]
    existing.parse_file_fields.return_value = incoming_rows
    stdtm.app.tool_data_tables.data_tables = {"all_fasta": existing}
    # Pre-populate shed config so kept_elems stays empty — we're testing the row-merge path.
    _write_shed_config_with_entry(stdtm, "all_fasta", os.path.join(tool_data_path, "shed", "all_fasta.loc"))

    _, kept_elems = stdtm.install_tool_data_tables(repo, samples)

    assert kept_elems == []
    assert not captured["to_xml_calls"]
    existing.append_entries_with_attribution.assert_called_once()
    call_args = existing.append_entries_with_attribution.call_args
    assert call_args.args[0] == incoming_rows
    attribution = call_args.args[1]
    assert "iuc/data_manager_fetch_genome_dbkeys_all_fasta" in attribution
    assert "abc" in attribution


def test_second_install_with_empty_loc_sample_does_not_append(tmp_path):
    stdtm, repo, samples, captured, tool_data_path, _, _ = _make_stdtm(tmp_path)
    matching_columns = {"value": 0, "dbkey": 1, "name": 2, "path": 3}
    existing = _registered_table(matching_columns)
    existing.parse_file_fields.return_value = []
    stdtm.app.tool_data_tables.data_tables = {"all_fasta": existing}
    _write_shed_config_with_entry(stdtm, "all_fasta", os.path.join(tool_data_path, "shed", "all_fasta.loc"))

    _, kept_elems = stdtm.install_tool_data_tables(repo, samples)

    assert kept_elems == []
    assert not captured["to_xml_calls"]
    existing.append_entries_with_attribution.assert_not_called()


def test_merge_skipped_for_non_tabular_table_types(tmp_path):
    """Refgenie-backed (and other non-tabular) tables don't get their .loc.sample parsed
    during install — refgenie's ``parse_file_fields`` expects YAML, not a .loc, so calling
    it on a ``.loc.sample`` is incorrect."""
    stdtm, repo, samples, _, tool_data_path, _, _ = _make_stdtm(tmp_path)
    matching_columns = {"value": 0, "dbkey": 1, "name": 2, "path": 3}
    existing = _registered_table(matching_columns, type_key="refgenie")
    stdtm.app.tool_data_tables.data_tables = {"all_fasta": existing}
    _write_shed_config_with_entry(stdtm, "all_fasta", os.path.join(tool_data_path, "shed", "all_fasta.loc"))

    _, kept_elems = stdtm.install_tool_data_tables(repo, samples)
    assert kept_elems == []
    existing.parse_file_fields.assert_not_called()
    existing.append_entries_with_attribution.assert_not_called()


def test_parse_table_columns_aliases_name_to_value():
    from galaxy.tool_shed.tools.data_table_manager import _parse_table_columns

    elem = Element("table")
    cols = SubElement(elem, "columns")
    cols.text = "value, path"
    parsed = _parse_table_columns(elem)
    assert parsed == {"value": 0, "path": 1, "name": 0}
