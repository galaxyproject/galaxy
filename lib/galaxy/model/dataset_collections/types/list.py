from galaxy.model import DatasetCollectionElement
from . import BaseDatasetCollectionType


class ListDatasetCollectionType(BaseDatasetCollectionType):
    """A flat list of named elements."""

    collection_type = "list"

    def generate_elements(self, dataset_instances, **kwds):
        for identifier, element in dataset_instances.items():
            association = DatasetCollectionElement(
                element=element,
                element_identifier=identifier,
            )
            yield association
