"""
API operations on a sample tracking system.
"""
import logging

from sqlalchemy import and_, false

from galaxy import web
from galaxy.util.bunch import Bunch
from galaxy.web import url_for
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger( __name__ )


class RequestsAPIController( BaseAPIController ):
    _update_types = Bunch( REQUEST='request_state' )
    _update_type_values = [v[1] for v in _update_types.items()]

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/requests
        Displays a collection (list) of sequencing requests.
        """
        # if admin user then return all requests
        if trans.user_is_admin():
            query = trans.sa_session.query( trans.app.model.Request ) \
                .filter(  trans.app.model.Request.table.c.deleted == false() )\
                .all()
        else:
            query = trans.sa_session.query( trans.app.model.Request )\
                .filter( and_( trans.app.model.Request.table.c.user_id == trans.user.id and
                trans.app.model.Request.table.c.deleted == false() ) ) \
                .all()
        rval = []
        for request in query:
            item = request.to_dict()
            item['url'] = url_for( 'requests', id=trans.security.encode_id( request.id ) )
            item['id'] = trans.security.encode_id( item['id'] )
            if trans.user_is_admin():
                item['user'] = request.user.email
            rval.append( item )
        return rval

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        GET /api/requests/{encoded_request_id}
        Displays details of a sequencing request.
        """
        try:
            request_id = trans.security.decode_id( id )
        except TypeError:
            trans.response.status = 400
            return "Malformed id ( %s ) specified, unable to decode." % ( str( id ) )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( request_id )
        except:
            request = None
        if not request or not ( trans.user_is_admin() or request.user.id == trans.user.id ):
            trans.response.status = 400
            return "Invalid request id ( %s ) specified." % str( request_id )
        item = request.to_dict()
        item['url'] = url_for( 'requests', id=trans.security.encode_id( request.id ) )
        item['id'] = trans.security.encode_id( item['id'] )
        item['user'] = request.user.email
        item['num_of_samples'] = len(request.samples)
        return item

    @web.expose_api
    def update( self, trans, id, key, payload, **kwd ):
        """
        PUT /api/requests/{encoded_request_id}
        Updates a request state, sample state or sample dataset transfer status
        depending on the update_type
        """
        update_type = None
        if 'update_type' not in payload:
            trans.response.status = 400
            return "Missing required 'update_type' parameter.  Please consult the API documentation for help."
        else:
            update_type = payload.pop( 'update_type' )
        if update_type not in self._update_type_values:
            trans.response.status = 400
            return "Invalid value for 'update_type' parameter ( %s ) specified.  Please consult the API documentation for help." % update_type
        try:
            request_id = trans.security.decode_id( id )
        except TypeError:
            trans.response.status = 400
            return "Malformed  request id ( %s ) specified, unable to decode." % str( id )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( request_id )
        except:
            request = None
        if not request or not ( trans.user_is_admin() or request.user.id == trans.user.id ):
            trans.response.status = 400
            return "Invalid request id ( %s ) specified." % str( request_id )
        # check update type
        if update_type == 'request_state':
            return self.__update_request_state( trans, encoded_request_id=id )

    def __update_request_state( self, trans, encoded_request_id ):
        requests_common_cntrller = trans.webapp.controllers['requests_common']
        status, output = requests_common_cntrller.update_request_state( trans,
                                                                        cntrller='api',
                                                                        request_id=encoded_request_id )
        return status, output
