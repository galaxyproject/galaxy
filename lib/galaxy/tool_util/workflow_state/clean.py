"""Stale state cleaning: domain logic, formatters, and run() entry point.

Strips stale tool_state keys from native .ga workflows by comparing
keys against current tool input definitions.
"""

import copy
import difflib
import json
import logging
import os
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
)

from ._cli_common import (
    setup_tool_info,
    ToolCacheOptions,
)
from galaxy.tool_util.parameters import (
    ConditionalParameterModel,
    RepeatParameterModel,
    ToolParameterT,
    validate_explicit_conditional_test_value,
)
from galaxy.tool_util_models.parameters import SectionParameterModel
from ._report_models import (
    CleanStepResult,
    SingleCleanReport,
    TreeCleanReport,
    WorkflowCleanResult,
    wrap_single_clean,
)
from ._report_output import emit_reports
from ._types import (
    GetToolInfo,
    NativeStepDict,
    NativeWorkflowDict,
    ToolInputs,
)
from ._walker import (
    _NATIVE_BOOKKEEPING_KEYS,
    _test_value_matches_discriminator,
    as_dict,
    as_list,
)
from .stale_keys import (
    ConflictingCategoryError,
    InvalidCategoryError,
    StaleKeyCategory,
    StaleKeyPolicy,
)
from .validation_native import get_parsed_tool_for_native_step
from .workflow_tools import load_workflow

log = logging.getLogger(__name__)

# Re-export for backwards compat
StepCleanResult = CleanStepResult


def _strip_bookkeeping_recursive(d: Dict[str, Any]) -> None:
    """Remove bookkeeping keys from a dict tree, recursing into nested dicts/lists.

    Does not require tool definitions — just walks all nested structures
    and removes keys in _NATIVE_BOOKKEEPING_KEYS.
    """
    for key in list(d.keys()):
        if key in _NATIVE_BOOKKEEPING_KEYS:
            del d[key]
            continue
        value = d[key]
        if isinstance(value, dict):
            _strip_bookkeeping_recursive(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _strip_bookkeeping_recursive(item)
        elif isinstance(value, str):
            try:
                decoded = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(decoded, dict):
                _strip_bookkeeping_recursive(decoded)
                d[key] = decoded
            elif isinstance(decoded, list):
                for item in decoded:
                    if isinstance(item, dict):
                        _strip_bookkeeping_recursive(item)
                d[key] = decoded


def strip_bookkeeping_from_workflow(workflow_dict: NativeWorkflowDict) -> None:
    """Strip all bookkeeping keys (__current_case__, etc.) from a native workflow in place."""
    steps = workflow_dict.get("steps", {})
    for step_def in steps.values():
        if step_def.get("type") == "subworkflow" and "subworkflow" in step_def:
            strip_bookkeeping_from_workflow(step_def["subworkflow"])
            continue
        tool_state_raw = step_def.get("tool_state")
        if not tool_state_raw:
            continue
        if isinstance(tool_state_raw, str):
            try:
                tool_state = json.loads(tool_state_raw)
            except (json.JSONDecodeError, TypeError):
                continue
        elif isinstance(tool_state_raw, dict):
            tool_state = tool_state_raw
        else:
            continue
        _strip_bookkeeping_recursive(tool_state)
        step_def["tool_state"] = tool_state


# -- Options model --


class CleanOptions(ToolCacheOptions):
    output_template: Optional[str] = None
    diff: bool = False
    report_json: Optional[str] = None
    report_markdown: Optional[str] = None
    preserve: List[str] = []
    strip: List[str] = []


# -- Intermediate result (for single-workflow cleaning before wrapping) --


class CleanResult:
    """Mutable accumulator for a single workflow's cleaning pass."""

    def __init__(self):
        self.step_results: List[CleanStepResult] = []

    @property
    def total_removed(self) -> int:
        return sum(len(r.removed_keys) for r in self.step_results)

    @property
    def steps_with_removals(self) -> int:
        return sum(1 for r in self.step_results if r.removed_keys)

    def merge(self, other: "CleanResult"):
        self.step_results.extend(other.step_results)


# -- Domain logic --


def _strip_recursive(
    state: Dict[str, Any],
    tool_inputs: List[ToolParameterT],
    removed_keys: List[str],
    prefix: str = "",
    strip_bookkeeping: bool = False,
):
    """Remove stale keys from state dict in place.

    Works on the raw JSON-decoded dict (values are still JSON strings for leaves,
    JSON-encoded dicts/lists for containers). Only decodes container values when
    recursing into them. Mutates state in place to preserve key ordering.
    """
    known = {inp.name for inp in tool_inputs}

    if strip_bookkeeping:
        stale = [key for key in state if key not in known]
    else:
        stale = [key for key in state if key not in known and key not in _NATIVE_BOOKKEEPING_KEYS]
    for key in stale:
        path = f"{prefix}{key}" if prefix else key
        removed_keys.append(path)
        del state[key]

    for tool_input in tool_inputs:
        name = tool_input.name
        if name not in state:
            continue

        value = state[name]
        parameter_type = tool_input.parameter_type
        child_prefix = f"{prefix}{name}|" if prefix else f"{name}|"

        if parameter_type == "gx_conditional":
            conditional = cast(ConditionalParameterModel, tool_input)
            cond_state = as_dict(value)
            if cond_state is None:
                continue

            test_param = conditional.test_parameter
            test_value_raw = cond_state.get(test_param.name)
            test_value = validate_explicit_conditional_test_value(test_param.name, test_value_raw)

            target_when = None
            for when in conditional.whens:
                if test_value is None and when.is_default_when:
                    target_when = when
                elif test_value is not None and _test_value_matches_discriminator(test_value, when.discriminator):
                    target_when = when

            if target_when is None:
                recorded_case = cond_state.get("__current_case__")
                if isinstance(recorded_case, int) and 0 <= recorded_case < len(conditional.whens):
                    target_when = conditional.whens[recorded_case]

            if target_when is None:
                continue

            branch_inputs: List[ToolParameterT] = [test_param] + list(target_when.parameters)
            _strip_recursive(
                cond_state, branch_inputs, removed_keys, prefix=child_prefix, strip_bookkeeping=strip_bookkeeping
            )
            state[name] = cond_state

        elif parameter_type == "gx_repeat":
            repeat = cast(RepeatParameterModel, tool_input)
            repeat_state = as_list(value)
            if not repeat_state:
                continue

            for i, instance in enumerate(repeat_state):
                if isinstance(instance, dict):
                    instance_prefix = f"{prefix}{name}_{i}|"
                    _strip_recursive(
                        instance,
                        list(repeat.parameters),
                        removed_keys,
                        prefix=instance_prefix,
                        strip_bookkeeping=strip_bookkeeping,
                    )
            state[name] = repeat_state

        elif parameter_type == "gx_section":
            section = cast(SectionParameterModel, tool_input)
            section_state = as_dict(value)
            if section_state is None:
                continue
            _strip_recursive(
                section_state,
                list(section.parameters),
                removed_keys,
                prefix=child_prefix,
                strip_bookkeeping=strip_bookkeeping,
            )
            state[name] = section_state


def _policy_to_strip_bookkeeping(policy: Optional[StaleKeyPolicy]) -> bool:
    """Extract strip_bookkeeping boolean from policy for _strip_recursive."""
    if policy is None:
        return False
    return policy.is_denied(StaleKeyCategory.BOOKKEEPING)


def strip_stale_keys(
    step: NativeStepDict, parsed_tool: ToolInputs, policy: Optional[StaleKeyPolicy] = None
) -> CleanStepResult:
    """Strip stale keys from a single step's tool_state."""
    tool_id = step.get("tool_id", "?")
    tool_version = step.get("tool_version")

    tool_state_raw = step.get("tool_state")
    if not tool_state_raw:
        return CleanStepResult(
            step="?",
            tool_id=tool_id,
            version=tool_version,
            skipped=True,
            skip_reason="No tool_state",
        )

    if isinstance(tool_state_raw, str):
        tool_state = json.loads(tool_state_raw)
    elif isinstance(tool_state_raw, dict):
        tool_state = tool_state_raw
    else:
        return CleanStepResult(
            step="?",
            tool_id=tool_id,
            version=tool_version,
            skipped=True,
            skip_reason="No tool_state",
        )

    removed_keys: List[str] = []
    _strip_recursive(
        tool_state,
        list(parsed_tool.inputs),
        removed_keys,
        strip_bookkeeping=_policy_to_strip_bookkeeping(policy),
    )
    step["tool_state"] = tool_state

    return CleanStepResult(
        step="?",
        tool_id=tool_id,
        version=tool_version,
        removed_keys=removed_keys,
    )


def clean_stale_state(
    workflow_dict: NativeWorkflowDict,
    get_tool_info: GetToolInfo,
    prefix: str = "",
    policy: Optional[StaleKeyPolicy] = None,
) -> CleanResult:
    """Clean stale keys from all steps in a native workflow dict (mutates in place)."""
    result = CleanResult()
    steps = workflow_dict.get("steps", {})

    for step_index, step_def in sorted(steps.items(), key=lambda x: int(x[0])):
        step_label = f"{prefix}{step_index}" if prefix else str(step_index)

        if step_def.get("type") == "subworkflow" and "subworkflow" in step_def:
            sub_result = clean_stale_state(
                step_def["subworkflow"], get_tool_info, prefix=f"{step_label}.", policy=policy
            )
            result.merge(sub_result)
            continue

        tool_id = step_def.get("tool_id")
        if not tool_id:
            continue

        tool_state = step_def.get("tool_state")
        if not tool_state:
            continue
        if isinstance(tool_state, dict):
            step_def["tool_state"] = json.dumps(tool_state)
        elif not isinstance(tool_state, str):
            continue

        try:
            parsed_tool = get_parsed_tool_for_native_step(step_def, get_tool_info)
        except Exception as e:
            result.step_results.append(
                CleanStepResult(
                    step=step_label,
                    tool_id=tool_id,
                    version=step_def.get("tool_version"),
                    skipped=True,
                    skip_reason=f"No tool definition: {e}",
                )
            )
            continue

        if parsed_tool is None:
            result.step_results.append(
                CleanStepResult(
                    step=step_label,
                    tool_id=tool_id,
                    version=step_def.get("tool_version"),
                    skipped=True,
                    skip_reason="No tool definition",
                )
            )
            continue

        step_result = strip_stale_keys(step_def, parsed_tool, policy=policy)
        step_result.step = step_label
        result.step_results.append(step_result)

    return result


def expand_output_path(template: str, original_path: str) -> str:
    """Expand an output template with path specifiers.

    Specifiers: {path}, {dir}, {name}, {stem}, {ext}
    """
    path = os.path.abspath(original_path)
    dir_part = os.path.dirname(path)
    name = os.path.basename(path)
    stem, ext = os.path.splitext(name)
    return template.format(
        path=path,
        dir=dir_part,
        name=name,
        stem=stem,
        ext=ext,
    )


def clean_tree(
    root: str,
    get_tool_info: "GetToolInfo",
    output_template: Optional[str] = None,
    policy: Optional[StaleKeyPolicy] = None,
) -> TreeCleanReport:
    """Clean stale state from all native .ga workflows under a directory tree.

    If output_template is None, operates in dry-run mode (no writes).
    """
    from .workflow_tree import (
        discover_workflows,
        load_workflow_safe,
    )

    workflows = discover_workflows(root, include_format2=False)
    report = TreeCleanReport(root=root)

    for info in workflows:
        wf_dict = load_workflow_safe(info)
        if wf_dict is None:
            report.results.append(
                WorkflowCleanResult(
                    path=info.path,
                    relative_path=info.relative_path,
                    category=info.category,
                    error="Failed to load workflow",
                )
            )
            continue

        if output_template is None:
            work_copy = copy.deepcopy(wf_dict)
        else:
            work_copy = wf_dict

        try:
            result = clean_stale_state(work_copy, get_tool_info, policy=policy)
        except Exception as e:
            report.results.append(
                WorkflowCleanResult(
                    path=info.path,
                    relative_path=info.relative_path,
                    category=info.category,
                    error=str(e),
                )
            )
            continue

        wf_result = WorkflowCleanResult(
            path=info.path,
            relative_path=info.relative_path,
            category=info.category,
            step_results=result.step_results,
            total_removed=result.total_removed,
        )
        report.results.append(wf_result)

        if result.total_removed > 0 and output_template is not None:
            output_json = json.dumps(work_copy, indent=4) + "\n"
            output_path = expand_output_path(output_template, info.path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w") as f:
                f.write(output_json)

    return report


# -- Formatters --


def format_dry_run(result: CleanResult) -> str:
    lines = []
    for sr in result.step_results:
        if sr.skipped:
            lines.append(f"Step {sr.step} ({sr.tool_id}): SKIP ({sr.skip_reason})")
            continue
        if sr.removed_keys:
            tool_label = sr.tool_id or "unknown"
            if sr.version:
                tool_label += f" {sr.version}"
            lines.append(f"Step {sr.step} ({tool_label}):")
            lines.append(f"  Removed: {', '.join(sr.removed_keys)}")

    if result.total_removed:
        lines.append("---")
        lines.append(f"{result.total_removed} stale key(s) found across {result.steps_with_removals} step(s)")
    else:
        lines.append("No stale keys found.")
    return "\n".join(lines)


def format_tree_clean_text(report: TreeCleanReport) -> str:
    s = report.summary
    total_wf = len(report.results)
    lines = [
        f"Root: {report.root}",
        f"Workflows: {total_wf} | {s['total_keys']} stale key(s) across {s['affected']} workflow(s)",
        "",
    ]

    for r in report.results:
        if r.error:
            lines.append(f"  {r.relative_path}: ERROR ({r.error})")
            continue
        if r.total_removed > 0:
            lines.append(f"  {r.relative_path}: {r.total_removed} stale key(s)")
            for sr in r.step_results:
                if sr.removed_keys:
                    lines.append(f"    Step {sr.step} ({sr.tool_id}): {', '.join(sr.removed_keys)}")

    lines.append("---")
    lines.append(
        f"Summary: {s['total_keys']} stale key(s), {s['affected']} affected, {s['clean']} clean, {s['errors']} errors"
    )
    return "\n".join(lines)


def format_tree_clean_markdown(report: TreeCleanReport) -> str:
    s = report.summary
    total_wf = len(report.results)
    lines = [
        "# Stale State Cleaning Report",
        "",
        f"Root: `{report.root}`",
        f"Workflows: {total_wf} | {s['total_keys']} stale key(s) across {s['affected']} workflow(s)",
        "",
    ]

    affected = [r for r in report.results if r.total_removed > 0 or r.error]
    if affected:
        lines.append("## Affected Workflows")
        lines.append("")
        lines.append("| Workflow | Steps Affected | Keys Removed | Details |")
        lines.append("| --- | --- | --- | --- |")
        for r in affected:
            name = r.relative_path
            if r.error:
                lines.append(f"| {name} | - | - | ERROR: {r.error} |")
                continue
            steps_affected = sum(1 for sr in r.step_results if sr.removed_keys)
            details_parts = []
            for sr in r.step_results:
                if sr.removed_keys:
                    details_parts.append(f"Step {sr.step} ({sr.tool_id}): {', '.join(sr.removed_keys)}")
            detail = "; ".join(details_parts) if details_parts else ""
            lines.append(f"| {name} | {steps_affected} | {r.total_removed} | {detail} |")
        lines.append("")

    if s["clean"] > 0:
        lines.append(f"## Clean Workflows ({s['clean']})")
        lines.append("")
        lines.append("All other workflows have no stale keys.")
        lines.append("")

    detail_lines = []
    for r in report.results:
        if r.total_removed > 0:
            detail_lines.append(f"### {r.relative_path}")
            for sr in r.step_results:
                if sr.removed_keys:
                    tool_label = sr.tool_id or "unknown"
                    if sr.version:
                        tool_label += f" {sr.version}"
                    detail_lines.append(f"- Step {sr.step} ({tool_label}): Removed `{'`, `'.join(sr.removed_keys)}`")
            detail_lines.append("")

    if detail_lines:
        lines.append("## Per-Workflow Details")
        lines.append("")
        lines.extend(detail_lines)

    return "\n".join(lines)


# -- JSON formatters (delegate to Pydantic model_dump) --


def format_json_single(result: CleanResult, workflow_path: str) -> dict:
    report = SingleCleanReport(workflow=workflow_path, results=result.step_results)
    return report.model_dump(by_alias=True)


def format_json_tree(report: TreeCleanReport) -> dict:
    return report.model_dump(by_alias=True)


# -- Entry point --


def run_clean(options: CleanOptions) -> int:
    """Run clean pipeline. Returns exit code."""
    import sys

    tool_info = setup_tool_info(options)

    try:
        policy = StaleKeyPolicy.for_clean(options.preserve, options.strip)
    except (InvalidCategoryError, ConflictingCategoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    is_dir = os.path.isdir(options.workflow_path)

    if is_dir:
        return _run_tree(options, tool_info, policy)
    else:
        return _run_single(options, tool_info, policy)


def _run_single(options: CleanOptions, tool_info, policy: StaleKeyPolicy) -> int:
    workflow = load_workflow(options.workflow_path)
    original_json = json.dumps(workflow, indent=4) + "\n"

    dry_run = options.output_template is None

    if dry_run:
        work_copy = copy.deepcopy(workflow)
    else:
        work_copy = workflow

    result = clean_stale_state(work_copy, tool_info, policy=policy)

    if options.diff:
        cleaned_json = json.dumps(work_copy, indent=4) + "\n"
        diff = difflib.unified_diff(
            original_json.splitlines(keepends=True),
            cleaned_json.splitlines(keepends=True),
            fromfile=options.workflow_path,
            tofile=options.workflow_path + " (cleaned)",
        )
        diff_text = "".join(diff)
        if diff_text:
            print(diff_text, end="")
        else:
            print("No changes.")

    json_data = SingleCleanReport(workflow=options.workflow_path, results=result.step_results)
    tree_report = wrap_single_clean(options.workflow_path, result.step_results)

    has_explicit_report = options.report_json is not None or options.report_markdown is not None

    # When --diff is shown, skip text/stderr output (diff already printed above)
    if not options.diff:
        text_content = format_dry_run(result)
        stderr_summary = format_dry_run(result)
    else:
        text_content = None
        stderr_summary = None

    # Emit JSON/Markdown reports via shared infrastructure
    if has_explicit_report:
        emit_reports(
            options=options,
            json_data=json_data,
            markdown_formatter=format_tree_clean_markdown,
            markdown_report=tree_report,
            text_content=text_content or "",
            stderr_summary=stderr_summary or "",
        )
    elif text_content:
        print(text_content)

    if not dry_run and result.total_removed > 0:
        output_json = json.dumps(work_copy, indent=4) + "\n"
        output_path = expand_output_path(options.output_template or options.workflow_path, options.workflow_path)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(output_json)

    return 1 if result.total_removed else 0


def _run_tree(options: CleanOptions, tool_info, policy: StaleKeyPolicy) -> int:
    report = clean_tree(
        options.workflow_path,
        tool_info,
        output_template=options.output_template,
        policy=policy,
    )

    s = report.summary
    emit_reports(
        options=options,
        json_data=report,
        markdown_formatter=format_tree_clean_markdown,
        markdown_report=report,
        text_content=format_tree_clean_text(report),
        stderr_summary=f"Summary: {s['total_keys']} stale key(s), {s['affected']} affected",
    )

    if s["total_keys"] > 0 or s["errors"] > 0:
        return 1
    return 0
