import tarfile
from galaxy.web.base.controller import *
from galaxy.webapps.community import model
from galaxy.model.orm import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.web.form_builder import SelectField
import logging
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
                rval = '<ul>'
                for tca in tool.categories:
                    rval += '<li><a href="browse_tools?operation=tools_by_category&id=%s&webapp=community">%s</a></li>' \
                        % ( trans.security.encode_id( tca.category.id ), tca.category.name )
                rval += '</ul>'
                return rval
            return 'not set'
    class ToolCategoryColumn( grids.GridColumn ):
        def filter( self, trans, user, query, column_filter ):
            """Modify query to filter by category."""
            if column_filter == "All":
                pass
            return query.filter( model.Category.name == column_filter )
    class UserColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            if tool.user:
                return tool.user.email
            return 'no user'
    class EmailColumn( grids.GridColumn ):
        def filter( self, trans, user, query, column_filter ):
            if column_filter == 'All':
                return query
            return query.filter( and_( model.Tool.table.c.user_id == model.User.table.c.id,
                                       model.User.table.c.email == column_filter ) )
    # Grid definition
    title = "Tools"
    model_class = model.Tool
    template='/webapps/community/tool/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="View Tool", id=item.id, webapp="community" ) ),
                    model_class=model.Tool,
                    attach_popup=True
                    ),
        VersionColumn( "Version",
                       key="version",
                       model_class=model.Tool,
                       attach_popup=False,
                       filterable="advanced" ),
        DescriptionColumn( "Description",
                           key="description",
                           model_class=model.Tool,
                           attach_popup=False
                           ),
        CategoryColumn( "Category",
                        model_class=model.Category,
                        attach_popup=False,
                        filterable="advanced" ),
        UserColumn( "Uploaded By",
                    model_class=model.User,
                    link=( lambda item: dict( operation="tools_by_user", id=item.id, webapp="community" ) ),
                    attach_popup=False,
                    filterable="advanced" ),
        # Columns that are valid for filtering but are not visible.
        EmailColumn( "Email",
                     key="email",
                     model_class=model.User,
                     visible=False ),
        ToolCategoryColumn( "Category",
                            key="category",
                            model_class=model.Category,
                            visible=False ),
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1], columns[2] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Download tool",
                             condition=( lambda item: not item.deleted ),
                             allow_multiple=False,
                             url_args=dict( controller="tool", action="download_tool", cntrller="tool", webapp="community" ) )
        ]
    standard_filters = []
    default_filter = {}
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class ) \
                               .join( model.ToolEventAssociation.table ) \
                               .join( model.Event.table ) \
                               .join( model.ToolCategoryAssociation.table ) \
                               .join( model.Category.table )

class CategoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.description

    # Grid definition
    webapp = "community"
    title = "Categories"
    model_class = model.Category
    template='/webapps/community/category/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    model_class=model.Category,
                    link=( lambda item: dict( operation="tools_by_category", id=item.id, webapp="community" ) ),
                    attach_popup=False,
                    filterable="advanced"
                  ),
        DescriptionColumn( "Description",
                    key="description",
                    model_class=model.Category,
                    attach_popup=False,
                    filterable="advanced"
                  ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted",
                             key="deleted",
                             visible=False,
                             filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search",
                                                cols_to_filter=[ columns[0], columns[1] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    # Override these
    global_actions = []
    operations = []
    standard_filters = []
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True

class CommonController( BaseController ):
    @web.expose
    def edit_tool( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              message='Select a tool to edit',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        if params.get( 'edit_tool_button', False ):
            if params.get( 'in_categories', False ):
                in_categories = [ trans.sa_session.query( trans.app.model.Category ).get( x ) for x in util.listify( params.in_categories ) ]
                trans.app.security_agent.set_entity_category_associations( tools=[ tool ], categories=in_categories )
            else:
                # There must not be any categories associated with the tool
                trans.app.security_agent.set_entity_category_associations( tools=[ tool ], categories=[] )
            user_description = util.restore_text( params.get( 'user_description', '' ) )
            if user_description:
                tool.user_description = user_description
            else:
                tool.user_description = ''
            trans.sa_session.add( tool )
            trans.sa_session.flush()
            message="Tool '%s' description and category associations have been saved" % tool.name
            return trans.response.send_redirect( web.url_for( controller='common',
                                                              action='edit_tool',
                                                              cntrller=cntrller,
                                                              id=id,
                                                              message=message,
                                                              status='done' ) )
        elif params.get( 'approval_button', False ):
            if params.get( 'in_categories', False ):
                in_categories = [ trans.sa_session.query( trans.app.model.Category ).get( x ) for x in util.listify( params.in_categories ) ]
                trans.app.security_agent.set_entity_category_associations( tools=[ tool ], categories=in_categories )
            else:
                # There must not be any categories associated with the tool
                trans.app.security_agent.set_entity_category_associations( tools=[ tool ], categories=[] )
            user_description = util.restore_text( params.get( 'user_description', '' ) )
            if user_description:
                tool.user_description = user_description
            else:
                tool.user_description = ''
            trans.sa_session.add( tool )
            trans.sa_session.flush()
            # Move the state from NEW to WAITING
            event = trans.app.model.Event( state=trans.app.model.Tool.states.WAITING )
            tea = trans.app.model.ToolEventAssociation( tool, event )
            trans.sa_session.add_all( ( event, tea ) )
            trans.sa_session.flush()
            message = "Tool '%s' has been submitted for approval and can no longer be modified" % ( tool.name )
            return trans.response.send_redirect( web.url_for( controller='common',
                                                              action='view_tool',
                                                              cntrller=cntrller,
                                                              id=id,
                                                              message=message,
                                                              status='done' ) )
        in_categories = []
        out_categories = []
        for category in get_categories( trans ):
            if category in [ x.category for x in tool.categories ]:
                in_categories.append( ( category.id, category.name ) )
            else:
                out_categories.append( ( category.id, category.name ) )
        return trans.fill_template( '/webapps/community/tool/edit_tool.mako',
                                    cntrller=cntrller,
                                    tool=tool,
                                    id=id,
                                    in_categories=in_categories,
                                    out_categories=out_categories,
                                    message=message,
                                    status=status )
    @web.expose
    def view_tool( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              message='Select a tool to view',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        categories = [ tca.category for tca in tool.categories ]
        tool_file_contents = tarfile.open( tool.file_name, 'r' ).getnames()
        versions = get_versions( trans, tool )
        return trans.fill_template( '/webapps/community/tool/view_tool.mako',
                                    tool=tool,
                                    tool_file_contents=tool_file_contents,
                                    versions=versions,
                                    categories=categories,
                                    cntrller=cntrller,
                                    message=message,
                                    status=status )
    @web.expose
    def delete_tool( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message='Select a tool to delete'
            status='error'
        else:
            tool = get_tool( trans, id )
            # Create a new event
            event = trans.model.Event( state=trans.model.Tool.states.DELETED )
            # Flush so we can get an event id
            trans.sa_session.add( event )
            trans.sa_session.flush()
            # Associate the tool with the event
            tea = trans.model.ToolEventAssociation( tool=tool, event=event )
            # Delete the tool, keeping state for categories, events and versions
            tool.deleted = True
            trans.sa_session.add_all( ( tool, tea ) )
            trans.sa_session.flush()
            # TODO: What if the tool has versions, should they all be deleted?
            message = "Tool '%s' has been marked deleted"
            status = 'done'
        return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                          action='browse_tools',
                                                          message=message,
                                                          status=status ) )
    @web.expose
    def upload_new_tool_version( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              message='Select a tool to to upload a new version',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        return trans.response.send_redirect( web.url_for( controller='upload',
                                                          action='upload',
                                                          message=message,
                                                          status=status,
                                                          replace_id=id ) )

## ---- Utility methods -------------------------------------------------------

def get_versions( trans, tool ):
    versions = [tool]
    this_tool = tool
    while tool.newer_version:
        versions.insert( 0, tool.newer_version )
        tool = tool.newer_version
    tool = this_tool
    while tool.older_version:
        versions.append( tool.older_version[0] )
        tool = tool.older_version[0]
    return versions
def get_categories( trans ):
    """Get all categories from the database"""
    return trans.sa_session.query( trans.model.Category ) \
                           .filter( trans.model.Category.table.c.deleted==False ) \
                           .order_by( trans.model.Category.table.c.name ).all()
def get_category( trans, id ):
    return trans.sa_session.query( trans.model.Category ).get( trans.security.decode_id( id ) )
def get_tool( trans, id ):
    return trans.sa_session.query( trans.model.Tool ).get( trans.app.security.decode_id( id ) )
def get_tools( trans ):
    # Return only the latest version of each tool
    return trans.sa_session.query( trans.model.Tool ) \
                           .filter( trans.model.Tool.newer_version_id == None ) \
                           .order_by( trans.model.Tool.name )
def get_event( trans, id ):
    return trans.sa_session.query( trans.model.Event ).get( trans.security.decode_id( id ) )
def get_user( trans, id ):
    return trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( id ) )
