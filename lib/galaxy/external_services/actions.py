#Contains actions that are used in External Services
import logging
from urllib import urlopen
from galaxy.web import url_for
from galaxy.util.template import fill_template
from result_handlers.basic import ExternalServiceActionResultHandler

log = logging.getLogger( __name__ )

class PopulatedExternalServiceAction( object ):
    def __init__( self, action, param_dict ):
        self.action = action
        self.param_dict = param_dict
        self.result = None
        self.handled_results = None
    def __getattr__( self, name ):
        return getattr( self.action, name )
    def get_action_access_link( self, trans ):
        return self.action.get_action_access_link( trans, self.param_dict )
    def perform_action( self ):
        if self.result is None:
            self.result = self.action.perform_action( self.param_dict )
        return self.result
    def handle_results( self, trans ):
        if self.result is None:
            self.perform_action()
        if self.handled_results is None:
            self.handled_results = self.action.handle_action( self.result, self.param_dict, trans )
        return self.handled_results

class ExternalServiceAction( object ):
    """ Abstract Class for External Service Actions """

    type = None

    @classmethod
    def from_elem( cls, elem, parent ):
        action_type = elem.get( 'type', None )
        assert action_type, 'ExternalServiceAction requires a type'
        return action_type_to_class[ action_type ]( elem, parent )
    def __init__( self, elem, parent ):
        self.name = elem.get( 'name', None )
        assert self.name, 'ExternalServiceAction requires a name'
        self.label = elem.get( 'label', self.name )
        self.parent = parent
        self.result_handlers = []
        for handler in elem.findall( 'result_handler' ):
            self.result_handlers.append( ExternalServiceActionResultHandler.from_elem( handler, self ) ) #parent ) )
    def __action_url_id( self, param_dict ):
        rval = self.name
        parent = self.parent
        while hasattr( parent.parent, 'parent' ):
            rval = "%s|%s" % ( parent.name, rval )
            parent = parent.parent
        rval = "%s|%s" % ( param_dict['service_instance'].id, rval )
        return rval
    def get_action_access_link( self, trans, param_dict ):
        return url_for( controller = '/external_services',
                        action = "access_action",
                        external_service_action=self.__action_url_id( param_dict ),
                        item = param_dict['item'].id,
                        item_type= param_dict['item'].__class__.__name__ )
    def populate_action( self, param_dict ):
        return PopulatedExternalServiceAction( self, param_dict )
    def handle_action( self, completed_action, param_dict, trans ):
        handled_results = []
        for handled_result in self.result_handlers:
            handled_results.append( handled_result.handle_result( completed_action, param_dict, trans ) )
        return handled_results
    def perform_action( self, param_dict ):
        raise 'Abstract Method'

class ExternalServiceResult( object ):
    def __init__( self, name, param_dict ):
        self.name = name
        self.param_dict = param_dict
    @property
    def content( self ):
        raise 'Abstract Method'

class ExternalServiceWebAPIActionResult( ExternalServiceResult ):
    def __init__( self, name, param_dict, url, method, target ):#, display_handler = None ):
        ExternalServiceResult.__init__( self, name, param_dict )
        self.url = url
        self.method = method
        self.target = target
        self._content = None
    @property
    def content( self ):
        if self._content is None:
            self._content =  urlopen( self.url ).read()
        return self._content

class ExternalServiceValueResult( ExternalServiceResult ):
    def __init__( self, name, param_dict, value ):
        self.name = name
        self.param_dict = param_dict
        self.value = value
    @property
    def content( self ):
        return self.value

class ExternalServiceWebAPIAction( ExternalServiceAction ):
    """ Action that accesses an external Web API and provides handlers for the requested content """

    type = 'web_api'

    class ExternalServiceWebAPIActionRequest( object ):
        def __init__( self, elem, parent ):
            self.target = elem.get( 'target', '_blank' )
            self.method = elem.get( 'method', 'post' )
            self.parent = parent
            self.url = Template( elem.find( 'url' ), parent )
        def get_web_api_action( self, param_dict ):
            name = self.parent.name
            target = self.target
            method = self.method
            url = self.url.build_template( param_dict ).strip()
            return ExternalServiceWebAPIActionResult( name, param_dict, url, method, target )

    def __init__( self, elem, parent ):
        ExternalServiceAction.__init__( self, elem, parent )
        self.web_api_request = self.ExternalServiceWebAPIActionRequest( elem.find( 'request' ), parent )
    def perform_action( self, param_dict ):
        return self.web_api_request.get_web_api_action( param_dict )

class ExternalServiceWebAction( ExternalServiceAction ):
    """ Action that accesses an external web application  """

    type = 'web'

    def __init__( self, elem, parent ):
        ExternalServiceAction.__init__( self, elem, parent )
        self.request_elem = elem.find( 'request' )
        self.url = Template( self.request_elem.find( 'url' ), parent )
        self.target = self.request_elem.get( 'target', '_blank' )
        self.method = self.request_elem.get( 'method', 'get' )
    def get_action_access_link( self, trans, param_dict ):
        url = self.url.build_template( param_dict ).strip()
        return url

class ExternalServiceTemplateAction( ExternalServiceAction ):
    """ Action that redirects to an external URL """

    type = 'template'

    def __init__( self, elem, parent ):
        ExternalServiceAction.__init__( self, elem, parent )
        self.template = Template( elem.find( 'template' ), parent )
    def perform_action( self, param_dict ):
        return ExternalServiceValueResult( self.name, param_dict, self.template.build_template( param_dict ) )

action_type_to_class = { ExternalServiceWebAction.type:ExternalServiceWebAction, ExternalServiceWebAPIAction.type:ExternalServiceWebAPIAction, ExternalServiceTemplateAction.type:ExternalServiceTemplateAction }

#utility classes
class Template( object ):
    def __init__( self, elem, parent ):
        self.text = elem.text
        self.parent = parent
    def build_template( self, param_dict ):
        template = fill_template( self.text, context = param_dict )
        return template
