from galaxy.util import bunch
from galaxy import exceptions
from .structure import get_structure

CANNOT_MATCH_ERROR_MESSAGE = "Cannot match collection types."


class CollectionsToMatch( object ):
    """ Structure representing a set of collections that need to be matched up
    when running tools (possibly workflows in the future as well).
    """

    def __init__( self ):
        self.collections = {}

    def add( self, input_name, hdca, subcollection_type=None ):
        self.collections[ input_name ] = bunch.Bunch(
            hdca=hdca,
            subcollection_type=subcollection_type,
        )

    def has_collections( self ):
        return len( self.collections ) > 0

    def iteritems( self ):
        return self.collections.iteritems()


class MatchingCollections( object ):
    """ Structure holding the result of matching a list of collections
    together. This class being different than the class above and being
    created in the dataset_collections_service layer may seem like
    overkill but I suspect in the future plugins will be subtypable for
    instance so matching collections will need to make heavy use of the
    dataset collection type registry managed by the dataset collections
    sevice - hence the complexity now.
    """

    def __init__( self ):
        self.structure = None
        self.collections = {}

    def __attempt_add_to_match( self, input_name, hdca, collection_type_description, subcollection_type ):
        structure = get_structure( hdca, collection_type_description, leaf_subcollection_type=subcollection_type )
        if not self.structure:
            self.structure = structure
            self.collections[ input_name ] = hdca
        else:
            if not self.structure.can_match( structure ):
                raise exceptions.MessageException( CANNOT_MATCH_ERROR_MESSAGE )
            self.collections[ input_name ] = hdca

    def slice_collections( self ):
        return self.structure.walk_collections( self.collections )

    @staticmethod
    def for_collections( collections_to_match, collection_type_descriptions ):
        if not collections_to_match.has_collections():
            return None

        matching_collections = MatchingCollections()
        for input_key, to_match in collections_to_match.iteritems():
            hdca = to_match.hdca
            subcollection_type = to_match.subcollection_type
            collection_type_description = collection_type_descriptions.for_collection_type( hdca.collection.collection_type )
            matching_collections.__attempt_add_to_match( input_key, hdca, collection_type_description, subcollection_type )

        return matching_collections
