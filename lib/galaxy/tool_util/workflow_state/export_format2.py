"""Export native Galaxy workflows to format2 with schema-aware state blocks.

gxformat2's to_format2() handles structural conversion (step ordering,
labels, connections). When given a state_encode_to_format2 callback via
ConversionOptions, it also converts tool_state to clean `state` dicts
using tool definitions. This module wires that callback with stale key
policy, strict mode, and per-step status tracking.
"""

import copy
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

from gxformat2.normalized import NormalizedFormat2
from gxformat2.options import ConversionOptions

from ._cli_common import (
    setup_tool_info,
    ToolCacheOptions,
)
from ._types import (
    GetToolInfo,
    NativeWorkflowDict,
)
from .convert import (
    ConversionValidationFailure,
    convert_state_to_format2,
)
from .stale_keys import (
    classify_stale_keys,
    ConflictingCategoryError,
    InvalidCategoryError,
    StaleKeyPolicy,
)
from .validation import _format
from .validation_native import get_parsed_tool_for_native_step
from .workflow_tools import load_workflow

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
    workflow_dict: NativeWorkflowDict,
    get_tool_info: GetToolInfo,
    strict: bool = False,
    policy: StaleKeyPolicy | None = None,
) -> ExportResult:
    """Export native workflow as format2 with schema-aware state blocks.

    Conversion happens inside to_format2() via the state_encode_to_format2
    callback. Steps where conversion fails keep their tool_state (best-effort)
    unless strict=True.
    """
    from gxformat2.to_format2 import to_format2

    if _format(workflow_dict) != "native":
        raise ValueError("export_workflow_to_format2 requires a native (.ga) workflow")

    step_statuses: list[StepExportStatus] = []
    callback = _make_export_callback(get_tool_info, step_statuses, strict=strict, policy=policy)

    native_copy = copy.deepcopy(workflow_dict)
    options = ConversionOptions(state_encode_to_format2=callback)
    format2_model = to_format2(native_copy, options=options)

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
    strict: bool = False
    diff: bool = False
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


def format_diff(original_format2: dict, converted_format2: dict, workflow_path: str) -> str:
    import difflib

    original_yaml = format_yaml(original_format2)
    converted_yaml = format_yaml(converted_format2)
    diff = difflib.unified_diff(
        original_yaml.splitlines(keepends=True),
        converted_yaml.splitlines(keepends=True),
        fromfile=f"{workflow_path} (naive)",
        tofile=f"{workflow_path} (schema-aware)",
    )
    return "".join(diff)


# -- Entry point --


def run_export(options: ExportOptions) -> int:
    """Run export pipeline. Returns exit code."""
    from gxformat2.to_format2 import to_format2

    tool_info = setup_tool_info(options)

    workflow = load_workflow(options.workflow_path)
    if _format(workflow) != "native":
        print("Error: input must be a native .ga workflow", file=sys.stderr)
        return 1

    try:
        policy = StaleKeyPolicy.for_export(options.allow, options.deny)
    except (InvalidCategoryError, ConflictingCategoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    try:
        result = export_workflow_to_format2(workflow, tool_info, strict=options.strict, policy=policy)
    except ExportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if options.diff:
        # Generate naive format2 for comparison
        naive_copy = copy.deepcopy(workflow)
        naive_model = to_format2(naive_copy)
        naive_dict = naive_model.to_dict()
        diff_text = format_diff(naive_dict, result.format2_dict, options.workflow_path)
        if diff_text:
            print(diff_text, end="")
        else:
            print("No differences.")
        print("---", file=sys.stderr)
        print(result.summary, file=sys.stderr)
        return 0

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
