import sys, os, operator, string, shutil, re, socket, urllib, time, logging

from galaxy.web.base.controller import *
from galaxy.webapps.community import model
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *

log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

class ToolListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            if tool.name:
                return tool.name
            return 'not set'
    class CategoryColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            if tool.category:
                return tool.category
            return 'not set'

    # Grid definition
    title = "Tools"
    model_class = model.Tool
    template='/webapps/community/tool/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    model_class=model.Tool,
                    link=( lambda item: dict( operation="Edit Tool", id=item.id, webapp="community" ) ),
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
        grids.GridOperation( "View versions", condition=( lambda item: not item.deleted ), allow_multiple=False )
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
                return trans.response.send_redirect( web.url_for( controller='tool_browser',
                                                                  action='browse_tool',
                                                                  **kwargs ) )
            elif operation == "edit tool":
                return trans.response.send_redirect( web.url_for( controller='tool_browser',
                                                                  action='edit_tool',
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
    def edit_tool( self, trans, id=None, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        # Get the tool
        tool = None
        if id is not None:
            encoded_id = id
            id = trans.app.security.decode_id( id )
            tool = trans.sa_session.query( trans.model.Tool ).get( id )
        if tool is None:
            return trans.response.send_redirect( web.url_for( controller='tool_browser',
                                                              action='browse_tools',
                                                              message='Please select a Tool to edit (the tool ID provided was invalid)',
                                                              status='error' ) )
        if params.save_button and ( params.file_data != '' or params.url != '' ):
            # TODO: call the upload method in the upload controller.
            message = 'Uploading new version not implemented'
            status = 'error'
        elif params.save_button:
            tool.user_description = params.description
            tool.category = params.category
        categories = trans.sa_session.query( trans.model.Category ).order_by( trans.model.Category.table.c.name ).all()
        return trans.fill_template( '/webapps/community/tool/edit_tool.mako',
                                    encoded_id = encoded_id,
                                    tool=tool,
                                    categories=categories,
                                    message=message,
                                    status=status )
