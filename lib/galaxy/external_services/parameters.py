# Contains parameters that are used in External Services
from galaxy.util import string_as_bool
from galaxy.util.template import fill_template


class ExternalServiceParameter( object ):
    """ Abstract Class for External Service Parameters """

    type = None
    requires_user_input = False

    @classmethod
    def from_elem( cls, elem, parent ):
        param_type = elem.get( 'type', None )
        assert param_type, 'ExternalServiceParameter requires a type'
        return parameter_type_to_class[ param_type ]( elem, parent )

    def __init__( self, elem, parent ):
        self.name = elem.get( 'name', None )
        assert self.name, 'ExternalServiceParameter requires a name'
        self.parent = parent

    def get_value( self, param_dict ):
        raise Exception( 'Abstract Method' )


class ExternalServiceTemplateParameter( ExternalServiceParameter ):
    """ Parameter that returns a string containing the requested content """

    type = 'template'

    def __init__( self, elem, parent ):
        ExternalServiceParameter.__init__( self, elem, parent )
        self.strip = string_as_bool( elem.get( 'strip', 'False' ) )
        self.text = elem.text

    def get_value( self, param_dict ):
        value = fill_template( self.text, context=param_dict )
        if self.strip:
            value = value.strip()
        return value


parameter_type_to_class = { ExternalServiceTemplateParameter.type: ExternalServiceTemplateParameter }
