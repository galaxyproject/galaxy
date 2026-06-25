"""Tests for StrictOptions decomposition (--strict = structure + encoding + state)."""

import argparse
import json

from galaxy.tool_util.workflow_state._cli_common import (
    add_strict_args,
    StrictOptions,
)
from galaxy.tool_util.workflow_state._encoding import (
    validate_encoding_format2,
    validate_encoding_native,
)
from galaxy.tool_util.workflow_state.export_format2 import ExportOptions
from galaxy.tool_util.workflow_state.lint_stateful import (
    _combined_exit_code,
    LintStatefulOptions,
)
from galaxy.tool_util.workflow_state.roundtrip import RoundTripValidateOptions
from galaxy.tool_util.workflow_state.to_native_stateful import ToNativeOptions
from galaxy.tool_util.workflow_state.validate import (
    run_validate,
    ValidateOptions,
)
from galaxy.tool_util.workflow_state._report_models import ValidationStepResult
from gxformat2.linting import LintContext


def test_strict_shorthand_expands():
    o = StrictOptions(strict=True)
    assert o.strict
    assert o.strict_structure
    assert o.strict_encoding
    assert o.strict_state


def test_strict_default_all_false():
    o = StrictOptions()
    assert not o.strict
    assert not o.strict_structure
    assert not o.strict_encoding
    assert not o.strict_state


def test_strict_sub_flags_independent():
    o = StrictOptions(strict_structure=True)
    assert not o.strict
    assert o.strict_structure
    assert not o.strict_encoding
    assert not o.strict_state

    o = StrictOptions(strict_encoding=True)
    assert not o.strict_structure and o.strict_encoding and not o.strict_state

    o = StrictOptions(strict_state=True)
    assert not o.strict_structure and not o.strict_encoding and o.strict_state


def test_strict_sub_flags_compose():
    o = StrictOptions(strict_structure=True, strict_encoding=True)
    assert not o.strict
    assert o.strict_structure and o.strict_encoding
    assert not o.strict_state


def test_add_strict_args_defaults_false():
    parser = argparse.ArgumentParser()
    add_strict_args(parser)
    args = parser.parse_args([])
    assert args.strict is False
    assert args.strict_structure is False
    assert args.strict_encoding is False
    assert args.strict_state is False


def test_add_strict_args_shorthand():
    parser = argparse.ArgumentParser()
    add_strict_args(parser)
    args = parser.parse_args(["--strict"])
    # argparse sets only --strict; expansion happens in the pydantic model
    assert args.strict is True
    assert args.strict_structure is False
    o = StrictOptions(**vars(args))
    assert o.strict_structure and o.strict_encoding and o.strict_state


def test_add_strict_args_individual():
    parser = argparse.ArgumentParser()
    add_strict_args(parser)
    args = parser.parse_args(["--strict-encoding"])
    assert not args.strict
    assert not args.strict_structure
    assert args.strict_encoding
    assert not args.strict_state


def test_validate_options_inherits_strict():
    o = ValidateOptions(workflow_path="x", strict=True)
    assert o.strict_structure and o.strict_encoding and o.strict_state

    o = ValidateOptions(workflow_path="x", strict_state=True)
    assert not o.strict and not o.strict_structure and not o.strict_encoding
    assert o.strict_state


def test_lint_stateful_options_inherits_strict():
    o = LintStatefulOptions(workflow_path="x", strict=True)
    assert o.strict_structure and o.strict_encoding and o.strict_state


def test_export_options_inherits_strict():
    o = ExportOptions(workflow_path="x", strict=True)
    assert o.strict_structure and o.strict_encoding and o.strict_state


def test_to_native_options_inherits_strict():
    o = ToNativeOptions(workflow_path="x", strict=True)
    assert o.strict_structure and o.strict_encoding and o.strict_state


def test_roundtrip_options_inherits_strict():
    o = RoundTripValidateOptions(workflow_path="x", strict=True)
    assert o.strict_structure and o.strict_encoding and o.strict_state


def test_options_from_namespace_expands_strict():
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow_path")
    add_strict_args(parser)
    args = parser.parse_args(["foo.ga", "--strict"])
    o = ValidateOptions.from_namespace(args)
    assert o.strict_structure and o.strict_encoding and o.strict_state


# -- Step 4: behavioral tests for --strict-state at enforcement sites --


def _skip_result():
    return ValidationStepResult(
        step="0",
        tool_id="unknown_tool",
        status="skip_tool_not_found",
        errors=["No tool definition"],
    )


def _ok_result():
    return ValidationStepResult(step="0", tool_id="known_tool", status="ok")


def _fail_result():
    return ValidationStepResult(step="0", tool_id="broken", status="fail", errors=["bad"])


def test_combined_exit_code_skip_strict_state_true():
    ctx = LintContext(level="all")
    assert _combined_exit_code(ctx, [_skip_result()], strict_state=True) == 2


def test_combined_exit_code_skip_strict_state_false():
    ctx = LintContext(level="all")
    assert _combined_exit_code(ctx, [_skip_result()], strict_state=False) == 0


def test_combined_exit_code_fail_overrides_strict_state():
    ctx = LintContext(level="all")
    # fail → exit 1 regardless of strict_state
    assert _combined_exit_code(ctx, [_fail_result()], strict_state=False) == 1
    assert _combined_exit_code(ctx, [_fail_result()], strict_state=True) == 1


def _write_native_unknown_tool(tmp_path):
    """Write a native workflow whose tool is not resolvable (clean encoding)."""
    wf = {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "steps": {
            "0": {
                "tool_id": "synthetic/unknown_tool",
                "tool_version": "1.0.0",
                "type": "tool",
                "tool_state": {"param": "value"},
            }
        },
    }
    path = tmp_path / "unknown_tool.ga"
    path.write_text(json.dumps(wf))
    return str(path)


def test_run_validate_skip_default_exit_0(tmp_path, monkeypatch):
    path = _write_native_unknown_tool(tmp_path)
    # Force tool cache miss
    from galaxy.tool_util.workflow_state import validate as validate_mod

    class _NullInfo:
        def get_tool_info(self, tool_id, tool_version=None):
            return None

    monkeypatch.setattr(validate_mod, "setup_tool_info", lambda options: _NullInfo())

    opts = ValidateOptions(workflow_path=path)
    assert run_validate(opts) == 0


def test_run_validate_skip_strict_state_exit_2(tmp_path, monkeypatch):
    path = _write_native_unknown_tool(tmp_path)
    from galaxy.tool_util.workflow_state import validate as validate_mod

    class _NullInfo:
        def get_tool_info(self, tool_id, tool_version=None):
            return None

    monkeypatch.setattr(validate_mod, "setup_tool_info", lambda options: _NullInfo())

    opts = ValidateOptions(workflow_path=path, strict_state=True)
    assert run_validate(opts) == 2


def test_run_validate_skip_strict_shorthand_exit_2(tmp_path, monkeypatch):
    path = _write_native_unknown_tool(tmp_path)
    from galaxy.tool_util.workflow_state import validate as validate_mod

    class _NullInfo:
        def get_tool_info(self, tool_id, tool_version=None):
            return None

    monkeypatch.setattr(validate_mod, "setup_tool_info", lambda options: _NullInfo())

    opts = ValidateOptions(workflow_path=path, strict=True)
    assert run_validate(opts) == 2


# -- Step 3: encoding validator unit tests --


def test_validate_encoding_native_clean():
    wf = {
        "a_galaxy_workflow": "true",
        "steps": {
            "0": {"type": "tool", "tool_id": "t", "tool_state": {"x": 1}},
        },
    }
    assert validate_encoding_native(wf) == []


def test_validate_encoding_native_rejects_string_tool_state():
    wf = {
        "a_galaxy_workflow": "true",
        "steps": {
            "0": {"type": "tool", "tool_id": "t", "tool_state": json.dumps({"x": 1})},
        },
    }
    errors = validate_encoding_native(wf)
    assert len(errors) == 1
    assert "tool_state is a JSON string" in errors[0]


def test_validate_encoding_native_ignores_non_tool_steps():
    wf = {
        "a_galaxy_workflow": "true",
        "steps": {
            "0": {"type": "data_input", "tool_state": "something"},
        },
    }
    assert validate_encoding_native(wf) == []


def test_validate_encoding_format2_clean():
    wf = {"steps": [{"tool_id": "t", "state": {"x": 1}}]}
    assert validate_encoding_format2(wf) == []


def test_validate_encoding_format2_rejects_tool_state_field():
    wf = {"steps": [{"tool_id": "t", "tool_state": {"x": 1}}]}
    errors = validate_encoding_format2(wf)
    assert len(errors) == 1
    assert "tool_state" in errors[0] and "instead of `state`" in errors[0]


# -- Step 3: behavioral wiring tests --


def _write_native_string_tool_state(tmp_path):
    """Write a native workflow whose tool_state is a JSON string (legacy-like)."""
    wf = {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "steps": {
            "0": {
                "tool_id": "synthetic/unknown_tool",
                "tool_version": "1.0.0",
                "type": "tool",
                "tool_state": json.dumps({"param": "value"}),
            }
        },
    }
    path = tmp_path / "string_tool_state.ga"
    path.write_text(json.dumps(wf))
    return str(path)


def test_run_validate_strict_encoding_rejects_json_string_tool_state(tmp_path, monkeypatch):
    path = _write_native_string_tool_state(tmp_path)
    from galaxy.tool_util.workflow_state import validate as validate_mod

    class _NullInfo:
        def get_tool_info(self, tool_id, tool_version=None):
            return None

    monkeypatch.setattr(validate_mod, "setup_tool_info", lambda options: _NullInfo())

    opts = ValidateOptions(workflow_path=path, strict_encoding=True)
    assert run_validate(opts) == 2


def test_run_validate_strict_state_alone_allows_json_string_tool_state(tmp_path, monkeypatch):
    """strict_state alone should NOT reject JSON-string tool_state."""
    path = _write_native_string_tool_state(tmp_path)
    from galaxy.tool_util.workflow_state import validate as validate_mod

    class _NullInfo:
        def get_tool_info(self, tool_id, tool_version=None):
            return None

    monkeypatch.setattr(validate_mod, "setup_tool_info", lambda options: _NullInfo())

    # This workflow has legacy encoding → precheck will skip → strict_state promotes to fail.
    # But reason is precheck, not strict-encoding. We're verifying strict-encoding is orthogonal.
    opts = ValidateOptions(workflow_path=path, strict_encoding=False)
    # Without strict-encoding or strict-state: precheck skip → exit 0
    assert run_validate(opts) == 0


def test_run_validate_skip_strict_structure_alone_exit_0(tmp_path, monkeypatch):
    """strict_structure alone should NOT promote skipped steps to failure."""
    path = _write_native_unknown_tool(tmp_path)
    from galaxy.tool_util.workflow_state import validate as validate_mod

    class _NullInfo:
        def get_tool_info(self, tool_id, tool_version=None):
            return None

    monkeypatch.setattr(validate_mod, "setup_tool_info", lambda options: _NullInfo())

    opts = ValidateOptions(workflow_path=path, strict_structure=True)
    assert run_validate(opts) == 0


# -- Step 2: strict-structure validator + wiring --


def _write_native_with_extra_key(tmp_path, extra_key="bogus_root_key"):
    """Native workflow with an unknown top-level key (rejected by strict schema)."""
    wf = {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "steps": {
            "0": {
                "tool_id": "synthetic/unknown_tool",
                "tool_version": "1.0.0",
                "type": "tool",
                "tool_state": {"param": "value"},
            }
        },
        extra_key: "surprise",
    }
    path = tmp_path / "extra_key.ga"
    path.write_text(json.dumps(wf))
    return str(path)


def _write_format2_with_extra_key(tmp_path, extra_key="bogus_root_key"):
    """Format2 workflow with an unknown top-level key."""
    wf = {
        "class": "GalaxyWorkflow",
        "inputs": {},
        "outputs": {},
        "steps": {},
        extra_key: "surprise",
    }
    path = tmp_path / "extra_key.gxwf.yml"
    import yaml as _yaml

    path.write_text(_yaml.safe_dump(wf))
    return str(path)


def test_check_strict_structure_clean_native():
    from galaxy.tool_util.workflow_state._encoding import check_strict_structure as _check_strict_structure

    wf = {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "steps": {},
    }
    assert _check_strict_structure(wf) == []


def test_check_strict_structure_native_extra_key():
    from galaxy.tool_util.workflow_state._encoding import check_strict_structure as _check_strict_structure

    wf = {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "steps": {},
        "bogus_root_key": "surprise",
    }
    errors = _check_strict_structure(wf)
    assert errors
    assert "bogus_root_key" in errors[0]


def test_check_strict_structure_clean_format2():
    from galaxy.tool_util.workflow_state._encoding import check_strict_structure as _check_strict_structure

    wf = {
        "class": "GalaxyWorkflow",
        "inputs": {},
        "outputs": {},
        "steps": {},
    }
    assert _check_strict_structure(wf) == []


def test_check_strict_structure_format2_extra_key():
    from galaxy.tool_util.workflow_state._encoding import check_strict_structure as _check_strict_structure

    wf = {
        "class": "GalaxyWorkflow",
        "inputs": {},
        "outputs": {},
        "steps": {},
        "bogus_root_key": "surprise",
    }
    errors = _check_strict_structure(wf)
    assert errors
    assert "bogus_root_key" in errors[0]


def test_run_validate_strict_structure_rejects_extra_key(tmp_path, monkeypatch):
    path = _write_native_with_extra_key(tmp_path)
    from galaxy.tool_util.workflow_state import validate as validate_mod

    class _NullInfo:
        def get_tool_info(self, tool_id, tool_version=None):
            return None

    monkeypatch.setattr(validate_mod, "setup_tool_info", lambda options: _NullInfo())

    opts = ValidateOptions(workflow_path=path, strict_structure=True)
    assert run_validate(opts) == 2


def test_run_validate_no_strict_structure_accepts_extra_key(tmp_path, monkeypatch):
    path = _write_native_with_extra_key(tmp_path)
    from galaxy.tool_util.workflow_state import validate as validate_mod

    class _NullInfo:
        def get_tool_info(self, tool_id, tool_version=None):
            return None

    monkeypatch.setattr(validate_mod, "setup_tool_info", lambda options: _NullInfo())

    # Without strict_structure, extra keys are ignored; tool is unknown → skip → exit 0
    opts = ValidateOptions(workflow_path=path)
    assert run_validate(opts) == 0


def test_run_validate_strict_shorthand_rejects_extra_key(tmp_path, monkeypatch):
    path = _write_native_with_extra_key(tmp_path)
    from galaxy.tool_util.workflow_state import validate as validate_mod

    class _NullInfo:
        def get_tool_info(self, tool_id, tool_version=None):
            return None

    monkeypatch.setattr(validate_mod, "setup_tool_info", lambda options: _NullInfo())

    opts = ValidateOptions(workflow_path=path, strict=True)
    assert run_validate(opts) == 2


def test_run_lint_stateful_strict_structure_rejects_extra_key(tmp_path, monkeypatch):
    from galaxy.tool_util.workflow_state import lint_stateful as lint_mod

    path = _write_native_with_extra_key(tmp_path)

    class _NullInfo:
        def get_tool_info(self, tool_id, tool_version=None):
            return None

    monkeypatch.setattr(lint_mod, "setup_tool_info", lambda options: _NullInfo())
    opts = LintStatefulOptions(workflow_path=path, strict_structure=True)
    assert lint_mod.run_lint_stateful(opts) == 2


def test_run_export_strict_structure_rejects_extra_key(tmp_path, monkeypatch):
    from galaxy.tool_util.workflow_state import export_format2 as export_mod

    path = _write_native_with_extra_key(tmp_path)

    class _NullInfo:
        def get_tool_info(self, tool_id, tool_version=None):
            return None

    monkeypatch.setattr(export_mod, "setup_tool_info", lambda options: _NullInfo())
    opts = ExportOptions(workflow_path=path, strict_structure=True)
    assert export_mod.run_export(opts) == 2


def test_run_to_native_strict_structure_rejects_extra_key(tmp_path, monkeypatch):
    from galaxy.tool_util.workflow_state import to_native_stateful as tn_mod

    path = _write_format2_with_extra_key(tmp_path)

    class _NullInfo:
        def get_tool_info(self, tool_id, tool_version=None):
            return None

    monkeypatch.setattr(tn_mod, "setup_tool_info", lambda options: _NullInfo())
    opts = ToNativeOptions(workflow_path=path, strict_structure=True)
    assert tn_mod.run_to_native(opts) == 2


# -- Step 5: roundtrip strict wiring --


class _NullInfo:
    def get_tool_info(self, tool_id, tool_version=None):
        return None


def test_roundtrip_validate_strict_structure_rejects_input_extra_key():
    from galaxy.tool_util.workflow_state.roundtrip import roundtrip_validate

    wf = {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "steps": {},
        "bogus_root_key": "surprise",
    }
    result = roundtrip_validate(wf, _NullInfo(), strict_structure=True)
    assert result.structure_errors
    assert result.error and "strict-structure (input)" in result.error
    # Downstream stages did not run
    assert result.format2_dict is None
    assert result.reimported_dict is None


def test_roundtrip_validate_strict_encoding_rejects_input_string_tool_state():
    from galaxy.tool_util.workflow_state.roundtrip import roundtrip_validate

    wf = {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "steps": {
            "0": {
                "type": "tool",
                "tool_id": "synthetic/unknown_tool",
                "tool_version": "1.0.0",
                "tool_state": json.dumps({"x": 1}),
            }
        },
    }
    result = roundtrip_validate(wf, _NullInfo(), strict_encoding=True)
    assert result.encoding_errors
    assert result.error and "strict-encoding (input)" in result.error


def test_roundtrip_validate_strict_state_promotes_precheck_skip(monkeypatch):
    """Precheck skips become failures under strict_state."""
    from galaxy.tool_util.workflow_state import roundtrip as rt_mod
    from galaxy.tool_util.workflow_state.precheck import (
        SkipWorkflowReason,
        WorkflowPrecheck,
    )

    def _fake_precheck(workflow, get_tool_info):
        return WorkflowPrecheck(
            can_process=False,
            skip_reasons=[SkipWorkflowReason.LEGACY_ENCODING],
            detail="legacy encoding (mock)",
        )

    monkeypatch.setattr(rt_mod, "precheck_native_workflow", _fake_precheck)

    wf = {"a_galaxy_workflow": "true", "format-version": "0.1", "steps": {}}

    result_lax = rt_mod.roundtrip_validate(wf, _NullInfo())
    assert result_lax.skipped_reason == SkipWorkflowReason.LEGACY_ENCODING
    assert result_lax.error is None

    result_strict = rt_mod.roundtrip_validate(wf, _NullInfo(), strict_state=True)
    assert result_strict.error and "strict-state" in result_strict.error
    assert result_strict.skipped_reason is None


def test_roundtrip_validate_strict_structure_clean_input_no_error():
    """Clean workflow with no tool steps should not trip strict-structure at stage 1."""
    from galaxy.tool_util.workflow_state.roundtrip import roundtrip_validate

    wf = {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "steps": {},
    }
    result = roundtrip_validate(wf, _NullInfo(), strict_structure=True)
    # Empty workflow passes stage 1; precheck skip (no tool steps is fine)
    # and proceeds to conversion — may or may not have diffs but structure passes.
    assert not result.structure_errors


def test_validate_single_library_strict_structure_populates_errors(tmp_path):
    """validate_single is a library entry point — direct callers must get strict enforcement."""
    from galaxy.tool_util.workflow_state.validate import validate_single

    path = _write_native_with_extra_key(tmp_path)
    report = validate_single(path, _NullInfo(), strict_structure=True)
    assert report.structure_errors
    assert report.results == []


def test_validate_single_library_strict_encoding_populates_errors(tmp_path):
    from galaxy.tool_util.workflow_state.validate import validate_single

    path = _write_native_string_tool_state(tmp_path)
    report = validate_single(path, _NullInfo(), strict_encoding=True)
    assert report.encoding_errors
    assert report.results == []


def test_lint_single_library_strict_structure_populates_errors(tmp_path):
    from galaxy.tool_util.workflow_state.lint_stateful import lint_single

    path = _write_native_with_extra_key(tmp_path)
    report = lint_single(path, _NullInfo(), strict_structure=True)
    assert report.structure_errors
    assert report.results == []


def test_run_roundtrip_validate_strict_structure_exit_2(tmp_path, monkeypatch):
    from galaxy.tool_util.workflow_state import roundtrip as rt_mod

    wf = {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "steps": {},
        "bogus_root_key": "surprise",
    }
    path = tmp_path / "extra_key.ga"
    path.write_text(json.dumps(wf))

    monkeypatch.setattr(rt_mod, "setup_tool_info", lambda options: _NullInfo())
    opts = RoundTripValidateOptions(workflow_path=str(path), strict_structure=True)
    # Matches sibling CLIs: strict-structure failures exit 2, not 1.
    assert rt_mod.run_roundtrip_validate(opts) == 2
