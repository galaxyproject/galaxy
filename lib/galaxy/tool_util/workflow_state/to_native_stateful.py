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
    Any,
    Dict,
    List,
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
    ToolCacheOptions,
)
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
) -> ToNativeResult:
    """Convert format2 workflow to native with schema-aware tool_state encoding.

    Requires format2 input — native .ga files are rejected because
    ensure_native() would short-circuit and skip the encoder callback.

    Conversion happens inside to_native() via the state_encode_to_native
    callback. Steps where encoding fails keep default json.dumps encoding
    unless strict=True.
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


class ToNativeOptions(ToolCacheOptions):
    output: Optional[str] = None
    strict: bool = False


class ToNativeTreeOptions(ToolCacheOptions):
    output_dir: str = ""
    strict: bool = False
    report_json: Optional[str] = None
    report_markdown: Optional[str] = None


class ToNativeTreeReport(BaseModel):
    """Tree-level report for batch format2→native conversion."""

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

    try:
        result = convert_to_native_stateful(
            options.workflow_path,
            tool_info,
            strict=options.strict,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = format_native_json(result.native_dict)

    if options.output:
        os.makedirs(os.path.dirname(os.path.abspath(options.output)), exist_ok=True)
        with open(options.output, "w") as f:
            f.write(output)
        print(format_summary(result), file=sys.stderr)
    else:
        print(format_summary(result), file=sys.stderr)
        sys.stdout.write(output)

    return 1 if result.failed_steps else 0


def _convert_dict_to_native(
    wf_dict: dict,
    get_tool_info: GetToolInfo,
    strict: bool = False,
    workflow_dir: str = "",
) -> ToNativeResult:
    """Convert a format2 dict to native (for tree mode)."""
    if isinstance(wf_dict, dict) and wf_dict.get("a_galaxy_workflow") == "true":
        raise EncodeError("Already native format")

    step_statuses: List[StepEncodeStatus] = []
    callback = _make_encode_callback(get_tool_info, step_statuses, strict=strict)

    options = ConversionOptions(
        state_encode_to_native=callback,
        workflow_directory=workflow_dir,
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

        result = _convert_dict_to_native(
            wf_dict,
            get_tool_info,
            strict=options.strict,
            workflow_dir=os.path.dirname(info.path),
        )

        stem = os.path.splitext(info.relative_path)[0]
        out_path = os.path.join(options.output_dir, stem + ".ga")
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w") as f:
            f.write(format_native_json(result.native_dict))

        return {
            "relative_path": info.relative_path,
            "ok": not result.failed_steps,
            "steps_encoded": sum(1 for s in result.steps if s.encoded),
            "steps_fallback": len(result.failed_steps),
        }

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
                        "path": r["relative_path"],
                        "ok": r["ok"],
                        "steps_encoded": r["steps_encoded"],
                        "steps_fallback": r["steps_fallback"],
                    }
                )
        return ToNativeTreeReport(root=tree_result.root, output_dir=options.output_dir, results=results)

    def _format_text(report):
        lines = [f"Convert: {report.root} → {report.output_dir}"]
        for r in report.results:
            path = r["path"]
            if r.get("error"):
                lines.append(f"  {path}: ERROR ({r['error']})")
            elif r.get("skipped_reason"):
                lines.append(f"  {path}: SKIPPED ({r['skipped_reason']})")
            elif r.get("ok"):
                lines.append(f"  {path}: OK ({r.get('steps_encoded', 0)} steps)")
            else:
                lines.append(f"  {path}: PARTIAL ({r.get('steps_fallback', 0)} fallbacks)")
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
        format_markdown=lambda r: _format_text(r),
        compute_exit_code=lambda r: 1 if r.summary["fail"] > 0 else 0,
        report_options=options,
    )
