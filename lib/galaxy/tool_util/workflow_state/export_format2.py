"""Export native Galaxy workflows to format2 with schema-aware state blocks.

gxformat2's from_galaxy_native() handles structural conversion (step ordering,
labels, connections) but produces tool_state as opaque JSON strings because it
has no tool definitions. This module replaces those with clean `state` dicts
using convert_state_to_format2(), falling back to tool_state on failure.
"""

import argparse
import copy
import logging
import os
import sys
from dataclasses import (
    dataclass,
    field,
)

from pydantic import BaseModel

from ._types import (
    Format2WorkflowDict,
    GetToolInfo,
    NativeWorkflowDict,
)
from .convert import convert_state_to_format2
from .roundtrip import (
    ensure_export_defaults,
    find_matching_native_step,
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
    format2_dict: Format2WorkflowDict
    steps: list[StepExportStatus] = field(default_factory=list)

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

    Structural conversion (step ordering, labels, connections) is delegated
    to gxformat2's from_galaxy_native(). We only replace tool_state with
    clean state + in blocks per tool step.

    In best-effort mode (default), steps that fail conversion keep their
    tool_state. In strict mode, any failure raises.

    If policy is provided, steps with denied stale key categories are skipped.
    """
    from gxformat2.export import from_galaxy_native

    if _format(workflow_dict) != "native":
        raise ValueError("export_workflow_to_format2 requires a native (.ga) workflow")

    native_copy = copy.deepcopy(workflow_dict)
    ensure_export_defaults(native_copy)
    format2_dict = from_galaxy_native(native_copy)

    steps: list[StepExportStatus] = []
    _replace_states(format2_dict, workflow_dict, get_tool_info, steps, strict, policy=policy)

    return ExportResult(format2_dict=format2_dict, steps=steps)


def _replace_states(
    format2_dict: dict,
    native_workflow: dict,
    get_tool_info: GetToolInfo,
    steps: list[StepExportStatus],
    strict: bool,
    path_prefix: str = "",
    policy: StaleKeyPolicy | None = None,
):
    """Replace tool_state with converted state in format2 steps."""
    format2_steps = format2_dict.get("steps", [])
    if isinstance(format2_steps, list):
        steps_iter = list(enumerate(format2_steps))
    else:
        steps_iter = list(format2_steps.items())

    num_inputs = len(format2_dict.get("inputs", {}))

    for step_key, format2_step in steps_iter:
        native_step_id = step_key + num_inputs if isinstance(step_key, int) else step_key
        step_label = f"{path_prefix}{native_step_id}"

        # Subworkflow — recurse into run: block
        if "run" in format2_step and isinstance(format2_step["run"], dict):
            native_step = find_matching_native_step(native_workflow, format2_step, native_step_id)
            if native_step and "subworkflow" in native_step:
                _replace_states(
                    format2_step["run"],
                    native_step["subworkflow"],
                    get_tool_info,
                    steps,
                    strict,
                    path_prefix=f"{step_label}.",
                    policy=policy,
                )
            continue

        # Non-tool steps
        if not format2_step.get("tool_id") and "tool_state" not in format2_step:
            continue

        native_step = find_matching_native_step(native_workflow, format2_step, native_step_id)
        tool_id = format2_step.get("tool_id")

        if native_step is None:
            status = StepExportStatus(
                step_id=step_label,
                step_label=format2_step.get("label"),
                tool_id=tool_id,
                converted=False,
                error="No matching native step found",
            )
            steps.append(status)
            if strict:
                raise ExportError(f"Step {step_label}: {status.error}")
            continue

        # Check stale key policy before conversion
        if policy and policy.denied:
            try:
                parsed_tool = get_parsed_tool_for_native_step(native_step, get_tool_info)
                if parsed_tool:
                    stale = classify_stale_keys(native_step, parsed_tool)
                    denied, _ = policy.filter(stale)
                    if denied:
                        cats = ", ".join(sorted({sk.category.value for sk in denied}))
                        steps.append(
                            StepExportStatus(
                                step_id=step_label,
                                step_label=format2_step.get("label"),
                                tool_id=tool_id,
                                converted=False,
                                error=f"Denied stale key categories: {cats}",
                            )
                        )
                        continue
            except Exception:
                pass  # classification failure shouldn't block conversion

        try:
            f2_state = convert_state_to_format2(native_step, get_tool_info)
            format2_step.pop("tool_state", None)
            format2_step["state"] = f2_state.state
            if f2_state.inputs:
                format2_step["in"] = {k: {"source": v} for k, v in f2_state.inputs.items() if v != "placeholder"}
            steps.append(
                StepExportStatus(
                    step_id=step_label,
                    step_label=format2_step.get("label"),
                    tool_id=tool_id,
                    converted=True,
                )
            )
        except Exception as e:
            error_msg = str(e)
            steps.append(
                StepExportStatus(
                    step_id=step_label,
                    step_label=format2_step.get("label"),
                    tool_id=tool_id,
                    converted=False,
                    error=error_msg,
                )
            )
            if strict:
                raise ExportError(f"Step {step_label}: {error_msg}") from e
            log.debug("Step %s: conversion failed, keeping tool_state: %s", step_label, error_msg)


class ExportError(Exception):
    pass


# -- Options model --


class ExportOptions(BaseModel):
    workflow_path: str
    output: str | None = None
    json_output: bool = False
    tool_source_cache_dir: str | None = None
    verbose: bool = False
    populate_cache: bool = False
    tool_source: str = "auto"
    strict: bool = False
    diff: bool = False
    allow: list[str] = []
    deny: list[str] = []

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "ExportOptions":
        fields = set(cls.model_fields)
        return cls(**{k: v for k, v in vars(args).items() if k in fields})


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
    from gxformat2.export import from_galaxy_native

    from ._cli_common import setup_logging
    from .cache import (
        build_tool_info,
        populate_cache,
    )

    setup_logging(options.verbose)
    tool_info = build_tool_info(options.tool_source_cache_dir)

    if options.populate_cache:
        populate_cache(tool_info, options.workflow_path, source=options.tool_source)
        print("", file=sys.stderr)

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
        ensure_export_defaults(naive_copy)
        naive_format2 = from_galaxy_native(naive_copy)
        diff_text = format_diff(naive_format2, result.format2_dict, options.workflow_path)
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
