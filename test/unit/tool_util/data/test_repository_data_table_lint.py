"""Linter tests for repository data-table bundles."""

import os
import shutil

from galaxy.tool_util.data.bundles.lint import (
    _find_tool_data_table_confs,
    ConflictingTableSchema,
    ConsumerTableDefined,
    DuplicateColumnNames,
    EmptyLocFile,
    find_and_lint_repository_data_tables,
    lint_repository_data_tables,
    lint_repository_data_tables_bundle,
    LocRowShape,
    ManagerTableConfigured,
    MissingLocFixture,
    OutputRefValid,
)
from galaxy.tool_util.data.bundles.repository import (
    _classify_loc_file,
    build_repository_data_tables,
)
from galaxy.tool_util.lint import (
    LintContext,
    LintLevel,
)
from galaxy.tool_util.parser.factory import get_tool_source

REPOS = os.path.join(os.path.dirname(__file__), "repositories")
FETCH_REPO = os.path.join(REPOS, "fetch_genome_dbkeys_all_fasta")
BROKEN_REPO = os.path.join(REPOS, "broken_rows")
MISSING_LOC_REPO = os.path.join(REPOS, "missing_loc")
MISSING_TWO_REPO = os.path.join(REPOS, "missing_two")
MISSING_AND_BROKEN_REPO = os.path.join(REPOS, "missing_and_broken")
SAMPLE_FALLBACK_REPO = os.path.join(REPOS, "sample_fallback")
TOOL_DATA_SAMPLE_REPO = os.path.join(REPOS, "tool_data_sample")
DUP_COLUMNS_REPO = os.path.join(REPOS, "dup_columns")
CONFLICT_COLUMNS_REPO = os.path.join(REPOS, "conflicting_columns")
CONFLICT_SEPARATOR_REPO = os.path.join(REPOS, "conflicting_separator")
CONFLICT_INDEXES_REPO = os.path.join(REPOS, "conflicting_indexes")
EMPTY_LOC_REPO = os.path.join(REPOS, "empty_loc")
CORE_CONSUMER_REPO = os.path.join(REPOS, "core_table_consumer")

FETCH_TABLE_TEST_CONF = os.path.join(FETCH_REPO, "tool_data_table_conf.xml.test")
FETCH_DM_CONF = os.path.join(FETCH_REPO, "data_manager_conf.xml")
FETCH_DM_CONF_BAD_OUTPUT_REF = os.path.join(FETCH_REPO, "data_manager_conf_bad_output_ref.xml")
FETCH_DM_CONF_MIXED_OUTPUT_REF = os.path.join(FETCH_REPO, "data_manager_conf_mixed_output_ref.xml")
FETCH_DM_CONF_MISSING_WRAPPER = os.path.join(FETCH_REPO, "data_manager_conf_missing_wrapper.xml")
FETCH_CONSUMER = os.path.join(FETCH_REPO, "tools", "consume_all_fasta.xml")
FETCH_DYNAMIC_CONSUMER = os.path.join(FETCH_REPO, "tools", "consume_dynamic_table.xml")


def _consumer_sources(*paths):
    return [(path, get_tool_source(config_file=path)) for path in paths]


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
    conf = os.path.join(SAMPLE_FALLBACK_REPO, "tool_data_table_conf.xml.sample")
    model = build_repository_data_tables(SAMPLE_FALLBACK_REPO, tool_data_table_confs=[conf])
    # Ensure the loader exercised its sample fallback.
    assert any(asset.found and asset.is_sample for asset in model.loc_assets)
    lint_ctx = _lint(model)
    assert [e for e in lint_ctx.error_messages if e.linter == MissingLocFixture.name()] == []


def test_tool_data_sample_backed_loc_is_not_a_missing_fixture():
    conf = os.path.join(TOOL_DATA_SAMPLE_REPO, "tool_data_table_conf.xml.sample")
    model = build_repository_data_tables(TOOL_DATA_SAMPLE_REPO, tool_data_table_confs=[conf])
    # The repository fallback, not the loader, must find this layout.
    assert any(not asset.found and asset.repo_backed for asset in model.loc_assets)
    lint_ctx = _lint(model)
    assert [e for e in lint_ctx.error_messages if e.linter == MissingLocFixture.name()] == []


def test_missing_test_fixture_is_not_backed_by_production_sample(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(FETCH_REPO, repo)
    (repo / "test-data" / "all_fasta.loc").unlink()

    lint_ctx = LintContext(level=LintLevel.SILENT)
    find_and_lint_repository_data_tables(lint_ctx, str(repo))

    missing = [e for e in lint_ctx.error_messages if e.linter == MissingLocFixture.name()]
    assert len(missing) == 1
    assert "test-data/all_fasta.loc" in missing[0].message


def test_sample_backed_loc_rows_are_checked(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(TOOL_DATA_SAMPLE_REPO, repo)
    (repo / "tool-data" / "bar.loc.sample").write_text("# value\tname\tpath\nshort\trow\n")

    lint_ctx = LintContext(level=LintLevel.SILENT)
    find_and_lint_repository_data_tables(lint_ctx, str(repo))

    assert [e for e in lint_ctx.error_messages if e.linter == MissingLocFixture.name()] == []
    rows = [e for e in lint_ctx.error_messages if e.linter == LocRowShape.name()]
    assert len(rows) == 1
    assert "Line 2" in rows[0].message


def test_multiple_missing_fixtures_each_error():
    conf = os.path.join(MISSING_TWO_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(MISSING_TWO_REPO, tool_data_table_confs=[conf])
    lint_ctx = _lint(model)
    errors = lint_ctx.error_messages
    assert len(errors) == 2
    assert all(e.linter == MissingLocFixture.name() for e in errors)


def test_missing_and_broken_together_no_contradictory_valid():
    conf = os.path.join(MISSING_AND_BROKEN_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(MISSING_AND_BROKEN_REPO, tool_data_table_confs=[conf])
    lint_ctx = _lint(model)
    missing = [e for e in lint_ctx.error_messages if e.linter == MissingLocFixture.name()]
    row = [e for e in lint_ctx.error_messages if e.linter == LocRowShape.name()]
    assert len(missing) == 1
    assert len(row) == 2
    assert [v for v in lint_ctx.valid_messages if v.linter == LocRowShape.name()] == []


def test_full_bundle_names_all_resolve():
    model = build_repository_data_tables(
        FETCH_REPO,
        data_manager_conf=FETCH_DM_CONF,
        tool_data_table_confs=[FETCH_TABLE_TEST_CONF],
        consumer_tool_sources=_consumer_sources(FETCH_CONSUMER),
    )
    lint_ctx = _lint(model)
    assert lint_ctx.error_messages == []
    assert lint_ctx.warn_messages == []


def test_manager_table_not_configured_is_an_error():
    model = build_repository_data_tables(FETCH_REPO, data_manager_conf=FETCH_DM_CONF)
    lint_ctx = _lint(model)
    errors = [e for e in lint_ctx.error_messages if e.linter == ManagerTableConfigured.name()]
    assert len(errors) == 2
    flagged = {name for name in ("all_fasta", "__dbkeys__") for e in errors if name in e.message}
    assert flagged == {"all_fasta", "__dbkeys__"}


def test_manager_table_supplied_externally_is_ok():
    model = build_repository_data_tables(
        FETCH_REPO,
        data_manager_conf=FETCH_DM_CONF,
        external_table_names=frozenset({"all_fasta", "__dbkeys__"}),
    )
    lint_ctx = _lint(model)
    assert [e for e in lint_ctx.error_messages if e.linter == ManagerTableConfigured.name()] == []


def test_consumer_of_unknown_table_warns():
    model = build_repository_data_tables(FETCH_REPO, consumer_tool_sources=_consumer_sources(FETCH_CONSUMER))
    lint_ctx = _lint(model)
    warns = [w for w in lint_ctx.warn_messages if w.linter == ConsumerTableDefined.name()]
    assert len(warns) == 1
    assert "all_fasta" in warns[0].message


def test_consumer_of_externally_supplied_table_does_not_warn():
    model = build_repository_data_tables(
        FETCH_REPO,
        consumer_tool_sources=_consumer_sources(FETCH_CONSUMER),
        external_table_names=frozenset({"all_fasta"}),
    )
    lint_ctx = _lint(model)
    assert [w for w in lint_ctx.warn_messages if w.linter == ConsumerTableDefined.name()] == []


def test_non_literal_consumer_table_is_not_checked():
    model = build_repository_data_tables(FETCH_REPO, consumer_tool_sources=_consumer_sources(FETCH_DYNAMIC_CONSUMER))
    # tools-iuc#5003: unresolved macro names are not evidence of a missing table.
    assert any("@" in c.table_name for c in model.consumers)
    lint_ctx = _lint(model)
    assert lint_ctx.error_messages == []
    assert lint_ctx.warn_messages == []
    assert [v for v in lint_ctx.valid_messages if v.linter == ConsumerTableDefined.name()] == []


def test_output_ref_names_real_output_is_clean():
    model = build_repository_data_tables(FETCH_REPO, data_manager_conf=FETCH_DM_CONF)
    lint_ctx = _lint(model)
    assert [e for e in lint_ctx.error_messages if e.linter == OutputRefValid.name()] == []
    assert any(v.linter == OutputRefValid.name() for v in lint_ctx.valid_messages)


def test_output_ref_to_missing_output_is_an_error():
    model = build_repository_data_tables(FETCH_REPO, data_manager_conf=FETCH_DM_CONF_BAD_OUTPUT_REF)
    lint_ctx = _lint(model)
    errors = [e for e in lint_ctx.error_messages if e.linter == OutputRefValid.name()]
    assert len(errors) == 1
    assert "no_such_output" in errors[0].message
    assert "out_file" in errors[0].message


def test_output_ref_flags_only_the_bad_ref_in_a_mixed_manager():
    model = build_repository_data_tables(FETCH_REPO, data_manager_conf=FETCH_DM_CONF_MIXED_OUTPUT_REF)
    errors = [e for e in _lint(model).error_messages if e.linter == OutputRefValid.name()]
    assert len(errors) == 1
    assert "no_such_output" in errors[0].message
    assert "__dbkeys__" in errors[0].message


def test_output_ref_not_checked_when_wrapper_unresolved():
    model = build_repository_data_tables(FETCH_REPO, data_manager_conf=FETCH_DM_CONF_MISSING_WRAPPER)
    # Unknown outputs must not be treated as an empty output set.
    assert model.managers and all(not m.wrapper_resolved for m in model.managers)
    lint_ctx = _lint(model)
    assert [e for e in lint_ctx.error_messages if e.linter == OutputRefValid.name()] == []
    assert [v for v in lint_ctx.valid_messages if v.linter == OutputRefValid.name()] == []


def test_duplicate_column_names_is_an_error():
    conf = os.path.join(DUP_COLUMNS_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(DUP_COLUMNS_REPO, tool_data_table_confs=[conf])
    errors = [e for e in _lint(model).error_messages if e.linter == DuplicateColumnNames.name()]
    assert len(errors) == 1
    assert "value" in errors[0].message


def test_conflicting_columns_reported_without_crashing_assembly():
    conf = os.path.join(CONFLICT_COLUMNS_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(CONFLICT_COLUMNS_REPO, tool_data_table_confs=[conf])
    # Raw declarations remain usable when loader merging is skipped.
    assert "conflict_tbl" in model.configured_table_names
    errors = [e for e in _lint(model).error_messages if e.linter == ConflictingTableSchema.name()]
    assert len(errors) == 1
    assert "conflict_tbl" in errors[0].message


def test_conflicting_indexes_reported_without_crashing_assembly():
    # Only the parsed name-to-index map exposes this conflict.
    conf = os.path.join(CONFLICT_INDEXES_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(CONFLICT_INDEXES_REPO, tool_data_table_confs=[conf])
    assert "idx_tbl" in model.configured_table_names
    errors = [e for e in _lint(model).error_messages if e.linter == ConflictingTableSchema.name()]
    assert len(errors) == 1
    assert "idx_tbl" in errors[0].message


def test_conflicting_separator_is_reported():
    conf = os.path.join(CONFLICT_SEPARATOR_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(CONFLICT_SEPARATOR_REPO, tool_data_table_confs=[conf])
    errors = [e for e in _lint(model).error_messages if e.linter == ConflictingTableSchema.name()]
    assert len(errors) == 1
    assert "sep_tbl" in errors[0].message


def test_clean_repo_has_no_schema_or_duplicate_errors():
    model = build_repository_data_tables(FETCH_REPO, tool_data_table_confs=[FETCH_TABLE_TEST_CONF])
    lint_ctx = _lint(model)
    schema_linters = {DuplicateColumnNames.name(), ConflictingTableSchema.name()}
    assert [e for e in lint_ctx.error_messages if e.linter in schema_linters] == []
    linters_with_valid = {v.linter for v in lint_ctx.valid_messages}
    assert schema_linters <= linters_with_valid


def test_empty_undocumented_loc_files_warn():
    conf = os.path.join(EMPTY_LOC_REPO, "tool_data_table_conf.xml.sample")
    model = build_repository_data_tables(EMPTY_LOC_REPO, tool_data_table_confs=[conf])
    assert any(not f.has_data and not f.has_comment for f in model.loc_files)
    assert any(not f.has_data and f.has_comment for f in model.loc_files)
    warns = [w for w in _lint(model).warn_messages if w.linter == EmptyLocFile.name()]
    flagged = {os.path.basename(w.message.split("[", 1)[1].split("]", 1)[0]) for w in warns}
    assert flagged == {"undocumented.loc.sample", "empty.loc"}


def test_loc_file_classification(tmp_path):
    def classify(name, data, *, binary=False):
        p = tmp_path / name
        p.write_bytes(data) if binary else p.write_text(data)
        loc = _classify_loc_file(str(p))
        return loc.has_data, loc.has_comment

    assert classify("blank.loc", "  \n\n\t\n") == (False, False)
    assert classify("bom_only.loc", b"\xef\xbb\xbf", binary=True) == (False, False)
    assert classify("bom_comment.loc", b"\xef\xbb\xbf# value\tpath\n", binary=True) == (False, True)
    assert classify("comment.loc", "# value\tpath\n\n") == (False, True)
    assert classify("data.loc", "# value\tpath\nv1\t/data/x\n") == (True, True)


def test_documented_loc_files_do_not_warn():
    model = build_repository_data_tables(FETCH_REPO, tool_data_table_confs=[FETCH_TABLE_TEST_CONF])
    lint_ctx = _lint(model)
    assert [w for w in lint_ctx.warn_messages if w.linter == EmptyLocFile.name()] == []
    assert any(v.linter == EmptyLocFile.name() for v in lint_ctx.valid_messages)


def test_linters_are_skippable_by_name():
    conf = os.path.join(MISSING_LOC_REPO, "tool_data_table_conf.xml.test")
    model = build_repository_data_tables(MISSING_LOC_REPO, tool_data_table_confs=[conf])
    lint_ctx = LintContext(level=LintLevel.SILENT, skip_types=[MissingLocFixture.name()])
    lint_repository_data_tables(model, lint_ctx)
    assert lint_ctx.error_messages == []


def _lint_bundle(repo_root, **kwargs):
    lint_ctx = LintContext(level=LintLevel.SILENT)
    lint_repository_data_tables_bundle(lint_ctx, repo_root, **kwargs)
    return lint_ctx


def test_bundle_clean_repository_has_no_errors():
    lint_ctx = _lint_bundle(FETCH_REPO, data_manager_conf=FETCH_DM_CONF, tool_data_table_confs=[FETCH_TABLE_TEST_CONF])
    assert lint_ctx.error_messages == []
    assert lint_ctx.valid_messages


def test_bundle_surfaces_linter_errors():
    conf = os.path.join(MISSING_LOC_REPO, "tool_data_table_conf.xml.test")
    lint_ctx = _lint_bundle(MISSING_LOC_REPO, tool_data_table_confs=[conf])
    errors = lint_ctx.error_messages
    assert len(errors) == 1
    assert errors[0].linter == MissingLocFixture.name()


def test_bundle_skips_when_no_configuration():
    lint_ctx = _lint_bundle(FETCH_REPO)
    assert lint_ctx.error_messages == []
    assert any("skipping data table linting" in m.message for m in lint_ctx.info_messages)
    assert lint_ctx.valid_messages == []


def test_bundle_reports_assembly_failure(tmp_path):
    conf = tmp_path / "data_manager_conf.xml"
    conf.write_text("<data_managers><data_manager id='x'\n")  # unclosed tag -> parse error
    lint_ctx = _lint_bundle(str(tmp_path), data_manager_conf=str(conf))
    errors = lint_ctx.error_messages
    assert len(errors) == 1
    assert "Problem assembling repository data table model" in errors[0].message


CORE_CONSUMER_SAMPLE_CONF = os.path.join(CORE_CONSUMER_REPO, "tool_data_table_conf.xml.sample")
CORE_CONSUMER_WRAPPER = os.path.join(CORE_CONSUMER_REPO, "data_manager", "bwa_mem2_index_builder.xml")


def test_find_and_lint_excludes_core_tables():
    lint_ctx = LintContext(level=LintLevel.SILENT)
    find_and_lint_repository_data_tables(lint_ctx, CORE_CONSUMER_REPO)
    assert [w for w in lint_ctx.warn_messages if w.linter == ConsumerTableDefined.name()] == []
    assert any(v.linter == ConsumerTableDefined.name() for v in lint_ctx.valid_messages)


def test_core_table_exclusion_is_what_suppresses_the_warning():
    # Without default external tables, the same reference warns.
    model = build_repository_data_tables(
        CORE_CONSUMER_REPO,
        tool_data_table_confs=[CORE_CONSUMER_SAMPLE_CONF],
        consumer_tool_sources=_consumer_sources(CORE_CONSUMER_WRAPPER),
    )
    assert "all_fasta" not in model.configured_table_names
    assert any(c.table_name == "all_fasta" for c in model.consumers)
    warns = [w for w in _lint(model).warn_messages if w.linter == ConsumerTableDefined.name()]
    assert len(warns) == 1
    assert "all_fasta" in warns[0].message


def test_every_shipped_conf_variant_is_discovered():
    assert _find_tool_data_table_confs(FETCH_REPO) == [
        FETCH_TABLE_TEST_CONF,
        os.path.join(FETCH_REPO, "tool_data_table_conf.xml.sample"),
    ]


def test_shipped_sample_bundle_is_linted_alongside_the_test_conf(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(FETCH_REPO, repo)
    (repo / "tool-data" / "all_fasta.loc.sample").unlink()

    lint_ctx = LintContext(level=LintLevel.SILENT)
    find_and_lint_repository_data_tables(lint_ctx, str(repo))

    missing = [e for e in lint_ctx.error_messages if e.linter == MissingLocFixture.name()]
    assert len(missing) == 1
    assert "tool-data/all_fasta.loc" in missing[0].message


def test_checked_in_loc_under_tool_data_is_not_a_missing_fixture(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(TOOL_DATA_SAMPLE_REPO, repo)
    (repo / "tool-data" / "bar.loc.sample").rename(repo / "tool-data" / "bar.loc")

    conf = str(repo / "tool_data_table_conf.xml.sample")
    model = build_repository_data_tables(str(repo), tool_data_table_confs=[conf])
    assert any(not asset.found and asset.repo_backed for asset in model.loc_assets)
    assert [e for e in _lint(model).error_messages if e.linter == MissingLocFixture.name()] == []


def test_checked_in_loc_rows_are_checked(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(TOOL_DATA_SAMPLE_REPO, repo)
    (repo / "tool-data" / "bar.loc.sample").unlink()
    (repo / "tool-data" / "bar.loc").write_text("# value\tname\tpath\nshort\trow\n")

    conf = str(repo / "tool_data_table_conf.xml.sample")
    model = build_repository_data_tables(str(repo), tool_data_table_confs=[conf])
    rows = [e for e in _lint(model).error_messages if e.linter == LocRowShape.name()]
    assert len(rows) == 1
    assert "Line 2" in rows[0].message
