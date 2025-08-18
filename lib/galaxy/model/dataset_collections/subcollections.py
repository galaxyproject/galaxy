from galaxy import exceptions
from .adapters import PromoteCollectionElementToCollectionAdapter


def split_dataset_collection_instance(dataset_collection_instance, collection_type):
    """Split up collection into collection."""
    return _split_dataset_collection(dataset_collection_instance.collection, collection_type)


def _is_a_subcollection_type(this_collection_type: str, collection_type: str):
    if collection_type == "single_datasets":
        # can be a subcollection of anything effectively...
        return True
    if not this_collection_type.endswith(collection_type) or this_collection_type == collection_type:
        return False
    return True


def _split_dataset_collection(dataset_collection, collection_type):
    this_collection_type = dataset_collection.collection_type
    is_this_collection_nested = ":" in this_collection_type
    if not _is_a_subcollection_type(this_collection_type, collection_type):
        raise exceptions.MessageException("Cannot split collection in desired fashion.")

    split_elements = []
    for element in dataset_collection.elements:
        if not is_this_collection_nested and collection_type == "single_datasets":
            split_elements.append(PromoteCollectionElementToCollectionAdapter(element))
            continue

        child_collection = element.child_collection
        if child_collection is None:
            raise exceptions.MessageException("Cannot split collection in desired fashion.")
        if child_collection.collection_type == collection_type:
            split_elements.append(element)
        else:
            split_elements.extend(_split_dataset_collection(element.child_collection, collection_type))

    return split_elements
