"""Linter tests for the repository data-table bundle.

These run the repository-level linters over :class:`RepositoryDataTables` models
built from the real fixture repositories under ``repositories/`` (no mocks) and
assert on the emitted :class:`~galaxy.tool_util.lint.LintContext` messages.
"""

import os

from galaxy.tool_util.data.bundles.lint import (
    lint_repository_data_tables,
    LocRowShape,
    MissingLocFixture,
)
from galaxy.tool_util.data.bundles.repository import build_repository_data_tables
from galaxy.tool_util.lint import (
    LintContext,
    LintLevel,
)

REPOS = os.path.join(os.path.dirname(__file__), "repositories")
FETCH_REPO = os.path.join(REPOS, "fetch_genome_dbkeys_all_fasta")
BROKEN_REPO = os.path.join(REPOS, "broken_rows")
MISSING_LOC_REPO = os.path.join(REPOS, "missing_loc")
MISSING_TWO_REPO = os.path.join(REPOS, "missing_two")
MISSING_AND_BROKEN_REPO = os.path.join(REPOS, "missing_and_broken")
SAMPLE_FALLBACK_REPO = os.path.join(REPOS, "sample_fallback")

FETCH_TABLE_TEST_CONF = os.path.join(FETCH_REPO, "tool_data_table_conf.xml.test")


def _lint(model):
    lint_ctx = LintContext(level=LintLevel.SILENT)
    lint_repository_data_tables(model, lint_ctx)
    return lint_ctx


def test_clean_repository_has_no_errors():
    model = build_repository_data_tables(FETCH_REPO, tool_data_table_confs=[FETCH_TABLE_TEST_CONF])
    lint_ctx = _lint(model)
    assert lint_ctx.error_messages == []


def test_missing_loc_fixture_is_an_error():
    conf = os.path.join(MISSING_LOC_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(MISSING_LOC_REPO, tool_data_table_confs=[conf])
    lint_ctx = _lint(model)
    errors = lint_ctx.error_messages
    assert len(errors) == 1
    assert errors[0].linter == MissingLocFixture.name()
    # Assert on stable linter wording, not the fixture's ("absent") file name.
    assert "does not exist" in errors[0].message


def test_short_and_wrong_separator_rows_are_errors():
    conf = os.path.join(BROKEN_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(BROKEN_REPO, tool_data_table_confs=[conf])
    lint_ctx = _lint(model)
    errors = lint_ctx.error_messages
    assert len(errors) == 2
    assert all(e.linter == LocRowShape.name() for e in errors)
    assert all("invalid" in e.message for e in errors)


def test_sample_fallback_is_not_a_missing_fixture():
    # A production loc resolved via .sample fallback is found; the missing-fixture
    # error must not fire on it (a P1 warning about the missing production loc is
    # a separate, later check).
    conf = os.path.join(SAMPLE_FALLBACK_REPO, "tool_data_table_conf.xml.sample")
    model = build_repository_data_tables(SAMPLE_FALLBACK_REPO, tool_data_table_confs=[conf])
    # Guard against the test passing vacuously: the asset must actually resolve via .sample.
    assert any(asset.found and asset.is_sample for asset in model.loc_assets)
    lint_ctx = _lint(model)
    assert [e for e in lint_ctx.error_messages if e.linter == MissingLocFixture.name()] == []


def test_multiple_missing_fixtures_each_error():
    conf = os.path.join(MISSING_TWO_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(MISSING_TWO_REPO, tool_data_table_confs=[conf])
    lint_ctx = _lint(model)
    errors = lint_ctx.error_messages
    assert len(errors) == 2
    assert all(e.linter == MissingLocFixture.name() for e in errors)


def test_missing_and_broken_together_no_contradictory_valid():
    # A repo with one unfound loc AND one loc with short rows: the missing-fixture
    # error and the row-shape errors must both fire, and LocRowShape must NOT also
    # emit a green "all rows fine" check off the back of the unparsed missing file.
    conf = os.path.join(MISSING_AND_BROKEN_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(MISSING_AND_BROKEN_REPO, tool_data_table_confs=[conf])
    lint_ctx = _lint(model)
    missing = [e for e in lint_ctx.error_messages if e.linter == MissingLocFixture.name()]
    row = [e for e in lint_ctx.error_messages if e.linter == LocRowShape.name()]
    assert len(missing) == 1
    assert len(row) == 2
    assert lint_ctx.valid_messages == []


def test_linters_are_skippable_by_name():
    conf = os.path.join(MISSING_LOC_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(MISSING_LOC_REPO, tool_data_table_confs=[conf])
    lint_ctx = LintContext(level=LintLevel.SILENT, skip_types=[MissingLocFixture.name()])
    lint_repository_data_tables(model, lint_ctx)
    assert lint_ctx.error_messages == []
