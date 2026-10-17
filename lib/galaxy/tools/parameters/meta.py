import copy
import itertools
import logging
from collections import namedtuple
from collections.abc import (
    Callable,
    Sequence,
)
from typing import (
    Any,
)

from galaxy import (
    exceptions,
    util,
)
from galaxy.model import (
    DatasetCollection,
    DatasetCollectionElement,
    DatasetInstance,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    LibraryDatasetDatasetAssociation,
)
from galaxy.model.dataset_collections import (
    matching,
    subcollections,
)
from galaxy.model.dataset_collections.adapters import (
    CollectionAdapter,
    PromoteCollectionElementToCollectionAdapter,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.tool_util.parameters import (
    RequestInternalDereferencedToolState,
    RequestInternalToolState,
)
from galaxy.util.permutations import (
    assert_matched_lengths,
    build_combos,
    input_classification,
    is_in_state,
    state_copy,
    state_get_value,
    state_remove_value,
    state_set_value,
)
from galaxy.work.context import WorkRequestContext
from . import visit_input_values
from .workflow_utils import (
    runtime_to_json,
    RuntimeValue,
)
from .wrapped import process_key
from .._types import (
    InputFormatT,
    ToolRequestT,
    ToolStateDumpedToJsonInternalT,
    ToolStateJobInstanceT,
)

log = logging.getLogger(__name__)

WorkflowParameterExpansion = namedtuple(
    "WorkflowParameterExpansion", ["param_combinations", "param_keys", "input_combinations"]
)


class ParamKey:
    def __init__(self, step_id, key):
        self.step_id = step_id
        self.key = key


class InputKey:
    def __init__(self, input_id):
        self.input_id = input_id


def expand_workflow_inputs(param_inputs, inputs=None):
    """
    Expands incoming encoded multiple payloads, into the set of all individual payload combinations
    >>> expansion = expand_workflow_inputs({'1': {'input': {'batch': True, 'product': True, 'values': [{'hid': '1'}, {'hid': '2'}] }}})
    >>> print(["%s" % (p['1']['input']['hid']) for p in expansion.param_combinations])
    ['1', '2']
    >>> expansion = expand_workflow_inputs({'1': {'input': {'batch': True, 'values': [{'hid': '1'}, {'hid': '2'}] }}})
    >>> print(["%s" % (p['1']['input']['hid']) for p in expansion.param_combinations])
    ['1', '2']
    >>> expansion = expand_workflow_inputs({'1': {'input': {'batch': True, 'values': [{'hid': '1'}, {'hid': '2'}] }}, '2': {'input': {'batch': True, 'values': [{'hid': '3'}, {'hid': '4'}] }}})
    >>> print(["%s%s" % (p['1']['input']['hid'], p['2']['input']['hid']) for p in expansion.param_combinations])
    ['13', '24']
    >>> expansion = expand_workflow_inputs({'1': {'input': {'batch': True, 'product': True, 'values': [{'hid': '1'}, {'hid': '2'}] }}, '2': {'input': {'batch': True, 'values': [{'hid': '3'}, {'hid': '4'}, {'hid': '5'}] }}})
    >>> print(["%s%s" % (p['1']['input']['hid'], p['2']['input']['hid']) for p in expansion.param_combinations])
    ['13', '23', '14', '24', '15', '25']
    >>> expansion = expand_workflow_inputs({'1': {'input': {'batch': True, 'product': True, 'values': [{'hid': '1'}, {'hid': '2'}] }}, '2': {'input': {'batch': True, 'product': True, 'values': [{'hid': '3'}, {'hid': '4'}, {'hid': '5'}] }}, '3': {'input': {'batch': True, 'product': True, 'values': [{'hid': '6'}, {'hid': '7'}, {'hid': '8'}] }}})
    >>> print(["%s%s%s" % (p['1']['input']['hid'], p['2']['input']['hid'], p['3']['input']['hid']) for p in expansion.param_combinations])
    ['136', '137', '138', '146', '147', '148', '156', '157', '158', '236', '237', '238', '246', '247', '248', '256', '257', '258']
    >>> expansion = expand_workflow_inputs(None, inputs={'myinput': {'batch': True, 'product': True, 'values': [{'hid': '1'}, {'hid': '2'}] }})
    >>> print(["%s" % (p['myinput']['hid']) for p in expansion.input_combinations])
    ['1', '2']
    """
    param_inputs = param_inputs or {}
    inputs = inputs or {}

    linked_n = None
    linked = []
    product = []
    linked_keys = []
    product_keys = []

    def is_batch(value):
        return (
            isinstance(value, dict)
            and "batch" in value
            and value["batch"] is True
            and "values" in value
            and isinstance(value["values"], list)
        )

    for step_id, step in sorted(param_inputs.items()):
        for key, value in sorted(step.items()):
            if is_batch(value):
                nval = len(value["values"])
                if "product" in value and value["product"] is True:
                    product.append(value["values"])
                    product_keys.append(ParamKey(step_id, key))
                else:
                    if linked_n is None:
                        linked_n = nval
                    elif linked_n != nval or nval == 0:
                        raise exceptions.RequestParameterInvalidException(
                            "Failed to match linked batch selections. Please select equal number of data files."
                        )
                    linked.append(value["values"])
                    linked_keys.append(ParamKey(step_id, key))

    # Force it to a list to allow modification...
    input_items = list(inputs.items())
    for input_id, value in input_items:
        if is_batch(value):
            nval = len(value["values"])
            if "product" in value and value["product"] is True:
                product.append(value["values"])
                product_keys.append(InputKey(input_id))
            else:
                if linked_n is None:
                    linked_n = nval
                elif linked_n != nval or nval == 0:
                    raise exceptions.RequestParameterInvalidException(
                        "Failed to match linked batch selections. Please select equal number of data files."
                    )
                linked.append(value["values"])
                linked_keys.append(InputKey(input_id))
        elif isinstance(value, dict) and "batch" in value:
            # remove batch wrapper and render simplified input form rest of workflow
            # code expects
            inputs[input_id] = value["values"][0]

    param_combinations = []
    input_combinations = []
    params_keys = []
    linked = linked or [[None]]
    product = product or [[None]]
    linked_keys = linked_keys or [None]
    product_keys = product_keys or [None]
    for linked_values, product_values in itertools.product(zip(*linked), itertools.product(*product)):
        new_params = copy.deepcopy(param_inputs)
        new_inputs = copy.deepcopy(inputs)
        new_keys = []
        for input_key, value in list(zip(linked_keys, linked_values)) + list(zip(product_keys, product_values)):
            if input_key:
                if isinstance(input_key, ParamKey):
                    step_id = input_key.step_id
                    key = input_key.key
                    assert step_id is not None
                    new_params[step_id][key] = value
                    if isinstance(value, dict) and "hid" in value:
                        new_keys.append(str(value["hid"]))
                else:
                    input_id = input_key.input_id
                    assert input_id is not None
                    new_inputs[input_id] = value
                    if isinstance(value, dict) and "hid" in value:
                        new_keys.append(str(value["hid"]))

        params_keys.append(new_keys)
        param_combinations.append(new_params)
        input_combinations.append(new_inputs)

    return WorkflowParameterExpansion(param_combinations, params_keys, input_combinations)


ExpandedT = tuple[list[ToolStateJobInstanceT], matching.MatchingCollections | None]


def expand_flat_parameters_to_nested(incoming_copy: ToolRequestT) -> dict[str, Any]:
    nested_dict: dict[str, Any] = {}
    for incoming_key, incoming_value in incoming_copy.items():
        if not incoming_key.startswith("__"):
            process_key(incoming_key, incoming_value=incoming_value, d=nested_dict)
    return nested_dict


def _remove_internal_state_keys(state: Any) -> None:
    """Remove ``__``-prefixed keys from every dict in the nested state.

    ``visit_input_values`` injects internal book-keeping entries such as
    ``__current_case__`` and ``__index__`` as side-effects.  These must not
    reach the job-internal Pydantic validation layer, which uses ``extra='forbid'``.
    """
    if isinstance(state, dict):
        for key in [k for k in state if k.startswith("__")]:
            del state[key]
        for v in state.values():
            _remove_internal_state_keys(v)
    elif isinstance(state, list):
        for item in state:
            _remove_internal_state_keys(item)


def expand_meta_parameters(
    trans: WorkRequestContext, tool, incoming: ToolRequestT, input_format: InputFormatT
) -> ExpandedT:
    """
    Take in a dictionary of raw incoming parameters and expand to a list
    of expanded incoming parameters (one set of parameters per tool
    execution).
    """

    for key in list(incoming.keys()):
        if key.endswith("|__identifier__"):
            incoming.pop(key)

    collections_to_match = matching.CollectionsToMatch()

    def expand_collection(input_key, collection_value, linked):
        return __expand_collection_parameter(trans, input_key, collection_value, collections_to_match, linked=linked)

    classifier = _meta_value_classifier(_is_legacy_batch, expand_collection)
    nested = input_format != "legacy"
    single_inputs, matched_multi_inputs, multiplied_multi_inputs = _split_meta_inputs(
        tool, incoming, nested, classifier
    )
    expanded_incomings = build_combos(single_inputs, matched_multi_inputs, multiplied_multi_inputs, nested=nested)
    if collections_to_match.has_collections():
        collection_info = trans.app.dataset_collection_manager.match_collections(collections_to_match)
    else:
        collection_info = None
    return expanded_incomings, collection_info


def _is_legacy_batch(value: dict[str, Any]) -> bool:
    return bool(value.get("batch", False))


def _is_async_batch(value: dict[str, Any]) -> bool:
    return bool(value.get("__class__", "Batch") == "Batch")


def _is_meta_wrapper(value: Any) -> bool:
    """Whether a request value is an explicit ``{"values": [...]}`` meta wrapper (batch or not)."""
    return isinstance(value, dict) and "values" in value


ExpandCollectionT = Callable[[str, Any, bool], Sequence[Any]]
ClassifierT = Callable[[Any, str], tuple[str, Any]]


def _meta_value_classifier(
    is_batch: Callable[[dict[str, Any]], bool], expand_collection: ExpandCollectionT | None
) -> ClassifierT:
    """Build a classifier mapping a request value to (MATCHED/MULTIPLIED/SINGLE, values).

    Without ``expand_collection``, collection map-overs stay SINGLE (left to collection matching).
    """

    def classifier_from_value(value: Any, input_key: str) -> tuple[str, Any]:
        if _is_meta_wrapper(value):
            # Explicit meta wrapper for inputs...
            batch = is_batch(value)
            is_linked = value.get("linked", True)
            if batch and is_linked:
                classification = input_classification.MATCHED
            elif batch:
                classification = input_classification.MULTIPLIED
            else:
                classification = input_classification.SINGLE
            if not __collection_multirun_parameter(value):
                values = value["values"]
            elif expand_collection:
                values = expand_collection(input_key, value["values"][0], is_linked)
            else:
                classification, values = input_classification.SINGLE, value
        else:
            classification = input_classification.SINGLE
            values = value
        return classification, values

    return classifier_from_value


def _split_meta_inputs(tool, incoming: ToolRequestT, nested: bool, classifier: ClassifierT):
    # If we're going to multiply input dataset combinations
    # order matters, so the following reorders incoming
    # according to tool.inputs (which is ordered).
    incoming_copy = incoming.copy()
    if nested:
        nested_dict = incoming_copy
    else:
        nested_dict = expand_flat_parameters_to_nested(incoming_copy)
    reordered_incoming = reorder_parameters(tool, incoming_copy, nested_dict, nested)
    if nested:
        return split_inputs_nested(tool.inputs, reordered_incoming, classifier)

    def classifier_flat(input_key):
        return classifier(incoming_copy[input_key], input_key)

    return split_inputs_flat(reordered_incoming, classifier_flat)


def reorder_parameters(tool, incoming, nested_dict, nested):
    # If we're going to multiply input dataset combinations
    # order matters, so the following reorders incoming
    # according to tool.inputs (which is ordered).
    incoming_copy = state_copy(incoming, nested)

    reordered_incoming = {}

    def visitor(input, value, prefix, prefixed_name, prefixed_label, error, **kwargs):
        if is_in_state(incoming_copy, prefixed_name, nested):
            value_to_copy_over = state_get_value(incoming_copy, prefixed_name, nested)
            state_set_value(reordered_incoming, prefixed_name, value_to_copy_over, nested)
            state_remove_value(incoming_copy, prefixed_name, nested)

    visit_input_values(inputs=tool.inputs, input_values=nested_dict, callback=visitor)

    def merge_into(from_object, into_object):
        if isinstance(from_object, dict):
            for key, value in from_object.items():
                if key not in into_object:
                    into_object[key] = value
                else:
                    into_target = into_object[key]
                    merge_into(value, into_target)
        elif isinstance(from_object, list):
            for index in from_object:
                if len(into_object) <= index:
                    into_object.append(from_object[index])
                else:
                    merge_into(from_object[index], into_object[index])

    merge_into(incoming_copy, reordered_incoming)
    return reordered_incoming


def split_inputs_flat(inputs: dict[str, Any], classifier):
    single_inputs: dict[str, Any] = {}
    matched_multi_inputs: dict[str, Any] = {}
    multiplied_multi_inputs: dict[str, Any] = {}

    for input_key in inputs:
        input_type, expanded_val = classifier(input_key)
        if input_type == input_classification.SINGLE:
            single_inputs[input_key] = expanded_val
        elif input_type == input_classification.MATCHED:
            matched_multi_inputs[input_key] = expanded_val
        elif input_type == input_classification.MULTIPLIED:
            multiplied_multi_inputs[input_key] = expanded_val

    return (single_inputs, matched_multi_inputs, multiplied_multi_inputs)


def split_inputs_nested(inputs, nested_dict, classifier):
    matched_multi_inputs: dict[str, Any] = {}
    multiplied_multi_inputs: dict[str, Any] = {}
    unset_value = object()

    def visitor(input, value, prefix, prefixed_name, prefixed_label, error, **kwargs):
        if value is unset_value:
            # don't want to inject extra nulls into state
            return

        input_type, expanded_val = classifier(value, prefixed_name)
        if input_type == input_classification.MATCHED:
            matched_multi_inputs[prefixed_name] = expanded_val
        elif input_type == input_classification.MULTIPLIED:
            multiplied_multi_inputs[prefixed_name] = expanded_val

    visit_input_values(
        inputs=inputs, input_values=nested_dict, callback=visitor, allow_case_inference=True, unset_value=unset_value
    )
    _remove_internal_state_keys(nested_dict)
    return (nested_dict, matched_multi_inputs, multiplied_multi_inputs)


ExpandedAsyncT = tuple[
    list[ToolStateJobInstanceT], list[ToolStateDumpedToJsonInternalT], matching.MatchingCollections | None
]


def validate_matched_batch_lengths(tool, incoming: RequestInternalToolState) -> None:
    """Fail fast on linked dataset batches of different lengths before expansion is queued.

    Collection map-overs are left to collection matching at expansion time.
    """

    classifier = _meta_value_classifier(_is_async_batch, None)
    _, matched_multi_inputs, _ = split_inputs_nested(tool.inputs, copy.deepcopy(incoming.input_state), classifier)
    assert_matched_lengths({key: len(values) for key, values in matched_multi_inputs.items()})


def expand_meta_parameters_async(app, tool, incoming: RequestInternalDereferencedToolState) -> ExpandedAsyncT:
    collections_to_match = matching.CollectionsToMatch()

    def expand_collection(input_key, collection_value, linked):
        return __expand_collection_parameter_async(
            app, input_key, collection_value, collections_to_match, linked=linked
        )

    classifier = _meta_value_classifier(_is_async_batch, expand_collection)
    # is there a way to make Pydantic ensure reordering isn't needed - model and serialize out the parameters maybe?
    single_inputs, matched_multi_inputs, multiplied_multi_inputs = _split_meta_inputs(
        tool, incoming.input_state, True, classifier
    )
    expanded_incomings = build_combos(single_inputs, matched_multi_inputs, multiplied_multi_inputs, nested=True)
    # those all have sa model objects from expansion to be used within for additional logic (maybe?)
    # but we want to record just src and IDS in the job state object - so undo that
    expanded_job_states = build_combos(
        to_decoded_json(single_inputs),
        to_decoded_json(matched_multi_inputs),
        to_decoded_json(multiplied_multi_inputs),
        nested=True,
    )
    if collections_to_match.has_collections():
        collection_info = app.dataset_collection_manager.match_collections(collections_to_match)
    else:
        collection_info = None
    return expanded_incomings, expanded_job_states, collection_info


def to_decoded_json(has_objects):
    if isinstance(has_objects, dict):
        decoded_json = {}
        for key, value in has_objects.items():
            decoded_json[key] = to_decoded_json(value)
        return decoded_json
    elif isinstance(has_objects, list):
        return [to_decoded_json(o) for o in has_objects]
    elif isinstance(has_objects, CollectionAdapter):
        return has_objects.to_adapter_model().model_dump()
    elif isinstance(has_objects, DatasetCollectionElement):
        return {"src": "dce", "id": has_objects.id}
    elif isinstance(has_objects, HistoryDatasetAssociation):
        return {"src": "hda", "id": has_objects.id}
    elif isinstance(has_objects, HistoryDatasetCollectionAssociation):
        return {"src": "hdca", "id": has_objects.id}
    elif isinstance(has_objects, LibraryDatasetDatasetAssociation):
        return {"src": "ldda", "id": has_objects.id}
    elif isinstance(has_objects, RuntimeValue):
        return runtime_to_json(has_objects)
    else:
        return has_objects


CollectionExpansionListT = (
    list[DatasetCollectionElement | PromoteCollectionElementToCollectionAdapter] | list[DatasetInstance]
)


def __expand_collection_parameter(
    trans: WorkRequestContext,
    input_key,
    incoming_val: dict[str, Any],
    collections_to_match: "matching.CollectionsToMatch",
    linked=False,
) -> CollectionExpansionListT:
    item, collection, subcollection_type = _batch_collection(trans, incoming_val)
    collections_to_match.add(input_key, item, subcollection_type=subcollection_type, linked=linked)
    return _collection_batch_values(collection, subcollection_type)


def _batch_collection(
    trans: WorkRequestContext, incoming_val: dict[str, Any]
) -> tuple[HistoryDatasetCollectionAssociation | DatasetCollectionElement, DatasetCollection, str | None]:
    """Load the populated collection a batch value maps over, with its ``map_over_type``."""
    decoded_id = trans.app.security.decode_id(incoming_val["id"])
    item, collection = _load_batch_collection(trans.sa_session, incoming_val["src"], decoded_id)
    if not collection.populated_optimized:
        raise exceptions.ToolInputsNotReadyException("An input collection is not populated.")
    return item, collection, incoming_val.get("map_over_type")


def _load_batch_collection(
    session: galaxy_scoped_session, src: str, item_id: int
) -> tuple[HistoryDatasetCollectionAssociation | DatasetCollectionElement, DatasetCollection]:
    """Load a batch's ``hdca``/``dce`` item and the collection it maps over."""
    if src == "dce":
        dce = session.get_one(DatasetCollectionElement, item_id)
        if not dce.child_collection:
            raise exceptions.ToolMetaParameterException(f"DCE {item_id} does not contain a child collection")
        return dce, dce.child_collection
    elif src == "hdca":
        hdca = session.get_one(HistoryDatasetCollectionAssociation, item_id)
        return hdca, hdca.collection
    raise exceptions.ToolMetaParameterException(f"Invalid dataset collection source type {src}")


def _collection_batch_values(collection: DatasetCollection, subcollection_type: str | None) -> CollectionExpansionListT:
    """What a batch over ``collection`` yields: its datasets, or its ``subcollection_type`` sub-collections."""
    if subcollection_type is not None:
        subcollection_elements: list[DatasetCollectionElement | PromoteCollectionElementToCollectionAdapter] = (
            subcollections._split_dataset_collection(collection, subcollection_type)
        )
        return subcollection_elements
    hdas: list[DatasetInstance] = []
    for element in collection.dataset_elements:
        hda = element.dataset_instance
        hda.element_identifier = element.element_identifier
        hdas.append(hda)
    return hdas


def __expand_collection_parameter_async(
    app,
    input_key,
    incoming_val: dict[str, Any],
    collections_to_match: "matching.CollectionsToMatch",
    linked=False,
) -> CollectionExpansionListT:
    subcollection_type = incoming_val.get("map_over_type")
    item, collection = _load_batch_collection(app.model.context, incoming_val["src"], incoming_val["id"])
    collections_to_match.add(input_key, item, subcollection_type=subcollection_type, linked=linked)
    return _collection_batch_values(collection, subcollection_type)


def __collection_multirun_parameter(value: dict[str, Any]) -> bool:
    is_batch = value.get("batch", False) or value.get("__class__", None) == "Batch"
    if not is_batch:
        return False

    batch_values = util.listify(value["values"])
    if len(batch_values) == 1:
        batch_over = batch_values[0]
        if isinstance(batch_over, dict) and ("src" in batch_over) and (batch_over["src"] in {"hdca", "dce"}):
            return True
    return False
