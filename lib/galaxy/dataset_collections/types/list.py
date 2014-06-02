from ..types import BaseDatasetCollectionType

from galaxy.model import DatasetCollectionElement


class ListDatasetCollectionType( BaseDatasetCollectionType ):
    """ A flat list of named elements.
    """
    collection_type = "list"

    def __init__( self ):
        pass

    def build_collection( self, elements ):
        associations = []
        for identifier, element in elements.iteritems():
            association = DatasetCollectionElement(
                element=element,
                element_identifier=identifier,
            )
            associations.append( association )

        return self._new_collection_for_elements( associations )
