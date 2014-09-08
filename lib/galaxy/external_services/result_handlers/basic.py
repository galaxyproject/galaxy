from galaxy.util.json import dumps, loads
from galaxy.util.template import fill_template
import logging

log = logging.getLogger( __name__ )


class ExternalServiceActionResultHandler( object ):
    """ Basic Class for External Service Actions Result Handlers"""

    type = 'display'

    @classmethod
    def from_elem( cls, elem, parent ):
        result_type = elem.get( 'type', None )
        assert result_type, 'ExternalServiceActionResultHandler requires a type'
        return result_type_to_class[ result_type ]( elem, parent )
    def __init__( self, elem, parent ):
        self.parent = parent
    def handle_result( self, result, param_dict, trans):
        return result.content
        #need to think about how to restore or set mime type:
        #both as specified in xml and also as set by an action,
        #    e.g. mimetype returned from web_api action should be reused here...

class ExternalServiceActionURLRedirectResultHandler( ExternalServiceActionResultHandler ):
    """ Basic Class for External Service Actions Result Handlers"""

    type = 'web_redirect'

    @classmethod
    def from_elem( cls, elem, parent ):
        result_type = elem.get( 'type', None )
        assert result_type, 'ExternalServiceActionResultHandler requires a type'
        return result_type_to_class[ result_type ]( elem, parent )
    def __init__( self, elem, parent ):
        self.parent = parent
    def handle_result( self, result, param_dict, trans ):
        return trans.response.send_redirect( result.content )

class ExternalServiceActionJSONResultHandler( ExternalServiceActionResultHandler ):
    """Class for External Service Actions JQuery Result Handler"""

    type = 'json_display'

    def handle_result( self, result, param_dict, trans ):
        rval = loads( result.content )
        return trans.fill_template( '/external_services/generic_json.mako', result = rval, param_dict = param_dict, action=self.parent )

class ExternalServiceActionJQueryGridResultHandler( ExternalServiceActionResultHandler ):
    """Class for External Service Actions JQuery Result Handler"""

    type = 'jquery_grid'

    def handle_result( self, result, param_dict, trans ):
        rval = loads( result.content )
        return trans.fill_template( '/external_services/generic_jquery_grid.mako', result = rval, param_dict = param_dict, action=self.parent )

result_type_to_class = {}
for handler_class in [ ExternalServiceActionResultHandler, ExternalServiceActionURLRedirectResultHandler, ExternalServiceActionJQueryGridResultHandler, ExternalServiceActionJSONResultHandler ]:
    result_type_to_class[handler_class.type] = handler_class
