from ..types import BaseDatasetCollectionType

from galaxy.model import DatasetCollectionElement

LEFT_IDENTIFIER = "left"
RIGHT_IDENTIFIER = "right"


class PairedDatasetCollectionType( BaseDatasetCollectionType ):
    """
    Paired (left/right) datasets.
    """
    collection_type = "paired"

    def __init__( self ):
        pass

    def build_collection( self, elements ):
        left_dataset = elements.get("left", None)
        right_dataset = elements.get("right", None)
        if not left_dataset or not right_dataset:
            self._validation_failed("Paired instance must define 'left' and 'right' datasets .")
        left_association = DatasetCollectionElement(
            element=left_dataset,
            element_identifier=LEFT_IDENTIFIER,
        )
        right_association = DatasetCollectionElement(
            element=right_dataset,
            element_identifier=RIGHT_IDENTIFIER,
        )
        return self._new_collection_for_elements([left_association, right_association])
