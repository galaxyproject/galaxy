"""
API operations on RequestType objects.
"""
import logging
from galaxy.web.base.controller import BaseAPIController, url_for
from galaxy import web
from galaxy.sample_tracking.request_types import request_type_factory
from elementtree.ElementTree import XML

log = logging.getLogger( __name__ )


class RequestTypeAPIController( BaseAPIController ):
    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/request_types
        Displays a collection (list) of request_types.
        """
        rval = []
        for request_type in trans.app.security_agent.get_accessible_request_types( trans, trans.user ):
            item = request_type.get_api_value( value_mapper={ 'id': trans.security.encode_id, 'request_form_id': trans.security.encode_id, 'sample_form_id': trans.security.encode_id } )
            encoded_id = trans.security.encode_id( request_type.id )
            item['url'] = url_for( 'request_type', id=encoded_id )
            rval.append( item )
        return rval

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        GET /api/request_types/{encoded_request_type_id}
        Displays information about a request_type.
        """
        request_type_id = id
        try:
            decoded_request_type_id = trans.security.decode_id( request_type_id )
        except TypeError:
            trans.response.status = 400
            return "Malformed request type id ( %s ) specified, unable to decode." % str( request_type_id )
        try:
            request_type = trans.sa_session.query( trans.app.model.RequestType ).get( decoded_request_type_id )
        except:
            request_type = None
        if not request_type:# or not trans.user_is_admin():
            trans.response.status = 400
            return "Invalid request_type id ( %s ) specified." % str( request_type_id )
        if not trans.app.security_agent.can_access_request_type( trans.user.all_roles(), request_type ):
            trans.response.status = 400
            return "No permission to access request_type ( %s )." % str( request_type_id )
        item = request_type.get_api_value( view='element', value_mapper={ 'id': trans.security.encode_id, 'request_form_id': trans.security.encode_id, 'sample_form_id': trans.security.encode_id } )
        item['url'] = url_for( 'request_type', id=request_type_id )
        return item

    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/request_types
        Creates a new request type (external_service configuration).
        """
        if not trans.user_is_admin():
            trans.response.status = 403
            return "You are not authorized to create a new request type (external_service configuration)."
        xml_text = payload.get( 'xml_text', None )
        if xml_text is None:
            trans.response.status = 400
            return "Missing required parameter 'xml_text'."
        elem = XML( xml_text )
        request_form_id = payload.get( 'request_form_id', None )
        if request_form_id is None:
            trans.response.status = 400
            return "Missing required parameter 'request_form_id'."
        request_form = trans.sa_session.query( trans.app.model.FormDefinition ).get( trans.security.decode_id( request_form_id ) )
        sample_form_id = payload.get( 'sample_form_id', None )
        if sample_form_id is None:
            trans.response.status = 400
            return "Missing required parameter 'sample_form_id'."
        sample_form = trans.sa_session.query( trans.app.model.FormDefinition ).get( trans.security.decode_id( sample_form_id ) )
        external_service_id = payload.get( 'external_service_id', None )
        if external_service_id is None:
            trans.response.status = 400
            return "Missing required parameter 'external_service_id'."
        external_service = trans.sa_session.query( trans.app.model.ExternalService ).get( trans.security.decode_id( external_service_id ) )
        request_type = request_type_factory.from_elem( elem, request_form, sample_form, external_service )
        #FIXME: move permission building/setting to separate abstract method call and
        #allow setting individual permissions by role (currently only one action, so not strictly needed)
        role_ids = payload.get( 'role_ids', [] )
        roles = [ trans.sa_session.query( trans.model.Role ).get( trans.security.decode_id( i ) ) for i in role_ids ]# if trans.app.security_agent.ok_to_display( trans.user, i ) ]
        permissions = {}
        if roles:
            #yikes, there has to be a better way?
            for k, v in trans.model.RequestType.permitted_actions.items():
                permissions[ trans.app.security_agent.get_action( v.action ) ] = roles
        if permissions:
            trans.app.security_agent.set_request_type_permissions( request_type, permissions )
        
        #flush objects
        trans.sa_session.add( request_type )
        trans.sa_session.flush()
        encoded_id = trans.security.encode_id( request_type.id )
        item = request_type.get_api_value( view='element', value_mapper={ 'id': trans.security.encode_id, 'request_form_id': trans.security.encode_id, 'sample_form_id': trans.security.encode_id } )
        item['url'] = url_for( 'request_type', id=encoded_id )
        return [ item ]
