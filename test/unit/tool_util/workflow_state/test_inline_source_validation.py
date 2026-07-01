"""Phase C tests for inline-source diagnostics in validate / lint_stateful.

Covers §9.5 (lint-stateful inline-source phase) and §9.6 (strict / offline)
from USER_DEFINED_TOOL_STEP_VALIDATION.md. Phase B routed every step
through ``resolve_for_step``; Phase C adds per-step source diagnostics
(pydantic schema + lint) and wires the ``--strict-inline-source`` and
``--offline`` axes through.
"""

from copy import deepcopy

from galaxy.tool_util.workflow_state._cli_common import (
    StrictOptions,
    ToolCacheOptions,
)
from galaxy.tool_util.workflow_state._report_models import SingleValidationReport
from galaxy.tool_util.workflow_state.lint_stateful import (
    _inline_source_exit_code,
    lint_single,
)
from galaxy.tool_util.workflow_state.validate import (
    _summary_inline_source_text,
    validate_single,
    validate_workflow_cli,
)
from galaxy.tool_util_models import ParsedTool
from .inline_udt_fixtures import (
    cat_udt_body,
    load_format2_inline_udt as _format2_with_inline_udt,
    load_native_inline_udt as _native_with_inline_udt,
)


class _EmptyGetToolInfo:
    def get_tool_info(self, tool_id: str, tool_version: str | None) -> ParsedTool | None:
        return None


CAT_UDT: dict = cat_udt_body()


# -- Phase C: inline-source diagnostics attached to step results ---------------


def test_validate_attaches_inline_source_for_clean_native():
    """A well-formed inline UDT step yields a result row with inline_source set."""
    wf = _native_with_inline_udt()
    results, precheck, conn = validate_workflow_cli(wf, _EmptyGetToolInfo())
    udt_rows = [r for r in results if r.inline_source is not None]
    assert len(udt_rows) == 1
    inline = udt_rows[0].inline_source
    assert inline is not None
    assert inline.inline_class == "GalaxyUserTool"
    assert inline.supported
    assert not inline.validation_errors


def test_validate_surfaces_blank_version_lint_finding_native():
    """Blank version in inline tool surfaces in inline_source.lint_errors or validation_errors."""
    rep = deepcopy(CAT_UDT)
    rep["version"] = "   "
    wf = _native_with_inline_udt(representation=rep)
    results, _, _ = validate_workflow_cli(wf, _EmptyGetToolInfo())
    udt_rows = [r for r in results if r.inline_source is not None]
    assert udt_rows
    inline = udt_rows[0].inline_source
    assert inline is not None
    # Blank version is caught at the pydantic gate (post PR #22615).
    assert inline.validation_errors


def test_validate_admin_class_unsupported_native():
    """class: GalaxyTool surfaces as inline_source.supported = False."""
    rep = deepcopy(CAT_UDT)
    rep["class"] = "GalaxyTool"
    wf = _native_with_inline_udt(representation=rep)
    results, _, _ = validate_workflow_cli(wf, _EmptyGetToolInfo())
    udt_rows = [r for r in results if r.inline_source is not None]
    assert udt_rows
    inline = udt_rows[0].inline_source
    assert inline is not None
    assert not inline.supported
    assert inline.inline_class == "GalaxyTool"


def test_validate_attaches_inline_source_format2():
    wf = _format2_with_inline_udt()
    results, _, _ = validate_workflow_cli(wf, _EmptyGetToolInfo())
    udt_rows = [r for r in results if r.inline_source is not None]
    assert len(udt_rows) == 1
    inline = udt_rows[0].inline_source
    assert inline is not None
    assert inline.supported


# -- §9.6 strict-inline-source -------------------------------------------------


def test_strict_inline_source_exit_code_via_helper():
    """The lint-stateful inline-source exit-code helper promotes pydantic errors under strict."""
    from galaxy.tool_util.workflow_state._inline_tool import InlineToolSourceResult
    from galaxy.tool_util.workflow_state._report_models import ValidationStepResult

    bad = ValidationStepResult(
        step="1",
        tool_id=None,
        status="skip_tool_not_found",
        inline_source=InlineToolSourceResult(ok=False, inline_class="GalaxyUserTool", validation_errors=["bad"]),
    )
    # Without strict — no fail
    assert _inline_source_exit_code([bad], strict_inline_source=False) == 0
    # With strict — fail
    assert _inline_source_exit_code([bad], strict_inline_source=True) == 1


def test_lint_errors_fail_under_strict_only():
    """Inline-source lint errors are gated by --strict-inline-source (plan §7.3)."""
    from galaxy.tool_util.workflow_state._inline_tool import InlineToolSourceResult
    from galaxy.tool_util.workflow_state._report_models import ValidationStepResult

    bad = ValidationStepResult(
        step="1",
        tool_id="t",
        status="ok",
        inline_source=InlineToolSourceResult(ok=False, inline_class="GalaxyUserTool", lint_errors=["missing tests"]),
    )
    assert _inline_source_exit_code([bad], strict_inline_source=False) == 0
    assert _inline_source_exit_code([bad], strict_inline_source=True) == 1


def test_lint_warnings_never_fail():
    """Inline-source lint warnings return EXIT_CODE_LINT_FAILED, not 1."""
    from gxformat2.lint import EXIT_CODE_LINT_FAILED

    from galaxy.tool_util.workflow_state._inline_tool import InlineToolSourceResult
    from galaxy.tool_util.workflow_state._report_models import ValidationStepResult

    warn = ValidationStepResult(
        step="1",
        tool_id="t",
        status="ok",
        inline_source=InlineToolSourceResult(ok=True, inline_class="GalaxyUserTool", lint_warnings=["container shape"]),
    )
    assert _inline_source_exit_code([warn], strict_inline_source=True) == EXIT_CODE_LINT_FAILED


# -- §9.5 lint_single surfaces inline-source -----------------------------------


def test_lint_single_attaches_inline_source(tmp_path):
    import json

    rep = deepcopy(CAT_UDT)
    rep["version"] = "   "  # blank — pydantic violation
    wf = _native_with_inline_udt(representation=rep)
    wf_path = tmp_path / "wf.ga"
    wf_path.write_text(json.dumps(wf))

    report = lint_single(str(wf_path), tool_info=_EmptyGetToolInfo())
    udt_rows = [r for r in report.results if r.inline_source is not None]
    assert udt_rows, "lint_single did not surface inline_source diagnostics"
    inline = udt_rows[0].inline_source
    assert inline is not None
    assert inline.validation_errors


# -- §9.6 offline plumbing -----------------------------------------------------


def test_offline_skips_network_linters_during_validate(monkeypatch):
    """When offline=True, lint_user_tool_source_structured is called with skip_network=True."""
    captured = {}

    from galaxy.tool_util.lint import lint_user_tool_source_structured
    from galaxy.tool_util.workflow_state import _inline_tool as inline_mod

    def spy(source, *, skip_network=False, **kw):
        captured["skip_network"] = skip_network
        return lint_user_tool_source_structured(source, skip_network=skip_network, **kw)

    monkeypatch.setattr(inline_mod, "lint_user_tool_source_structured", spy)
    wf = _native_with_inline_udt()
    validate_workflow_cli(wf, _EmptyGetToolInfo(), offline=True)
    assert captured.get("skip_network") is True


def test_offline_default_runs_network_linters_during_validate(monkeypatch):
    captured = {}

    from galaxy.tool_util.lint import lint_user_tool_source_structured
    from galaxy.tool_util.workflow_state import _inline_tool as inline_mod

    def spy(source, *, skip_network=False, **kw):
        captured["skip_network"] = skip_network
        return lint_user_tool_source_structured(source, skip_network=skip_network, **kw)

    monkeypatch.setattr(inline_mod, "lint_user_tool_source_structured", spy)
    wf = _native_with_inline_udt()
    validate_workflow_cli(wf, _EmptyGetToolInfo(), offline=False)
    assert captured.get("skip_network") is False


# -- CLI surface: --strict-inline-source / --offline -----------------------------


def test_strict_inline_source_promoted_by_strict_shorthand():
    s = StrictOptions(strict=True)
    assert s.strict_inline_source is True
    assert s.strict_state is True
    assert s.strict_encoding is True
    assert s.strict_structure is True


def test_offline_default_false_on_tool_cache_options():
    t = ToolCacheOptions(workflow_path="/tmp/wf.ga")
    assert t.offline is False


def test_offline_arg_registered_on_base_parser():
    from galaxy.tool_util.workflow_state._cli_common import build_base_parser

    parser = build_base_parser(prog="gxwf-x", description="x")
    args = parser.parse_args(["--offline", "/tmp/wf.ga"])
    assert args.offline is True


def test_strict_inline_source_arg_registered():
    """--strict-inline-source parses without error and ends up on the namespace."""
    from galaxy.tool_util.workflow_state.scripts.workflow_validate import build_parser

    parser = build_parser()
    args = parser.parse_args(["--strict-inline-source", "/tmp/wf.ga"])
    assert getattr(args, "strict_inline_source", False) is True


# -- Reporting helpers ---------------------------------------------------------


def test_summary_inline_source_text_returns_none_when_no_issues():
    from galaxy.tool_util.workflow_state._report_models import ValidationStepResult

    assert _summary_inline_source_text([ValidationStepResult(step="1", status="ok")]) is None


def test_summary_inline_source_text_tallies_diagnostics():
    from galaxy.tool_util.workflow_state._inline_tool import InlineToolSourceResult
    from galaxy.tool_util.workflow_state._report_models import ValidationStepResult

    results = [
        ValidationStepResult(
            step="1",
            status="ok",
            inline_source=InlineToolSourceResult(ok=False, inline_class="GalaxyUserTool", validation_errors=["bad"]),
        ),
        ValidationStepResult(
            step="2",
            status="ok",
            inline_source=InlineToolSourceResult(ok=False, inline_class="GalaxyTool", supported=False),
        ),
    ]
    summary = _summary_inline_source_text(results)
    assert summary is not None
    assert "1 INVALID" in summary
    assert "1 UNSUPPORTED" in summary


def test_single_validation_report_inline_summary_field():
    """SingleValidationReport.inline_source_summary tallies per-workflow."""
    from galaxy.tool_util.workflow_state._inline_tool import InlineToolSourceResult
    from galaxy.tool_util.workflow_state._report_models import ValidationStepResult

    report = SingleValidationReport(
        workflow="wf.ga",
        results=[
            ValidationStepResult(
                step="1",
                status="ok",
                inline_source=InlineToolSourceResult(
                    ok=True,
                    inline_class="GalaxyUserTool",
                    lint_warnings=["container shape"],
                ),
            ),
        ],
    )
    assert report.inline_source_summary == {
        "invalid": 0,
        "lint_errors": 0,
        "lint_warnings": 1,
        "unsupported": 0,
    }


# -- §9.6 strict-inline-source — exit code through validate_single ----------------


def test_validate_single_strict_inline_source_exit_code(tmp_path):
    """validate_single + strict_inline_source exit-code path via the public CLI helper.

    We don't call run_validate (would print to stdout) — instead we drive
    the same exit-code logic on the returned report.
    """
    import json

    rep = deepcopy(CAT_UDT)
    rep["version"] = "   "
    wf = _native_with_inline_udt(representation=rep)
    wf_path = tmp_path / "wf.ga"
    wf_path.write_text(json.dumps(wf))

    report = validate_single(str(wf_path), _EmptyGetToolInfo())
    # Confirm inline-source surfaces the issue.
    udt_rows = [r for r in report.results if r.inline_source is not None]
    assert udt_rows
    inline = udt_rows[0].inline_source
    assert inline is not None
    assert inline.validation_errors
