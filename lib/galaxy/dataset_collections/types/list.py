from ..types import BaseDatasetCollectionType

from galaxy.model import DatasetCollectionElement


class ListDatasetCollectionType( BaseDatasetCollectionType ):
    """ A flat list of named elements.
    """
    collection_type = "list"

    def __init__( self ):
        pass

    def generate_elements( self, elements ):
        for identifier, element in elements.iteritems():
            association = DatasetCollectionElement(
                element=element,
                element_identifier=identifier,
            )
            yield association
