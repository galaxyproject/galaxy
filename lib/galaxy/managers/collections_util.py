import logging
import math
from typing import (
    Any,
    Dict,
)

from galaxy import (
    exceptions,
    model,
)
from galaxy.util import string_as_bool

log = logging.getLogger(__name__)

ERROR_MESSAGE_UNKNOWN_SRC = "Unknown dataset source (src) %s."
ERROR_MESSAGE_NO_NESTED_IDENTIFIERS = (
    "Dataset source new_collection requires nested element_identifiers for new collection."
)
ERROR_MESSAGE_NO_NAME = "Cannot load invalid dataset identifier - missing name - %s"
ERROR_MESSAGE_NO_COLLECTION_TYPE = "No collection_type define for nested collection %s."
ERROR_MESSAGE_INVALID_PARAMETER_FOUND = "Found invalid parameter %s in element identifier description %s."
ERROR_MESSAGE_DUPLICATED_IDENTIFIER_FOUND = "Found duplicated element identifier name %s."


def api_payload_to_create_params(payload):
    """
    Cleanup API payload to pass into dataset_collections.
    """
    required_parameters = ["collection_type", "element_identifiers"]
    missing_parameters = [p for p in required_parameters if p not in payload]
    if missing_parameters:
        message = f"Missing required parameters {missing_parameters}"
        raise exceptions.ObjectAttributeMissingException(message)

    params = dict(
        collection_type=payload.get("collection_type"),
        element_identifiers=payload.get("element_identifiers"),
        name=payload.get("name", None),
        hide_source_items=string_as_bool(payload.get("hide_source_items", False)),
        copy_elements=string_as_bool(payload.get("copy_elements", False)),
    )
    return params


def validate_input_element_identifiers(element_identifiers):
    """Scan through the list of element identifiers supplied by the API consumer
    and verify the structure is valid.
    """
    log.debug("Validating %d element identifiers for collection creation." % len(element_identifiers))
    identifier_names = set()
    for element_identifier in element_identifiers:
        if "__object__" in element_identifier:
            message = ERROR_MESSAGE_INVALID_PARAMETER_FOUND % ("__object__", element_identifier)
            raise exceptions.RequestParameterInvalidException(message)
        if "name" not in element_identifier:
            message = ERROR_MESSAGE_NO_NAME % element_identifier
            raise exceptions.RequestParameterInvalidException(message)
        name = element_identifier["name"]
        if name in identifier_names:
            message = ERROR_MESSAGE_DUPLICATED_IDENTIFIER_FOUND % name
            raise exceptions.RequestParameterInvalidException(message)
        else:
            identifier_names.add(name)
        src = element_identifier.get("src", "hda")
        if src not in ["hda", "hdca", "ldda", "new_collection"]:
            message = ERROR_MESSAGE_UNKNOWN_SRC % src
            raise exceptions.RequestParameterInvalidException(message)
        if src == "new_collection":
            if "element_identifiers" not in element_identifier:
                message = ERROR_MESSAGE_NO_NESTED_IDENTIFIERS
                raise exceptions.RequestParameterInvalidException(ERROR_MESSAGE_NO_NESTED_IDENTIFIERS)
            if "collection_type" not in element_identifier:
                message = ERROR_MESSAGE_NO_COLLECTION_TYPE % element_identifier
                raise exceptions.RequestParameterInvalidException(message)
            validate_input_element_identifiers(element_identifier["element_identifiers"])


def get_hda_and_element_identifiers(dataset_collection_instance):
    name = dataset_collection_instance.name
    collection = dataset_collection_instance.collection
    return get_collection(collection, name=name)


def get_collection(collection, name=""):
    names = []
    hdas = []
    if collection.has_subcollections:
        for element in collection.elements:
            subnames, subhdas = get_collection_elements(
                element.child_collection, name=f"{name}/{element.element_identifier}"
            )
            names.extend(subnames)
            hdas.extend(subhdas)
    else:
        for element in collection.elements:
            names.append(f"{name}/{element.element_identifier}")
            hdas.append(element.dataset_instance)
    return names, hdas


def get_collection_elements(collection, name=""):
    names = []
    hdas = []
    for element in collection.elements:
        full_element_name = f"{name}/{element.element_identifier}"
        if element.is_collection:
            subnames, subhdas = get_collection(element.child_collection, name=full_element_name)
            names.extend(subnames)
            hdas.extend(subhdas)
        else:
            names.append(full_element_name)
            hdas.append(element.dataset_instance)
    return names, hdas


def dictify_dataset_collection_instance(
    dataset_collection_instance, parent, security, url_builder, view="element", fuzzy_count=None
):
    hdca_view = "element" if view in ["element", "element-reference"] else "collection"
    dict_value = dataset_collection_instance.to_dict(view=hdca_view)
    encoded_id = security.encode_id(dataset_collection_instance.id)
    if isinstance(parent, model.History):
        encoded_history_id = security.encode_id(parent.id)
        dict_value["url"] = url_builder(
            "history_content_typed", history_id=encoded_history_id, id=encoded_id, type="dataset_collection"
        )
    elif isinstance(parent, model.LibraryFolder):
        encoded_library_id = security.encode_id(parent.library_root.id)
        encoded_folder_id = security.encode_id(parent.id)
        # TODO: Work in progress - this end-point is not right yet...
        dict_value["url"] = url_builder(
            "library_content", library_id=encoded_library_id, id=encoded_id, folder_id=encoded_folder_id
        )

    dict_value["contents_url"] = url_builder(
        "contents_dataset_collection",
        hdca_id=encoded_id,
        parent_id=security.encode_id(dataset_collection_instance.collection_id),
    )
    if view in ["element", "element-reference"]:
        collection = dataset_collection_instance.collection
        rank_fuzzy_counts = gen_rank_fuzzy_counts(collection.collection_type, fuzzy_count)
        elements, rest_fuzzy_counts = get_fuzzy_count_elements(collection, rank_fuzzy_counts)
        if view == "element":
            dict_value["populated"] = collection.populated
            element_func = dictify_element
        else:
            element_func = dictify_element_reference
        dict_value["elements"] = [element_func(_, rank_fuzzy_counts=rest_fuzzy_counts) for _ in elements]
        icj = dataset_collection_instance.implicit_collection_jobs
        if icj:
            dict_value["implicit_collection_jobs_id"] = icj.id
        else:
            dict_value["implicit_collection_jobs_id"] = None

    return dict_value


def dictify_element_reference(
    element: model.DatasetCollectionElement, rank_fuzzy_counts=None, recursive=True, security=None
):
    """Load minimal details of elements required to show outline of contents in history panel.

    History panel can use this reference to expand to full details if individual dataset elements
    are clicked.
    """
    dictified = element.to_dict(view="element")
    if (element_object := element.element_object) is not None:
        object_details: Dict[str, Any] = dict(
            id=element_object.id,
            model_class=element_object.__class__.__name__,
        )
        if isinstance(element_object, model.DatasetCollection):
            object_details["collection_type"] = element_object.collection_type
            object_details["element_count"] = element_object.element_count
            object_details["populated"] = element_object.populated_optimized

            # Recursively yield elements for each nested collection...
            if recursive:
                elements, rest_fuzzy_counts = get_fuzzy_count_elements(element_object, rank_fuzzy_counts)
                object_details["elements"] = [
                    dictify_element_reference(_, rank_fuzzy_counts=rest_fuzzy_counts, recursive=recursive)
                    for _ in elements
                ]
        else:
            object_details["state"] = element_object.state
            object_details["hda_ldda"] = "hda"
            object_details["purged"] = element_object.purged
            if isinstance(element_object, model.HistoryDatasetAssociation):
                object_details["history_id"] = element_object.history_id
                object_details["tags"] = element_object.make_tag_string_list()

        dictified["object"] = object_details
    else:
        dictified["object"] = None
    return dictified


def dictify_element(element, rank_fuzzy_counts=None):
    dictified = element.to_dict(view="element")
    element_object = element.element_object
    if element_object is not None:
        object_details = element.element_object.to_dict()
        if element.child_collection:
            child_collection = element.child_collection
            elements, rest_fuzzy_counts = get_fuzzy_count_elements(child_collection, rank_fuzzy_counts)

            # Recursively yield elements for each nested collection...
            object_details["elements"] = [dictify_element(_, rank_fuzzy_counts=rest_fuzzy_counts) for _ in elements]
            object_details["populated"] = child_collection.populated
            object_details["element_count"] = child_collection.element_count
    else:
        object_details = None

    dictified["object"] = object_details
    return dictified


def get_fuzzy_count_elements(collection, rank_fuzzy_counts):
    if rank_fuzzy_counts and rank_fuzzy_counts[0]:
        rank_fuzzy_count = rank_fuzzy_counts[0]
        elements = collection.elements[0:rank_fuzzy_count]
    else:
        elements = collection.elements

    if rank_fuzzy_counts is not None:
        rest_fuzzy_counts = rank_fuzzy_counts[1:]
    else:
        rest_fuzzy_counts = None

    return elements, rest_fuzzy_counts


def gen_rank_fuzzy_counts(collection_type, fuzzy_count=None):
    """Turn a global estimate on elements to return to per nested level based on collection type.

    This takes an arbitrary constant and generates an arbitrary constant and is quite messy.
    None of this should be relied on as a stable API - it is more of a general guideline to
    restrict within broad ranges the amount of objects returned.

    >>> def is_around(x, y):
    ...     return y - 1 < x and y + 1 > y
    ...
    >>> gen_rank_fuzzy_counts("list", None)
    [None]
    >>> gen_rank_fuzzy_counts("list", 500)
    [500]
    >>> gen_rank_fuzzy_counts("paired", 500)
    [2]
    >>> gen_rank_fuzzy_counts("list:paired", None)
    [None, None]
    >>> gen_rank_fuzzy_counts("list:list", 101)  # 100 would be edge case at 10 so bump to ensure 11
    [11, 11]
    >>> ll, pl = gen_rank_fuzzy_counts("list:paired", 100)
    >>> pl
    2
    >>> is_around(ll, 50)
    True
    >>> pl, ll = gen_rank_fuzzy_counts("paired:list", 100)
    >>> pl
    2
    >>> is_around(ll, 50)
    True
    >>> gen_rank_fuzzy_counts("list:list:list", 1001)
    [11, 11, 11]
    >>> l1l, l2l, l3l, pl = gen_rank_fuzzy_counts("list:list:list:paired", 2000)
    >>> pl
    2
    >>> is_around(10, l1l)
    True
    >>> gen_rank_fuzzy_counts("list:list:list", 1)
    [1, 1, 1]
    >>> gen_rank_fuzzy_counts("list:list:list", 2)
    [2, 2, 2]
    >>> gen_rank_fuzzy_counts("paired:paired", 400)
    [2, 2]
    >>> gen_rank_fuzzy_counts("paired:paired", 5)
    [2, 2]
    >>> gen_rank_fuzzy_counts("paired:paired", 3)
    [2, 2]
    >>> gen_rank_fuzzy_counts("paired:paired", 1)
    [1, 1]
    >>> gen_rank_fuzzy_counts("paired:paired", 2)
    [2, 2]
    """
    rank_collection_types = collection_type.split(":")
    if fuzzy_count is None:
        return [None for rt in rank_collection_types]
    else:
        # This is a list...
        paired_count = sum(1 if rt == "paired" else 0 for rt in rank_collection_types)
        list_count = len(rank_collection_types) - paired_count
        paired_fuzzy_count_mult = 1 if paired_count == 0 else 2 << (paired_count - 1)
        list_fuzzy_count_mult = math.floor((fuzzy_count * 1.0) / paired_fuzzy_count_mult)
        list_rank_fuzzy_count = (
            int(math.floor(math.pow(list_fuzzy_count_mult, 1.0 / list_count)) + 1) if list_count > 0 else 1.0
        )
        pair_rank_fuzzy_count = 2
        if list_rank_fuzzy_count > fuzzy_count:
            list_rank_fuzzy_count = fuzzy_count
        if pair_rank_fuzzy_count > fuzzy_count:
            pair_rank_fuzzy_count = fuzzy_count
        rank_fuzzy_counts = [
            pair_rank_fuzzy_count if rt == "paired" else list_rank_fuzzy_count for rt in rank_collection_types
        ]

        return rank_fuzzy_counts


__all__ = ("api_payload_to_create_params", "dictify_dataset_collection_instance")
