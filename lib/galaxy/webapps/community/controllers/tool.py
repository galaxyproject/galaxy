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
    class CategoryColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            if tool.categories:
                rval = ''
                for tca in tool.categories:
                    rval += '%s<br/>\n' % tca.category.name
                return rval
            return 'not set'
        def filter( self, trans, user, query, column_filter ):
            # Category.name conflicts with Tool.name, so we have to make our own filter
            def get_single_filter( filter ):
                return func.lower( model.Category.name ).like( "%" + filter.lower() + "%" )
            if column_filter == 'All':
                pass
            elif isinstance( column_filter, list ):
                clause_list = []
                for filter in column_filter:
                    clause_list.append( get_single_filter( filter ) )
                query = query.filter( or_( *clause_list ) )
            else:
                query = query.filter( get_single_filter( column_filter ) )
            return query
        def get_link( self, trans, grid, tool, filter_params ):
            if tool.categories:
                filter_params['f-category'] = []
                for tca in tool.categories:
                    filter_params['f-category'].append( tca.category.name )
                if len( filter_params['f-category'] ) == 1:
                    filter_params['f-category'] = filter_params['f-category'][0]
                filter_params['advanced-search'] = 'True'
                return filter_params
            return None
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
            return tool.user.username
        def get_link( self, trans, grid, tool, filter_params ):
            filter_params['f-username'] = tool.user.username
            filter_params['advanced-search'] = 'True'
            return filter_params
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
        CategoryColumn( "Categories",
                        key="category",
                        model_class=model.Tool,
                        attach_popup=False,
                        filterable="advanced" ),
        UserColumn( "Uploaded By",
                    key="username",
                    model_class=model.User,
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
        return session.query( self.model_class ).outerjoin( model.ToolCategoryAssociation ).outerjoin( model.Category )
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter( self.model_class.deleted==False )

class ToolCategoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.description
    # Grid definition
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
                        filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    standard_filters = [
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
    
    tool_category_list_grid = ToolCategoryListGrid()
    tool_list_grid = ToolListGrid()
    
    @web.expose
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/community/index.mako', message=message, status=status )
    @web.expose
    def browse_tool_categories( self, trans, **kwargs ):
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "browse category":
                category_id = int( trans.app.security.decode_id( kwargs['id'] ) )
                category = trans.sa_session.query( model.Category ).get( category_id )
                del kwargs['id']
                del kwargs['operation']
                kwargs['f-category'] = category.name
                return trans.response.send_redirect( web.url_for( controller='tool',
                                                                  action='browse_tools',
                                                                  **kwargs ) )
        return self.tool_category_list_grid( trans, **kwargs )
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
