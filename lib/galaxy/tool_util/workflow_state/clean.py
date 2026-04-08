"""Stale state cleaning: domain logic, formatters, and run() entry point.

Strips stale tool_state keys from native .ga and format2 .gxwf.yml workflows
by comparing keys against current tool input definitions.
"""

import copy
import difflib
import json
import logging
import os
import sys
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
)

from gxformat2.normalized import (
    ensure_native,
    NormalizedNativeWorkflow,
)

from galaxy.tool_util.parameters import (
    ConditionalParameterModel,
    RepeatParameterModel,
    ToolParameterT,
)
from galaxy.tool_util_models.parameters import SectionParameterModel
from ._cli_common import (
    setup_tool_info,
    ToolCacheOptions,
)
from ._report_models import (
    CleanStepResult,
    SingleCleanReport,
    TreeCleanReport,
    WorkflowCleanResult,
    wrap_single_clean,
)
from ._report_output import emit_reports
from ._report_templates import make_markdown_renderer
from ._tree_orchestrator import skip_workflow
from ._types import (
    GetToolInfo,
    NativeStepDict,
    NativeWorkflowDict,
    ToolInputs,
)
from ._walker import (
    _NATIVE_BOOKKEEPING_KEYS,
    _select_which_when_native,
    select_which_when_format2,
)
from .precheck import precheck_native_workflow
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
    skip_uuid: bool = False


class CleanTreeOptions(ToolCacheOptions):
    output_template: Optional[str] = None
    report_json: Optional[str] = None
    report_markdown: Optional[str] = None
    preserve: List[str] = []
    strip: List[str] = []
    skip_uuid: bool = False


# -- Intermediate result (for single-workflow cleaning before wrapping) --


class CleanResult:
    """Mutable accumulator for a single workflow's cleaning pass."""

    def __init__(self):
        self.step_results: List[CleanStepResult] = []

    @property
    def total_removed(self) -> int:
        return sum(len(r.removed_state_keys) + len(r.removed_step_keys) for r in self.step_results)

    @property
    def steps_with_removals(self) -> int:
        return sum(1 for r in self.step_results if r.removed_state_keys or r.removed_step_keys)

    def merge(self, other: "CleanResult"):
        self.step_results.extend(other.step_results)


# -- Domain logic --


def strip_structural_step(step_dict: NativeStepDict, skip_uuid: bool = False) -> List[str]:
    """Strip Galaxy-injected structural properties from a step dict in place.

    Always removes: errors (Galaxy runtime annotation, not part of the workflow spec).
    Conditionally removes: uuid (unless skip_uuid=True).
    Preserves: position and all other keys.

    Returns the list of keys removed.
    """
    removed: List[str] = []
    if "errors" in step_dict:
        del step_dict["errors"]
        removed.append("errors")
    if not skip_uuid and "uuid" in step_dict:
        del step_dict["uuid"]
        removed.append("uuid")
    return removed


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
            if not isinstance(value, dict):
                continue
            cond_state = value

            test_param = conditional.test_parameter
            target_when = _select_which_when_native(conditional, cond_state)
            if target_when is None:
                branch_inputs: List[ToolParameterT] = [test_param]
            else:
                branch_inputs = [test_param] + list(target_when.parameters)
            _strip_recursive(
                cond_state, branch_inputs, removed_keys, prefix=child_prefix, strip_bookkeeping=strip_bookkeeping
            )
            state[name] = cond_state

        elif parameter_type == "gx_repeat":
            repeat = cast(RepeatParameterModel, tool_input)
            if not isinstance(value, list):
                continue
            repeat_state = value

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
            if not isinstance(value, dict):
                continue
            section_state = value
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

    removed_state_keys: List[str] = []
    _strip_recursive(
        tool_state,
        list(parsed_tool.inputs),
        removed_state_keys,
        strip_bookkeeping=_policy_to_strip_bookkeeping(policy),
    )
    step["tool_state"] = tool_state

    return CleanStepResult(
        step="?",
        tool_id=tool_id,
        version=tool_version,
        removed_state_keys=removed_state_keys,
    )


def clean_stale_state(
    workflow: NormalizedNativeWorkflow,
    workflow_dict: NativeWorkflowDict,
    get_tool_info: GetToolInfo,
    prefix: str = "",
    policy: Optional[StaleKeyPolicy] = None,
    skip_uuid: bool = False,
) -> CleanResult:
    """Clean stale keys from all steps in a native workflow dict (mutates in place).

    Uses *workflow* (pre-normalized) for step navigation (tool_id, type
    detection, subworkflow handling).  The raw *workflow_dict* is only
    touched to mutate tool_state.  The normalized model's tool_state is
    kept in sync with the raw dict after cleaning.

    When *policy* is None, defaults to ``StaleKeyPolicy.for_clean([], [])``
    which strips all stale categories including bookkeeping.
    """
    if policy is None:
        policy = StaleKeyPolicy.for_clean([], [])
    result = CleanResult()
    raw_steps = workflow_dict.get("steps", {})

    for step_id, step in sorted(workflow.steps.items(), key=lambda x: int(x[0])):
        step_label = f"{prefix}{step_id}" if prefix else str(step_id)

        if step.is_subworkflow_step and step.subworkflow:
            step_def = raw_steps.get(str(step_id), raw_steps.get(step_id, {}))
            sub_dict = step_def.get("subworkflow", {}) if isinstance(step_def, dict) else {}
            sub_result = clean_stale_state(
                step.subworkflow,
                sub_dict,
                get_tool_info,
                prefix=f"{step_label}.",
                policy=policy,
                skip_uuid=skip_uuid,
            )
            result.merge(sub_result)
            continue

        if not step.tool_id:
            continue

        if not step.tool_state:
            continue

        try:
            parsed_tool = get_parsed_tool_for_native_step(step, get_tool_info)
        except Exception as e:
            result.step_results.append(
                CleanStepResult(
                    step=step_label,
                    tool_id=step.tool_id,
                    version=step.tool_version,
                    skipped=True,
                    skip_reason=f"No tool definition: {e}",
                )
            )
            continue

        if parsed_tool is None:
            result.step_results.append(
                CleanStepResult(
                    step=step_label,
                    tool_id=step.tool_id,
                    version=step.tool_version,
                    skipped=True,
                    skip_reason="No tool definition",
                )
            )
            continue

        step_def = raw_steps.get(str(step_id), raw_steps.get(step_id, {}))
        removed_step_keys = strip_structural_step(step_def, skip_uuid=skip_uuid)
        step_result = strip_stale_keys(step_def, parsed_tool, policy=policy)
        # Keep normalized model in sync with the mutated raw dict
        cleaned_state = step_def.get("tool_state")
        if isinstance(cleaned_state, dict):
            step.tool_state = cleaned_state
        step_result.step = step_label
        step_result.removed_step_keys = removed_step_keys
        result.step_results.append(step_result)

    return result


def _strip_format2_recursive(
    state: Dict[str, Any],
    tool_inputs: List[ToolParameterT],
    removed_keys: List[str],
    prefix: str = "",
) -> None:
    """Remove stale keys from a format2 state dict in place.

    Format2 state is already decoded (no JSON double-encoding), so we compare
    keys directly against tool input names and recurse into containers.
    """
    known = {inp.name for inp in tool_inputs}
    stale = [key for key in state if key not in known]
    for key in stale:
        path = f"{prefix}{key}" if prefix else key
        removed_keys.append(path)
        del state[key]

    for tool_input in tool_inputs:
        name = tool_input.name
        if name not in state:
            continue
        value = state[name]
        child_prefix = f"{prefix}{name}." if prefix else f"{name}."

        if isinstance(tool_input, ConditionalParameterModel):
            if isinstance(value, dict):
                when = select_which_when_format2(tool_input, value)
                branch_inputs: List[ToolParameterT] = [tool_input.test_parameter]
                if when is not None:
                    branch_inputs = branch_inputs + list(when.parameters)
                _strip_format2_recursive(value, branch_inputs, removed_keys, prefix=child_prefix)

        elif isinstance(tool_input, RepeatParameterModel):
            if isinstance(value, list):
                for i, instance in enumerate(value):
                    if isinstance(instance, dict):
                        instance_prefix = f"{prefix}{name}_{i}." if prefix else f"{name}_{i}."
                        _strip_format2_recursive(
                            instance, list(tool_input.parameters), removed_keys, prefix=instance_prefix
                        )

        elif isinstance(tool_input, SectionParameterModel):
            if isinstance(value, dict):
                _strip_format2_recursive(value, list(tool_input.parameters), removed_keys, prefix=child_prefix)


def clean_format2_state(
    workflow_dict: dict,
    get_tool_info: GetToolInfo,
    policy: Optional[StaleKeyPolicy] = None,
    skip_uuid: bool = False,
    prefix: str = "",
) -> CleanResult:
    """Clean stale keys from all steps in a format2 workflow dict (mutates in place).

    Iterates raw workflow dict steps (both list and dict formats). Strips
    structural step keys (uuid/errors) and stale state keys for each tool step.
    Recurses into inline subworkflows via the ``run`` key.
    """
    if policy is None:
        policy = StaleKeyPolicy.for_clean([], [])
    result = CleanResult()
    raw_steps = workflow_dict.get("steps", {})

    if isinstance(raw_steps, dict):
        steps_iter = list(raw_steps.items())
    else:
        steps_iter = [(str(i), s) for i, s in enumerate(raw_steps)]

    for step_key, step_dict in steps_iter:
        if not isinstance(step_dict, dict):
            continue
        step_label = f"{prefix}{step_key}" if prefix else str(step_key)

        # Inline subworkflow — recurse, don't clean as a tool step
        run = step_dict.get("run")
        if isinstance(run, dict):
            sub_result = clean_format2_state(
                run, get_tool_info, policy=policy, skip_uuid=skip_uuid, prefix=f"{step_label}."
            )
            result.merge(sub_result)
            continue

        tool_id = step_dict.get("tool_id")
        if not tool_id:
            continue
        tool_version: Optional[str] = step_dict.get("tool_version")

        removed_step_keys = strip_structural_step(step_dict, skip_uuid=skip_uuid)

        try:
            parsed_tool = get_tool_info.get_tool_info(tool_id, tool_version)
        except Exception as e:
            result.step_results.append(
                CleanStepResult(
                    step=step_label,
                    tool_id=tool_id,
                    version=tool_version,
                    skipped=True,
                    skip_reason=f"No tool definition: {e}",
                    removed_step_keys=removed_step_keys,
                )
            )
            continue

        if parsed_tool is None:
            result.step_results.append(
                CleanStepResult(
                    step=step_label,
                    tool_id=tool_id,
                    version=tool_version,
                    skipped=True,
                    skip_reason="No tool definition",
                    removed_step_keys=removed_step_keys,
                )
            )
            continue

        state = step_dict.get("state")
        if not isinstance(state, dict):
            result.step_results.append(
                CleanStepResult(
                    step=step_label,
                    tool_id=tool_id,
                    version=tool_version,
                    removed_step_keys=removed_step_keys,
                )
            )
            continue

        removed_state_keys: List[str] = []
        _strip_format2_recursive(state, list(parsed_tool.inputs), removed_state_keys)

        result.step_results.append(
            CleanStepResult(
                step=step_label,
                tool_id=tool_id,
                version=tool_version,
                removed_state_keys=removed_state_keys,
                removed_step_keys=removed_step_keys,
            )
        )

    return result


def _is_format2(workflow_dict: dict) -> bool:
    return workflow_dict.get("a_galaxy_workflow") != "true"


def clean_single(
    workflow_path: str,
    tool_info: GetToolInfo,
    policy: Optional[StaleKeyPolicy] = None,
) -> SingleCleanReport:
    """Clean stale keys from a single workflow, return structured report.

    Library-level entry point with no CLI dependencies.
    Loads the workflow, prechecks, normalizes, cleans, and wraps results.
    Does not write to disk — the caller decides what to do with the report.
    """
    workflow = load_workflow(workflow_path)
    workflow_name = os.path.basename(workflow_path)

    precheck = precheck_native_workflow(workflow, tool_info)
    if not precheck.can_process:
        return SingleCleanReport(workflow=workflow_name, results=[])

    normalized = ensure_native(workflow)
    result = clean_stale_state(normalized, workflow, tool_info, policy=policy)
    return SingleCleanReport(workflow=workflow_name, results=list(result.step_results))


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


def _make_clean_process_one(
    policy: Optional[StaleKeyPolicy] = None,
    output_template: Optional[str] = None,
    skip_uuid: bool = False,
):
    """Build a process_one callback for clean tree runs."""
    from .workflow_tree import WorkflowInfo

    def process_one(info: WorkflowInfo, wf_dict: dict, get_tool_info: GetToolInfo):
        if output_template is None:
            work_copy = copy.deepcopy(wf_dict)
        else:
            work_copy = wf_dict

        if _is_format2(work_copy):
            result = clean_format2_state(work_copy, get_tool_info, policy=policy, skip_uuid=skip_uuid)
        else:
            precheck = precheck_native_workflow(wf_dict, get_tool_info)
            if not precheck.can_process:
                skip_workflow(precheck.skip_reasons[0].value)
            normalized = ensure_native(work_copy)
            result = clean_stale_state(normalized, work_copy, get_tool_info, policy=policy, skip_uuid=skip_uuid)

        if result.total_removed > 0 and output_template is not None:
            output_json = json.dumps(work_copy, indent=4) + "\n"
            output_path = expand_output_path(output_template, info.path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w") as f:
                f.write(output_json)

        return result

    return process_one


def _aggregate_clean(tree_result) -> TreeCleanReport:
    """Build TreeCleanReport from orchestrator outcomes."""
    from .precheck import SkipWorkflowReason

    report = TreeCleanReport(root=tree_result.root)
    for outcome in tree_result.outcomes:
        info = outcome.info
        if outcome.error:
            report.results.append(
                WorkflowCleanResult(
                    path=info.path,
                    relative_path=info.relative_path,
                    category=info.category,
                    error=outcome.error,
                )
            )
        elif outcome.skipped:
            report.results.append(
                WorkflowCleanResult(
                    path=info.path,
                    relative_path=info.relative_path,
                    category=info.category,
                    skipped_reason=SkipWorkflowReason(outcome.skip_reason),
                )
            )
        elif outcome.result is not None:
            result = outcome.result
            report.results.append(
                WorkflowCleanResult(
                    path=info.path,
                    relative_path=info.relative_path,
                    category=info.category,
                    step_results=result.step_results,
                    total_removed=result.total_removed,
                )
            )
    return report


def clean_tree(
    root: str,
    get_tool_info: "GetToolInfo",
    output_template: Optional[str] = None,
    policy: Optional[StaleKeyPolicy] = None,
    skip_uuid: bool = False,
) -> TreeCleanReport:
    """Clean stale state from all native .ga workflows under a directory tree.

    If output_template is None, operates in dry-run mode (no writes).
    """
    from ._tree_orchestrator import (
        collect_tree,
        TreeContext,
    )

    ctx = TreeContext(root=root, tool_info=get_tool_info, include_format2=True)
    process_one = _make_clean_process_one(policy=policy, output_template=output_template, skip_uuid=skip_uuid)
    tree_result = collect_tree(ctx, process_one)
    return _aggregate_clean(tree_result)


# -- Formatters --


def format_dry_run(result: CleanResult) -> str:
    lines = []
    for sr in result.step_results:
        if sr.skipped:
            lines.append(f"Step {sr.step} ({sr.tool_id}): SKIP ({sr.skip_reason})")
            continue
        all_removed = sr.removed_step_keys + sr.removed_state_keys
        if all_removed:
            tool_label = sr.tool_id or "unknown"
            if sr.version:
                tool_label += f" {sr.version}"
            lines.append(f"Step {sr.step} ({tool_label}):")
            lines.append(f"  Removed: {', '.join(all_removed)}")

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
        if r.skipped_reason:
            lines.append(f"  {r.relative_path}: SKIPPED ({r.skipped_reason.value})")
            continue
        if r.error:
            lines.append(f"  {r.relative_path}: ERROR ({r.error})")
            continue
        if r.total_removed > 0:
            lines.append(f"  {r.relative_path}: {r.total_removed} stale key(s)")
            for sr in r.step_results:
                all_removed = sr.removed_step_keys + sr.removed_state_keys
                if all_removed:
                    lines.append(f"    Step {sr.step} ({sr.tool_id}): {', '.join(all_removed)}")

    lines.append("---")
    skipped_count = s.get("skipped", 0)
    lines.append(
        f"Summary: {s['total_keys']} stale key(s), {s['affected']} affected, {s['clean']} clean, {s['errors']} errors, {skipped_count} skipped"
    )
    return "\n".join(lines)


# -- JSON formatters (delegate to Pydantic model_dump) --


def format_json_single(result: CleanResult, workflow_path: str) -> dict:
    report = SingleCleanReport(workflow=workflow_path, results=result.step_results)
    return report.model_dump(by_alias=True)


def format_json_tree(report: TreeCleanReport) -> dict:
    return report.model_dump(by_alias=True)


# -- Entry point --


def run_clean(options: CleanOptions) -> int:
    """Run single-file clean pipeline. Returns exit code."""
    if os.path.isdir(options.workflow_path):
        print("Error: got directory, use gxwf-state-clean-tree for batch cleaning", file=sys.stderr)
        return 2

    tool_info = setup_tool_info(options)

    try:
        policy = StaleKeyPolicy.for_clean(options.preserve, options.strip)
    except (InvalidCategoryError, ConflictingCategoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    return _run_single(options, tool_info, policy)


def run_clean_tree(options: CleanTreeOptions) -> int:
    """Run tree clean pipeline. Returns exit code."""
    if not os.path.isdir(options.workflow_path):
        print("Error: expected directory, got file", file=sys.stderr)
        return 2

    tool_info = setup_tool_info(options)

    try:
        policy = StaleKeyPolicy.for_clean(options.preserve, options.strip)
    except (InvalidCategoryError, ConflictingCategoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    from ._tree_orchestrator import (
        run_tree,
        TreeContext,
    )

    ctx = TreeContext(root=options.workflow_path, tool_info=tool_info, include_format2=True)
    process_one = _make_clean_process_one(
        policy=policy, output_template=options.output_template, skip_uuid=options.skip_uuid
    )

    return run_tree(
        ctx=ctx,
        process_one=process_one,
        aggregate=_aggregate_clean,
        format_text=format_tree_clean_text,
        format_summary=lambda r: f"Summary: {r.summary['total_keys']} stale key(s), {r.summary['affected']} affected",
        format_markdown=make_markdown_renderer("clean_tree.md.j2"),
        compute_exit_code=lambda r: 1 if r.summary["total_keys"] > 0 or r.summary["errors"] > 0 else 0,
        report_options=options,
    )


def _run_single(options: CleanOptions, tool_info, policy: StaleKeyPolicy) -> int:
    workflow = load_workflow(options.workflow_path)

    original_json = json.dumps(workflow, indent=4) + "\n"

    dry_run = options.output_template is None

    if dry_run:
        work_copy = copy.deepcopy(workflow)
    else:
        work_copy = workflow

    if _is_format2(work_copy):
        result = clean_format2_state(work_copy, tool_info, policy=policy, skip_uuid=options.skip_uuid)
    else:
        precheck = precheck_native_workflow(workflow, tool_info)
        if not precheck.can_process:
            print(f"Skipped: {precheck.detail}", file=sys.stderr)
            return 0
        normalized = ensure_native(work_copy)
        result = clean_stale_state(normalized, work_copy, tool_info, policy=policy, skip_uuid=options.skip_uuid)

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
            markdown_formatter=make_markdown_renderer("clean_tree.md.j2"),
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
