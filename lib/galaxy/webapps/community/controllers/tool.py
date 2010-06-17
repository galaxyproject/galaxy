import os, logging, urllib, tarfile

from galaxy.web.base.controller import *
from galaxy.webapps.community import model
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from common import *

log = logging.getLogger( __name__ )

class ApprovedToolListGrid( ToolListGrid ):
    def apply_query_filter( self, trans, query, **kwargs ):
        return query.filter( model.Event.table.c.state == 'approved' )

class MyToolsListGrid( ToolListGrid ):
    class StateColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            state = tool.state()
            if state == 'approved':
                state_color = 'ok'
            elif state == 'rejected':
                state_color = 'error'
            elif state == 'archived':
                state_color = 'upload'
            else:
                state_color = state
            return '<div class="count-box state-color-%s">%s</div>' % ( state_color, state )
    class ToolStateColumn( grids.StateColumn ):
        def filter( self, trans, user, query, column_filter ):
            """Modify query to filter self.model_class by state."""
            if column_filter == "All":
                pass
            elif column_filter in [ v for k, v in self.model_class.states.items() ]:
                # Get all of the latest ToolEventAssociation ids
                tea_ids = [ tea_id_tup[0] for tea_id_tup in trans.sa_session.query( func.max( model.ToolEventAssociation.table.c.id ) ) \
                                                                            .group_by( model.ToolEventAssociation.table.c.tool_id ) ]
                # Get all of the Event ids associated with the latest ToolEventAssociation ids
                event_ids = [ event_id_tup[0] for event_id_tup in trans.sa_session.query( model.ToolEventAssociation.table.c.event_id ) \
                                                                                  .filter( model.ToolEventAssociation.table.c.id.in_( tea_ids ) ) ]
                # Filter our query by state and event ids
                return query.filter( and_( model.Event.table.c.state == column_filter,
                                           model.Event.table.c.id.in_( event_ids ) ) )
            return query

    columns = [ col for col in ToolListGrid.columns ]
    columns.append(
        StateColumn( "Status",
                     model_class=model.Tool,
                     link=( lambda item: dict( operation="tools_by_state", id=item.id, webapp="community" ) ),
                     attach_popup=False )
    )
    columns.append(
        ToolStateColumn( "State",
                         key="state",
                         model_class=model.Tool,
                         visible=False,
                         filterable="advanced" )
    )

class ToolCategoryListGrid( CategoryListGrid ):
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

    columns = [ col for col in CategoryListGrid.columns ]
    columns.append(
        ToolsColumn( "Tools",
                     model_class=model.Tool,
                     attach_popup=False )
    )

class ToolController( BaseController ):

    tool_list_grid = ApprovedToolListGrid()
    my_tools_list_grid = MyToolsListGrid()
    category_list_grid = ToolCategoryListGrid()
    
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
            if operation in [ "tools_by_category", "tools_by_state", "tools_by_user" ]:
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                return self.browse_tools( trans, **kwd )
        # Render the list view
        return self.category_list_grid( trans, **kwd )
    @web.expose
    def browse_tools( self, trans, **kwd ):
        # We add params to the keyword dict in this method in order to rename the param
        # with an "f-" prefix, simulating filtering by clicking a search link.  We have
        # to take this approach because the "-" character is illegal in HTTP requests.
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "view tool":
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
            elif operation == "tools_by_user":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                if 'user_id' in kwd:
                    user = get_user( trans, kwd[ 'user_id' ] )
                    kwd[ 'f-email' ] = user.email
                    del kwd[ 'user_id' ]
                else:
                    # The received id is the tool id, so we need to get the id of the user
                    # that uploaded the tool.
                    tool_id = kwd.get( 'id', None )
                    tool = get_tool( trans, tool_id )
                    kwd[ 'f-email' ] = tool.user.email
            elif operation == "my_tools":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                kwd[ 'f-email' ] = trans.user.email
                return self.my_tools_list_grid( trans, **kwd )
            elif operation == "tools_by_category":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                category_id = kwd.get( 'id', None )
                category = get_category( trans, category_id )
                kwd[ 'f-category' ] = category.name
        # Render the list view
        return self.tool_list_grid( trans, **kwd )
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
