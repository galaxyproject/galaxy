from __future__ import absolute_import

from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import grids
from galaxy.model.orm import *
from galaxy.web.form_builder import *
from .requests_common import RequestsGrid
import logging

log = logging.getLogger( __name__ )

class UserRequestsGrid( RequestsGrid ):
    operations = [ operation for operation in RequestsGrid.operations ]
    operations.append( grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: item.is_unsubmitted and not item.deleted ) ) )
    operations.append( grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: item.is_new and not item.deleted ) ) )
    operations.append( grids.GridOperation( "Undelete", allow_multiple=True, condition=( lambda item: item.deleted ) ) )
    def apply_query_filter( self, trans, query, **kwd ):
        return query.filter_by( user=trans.user )

class Requests( BaseUIController ):
    request_grid = UserRequestsGrid()

    @web.expose
    @web.require_login( "view sequencing requests" )
    def index( self, trans ):
        return trans.fill_template( "requests/index.mako" )
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def find_samples_index( self, trans ):
        return trans.fill_template( "requests/find_samples_index.mako" )
    @web.expose
    def browse_requests( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "edit":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='edit_basic_request_info',
                                                                  cntrller='requests',
                                                                  **kwd ) )
            if operation == "add_samples":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='add_samples',
                                                                  cntrller='requests',
                                                                  **kwd ) )
            if operation == "edit_samples":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='edit_samples',
                                                                  cntrller='requests',
                                                                  **kwd ) )
            if operation == "view_request":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='view_request',
                                                                  cntrller='requests',
                                                                  **kwd ) )
            if operation == "delete":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='delete_request',
                                                                  cntrller='requests',
                                                                  **kwd ) )
            if operation == "undelete":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='undelete_request',
                                                                  cntrller='requests',
                                                                  **kwd ) )
            if operation == "view_request_history":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='view_request_history',
                                                                  cntrller='requests',
                                                                  **kwd ) )

        # If there are requests that have been rejected, show a message as a reminder to the user
        rejected = 0
        for request in trans.sa_session.query( trans.app.model.Request ) \
                            .filter( trans.app.model.Request.table.c.deleted==False ) \
                            .filter( trans.app.model.Request.table.c.user_id==trans.user.id ):
            if request.is_rejected:
                rejected = rejected + 1
        if rejected:
            status = 'warning'
            message = "%d requests (highlighted in red) were rejected.  Click on the request name for details." % rejected
            kwd[ 'status' ] = status
            kwd[ 'message' ] = message
        # Allow the user to create a new request only if they have permission to access a request type.
        accessible_request_types = trans.app.security_agent.get_accessible_request_types( trans, trans.user )
        if accessible_request_types:
            self.request_grid.global_actions = [ grids.GridAction( "Create new request", dict( controller='requests_common',
                                                                                               action='create_request',
                                                                                               cntrller='requests' ) ) ]
        else:
            self.request_grid.global_actions = []
        # Render the list view
        return self.request_grid( trans, **kwd )

