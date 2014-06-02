import logging
log = logging.getLogger( __name__ )


class HistoryQuery( object ):
    """ An object for describing the collections to pull out of a history,
    used by DataCollectionToolParameter.
    """

    def __init__( self, **kwargs ):
        self.collection_type_description = kwargs.get( "collection_type_description", None )

    @staticmethod
    def from_parameter_elem( elem, collection_type_descriptions ):
        """ Take in a tool parameter element.
        """
        collection_type = elem.get( "collection_type", None )
        if collection_type:
            collection_type_description = collection_type_descriptions.for_collection_type( collection_type )
        else:
            collection_type_description = None
        kwargs = dict( collection_type_description=collection_type_description )
        return HistoryQuery( **kwargs )

    def direct_match( self, hdca ):
        collection_type_description = self.collection_type_description
        if collection_type_description and not collection_type_description.can_match_type( hdca.collection.collection_type ):
            return False

        return True

    def can_map_over( self, hdca ):
        collection_type_description = self.collection_type_description
        if not collection_type_description:
            return False

        hdca_collection_type = hdca.collection.collection_type
        return collection_type_description.is_subcollection_of_type( hdca_collection_type )
