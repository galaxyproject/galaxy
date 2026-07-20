"""Fixture-based connection validation tests.

Auto-discovers gxformat2 workflow fixtures and validates them.
ok_* workflows must validate, fail_* must not.
Sidecar YAML files in expected/ provide targeted assertions via dict_verify_each.
"""

from pathlib import Path

import pytest
import yaml
from gxformat2.converter import python_to_workflow

from galaxy.tool_util.workflow_state.connection_validation import (
    validate_connections_report,
)
from .functional_tool_info import FunctionalGetToolInfo
from ..util import dict_verify_each

WORKFLOW_DIR = Path(__file__).parent / "connection_workflows"
EXPECTED_DIR = WORKFLOW_DIR / "expected"


def discover_workflows():
    if not WORKFLOW_DIR.exists():
        return []
    return sorted(WORKFLOW_DIR.glob("*.gxwf.yml"))


def workflow_ids():
    return [p.stem.removesuffix(".gxwf") for p in discover_workflows()]


@pytest.fixture(scope="module")
def tool_info():
    return FunctionalGetToolInfo()


def _collect_errors(report):
    errors = []
    for sr in report.step_results:
        errors.extend(sr.errors)
        for cr in sr.connections:
            errors.extend(cr.errors)
    return errors


@pytest.mark.parametrize("workflow_path", discover_workflows(), ids=workflow_ids())
def test_connection_workflow(workflow_path, tool_info):
    wf_dict = yaml.safe_load(workflow_path.read_text())
    native = python_to_workflow(wf_dict, galaxy_interface=None)
    report = validate_connections_report(native, tool_info)

    stem = workflow_path.stem
    if stem.startswith("ok_"):
        assert report.valid, f"Expected valid but got errors: {_collect_errors(report)}"
    elif stem.startswith("fail_"):
        assert not report.valid, "Expected invalid but workflow validated"
    else:
        pytest.skip(f"Unknown prefix for {stem}")

    # Check sidecar expectations if present
    expected_path = EXPECTED_DIR / f"{stem}.yml"
    if expected_path.exists():
        raw = yaml.safe_load(expected_path.read_text())
        expectations = [(e["target"], e["value"]) for e in raw]
        report_dict = report.model_dump(by_alias=True, exclude_none=True)
        dict_verify_each(report_dict, expectations)
