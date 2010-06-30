from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import model, util
from galaxy.util.streamball import StreamBall
from galaxy.util.odict import odict
import logging, tempfile, zipfile, tarfile, os, sys
from galaxy.web.form_builder import * 
from datetime import datetime, timedelta
from cgi import escape, FieldStorage

log = logging.getLogger( __name__ )

class RequestsGrid( grids.Grid ):
    # Custom column types
    class NameColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request):
            return request.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request):
            return request.desc
    class SamplesColumn( grids.GridColumn ):
        def get_value(self, trans, grid, request):
            return str(len(request.samples))
    class TypeColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request):
            return request.type.name
    class StateColumn( grids.GridColumn ):
        def __init__( self, col_name, key, model_class, event_class, filterable, link ):
            grids.GridColumn.__init__(self, col_name, key=key, model_class=model_class, filterable=filterable, link=link)
            self.event_class = event_class
        def get_value(self, trans, grid, request):
            if request.state() == request.states.REJECTED:
                return '<div class="count-box state-color-error">%s</div>' % request.state()
            elif request.state() == request.states.NEW:
                return '<div class="count-box state-color-queued">%s</div>' % request.state()
            elif request.state() == request.states.SUBMITTED:
                return '<div class="count-box state-color-running">%s</div>' % request.state()
            elif request.state() == request.states.COMPLETE:
                return '<div class="count-box state-color-ok">%s</div>' % request.state()
            return request.state()
        def filter( self, db_session, user, query, column_filter ):
            """ Modify query to filter request by state. """
            if column_filter == "All":
                return query
            if column_filter:
                # select r.id, r.name, re.id, re.state 
                # from request as r, request_event as re
                # where re.request_id=r.id and re.state='Complete' and re.create_time in
                #                        (select MAX( create_time)
                #                         from request_event
                #                         group by request_id)
                q = query.join(self.event_class.table)\
                         .filter( self.model_class.table.c.id==self.event_class.table.c.request_id )\
                         .filter( self.event_class.table.c.state==column_filter )\
                         .filter( self.event_class.table.c.id.in_(select(columns=[func.max(self.event_class.table.c.id)],
                                                                                  from_obj=self.event_class.table,
                                                                                  group_by=self.event_class.table.c.request_id)))
            return q
        def get_accepted_filters( self ):
            """ Returns a list of accepted filters for this column. """
            accepted_filter_labels_and_vals = [ model.Request.states.NEW,
                                                model.Request.states.REJECTED,
                                                model.Request.states.SUBMITTED,
                                                model.Request.states.COMPLETE,
                                                "All"]
            accepted_filters = []
            for val in accepted_filter_labels_and_vals:
                label = val.lower()
                args = { self.key: val }
                accepted_filters.append( grids.GridColumnFilter( label, args) )
            return accepted_filters
    # Grid definition
    title = "Sequencing Requests"
    template = 'requests/grid.mako'
    model_class = model.Request
    default_sort_key = "create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = True
    default_filter = dict( deleted="False")
    columns = [
        NameColumn( "Name", 
                    key="name", 
                    model_class=model.Request,
                    link=( lambda item: iff( item.deleted, None, dict( operation="show", id=item.id ) ) ),
                    attach_popup=True, 
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key='desc',
                           model_class=model.Request,
                           filterable="advanced" ),
        SamplesColumn( "Sample(s)", 
                       link=( lambda item: iff( item.deleted, None, dict( operation="show", id=item.id ) ) ), ),
        TypeColumn( "Type" ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        grids.DeletedColumn( "Deleted", 
                       key="deleted", 
                       visible=False, 
                       filterable="advanced" ),
        StateColumn( "State", 
                     model_class=model.Request,
                     event_class=model.RequestEvent,
                     key='state',
                     filterable="advanced",
                     link=( lambda item: iff( item.deleted, None, dict( operation="events", id=item.id ) ) ) )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Submit", allow_multiple=False, condition=( lambda item: not item.deleted and item.unsubmitted() and item.samples ),
                             confirm="More samples cannot be added to this request once it is submitted. Click OK to submit."  ),
        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted and item.unsubmitted() )  ),
        grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: not item.deleted and item.new() )  ),
        grids.GridOperation( "Undelete", allow_multiple=True, condition=( lambda item: item.deleted )  )

    ]
    global_actions = [
        grids.GridAction( "Create new request", dict( controller='requests_common',
                                                      cntrller='requests', 
                                                      action='new', 
                                                      select_request_type='True' ) )
    ]
    def apply_query_filter( self, trans, query, **kwd ):
        return query.filter_by( user=trans.user )

class Requests( BaseController ):
    request_grid = RequestsGrid()

    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def index( self, trans ):
        return trans.fill_template( "requests/index.mako" )

    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def list( self, trans, **kwd ):
        '''
        List all request made by the current user
        '''
        
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if not kwd.get( 'id', None ):
                return trans.response.send_redirect( web.url_for( controller='requests',
                                                                  action='list',
                                                                  status='error',
                                                                  message="Invalid request ID") )
            if operation == "show":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller='requests',
                                                                  action='show',
                                                                  **kwd ) )
            elif operation == "submit":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller='requests',
                                                                  action='submit',
                                                                  **kwd ) )
            elif operation == "delete":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller='requests',
                                                                  action='delete',
                                                                  **kwd ) )
            elif operation == "undelete":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller='requests',
                                                                  action='undelete',
                                                                  **kwd ) )
            elif operation == "edit":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller='requests',
                                                                  action='edit',
                                                                  show=True, **kwd ) )
            elif operation == "events":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller='requests',
                                                                  action='events',
                                                                  **kwd ) )
        # if there are one or more requests that has been rejected by the admin
        # recently, then show a message as a reminder to the user
        rlist = trans.sa_session.query( trans.app.model.Request ) \
                                .filter( trans.app.model.Request.table.c.deleted==False ) \
                                .filter( trans.app.model.Request.table.c.user_id==trans.user.id )
        rejected = 0
        for r in rlist:
            if r.rejected():
                rejected = rejected + 1
        if rejected:
            kwd['status'] = 'warning'
            kwd['message'] = "%d requests (highlighted in red) were rejected, click on the request name for details." \
                             % rejected 
        # Render the list view
        return self.request_grid( trans, **kwd )
    