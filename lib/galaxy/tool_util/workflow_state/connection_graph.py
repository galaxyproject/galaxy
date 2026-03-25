"""Workflow graph builder for connection validation.

Extracts typed input/output/connection information from a workflow dict
and produces a graph of ResolvedSteps in topological order.
"""

import logging
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from gxformat2.normalized import (
    normalized_native,
    NormalizedNativeStep,
    NormalizedNativeWorkflow,
)
from gxformat2.schema.native import NativeStepType

from galaxy.tool_util.parameters import ToolParameterT
from galaxy.tool_util_models.tool_outputs import (
    ToolOutputBoolean,
    ToolOutputCollection,
    ToolOutputDataset,
    ToolOutputFloat,
    ToolOutputInteger,
    ToolOutputText,
)
from galaxy.util.topsort import topsort
from ._types import GetToolInfo
from ._util import step_tool_state

log = logging.getLogger(__name__)


@dataclass
class ConnectionRef:
    """Reference to a source step output."""

    source_step: str
    output_name: str
    input_subworkflow_step_id: Optional[str] = None


@dataclass
class ResolvedInput:
    """A typed input on a step, from the tool definition."""

    name: str
    state_path: str
    type: str  # "data", "collection", "text", "integer", "float", "boolean", "color"
    collection_type: Optional[str] = None
    multiple: bool = False
    optional: bool = False
    extensions: List[str] = field(default_factory=lambda: ["data"])


@dataclass
class ResolvedOutput:
    """A typed output on a step, from the tool definition."""

    name: str
    type: str  # "data", "collection", "text", "integer", "float", "boolean"
    collection_type: Optional[str] = None
    collection_type_source: Optional[str] = None
    collection_type_from_rules: Optional[str] = None
    structured_like: Optional[str] = None
    format: Optional[str] = None
    format_source: Optional[str] = None


@dataclass
class ResolvedStep:
    """A workflow step with resolved input/output type information."""

    step_id: str
    tool_id: Optional[str]
    step_type: str
    inputs: Dict[str, ResolvedInput] = field(default_factory=dict)
    outputs: Dict[str, ResolvedOutput] = field(default_factory=dict)
    connections: Dict[str, List[ConnectionRef]] = field(default_factory=dict)
    declared_collection_type: Optional[str] = None
    inner_graph: Optional["WorkflowGraph"] = None
    subworkflow_output_map: Dict[str, Tuple[str, str]] = field(default_factory=dict)


@dataclass
class WorkflowGraph:
    """Typed workflow graph with steps in topological order."""

    steps: Dict[str, ResolvedStep] = field(default_factory=dict)
    sorted_step_ids: List[str] = field(default_factory=list)


def build_workflow_graph(
    workflow: Union[NormalizedNativeWorkflow, dict],
    get_tool_info: GetToolInfo,
) -> WorkflowGraph:
    """Build a typed workflow graph from a native workflow dict or model."""
    if isinstance(workflow, dict):
        workflow = normalized_native(workflow)

    steps: Dict[str, ResolvedStep] = {}
    for step_id_str, step in workflow.steps.items():
        if step.type_ in (
            NativeStepType.data_input,
            NativeStepType.data_collection_input,
            NativeStepType.parameter_input,
        ):
            resolved = _resolve_input_step(step_id_str, step)
        elif step.type_ == NativeStepType.tool:
            resolved = _resolve_tool_step(step_id_str, step, get_tool_info)
        elif step.type_ == NativeStepType.subworkflow:
            resolved = _resolve_subworkflow_step(step_id_str, step, get_tool_info)
        elif step.type_ == NativeStepType.pause:
            resolved = ResolvedStep(step_id=step_id_str, tool_id=None, step_type="pause")
        else:
            resolved = ResolvedStep(step_id=step_id_str, tool_id=None, step_type=step.type_.value)

        steps[step_id_str] = resolved

    sorted_ids = _topological_sort(steps)
    return WorkflowGraph(steps=steps, sorted_step_ids=sorted_ids)


def _resolve_input_step(step_id: str, step: NormalizedNativeStep) -> ResolvedStep:
    """Resolve a data_input, data_collection_input, or parameter_input step."""
    step_type = step.type_.value
    tool_state = step.tool_state

    if step.type_ == NativeStepType.data_input:
        output = ResolvedOutput(name="output", type="data")
        return ResolvedStep(
            step_id=step_id,
            tool_id=None,
            step_type=step_type,
            outputs={"output": output},
        )

    elif step.type_ == NativeStepType.data_collection_input:
        collection_type = tool_state.get("collection_type", "list")
        output = ResolvedOutput(
            name="output",
            type="collection",
            collection_type=collection_type,
        )
        return ResolvedStep(
            step_id=step_id,
            tool_id=None,
            step_type=step_type,
            outputs={"output": output},
            declared_collection_type=collection_type,
        )

    else:  # parameter_input
        param_type = tool_state.get("parameter_type", "text")
        output = ResolvedOutput(name="output", type=param_type)
        return ResolvedStep(
            step_id=step_id,
            tool_id=None,
            step_type=step_type,
            outputs={"output": output},
        )


def _resolve_tool_step(
    step_id: str,
    step: NormalizedNativeStep,
    get_tool_info: GetToolInfo,
) -> ResolvedStep:
    """Resolve a tool step using its ParsedTool definition."""
    connections = _parse_connections(step)

    inputs: Dict[str, ResolvedInput] = {}
    outputs: Dict[str, ResolvedOutput] = {}

    if step.tool_id:
        try:
            parsed_tool = get_tool_info.get_tool_info(step.tool_id, step.tool_version)
            if parsed_tool:
                tool_state = step_tool_state(step)
                inputs = _collect_inputs(parsed_tool.inputs, tool_state)
                outputs = _collect_outputs(parsed_tool.outputs)
                _resolve_rules_collection_types(outputs, tool_state)
        except (KeyError, ValueError) as e:
            log.debug("Could not resolve tool %s: %s", step.tool_id, e)
        except Exception:
            log.warning("Unexpected error resolving tool %s", step.tool_id, exc_info=True)

    if step.when and "when" in connections:
        inputs["when"] = ResolvedInput(name="when", state_path="when", type="boolean")

    return ResolvedStep(
        step_id=step_id,
        tool_id=step.tool_id,
        step_type="tool",
        inputs=inputs,
        outputs=outputs,
        connections=connections,
    )


def _resolve_subworkflow_step(step_id: str, step: NormalizedNativeStep, get_tool_info: GetToolInfo) -> ResolvedStep:
    """Resolve a subworkflow step by recursively building the inner workflow graph."""
    connections = _parse_connections(step)

    inner_graph = None
    output_map: Dict[str, Tuple[str, str]] = {}
    inputs: Dict[str, ResolvedInput] = {}

    if step.subworkflow is not None:
        try:
            inner_graph = build_workflow_graph(step.subworkflow, get_tool_info)
            output_map = _build_subworkflow_output_map(step.subworkflow)
            inputs = _synthesize_subworkflow_inputs(connections, inner_graph)
        except Exception:
            log.warning("Failed to build inner graph for subworkflow step %s", step_id, exc_info=True)

    if step.when and "when" in connections:
        inputs["when"] = ResolvedInput(name="when", state_path="when", type="boolean")

    return ResolvedStep(
        step_id=step_id,
        tool_id=None,
        step_type="subworkflow",
        inputs=inputs,
        connections=connections,
        inner_graph=inner_graph,
        subworkflow_output_map=output_map,
    )


def _synthesize_subworkflow_inputs(
    connections: Dict[str, List[ConnectionRef]],
    inner_graph: WorkflowGraph,
) -> Dict[str, ResolvedInput]:
    """Create ResolvedInputs for a subworkflow step from inner graph input steps."""
    inputs: Dict[str, ResolvedInput] = {}
    for input_path, conn_refs in connections.items():
        for ref in conn_refs:
            inner_id = ref.input_subworkflow_step_id
            if inner_id and inner_id in inner_graph.steps:
                inner_step = inner_graph.steps[inner_id]
                inputs[input_path] = _input_from_inner_step(inner_step, input_path)
    return inputs


def _input_from_inner_step(inner_step: ResolvedStep, input_path: str) -> ResolvedInput:
    """Create a ResolvedInput based on an inner workflow input step."""
    if inner_step.step_type == "data_collection_input":
        return ResolvedInput(
            name=input_path,
            state_path=input_path,
            type="collection",
            collection_type=inner_step.declared_collection_type,
        )
    elif inner_step.step_type == "data_input":
        return ResolvedInput(name=input_path, state_path=input_path, type="data")
    elif inner_step.step_type == "parameter_input":
        inner_output = inner_step.outputs.get("output")
        param_type = inner_output.type if inner_output else "text"
        return ResolvedInput(name=input_path, state_path=input_path, type=param_type)
    else:
        return ResolvedInput(name=input_path, state_path=input_path, type="data")


def _build_subworkflow_output_map(subworkflow: NormalizedNativeWorkflow) -> Dict[str, Tuple[str, str]]:
    """Build mapping from external output name to (inner_step_id, inner_output_name).

    Scans inner workflow steps for workflow_outputs declarations.
    The label (or fallback "{step_id}:{output_name}") becomes the externally visible name.
    """
    output_map: Dict[str, Tuple[str, str]] = {}
    for step_id, step in subworkflow.steps.items():
        for wo in step.workflow_outputs:
            if not wo.output_name:
                continue
            external_name = wo.label or f"{step_id}:{wo.output_name}"
            output_map[external_name] = (str(step_id), wo.output_name)
    return output_map


def _parse_connections(step: NormalizedNativeStep) -> Dict[str, List[ConnectionRef]]:
    """Parse input_connections from a normalized step."""
    result: Dict[str, List[ConnectionRef]] = {}
    for state_path, conns in step.input_connections.items():
        refs = []
        for conn in conns:
            subwf_step_id = conn.input_subworkflow_step_id
            refs.append(
                ConnectionRef(
                    source_step=str(conn.id),
                    output_name=conn.output_name,
                    input_subworkflow_step_id=str(subwf_step_id) if subwf_step_id is not None else None,
                )
            )
        if refs:
            result[state_path] = refs
    return result


_PARAMETER_INPUT_TYPES = frozenset({"gx_text", "gx_integer", "gx_float", "gx_boolean", "gx_color", "gx_select"})


def _collect_inputs(
    params: List[ToolParameterT],
    tool_state: Optional[dict] = None,
    prefix: Optional[str] = None,
) -> Dict[str, ResolvedInput]:
    """Walk parameter tree and collect typed inputs with state paths."""
    result: Dict[str, ResolvedInput] = {}

    for param in params:
        state_path = param.name if prefix is None else f"{prefix}|{param.name}"

        if param.parameter_type == "gx_data":
            result[state_path] = ResolvedInput(
                name=param.name,
                state_path=state_path,
                type="data",
                multiple=getattr(param, "multiple", False),
                optional=getattr(param, "optional", False),
                extensions=getattr(param, "extensions", ["data"]),
            )

        elif param.parameter_type == "gx_data_collection":
            result[state_path] = ResolvedInput(
                name=param.name,
                state_path=state_path,
                type="collection",
                collection_type=getattr(param, "collection_type", None),
                optional=getattr(param, "optional", False),
                extensions=getattr(param, "extensions", ["data"]),
            )

        elif param.parameter_type in _PARAMETER_INPUT_TYPES:
            # Strip "gx_" prefix: "gx_text" -> "text", "gx_integer" -> "integer", etc.
            param_type = param.parameter_type[3:]
            result[state_path] = ResolvedInput(
                name=param.name,
                state_path=state_path,
                type=param_type,
            )

        elif param.parameter_type == "gx_conditional":
            cond_state = tool_state.get(param.name, {}) if tool_state else {}
            if not isinstance(cond_state, dict):
                cond_state = {}

            active_case = cond_state.get("__current_case__")
            whens = getattr(param, "whens", [])

            if active_case is not None:
                try:
                    case_idx = int(active_case)
                    if 0 <= case_idx < len(whens):
                        result.update(_collect_inputs(whens[case_idx].parameters, cond_state, prefix=state_path))
                    else:
                        # Invalid case index — walk all
                        for when in whens:
                            result.update(_collect_inputs(when.parameters, cond_state, prefix=state_path))
                except (ValueError, IndexError):
                    for when in whens:
                        result.update(_collect_inputs(when.parameters, cond_state, prefix=state_path))
            else:
                # No active case info — walk all branches
                for when in whens:
                    result.update(_collect_inputs(when.parameters, cond_state, prefix=state_path))

        elif param.parameter_type == "gx_repeat":
            inner_params = getattr(param, "parameters", [])
            repeat_instances = tool_state.get(param.name, []) if tool_state else []
            if not isinstance(repeat_instances, list):
                repeat_instances = []
            if repeat_instances:
                # Walk each repeat instance with indexed prefix: name_0, name_1, ...
                for idx, instance_state in enumerate(repeat_instances):
                    if not isinstance(instance_state, dict):
                        instance_state = {}
                    indexed_prefix = f"{param.name}_{idx}" if prefix is None else f"{prefix}|{param.name}_{idx}"
                    result.update(_collect_inputs(inner_params, instance_state, prefix=indexed_prefix))
            else:
                # No instances in state — emit unindexed as fallback
                result.update(_collect_inputs(inner_params, None, prefix=state_path))

        elif param.parameter_type == "gx_section":
            section_state = tool_state.get(param.name, {}) if tool_state else {}
            if not isinstance(section_state, dict):
                section_state = {}
            inner_params = getattr(param, "parameters", [])
            result.update(_collect_inputs(inner_params, section_state, prefix=state_path))

    return result


def _collect_outputs(outputs: list) -> Dict[str, ResolvedOutput]:
    """Extract data and collection outputs from ParsedTool.outputs."""
    result: Dict[str, ResolvedOutput] = {}

    for output in outputs:
        if isinstance(output, ToolOutputDataset):
            result[output.name] = ResolvedOutput(
                name=output.name,
                type="data",
                format=output.format,
                format_source=output.format_source,
            )
        elif isinstance(output, ToolOutputCollection):
            structure = output.structure
            result[output.name] = ResolvedOutput(
                name=output.name,
                type="collection",
                collection_type=structure.collection_type,
                collection_type_source=structure.collection_type_source,
                collection_type_from_rules=structure.collection_type_from_rules,
                structured_like=structure.structured_like,
            )
        elif isinstance(output, (ToolOutputText, ToolOutputInteger, ToolOutputFloat, ToolOutputBoolean)):
            result[output.name] = ResolvedOutput(
                name=output.name,
                type=output.type,  # "text", "integer", "float", "boolean"
            )

    return result


def _resolve_rules_collection_types(
    outputs: Dict[str, ResolvedOutput],
    tool_state: Optional[dict],
) -> None:
    """Resolve collection_type_from_rules outputs using rules mapping in tool_state.

    Modifies outputs in place, setting collection_type from the rules dict.
    """
    if not tool_state:
        return

    for output in outputs.values():
        rules_param = output.collection_type_from_rules
        if not rules_param or output.collection_type:
            continue

        rules_dict = tool_state.get(rules_param)
        if not isinstance(rules_dict, dict) or "mapping" not in rules_dict:
            continue

        try:
            from galaxy.util.rules_dsl import RuleSet

            rule_set = RuleSet(rules_dict)
            ct = rule_set.collection_type
            if ct:
                output.collection_type = ct
        except Exception:
            log.debug("Failed to resolve collection type from rules for output %s", output.name)


def _topological_sort(steps: Dict[str, ResolvedStep]) -> List[str]:
    """Topological sort of step IDs based on connections."""
    pairs = []
    all_ids = set(steps.keys())

    for step_id, step in steps.items():
        # Self-pair ensures every step appears in output
        pairs.append((step_id, step_id))
        for conn_refs in step.connections.values():
            for ref in conn_refs:
                if ref.source_step in all_ids:
                    pairs.append((ref.source_step, step_id))

    return topsort(pairs)
