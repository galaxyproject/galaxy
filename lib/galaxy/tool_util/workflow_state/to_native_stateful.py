"""Convert format2 workflows to native Galaxy format with schema-aware state encoding.

gxformat2's to_native() handles structural conversion (steps, connections,
tool_state). When given a state_encode_to_native callback via ConversionOptions,
it produces correctly-typed native tool_state using tool definitions — reversing
format2 conveniences like list→comma-string for multiple selects. This module
wires that callback with per-step tracking and strict mode.
"""

import json
import logging
import os
import sys
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Dict,
    List,
    Literal,
    Optional,
)

from gxformat2.normalized import (
    NormalizedNativeWorkflow,
    to_native,
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
from ._report_models import (
    TreeReportBase,
    WorkflowResultBase,
)
from ._encoding import (
    check_strict_structure as _check_strict_structure,
    validate_encoding_format2,
    validate_encoding_native,
)
from ._report_output import emit_reports
from ._report_templates import make_markdown_renderer
from ._types import GetToolInfo
from .convert import make_encode_tool_state

log = logging.getLogger(__name__)


@dataclass
class StepEncodeStatus:
    step_id: str
    step_label: Optional[str] = None
    tool_id: Optional[str] = None
    encoded: bool = False
    error: Optional[str] = None


@dataclass
class ToNativeResult:
    native: NormalizedNativeWorkflow
    steps: List[StepEncodeStatus] = field(default_factory=list)

    @property
    def native_dict(self) -> dict:
        return self.native.to_dict()

    @property
    def all_encoded(self) -> bool:
        return all(s.encoded for s in self.steps)

    @property
    def failed_steps(self) -> List[StepEncodeStatus]:
        return [s for s in self.steps if not s.encoded]

    @property
    def summary(self) -> str:
        ok = sum(1 for s in self.steps if s.encoded)
        fail = len(self.steps) - ok
        return f"{ok} schema-encoded, {fail} fell back to default"


def convert_to_native_stateful(
    workflow_path: str,
    get_tool_info: GetToolInfo,
    strict: bool = False,
    strict_structure: bool = False,
) -> ToNativeResult:
    """Convert format2 workflow to native with schema-aware tool_state encoding.

    Requires format2 input — native .ga files are rejected because
    ensure_native() would short-circuit and skip the encoder callback.

    Conversion happens inside to_native() via the state_encode_to_native
    callback. Steps where encoding fails fall back to gxformat2's default
    passthrough (clean dict, no json.dumps) unless strict=True. When
    strict_structure=True, gxformat2 validates both the format2 input and
    the native output against extra='forbid' strict schema models.
    """
    workflow_dict = ordered_load_path(workflow_path)
    if isinstance(workflow_dict, dict) and workflow_dict.get("a_galaxy_workflow") == "true":
        raise EncodeError(
            f"{workflow_path} is already native format. "
            "Use gxwf-to-format2-stateful to convert native→format2, "
            "or gxwf-roundtrip-validate for native→format2→native validation."
        )

    step_statuses: List[StepEncodeStatus] = []
    callback = _make_encode_callback(get_tool_info, step_statuses, strict=strict)

    options = ConversionOptions(
        state_encode_to_native=callback,
        workflow_directory=os.path.dirname(os.path.abspath(workflow_path)),
        strict_structure=strict_structure,
    )
    native = to_native(workflow_dict, options=options)

    return ToNativeResult(native=native, steps=step_statuses)


def _make_encode_callback(
    get_tool_info: GetToolInfo,
    step_statuses: List[StepEncodeStatus],
    strict: bool = False,
):
    """Build a state_encode_to_native callback with status tracking."""
    base_encoder = make_encode_tool_state(get_tool_info)
    step_counter = [0]

    def _encode(step: dict, state: dict):
        step_counter[0] += 1
        tool_id = step.get("tool_id")
        step_id = str(step_counter[0])

        try:
            result = base_encoder(step, state)
            if result is not None:
                step_statuses.append(StepEncodeStatus(step_id=step_id, tool_id=tool_id, encoded=True))
                return result
            else:
                error = "no tool definition available"
                step_statuses.append(StepEncodeStatus(step_id=step_id, tool_id=tool_id, encoded=False, error=error))
                if strict:
                    raise EncodeError(f"Step {step_id} ({tool_id}): {error}")
                return None
        except EncodeError:
            raise
        except Exception as e:
            error_msg = str(e)
            step_statuses.append(StepEncodeStatus(step_id=step_id, tool_id=tool_id, encoded=False, error=error_msg))
            if strict:
                raise EncodeError(f"Step {step_id} ({tool_id}): {error_msg}") from e
            log.debug("Step %s (%s): encoding failed, using default: %s", step_id, tool_id, error_msg)
            return None

    return _encode


class EncodeError(Exception):
    pass


# -- Options model --


class ToNativeOptions(ToolCacheOptions, StrictOptions):
    output: Optional[str] = None
    report_json: Optional[str] = None
    report_markdown: Optional[str] = None


class ToNativeTreeOptions(ToolCacheOptions, StrictOptions):
    output_dir: str = ""
    report_json: Optional[str] = None
    report_markdown: Optional[str] = None


class WorkflowToNativeResult(WorkflowResultBase):
    """Per-workflow format2→native conversion result."""

    skipped_reason: Optional[str] = None  # override: free-form skip reasons beyond SkipWorkflowReason
    ok: bool = False
    steps_encoded: int = 0
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


class SingleToNativeReport(BaseModel):
    """JSON shape for single-file format2→native conversion."""

    workflow: str
    ok: bool = False
    steps_encoded: int = 0
    steps_fallback: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Dict[str, int]:
        return {"encoded": self.steps_encoded, "fallback": self.steps_fallback}


class ToNativeTreeReport(TreeReportBase):
    """Tree-level report for batch format2→native conversion."""

    output_dir: str
    results: List[WorkflowToNativeResult] = Field(default_factory=list, serialization_alias="workflows")

    def _workflow_results(self) -> list:
        return self.results

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Dict[str, int]:
        ok = sum(1 for r in self.results if r.ok)
        fail = sum(1 for r in self.results if r.error)
        skipped = sum(1 for r in self.results if r.skipped_reason)
        return {"ok": ok, "fail": fail, "skipped": skipped}


def wrap_single_to_native(workflow_path: str, report: SingleToNativeReport) -> ToNativeTreeReport:
    """Wrap single-file result into a tree report for Markdown rendering."""
    return ToNativeTreeReport(
        root=workflow_path,
        output_dir="",
        results=[
            WorkflowToNativeResult(
                path=workflow_path,
                relative_path=os.path.basename(workflow_path),
                category="",
                ok=report.ok,
                steps_encoded=report.steps_encoded,
                steps_fallback=report.steps_fallback,
            )
        ],
    )


# -- Formatters --


def format_summary(result: ToNativeResult) -> str:
    lines = []
    for s in result.steps:
        tool_label = s.tool_id or "?"
        if s.encoded:
            lines.append(f"Step {s.step_id}: {tool_label} ... OK")
        else:
            lines.append(f"Step {s.step_id}: {tool_label} ... FALLBACK ({s.error})")
    lines.append("---")
    lines.append(result.summary)
    return "\n".join(lines)


def format_native_json(native_dict: dict) -> str:
    return json.dumps(native_dict, indent=4) + "\n"


# -- Entry point --


def run_to_native(options: ToNativeOptions) -> int:
    """Run single-file format2→native conversion. Returns exit code."""
    if os.path.isdir(options.workflow_path):
        print("Error: got directory, use gxwf-to-native-stateful-tree for batch conversion", file=sys.stderr)
        return 2

    tool_info = setup_tool_info(options)

    if options.strict_encoding or options.strict_structure:
        try:
            raw_dict = ordered_load_path(options.workflow_path)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        if options.strict_encoding:
            enc_errors = validate_encoding_format2(raw_dict)
            if enc_errors:
                print("Error: strict-encoding (input):", file=sys.stderr)
                for e_msg in enc_errors:
                    print(f"  {e_msg}", file=sys.stderr)
                return 2
        if options.strict_structure:
            struct_errors = _check_strict_structure(raw_dict)
            if struct_errors:
                print("Error: strict-structure (input):", file=sys.stderr)
                for e_msg in struct_errors:
                    print(f"  {e_msg}", file=sys.stderr)
                return 2

    try:
        result = convert_to_native_stateful(
            options.workflow_path,
            tool_info,
            strict=options.strict_state,
            strict_structure=options.strict_structure,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if options.strict_encoding:
        enc_errors = validate_encoding_native(result.native_dict)
        if enc_errors:
            print("Error: strict-encoding (output):", file=sys.stderr)
            for e_msg in enc_errors:
                print(f"  {e_msg}", file=sys.stderr)
            return 2

    output = format_native_json(result.native_dict)

    # Write converted workflow
    if options.output:
        os.makedirs(os.path.dirname(os.path.abspath(options.output)), exist_ok=True)
        with open(options.output, "w") as f:
            f.write(output)
    else:
        sys.stdout.write(output)

    # Emit report
    encoded = sum(1 for s in result.steps if s.encoded)
    fallback = len(result.failed_steps)
    json_data = SingleToNativeReport(
        workflow=options.workflow_path,
        ok=not result.failed_steps,
        steps_encoded=encoded,
        steps_fallback=fallback,
    )
    tree_report = wrap_single_to_native(options.workflow_path, json_data)
    text_content = format_summary(result)
    summary_text = result.summary

    emit_reports(
        options=options,
        json_data=json_data,
        markdown_formatter=make_markdown_renderer("to_native_tree.md.j2"),
        markdown_report=tree_report,
        text_content=text_content,
        stderr_summary=summary_text,
    )

    return 1 if result.failed_steps else 0


def _convert_dict_to_native(
    wf_dict: dict,
    get_tool_info: GetToolInfo,
    strict: bool = False,
    workflow_dir: str = "",
    strict_structure: bool = False,
) -> ToNativeResult:
    """Convert a format2 dict to native (for tree mode)."""
    if isinstance(wf_dict, dict) and wf_dict.get("a_galaxy_workflow") == "true":
        raise EncodeError("Already native format")

    step_statuses: List[StepEncodeStatus] = []
    callback = _make_encode_callback(get_tool_info, step_statuses, strict=strict)

    options = ConversionOptions(
        state_encode_to_native=callback,
        workflow_directory=workflow_dir,
        strict_structure=strict_structure,
    )
    native = to_native(wf_dict, options=options)
    return ToNativeResult(native=native, steps=step_statuses)


def run_to_native_tree(options: ToNativeTreeOptions) -> int:
    """Run tree format2→native conversion. Returns exit code."""
    if not os.path.isdir(options.workflow_path):
        print("Error: expected directory, got file", file=sys.stderr)
        return 2

    if not options.output_dir:
        print("Error: --output-dir is required for tree conversion", file=sys.stderr)
        return 2

    tool_info = setup_tool_info(options)

    from ._tree_orchestrator import (
        run_tree,
        skip_workflow,
        TreeContext,
    )
    from .workflow_tree import WorkflowInfo

    def process_one(info: WorkflowInfo, wf_dict: dict, get_tool_info):
        if isinstance(wf_dict, dict) and wf_dict.get("a_galaxy_workflow") == "true":
            skip_workflow("native format (not format2)")

        if options.strict_encoding:
            enc_errors = validate_encoding_format2(wf_dict)
            if enc_errors:
                raise RuntimeError("strict-encoding (input): " + "; ".join(enc_errors))

        if options.strict_structure:
            struct_errors = _check_strict_structure(wf_dict)
            if struct_errors:
                raise RuntimeError("strict-structure (input): " + "; ".join(struct_errors))

        result = _convert_dict_to_native(
            wf_dict,
            get_tool_info,
            strict=options.strict_state,
            workflow_dir=os.path.dirname(info.path),
            strict_structure=options.strict_structure,
        )

        if options.strict_encoding:
            enc_errors = validate_encoding_native(result.native_dict)
            if enc_errors:
                raise RuntimeError("strict-encoding (output): " + "; ".join(enc_errors))

        stem = os.path.splitext(info.relative_path)[0]
        out_path = os.path.join(options.output_dir, stem + ".ga")
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w") as f:
            f.write(format_native_json(result.native_dict))

        return WorkflowToNativeResult(
            path=info.path,
            relative_path=info.relative_path,
            category=info.category,
            ok=not result.failed_steps,
            steps_encoded=sum(1 for s in result.steps if s.encoded),
            steps_fallback=len(result.failed_steps),
        )

    def aggregate(tree_result):
        results = []
        for outcome in tree_result.outcomes:
            info = outcome.info
            if outcome.error:
                results.append(
                    WorkflowToNativeResult(
                        path=info.path,
                        relative_path=info.relative_path,
                        category=info.category,
                        error=outcome.error,
                    )
                )
            elif outcome.skipped:
                results.append(
                    WorkflowToNativeResult(
                        path=info.path,
                        relative_path=info.relative_path,
                        category=info.category,
                        skipped_reason=outcome.skip_reason,
                    )
                )
            elif outcome.result is not None:
                results.append(outcome.result)
        return ToNativeTreeReport(root=tree_result.root, output_dir=options.output_dir, results=results)

    def _format_text(report):
        lines = [f"Convert: {report.root} → {report.output_dir}"]
        for r in report.results:
            if r.error:
                lines.append(f"  {r.relative_path}: ERROR ({r.error})")
            elif r.skipped_reason:
                lines.append(f"  {r.relative_path}: SKIPPED ({r.skipped_reason})")
            elif r.ok:
                lines.append(f"  {r.relative_path}: OK ({r.steps_encoded} steps)")
            else:
                lines.append(f"  {r.relative_path}: PARTIAL ({r.steps_fallback} fallbacks)")
        s = report.summary
        lines.append(f"Summary: {s['ok']} OK, {s['fail']} errors, {s['skipped']} skipped")
        return "\n".join(lines)

    ctx = TreeContext(root=options.workflow_path, tool_info=tool_info, include_format2=True)
    return run_tree(
        ctx=ctx,
        process_one=process_one,
        aggregate=aggregate,
        format_text=_format_text,
        format_summary=lambda r: f"Convert: {r.summary['ok']} OK, {r.summary['fail']} errors",
        format_markdown=make_markdown_renderer("to_native_tree.md.j2"),
        compute_exit_code=lambda r: 1 if r.summary["fail"] > 0 else 0,
        report_options=options,
    )
