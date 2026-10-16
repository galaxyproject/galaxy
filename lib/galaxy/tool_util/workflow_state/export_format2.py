"""Export native Galaxy workflows to format2 with schema-aware state blocks.

gxformat2's to_format2() handles structural conversion (step ordering,
labels, connections). When given a state_encode_to_format2 callback via
ConversionOptions, it also converts tool_state to clean `state` dicts
using tool definitions. This module wires that callback with stale key
policy, strict mode, and per-step status tracking.
"""

import io
import json
import logging
import os
import sys
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Any,
    Literal,
)

import yaml
from gxformat2.normalized import (
    ensure_native,
    NormalizedFormat2,
    NormalizedNativeWorkflow,
    to_format2,
)
from gxformat2.options import ConversionOptions
from gxformat2.yaml import ordered_load_path
from pydantic import (
    BaseModel,
    computed_field,
    Field,
)

from ._cli_common import (
    setup_tool_info,
    StrictOptions,
    ToolCacheOptions,
)
from ._encoding import (
    check_strict_structure as _check_strict_structure,
    validate_encoding_format2,
    validate_encoding_native,
)
from ._report_models import (
    TreeReportBase,
    WorkflowResultBase,
)
from ._report_output import emit_reports
from ._report_templates import make_markdown_renderer
from ._types import GetToolInfo
from .convert import (
    ConversionValidationFailure,
    convert_state_to_format2,
)
from .precheck import precheck_native_workflow
from .stale_keys import (
    classify_stale_keys,
    ConflictingCategoryError,
    InvalidCategoryError,
    StaleKeyPolicy,
)
from .validation_native import get_parsed_tool_for_native_step

log = logging.getLogger(__name__)


@dataclass
class StepExportStatus:
    step_id: str
    step_label: str | None = None
    tool_id: str | None = None
    converted: bool = False
    error: str | None = None


@dataclass
class ExportResult:
    format2: NormalizedFormat2
    steps: list[StepExportStatus] = field(default_factory=list)

    @property
    def format2_dict(self) -> dict:
        return self.format2.to_dict()

    @property
    def all_converted(self) -> bool:
        return all(s.converted for s in self.steps)

    @property
    def failed_steps(self) -> list[StepExportStatus]:
        return [s for s in self.steps if not s.converted]

    @property
    def summary(self) -> str:
        ok = sum(1 for s in self.steps if s.converted)
        fail = len(self.steps) - ok
        return f"{ok} converted, {fail} fell back to tool_state"


def export_workflow_to_format2(
    workflow: NormalizedNativeWorkflow,
    get_tool_info: GetToolInfo,
    strict: bool = False,
    compact: bool = False,
    policy: StaleKeyPolicy | None = None,
    strict_structure: bool = False,
) -> ExportResult:
    """Export native workflow as format2 with schema-aware state blocks.

    Conversion happens inside to_format2() via the state_encode_to_format2
    callback. Steps where conversion fails keep their tool_state (best-effort)
    unless strict=True. When strict_structure=True, gxformat2 validates the
    converted format2 output against the strict schema (extra='forbid').
    """
    step_statuses: list[StepExportStatus] = []
    callback = _make_export_callback(get_tool_info, step_statuses, strict=strict, policy=policy)

    options = ConversionOptions(
        state_encode_to_format2=callback,
        compact=compact,
        strict_structure=strict_structure,
    )
    format2_model = to_format2(workflow, options=options)

    return ExportResult(format2=format2_model, steps=step_statuses)


def _make_export_callback(
    get_tool_info: GetToolInfo,
    step_statuses: list[StepExportStatus],
    strict: bool = False,
    policy: StaleKeyPolicy | None = None,
):
    """Build a state_encode_to_format2 callback with policy checking and status tracking."""

    def _convert(native_step: dict) -> dict[str, Any] | None:
        tool_id = native_step.get("tool_id")
        step_label = native_step.get("label") or str(native_step.get("id", "?"))

        if not tool_id:
            return None

        # Check stale key policy before conversion
        if policy and policy.denied:
            try:
                parsed_tool = get_parsed_tool_for_native_step(native_step, get_tool_info)
                if parsed_tool:
                    stale = classify_stale_keys(native_step, parsed_tool)
                    denied, _ = policy.filter(stale)
                    if denied:
                        cats = ", ".join(sorted({sk.category.value for sk in denied}))
                        step_statuses.append(
                            StepExportStatus(
                                step_id=step_label,
                                step_label=native_step.get("label"),
                                tool_id=tool_id,
                                converted=False,
                                error=f"Denied stale key categories: {cats}",
                            )
                        )
                        return None
            except Exception:
                pass  # classification failure shouldn't block conversion

        try:
            f2_state = convert_state_to_format2(native_step, get_tool_info)
            step_statuses.append(
                StepExportStatus(
                    step_id=step_label,
                    step_label=native_step.get("label"),
                    tool_id=tool_id,
                    converted=True,
                )
            )
            return f2_state.state
        except ConversionValidationFailure as e:
            error_msg = str(e)
            step_statuses.append(
                StepExportStatus(
                    step_id=step_label,
                    step_label=native_step.get("label"),
                    tool_id=tool_id,
                    converted=False,
                    error=error_msg,
                )
            )
            if strict:
                raise ExportError(f"Step {step_label}: {error_msg}") from e
            log.debug("Step %s: conversion failed, keeping tool_state: %s", step_label, error_msg)
            return None
        except Exception as e:
            error_msg = str(e)
            step_statuses.append(
                StepExportStatus(
                    step_id=step_label,
                    step_label=native_step.get("label"),
                    tool_id=tool_id,
                    converted=False,
                    error=error_msg,
                )
            )
            if strict:
                raise ExportError(f"Step {step_label}: {error_msg}") from e
            log.debug("Step %s: conversion failed, keeping tool_state: %s", step_label, error_msg)
            return None

    return _convert


class ExportError(Exception):
    pass


# -- Options model --


class ExportOptions(ToolCacheOptions, StrictOptions):
    output: str | None = None
    json_output: bool = False
    compact: bool = False
    report_json: str | None = None
    report_markdown: str | None = None
    allow: list[str] = []
    deny: list[str] = []


class ExportTreeOptions(ToolCacheOptions, StrictOptions):
    output_dir: str = ""
    json_output: bool = False
    compact: bool = False
    report_json: str | None = None
    report_markdown: str | None = None
    allow: list[str] = []
    deny: list[str] = []


# -- Formatters --


def format_summary(result: ExportResult) -> str:
    lines = []
    for s in result.steps:
        tool_label = s.tool_id or "?"
        if s.converted:
            lines.append(f"Step {s.step_id}: {tool_label} ... OK")
        else:
            lines.append(f"Step {s.step_id}: {tool_label} ... FALLBACK ({s.error})")
    lines.append("---")
    lines.append(result.summary)
    return "\n".join(lines)


_YAML_RESOLVER = yaml.resolver.Resolver()


def _scalar_needs_quoting(value: str) -> bool:
    """True if emitting ``value`` unquoted would let a reader re-read it as a non-string.

    Uses PyYAML's (YAML 1.1) resolver, the most permissive, so quoted output is safe for
    any 1.1 or 1.2 consumer. Covers the reserved words (yes/no/on/off/true/false/null) and
    numeric-looking strings that ruamel's emitter otherwise writes bare.
    """
    return _YAML_RESOLVER.resolve(yaml.ScalarNode, value, (True, False)) != "tag:yaml.org,2002:str"


def _represent_portable_str(representer, data):
    style = "'" if _scalar_needs_quoting(data) else None
    return representer.represent_scalar("tag:yaml.org,2002:str", data, style=style)


def format_yaml(format2_dict: dict) -> str:
    try:
        from ruamel.yaml import YAML

        yaml_dumper = YAML()
        yaml_dumper.default_flow_style = False
        yaml_dumper.representer.add_representer(str, _represent_portable_str)
        stream = io.StringIO()
        yaml_dumper.dump(format2_dict, stream)
        return stream.getvalue()
    except ImportError:
        return yaml.dump(format2_dict, default_flow_style=False, sort_keys=False)


def format_json(format2_dict: dict) -> str:
    return json.dumps(format2_dict, indent=4) + "\n"


# -- Library-level entry point --


@dataclass
class ExportSingleResult:
    """Bundle of export report + converted format2 dict."""

    report: "SingleExportReport"
    format2_dict: dict
    export_result: ExportResult


def export_single(
    workflow_path: str,
    tool_info: GetToolInfo,
    strict: bool = False,
    compact: bool = False,
    policy: StaleKeyPolicy | None = None,
) -> ExportSingleResult | None:
    """Export a single native workflow to format2, return structured report.

    Library-level entry point with no CLI dependencies.
    Returns None if the workflow is skipped (legacy encoding).
    """
    workflow = ensure_native(workflow_path)
    workflow_name = os.path.basename(workflow_path)

    precheck = precheck_native_workflow(workflow, tool_info)
    if not precheck.can_process:
        return None

    result = export_workflow_to_format2(workflow, tool_info, strict=strict, compact=compact, policy=policy)

    converted = sum(1 for s in result.steps if s.converted)
    fallback = len(result.failed_steps)
    report = SingleExportReport(
        workflow=workflow_name,
        ok=not result.failed_steps,
        steps_converted=converted,
        steps_fallback=fallback,
    )
    return ExportSingleResult(report=report, format2_dict=result.format2_dict, export_result=result)


# -- CLI entry point --


def run_export(options: ExportOptions) -> int:
    """Run single-file export pipeline. Returns exit code."""
    if os.path.isdir(options.workflow_path):
        print("Error: got directory, use 'gxwf convert-tree --to format2' for batch export", file=sys.stderr)
        return 2

    tool_info = setup_tool_info(options)

    try:
        workflow = ensure_native(options.workflow_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if options.strict_encoding or options.strict_structure:
        raw_dict = ordered_load_path(options.workflow_path)
        if options.strict_encoding:
            enc_errors = validate_encoding_native(raw_dict)
            if enc_errors:
                print("Error: strict-encoding (input):", file=sys.stderr)
                for error in enc_errors:
                    print(f"  {error}", file=sys.stderr)
                return 2
        if options.strict_structure:
            struct_errors = _check_strict_structure(raw_dict)
            if struct_errors:
                print("Error: strict-structure (input):", file=sys.stderr)
                for error in struct_errors:
                    print(f"  {error}", file=sys.stderr)
                return 2

    try:
        policy = StaleKeyPolicy.for_export(options.allow, options.deny)
    except (InvalidCategoryError, ConflictingCategoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    precheck = precheck_native_workflow(workflow, tool_info)
    if not precheck.can_process:
        print(f"Skipped: {precheck.detail}", file=sys.stderr)
        if options.strict_state:
            print(f"Error: strict-state: cannot process: {precheck.detail}", file=sys.stderr)
            return 2
        return 0

    try:
        result = export_workflow_to_format2(
            workflow,
            tool_info,
            strict=options.strict_state,
            compact=options.compact,
            policy=policy,
            strict_structure=options.strict_structure,
        )
    except ExportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if options.strict_encoding:
        enc_errors = validate_encoding_format2(result.format2_dict)
        if enc_errors:
            print("Error: strict-encoding (output):", file=sys.stderr)
            for error in enc_errors:
                print(f"  {error}", file=sys.stderr)
            return 2

    # Format output
    if options.json_output:
        output = format_json(result.format2_dict)
    else:
        output = format_yaml(result.format2_dict)

    # Write converted workflow
    if options.output:
        os.makedirs(os.path.dirname(os.path.abspath(options.output)), exist_ok=True)
        with open(options.output, "w") as f:
            f.write(output)
    else:
        sys.stdout.write(output)

    # Emit report
    converted = sum(1 for s in result.steps if s.converted)
    fallback = len(result.failed_steps)
    json_data = SingleExportReport(
        workflow=options.workflow_path,
        ok=not result.failed_steps,
        steps_converted=converted,
        steps_fallback=fallback,
    )
    tree_report = wrap_single_export(options.workflow_path, json_data)
    text_content = format_summary(result)
    summary_text = result.summary

    emit_reports(
        options=options,
        json_data=json_data,
        markdown_formatter=make_markdown_renderer("export_tree.md.j2"),
        markdown_report=tree_report,
        text_content=text_content,
        stderr_summary=summary_text,
    )

    return 1 if result.failed_steps else 0


# -- Report models --


class WorkflowExportResult(WorkflowResultBase):
    """Per-workflow export result."""

    # free-form skip reasons beyond SkipWorkflowReason; base field is the enum type
    skipped_reason: str | None = None  # type: ignore[assignment]
    ok: bool = False
    steps_converted: int = 0
    steps_fallback: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status(self) -> Literal["ok", "partial", "error", "skipped"]:
        # Precedence: error → skipped → ok → partial. ``ok=True`` with
        # ``steps_fallback>0`` stays "ok" (fallback count is a detail,
        # not a state) — matches the original formatter's branch order.
        if self.error:
            return "error"
        if self.skipped_reason:
            return "skipped"
        if self.ok:
            return "ok"
        return "partial"


class SingleExportReport(BaseModel):
    """JSON shape for single-file export."""

    workflow: str
    ok: bool = False
    steps_converted: int = 0
    steps_fallback: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> dict[str, int]:
        return {"converted": self.steps_converted, "fallback": self.steps_fallback}


class ExportTreeReport(TreeReportBase):
    """Tree-level report for batch export."""

    output_dir: str
    results: list[WorkflowExportResult] = Field(default_factory=list, serialization_alias="workflows")

    def _workflow_results(self) -> list:
        return self.results

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> dict[str, int]:
        ok = sum(1 for r in self.results if r.ok)
        fail = sum(1 for r in self.results if r.error)
        skipped = sum(1 for r in self.results if r.skipped_reason)
        return {"ok": ok, "fail": fail, "skipped": skipped}


def wrap_single_export(workflow_path: str, report: SingleExportReport) -> ExportTreeReport:
    """Wrap single-file export result into a tree report for Markdown rendering."""
    return ExportTreeReport(
        root=workflow_path,
        output_dir="",
        results=[
            WorkflowExportResult(
                path=workflow_path,
                relative_path=os.path.basename(workflow_path),
                category="",
                ok=report.ok,
                steps_converted=report.steps_converted,
                steps_fallback=report.steps_fallback,
            )
        ],
    )


def run_export_tree(options: ExportTreeOptions) -> int:
    """Run tree export pipeline. Returns exit code."""
    if not os.path.isdir(options.workflow_path):
        print("Error: expected directory, got file", file=sys.stderr)
        return 2

    if not options.output_dir:
        print("Error: --output-dir is required for tree export", file=sys.stderr)
        return 2

    tool_info = setup_tool_info(options)

    try:
        policy = StaleKeyPolicy.for_export(options.allow, options.deny)
    except (InvalidCategoryError, ConflictingCategoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    from ._tree_orchestrator import (
        run_tree,
        skip_workflow,
        TreeContext,
    )
    from .workflow_tree import WorkflowInfo

    def process_one(info: WorkflowInfo, wf_dict: dict, get_tool_info):
        if options.strict_encoding:
            enc_errors = validate_encoding_native(wf_dict)
            if enc_errors:
                raise RuntimeError("strict-encoding (input): " + "; ".join(enc_errors))
        if options.strict_structure:
            struct_errors = _check_strict_structure(wf_dict)
            if struct_errors:
                raise RuntimeError("strict-structure (input): " + "; ".join(struct_errors))
        workflow = ensure_native(wf_dict)
        precheck = precheck_native_workflow(workflow, get_tool_info)
        if not precheck.can_process:
            if options.strict_state:
                raise RuntimeError(f"strict-state: cannot process: {precheck.detail}")
            skip_workflow(precheck.skip_reasons[0].value)

        result = export_workflow_to_format2(
            workflow,
            get_tool_info,
            strict=options.strict_state,
            compact=options.compact,
            policy=policy,
            strict_structure=options.strict_structure,
        )

        if options.strict_encoding:
            enc_errors = validate_encoding_format2(result.format2_dict)
            if enc_errors:
                raise RuntimeError("strict-encoding (output): " + "; ".join(enc_errors))

        ext = ".json" if options.json_output else ".gxwf.yml"
        stem = os.path.splitext(info.relative_path)[0]
        out_path = os.path.join(options.output_dir, stem + ext)
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

        if options.json_output:
            output = format_json(result.format2_dict)
        else:
            output = format_yaml(result.format2_dict)

        with open(out_path, "w") as f:
            f.write(output)

        return WorkflowExportResult(
            path=info.path,
            relative_path=info.relative_path,
            category=info.category,
            ok=not result.failed_steps,
            steps_converted=sum(1 for s in result.steps if s.converted),
            steps_fallback=len(result.failed_steps),
        )

    def aggregate(tree_result):
        results = []
        for outcome in tree_result.outcomes:
            info = outcome.info
            if outcome.error:
                results.append(
                    WorkflowExportResult(
                        path=info.path,
                        relative_path=info.relative_path,
                        category=info.category,
                        error=outcome.error,
                    )
                )
            elif outcome.skipped:
                results.append(
                    WorkflowExportResult(
                        path=info.path,
                        relative_path=info.relative_path,
                        category=info.category,
                        skipped_reason=outcome.skip_reason,
                    )
                )
            elif outcome.result is not None:
                results.append(outcome.result)
        return ExportTreeReport(root=tree_result.root, output_dir=options.output_dir, results=results)

    def format_text(report):
        lines = [f"Export: {report.root} → {report.output_dir}"]
        for r in report.results:
            if r.error:
                lines.append(f"  {r.relative_path}: ERROR ({r.error})")
            elif r.skipped_reason:
                lines.append(f"  {r.relative_path}: SKIPPED ({r.skipped_reason})")
            elif r.ok:
                lines.append(f"  {r.relative_path}: OK ({r.steps_converted} steps)")
            else:
                lines.append(f"  {r.relative_path}: PARTIAL ({r.steps_fallback} fallbacks)")
        s = report.summary
        lines.append(f"Summary: {s['ok']} OK, {s['fail']} errors, {s['skipped']} skipped")
        return "\n".join(lines)

    ctx = TreeContext(root=options.workflow_path, tool_info=tool_info, include_format2=False)
    return run_tree(
        ctx=ctx,
        process_one=process_one,
        aggregate=aggregate,
        format_text=format_text,
        format_summary=lambda r: f"Export: {r.summary['ok']} OK, {r.summary['fail']} errors",
        format_markdown=make_markdown_renderer("export_tree.md.j2"),
        compute_exit_code=lambda r: 1 if r.summary["fail"] > 0 else 0,
        report_options=options,
    )
