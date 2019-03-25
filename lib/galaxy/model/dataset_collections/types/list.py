from galaxy.model import DatasetCollectionElement
from ..types import BaseDatasetCollectionType


class ListDatasetCollectionType(BaseDatasetCollectionType):
    """ A flat list of named elements.
    """
    collection_type = "list"

    def __init__(self):
        pass

    def generate_elements(self, elements):
        for identifier, element in elements.items():
            association = DatasetCollectionElement(
                element=element,
                element_identifier=identifier,
            )
            yield association
