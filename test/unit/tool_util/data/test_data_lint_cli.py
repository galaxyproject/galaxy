"""Tests for the ``galaxy-tool-data-lint`` CLI.

These drive the command-line entry point over the real fixture repositories under
``repositories/`` and assert on its exit code and output -- the standalone counterpart
to the in-process linter tests in ``test_repository_data_table_lint.py``.
"""

import json
import os

import pytest

from galaxy.tool_util.data.bundles.script import (
    lint,
    main,
)

REPOS = os.path.join(os.path.dirname(__file__), "repositories")
CLEAN_REPO = os.path.join(REPOS, "fetch_genome_dbkeys_all_fasta")
MISSING_LOC_REPO = os.path.join(REPOS, "missing_loc")


def _lint(repository, skip="", report_level="all", fail_level="error", json=False):
    return lint(repository, skip=skip, report_level=report_level, fail_level=fail_level, json=json)


def test_clean_repository_exits_zero(capsys):
    code = _lint(CLEAN_REPO)
    assert code == 0
    out = capsys.readouterr().out
    # Discovery found the bundle and every linter ran (all green checks printed).
    assert "MissingLocFixture" in out
    assert "ERROR" not in out


def test_missing_loc_repository_exits_one(capsys):
    code = _lint(MISSING_LOC_REPO)
    assert code == 1
    out = capsys.readouterr().out
    assert "ERROR (MissingLocFixture)" in out
    assert "does not exist" in out


def test_skip_suppresses_linter_and_exit_code(capsys):
    # Skipping the only failing linter drops both its message and the failure.
    code = _lint(MISSING_LOC_REPO, skip="MissingLocFixture")
    assert code == 0
    assert "MissingLocFixture" not in capsys.readouterr().out


def test_no_configuration_is_skipped(tmp_path, capsys):
    code = _lint(str(tmp_path))
    assert code == 0
    assert "skipping data table linting" in capsys.readouterr().out


def test_json_output_lists_messages(capsys):
    code = _lint(MISSING_LOC_REPO, json=True)
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    errors = [m for m in payload["messages"] if m["level"] == "error"]
    assert len(errors) == 1
    assert errors[0]["linter"] == "MissingLocFixture"


def test_main_exits_via_system_exit():
    with pytest.raises(SystemExit) as exc_info:
        main([MISSING_LOC_REPO])
    assert exc_info.value.code == 1
