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
)

from jsonschema import Draft202012Validator
from typing import Literal

from ._inline_tool import resolve_for_step
from ._state_merge import inject_connections_into_state
from ._types import GetToolInfo
from ._util import (
    step_input_connections,
    step_is_inline_tool,
    step_tool_state,
)

log = logging.getLogger(__name__)

_structural_schema_cache: dict[bool, Draft202012Validator] = {}
_native_structural_schema_cache: dict[bool, Draft202012Validator] = {}


@dataclass
class JsonSchemaValidationError:
    path: str
    message: str
    schema_path: str


@dataclass
class JsonSchemaStepResult:
    step: str
    tool_id: str | None
    errors: list[JsonSchemaValidationError]
    status: Literal["ok", "fail", "skip"]
    skip_reason: str | None = None


@dataclass
class JsonSchemaValidationResult:
    structural_errors: list[JsonSchemaValidationError] = field(default_factory=list)
    step_results: list[JsonSchemaStepResult] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.structural_errors and all(s.status != "fail" for s in self.step_results)


def _get_structural_validator(strict: bool = False) -> Draft202012Validator:
    if strict not in _structural_schema_cache:
        from gxformat2.schema.json_schema import workflow_json_schema

        schema = workflow_json_schema(strict=strict)
        _structural_schema_cache[strict] = Draft202012Validator(schema)
    return _structural_schema_cache[strict]


def _get_native_structural_validator(strict: bool = False) -> Draft202012Validator:
    if strict not in _native_structural_schema_cache:
        from gxformat2.schema.json_schema import native_workflow_json_schema

        schema = native_workflow_json_schema(strict=strict)
        _native_structural_schema_cache[strict] = Draft202012Validator(schema)
    return _native_structural_schema_cache[strict]


def _convert_errors(errors) -> list[JsonSchemaValidationError]:
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
    workflow_dict: dict[str, Any],
    *,
    strict: bool = False,
) -> list[JsonSchemaValidationError]:
    """Validate a format2 workflow dict against GalaxyWorkflow JSON Schema.

    Returns list of validation errors (empty = valid).
    """
    validator = _get_structural_validator(strict=strict)
    errors = sorted(validator.iter_errors(workflow_dict), key=lambda e: list(e.absolute_path))
    return _convert_errors(errors)


def _build_tool_state_validator(
    tool_id: str,
    tool_version: str | None,
    get_tool_info: GetToolInfo,
    representation: str = "workflow_step",
) -> Draft202012Validator | None:
    """Build a JSON Schema validator for a tool's state."""
    parsed_tool = get_tool_info.get_tool_info(tool_id, tool_version)
    if parsed_tool is None:
        return None
    return _build_tool_state_validator_from_parsed_tool(parsed_tool, representation=representation)


def _build_tool_state_validator_from_parsed_tool(
    parsed_tool, representation: str = "workflow_step"
) -> Draft202012Validator:
    """Build a JSON Schema validator from an already-resolved ParsedTool.

    Lets inline-UDT callers reuse the parsed tool from ``resolve_for_step``
    without round-tripping through a :class:`GetToolInfo` cache.
    """
    from galaxy.tool_util.parameters.json import to_json_schema
    from galaxy.tool_util.parameters.state import (
        WorkflowStepLinkedToolState,
        WorkflowStepNativeToolState,
        WorkflowStepToolState,
    )

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
    tool_version: str | None,
    schema_dir: str,
    *,
    step_path: str | None = None,
) -> Draft202012Validator | None:
    """Load a pre-exported tool state JSON Schema from a directory.

    Two naming schemes coexist on disk:

    * **Per-step (inline)**: ``{schema_dir}/{safe_tool_id}.{version}.{step_path}.schema.json``.
      Used by ``galaxy-tool-cache embedded-schema`` for inline UDT steps —
      step path guarantees uniqueness when the same ``(tool_id, version)``
      is embedded twice in the same workflow.
    * **Cacheable**: ``{schema_dir}/{safe_tool_id}/{version}.json``. Used by
      ``galaxy-tool-cache schema`` for ToolShed tools shared across
      workflows.

    Inline steps consult per-step first, then fall through to cacheable;
    non-inline steps (``step_path=None``) only consult cacheable.
    """
    safe_id = tool_id.replace("/", "~")
    version = tool_version or "_default_"

    # Per-step inline lookup (preferred for inline UDT steps).
    if step_path is not None:
        inline_path = os.path.join(schema_dir, f"{safe_id}.{version}.{step_path}.schema.json")
        if os.path.exists(inline_path):
            with open(inline_path) as f:
                schema = json.load(f)
            return Draft202012Validator(schema)

    # Cacheable fallback.
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
    workflow_dict: dict[str, Any],
    get_tool_info: GetToolInfo | None = None,
    tool_schema_dir: str | None = None,
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

    _validator_cache: dict[str, Draft202012Validator] = {}

    for step_key, step in step_items:
        if not isinstance(step, dict):
            continue

        tool_id = step.get("tool_id")
        is_inline = step_is_inline_tool(step)
        if not tool_id and not is_inline:
            continue

        tool_version = step.get("tool_version")
        # State shape selects the schema: a schema-aware ``state`` block
        # validates against *representation*; a verbatim native ``tool_state``
        # block validates against the native representation (parity with the
        # Pydantic path, where tool_state routes to WorkflowStepNativeToolState).
        state = step.get("state")
        tool_state = step.get("tool_state")
        if state is not None:
            state_to_validate = state
            state_representation = representation
        elif tool_state:
            state_to_validate = tool_state
            state_representation = "workflow_step_native"
        else:
            result.step_results.append(
                JsonSchemaStepResult(
                    step=step_key,
                    tool_id=tool_id,
                    errors=[],
                    status="skip",
                )
            )
            continue

        # Resolve through the inline-aware resolver. For format2, ``step``
        # is a raw dict here; resolve_for_step's StepLike accepts it.
        parsed_tool = None
        if get_tool_info is not None:
            parsed_tool = resolve_for_step(get_tool_info, step)

        effective_tool_id = tool_id or (parsed_tool.id if parsed_tool else None)
        effective_version = tool_version or (parsed_tool.version if parsed_tool else None)

        cache_key = f"{effective_tool_id}@{effective_version}@{state_representation}@{step_key if is_inline else '-'}"
        if cache_key not in _validator_cache:
            validator = None
            # Pre-exported dir schemas are the default ``representation`` only;
            # a native tool_state block must build from the parsed tool.
            if tool_schema_dir and effective_tool_id is not None and state_representation == representation:
                step_path = step_key if is_inline else None
                validator = _load_tool_state_validator_from_dir(
                    effective_tool_id, effective_version, tool_schema_dir, step_path=step_path
                )
            if validator is None and parsed_tool is not None:
                try:
                    validator = _build_tool_state_validator_from_parsed_tool(
                        parsed_tool, representation=state_representation
                    )
                except Exception:
                    log.debug(f"Failed to build validator for {effective_tool_id}", exc_info=True)
            _validator_cache[cache_key] = validator

        validator = _validator_cache.get(cache_key)
        if validator is None:
            result.step_results.append(
                JsonSchemaStepResult(
                    step=step_key,
                    tool_id=effective_tool_id,
                    errors=[],
                    status="skip",
                )
            )
            continue

        errors = sorted(validator.iter_errors(state_to_validate), key=lambda e: list(e.absolute_path))
        step_errors = _convert_errors(errors)
        result.step_results.append(
            JsonSchemaStepResult(
                step=step_key,
                tool_id=effective_tool_id,
                errors=step_errors,
                status="fail" if step_errors else "ok",
            )
        )

    return result


def validate_native_structural_json_schema(
    workflow_dict: dict[str, Any],
    *,
    strict: bool = False,
) -> list[JsonSchemaValidationError]:
    """Validate a native .ga workflow dict against NativeGalaxyWorkflow JSON Schema.

    Returns list of validation errors (empty = valid).
    """
    validator = _get_native_structural_validator(strict=strict)
    errors = sorted(validator.iter_errors(workflow_dict), key=lambda e: list(e.absolute_path))
    return _convert_errors(errors)


def validate_native_workflow_json_schema(
    workflow_dict: dict[str, Any],
    get_tool_info: GetToolInfo,
    tool_schema_dir: str | None = None,
) -> JsonSchemaValidationResult:
    """Two-level JSON Schema validation of a native .ga workflow.

    Level 1: structural validation against NativeGalaxyWorkflow schema.
    Level 2: per-step tool state validation (inject connections, then validate
    against WorkflowStepNativeToolState JSON Schema).
    """
    from .legacy_parameters import (
        ReplacementClassification,
        scan_native_state,
    )

    result = JsonSchemaValidationResult()

    # Level 1: structural
    result.structural_errors = validate_native_structural_json_schema(workflow_dict)
    if result.structural_errors:
        return result

    steps = workflow_dict.get("steps", {})
    if not isinstance(steps, dict):
        return result

    _validator_cache: dict[str, Draft202012Validator | None] = {}
    _parsed_tool_cache: dict[str, Any] = {}

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
        is_inline = step_is_inline_tool(step_def)
        if not tool_id and not is_inline:
            continue

        # Resolve parsed tool through the shared resolver — picks up inline
        # UDTs locally without touching the network.
        parsed_tool = resolve_for_step(get_tool_info, step_def)
        if parsed_tool is None:
            result.step_results.append(
                JsonSchemaStepResult(
                    step=step_key, tool_id=tool_id, errors=[], status="skip", skip_reason="tool_not_found"
                )
            )
            continue

        # Inline UDT steps clear ``tool_id`` on export; use the parsed
        # tool's id for cache key + diagnostics labelling.
        effective_tool_id = tool_id or parsed_tool.id
        tool_version = step_def.get("tool_version") or parsed_tool.version
        cache_key = f"{effective_tool_id}@{tool_version}@{step_key if is_inline else '-'}"
        _parsed_tool_cache[cache_key] = parsed_tool

        # Prepare state: decode → inject connections
        tool_state = step_tool_state(step_def)
        input_connections = step_input_connections(step_def)

        scan = scan_native_state(list(parsed_tool.inputs), tool_state, input_connections)
        if scan.classification == ReplacementClassification.YES:
            result.step_results.append(
                JsonSchemaStepResult(
                    step=step_key,
                    tool_id=effective_tool_id,
                    errors=[],
                    status="skip",
                    skip_reason="replacement_params",
                )
            )
            continue

        state = copy.deepcopy(tool_state)

        connections: dict[str, object] = {
            key: (val if isinstance(val, list) else [val]) for key, val in input_connections.items()
        }
        inject_connections_into_state(list(parsed_tool.inputs), state, connections)

        # Build/cache validator
        if cache_key not in _validator_cache:
            validator = None
            if tool_schema_dir:
                step_path = step_key if is_inline else None
                validator = _load_tool_state_validator_from_dir(
                    effective_tool_id, tool_version, tool_schema_dir, step_path=step_path
                )
            if validator is None:
                try:
                    validator = _build_tool_state_validator_from_parsed_tool(
                        parsed_tool, representation="workflow_step_native"
                    )
                except Exception:
                    log.debug(f"Failed to build native validator for {effective_tool_id}", exc_info=True)
            _validator_cache[cache_key] = validator

        validator = _validator_cache.get(cache_key)
        if validator is None:
            result.step_results.append(
                JsonSchemaStepResult(step=step_key, tool_id=effective_tool_id, errors=[], status="skip")
            )
            continue

        errors = sorted(validator.iter_errors(state), key=lambda e: list(e.absolute_path))
        step_errors = _convert_errors(errors)
        result.step_results.append(
            JsonSchemaStepResult(
                step=step_key,
                tool_id=effective_tool_id,
                errors=step_errors,
                status="fail" if step_errors else "ok",
            )
        )

    return result
