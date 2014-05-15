from ..types import BaseDatasetCollectionType

from galaxy.model import DatasetCollectionElement

FORWARD_IDENTIFIER = "forward"
REVERSE_IDENTIFIER = "reverse"

INVALID_IDENTIFIERS_MESSAGE = "Paired instance must define '%s' and '%s' datasets ." % ( FORWARD_IDENTIFIER, REVERSE_IDENTIFIER )


class PairedDatasetCollectionType( BaseDatasetCollectionType ):
    """
    Paired (left/right) datasets.
    """
    collection_type = "paired"

    def __init__( self ):
        pass

    def build_collection( self, elements ):
        forward_dataset = elements.get( FORWARD_IDENTIFIER, None )
        reverse_dataset = elements.get( REVERSE_IDENTIFIER, None )
        if not forward_dataset or not reverse_dataset:
            self._validation_failed( INVALID_IDENTIFIERS_MESSAGE )
        left_association = DatasetCollectionElement(
            element=forward_dataset,
            element_identifier=FORWARD_IDENTIFIER,
        )
        right_association = DatasetCollectionElement(
            element=reverse_dataset,
            element_identifier=REVERSE_IDENTIFIER,
        )
        return self._new_collection_for_elements([left_association, right_association])
