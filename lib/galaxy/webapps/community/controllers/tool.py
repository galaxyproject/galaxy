import sys, os, operator, string, shutil, re, socket, urllib, time, logging, mimetypes

from galaxy.web.base.controller import *
from galaxy.webapps.community import model
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from common import *

log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

class ToolListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            return tool.name
    class CategoryColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            if tool.categories:
                rval = ''
                for tca in tool.categories:
                    rval = '%s%s<br/>' % ( rval, tca.category.name )
                return rval
            return 'not set'
    class StateColumn( grids.GridColumn ):
        def get_value( self, trans, grid, tool ):
            state = tool.state()
            if state == tool.states.NEW:
                return '<div class="count-box state-color-queued">%s</div>' % state
            if state == tool.states.WAITING:
                return '<div class="count-box state-color-running">%s</div>' % state
            if state == tool.states.APPROVED:
                return '<div class="count-box state-color-ok">%s</div>' % state
            if state == tool.states.REJECTED or state == tool.states.ERROR:
                return '<div class="count-box state-color-error">%s</div>' % state
            return state
        def get_accepted_filters( self ):
            """ Returns a list of accepted filters for this column."""
            accepted_filter_labels_and_vals = [ model.Tool.states.NEW,
                                                model.Tool.states.WAITING,
                                                model.Tool.states.APPROVED,
                                                model.Tool.states.REJECTED,
                                                model.Tool.states.DELETED,
                                                "All" ]
            accepted_filters = []
            for val in accepted_filter_labels_and_vals:
                label = val.lower()
                args = { self.key: val }
                accepted_filters.append( grids.GridColumnFilter( label, args ) )
            return accepted_filters
    class UserColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            return tool.user.email
    # Grid definition
    title = "Tools"
    model_class = model.Tool
    template='/webapps/community/tool/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    model_class=model.Tool,
                    link=( lambda item: dict( operation="View Tool", id=item.id, cntrller='tool', webapp="community" ) ),
                    attach_popup=True,
                    filterable="advanced" ),
        CategoryColumn( "Category",
                    key="category",
                    model_class=model.Category,
                    attach_popup=False,
                    filterable="advanced" ),
        StateColumn( "State",
                     key="state",
                     model_class=model.Event,
                     attach_popup=False,
                     filterable="advanced" ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = [
        grids.GridAction( "Upload tool", dict( controller='upload', action='upload', type='tool' ) )
    ]
    operations = [
        grids.GridOperation( "Download tool",
                             condition=( lambda item: not item.deleted ),
                             allow_multiple=False,
                             url_args=dict( controller="tool", action="download_tool", cntrller="tool", webapp="community" ) )
        ]
    standard_filters = [
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    default_filter = dict( name="All", deleted="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, session ):
        return session.query( self.model_class )
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter( self.model_class.deleted==False )

class ToolBrowserController( BaseController ):
    
    tool_list_grid = ToolListGrid()
    
    @web.expose
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/community/index.mako', message=message, status=status )
    @web.expose
    def browse_tools( self, trans, **kwargs ):
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "browse":
                return trans.response.send_redirect( web.url_for( controller='tool',
                                                                  action='browse_tool',
                                                                  cntrller='tool',
                                                                  **kwargs ) )
            elif operation == "view tool":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='view_tool',
                                                                  cntrller='tool',
                                                                  **kwargs ) )
            elif operation == "edit tool":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='edit_tool',
                                                                  cntrller='tool',
                                                                  **kwargs ) )
            elif operation == "download tool":
                return trans.response.send_redirect( web.url_for( controller='tool',
                                                                  action='download_tool',
                                                                  **kwargs ) )
        # Render the list view
        return self.tool_list_grid( trans, **kwargs )
    @web.expose
    def browse_tool( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/community/tool/browse_tool.mako', 
                                    tools=tools,
                                    message=message,
                                    status=status )
    @web.expose
    def download_tool( self, trans, **kwd ):
        params = util.Params( kwd )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller='tool',
                                                              action='browse_tools',
                                                              message='Select a tool to download',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        trans.response.set_content_type( tool.mimetype )
        trans.response.headers['Content-Length'] = int( os.stat( tool.file_name ).st_size )
        trans.response.headers['Content-Disposition'] = 'attachment; filename=%s' % tool.download_file_name
        return open( tool.file_name )
