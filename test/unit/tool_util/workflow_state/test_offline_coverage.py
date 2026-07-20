"""Phase C/D coverage tests: --offline plumbing across gxwf + galaxy-tool-cache.

Covers §9.6 ``test_offline_coverage`` from USER_DEFINED_TOOL_STEP_VALIDATION.md.
Limited to the subcommand-registration and short-circuit assertions —
deeper network-linter side-effects are exercised in test_inline_source_validation.
"""

import pytest

from galaxy.tool_util.workflow_state._cli_common import build_base_parser
from galaxy.tool_util.workflow_state.toolshed_tool_info import ToolShedGetToolInfo

# -- Every gxwf-style parser accepts --offline -------------------------------


def test_base_parser_accepts_offline():
    parser = build_base_parser(prog="gxwf-x", description="x")
    args = parser.parse_args(["--offline", "/tmp/wf.ga"])
    assert args.offline is True


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(
            "galaxy.tool_util.workflow_state.scripts.workflow_validate:build_parser",
            id="gxwf-state-validate",
        ),
        pytest.param(
            "galaxy.tool_util.workflow_state.scripts.workflow_validate_tree:build_parser",
            id="gxwf-state-validate-tree",
        ),
        pytest.param(
            "galaxy.tool_util.workflow_state.scripts.workflow_lint_stateful:build_parser",
            id="gxwf-lint-stateful",
        ),
        pytest.param(
            "galaxy.tool_util.workflow_state.scripts.workflow_lint_stateful_tree:build_parser",
            id="gxwf-lint-stateful-tree",
        ),
    ],
)
def test_gxwf_subcommand_accepts_offline(build):
    import importlib

    module_name, attr = build.split(":")
    parser = getattr(importlib.import_module(module_name), attr)()
    args = parser.parse_args(["--offline", "/tmp/wf.ga"])
    assert args.offline is True


# -- galaxy-tool-cache populate-workflow honors --offline --------------------


def test_galaxy_tool_cache_populate_workflow_offline_arg():
    from galaxy.tool_util.workflow_state.scripts.tool_cache import build_parser

    parser = build_parser()
    args = parser.parse_args(["populate-workflow", "/tmp/wf.ga", "--offline"])
    assert args.offline is True


def test_populate_cache_offline_skips_add_tool(tmp_path):
    """populate_cache with offline=True does not call add_tool."""
    import json

    from galaxy.tool_util.workflow_state import cache as cache_mod

    wf = {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "name": "shed only",
        "steps": {
            "0": {
                "id": 0,
                "type": "tool",
                "tool_id": "toolshed.example/repo/cat/cat/1.0",
                "tool_version": "1.0",
                "tool_state": "{}",
                "input_connections": {},
                "outputs": [],
            },
        },
    }
    wf_path = tmp_path / "wf.ga"
    wf_path.write_text(json.dumps(wf))

    captured = {"count": 0}

    def spy(*args, **kwargs):
        captured["count"] += 1
        return True

    orig = cache_mod.add_tool
    cache_mod.add_tool = spy
    try:
        cache_mod.populate_cache(
            tool_info=ToolShedGetToolInfo(cache_dir=str(tmp_path)), path=str(wf_path), offline=True
        )
    finally:
        cache_mod.add_tool = orig

    assert captured["count"] == 0, "add_tool must not be called under --offline"


def test_populate_cache_default_calls_add_tool(tmp_path):
    """Without --offline, populate_cache calls add_tool for each toolshed tool."""
    import json

    from galaxy.tool_util.workflow_state import cache as cache_mod

    wf = {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "name": "shed only",
        "steps": {
            "0": {
                "id": 0,
                "type": "tool",
                "tool_id": "toolshed.example/repo/cat/cat/1.0",
                "tool_version": "1.0",
                "tool_state": "{}",
                "input_connections": {},
                "outputs": [],
            },
        },
    }
    wf_path = tmp_path / "wf.ga"
    wf_path.write_text(json.dumps(wf))

    captured = {"count": 0}

    def spy(*args, **kwargs):
        captured["count"] += 1
        return True

    orig = cache_mod.add_tool
    cache_mod.add_tool = spy
    try:
        cache_mod.populate_cache(
            tool_info=ToolShedGetToolInfo(cache_dir=str(tmp_path)), path=str(wf_path), offline=False
        )
    finally:
        cache_mod.add_tool = orig

    assert captured["count"] == 1, "add_tool should be called once for the single toolshed tool"
