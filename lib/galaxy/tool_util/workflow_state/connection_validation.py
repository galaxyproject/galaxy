"""Connection validation engine for workflow connections.

Validates each connection's type compatibility, resolves step map-over
states, and computes output collection types during topological traversal.
"""

# TODO: Give this type a name and reuse Dict[str, Dict[str, CollectionTypeOrSentinel]]

from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)

from galaxy.tool_util.collections import (
    COLLECTION_TYPE_DESCRIPTION_FACTORY,
    CollectionTypeDescription,
)
from ._report_models import (
    ConnectionResult,
    ConnectionStatus,
    ConnectionStepResult,
    ConnectionValidationReport,
    ResolvedOutputType,
)
from ._types import GetToolInfo
from .connection_graph import (
    build_workflow_graph,
    ResolvedInput,
    ResolvedOutput,
    ResolvedStep,
    WorkflowGraph,
)
from .connection_types import (
    ANY_COLLECTION_TYPE,
    can_match,
    CollectionTypeOrSentinel,
    effective_map_over,
    is_list_like,
    NULL_COLLECTION_TYPE,
)


@dataclass
class ConnectionValidationResult:
    """Result of validating a single connection."""

    source_step: str
    source_output: str
    target_step: str
    target_input: str
    status: ConnectionStatus
    mapping: Optional[str] = None  # collection type being mapped over, None = direct
    errors: List[str] = field(default_factory=list)


@dataclass
class StepConnectionResult:
    """Aggregated connection validation for one step."""

    step_id: str
    tool_id: Optional[str] = None
    step_type: str = "tool"
    map_over: Optional[str] = None
    connections: List[ConnectionValidationResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class WorkflowConnectionResult:
    """Whole-workflow connection validation result."""

    step_results: List[StepConnectionResult] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        for sr in self.step_results:
            if sr.errors:
                return False
            for cr in sr.connections:
                if cr.status == "invalid":
                    return False
        return True

    @property
    def summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {"ok": 0, "invalid": 0, "skip": 0}
        for sr in self.step_results:
            for cr in sr.connections:
                counts[cr.status] = counts.get(cr.status, 0) + 1
        return counts


def validate_connections(
    workflow_dict: dict,
    get_tool_info: GetToolInfo,
) -> WorkflowConnectionResult:
    """Validate all connections in a workflow."""
    graph = build_workflow_graph(workflow_dict, get_tool_info)
    result, _ = validate_connection_graph(graph)
    return result


def validate_connections_report(
    workflow_dict: dict,
    get_tool_info: GetToolInfo,
) -> ConnectionValidationReport:
    """Validate connections and return a Pydantic report with resolved output types."""
    graph = build_workflow_graph(workflow_dict, get_tool_info)
    result, resolved = validate_connection_graph(graph)
    return to_connection_validation_report(result, resolved)


def validate_connection_graph(
    graph: WorkflowGraph,
    seed_output_types: Optional[Dict[str, Dict[str, CollectionTypeOrSentinel]]] = None,
) -> Tuple[WorkflowConnectionResult, Dict[str, Dict[str, CollectionTypeOrSentinel]]]:
    """Validate connections on a pre-built workflow graph.

    Processes steps in topological order so upstream output types are
    resolved before they're needed by downstream connection validation.

    seed_output_types: optional pre-resolved types for input steps, used
    when validating inner subworkflows to propagate outer types inward.
    """
    # Mutable state: step_id → output_name → resolved type
    resolved_output_types: Dict[str, Dict[str, CollectionTypeOrSentinel]] = {}

    # Seed output types from the graph (static types from tool defs / input steps)
    for step_id, step in graph.steps.items():
        resolved_output_types[step_id] = {}
        for output_name, output in step.outputs.items():
            resolved_output_types[step_id][output_name] = _output_to_type(output)

    # Override with externally provided seed types (for subworkflow input propagation)
    if seed_output_types:
        for step_id, outputs in seed_output_types.items():
            if step_id in resolved_output_types:
                resolved_output_types[step_id].update(outputs)

    result = WorkflowConnectionResult()

    for step_id in graph.sorted_step_ids:
        step = graph.steps[step_id]
        step_result = StepConnectionResult(
            step_id=step_id,
            tool_id=step.tool_id,
            step_type=step.step_type,
        )

        if not step.connections:
            result.step_results.append(step_result)
            continue

        # Validate each connection into this step
        map_over_contributions: List[Optional[CollectionTypeDescription]] = []

        for input_path, conn_refs in step.connections.items():
            for ref in conn_refs:
                conn_result = _validate_single_connection(
                    source_step=ref.source_step,
                    source_output=ref.output_name,
                    target_step=step_id,
                    target_input=input_path,
                    target_resolved_input=step.inputs.get(input_path),
                    resolved_output_types=resolved_output_types,
                )
                step_result.connections.append(conn_result)

                if conn_result.status == "ok" and conn_result.mapping:
                    ctd = COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type(conn_result.mapping)
                    map_over_contributions.append(ctd)
                elif conn_result.status in ("ok", "skip"):
                    map_over_contributions.append(None)

        # Resolve step map-over from contributions
        step_map_over = _resolve_step_map_over(map_over_contributions, step_result)
        if step_map_over:
            step_result.map_over = step_map_over.collection_type

        # Resolve output types: subworkflow recursion or normal tool output resolution
        if step.step_type == "subworkflow" and step.inner_graph:
            _resolve_subworkflow_outputs(step, resolved_output_types)
        else:
            _resolve_output_types(step, step_map_over, resolved_output_types)

        result.step_results.append(step_result)

    return result, resolved_output_types


def _validate_single_connection(
    source_step: str,
    source_output: str,
    target_step: str,
    target_input: str,
    target_resolved_input: Optional[ResolvedInput],
    resolved_output_types: Dict[str, Dict[str, CollectionTypeOrSentinel]],
) -> ConnectionValidationResult:
    """Validate a single output->input connection."""
    # Resolve source output type
    source_types = resolved_output_types.get(source_step, {})
    source_type = source_types.get(source_output)

    if source_type is None:
        return ConnectionValidationResult(
            source_step=source_step,
            source_output=source_output,
            target_step=target_step,
            target_input=target_input,
            status="skip",
            errors=[f"Cannot resolve output '{source_output}' on step {source_step}"],
        )

    # No target input info (tool not resolved) -> skip
    if target_resolved_input is None:
        return ConnectionValidationResult(
            source_step=source_step,
            source_output=source_output,
            target_step=target_step,
            target_input=target_input,
            status="skip",
            errors=[f"Cannot resolve input '{target_input}' on step {target_step}"],
        )

    target_type = _input_to_type(target_resolved_input)

    def _ok(mapping: Optional[str] = None):
        return ConnectionValidationResult(
            source_step=source_step,
            source_output=source_output,
            target_step=target_step,
            target_input=target_input,
            status="ok",
            mapping=mapping,
        )

    # Dataset -> dataset: always valid
    if source_type is NULL_COLLECTION_TYPE:
        if target_type is NULL_COLLECTION_TYPE:
            return _ok()
        # Dataset -> collection input: fall through to invalid

    elif source_type is ANY_COLLECTION_TYPE:
        # Output type unknown at static analysis time (e.g. __FILTER_EMPTY_DATASETS__)
        return ConnectionValidationResult(
            source_step=source_step,
            source_output=source_output,
            target_step=target_step,
            target_input=target_input,
            status="skip",
            errors=[f"Cannot determine output type for '{source_output}' on step {source_step}"],
        )

    else:
        # Source is a real collection type

        # Multi-data reduction: list-like collection -> data(multiple=True)
        # Must check before map-over since can_map_over(collection, NULL) is True.
        if target_resolved_input.multiple and target_resolved_input.type == "data":
            if isinstance(source_type, CollectionTypeDescription) and is_list_like(source_type):
                # Simple list -> multi-data: full reduction, no map-over
                # Deeper (list:list, list:paired, etc.) -> multi-data: outer levels map over
                inner_list = COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type("list")
                if source_type.has_subcollections_of_type(inner_list):
                    remaining = source_type.effective_collection_type(inner_list)
                    return _ok(mapping=remaining)
                return _ok()
            # Non-list-like -> fall through to can_match / map_over

        # Direct collection match?
        if can_match(source_type, target_type):
            return _ok()

        # Map over?
        map_over = effective_map_over(source_type, target_type)
        if map_over is not None:
            return _ok(mapping=map_over.collection_type)

    # Invalid
    source_desc = _type_description(source_type)
    target_desc = _type_description(target_type)
    return ConnectionValidationResult(
        source_step=source_step,
        source_output=source_output,
        target_step=target_step,
        target_input=target_input,
        status="invalid",
        errors=[f"Incompatible types: output is {source_desc}, input expects {target_desc}"],
    )


def _resolve_step_map_over(
    contributions: List[Optional[CollectionTypeDescription]],
    step_result: StepConnectionResult,
) -> Optional[CollectionTypeDescription]:
    """Resolve effective map-over from all connection contributions.

    All non-None map-over types must be identical. If any disagree,
    report an error (the step can't satisfy both map-over structures).
    """
    non_none = [c for c in contributions if c is not None]
    if not non_none:
        return None

    best = non_none[0]
    for ctd in non_none[1:]:
        if ctd.collection_type != best.collection_type:
            step_result.errors.append(f"Incompatible map-over types: {best.collection_type} vs {ctd.collection_type}")
            return best  # return something, error recorded

    return best


def _resolve_output_types(
    step: ResolvedStep,
    map_over: Optional[CollectionTypeDescription],
    resolved_output_types: Dict[str, Dict[str, CollectionTypeOrSentinel]],
):
    """Resolve a step's output types accounting for map-over.

    Updates resolved_output_types in place for downstream consumption.
    """
    for output_name, output in step.outputs.items():
        if output.type == "collection":
            base_type = _resolve_collection_output_type(step, output, resolved_output_types, map_over)
            if base_type and map_over:
                combined = f"{map_over.collection_type}:{base_type}"
                resolved_output_types[step.step_id][output_name] = (
                    COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type(combined)
                )
            elif base_type:
                resolved_output_types[step.step_id][output_name] = (
                    COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type(base_type)
                )
            # else: leave as initialized (ANY_COLLECTION_TYPE or whatever)
        else:
            # Plain dataset output: if mapped over, becomes a collection
            if map_over:
                resolved_output_types[step.step_id][output_name] = (
                    COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type(map_over.collection_type)
                )
            else:
                resolved_output_types[step.step_id][output_name] = NULL_COLLECTION_TYPE


def _resolve_subworkflow_outputs(
    step: ResolvedStep,
    resolved_output_types: Dict[str, Dict[str, CollectionTypeOrSentinel]],
) -> None:
    """Recursively validate inner workflow and propagate output types outward."""
    inner_graph = step.inner_graph
    assert inner_graph is not None

    # Build seed types: propagate outer resolved types into inner input steps
    seed: Dict[str, Dict[str, CollectionTypeOrSentinel]] = {}
    for _input_path, conn_refs in step.connections.items():
        for ref in conn_refs:
            inner_step_id = ref.input_subworkflow_step_id
            if inner_step_id is None:
                continue
            outer_type = resolved_output_types.get(ref.source_step, {}).get(ref.output_name)
            if outer_type is not None and inner_step_id in inner_graph.steps:
                seed.setdefault(inner_step_id, {})["output"] = outer_type

    # Recursively validate inner graph
    _inner_result, inner_resolved = validate_connection_graph(inner_graph, seed_output_types=seed)

    # Map exposed inner outputs to outer step's output types
    resolved_output_types.setdefault(step.step_id, {})
    for external_name, (inner_step_id, inner_output_name) in step.subworkflow_output_map.items():
        inner_type = inner_resolved.get(inner_step_id, {}).get(inner_output_name)
        if inner_type is not None:
            resolved_output_types[step.step_id][external_name] = inner_type


def _resolve_collection_output_type(
    step: ResolvedStep,
    output: ResolvedOutput,
    resolved_output_types: Dict[str, Dict[str, CollectionTypeOrSentinel]],
    map_over: Optional[CollectionTypeDescription] = None,
) -> Optional[str]:
    """Resolve a collection output's base type (before map-over prefix)."""
    if output.collection_type:
        return output.collection_type

    # Dynamic: collection_type_source or structured_like
    source_param = output.collection_type_source or output.structured_like
    if source_param:
        return _resolve_collection_type_source(step, source_param, resolved_output_types, map_over)

    return None


def _resolve_collection_type_source(
    step: ResolvedStep,
    source_param: str,
    resolved_output_types: Dict[str, Dict[str, CollectionTypeOrSentinel]],
    map_over: Optional[CollectionTypeDescription] = None,
) -> Optional[str]:
    """Resolve a collection_type_source/structured_like reference.

    When the step is mapped over, the upstream output type includes the
    map-over prefix. The effective input type (what the tool actually sees)
    is the upstream type with the map-over prefix stripped.
    """
    conn_refs = step.connections.get(source_param, [])
    if not conn_refs:
        return None

    ref = conn_refs[0]
    source_types = resolved_output_types.get(ref.source_step, {})
    source_type = source_types.get(ref.output_name)
    if source_type is None or source_type is NULL_COLLECTION_TYPE or source_type is ANY_COLLECTION_TYPE:
        return None

    assert isinstance(source_type, CollectionTypeDescription)
    ct = source_type.collection_type

    # Strip map-over prefix to get the effective input type
    if map_over:
        prefix = map_over.collection_type + ":"
        if ct.startswith(prefix):
            ct = ct[len(prefix) :]

    return ct


def _output_to_type(output: ResolvedOutput) -> CollectionTypeOrSentinel:
    """Convert a ResolvedOutput to a CollectionTypeOrSentinel."""
    if output.type == "collection":
        if output.collection_type:
            return COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type(output.collection_type)
        return ANY_COLLECTION_TYPE
    return NULL_COLLECTION_TYPE


def _input_to_type(input_: ResolvedInput) -> CollectionTypeOrSentinel:
    """Convert a ResolvedInput to a CollectionTypeOrSentinel."""
    if input_.type == "collection":
        if input_.collection_type:
            return COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type(input_.collection_type)
        return ANY_COLLECTION_TYPE
    return NULL_COLLECTION_TYPE


def _type_description(t: CollectionTypeOrSentinel) -> str:
    """Human-readable description of a collection type or sentinel."""
    if t is NULL_COLLECTION_TYPE:
        return "dataset"
    if t is ANY_COLLECTION_TYPE:
        return "collection (any type)"
    assert isinstance(t, CollectionTypeDescription)
    return f"collection<{t.collection_type}>"


def _sentinel_to_collection_type(t: CollectionTypeOrSentinel) -> Optional[str]:
    """Convert a CollectionTypeOrSentinel to an optional collection_type string."""
    if t is NULL_COLLECTION_TYPE or t is ANY_COLLECTION_TYPE:
        return None
    assert isinstance(t, CollectionTypeDescription)
    return t.collection_type


def to_connection_validation_report(
    result: WorkflowConnectionResult,
    resolved_output_types: Dict[str, Dict[str, CollectionTypeOrSentinel]],
) -> ConnectionValidationReport:
    """Convert dataclass result + resolved output types to Pydantic report."""
    step_results = []
    for sr in result.step_results:
        connections = [
            ConnectionResult(
                source_step=cr.source_step,
                source_output=cr.source_output,
                target_step=cr.target_step,
                target_input=cr.target_input,
                status=cr.status,
                mapping=cr.mapping,
                errors=cr.errors,
            )
            for cr in sr.connections
        ]
        step_outputs = resolved_output_types.get(sr.step_id, {})
        resolved_outputs = [
            ResolvedOutputType(
                name=name,
                collection_type=_sentinel_to_collection_type(t),
            )
            for name, t in step_outputs.items()
        ]
        step_results.append(
            ConnectionStepResult(
                step=sr.step_id,
                tool_id=sr.tool_id,
                step_type=sr.step_type,
                map_over=sr.map_over,
                connections=connections,
                resolved_outputs=resolved_outputs,
                errors=sr.errors,
            )
        )
    return ConnectionValidationReport(
        valid=result.valid,
        step_results=step_results,
        summary=result.summary,
    )
