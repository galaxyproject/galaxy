"""Declarative YAML-driven tests for Galaxy workflow_state operations.

Uses gxformat2.testing harness with Galaxy-specific operations.
Expectation files live in test/unit/tool_util/workflow_state/expectations/.
"""

import copy
import os

from gxformat2.normalized import ensure_native
from gxformat2.testing import DeclarativeTestSuite

from galaxy.tool_util.workflow_state.cache import build_tool_info
from galaxy.tool_util.workflow_state.clean import clean_stale_state
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


def _resolve_fixture_path(name: str) -> str:
    """Resolve a fixture name to a file path.

    Tries: fixtures/ dir, framework test data, IWC cache, absolute path.
    """
    for base in [FIXTURES_DIR, FRAMEWORK_WORKFLOWS_DIR]:
        candidate = os.path.join(base, name)
        if os.path.exists(candidate):
            return candidate
    iwc_dir = os.path.join(os.path.dirname(__file__), "..", "..", "workflows", "iwc")
    candidate = os.path.normpath(os.path.join(iwc_dir, name))
    if os.path.exists(candidate):
        return candidate
    if os.path.isabs(name) and os.path.exists(name):
        return name
    raise FileNotFoundError(f"Fixture not found: {name}")


def _load_fixture(name: str) -> dict:
    path = _resolve_fixture_path(name)
    return load_workflow(path)


def _clean_op(wf_dict: dict) -> dict:
    """Full clean: strip all stale keys including bookkeeping.

    Returns the cleaned workflow dict directly so assertions
    navigate the workflow structure (not operation metadata).
    """
    workflow = copy.deepcopy(wf_dict)
    normalized = ensure_native(workflow)
    policy = StaleKeyPolicy.for_clean([], [])
    clean_stale_state(normalized, workflow, _tool_info, policy=policy)
    return workflow


def _validate_op(wf_dict: dict) -> dict:
    """Validate workflow; raise on precheck skip or validation failures.

    On success returns the workflow dict so assertions can navigate
    its structure.  Raises on legacy encoding (precheck skip) or
    validation errors, testable via ``expect_error: true``.
    """
    workflow = copy.deepcopy(wf_dict)
    results, precheck, _conn = validate_workflow_cli(workflow, _tool_info)
    if precheck is not None and not precheck.can_process:
        raise RuntimeError(f"Validation skipped: {precheck.reason}")
    failures = [r for r in results if r.status == "fail"]
    if failures:
        msgs = [f"step {r.step} ({r.tool_id}): {[e.message for e in r.errors]}" for r in failures]
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
        raise RuntimeError(f"Validation skipped after clean: {precheck.reason}")
    failures = [r for r in results if r.status == "fail"]
    if failures:
        msgs = [f"step {r.step} ({r.tool_id}): {[e.message for e in r.errors]}" for r in failures]
        raise RuntimeError("Validation failed after clean:\n" + "\n".join(msgs))
    return workflow


OPERATIONS = {
    "clean": _clean_op,
    "validate": _validate_op,
    "export_format2": _export_op,
    "clean_then_validate": _clean_then_validate_op,
}

suite = DeclarativeTestSuite(
    operations=OPERATIONS,
    load_fixture=_load_fixture,
    expectations_dir=EXPECTATIONS_DIR,
)


@suite.pytest_params()
def test_declarative(test_id, case):
    suite.run(test_id, case)
