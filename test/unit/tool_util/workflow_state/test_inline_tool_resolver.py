"""Unit tests for the inline UDT parse + validate seam (Phase A).

Phase B will add resolver-shape tests (`resolve_for_step`); this module
exercises only the helpers that land in Phase A.
"""

from copy import deepcopy
from unittest.mock import patch

import pytest

from galaxy.tool_util.lint import (
    lint_user_tool_source_structured,
    NETWORK_LINTERS,
)
from galaxy.tool_util.workflow_state import InlineToolSourceResult
from galaxy.tool_util.workflow_state._inline_tool import (
    _parse_inline_tool,
    _validate_inline_tool_source,
)
from galaxy.tool_util_models import UserToolSource

MINIMAL_USER_TOOL: dict = {
    "class": "GalaxyUserTool",
    "id": "cat_user_defined",
    "name": "cat_user_defined",
    "version": "0.1",
    "container": "busybox",
    "shell_command": "cat '$(inputs.input1.path)' > output.txt",
    "inputs": [{"name": "input1", "type": "data", "format": "txt"}],
    "outputs": [{"name": "output1", "type": "data", "format": "txt", "from_work_dir": "output.txt"}],
}


def _rep(**overrides) -> dict:
    rep = deepcopy(MINIMAL_USER_TOOL)
    rep.update(overrides)
    return rep


def test_parse_minimal_user_tool():
    parsed = _parse_inline_tool(MINIMAL_USER_TOOL)
    assert parsed.id == "cat_user_defined"
    assert parsed.version == "0.1"
    assert len(parsed.inputs) == 1
    assert [o.name for o in parsed.outputs] == ["output1"]


def test_validate_source_minimal_clean():
    result = _validate_inline_tool_source(MINIMAL_USER_TOOL)
    assert isinstance(result, InlineToolSourceResult)
    assert result.ok is True
    assert result.supported is True
    assert result.inline_class == "GalaxyUserTool"
    assert result.validation_errors == []
    assert result.lint_errors == []


def test_validate_source_blank_version():
    result = _validate_inline_tool_source(_rep(version="   "))
    assert result.ok is False
    assert any("version" in err for err in result.validation_errors)


def test_validate_source_undeclared_input_ref():
    result = _validate_inline_tool_source(_rep(shell_command="echo $(inputs.missing)"))
    assert result.ok is False
    joined = " ".join(result.validation_errors)
    assert "missing" in joined


def test_validate_source_unclaimed_output():
    result = _validate_inline_tool_source(_rep(outputs=[{"name": "output1", "type": "data", "format": "txt"}]))
    assert result.ok is False
    joined = " ".join(result.validation_errors)
    assert "from_work_dir" in joined or "discover_datasets" in joined


def test_admin_class_emits_unsupported():
    rep = _rep()
    rep["class"] = "GalaxyTool"
    result = _validate_inline_tool_source(rep)
    assert result.supported is False
    assert result.ok is False
    assert result.inline_class == "GalaxyTool"
    # No pydantic validation against UserToolSource for the admin class.
    assert result.validation_errors == []


def test_unknown_class_emits_unsupported():
    rep = _rep()
    rep["class"] = "SomethingElse"
    result = _validate_inline_tool_source(rep)
    assert result.supported is False
    assert result.inline_class == "SomethingElse"


def test_validate_passes_offline_skips_network_linters():
    """``offline=True`` must thread ``skip_network=True`` through to the linter.

    Patches the linter at the call site and asserts the keyword flips.
    """
    with patch(
        "galaxy.tool_util.workflow_state._inline_tool.lint_user_tool_source_structured",
        return_value=([], []),
    ) as mock_lint:
        _validate_inline_tool_source(MINIMAL_USER_TOOL, offline=True)
        _validate_inline_tool_source(MINIMAL_USER_TOOL, offline=False)

    assert mock_lint.call_count == 2
    assert mock_lint.call_args_list[0].kwargs == {"skip_network": True}
    assert mock_lint.call_args_list[1].kwargs == {"skip_network": False}


def test_lint_structured_returns_severity_tuple():
    src = UserToolSource.model_validate(MINIMAL_USER_TOOL)
    errors, warnings = lint_user_tool_source_structured(src, skip_network=True)
    assert isinstance(errors, list)
    assert isinstance(warnings, list)
    assert errors == []


def test_lint_structured_network_linters_gated_by_skip_network():
    src = UserToolSource.model_validate(MINIMAL_USER_TOOL)

    seen_skips: list[list[str]] = []

    def _capture(tool_source, extra_modules=None, skip_types=None, name=None):
        seen_skips.append(list(skip_types or []))
        # Return an empty lint context-like stub to avoid running the
        # real linters; the structured wrapper only reads
        # error_messages / warn_messages.
        from galaxy.tool_util.lint import LintContext, LintLevel

        return LintContext(level=LintLevel.ALL, skip_types=skip_types, object_name=name)

    with patch(
        "galaxy.tool_util.lint.get_lint_context_for_tool_source",
        side_effect=_capture,
    ):
        lint_user_tool_source_structured(src, skip_network=True)
        lint_user_tool_source_structured(src, skip_network=False)

    assert sorted(seen_skips[0]) == sorted(NETWORK_LINTERS)
    assert seen_skips[1] == []


@pytest.mark.parametrize(
    "field",
    ["name", "container", "shell_command"],
)
def test_validate_source_missing_required_field(field):
    rep = _rep()
    rep.pop(field)
    result = _validate_inline_tool_source(rep)
    assert result.ok is False
    assert result.validation_errors  # actual messages vary; just ensure populated


def test_validate_source_missing_id_caught_by_linter():
    """``id`` is optional on the pydantic schema but flagged by the linter."""
    rep = _rep()
    rep.pop("id")
    result = _validate_inline_tool_source(rep)
    assert result.ok is False
    assert result.validation_errors == []
    assert any("id" in err.lower() for err in result.lint_errors)
