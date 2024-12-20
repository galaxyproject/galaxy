import copy
import itertools
import logging
from collections import namedtuple
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from galaxy import (
    exceptions,
    util,
)
from galaxy.model import (
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
from galaxy.tool_util.parameters import RequestInternalDereferencedToolState
from galaxy.util.permutations import (
    build_combos,
    input_classification,
    is_in_state,
    state_copy,
    state_get_value,
    state_remove_value,
    state_set_value,
)
from . import visit_input_values
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
                    if "hid" in value:
                        new_keys.append(str(value["hid"]))
                else:
                    input_id = input_key.input_id
                    assert input_id is not None
                    new_inputs[input_id] = value
                    if "hid" in value:
                        new_keys.append(str(value["hid"]))

        params_keys.append(new_keys)
        param_combinations.append(new_params)
        input_combinations.append(new_inputs)

    return WorkflowParameterExpansion(param_combinations, params_keys, input_combinations)


ExpandedT = Tuple[List[ToolStateJobInstanceT], Optional[matching.MatchingCollections]]


def expand_flat_parameters_to_nested(incoming_copy: ToolRequestT) -> Dict[str, Any]:
    nested_dict: Dict[str, Any] = {}
    for incoming_key, incoming_value in incoming_copy.items():
        if not incoming_key.startswith("__"):
            process_key(incoming_key, incoming_value=incoming_value, d=nested_dict)
    return nested_dict


def expand_meta_parameters(trans, tool, incoming: ToolRequestT, input_format: InputFormatT) -> ExpandedT:
    """
    Take in a dictionary of raw incoming parameters and expand to a list
    of expanded incoming parameters (one set of parameters per tool
    execution).
    """

    for key in list(incoming.keys()):
        if key.endswith("|__identifier__"):
            incoming.pop(key)

    # If we're going to multiply input dataset combinations
    # order matters, so the following reorders incoming
    # according to tool.inputs (which is ordered).
    incoming_copy = incoming.copy()
    if input_format == "legacy":
        nested_dict = expand_flat_parameters_to_nested(incoming_copy)
    else:
        nested_dict = incoming_copy

    collections_to_match = matching.CollectionsToMatch()

    def classifier_from_value(value, input_key):
        if isinstance(value, dict) and "values" in value:
            # Explicit meta wrapper for inputs...
            is_batch = value.get("batch", False)
            is_linked = value.get("linked", True)
            if is_batch and is_linked:
                classification = input_classification.MATCHED
            elif is_batch:
                classification = input_classification.MULTIPLIED
            else:
                classification = input_classification.SINGLE
            if __collection_multirun_parameter(value):
                collection_value = value["values"][0]
                values = __expand_collection_parameter(
                    trans, input_key, collection_value, collections_to_match, linked=is_linked
                )
            else:
                values = value["values"]
        else:
            classification = input_classification.SINGLE
            values = value
        return classification, values

    nested = input_format != "legacy"
    if not nested:
        reordered_incoming = reorder_parameters(tool, incoming_copy, nested_dict, nested)
        incoming_template = reordered_incoming

        def classifier_flat(input_key):
            return classifier_from_value(incoming[input_key], input_key)

        single_inputs, matched_multi_inputs, multiplied_multi_inputs = split_inputs_flat(
            incoming_template, classifier_flat
        )
    else:
        reordered_incoming = reorder_parameters(tool, incoming_copy, nested_dict, nested)
        incoming_template = reordered_incoming
        single_inputs, matched_multi_inputs, multiplied_multi_inputs = split_inputs_nested(
            tool.inputs, incoming_template, classifier_from_value
        )

    expanded_incomings = build_combos(single_inputs, matched_multi_inputs, multiplied_multi_inputs, nested=nested)
    if collections_to_match.has_collections():
        collection_info = trans.app.dataset_collection_manager.match_collections(collections_to_match)
    else:
        collection_info = None
    return expanded_incomings, collection_info


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


def split_inputs_flat(inputs: Dict[str, Any], classifier):
    single_inputs: Dict[str, Any] = {}
    matched_multi_inputs: Dict[str, Any] = {}
    multiplied_multi_inputs: Dict[str, Any] = {}

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
    single_inputs: Dict[str, Any] = {}
    matched_multi_inputs: Dict[str, Any] = {}
    multiplied_multi_inputs: Dict[str, Any] = {}
    unset_value = object()

    def visitor(input, value, prefix, prefixed_name, prefixed_label, error, **kwargs):
        if value is unset_value:
            # don't want to inject extra nulls into state
            return

        input_type, expanded_val = classifier(value, prefixed_name)
        if input_type == input_classification.SINGLE:
            single_inputs[prefixed_name] = expanded_val
        elif input_type == input_classification.MATCHED:
            matched_multi_inputs[prefixed_name] = expanded_val
        elif input_type == input_classification.MULTIPLIED:
            multiplied_multi_inputs[prefixed_name] = expanded_val

    visit_input_values(
        inputs=inputs, input_values=nested_dict, callback=visitor, allow_case_inference=True, unset_value=unset_value
    )
    single_inputs_nested = expand_flat_parameters_to_nested(single_inputs)
    return (single_inputs_nested, matched_multi_inputs, multiplied_multi_inputs)


ExpandedAsyncT = Tuple[
    List[ToolStateJobInstanceT], List[ToolStateDumpedToJsonInternalT], Optional[matching.MatchingCollections]
]


def expand_meta_parameters_async(app, tool, incoming: RequestInternalDereferencedToolState) -> ExpandedAsyncT:
    # TODO: Tool State 2.0 Follow Up: rework this to only test permutation at actual input value roots.

    collections_to_match = matching.CollectionsToMatch()

    def classifier_from_value(value, input_key):
        if isinstance(value, dict) and "values" in value:
            # Explicit meta wrapper for inputs...
            is_batch = value.get("__class__", "Batch") == "Batch"
            is_linked = value.get("linked", True)
            if is_batch and is_linked:
                classification = input_classification.MATCHED
            elif is_batch:
                classification = input_classification.MULTIPLIED
            else:
                classification = input_classification.SINGLE
            if __collection_multirun_parameter(value):
                log.info("IN HERE WITH A COLLECTION MULTIRUN PARAMETER")
                collection_value = value["values"][0]
                values = __expand_collection_parameter_async(
                    app, input_key, collection_value, collections_to_match, linked=is_linked
                )
            else:
                log.info("NOT IN HERE WITH A COLLECTION MULTIRUN PARAMETER")
                values = value["values"]
        else:
            classification = input_classification.SINGLE
            values = value
        return classification, values

    # is there a way to make Pydantic ensure reordering isn't needed - model and serialize out the parameters maybe?
    reordered_incoming = reorder_parameters(tool, incoming.input_state, incoming.input_state, True)
    incoming_template = reordered_incoming

    single_inputs, matched_multi_inputs, multiplied_multi_inputs = split_inputs_nested(
        tool.inputs, incoming_template, classifier_from_value
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
    elif isinstance(has_objects, DatasetCollectionElement):
        return {"src": "dce", "id": has_objects.id}
    elif isinstance(has_objects, HistoryDatasetAssociation):
        return {"src": "hda", "id": has_objects.id}
    elif isinstance(has_objects, HistoryDatasetCollectionAssociation):
        return {"src": "hdca", "id": has_objects.id}
    elif isinstance(has_objects, LibraryDatasetDatasetAssociation):
        return {"src": "ldda", "id": has_objects.id}
    else:
        return has_objects


CollectionExpansionListT = Union[List[DatasetCollectionElement], List[DatasetInstance]]


def __expand_collection_parameter(
    trans, input_key: str, incoming_val, collections_to_match: "matching.CollectionsToMatch", linked=False
) -> CollectionExpansionListT:
    # If subcollectin multirun of data_collection param - value will
    # be "hdca_id|subcollection_type" else it will just be hdca_id
    if "|" in incoming_val:
        encoded_hdc_id, subcollection_type = incoming_val.split("|", 1)
    else:
        try:
            src = incoming_val["src"]
            if src != "hdca":
                raise exceptions.ToolMetaParameterException(f"Invalid dataset collection source type {src}")
            encoded_hdc_id = incoming_val["id"]
            subcollection_type = incoming_val.get("map_over_type", None)
        except TypeError:
            encoded_hdc_id = incoming_val
            subcollection_type = None
    hdc_id = trans.app.security.decode_id(encoded_hdc_id)
    hdc = trans.sa_session.get(HistoryDatasetCollectionAssociation, hdc_id)
    if not hdc.collection.populated_optimized:
        raise exceptions.ToolInputsNotReadyException("An input collection is not populated.")
    collections_to_match.add(input_key, hdc, subcollection_type=subcollection_type, linked=linked)
    if subcollection_type is not None:
        subcollection_elements: List[DatasetCollectionElement] = subcollections.split_dataset_collection_instance(
            hdc, subcollection_type
        )
        return subcollection_elements
    else:
        hdas: List[DatasetInstance] = []
        for element in hdc.collection.dataset_elements:
            hda = element.dataset_instance
            hda.element_identifier = element.element_identifier
            hdas.append(hda)
        return hdas


def __expand_collection_parameter_async(app, input_key, incoming_val, collections_to_match, linked=False):
    # If subcollection multirun of data_collection param - value will
    # be "hdca_id|subcollection_type" else it will just be hdca_id
    try:
        src = incoming_val["src"]
        if src != "hdca":
            raise exceptions.ToolMetaParameterException(f"Invalid dataset collection source type {src}")
        hdc_id = incoming_val["id"]
        subcollection_type = incoming_val.get("map_over_type", None)
    except TypeError:
        hdc_id = incoming_val
        subcollection_type = None
    hdc = app.model.context.get(HistoryDatasetCollectionAssociation, hdc_id)
    collections_to_match.add(input_key, hdc, subcollection_type=subcollection_type, linked=linked)
    if subcollection_type is not None:
        subcollection_elements = subcollections.split_dataset_collection_instance(hdc, subcollection_type)
        return subcollection_elements
    else:
        hdas = []
        for element in hdc.collection.dataset_elements:
            hda = element.dataset_instance
            hda.element_identifier = element.element_identifier
            hdas.append(hda)
        return hdas


def __collection_multirun_parameter(value: Dict[str, Any]) -> bool:
    is_batch = value.get("batch", False) or value.get("__class__", None) == "Batch"
    if not is_batch:
        return False

    batch_values = util.listify(value["values"])
    if len(batch_values) == 1:
        batch_over = batch_values[0]
        if isinstance(batch_over, dict) and ("src" in batch_over) and (batch_over["src"] in {"hdca", "dce"}):
            return True
    return False
