import os, logging, urllib, tarfile

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
    class VersionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            return tool.version
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            return tool.description
    class CategoryColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            if tool.categories:
                rval = ''
                for tca in tool.categories:
                    rval += '<a href="browse_category?id=%s">%s</a><br/>\n' % ( trans.security.encode_id( tca.category.id ), tca.category.name ) 
                return rval
            return 'not set'
    class UserColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            return '<a href="browse_tools_by_user?operation=browse&id=%s">%s</a>' % ( trans.security.encode_id( tool.user.id ), tool.user.username )
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
        VersionColumn( "Version",
                        model_class=model.Tool,
                        attach_popup=False,
                        filterable="advanced" ),
        DescriptionColumn( "Description",
                        model_class=model.Tool,
                        attach_popup=False,
                        filterable="advanced" ),
        CategoryColumn( "Categories",
                        model_class=model.Category,
                        attach_popup=False,
                        filterable="advanced" ),
        UserColumn( "Uploaded By",
                    key="username",
                    model_class=model.User,
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
    default_filter = dict( name="All", deleted="False", username="All" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, session ):
        return session.query( self.model_class )
    def apply_default_filter( self, trans, query, **kwd ):
        def filter_query( query, tool_id ):
            if str( tool_id ).lower() in [ '', 'none' ]:
                # Return an empty query since the current user cannot view any
                # tools (possibly due to state not being approved, etc).
                return query.filter( model.Tool.id == None )
            tool_id = util.listify( tool_id )
            query = query.filter( or_( *map( lambda id: self.model_class.id == id, tool_id ) ) )
            return query.filter( self.model_class.deleted==False )
        tool_id = kwd.get( 'tool_id', False )
        if not tool_id:
            # Display only approved tools
            tool_id = get_approved_tools( trans )
            if not tool_id:
                tool_id = 'None'
        return filter_query( query, tool_id )

class ToolsByUserListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            return tool.name
    class VersionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            return tool.version
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            return tool.description
    class CategoryColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            if tool.categories:
                rval = ''
                for tca in tool.categories:
                    rval += '<a href="browse_category?id=%s">%s</a><br/>\n' % ( trans.security.encode_id( tca.category.id ), tca.category.name ) 
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
            return '<a href="browse_tools_by_user?operation=browse&id=%s">%s</a>' % ( trans.security.encode_id( tool.user.id ), tool.user.username )
    # Grid definition
    title = "Tools By User"
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
        VersionColumn( "Version",
                        model_class=model.Tool,
                        attach_popup=False,
                        filterable="advanced" ),
        DescriptionColumn( "Description",
                        model_class=model.Tool,
                        attach_popup=False,
                        filterable="advanced" ),
        CategoryColumn( "Categories",
                        model_class=model.Category,
                        attach_popup=False,
                        filterable="advanced" ),
        StateColumn( "Status",
                     model_class=model.Event,
                     attach_popup=False ),
        UserColumn( "Uploaded By",
                    key="username",
                    model_class=model.User,
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
    default_filter = dict( name="All", deleted="False", username="All" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, session ):
        return session.query( self.model_class )
    def apply_default_filter( self, trans, query, **kwd ):
        def filter_query( query, tool_id ):
            if str( tool_id ).lower() in [ '', 'none' ]:
                # Return an empty query since the current user cannot view any
                # tools (possibly due to state not being approved, etc).
                return query.filter( model.Tool.id == None )
            tool_id = util.listify( tool_id )
            query = query.filter( or_( *map( lambda id: self.model_class.id == id, tool_id ) ) )
            return query.filter( self.model_class.deleted==False )
        tool_id = kwd.get( 'tool_id', False )
        if not tool_id:
            # Display only approved tools
            tool_id = get_approved_tools( trans )
            if not tool_id:
                tool_id = 'None'
        return filter_query( query, tool_id )

class CategoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.description
    class ToolsColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            if category.tools:
                viewable_tools = 0
                for tca in category.tools:
                    tool = tca.tool
                    if tool.is_approved():
                        viewable_tools += 1
                return viewable_tools
            return 0

    # Grid definition
    webapp = "community"
    title = "Tool Categories"
    model_class = model.Category
    template='/webapps/community/category/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    model_class=model.Category,
                    link=( lambda item: dict( operation="Browse Category", id=item.id, webapp="community" ) ),
                    attach_popup=False,
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                        key="description",
                        model_class=model.Category,
                        attach_popup=False,
                        filterable="advanced" ),
        ToolsColumn( "Tools",
                     model_class=model.Tool,
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
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, session ):
        return session.query( self.model_class )
    def apply_default_filter( self, trans, query, **kwd ):
        return query.filter( self.model_class.deleted==False )

class ToolController( BaseController ):

    tool_list_grid = ToolListGrid()
    tools_by_user_list_grid = ToolsByUserListGrid()
    category_list_grid = CategoryListGrid()
    
    @web.expose
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/community/index.mako', message=message, status=status )
    @web.expose
    def browse_categories( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "browse category":
                return self.browse_category( trans, id=kwd['id'] )
            elif operation == "view tool":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='view_category',
                                                                  cntrller='tool',
                                                                  **kwd ) )
            elif operation == "edit tool":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='edit_category',
                                                                  cntrller='tool',
                                                                  **kwd ) )
        # Render the list view
        return self.category_list_grid( trans, **kwd )
    @web.expose
    def browse_category( self, trans, **kwd ):
        return trans.response.send_redirect( web.url_for( controller='common',
                                                          action='browse_category',
                                                          cntrller='tool',
                                                          **kwd ) )
    @web.expose
    def browse_tools( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "browse category":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='browse_category',
                                                                  cntrller='tool',
                                                                  **kwd ) )
            elif operation == "view tool":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='view_tool',
                                                                  cntrller='tool',
                                                                  **kwd ) )
            elif operation == "edit tool":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='edit_tool',
                                                                  cntrller='tool',
                                                                  **kwd ) )
            elif operation == "download tool":
                return trans.response.send_redirect( web.url_for( controller='tool',
                                                                  action='download_tool',
                                                                  **kwd ) )
        # Render the list view
        return self.tool_list_grid( trans, **kwd )
    @web.expose
    def browse_tools_by_user( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "browse":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='browse_tools_by_user',
                                                                  cntrller='tool',
                                                                  **kwd ) )
            elif operation == "browse category":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='browse_category',
                                                                  cntrller='tool',
                                                                  **kwd ) )
            elif operation == "view tool":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='view_tool',
                                                                  cntrller='tool',
                                                                  **kwd ) )
            elif operation == "edit tool":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='edit_tool',
                                                                  cntrller='tool',
                                                                  **kwd ) )
            elif operation == "download tool":
                return trans.response.send_redirect( web.url_for( controller='tool',
                                                                  action='download_tool',
                                                                  **kwd ) )
        # Render the list view
        return self.tools_by_user_list_grid( trans, **kwd )
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
    @web.expose
    def view_tool_file( self, trans, **kwd ):
        params = util.Params( kwd )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller='tool',
                                                              action='browse_tools',
                                                              message='Select a tool to download',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        tool_file_name = urllib.unquote_plus( kwd['file_name'] )
        tool_file = tarfile.open( tool.file_name ).extractfile( tool_file_name )
        trans.response.set_content_type( 'text/plain' )
        return tool_file
    @web.expose
    def help( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/community/tool/help.mako', message=message, status=status, **kwd )
