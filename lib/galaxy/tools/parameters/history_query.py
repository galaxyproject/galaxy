import logging
log = logging.getLogger( __name__ )


class HistoryQuery( object ):
    """ An object for describing the collections to pull out of a history,
    used by DataCollectionToolParameter.
    """

    def __init__( self, **kwargs ):
        self.collection_type = kwargs.get( "collection_type", None )

    @staticmethod
    def from_parameter_elem( elem ):
        """ Take in a tool parameter element.
        """
        kwargs = dict( collection_type=elem.get( "collection_type", None ) )
        return HistoryQuery( **kwargs )

    def direct_match( self, hdca ):
        if self.collection_type and hdca.collection.collection_type != self.collection_type:
            return False

        return True
