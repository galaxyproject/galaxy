"""Reusable round-trip logic for native↔format2 workflow state conversion.

Provides comparison, classification, and full round-trip validation
functions used by both the CLI tools and the test harness.
"""

import argparse
import copy
import json
import logging
import os
import sys
from dataclasses import (
    dataclass,
    field,
)
from enum import Enum
from typing import (
    Any,
)

from gxformat2.normalized import (
    NormalizedNativeStep,
    NormalizedNativeWorkflow,
)
from gxformat2.options import ConversionOptions
from gxformat2.schema.native import NativeInputConnection
from gxformat2.to_format2 import to_format2
from gxformat2.to_native import (
    ensure_native,
    to_native,
)
from pydantic import BaseModel

from ._types import GetToolInfo
from .convert import (
    ConversionValidationFailure,
    convert_state_to_format2,
    make_convert_tool_state,
    make_encode_tool_state,
)

log = logging.getLogger(__name__)


# -- Failure classification --


class FailureClass(Enum):
    TOOL_NOT_FOUND = "tool_not_found"
    NATIVE_VALIDATION = "native_validation"
    CONVERSION_ERROR = "conversion_error"
    TYPE_NOT_HANDLED = "type_not_handled"
    FORMAT2_VALIDATION = "format2_validation"
    REIMPORT_ERROR = "reimport_error"
    ROUNDTRIP_MISMATCH = "roundtrip_mismatch"
    SUBWORKFLOW = "subworkflow"
    PARSE_ERROR = "parse_error"
    OTHER = "other"


@dataclass
class StepResult:
    step_id: str
    tool_id: str | None
    success: bool
    failure_class: FailureClass | None = None
    error: str | None = None
    diffs: list[str] = field(default_factory=list)


@dataclass
class RoundTripResult:
    workflow_name: str
    direction: str  # "native_to_format2" or "format2_to_native"
    step_results: list[StepResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return all(r.success for r in self.step_results)

    @property
    def failure_summary(self) -> str:
        failures = [r for r in self.step_results if not r.success]
        if not failures:
            return "PASS"
        parts = []
        for f in failures:
            parts.append(
                f"step {f.step_id} ({f.tool_id}): {f.failure_class.value if f.failure_class else 'unknown'} - {f.error}"
            )
        return "; ".join(parts)


# -- Diff model --


class DiffType(Enum):
    VALUE_MISMATCH = "value_mismatch"
    MISSING_IN_ROUNDTRIP = "missing_in_roundtrip"
    MISSING_IN_ORIGINAL = "missing_in_original"
    CONNECTION_MISMATCH = "connection_mismatch"
    POSITION_MISMATCH = "position_mismatch"
    LABEL_MISMATCH = "label_mismatch"
    ANNOTATION_MISMATCH = "annotation_mismatch"
    COMMENT_MISMATCH = "comment_mismatch"
    STEP_MISSING = "step_missing"


class DiffSeverity(Enum):
    ERROR = "error"
    BENIGN = "benign"


@dataclass(frozen=True)
class BenignArtifact:
    reason: str
    proven_by: list[str] = field(default_factory=list)


class KnownBenignArtifacts:
    ALL_NONE_SECTION_OMITTED = BenignArtifact(
        reason="all-None section omitted by format2 export",
        proven_by=[
            "lib/galaxy_test/api/test_wf_conversion_artifacts.py::TestWfConversionArtifacts::test_absent_allnone_section"
        ],
    )
    EMPTY_REPEAT_OMITTED = BenignArtifact(
        reason="empty repeat/list omitted by format2 export",
        proven_by=[
            "lib/galaxy_test/api/test_wf_conversion_artifacts.py::TestWfConversionArtifacts::test_absent_empty_repeat_safe_template",
            "lib/galaxy_test/api/test_tool_execute.py::test_optional_repeats_with_mins_filled_id",
        ],
    )
    CONNECTION_ONLY_SECTION_OMITTED = BenignArtifact(
        reason="connection-only section omitted (connections in 'in' block)",
        proven_by=[
            "lib/galaxy_test/api/test_wf_conversion_artifacts.py::TestWfConversionArtifacts::test_connection_only_section_omitted"
        ],
    )
    MULTI_SELECT_NORMALIZED = BenignArtifact(
        reason="multiple-select scalar normalized to list",
        proven_by=[
            "lib/galaxy_test/api/test_wf_conversion_artifacts.py::TestWfConversionArtifacts::test_multiple_select_list_form"
        ],
    )
    MULTI_SELECT_COLLAPSED = BenignArtifact(
        reason="multiple-select list collapsed to scalar",
        proven_by=["lib/galaxy_test/api/test_tool_execute.py::test_multi_select_as_list"],
    )
    MULTI_SELECT_REPRESENTATION = BenignArtifact(
        reason="multiple-select representation difference",
        proven_by=[
            "lib/galaxy_test/api/test_wf_conversion_artifacts.py::TestWfConversionArtifacts::test_multiple_select_list_form",
            "lib/galaxy_test/api/test_tool_execute.py::test_multi_select_as_list",
        ],
    )


@dataclass
class StepDiff:
    step_path: str
    key_path: str
    diff_type: DiffType
    severity: DiffSeverity
    description: str
    original_value: Any | None = None
    roundtrip_value: Any | None = None
    benign_artifact: BenignArtifact | None = None

    def format_line(self, verbose: bool = False) -> str:
        tag = f"[{self.severity.value}] " if self.severity == DiffSeverity.BENIGN else ""
        suffix = f" ({self.benign_artifact.reason})" if verbose and self.benign_artifact else ""
        return f"  {tag}{self.step_path}: {self.description}{suffix}"


# -- Benign classifiers --


def _is_all_none_dict(d) -> bool:
    """Dict where every leaf is None/null — dropped by gxformat2 as empty."""
    if not isinstance(d, dict):
        return False
    if not d:
        return True
    for v in d.values():
        if isinstance(v, dict):
            if not _is_all_none_dict(v):
                return False
        elif v not in (None, "null"):
            return False
    return True


def _is_empty_container_dict(d) -> bool:
    """Dict containing only empty lists and None/null — dropped by gxformat2."""
    if not isinstance(d, dict):
        return False
    has_empty_list = False
    for v in d.values():
        if isinstance(v, list) and len(v) == 0:
            has_empty_list = True
        elif isinstance(v, dict):
            if not _is_empty_container_dict(v):
                return False
        elif v not in (None, "null"):
            return False
    return has_empty_list


def _is_connection_only_dict(d) -> bool:
    """Dict where every leaf is ConnectedValue/RuntimeValue or None — connections preserved in 'in' block."""
    if not isinstance(d, dict):
        return False
    if not d:
        return False
    for v in d.values():
        if isinstance(v, dict):
            if _is_connection_marker(v):
                continue
            if not _is_connection_only_dict(v):
                return False
        elif v not in (None, "null"):
            return False
    return True


def _classify_missing_value(orig_val: Any) -> tuple[DiffSeverity, BenignArtifact | None]:
    """Classify a value present in original but missing in roundtripped."""
    if isinstance(orig_val, dict):
        if _is_all_none_dict(orig_val):
            return DiffSeverity.BENIGN, KnownBenignArtifacts.ALL_NONE_SECTION_OMITTED
        if _is_empty_container_dict(orig_val):
            return DiffSeverity.BENIGN, KnownBenignArtifacts.EMPTY_REPEAT_OMITTED
        if _is_connection_only_dict(orig_val):
            return DiffSeverity.BENIGN, KnownBenignArtifacts.CONNECTION_ONLY_SECTION_OMITTED
    return DiffSeverity.ERROR, None


def _classify_value_mismatch(orig_val: Any, after_val: Any) -> tuple[DiffSeverity, BenignArtifact | None]:
    """Classify a value mismatch — some are benign multiple-select representation differences."""
    if _is_multiple_select_equivalent(orig_val, after_val):
        if isinstance(after_val, list) and not isinstance(orig_val, list):
            return DiffSeverity.BENIGN, KnownBenignArtifacts.MULTI_SELECT_NORMALIZED
        elif isinstance(orig_val, list) and not isinstance(after_val, list):
            return DiffSeverity.BENIGN, KnownBenignArtifacts.MULTI_SELECT_COLLAPSED
        else:
            return DiffSeverity.BENIGN, KnownBenignArtifacts.MULTI_SELECT_REPRESENTATION
    return DiffSeverity.ERROR, None


def _is_multiple_select_equivalent(a: Any, b: Any) -> bool:
    """Check if two values are equivalent multiple-select representations.

    Native tool_state may store multiple-select values as:
    - comma-delimited string: "35" or "35,62"
    - JSON list: ["35"] or ["35", "62"]
    - bare scalar (after JSON decode): 35
    All are equivalent for the same parameter.
    """

    def _to_str_list(v):
        if isinstance(v, list):
            return [str(x) for x in v]
        if isinstance(v, str):
            return [x.strip() for x in v.split(",")]
        if isinstance(v, (int, float)):
            return [str(v)]
        return None

    a_list = _to_str_list(a)
    b_list = _to_str_list(b)
    if a_list is not None and b_list is not None:
        return a_list == b_list
    return False


# -- Comparison logic --

SKIP_KEYS = {
    "__current_case__",
    "__input_ext",
    "__page__",
    "__rerun_remap_job_id__",
    "__index__",
    "__job_resource",
    "chromInfo",
}


def compare_tool_state(orig: dict, after: dict, path: str = "", step_path: str = "") -> list[StepDiff]:
    """Recursively compare parsed tool_state dicts, skipping bookkeeping keys."""
    diffs: list[StepDiff] = []
    all_keys = set(list(orig.keys()) + list(after.keys()))
    for key in sorted(all_keys):
        if key in SKIP_KEYS:
            continue
        key_path = f"{path}.{key}" if path else key
        orig_val = _try_json_decode(orig.get(key))
        after_val = _try_json_decode(after.get(key))
        if key not in orig:
            if after_val not in (None, "null"):
                diffs.append(
                    StepDiff(
                        step_path=step_path,
                        key_path=key_path,
                        diff_type=DiffType.MISSING_IN_ORIGINAL,
                        severity=DiffSeverity.ERROR,
                        description=f"missing in original, present in roundtripped ({after_val!r})",
                        roundtrip_value=after_val,
                    )
                )
        elif key not in after:
            if orig_val in (None, "null", []) or _is_connection_marker(orig_val):
                continue
            severity, artifact = _classify_missing_value(orig_val)
            diffs.append(
                StepDiff(
                    step_path=step_path,
                    key_path=key_path,
                    diff_type=DiffType.MISSING_IN_ROUNDTRIP,
                    severity=severity,
                    description=f"present in original ({orig_val!r}), missing in roundtripped",
                    original_value=orig_val,
                    benign_artifact=artifact,
                )
            )
        elif isinstance(orig_val, dict) and isinstance(after_val, dict):
            diffs.extend(compare_tool_state(orig_val, after_val, key_path, step_path))
        elif isinstance(orig_val, list) and isinstance(after_val, list):
            diffs.extend(_compare_list_state(orig_val, after_val, key_path, step_path))
        elif not _values_equivalent(orig_val, after_val):
            severity, artifact = _classify_value_mismatch(orig_val, after_val)
            diffs.append(
                StepDiff(
                    step_path=step_path,
                    key_path=key_path,
                    diff_type=DiffType.VALUE_MISMATCH,
                    severity=severity,
                    description=f"{orig_val!r} != {after_val!r}",
                    original_value=orig_val,
                    roundtrip_value=after_val,
                    benign_artifact=artifact,
                )
            )
    return diffs


def _compare_list_state(orig: list, after: list, path: str, step_path: str = "") -> list[StepDiff]:
    """Compare lists (e.g. repeat instances) in tool state."""
    diffs: list[StepDiff] = []
    if len(orig) > 0 and isinstance(orig[0], str):
        try:
            orig = [json.loads(v) if isinstance(v, str) else v for v in orig]
        except (json.JSONDecodeError, TypeError):
            pass
    if len(after) > 0 and isinstance(after[0], str):
        try:
            after = [json.loads(v) if isinstance(v, str) else v for v in after]
        except (json.JSONDecodeError, TypeError):
            pass
    if len(orig) != len(after):
        diffs.append(
            StepDiff(
                step_path=step_path,
                key_path=path,
                diff_type=DiffType.VALUE_MISMATCH,
                severity=DiffSeverity.ERROR,
                description=f"{len(orig)} items vs {len(after)}",
                original_value=orig,
                roundtrip_value=after,
            )
        )
        return diffs
    for i, (o, a) in enumerate(zip(orig, after)):
        item_path = f"{path}[{i}]"
        if isinstance(o, dict) and isinstance(a, dict):
            diffs.extend(compare_tool_state(o, a, item_path, step_path))
        elif not _values_equivalent(o, a):
            severity, artifact = _classify_value_mismatch(o, a)
            diffs.append(
                StepDiff(
                    step_path=step_path,
                    key_path=item_path,
                    diff_type=DiffType.VALUE_MISMATCH,
                    severity=severity,
                    description=f"{o!r} != {a!r}",
                    original_value=o,
                    roundtrip_value=a,
                    benign_artifact=artifact,
                )
            )
    return diffs


def _try_json_decode(value):
    """Try to JSON-decode a string value. Returns original if not decodable."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass
    return value


def _is_connection_marker(value) -> bool:
    """Check if value is a ConnectedValue/RuntimeValue marker."""
    return isinstance(value, dict) and value.get("__class__") in ("ConnectedValue", "RuntimeValue")


def _values_equivalent(a: Any, b: Any) -> bool:
    """Type-aware value comparison (e.g. "5" == 5, "true" == True)."""
    if a == b:
        return True
    try:
        if isinstance(a, str) and isinstance(b, int):
            return int(a) == b
        if isinstance(a, int) and isinstance(b, str):
            return a == int(b)
    except (ValueError, TypeError):
        pass
    try:
        if isinstance(a, str) and isinstance(b, float):
            return float(a) == b
        if isinstance(a, float) and isinstance(b, str):
            return a == float(b)
    except (ValueError, TypeError):
        pass
    if isinstance(a, str) and isinstance(b, bool):
        if b:
            return a.lower() in ("true", "yes")
        else:
            return a.lower() in ("false", "no")
    if isinstance(a, bool) and isinstance(b, str):
        return _values_equivalent(b, a)
    if a == "null" and b is None:
        return True
    if a is None and b == "null":
        return True
    return False


def _compare_step_visual(
    orig_step: NormalizedNativeStep, after_step: NormalizedNativeStep, step_path: str
) -> list[StepDiff]:
    """Compare visual/layout fields of two workflow steps."""
    diffs: list[StepDiff] = []

    orig_pos = orig_step.position
    after_pos = after_step.position
    orig_left = orig_pos.left if orig_pos else None
    orig_top = orig_pos.top if orig_pos else None
    after_left = after_pos.left if after_pos else None
    after_top = after_pos.top if after_pos else None
    if orig_left != after_left or orig_top != after_top:
        diffs.append(
            StepDiff(
                step_path=step_path,
                key_path="position",
                diff_type=DiffType.POSITION_MISMATCH,
                severity=DiffSeverity.ERROR,
                description=f"{orig_pos} != {after_pos}",
                original_value=orig_pos,
                roundtrip_value=after_pos,
            )
        )

    if orig_step.label != after_step.label:
        diffs.append(
            StepDiff(
                step_path=step_path,
                key_path="label",
                diff_type=DiffType.LABEL_MISMATCH,
                severity=DiffSeverity.ERROR,
                description=f"{orig_step.label!r} != {after_step.label!r}",
                original_value=orig_step.label,
                roundtrip_value=after_step.label,
            )
        )

    orig_ann = orig_step.annotation or ""
    after_ann = after_step.annotation or ""
    if orig_ann != after_ann:
        diffs.append(
            StepDiff(
                step_path=step_path,
                key_path="annotation",
                diff_type=DiffType.ANNOTATION_MISMATCH,
                severity=DiffSeverity.ERROR,
                description=f"{orig_ann!r} != {after_ann!r}",
                original_value=orig_ann,
                roundtrip_value=after_ann,
            )
        )

    return diffs


# -- Error classification --


def classify_error(e: Exception) -> FailureClass:
    msg = str(e)
    if "Could not resolve tool" in msg or "get_tool_info" in msg.lower():
        return FailureClass.TOOL_NOT_FOUND
    if isinstance(e, ConversionValidationFailure):
        if "not going to convert" in msg and "native" in msg:
            return FailureClass.NATIVE_VALIDATION
        if "not going to convert" in msg and "cleaned" in msg:
            return FailureClass.FORMAT2_VALIDATION
        return FailureClass.CONVERSION_ERROR
    if "Unhandled parameter type" in msg:
        return FailureClass.TYPE_NOT_HANDLED
    if isinstance(e, NotImplementedError):
        if "parameter type" in msg.lower():
            return FailureClass.TYPE_NOT_HANDLED
        return FailureClass.CONVERSION_ERROR
    if "subworkflow" in msg.lower():
        return FailureClass.SUBWORKFLOW
    if isinstance(e, (json.JSONDecodeError, KeyError)):
        return FailureClass.PARSE_ERROR
    return FailureClass.OTHER


# -- Per-step round-trip --


def roundtrip_native_step(
    step: NormalizedNativeStep,
    step_id: str,
    get_tool_info: GetToolInfo,
) -> StepResult:
    """Try to convert a single native step to format2 state."""
    tool_id = step.tool_id

    if step.is_subworkflow_step:
        return _roundtrip_subworkflow_step(step, step_id, get_tool_info)

    if not step.is_tool_step or not tool_id:
        return StepResult(step_id=step_id, tool_id=tool_id, success=True)

    try:
        convert_state_to_format2(step, get_tool_info)
        return StepResult(step_id=step_id, tool_id=tool_id, success=True)
    except Exception as e:
        return StepResult(
            step_id=step_id,
            tool_id=tool_id,
            success=False,
            failure_class=classify_error(e),
            error=str(e),
        )


def _roundtrip_subworkflow_step(
    step: NormalizedNativeStep,
    step_id: str,
    get_tool_info: GetToolInfo,
) -> StepResult:
    """Recurse into a subworkflow step, validating/converting nested tool steps."""
    subworkflow = step.subworkflow
    if not subworkflow:
        return StepResult(
            step_id=step_id,
            tool_id=None,
            success=False,
            failure_class=FailureClass.SUBWORKFLOW,
            error="Subworkflow step missing 'subworkflow' key",
        )
    nested_results = roundtrip_native_workflow(subworkflow, get_tool_info, f"subworkflow@step{step_id}")
    nested_failures = [r for r in nested_results.step_results if not r.success]
    if nested_failures:
        errors = "; ".join(f"nested step {f.step_id}: {f.error}" for f in nested_failures)
        return StepResult(
            step_id=step_id,
            tool_id=None,
            success=False,
            failure_class=nested_failures[0].failure_class,
            error=f"Subworkflow nested failures: {errors}",
        )
    return StepResult(step_id=step_id, tool_id=None, success=True)


def roundtrip_native_workflow(
    workflow: "NormalizedNativeWorkflow | dict",
    get_tool_info: GetToolInfo,
    workflow_name: str = "",
) -> RoundTripResult:
    """Round-trip a native workflow: try converting each tool step to format2."""
    if not isinstance(workflow, NormalizedNativeWorkflow):
        workflow = ensure_native(workflow)
    result = RoundTripResult(workflow_name=workflow_name, direction="native_to_format2")

    for step_id, step in workflow.steps.items():
        step_result = roundtrip_native_step(step, step_id, get_tool_info)
        result.step_results.append(step_result)

    return result


# -- Full round-trip: native → format2 → native' → compare --


def full_roundtrip_native(
    workflow_dict: dict,
    get_tool_info: GetToolInfo,
    workflow_name: str = "",
) -> tuple[RoundTripResult, list[StepDiff] | None]:
    """Full round-trip: native → format2 → native' → compare.

    Delegates to roundtrip_validate() and unwraps the result to the
    legacy (RoundTripResult, diffs) tuple for backwards compatibility.
    """
    result = roundtrip_validate(workflow_dict, get_tool_info, workflow_path=workflow_name)
    conversion_result = result.conversion_result or RoundTripResult(
        workflow_name=workflow_name, direction="native_to_format2"
    )
    if result.error:
        conversion_result.step_results.append(
            StepResult(
                step_id="reimport",
                tool_id=None,
                success=False,
                failure_class=FailureClass.REIMPORT_ERROR,
                error=result.error,
            )
        )
        return conversion_result, None
    return conversion_result, result.diffs


def _build_step_id_mapping(
    orig_workflow: NormalizedNativeWorkflow, after_workflow: NormalizedNativeWorkflow
) -> dict[str, str | None]:
    """Build a mapping from original step IDs to after step IDs using label+type matching.

    Falls back to positional ID matching when labels are absent or non-unique.
    """
    orig_steps = orig_workflow.steps
    after_steps = after_workflow.steps
    mapping: dict[str, str | None] = {}
    used_after_ids: set[str] = set()

    # First pass: match by label+type (strongest signal)
    for orig_id, orig_step in orig_steps.items():
        label = orig_step.label
        if not label:
            continue
        step_type = orig_step.type_
        for after_id, after_step in after_steps.items():
            if after_id in used_after_ids:
                continue
            if after_step.label == label and after_step.type_ == step_type:
                mapping[orig_id] = after_id
                used_after_ids.add(after_id)
                break

    # Second pass: match remaining by same ID if type matches
    for orig_id, orig_step in orig_steps.items():
        if orig_id in mapping:
            continue
        after_step = after_steps.get(orig_id)
        if after_step and orig_id not in used_after_ids:
            if after_step.type_ == orig_step.type_:
                mapping[orig_id] = orig_id
                used_after_ids.add(orig_id)

    # Third pass: match remaining by tool_id+type (handles unlabeled steps that shifted position)
    unmatched_orig = {oid: orig_steps[oid] for oid in orig_steps if oid not in mapping}
    unmatched_after = {aid: after_steps[aid] for aid in after_steps if aid not in used_after_ids}
    for orig_id, orig_step in unmatched_orig.items():
        tool_id = orig_step.tool_id
        step_type = orig_step.type_
        if not tool_id:
            continue
        candidates = [
            aid for aid, astep in unmatched_after.items() if astep.tool_id == tool_id and astep.type_ == step_type
        ]
        if len(candidates) == 1:
            mapping[orig_id] = candidates[0]
            used_after_ids.add(candidates[0])
            del unmatched_after[candidates[0]]

    # Mark unmatched as None
    for orig_id in orig_steps:
        if orig_id not in mapping:
            mapping[orig_id] = None

    return mapping


def compare_workflow_steps(
    orig_workflow: NormalizedNativeWorkflow,
    after_workflow: NormalizedNativeWorkflow,
    path_prefix: str = "",
) -> list[StepDiff]:
    """Compare steps between original and roundtripped workflows, recursing into subworkflows.

    Matches steps by label+type rather than step ID to handle gxformat2 step reordering.
    """
    all_diffs: list[StepDiff] = []
    id_mapping = _build_step_id_mapping(orig_workflow, after_workflow)

    for orig_id, orig_step in orig_workflow.steps.items():
        step_path = f"{path_prefix}step {orig_id}" if not path_prefix else f"{path_prefix}/step {orig_id}"

        after_id = id_mapping.get(orig_id)
        if after_id is None:
            all_diffs.append(
                StepDiff(
                    step_path=step_path,
                    key_path="",
                    diff_type=DiffType.STEP_MISSING,
                    severity=DiffSeverity.ERROR,
                    description="missing in roundtripped workflow",
                )
            )
            continue

        after_step = after_workflow.steps[after_id]

        if orig_step.is_subworkflow_step:
            orig_sub = orig_step.subworkflow
            after_sub = after_step.subworkflow
            if not after_sub:
                all_diffs.append(
                    StepDiff(
                        step_path=step_path,
                        key_path="subworkflow",
                        diff_type=DiffType.STEP_MISSING,
                        severity=DiffSeverity.ERROR,
                        description="subworkflow missing in roundtripped",
                    )
                )
                continue
            sub_diffs = compare_workflow_steps(orig_sub, after_sub, path_prefix=f"{step_path}:subworkflow/")
            all_diffs.extend(sub_diffs)
        elif orig_step.is_tool_step:
            all_diffs.extend(_compare_steps_with_id_mapping(orig_step, after_step, id_mapping, step_path))

        all_diffs.extend(_compare_step_visual(orig_step, after_step, step_path))

    all_diffs.extend(compare_comments(orig_workflow, after_workflow, path_prefix, id_mapping))

    return all_diffs


def _compare_steps_with_id_mapping(
    orig_step: NormalizedNativeStep,
    after_step: NormalizedNativeStep,
    id_mapping: dict[str, str | None],
    step_path: str,
) -> list[StepDiff]:
    """Compare two tool steps, remapping connection step IDs to account for reordering."""
    diffs: list[StepDiff] = []
    for key in ["tool_id", "tool_version"]:
        orig_val = getattr(orig_step, key)
        after_val = getattr(after_step, key)
        if orig_val != after_val:
            diffs.append(
                StepDiff(
                    step_path=step_path,
                    key_path=key,
                    diff_type=DiffType.VALUE_MISMATCH,
                    severity=DiffSeverity.ERROR,
                    description=f"{orig_val!r} != {after_val!r}",
                    original_value=orig_val,
                    roundtrip_value=after_val,
                )
            )

    orig_ts = orig_step.tool_state
    after_ts = after_step.tool_state
    if orig_ts and after_ts:
        diffs.extend(compare_tool_state(orig_ts, after_ts, step_path=step_path))

    diffs.extend(
        _compare_connections_with_id_mapping(
            orig_step.input_connections, after_step.input_connections, id_mapping, step_path=step_path
        )
    )

    return diffs


def _compare_connections_with_id_mapping(
    orig_connections: dict,
    after_connections: dict,
    id_mapping: dict[str, str | None],
    path: str = "",
    step_path: str = "",
) -> list[StepDiff]:
    """Compare input_connections, remapping step IDs via id_mapping before comparison."""
    reverse_map = {v: k for k, v in id_mapping.items() if v is not None}

    def _conn_id(conn) -> int:
        return conn.id if isinstance(conn, NativeInputConnection) else conn.get("id")

    def _conn_output(conn) -> str:
        return conn.output_name if isinstance(conn, NativeInputConnection) else conn.get("output_name")

    def _remap_id(conn) -> int:
        cid = _conn_id(conn)
        orig_id = reverse_map.get(str(cid))
        return int(orig_id) if orig_id is not None else cid

    diffs: list[StepDiff] = []
    all_keys = set(list(orig_connections.keys()) + list(after_connections.keys()))
    for key in sorted(all_keys):
        key_path = f"{path}.input_connections.{key}" if path else f"input_connections.{key}"
        if key not in orig_connections:
            diffs.append(
                StepDiff(
                    step_path=step_path,
                    key_path=key_path,
                    diff_type=DiffType.CONNECTION_MISMATCH,
                    severity=DiffSeverity.ERROR,
                    description="missing in original",
                )
            )
        elif key not in after_connections:
            diffs.append(
                StepDiff(
                    step_path=step_path,
                    key_path=key_path,
                    diff_type=DiffType.CONNECTION_MISMATCH,
                    severity=DiffSeverity.ERROR,
                    description="missing in roundtripped",
                )
            )
        else:
            orig_val = orig_connections[key]
            after_val = after_connections[key]
            if len(orig_val) != len(after_val):
                diffs.append(
                    StepDiff(
                        step_path=step_path,
                        key_path=key_path,
                        diff_type=DiffType.CONNECTION_MISMATCH,
                        severity=DiffSeverity.ERROR,
                        description=f"{len(orig_val)} connections vs {len(after_val)}",
                        original_value=orig_val,
                        roundtrip_value=after_val,
                    )
                )
            else:
                for i, (o, a) in enumerate(zip(orig_val, after_val)):
                    remapped_id = _remap_id(a)
                    if _conn_id(o) != remapped_id or _conn_output(o) != _conn_output(a):
                        diffs.append(
                            StepDiff(
                                step_path=step_path,
                                key_path=f"{key_path}[{i}]",
                                diff_type=DiffType.CONNECTION_MISMATCH,
                                severity=DiffSeverity.ERROR,
                                description=f"{o} != {a}",
                                original_value=o,
                                roundtrip_value=a,
                            )
                        )
    return diffs


def compare_comments(
    orig_workflow: NormalizedNativeWorkflow,
    after_workflow: NormalizedNativeWorkflow,
    path_prefix: str = "",
    id_mapping: dict[str, str | None] | None = None,
) -> list[StepDiff]:
    """Compare workflow comments between original and roundtripped workflows.

    Comments are matched by content rather than id, since reimport may renumber ids.
    child_steps references are remapped through id_mapping to account for step reordering.
    """
    orig_comments = [c.model_dump(by_alias=True) if hasattr(c, "model_dump") else c for c in orig_workflow.comments]
    after_comments = [c.model_dump(by_alias=True) if hasattr(c, "model_dump") else c for c in after_workflow.comments]
    diffs: list[StepDiff] = []
    prefix = f"{path_prefix}comments" if not path_prefix else f"{path_prefix}/comments"

    if len(orig_comments) != len(after_comments):
        diffs.append(
            StepDiff(
                step_path=prefix,
                key_path="",
                diff_type=DiffType.COMMENT_MISMATCH,
                severity=DiffSeverity.ERROR,
                description=f"{len(orig_comments)} comments vs {len(after_comments)}",
                original_value=len(orig_comments),
                roundtrip_value=len(after_comments),
            )
        )
        return diffs

    orig_normalized = sorted((_normalize_comment(c) for c in orig_comments), key=_comment_sort_key)
    after_normalized = sorted(
        (_normalize_comment(c, id_mapping=id_mapping) for c in after_comments), key=_comment_sort_key
    )

    for i, (o, a) in enumerate(zip(orig_normalized, after_normalized)):
        if o != a:
            for k in sorted(set(list(o.keys()) + list(a.keys()))):
                if o.get(k) != a.get(k):
                    diffs.append(
                        StepDiff(
                            step_path=f"{prefix}[{i}]",
                            key_path=k,
                            diff_type=DiffType.COMMENT_MISMATCH,
                            severity=DiffSeverity.ERROR,
                            description=f"{o.get(k)!r} != {a.get(k)!r}",
                            original_value=o.get(k),
                            roundtrip_value=a.get(k),
                        )
                    )

    return diffs


def _normalize_comment(comment: dict, id_mapping: dict[str, str | None] | None = None) -> dict:
    """Normalize a comment for comparison — drop id, normalize position/size, remap child_steps."""
    normalized = {k: v for k, v in comment.items() if k != "id"}
    for key in ("position", "size"):
        val = normalized.get(key)
        if isinstance(val, (list, tuple)):
            normalized[key] = list(val)
    if "child_steps" in normalized:
        if id_mapping:
            reverse_map = {int(v): int(k) for k, v in id_mapping.items() if v is not None}
            normalized["child_steps"] = sorted(
                reverse_map.get(step_id, step_id) for step_id in normalized["child_steps"]
            )
        else:
            normalized["child_steps"] = sorted(normalized["child_steps"])
    return normalized


def _comment_sort_key(comment: dict) -> tuple:
    """Sort key for comments — by type, then position, then data content."""
    pos = comment.get("position", [0, 0])
    return (comment.get("type", ""), pos[0] if pos else 0, pos[1] if pos else 0, str(comment.get("data", "")))


# -- Shared helpers for format2 export --


# -- Round-trip validation (CLI-facing) --


@dataclass
class RoundTripValidationResult:
    """Result of validating a workflow's native→format2→native round-trip."""

    workflow_path: str
    format2_dict: dict | None = None
    reimported_dict: dict | None = None
    conversion_result: RoundTripResult | None = None
    diffs: list[StepDiff] | None = None
    error: str | None = None

    @property
    def error_diffs(self) -> list[StepDiff]:
        return [d for d in (self.diffs or []) if d.severity == DiffSeverity.ERROR]

    @property
    def benign_diffs(self) -> list[StepDiff]:
        return [d for d in (self.diffs or []) if d.severity == DiffSeverity.BENIGN]

    @property
    def ok(self) -> bool:
        if self.error:
            return False
        if self.conversion_result and not self.conversion_result.success:
            return False
        if self.diffs is None:
            return False
        return len(self.error_diffs) == 0

    @property
    def status(self) -> str:
        if self.error:
            return "error"
        if self.conversion_result and not self.conversion_result.success:
            return "conversion_fail"
        if self.diffs is None:
            return "error"
        if len(self.error_diffs) > 0:
            return "roundtrip_mismatch"
        return "ok"

    @property
    def summary_line(self) -> str:
        status = self.status
        name = os.path.basename(self.workflow_path)
        n_steps = len(self.conversion_result.step_results) if self.conversion_result else 0
        if status == "ok":
            benign = len(self.benign_diffs)
            if benign:
                return f"{name}: OK ({n_steps} steps, {benign} benign diff(s))"
            return f"{name}: OK ({n_steps} steps)"
        elif status == "conversion_fail":
            assert self.conversion_result is not None
            failures = [r for r in self.conversion_result.step_results if not r.success]
            return f"{name}: CONVERSION FAIL ({len(failures)} step(s))"
        elif status == "roundtrip_mismatch":
            errors = len(self.error_diffs)
            benign = len(self.benign_diffs)
            parts = f"{errors} error(s)"
            if benign:
                parts += f", {benign} benign"
            return f"{name}: MISMATCH ({parts})"
        else:
            return f"{name}: ERROR ({self.error})"


def roundtrip_validate(
    workflow_dict: dict,
    get_tool_info: "GetToolInfo",
    workflow_path: str = "",
    strip_bookkeeping: bool = False,
    clean_stale: bool = True,
) -> RoundTripValidationResult:
    """Validate a native workflow survives native→format2→native round-trip.

    Returns a RoundTripValidationResult with the intermediate format2 dict,
    the reimported native dict, and any diffs found.

    If clean_stale is True (default), stale tool_state keys are stripped
    before conversion — these are keys left behind by older tool versions
    or Galaxy serialization bugs that would otherwise cause validation failures.
    """
    from .clean import (
        clean_stale_state,
        strip_bookkeeping_from_workflow,
    )

    result = RoundTripValidationResult(workflow_path=workflow_path)

    if strip_bookkeeping:
        strip_bookkeeping_from_workflow(workflow_dict)

    if clean_stale:
        strip_bookkeeping_from_workflow(workflow_dict)
        clean_stale_state(workflow_dict, get_tool_info)

    workflow_name = os.path.basename(workflow_path) if workflow_path else ""
    orig_model = ensure_native(workflow_dict)

    # Per-step conversion (validates each tool step can be converted)
    step_result = roundtrip_native_workflow(orig_model, get_tool_info, workflow_name)
    result.conversion_result = step_result
    if not step_result.success:
        return result

    # Forward: native → format2 with schema-aware state conversion
    native_copy = copy.deepcopy(workflow_dict)
    forward_options = ConversionOptions(state_encode_to_format2=make_convert_tool_state(get_tool_info))
    format2_model = to_format2(native_copy, options=forward_options)
    result.format2_dict = format2_model.to_dict()

    # Reverse: format2 → native with schema-aware encoding (pass model directly)
    try:
        reverse_options = ConversionOptions(state_encode_to_native=make_encode_tool_state(get_tool_info))
        native_prime = to_native(format2_model, options=reverse_options)
    except Exception as e:
        result.error = f"Reimport failed: {e}"
        return result

    result.reimported_dict = native_prime.to_dict()
    result.diffs = compare_workflow_steps(orig_model, native_prime)
    return result


# -- Options model --


class RoundTripValidateOptions(BaseModel):
    workflow_path: str
    tool_source_cache_dir: str | None = None
    verbose: bool = False
    populate_cache: bool = False
    tool_source: str = "auto"
    strip_bookkeeping: bool = False
    strict: bool = False
    output_native: str | None = None
    output_format2: str | None = None

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "RoundTripValidateOptions":
        fields = set(cls.model_fields)
        return cls(**{k: v for k, v in vars(args).items() if k in fields})


def _is_passing(result: RoundTripValidationResult, strict: bool) -> bool:
    if strict:
        return (
            result.diffs is not None
            and len(result.diffs) == 0
            and not result.error
            and (not result.conversion_result or result.conversion_result.success)
        )
    return result.ok


# -- Formatters --


def format_validation_text(
    results: list[RoundTripValidationResult],
    verbose: bool = False,
    strict: bool = False,
) -> str:
    lines = []
    ok_count = sum(1 for r in results if _is_passing(r, strict))
    fail_count = len(results) - ok_count

    for r in results:
        if strict:
            lines.append(r.summary_line)
        else:
            lines.append(r.summary_line)
        if verbose and r.status == "conversion_fail" and r.conversion_result:
            for sr in r.conversion_result.step_results:
                if not sr.success:
                    fc = sr.failure_class.value if sr.failure_class else "unknown"
                    lines.append(f"  step {sr.step_id} ({sr.tool_id}): [{fc}] {sr.error}")
        if verbose and r.diffs:
            for d in r.diffs:
                lines.append(d.format_line(verbose=verbose))
        if verbose and r.error:
            lines.append(f"  {r.error}")

    lines.append("---")
    ok_clean = sum(1 for r in results if _is_passing(r, strict) and not r.benign_diffs)
    ok_benign = ok_count - ok_clean
    if ok_benign and not strict:
        ok_label = f"{ok_count} OK ({ok_clean} clean, {ok_benign} with benign diffs)"
    else:
        ok_label = f"{ok_count} OK"
    lines.append(f"Summary: {ok_label}, {fail_count} FAIL (total {len(results)} workflows)")
    return "\n".join(lines)


# -- Entry point --


def run_roundtrip_validate(options: RoundTripValidateOptions) -> int:
    """Run round-trip validation pipeline. Returns exit code."""
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

    is_dir = os.path.isdir(options.workflow_path)

    if is_dir:
        return _run_tree_validation(options, tool_info)
    else:
        return _run_single_validation(options, tool_info)


def _run_single_validation(options: "RoundTripValidateOptions", tool_info) -> int:
    from .validation import _format
    from .workflow_tools import load_workflow

    workflow = load_workflow(options.workflow_path)
    if _format(workflow) != "native":
        print("Error: round-trip validation requires a native .ga workflow", file=sys.stderr)
        return 1

    result = roundtrip_validate(
        workflow,
        tool_info,
        workflow_path=options.workflow_path,
        strip_bookkeeping=options.strip_bookkeeping,
    )

    # Write intermediate artifacts if requested
    if options.output_format2 and result.format2_dict:
        _write_json(result.format2_dict, options.output_format2)
        print(f"Format2 written to {options.output_format2}", file=sys.stderr)

    if options.output_native and result.reimported_dict:
        _write_json(result.reimported_dict, options.output_native)
        print(f"Reimported native written to {options.output_native}", file=sys.stderr)

    print(format_validation_text([result], verbose=options.verbose, strict=options.strict))
    return 0 if _is_passing(result, options.strict) else 1


def _run_tree_validation(options: "RoundTripValidateOptions", tool_info) -> int:
    from .validation import _format
    from .workflow_tree import (
        discover_workflows,
        load_workflow_safe,
    )

    workflows = discover_workflows(options.workflow_path, include_format2=False)
    results: list[RoundTripValidationResult] = []

    for info in workflows:
        wf_dict = load_workflow_safe(info)
        if wf_dict is None:
            results.append(
                RoundTripValidationResult(
                    workflow_path=info.path,
                    error="Failed to load workflow",
                )
            )
            continue

        if _format(wf_dict) != "native":
            continue

        result = roundtrip_validate(
            wf_dict,
            tool_info,
            workflow_path=info.relative_path,
            strip_bookkeeping=options.strip_bookkeeping,
        )
        results.append(result)

    print(format_validation_text(results, verbose=options.verbose, strict=options.strict))

    has_failures = any(not _is_passing(r, options.strict) for r in results)
    return 1 if has_failures else 0


def _write_json(data: dict, path: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
        f.write("\n")
