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

    def add( self, input_name, hdca ):
        self.collections[ input_name ] = bunch.Bunch(
            hdca=hdca,
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

    def __attempt_add_to_match( self, input_name, hdca ):
        structure = get_structure( hdca )
        if not self.structure:
            self.structure = structure
            self.collections[ input_name ] = hdca
        else:
            if not self.structure.can_match( structure ):
                raise exceptions.MessageException( CANNOT_MATCH_ERROR_MESSAGE )
            self.collections[ input_name ] = hdca

    @staticmethod
    def for_collections( collections_to_match ):
        if not collections_to_match.has_collections():
            return None

        matching_collections = MatchingCollections()
        for input_key, to_match in collections_to_match.iteritems():
            hdca = to_match.hdca
            matching_collections.__attempt_add_to_match( input_key, hdca )

        return matching_collections
