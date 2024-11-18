from typing import (
    List,
    TYPE_CHECKING,
)

from galaxy import exceptions

if TYPE_CHECKING:
    from galaxy.model import (
        DatasetCollection,
        DatasetCollectionElement,
        HistoryDatasetCollectionAssociation,
    )


def split_dataset_collection_instance(
    dataset_collection_instance: "HistoryDatasetCollectionAssociation", collection_type: str
) -> List["DatasetCollectionElement"]:
    """Split up collection into collection."""
    return _split_dataset_collection(dataset_collection_instance.collection, collection_type)


def _split_dataset_collection(
    dataset_collection: "DatasetCollection", collection_type: str
) -> List["DatasetCollectionElement"]:
    this_collection_type = dataset_collection.collection_type
    if not this_collection_type.endswith(collection_type) or this_collection_type == collection_type:
        raise exceptions.MessageException("Cannot split collection in desired fashion.")

    split_elements = []
    for element in dataset_collection.elements:
        child_collection = element.child_collection
        if child_collection is None:
            raise exceptions.MessageException("Cannot split collection in desired fashion.")
        if child_collection.collection_type == collection_type:
            split_elements.append(element)
        else:
            split_elements.extend(_split_dataset_collection(element.child_collection, collection_type))

    return split_elements
