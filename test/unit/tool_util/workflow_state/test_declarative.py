"""Declarative YAML-driven tests for Galaxy workflow_state operations.

Uses gxformat2.testing harness with Galaxy-specific operations.
Expectation files live in test/unit/tool_util/workflow_state/expectations/.
"""

import copy
import os

import pytest
from gxformat2.normalized import ensure_native
from gxformat2.testing import DeclarativeTestSuite

from galaxy.tool_util.workflow_state._encoding import (
    check_strict_encoding,
    check_strict_structure,
)
from galaxy.tool_util.workflow_state._report_models import SKIP_STATUSES
from galaxy.tool_util.workflow_state.cache import build_tool_info
from galaxy.tool_util.workflow_state.clean import (
    _is_format2,
    clean_format2_state,
    clean_stale_state,
)
from galaxy.tool_util.workflow_state.export_format2 import export_workflow_to_format2
from galaxy.tool_util.workflow_state.stale_keys import StaleKeyPolicy
from galaxy.tool_util.workflow_state.validate import validate_workflow_cli
from galaxy.tool_util.workflow_state.workflow_tools import load_workflow
from .functional_tool_info import FunctionalGetToolInfo

EXPECTATIONS_DIR = os.path.join(os.path.dirname(__file__), "expectations")
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
FRAMEWORK_WORKFLOWS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "lib", "galaxy_test", "base", "data"
)


class _CombinedToolInfo:
    """Try cache-based tool info first, fall back to functional test tools."""

    def __init__(self):
        self._cache = build_tool_info()
        self._functional = FunctionalGetToolInfo()

    def get_tool_info(self, tool_id, tool_version=None):
        try:
            result = self._cache.get_tool_info(tool_id, tool_version)
            if result is not None:
                return result
        except Exception:
            pass
        return self._functional.get_tool_info(tool_id, tool_version)


_tool_info = _CombinedToolInfo()


INLINE_UDT_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "inline_udt")
# IWC-vendored workflows are shared with test/unit/workflows and live outside this
# package's symlinked test tree, so they're absent in the isolated tool_util package test.
IWC_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "workflows", "iwc"))


def _resolve_fixture_path(name: str) -> str:
    """Resolve a fixture name to a file path.

    Tries: fixtures/ dir, framework test data, IWC cache, inline-UDT dir,
    absolute path.
    """
    for base in [FIXTURES_DIR, FRAMEWORK_WORKFLOWS_DIR, INLINE_UDT_DIR]:
        candidate = os.path.join(base, name)
        if os.path.exists(candidate):
            return candidate
    candidate = os.path.join(IWC_DIR, name)
    if os.path.exists(candidate):
        return candidate
    if os.path.isabs(name) and os.path.exists(name):
        return name
    raise FileNotFoundError(f"Fixture not found: {name}")


def _load_fixture(name: str) -> dict:
    try:
        path = _resolve_fixture_path(name)
    except FileNotFoundError:
        if not os.path.isdir(IWC_DIR):
            pytest.skip(f"IWC fixture unavailable in this environment: {name}")
        raise
    return load_workflow(path)


def _run_clean(wf_dict: dict, skip_uuid: bool = False) -> dict:
    """Dispatch clean to the appropriate format-aware function."""
    workflow = copy.deepcopy(wf_dict)
    policy = StaleKeyPolicy.for_clean([], [])
    if _is_format2(workflow):
        clean_format2_state(workflow, _tool_info, policy=policy, skip_uuid=skip_uuid)
    else:
        normalized = ensure_native(workflow)
        clean_stale_state(normalized, workflow, _tool_info, policy=policy, skip_uuid=skip_uuid)
    return workflow


def _clean_op(wf_dict: dict) -> dict:
    """Full clean: strip all stale keys including bookkeeping.

    Returns the cleaned workflow dict directly so assertions
    navigate the workflow structure (not operation metadata).
    """
    return _run_clean(wf_dict)


def _clean_skip_uuid_op(wf_dict: dict) -> dict:
    """Clean with skip_uuid=True: structural step cleaning preserves uuid fields."""
    return _run_clean(wf_dict, skip_uuid=True)


def _validate_op(wf_dict: dict) -> dict:
    """Validate workflow; raise on precheck skip or validation failures.

    On success returns the workflow dict so assertions can navigate
    its structure.  Raises on legacy encoding (precheck skip) or
    validation errors, testable via ``expect_error: true``.
    """
    workflow = copy.deepcopy(wf_dict)
    results, precheck, _conn = validate_workflow_cli(workflow, _tool_info)
    if precheck is not None and not precheck.can_process:
        raise RuntimeError(f"Validation skipped: {precheck.detail}")
    failures = [r for r in results if r.status == "fail"]
    if failures:
        msgs = [f"step {r.step} ({r.tool_id}): {r.errors}" for r in failures]
        raise RuntimeError("Validation failed:\n" + "\n".join(msgs))
    return workflow


def _export_op(wf_dict: dict) -> dict:
    """Export to format2, return the format2 dict directly.

    Assertions navigate the format2 structure (class, inputs,
    steps, outputs) rather than export metadata.
    """
    normalized = ensure_native(wf_dict)
    result = export_workflow_to_format2(normalized, _tool_info)
    return result.format2_dict


def _clean_then_validate_op(wf_dict: dict) -> dict:
    """Clean stale state, then validate — the real-world pipeline.

    Returns the cleaned workflow dict on success.  Raises on
    validation failure after cleaning.
    """
    workflow = copy.deepcopy(wf_dict)
    normalized = ensure_native(workflow)
    policy = StaleKeyPolicy.for_clean([], [])
    clean_stale_state(normalized, workflow, _tool_info, policy=policy)
    results, precheck, _conn = validate_workflow_cli(workflow, _tool_info)
    if precheck is not None and not precheck.can_process:
        raise RuntimeError(f"Validation skipped after clean: {precheck.detail}")
    failures = [r for r in results if r.status == "fail"]
    if failures:
        msgs = [f"step {r.step} ({r.tool_id}): {r.errors}" for r in failures]
        raise RuntimeError("Validation failed after clean:\n" + "\n".join(msgs))
    return workflow


def _strict_encoding_op(wf_dict: dict) -> dict:
    """Check strict-encoding; raise on violations, return workflow on success."""
    errors = check_strict_encoding(wf_dict)
    if errors:
        raise RuntimeError("Strict-encoding violations:\n" + "\n".join(errors))
    return wf_dict


def _strict_structure_op(wf_dict: dict) -> dict:
    """Check strict-structure; raise on violations, return workflow on success."""
    errors = check_strict_structure(wf_dict)
    if errors:
        raise RuntimeError("Strict-structure violations:\n" + "\n".join(errors))
    return wf_dict


def _strict_state_validate_op(wf_dict: dict) -> dict:
    """Validate with strict-state semantics: skips and missing tools are failures.

    Raises on precheck skip, validation failures, or skipped steps.
    """
    workflow = copy.deepcopy(wf_dict)
    results, precheck, _conn = validate_workflow_cli(workflow, _tool_info)
    if precheck is not None and not precheck.can_process:
        raise RuntimeError(f"Strict-state: cannot process: {precheck.detail}")
    failures = [r for r in results if r.status == "fail"]
    if failures:
        msgs = [f"step {r.step} ({r.tool_id}): {r.errors}" for r in failures]
        raise RuntimeError("Strict-state validation failed:\n" + "\n".join(msgs))
    skips = [r for r in results if r.status in SKIP_STATUSES]
    if skips:
        msgs = [f"step {r.step} ({r.tool_id}): {r.errors}" for r in skips]
        raise RuntimeError("Strict-state: skipped steps:\n" + "\n".join(msgs))
    return workflow


def _validate_clean_op(wf_dict: dict) -> dict:
    """Validate with --clean: full stale-key cleaning before validation.

    Exercises the validate_workflow_cli(clean=True) codepath.
    Returns the (uncleaned) workflow dict on success — cleaning
    happens on an internal copy, the input is not mutated.
    """
    workflow = copy.deepcopy(wf_dict)
    results, precheck, _conn = validate_workflow_cli(workflow, _tool_info, clean=True)
    if precheck is not None and not precheck.can_process:
        raise RuntimeError(f"Validation skipped: {precheck.detail}")
    failures = [r for r in results if r.status == "fail"]
    if failures:
        msgs = [f"step {r.step} ({r.tool_id}): {r.errors}" for r in failures]
        raise RuntimeError("Validation failed:\n" + "\n".join(msgs))
    return workflow


OPERATIONS = {
    "clean": _clean_op,
    "clean_skip_uuid": _clean_skip_uuid_op,
    "validate": _validate_op,
    "validate_clean": _validate_clean_op,
    "export_format2": _export_op,
    "clean_then_validate": _clean_then_validate_op,
    "strict_encoding": _strict_encoding_op,
    "strict_structure": _strict_structure_op,
    "strict_state_validate": _strict_state_validate_op,
}

suite = DeclarativeTestSuite(
    operations=OPERATIONS,
    load_fixture=_load_fixture,
    expectations_dir=EXPECTATIONS_DIR,
)


@suite.pytest_params()
def test_declarative(test_id, case):
    suite.run(test_id, case)
