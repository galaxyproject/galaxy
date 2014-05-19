import galaxy.model

from logging import getLogger
log = getLogger( __name__ )

ROLES_UNSET = object()
INVALID_STATES = [ galaxy.model.Dataset.states.ERROR, galaxy.model.Dataset.states.DISCARDED ]


class DatasetMatcher( object ):
    """ Utility class to aid DataToolParameter and similar classes in reasoning
    about what HDAs could match or are selected for a parameter and value.

    Goal here is to both encapsulate and reuse logic related to filtering,
    datatype matching, hiding errored dataset, finding implicit conversions,
    and permission handling.
    """

    def __init__( self, trans, param, value, other_values ):
        self.trans = trans
        self.param = param
        self.tool = param.tool
        self.value = value
        self.current_user_roles = ROLES_UNSET
        filter_value = None
        if param.options:
            try:
                filter_value = param.options.get_options( trans, other_values )[0][0]
            except IndexError:
                pass  # no valid options
        self.filter_value = filter_value

    def hda_accessible( self, hda, check_security=True ):
        """ Does HDA correspond to dataset that is an a valid state and is
        accessible to user.
        """
        dataset = hda.dataset
        state_valid = not dataset.state in INVALID_STATES
        return state_valid and ( not check_security or self.__can_access_dataset( dataset ) )

    def valid_hda_match( self, hda, check_implicit_conversions=True, check_security=False ):
        """ Return False of this parameter can not be matched to a the supplied
        HDA, otherwise return a description of the match (either a
        HdaDirectMatch describing a direct match or a HdaImplicitMatch
        describing an implicit conversion.)
        """
        if self.filter( hda ):
            return False
        formats = self.param.formats
        if hda.datatype.matches_any( formats ):
            return HdaDirectMatch( hda )
        if not check_implicit_conversions:
            return False
        target_ext, converted_dataset = hda.find_conversion_destination( formats )
        if target_ext:
            if converted_dataset:
                hda = converted_dataset
            if check_security and not self.__can_access_dataset( hda.dataset ):
                return False
            return HdaImplicitMatch( hda, target_ext )
        return False

    def hda_match( self, hda, check_implicit_conversions=True, ensure_visible=True ):
        """ If HDA is accessible, return information about whether it could
        match this parameter and if so how. See valid_hda_match for more
        information.
        """
        accessible = self.hda_accessible( hda )
        if accessible and ( not ensure_visible or hda.visible or ( self.selected( hda ) and not hda.implicitly_converted_parent_datasets ) ):
            # If we are sending data to an external application, then we need to make sure there are no roles
            # associated with the dataset that restrict its access from "public".
            require_public = self.tool and self.tool.tool_type == 'data_destination'
            if require_public and not self.trans.app.security_agent.dataset_is_public( hda.dataset ):
                return False
            if self.filter( hda ):
                return False
            return self.valid_hda_match( hda, check_implicit_conversions=check_implicit_conversions )

    def selected( self, hda ):
        """ Given value for DataToolParameter, is this HDA "selected".
        """
        value = self.value
        if value and str( value[ 0 ] ).isdigit():
            return hda.id in map(int, value)
        else:
            return value and hda in value

    def filter( self, hda ):
        """ Filter out this value based on other values for job (if
        applicable).
        """
        param = self.param
        return param.options and param._options_filter_attribute( hda ) != self.filter_value

    def __can_access_dataset( self, dataset ):
        # Lazily cache current_user_roles.
        if self.current_user_roles is ROLES_UNSET:
            self.current_user_roles = self.trans.get_current_user_roles()
        return self.trans.app.security_agent.can_access_dataset( self.current_user_roles, dataset )


class HdaDirectMatch( object ):
    """ Supplied HDA was a valid option directly (did not need to find implicit
    conversion).
    """

    def __init__( self, hda ):
        self.hda = hda

    @property
    def implicit_conversion( self ):
        return False


class HdaImplicitMatch( object ):
    """ Supplied HDA was a valid option directly (did not need to find implicit
    conversion).
    """

    def __init__( self, hda, target_ext ):
        self.hda = hda
        self.target_ext = target_ext

    @property
    def implicit_conversion( self ):
        return True


class DatasetCollectionMatcher( object ):

    def __init__( self, dataset_matcher ):
        self.dataset_matcher = dataset_matcher

    def __valid_element( self, element ):
        # Simplify things for now and assume these are hdas and not implicit
        # converts. One could imagine handling both of those cases down the
        # road.
        if element.ldda:
            return False

        child_collection = element.child_collection
        if child_collection:
            return self.dataset_collection_match( child_collection )

        hda = element.hda
        if not hda:
            return False
        hda_match = self.dataset_matcher.hda_match( hda, ensure_visible=False )
        return hda_match and not hda_match.implicit_conversion

    def hdca_match( self, history_dataset_collection_association, reduction=False ):
        dataset_collection = history_dataset_collection_association.collection
        if reduction and dataset_collection.collection_type.find( ":" ) > 0:
            return False
        else:
            return self.dataset_collection_match( dataset_collection )

    def dataset_collection_match( self, dataset_collection ):
        valid = True
        for element in dataset_collection.elements:
            if not self.__valid_element( element ):
                valid = False
                break
        return valid

__all__ = [ DatasetMatcher, DatasetCollectionMatcher ]
