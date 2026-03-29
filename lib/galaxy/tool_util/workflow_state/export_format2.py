"""Export native Galaxy workflows to format2 with schema-aware state blocks.

gxformat2's to_format2() handles structural conversion (step ordering,
labels, connections). When given a state_encode_to_format2 callback via
ConversionOptions, it also converts tool_state to clean `state` dicts
using tool definitions. This module wires that callback with stale key
policy, strict mode, and per-step status tracking.
"""

import logging
import os
import sys
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Any,
)

from pydantic import (
    BaseModel,
    computed_field,
    Field,
)

from gxformat2.normalized import (
    ensure_native,
    NormalizedFormat2,
    NormalizedNativeWorkflow,
    to_format2,
)
from gxformat2.options import ConversionOptions

from ._cli_common import (
    setup_tool_info,
    ToolCacheOptions,
)
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
) -> ExportResult:
    """Export native workflow as format2 with schema-aware state blocks.

    Conversion happens inside to_format2() via the state_encode_to_format2
    callback. Steps where conversion fails keep their tool_state (best-effort)
    unless strict=True.
    """
    step_statuses: list[StepExportStatus] = []
    callback = _make_export_callback(get_tool_info, step_statuses, strict=strict, policy=policy)

    options = ConversionOptions(state_encode_to_format2=callback, compact=compact)
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


class ExportOptions(ToolCacheOptions):
    output: str | None = None
    json_output: bool = False
    compact: bool = False
    strict: bool = False
    allow: list[str] = []
    deny: list[str] = []


class ExportTreeOptions(ToolCacheOptions):
    output_dir: str = ""
    json_output: bool = False
    compact: bool = False
    strict: bool = False
    report_json: Optional[str] = None
    report_markdown: Optional[str] = None
    allow: List[str] = []
    deny: List[str] = []


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


def format_yaml(format2_dict: dict) -> str:
    try:
        import io

        from ruamel.yaml import YAML

        yaml = YAML()
        yaml.default_flow_style = False
        stream = io.StringIO()
        yaml.dump(format2_dict, stream)
        return stream.getvalue()
    except ImportError:
        import yaml as pyyaml

        return pyyaml.dump(format2_dict, default_flow_style=False, sort_keys=False)


def format_json(format2_dict: dict) -> str:
    import json

    return json.dumps(format2_dict, indent=4) + "\n"


# -- Entry point --


def run_export(options: ExportOptions) -> int:
    """Run single-file export pipeline. Returns exit code."""
    if os.path.isdir(options.workflow_path):
        print("Error: got directory, use gxwf-to-format2-stateful-tree for batch export", file=sys.stderr)
        return 2

    tool_info = setup_tool_info(options)

    try:
        workflow = ensure_native(options.workflow_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    try:
        policy = StaleKeyPolicy.for_export(options.allow, options.deny)
    except (InvalidCategoryError, ConflictingCategoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    precheck = precheck_native_workflow(workflow, tool_info)
    if not precheck.can_process:
        print(f"Skipped: {precheck.detail}", file=sys.stderr)
        return 0

    try:
        result = export_workflow_to_format2(
            workflow, tool_info, strict=options.strict, compact=options.compact, policy=policy
        )
    except ExportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Format output
    if options.json_output:
        output = format_json(result.format2_dict)
    else:
        output = format_yaml(result.format2_dict)

    # Write output
    if options.output:
        os.makedirs(os.path.dirname(os.path.abspath(options.output)), exist_ok=True)
        with open(options.output, "w") as f:
            f.write(output)
        print(format_summary(result), file=sys.stderr)
    else:
        # Summary to stderr, format2 to stdout
        print(format_summary(result), file=sys.stderr)
        sys.stdout.write(output)

    return 1 if result.failed_steps else 0


# -- Tree export --


@dataclass
class WorkflowExportResult:
    """Result of exporting one workflow in a tree run."""

    relative_path: str
    ok: bool
    steps_converted: int = 0
    steps_fallback: int = 0
    error: Optional[str] = None
    skipped_reason: Optional[str] = None


class ExportTreeReport(BaseModel):
    """Tree-level report for batch export."""

    root: str
    output_dir: str
    results: List[Dict[str, Any]] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Dict[str, int]:
        ok = sum(1 for r in self.results if r.get("ok"))
        fail = sum(1 for r in self.results if r.get("error"))
        skipped = sum(1 for r in self.results if r.get("skipped_reason"))
        return {"ok": ok, "fail": fail, "skipped": skipped}


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

    from ._tree_orchestrator import skip_workflow, TreeContext, run_tree
    from .workflow_tree import WorkflowInfo

    def process_one(info: WorkflowInfo, wf_dict: dict, get_tool_info):
        workflow = ensure_native(wf_dict)
        precheck = precheck_native_workflow(workflow, get_tool_info)
        if not precheck.can_process:
            skip_workflow(precheck.skip_reasons[0].value)

        result = export_workflow_to_format2(
            workflow,
            get_tool_info,
            strict=options.strict,
            compact=options.compact,
            policy=policy,
        )

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
            relative_path=info.relative_path,
            ok=not result.failed_steps,
            steps_converted=sum(1 for s in result.steps if s.converted),
            steps_fallback=len(result.failed_steps),
        )

    def aggregate(tree_result):
        results = []
        for outcome in tree_result.outcomes:
            if outcome.error:
                results.append({"path": outcome.info.relative_path, "ok": False, "error": outcome.error})
            elif outcome.skipped:
                results.append({"path": outcome.info.relative_path, "ok": False, "skipped_reason": outcome.skip_reason})
            elif outcome.result is not None:
                r = outcome.result
                results.append(
                    {
                        "path": r.relative_path,
                        "ok": r.ok,
                        "steps_converted": r.steps_converted,
                        "steps_fallback": r.steps_fallback,
                    }
                )
        return ExportTreeReport(root=tree_result.root, output_dir=options.output_dir, results=results)

    def format_text(report):
        lines = [f"Export: {report.root} → {report.output_dir}"]
        for r in report.results:
            path = r["path"]
            if r.get("error"):
                lines.append(f"  {path}: ERROR ({r['error']})")
            elif r.get("skipped_reason"):
                lines.append(f"  {path}: SKIPPED ({r['skipped_reason']})")
            elif r.get("ok"):
                lines.append(f"  {path}: OK ({r.get('steps_converted', 0)} steps)")
            else:
                lines.append(f"  {path}: PARTIAL ({r.get('steps_fallback', 0)} fallbacks)")
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
        format_markdown=lambda r: format_text(r),  # simple for now
        compute_exit_code=lambda r: 1 if r.summary["fail"] > 0 else 0,
        report_options=options,
    )
