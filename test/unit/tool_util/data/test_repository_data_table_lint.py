"""Linter tests for the repository data-table bundle.

These run the repository-level linters over :class:`RepositoryDataTables` models
built from the real fixture repositories under ``repositories/`` (no mocks) and
assert on the emitted :class:`~galaxy.tool_util.lint.LintContext` messages.
"""

import os

from galaxy.tool_util.data.bundles.lint import (
    ConflictingTableSchema,
    ConsumerTableDefined,
    DuplicateColumnNames,
    EmptyLocFile,
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


def test_tool_data_sample_backed_loc_is_not_a_missing_fixture():
    # The real Tool Shed layout: conf references tool-data/bar.loc, the sample ships at
    # tool-data/bar.loc.sample. The loader's own .sample fallback does NOT resolve this
    # (found=False), so without sample_backed every reference-data repo would wrongly
    # report a missing loc. sample_backed must recognize the shipped sample.
    conf = os.path.join(TOOL_DATA_SAMPLE_REPO, "tool_data_table_conf.xml.sample")
    model = build_repository_data_tables(TOOL_DATA_SAMPLE_REPO, tool_data_table_confs=[conf])
    # Guard against a vacuous pass: the loader must genuinely miss it, and sample_backed catch it.
    assert any(not asset.found and asset.sample_backed for asset in model.loc_assets)
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
    # The point of this case: LocRowShape must not emit a green "rows are fine"
    # check off the back of the unparsed missing file.
    assert [v for v in lint_ctx.valid_messages if v.linter == LocRowShape.name()] == []


def test_full_bundle_names_all_resolve():
    # Manager tables + consumer reference are all locally configured -> no errors,
    # no warnings; both name-relationship linters confirm valid.
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
    # Manager declares all_fasta + __dbkeys__ but no tool_data_table config is present.
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
    # A from_data_table that stays non-literal after macro expansion must not be
    # flagged as missing (galaxyproject/tools-iuc#5003 false-positive guard).
    model = build_repository_data_tables(FETCH_REPO, consumer_tool_sources=_consumer_sources(FETCH_DYNAMIC_CONSUMER))
    # Precondition: the consumer's table name really is non-literal (guard is exercised).
    assert any("@" in c.table_name for c in model.consumers)
    lint_ctx = _lint(model)
    assert lint_ctx.error_messages == []
    assert lint_ctx.warn_messages == []
    # Nothing literal was checked, so no green confirmation either.
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
    assert "out_file" in errors[0].message  # names the real declared output for the fix


def test_output_ref_flags_only_the_bad_ref_in_a_mixed_manager():
    # One <data_table> has a valid output_ref, another a bad one; only the bad
    # one is flagged (exercises per-table iteration within a single manager).
    model = build_repository_data_tables(FETCH_REPO, data_manager_conf=FETCH_DM_CONF_MIXED_OUTPUT_REF)
    errors = [e for e in _lint(model).error_messages if e.linter == OutputRefValid.name()]
    assert len(errors) == 1
    assert "no_such_output" in errors[0].message
    assert "__dbkeys__" in errors[0].message


def test_output_ref_not_checked_when_wrapper_unresolved():
    # tool_file points at a wrapper that does not exist, so build resolves
    # wrapper_resolved=False and the outputs are unknown; a bad-looking output_ref
    # must not be reported as demonstrably missing.
    model = build_repository_data_tables(FETCH_REPO, data_manager_conf=FETCH_DM_CONF_MISSING_WRAPPER)
    # Precondition: the wrapper genuinely failed to resolve (guard is exercised).
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
    # Assembly must not raise even though the loader's merge would on this conflict.
    model = build_repository_data_tables(CONFLICT_COLUMNS_REPO, tool_data_table_confs=[conf])
    # Loader was skipped, but the name is still known from the raw declarations.
    assert "conflict_tbl" in model.configured_table_names
    errors = [e for e in _lint(model).error_messages if e.linter == ConflictingTableSchema.name()]
    assert len(errors) == 1
    assert "conflict_tbl" in errors[0].message


def test_conflicting_indexes_reported_without_crashing_assembly():
    # Same column names but different index attributes: the raw name tuples match,
    # so only the parsed columns-map catches the conflict -- and the loader would
    # crash on it, so assembly must skip the loader and still not raise.
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
    # Empty, comment-less loc files are flagged (Planemo #869), whether a shipped
    # .loc.sample or a plain test-data *.loc; a sibling empty-but-documented
    # (header-only) sample must NOT be flagged.
    conf = os.path.join(EMPTY_LOC_REPO, "tool_data_table_conf.xml.sample")
    model = build_repository_data_tables(EMPTY_LOC_REPO, tool_data_table_confs=[conf])
    # Guard against a vacuous pass: bare loc files are present, and a documented
    # (header-only) one is too.
    assert any(not f.has_data and not f.has_comment for f in model.loc_files)
    assert any(not f.has_data and f.has_comment for f in model.loc_files)
    warns = [w for w in _lint(model).warn_messages if w.linter == EmptyLocFile.name()]
    flagged = {os.path.basename(w.message.split("[", 1)[1].split("]", 1)[0]) for w in warns}
    assert flagged == {"undocumented.loc.sample", "empty.loc"}


def test_loc_file_classification(tmp_path):
    # The empty/documented distinction the linter keys on: whitespace-only and a
    # lone UTF-8 BOM both count as empty-and-undocumented; a comment (even behind a
    # BOM) documents the file; a data row is data.
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
    # The clean fixture ships data rows and header-only samples only; the empty-loc
    # linter must stay green and confirm valid (no false positive on documented files).
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
    # the per-table linters actually ran (not skipped)
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
    # nothing was assembled, so no per-table linter ran
    assert lint_ctx.valid_messages == []


def test_bundle_reports_assembly_failure(tmp_path):
    conf = tmp_path / "data_manager_conf.xml"
    conf.write_text("<data_managers><data_manager id='x'\n")  # unclosed tag -> parse error
    lint_ctx = _lint_bundle(str(tmp_path), data_manager_conf=str(conf))
    errors = lint_ctx.error_messages
    assert len(errors) == 1
    assert "Problem assembling repository data table model" in errors[0].message
