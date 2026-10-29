from typing import (
    TYPE_CHECKING,
    Union,
)

from galaxy import exceptions
from .adapters import PromoteCollectionElementToCollectionAdapter
from .type_description import COLLECTION_TYPE_DESCRIPTION_FACTORY

if TYPE_CHECKING:
    from galaxy.model import (
        DatasetCollection,
        DatasetCollectionElement,
        HistoryDatasetCollectionAssociation,
    )


SplitReturnType = list[Union["DatasetCollectionElement", "PromoteCollectionElementToCollectionAdapter"]]


def split_dataset_collection_instance(
    dataset_collection_instance: "HistoryDatasetCollectionAssociation", collection_type: str
) -> SplitReturnType:
    """Split up collection into collection."""
    return _split_dataset_collection(dataset_collection_instance.collection, collection_type)


def _is_compound_paired_or_unpaired(collection_type: str) -> bool:
    # a split never yields a sample_sheet
    return collection_type.endswith(":paired_or_unpaired") and not collection_type.startswith("sample_sheet")


def _is_a_subcollection_type(this_collection_type: str, collection_type: str):
    if collection_type == "single_datasets":
        # can be a subcollection of anything effectively...
        return True
    if _is_compound_paired_or_unpaired(collection_type):
        return COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type(this_collection_type).has_subcollections_of_type(
            collection_type
        )
    if not this_collection_type.endswith(collection_type) or this_collection_type == collection_type:
        return False
    return True


def _is_split_type(child_collection_type: str, collection_type: str) -> bool:
    if child_collection_type == collection_type:
        return True
    # e.g. list:paired_or_unpaired consumes list and list:paired
    return _is_compound_paired_or_unpaired(collection_type) and (
        COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type(collection_type).can_match_type(child_collection_type)
    )


def _split_dataset_collection(dataset_collection: "DatasetCollection", collection_type: str) -> SplitReturnType:
    this_collection_type = dataset_collection.collection_type
    is_this_collection_nested = ":" in this_collection_type
    if not _is_a_subcollection_type(this_collection_type, collection_type):
        raise exceptions.MessageException("Cannot split collection in desired fashion.")

    split_elements: SplitReturnType = []
    for element in dataset_collection.elements:
        if not is_this_collection_nested and collection_type == "single_datasets":
            split_elements.append(PromoteCollectionElementToCollectionAdapter(element))
            continue

        child_collection = element.child_collection
        if child_collection is None:
            raise exceptions.MessageException("Cannot split collection in desired fashion.")
        if _is_split_type(child_collection.collection_type, collection_type):
            split_elements.append(element)
        else:
            child_collection = element.child_collection
            if child_collection is not None:
                split_elements.extend(_split_dataset_collection(child_collection, collection_type))

    return split_elements
