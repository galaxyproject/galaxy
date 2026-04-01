"""JSON Schema-based workflow validation.

Two-level validation using exported Pydantic JSON Schemas and the jsonschema library,
proving the same schemas work identically in Python and TypeScript consumers.

Level 1 (structural): validates workflow dict against gxformat2 GalaxyWorkflow schema.
Level 2 (per-step tool state): validates each step's state against WorkflowStepToolState schema.
"""

import copy
import json
import logging
import os
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

from jsonschema import Draft202012Validator
from typing_extensions import Literal

from ._state_merge import inject_connections_into_state
from ._types import GetToolInfo
from ._util import (
    step_input_connections,
    step_tool_state,
)

log = logging.getLogger(__name__)

_structural_schema_cache: Dict[bool, Draft202012Validator] = {}


@dataclass
class JsonSchemaValidationError:
    path: str
    message: str
    schema_path: str


@dataclass
class JsonSchemaStepResult:
    step: str
    tool_id: Optional[str]
    errors: List[JsonSchemaValidationError]
    status: Literal["ok", "fail", "skip"]


@dataclass
class JsonSchemaValidationResult:
    structural_errors: List[JsonSchemaValidationError] = field(default_factory=list)
    step_results: List[JsonSchemaStepResult] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.structural_errors and all(s.status != "fail" for s in self.step_results)


def _get_structural_validator(strict: bool = False) -> Draft202012Validator:
    if strict not in _structural_schema_cache:
        from gxformat2.schema.json_schema import workflow_json_schema

        schema = workflow_json_schema(strict=strict)
        _structural_schema_cache[strict] = Draft202012Validator(schema)
    return _structural_schema_cache[strict]


def _convert_errors(errors) -> List[JsonSchemaValidationError]:
    result = []
    for error in errors:
        path = "/".join(str(p) for p in error.absolute_path) if error.absolute_path else ""
        schema_path = "/".join(str(p) for p in error.absolute_schema_path) if error.absolute_schema_path else ""
        result.append(
            JsonSchemaValidationError(
                path=path,
                message=error.message,
                schema_path=schema_path,
            )
        )
    return result


def validate_structural_json_schema(
    workflow_dict: Dict[str, Any],
    *,
    strict: bool = False,
) -> List[JsonSchemaValidationError]:
    """Validate a format2 workflow dict against GalaxyWorkflow JSON Schema.

    Returns list of validation errors (empty = valid).
    """
    validator = _get_structural_validator(strict=strict)
    errors = sorted(validator.iter_errors(workflow_dict), key=lambda e: list(e.absolute_path))
    return _convert_errors(errors)


def _build_tool_state_validator(
    tool_id: str,
    tool_version: Optional[str],
    get_tool_info: GetToolInfo,
    representation: str = "workflow_step",
) -> Optional[Draft202012Validator]:
    """Build a JSON Schema validator for a tool's state."""
    from galaxy.tool_util.parameters.json import to_json_schema
    from galaxy.tool_util.parameters.state import (
        WorkflowStepLinkedToolState,
        WorkflowStepNativeToolState,
        WorkflowStepToolState,
    )

    parsed_tool = get_tool_info.get_tool_info(tool_id, tool_version)
    if parsed_tool is None:
        return None

    _state_cls_map = {
        "workflow_step": WorkflowStepToolState,
        "workflow_step_linked": WorkflowStepLinkedToolState,
        "workflow_step_native": WorkflowStepNativeToolState,
    }
    state_cls = _state_cls_map.get(representation, WorkflowStepToolState)
    model = state_cls.parameter_model_for(list(parsed_tool.inputs))
    schema = to_json_schema(model)
    return Draft202012Validator(schema)


def _load_tool_state_validator_from_dir(
    tool_id: str,
    tool_version: Optional[str],
    schema_dir: str,
) -> Optional[Draft202012Validator]:
    """Load a pre-exported tool state JSON Schema from a directory.

    Directory layout: {schema_dir}/{safe_tool_id}/{version}.json
    where safe_tool_id replaces '/' with '~' to match TRS ID convention.
    """
    safe_id = tool_id.replace("/", "~")
    version = tool_version or "_default_"
    tool_dir = os.path.join(schema_dir, safe_id)
    path = os.path.join(tool_dir, f"{version}.json")
    if not os.path.exists(path):
        # Try _default_ version as fallback
        path = os.path.join(tool_dir, "_default_.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        schema = json.load(f)
    return Draft202012Validator(schema)


def validate_workflow_json_schema(
    workflow_dict: Dict[str, Any],
    get_tool_info: Optional[GetToolInfo] = None,
    tool_schema_dir: Optional[str] = None,
    *,
    strict: bool = False,
    representation: str = "workflow_step",
) -> JsonSchemaValidationResult:
    """Two-level JSON Schema validation of a format2 workflow.

    Level 1: structural validation against GalaxyWorkflow schema.
    Level 2: per-step tool state validation (requires get_tool_info or tool_schema_dir).

    If structural validation fails, step validation is skipped.
    """
    result = JsonSchemaValidationResult()

    # Level 1: structural
    result.structural_errors = validate_structural_json_schema(workflow_dict, strict=strict)
    if result.structural_errors:
        return result

    # Level 2: per-step tool state
    if get_tool_info is None and tool_schema_dir is None:
        return result

    steps = workflow_dict.get("steps", [])
    if isinstance(steps, dict):
        step_items = list(steps.items())
    elif isinstance(steps, list):
        step_items = [(str(i), step) for i, step in enumerate(steps)]
    else:
        return result

    _validator_cache: Dict[str, Draft202012Validator] = {}

    for step_key, step in step_items:
        if not isinstance(step, dict):
            continue

        tool_id = step.get("tool_id")
        if not tool_id:
            continue

        tool_version = step.get("tool_version")
        state = step.get("state")
        if state is None:
            result.step_results.append(
                JsonSchemaStepResult(
                    step=step_key,
                    tool_id=tool_id,
                    errors=[],
                    status="skip",
                )
            )
            continue

        cache_key = f"{tool_id}@{tool_version}"
        if cache_key not in _validator_cache:
            validator = None
            if tool_schema_dir:
                validator = _load_tool_state_validator_from_dir(tool_id, tool_version, tool_schema_dir)
            if validator is None and get_tool_info is not None:
                try:
                    validator = _build_tool_state_validator(
                        tool_id,
                        tool_version,
                        get_tool_info,
                        representation=representation,
                    )
                except Exception:
                    log.debug(f"Failed to build validator for {tool_id}", exc_info=True)
            _validator_cache[cache_key] = validator

        validator = _validator_cache.get(cache_key)
        if validator is None:
            result.step_results.append(
                JsonSchemaStepResult(
                    step=step_key,
                    tool_id=tool_id,
                    errors=[],
                    status="skip",
                )
            )
            continue

        errors = sorted(validator.iter_errors(state), key=lambda e: list(e.absolute_path))
        step_errors = _convert_errors(errors)
        result.step_results.append(
            JsonSchemaStepResult(
                step=step_key,
                tool_id=tool_id,
                errors=step_errors,
                status="fail" if step_errors else "ok",
            )
        )

    return result


def validate_native_workflow_json_schema(
    workflow_dict: Dict[str, Any],
    get_tool_info: GetToolInfo,
    tool_schema_dir: Optional[str] = None,
) -> JsonSchemaValidationResult:
    """JSON Schema validation of a native .ga workflow's per-step tool state.

    No structural validation (no native structural schema exists).
    Per-step: inject connections, then validate against
    WorkflowStepNativeToolState JSON Schema.
    """
    from .legacy_parameters import (
        ReplacementClassification,
        scan_native_state,
    )

    result = JsonSchemaValidationResult()

    steps = workflow_dict.get("steps", {})
    if not isinstance(steps, dict):
        return result

    _validator_cache: Dict[str, Optional[Draft202012Validator]] = {}
    _parsed_tool_cache: Dict[str, Any] = {}

    for step_key, step_def in sorted(steps.items(), key=lambda x: int(x[0])):
        if not isinstance(step_def, dict):
            continue

        if step_def.get("type") == "subworkflow" and "subworkflow" in step_def:
            sub_result = validate_native_workflow_json_schema(
                step_def["subworkflow"],
                get_tool_info,
                tool_schema_dir=tool_schema_dir,
            )
            result.step_results.extend(sub_result.step_results)
            continue

        tool_id = step_def.get("tool_id")
        if not tool_id:
            continue

        tool_version = step_def.get("tool_version")
        cache_key = f"{tool_id}@{tool_version}"

        # Resolve parsed tool (needed for connection injection)
        if cache_key not in _parsed_tool_cache:
            _parsed_tool_cache[cache_key] = get_tool_info.get_tool_info(tool_id, tool_version)
        parsed_tool = _parsed_tool_cache[cache_key]

        if parsed_tool is None:
            result.step_results.append(JsonSchemaStepResult(step=step_key, tool_id=tool_id, errors=[], status="skip"))
            continue

        # Prepare state: decode → inject connections
        tool_state = step_tool_state(step_def)
        input_connections = step_input_connections(step_def)

        scan = scan_native_state(list(parsed_tool.inputs), tool_state, input_connections)
        if scan.classification == ReplacementClassification.YES:
            result.step_results.append(JsonSchemaStepResult(step=step_key, tool_id=tool_id, errors=[], status="skip"))
            continue

        state = copy.deepcopy(tool_state)

        connections = {key: (val if isinstance(val, list) else [val]) for key, val in input_connections.items()}
        inject_connections_into_state(list(parsed_tool.inputs), state, connections)

        # Build/cache validator
        if cache_key not in _validator_cache:
            validator = None
            if tool_schema_dir:
                validator = _load_tool_state_validator_from_dir(tool_id, tool_version, tool_schema_dir)
            if validator is None:
                try:
                    validator = _build_tool_state_validator(
                        tool_id, tool_version, get_tool_info, representation="workflow_step_native"
                    )
                except Exception:
                    log.debug(f"Failed to build native validator for {tool_id}", exc_info=True)
            _validator_cache[cache_key] = validator

        validator = _validator_cache.get(cache_key)
        if validator is None:
            result.step_results.append(JsonSchemaStepResult(step=step_key, tool_id=tool_id, errors=[], status="skip"))
            continue

        errors = sorted(validator.iter_errors(state), key=lambda e: list(e.absolute_path))
        step_errors = _convert_errors(errors)
        result.step_results.append(
            JsonSchemaStepResult(
                step=step_key,
                tool_id=tool_id,
                errors=step_errors,
                status="fail" if step_errors else "ok",
            )
        )

    return result
