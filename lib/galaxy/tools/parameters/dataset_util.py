import galaxy.model

from logging import getLogger
log = getLogger( __name__ )

ROLES_UNSET = object()
INVALID_STATES = [ galaxy.model.Dataset.states.ERROR, galaxy.model.Dataset.states.DISCARDED ]


class DatasetParamContext( object ):

    def __init__( self, trans, history, param, value, other_values ):
        self.trans = trans
        self.history = history
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
        dataset = hda.dataset
        state_valid = not dataset.state in INVALID_STATES
        return state_valid and (not check_security or self.__can_access_dataset( dataset ) )

    def valid_hda_matches_format( self, hda, check_implicit_conversions=True, check_security=False ):
        if self.filter( hda ):
            return False
        formats = self.param.formats
        if hda.datatype.matches_any( formats ):
            return ValidParamHdaDirect( hda )
        if not check_implicit_conversions:
            return False
        target_ext, converted_dataset = hda.find_conversion_destination( formats )
        if target_ext:
            if converted_dataset:
                hda = converted_dataset
            if check_security and not self.__can_access_dataset( hda.dataset ):
                return False
            return ValidParamHdaImplicit(converted_dataset, target_ext)
        return False

    def valid_hda( self, hda, check_implicit_conversions=True ):
        accessible = self.hda_accessible( hda )
        if accessible and ( hda.visible or ( self.selected( hda ) and not hda.implicitly_converted_parent_datasets ) ):
            # If we are sending data to an external application, then we need to make sure there are no roles
            # associated with the dataset that restrict it's access from "public".
            require_public = self.tool and self.tool.tool_type == 'data_destination'
            if require_public and not self.trans.app.security_agent.dataset_is_public( hda.dataset ):
                return False
            if self.filter( hda ):
                return False
            return self.valid_hda_matches_format(hda)

    def selected( self, hda ):
        value = self.value
        return value and hda in value

    def filter( self, hda ):
        param = self.param
        return param.options and param._options_filter_attribute( hda ) != self.filter_value

    def __can_access_dataset( self, dataset ):
        if self.current_user_roles is ROLES_UNSET:
            self.current_user_roles = self.trans.get_current_user_roles()
        return self.trans.app.security_agent.can_access_dataset( self.current_user_roles, dataset )


class ValidParamHdaDirect( object ):

    def __init__( self, hda ):
        self.hda = hda

    @property
    def implicit_conversion( self ):
        return False


class ValidParamHdaImplicit( object ):

    def __init__( self, converted_dataset, target_ext ):
        self.hda = converted_dataset
        self.target_ext = target_ext

    @property
    def implicit_conversion( self ):
        return True


__all__ = [ DatasetParamContext ]
