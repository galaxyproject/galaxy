"""Sweep tests: run workflow_state operations against a real IWC checkout.

Gated on GALAXY_TEST_IWC_DIRECTORY — skipped unless set.
Uses the default tool cache (~/.galaxy/tool_info_cache/) and auto-populates
missing tools from the ToolShed on first run.
"""

import os
from pathlib import Path
from typing import (
    List,
    Optional,
)

import pytest
from gxformat2.normalized import ensure_native

from galaxy.tool_util.workflow_state.cache import (
    build_tool_info,
    populate_cache,
)
from galaxy.tool_util.workflow_state.clean import clean_stale_state
from galaxy.tool_util.workflow_state.export_format2 import export_workflow_to_format2
from galaxy.tool_util.workflow_state.lint_stateful import run_structural_lint
from galaxy.tool_util.workflow_state.roundtrip import roundtrip_validate
from galaxy.tool_util.workflow_state.to_native_stateful import convert_to_native_stateful
from galaxy.tool_util.workflow_state.validate import validate_workflow_cli
from galaxy.tool_util.workflow_state.validation_json_schema import validate_workflow_json_schema
from galaxy.tool_util.workflow_state.validation_native import validate_workflow_native
from galaxy.tool_util.workflow_state.workflow_tools import load_workflow
from galaxy.tool_util_models import ParsedTool
from galaxy.util.unittest_utils import skip_unless_environ

IWC_ENV = "GALAXY_TEST_IWC_DIRECTORY"


def _discover_native_workflows() -> List[str]:
    iwc_dir = os.environ.get(IWC_ENV, "")
    if not iwc_dir:
        return []
    return sorted(str(p) for p in Path(iwc_dir).rglob("workflows/**/*.ga") if p.is_file())


def _workflow_id(path: str) -> str:
    iwc_dir = os.environ.get(IWC_ENV, "")
    return os.path.relpath(path, os.path.join(iwc_dir, "workflows"))


class _LenientToolInfo:
    """Wraps a GetToolInfo to return None instead of raising on missing tools."""

    def __init__(self, delegate):
        self._delegate = delegate

    def get_tool_info(self, tool_id: str, tool_version: Optional[str]) -> Optional[ParsedTool]:
        try:
            return self._delegate.get_tool_info(tool_id, tool_version)
        except (KeyError, Exception):
            return None


@pytest.fixture(scope="session")
def tool_info():
    """Build ToolShedGetToolInfo using default cache, populate for all IWC workflows."""
    cache_dir = os.environ.get("GALAXY_TOOL_CACHE_DIR")
    info = build_tool_info(cache_dir)
    for wf_path in _discover_native_workflows():
        populate_cache(info, wf_path, source="shed")
    return _LenientToolInfo(info)


@skip_unless_environ(IWC_ENV)
class TestIWCSweepValidateNative:
    """validate_workflow_native after cleaning stale state."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_validate_native(self, wf_path, tool_info):
        workflow = load_workflow(wf_path)
        normalized = ensure_native(workflow)
        clean_stale_state(normalized, workflow, tool_info)
        validate_workflow_native(workflow, tool_info)


@skip_unless_environ(IWC_ENV)
class TestIWCSweepClean:
    """clean_stale_state on every IWC .ga workflow."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_clean(self, wf_path, tool_info):
        workflow = load_workflow(wf_path)
        normalized = ensure_native(workflow)
        result = clean_stale_state(normalized, workflow, tool_info)
        assert result is not None


@skip_unless_environ(IWC_ENV)
class TestIWCSweepExport:
    """export_workflow_to_format2 on every IWC .ga workflow."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_export(self, wf_path, tool_info):
        workflow = ensure_native(wf_path)
        result = export_workflow_to_format2(workflow, tool_info)
        assert result.format2 is not None
        fmt2_dict = result.format2_dict
        assert fmt2_dict.get("class") == "GalaxyWorkflow"


@skip_unless_environ(IWC_ENV)
class TestIWCSweepRoundtrip:
    """roundtrip_validate on every IWC .ga workflow."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_roundtrip(self, wf_path, tool_info):
        workflow = load_workflow(wf_path)
        result = roundtrip_validate(workflow, tool_info, workflow_path=wf_path)
        assert result.ok, f"Roundtrip failed for {wf_path}: {result.error or result.error_diffs}"


@skip_unless_environ(IWC_ENV)
class TestIWCSweepToNativeStateful:
    """convert_to_native_stateful on every IWC .ga exported to format2 first."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_to_native_stateful(self, wf_path, tool_info, tmp_path):
        workflow = ensure_native(wf_path)
        f2_result = export_workflow_to_format2(workflow, tool_info)
        # Write format2 to temp file so convert_to_native_stateful can load it
        import json

        f2_path = str(tmp_path / "workflow.gxwf.yml")
        with open(f2_path, "w") as f:
            json.dump(f2_result.format2_dict, f, indent=2)
        result = convert_to_native_stateful(f2_path, tool_info)
        assert result.native is not None
        assert result.native_dict.get("a_galaxy_workflow") == "true"


@skip_unless_environ(IWC_ENV)
class TestIWCSweepLintStateful:
    """run_structural_lint + validate_workflow_cli on every IWC .ga workflow."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_lint_stateful(self, wf_path, tool_info):
        workflow_dict = load_workflow(wf_path)
        lint_ctx = run_structural_lint(workflow_dict)
        assert lint_ctx is not None
        results, precheck, _conn_report = validate_workflow_cli(workflow_dict, tool_info)
        assert results is not None


@skip_unless_environ(IWC_ENV)
class TestIWCSweepJsonSchema:
    """Two-level JSON Schema validation on exported format2 workflows."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_json_schema_validate(self, wf_path, tool_info):
        workflow = ensure_native(wf_path)
        export_result = export_workflow_to_format2(workflow, tool_info)
        fmt2_dict = export_result.format2_dict
        result = validate_workflow_json_schema(fmt2_dict, get_tool_info=tool_info)
        errors = []
        if result.structural_errors:
            errors.append(f"structural: {[e.message for e in result.structural_errors]}")
        for sr in result.step_results:
            if sr.status == "fail":
                errors.append(f"step {sr.step} ({sr.tool_id}): {[e.message for e in sr.errors]}")
        assert result.valid, f"JSON Schema validation failed for {wf_path}:\n" + "\n".join(errors)
