"""Unit tests for workflow-test-file validation (gxwf validate-tests)."""

import os

import pytest

from galaxy.tool_util.workflow_state.validation_tests import (
    load_tests_file,
    validate_tests_file,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "tests")

POSITIVE = [
    "file_path.yml",
    "file_location.yml",
    "file_composite.yml",
    "collection_list.yml",
    "collection_paired.yml",
    "collection_nested.yml",
    "scalars.yml",
    "list_of_files.yml",
    "list_of_scalars.yml",
]

NEGATIVE = [
    "neg_legacy_type_file.yml",
    "neg_legacy_type_raw.yml",
    "neg_elements_without_class.yml",
    "neg_file_no_path_or_location.yml",
    "neg_unknown_field.yml",
    "neg_bad_collection_type.yml",
    "neg_top_level_not_list.yml",
    "neg_collection_type_conflict.yml",
    "neg_collection_type_sugar.yml",
]


def _load(name):
    return load_tests_file(os.path.join(FIXTURES_DIR, name))


@pytest.mark.parametrize("fixture", POSITIVE)
def test_positive_fixture_validates(fixture):
    parsed = _load(fixture)
    result = validate_tests_file(parsed)
    assert result.valid, f"{fixture} should validate, got: {[d.message for d in result.diagnostics]}"
    assert result.diagnostics == []


@pytest.mark.parametrize("fixture", NEGATIVE)
def test_negative_fixture_rejected(fixture):
    parsed = _load(fixture)
    result = validate_tests_file(parsed)
    assert not result.valid, f"{fixture} should not validate"
    assert result.diagnostics, f"{fixture} should produce diagnostics"
    for d in result.diagnostics:
        assert d.message
        assert isinstance(d.path, str)


def test_top_level_not_list_message():
    parsed = _load("neg_top_level_not_list.yml")
    result = validate_tests_file(parsed)
    assert not result.valid
    joined = " ".join(d.message.lower() for d in result.diagnostics)
    assert "list" in joined or "array" in joined


def test_unknown_field_reported():
    parsed = _load("neg_unknown_field.yml")
    result = validate_tests_file(parsed)
    assert not result.valid
    assert any("unknown_field" in d.path or "unknown_field" in d.message for d in result.diagnostics)


# -- CLI / orchestrator layer --


def test_run_validate_tests_single_ok(tmp_path, capsys):
    from galaxy.tool_util.workflow_state.validate_tests import (
        run_validate_tests,
        ValidateTestsOptions,
    )

    opts = ValidateTestsOptions(workflow_path=os.path.join(FIXTURES_DIR, "file_path.yml"))
    assert run_validate_tests(opts) == 0


def test_run_validate_tests_single_invalid(tmp_path, capsys):
    from galaxy.tool_util.workflow_state.validate_tests import (
        run_validate_tests,
        ValidateTestsOptions,
    )

    opts = ValidateTestsOptions(workflow_path=os.path.join(FIXTURES_DIR, "neg_unknown_field.yml"))
    assert run_validate_tests(opts) == 1


def test_run_validate_tests_tree_mixed(tmp_path, capsys):
    import shutil

    from galaxy.tool_util.workflow_state.validate_tests import (
        run_validate_tests_tree,
        validate_tests_tree,
        ValidateTestsTreeOptions,
    )

    d = tmp_path / "mixed"
    d.mkdir()
    shutil.copy(os.path.join(FIXTURES_DIR, "file_path.yml"), d / "ok-tests.yml")
    shutil.copy(os.path.join(FIXTURES_DIR, "neg_unknown_field.yml"), d / "bad-tests.yml")

    report = validate_tests_tree(str(d))
    assert report.summary["total"] == 2
    assert report.summary["valid"] == 1
    assert report.summary["invalid"] == 1

    opts = ValidateTestsTreeOptions(workflow_path=str(d))
    assert run_validate_tests_tree(opts) == 1


def test_discover_test_files(tmp_path):
    from galaxy.tool_util.workflow_state.validate_tests import discover_test_files

    (tmp_path / "a-tests.yml").write_text("- job: {}\n  outputs: {}\n")
    (tmp_path / "b-test.yaml").write_text("- job: {}\n  outputs: {}\n")
    (tmp_path / "c.gxwf-tests.yml").write_text("- job: {}\n  outputs: {}\n")
    (tmp_path / "not_a_tests_file.yml").write_text("foo: 1\n")
    (tmp_path / "workflow.ga").write_text("{}")

    found = [os.path.basename(p) for p in discover_test_files(str(tmp_path))]
    assert "a-tests.yml" in found
    assert "b-test.yaml" in found
    assert "c.gxwf-tests.yml" in found
    assert "not_a_tests_file.yml" not in found
    assert "workflow.ga" not in found
