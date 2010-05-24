from galaxy.web.base.controller import *
from galaxy.webapps.community import model
from galaxy.model.orm import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from common import get_categories, get_category, get_tools, get_event, get_tool, get_versions
import logging
log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

class UserListGrid( grids.Grid ):
    class EmailColumn( grids.TextColumn ):
        def get_value( self, trans, grid, user ):
            return user.email
    class UserNameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, user ):
            if user.username:
                return user.username
            return 'not set'
    class GroupsColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            if user.groups:
                return len( user.groups )
            return 0
    class RolesColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            if user.roles:
                return len( user.roles )
            return 0
    class ExternalColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            if user.external:
                return 'yes'
            return 'no'
    class LastLoginColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            if user.galaxy_sessions:
                return self.format( user.galaxy_sessions[ 0 ].update_time )
            return 'never'
    class StatusColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            if user.purged:
                return "purged"
            elif user.deleted:
                return "deleted"
            return ""
    class ToolsColumn( grids.TextColumn ):
        def get_value( self, trans, grid, user ):
            return '<a href="browse_tools_by_user?operation=browse&id=%s&webapp=community">%s</a>' % ( trans.security.encode_id( user.id ), str( len( user.tools ) ) )

    # Grid definition
    webapp = "community"
    title = "Users"
    model_class = model.User
    template='/admin/user/grid.mako'
    default_sort_key = "email"
    columns = [
        EmailColumn( "Email",
                     key="email",
                     model_class=model.User,
                     link=( lambda item: dict( operation="information", id=item.id, webapp="community" ) ),
                     attach_popup=True,
                     filterable="advanced" ),
        UserNameColumn( "User Name",
                        key="username",
                        model_class=model.User,
                        attach_popup=False,
                        filterable="advanced" ),
        GroupsColumn( "Groups", attach_popup=False ),
        RolesColumn( "Roles", attach_popup=False ),
        ExternalColumn( "External", attach_popup=False ),
        LastLoginColumn( "Last Login", format=time_ago ),
        StatusColumn( "Status", attach_popup=False ),
        ToolsColumn( "Uploaded Tools",
                     model_class=model.User,
                     attach_popup=False,
                     filterable="advanced" ),
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
    global_actions = [
        grids.GridAction( "Create new user",
                          dict( controller='admin', action='users', operation='create', webapp="community" ) )
    ]
    operations = [
        grids.GridOperation( "Manage Roles and Groups",
                             condition=( lambda item: not item.deleted ),
                             allow_multiple=False,
                             url_args=dict( webapp="community", action="manage_roles_and_groups_for_user" ) ),
        grids.GridOperation( "Reset Password",
                             condition=( lambda item: not item.deleted ),
                             allow_multiple=True,
                             allow_popup=False,
                             url_args=dict( webapp="community", action="reset_user_password" ) )
    ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True, purged=False ) ),
        grids.GridColumnFilter( "Purged", args=dict( purged=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def get_current_item( self, trans ):
        return trans.user
    def build_initial_query( self, trans ):
        return trans.sa_session.query( self.model_class )

class RoleListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, role ):
            return role.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, role ):
            if role.description:
                return role.description
            return ''
    class TypeColumn( grids.TextColumn ):
        def get_value( self, trans, grid, role ):
            return role.type
    class StatusColumn( grids.GridColumn ):
        def get_value( self, trans, grid, role ):
            if role.deleted:
                return "deleted"
            return ""
    class GroupsColumn( grids.GridColumn ):
        def get_value( self, trans, grid, role ):
            if role.groups:
                return len( role.groups )
            return 0
    class UsersColumn( grids.GridColumn ):
        def get_value( self, trans, grid, role ):
            if role.users:
                return len( role.users )
            return 0

    # Grid definition
    webapp = "community"
    title = "Roles"
    model_class = model.Role
    template='/admin/dataset_security/role/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="Manage users and groups", id=item.id, webapp="community" ) ),
                    model_class=model.Role,
                    attach_popup=True,
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key='description',
                           model_class=model.Role,
                           attach_popup=False,
                           filterable="advanced" ),
        TypeColumn( "Type",
                    key='type',
                    model_class=model.Role,
                    attach_popup=False,
                    filterable="advanced" ),
        GroupsColumn( "Groups", attach_popup=False ),
        UsersColumn( "Users", attach_popup=False ),
        StatusColumn( "Status", attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted",
                             key="deleted",
                             visible=False,
                             filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1], columns[2] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = [
        grids.GridAction( "Add new role",
                          dict( controller='admin', action='roles', operation='create', webapp="community" ) )
    ]
    operations = [ grids.GridOperation( "Rename",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=False,
                                        url_args=dict( webapp="community", action="rename_role" ) ),
                   grids.GridOperation( "Delete",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="mark_role_deleted" ) ),
                   grids.GridOperation( "Undelete",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="undelete_role" ) ),
                   grids.GridOperation( "Purge",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="purge_role" ) ) ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def get_current_item( self, trans ):
        return None
    def build_initial_query( self, trans ):
        return trans.sa_session.query( self.model_class )
    def apply_default_filter( self, trans, query, **kwd ):
        return query.filter( model.Role.type != model.Role.types.PRIVATE )

class GroupListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, group ):
            return group.name
    class StatusColumn( grids.GridColumn ):
        def get_value( self, trans, grid, group ):
            if group.deleted:
                return "deleted"
            return ""
    class RolesColumn( grids.GridColumn ):
        def get_value( self, trans, grid, group ):
            if group.roles:
                return len( group.roles )
            return 0
    class UsersColumn( grids.GridColumn ):
        def get_value( self, trans, grid, group ):
            if group.members:
                return len( group.members )
            return 0

    # Grid definition
    webapp = "community"
    title = "Groups"
    model_class = model.Group
    template='/admin/dataset_security/group/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    #key="name",
                    link=( lambda item: dict( operation="Manage users and roles", id=item.id, webapp="community" ) ),
                    model_class=model.Group,
                    attach_popup=True
                    #filterable="advanced"
                    ),
        UsersColumn( "Users", attach_popup=False ),
        RolesColumn( "Roles", attach_popup=False ),
        StatusColumn( "Status", attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted",
                             key="deleted",
                             visible=False,
                             filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1], columns[2] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = [
        grids.GridAction( "Add new group",
                          dict( controller='admin', action='groups', operation='create', webapp="community" ) )
    ]
    operations = [ grids.GridOperation( "Rename",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=False,
                                        url_args=dict( webapp="community", action="rename_group" ) ),
                   grids.GridOperation( "Delete",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="mark_group_deleted" ) ),
                   grids.GridOperation( "Undelete",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="undelete_group" ) ),
                   grids.GridOperation( "Purge",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="purge_group" ) ) ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def get_current_item( self, trans ):
        return None
    def build_initial_query( self, trans ):
        return trans.sa_session.query( self.model_class )

class ManageCategoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.description

    # Grid definition
    webapp = "community"
    title = "Manage Categories"
    model_class = model.Category
    template='/webapps/community/category/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="Edit", id=item.id, webapp="community" ) ),
                    model_class=model.Category,
                    attach_popup=False,
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key="description",
                           model_class=model.Category,
                           attach_popup=False,
                           filterable="advanced" ),
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
    global_actions = [
        grids.GridAction( "Add new category",
                          dict( controller='admin', action='manage_categories', operation='create', webapp="community" ) )
    ]
    operations = [ grids.GridOperation( "Delete",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="mark_category_deleted" ) ),
                   grids.GridOperation( "Undelete",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="undelete_category" ) ),
                   grids.GridOperation( "Purge",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="purge_category" ) ) ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def get_current_item( self, trans ):
        return None
    def build_initial_query( self, trans ):
        return trans.sa_session.query( self.model_class )

class ToolsByCategoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.description
    class ToolsColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            if category.tools:
                return len( category.tools )
            return 0

    # Grid definition
    webapp = "community"
    title = "Tools by Category"
    model_class = model.Category
    template='/webapps/community/category/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                     # TODO: we cannot currently sort by columns since the grid may be filtered by tool ids
                     # and it is not clear if / how that will work.  We need to be able to send to the grid helper
                     # the list of ids on which to filter when sorting on the column.
                    #key="name",
                    model_class=model.Category,
                    link=( lambda item: dict( operation="Browse Category", id=item.id, webapp="community" ) ),
                    attach_popup=False
                    #filterable="advanced" 
                    ),
        DescriptionColumn( "Description",
                           #key="description",
                           model_class=model.Category,
                           attach_popup=False
                           #filterable="advanced" 
                           ),
        ToolsColumn( "Tools",
                     model_class=model.Tool,
                     attach_popup=False,
                     filterable="advanced" ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted",
                             key="deleted",
                             visible=False,
                             filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search",
                                                #cols_to_filter=[ columns[0], columns[1] ],
                                                cols_to_filter=[],
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
    def build_initial_query( self, trans ):
        return trans.sa_session.query( self.model_class )
    def apply_default_filter( self, trans, query, **kwd ):
        ids = kwd.get( 'ids', False )
        if ids:
            if str( ids ).lower() == 'none':
                # No tools for display
                return query.filter( model.Tool.id == None )
            ids = util.listify( ids )
            query = query.filter( or_( *map( lambda id: self.model_class.id == id, ids ) ) )
        return query

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
                    rval += '<a href="browse_category?id=%s&webapp=community">%s</a><br/>\n' % ( trans.security.encode_id( tca.category.id ), tca.category.name ) 
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
            return '<a href="browse_tools_by_user?operation=browse&id=%s&webapp=community">%s</a>' % ( trans.security.encode_id( tool.user.id ), tool.user.username )
    # Grid definition
    title = "Tools"
    model_class = model.Tool
    template='/webapps/community/tool/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                     # TODO: we cannot currently sort by columns since the grid may be filtered by tool ids
                     # and it is not clear if / how that will work.  We need to be able to send to the grid helper
                     # the list of ids on which to filter when sorting on the column.
                    #key="name",
                    link=( lambda item: dict( operation="View Tool", id=item.id, cntrller="admin", webapp="community" ) ),
                    model_class=model.Tool,
                    attach_popup=True
                    #filterable="advanced"
                    ),
        VersionColumn( "Version",
                        model_class=model.Tool,
                        attach_popup=False,
                        filterable="advanced" ),
        DescriptionColumn( "Description",
                           #key="description",
                           model_class=model.Tool,
                           attach_popup=False
                           #filterable="advanced"
                           ),
        CategoryColumn( "Category",
                    model_class=model.Category,
                    attach_popup=False,
                    filterable="advanced" ),
        StateColumn( "Status",
                     model_class=model.Event,
                     attach_popup=False ),
        UserColumn( "Uploaded By",
                    model_class=model.User,
                    attach_popup=False,
                    filterable="advanced" ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted",
                             model_class=model.Tool,
                             key="deleted",
                             visible=False,
                             filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                #cols_to_filter=[ columns[0], columns[2], columns[5] ],
                                                cols_to_filter=[],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Edit information",
                             condition=( lambda item: not item.deleted ),
                             allow_multiple=False,
                             url_args=dict( controller="common", action="edit_tool", cntrller="admin", webapp="community" ) )
    ]
    standard_filters = [
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) ),
    ]
    default_filter = dict( name="All", deleted="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans ):
        return trans.sa_session.query( self.model_class )
    def apply_default_filter( self, trans, query, **kwd ):
        ids = kwd.get( 'ids', False )
        if ids:
            if str( ids ).lower() == 'none':
                # No tools for display
                return query.filter( model.Tool.id == None )
            ids = util.listify( ids )
            query = query.filter( or_( *map( lambda id: self.model_class.id == id, ids ) ) )
        return query

class AdminController( BaseController, Admin ):
    
    user_list_grid = UserListGrid()
    role_list_grid = RoleListGrid()
    group_list_grid = GroupListGrid()
    manage_category_list_grid = ManageCategoryListGrid()
    tools_by_category_list_grid = ToolsByCategoryListGrid()
    tool_list_grid = ToolListGrid()

    @web.expose
    @web.require_admin
    def browse_tools( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "edit tool":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='edit_tool',
                                                                  cntrller='admin',
                                                                  **kwd ) )
            elif operation == "view tool":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='view_tool',
                                                                  cntrller='admin',
                                                                  **kwd ) )
        # Render the list view
        return self.tool_list_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def browse_tools_by_category( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "browse category":
                return self.browse_category( trans, id=kwd['id'] )
        # Render the list view
        return self.tools_by_category_list_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def browse_tools_by_user( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "browse":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='browse_tools_by_user',
                                                                  cntrller='admin',
                                                                  **kwd ) )
            elif operation == "browse category":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='browse_category',
                                                                  cntrller='admin',
                                                                  **kwd ) )
            elif operation == "view tool":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='view_tool',
                                                                  cntrller='admin',
                                                                  **kwd ) )
            elif operation == "edit tool":
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='edit_tool',
                                                                  cntrller='admin',
                                                                  **kwd ) )
            elif operation == "download tool":
                return trans.response.send_redirect( web.url_for( controller='tool',
                                                                  action='download_tool',
                                                                  **kwd ) )
        # Render the list view
        return self.tool_list_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def manage_categories( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "create":
                return self.create_category( trans, **kwd )
            if operation == "delete":
                return self.mark_category_deleted( trans, **kwd )
            if operation == "undelete":
                return self.undelete_category( trans, **kwd )
            if operation == "purge":
                return self.purge_category( trans, **kwd )
            if operation == "edit":
                return self.edit_category( trans, **kwd )
        # Render the list view
        return self.manage_category_list_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def browse_tools_by_state( self, trans, state=None, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if state is None:
            id = params.get( 'id', None )
            if not id:
                return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                                  action='browse_tools',
                                                                  message='Select a status',
                                                                  status='error' ) )
            event = get_event( trans, id )
            state = event.state
        ids = get_tools_by_state( trans, state )
        if not ids:
            ids = 'none'
        return trans.response.send_redirect( web.url_for( controller='admin',
                                                          action='browse_tools',
                                                          ids=ids ) )
    @web.expose
    @web.require_admin
    def browse_category( self, trans, **kwd ):
        return trans.response.send_redirect( web.url_for( controller='common',
                                                          action='browse_category',
                                                          cntrller='admin',
                                                          **kwd ) )
    @web.expose
    @web.require_admin
    def create_category( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'community' )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if params.get( 'create_category_button', False ):
            name = util.restore_text( params.name )
            description = util.restore_text( params.description )
            if not name or not description:
                message = "Enter a valid name and a description"
            elif trans.sa_session.query( trans.app.model.Category ).filter( trans.app.model.Category.table.c.name==name ).first():
                message = "A category with that name already exists"
            else:
                # Create the category
                category = trans.app.model.Category( name=name, description=description )
                trans.sa_session.add( category )
                message = "Category '%s' has been created" % category.name
                trans.sa_session.flush()
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='manage_categories',
                                                           webapp=webapp,
                                                           message=util.sanitize_text( message ),
                                                           status='done' ) )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='create_category',
                                                       webapp=webapp,
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        return trans.fill_template( '/webapps/community/category/create_category.mako',
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def set_tool_state( self, trans, state, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        redirect = params.get( 'no_redirect', True )
        id = params.get( 'id', None )
        if not id:
            message = "No tool id received for setting status"
            status = 'error'
        else:
            tool = get_tool( trans, id )
            if state == trans.app.model.Tool.states.APPROVED:
                # If we're approving a tool, all previous versions must be set to archived
                for version in get_versions( trans, tool ):
                    if version != tool and version.is_approved():
                        self.set_tool_state( trans,
                                             trans.app.model.Tool.states.ARCHIVED,
                                             id=trans.security.encode_id( version.id ),
                                             redirect='False' )
            event = trans.model.Event( state )
            # Flush so we an get an id
            trans.sa_session.add( event )
            trans.sa_session.flush()
            tea = trans.model.ToolEventAssociation( tool, event )
            trans.sa_session.add( tea )
            trans.sa_session.flush()
            message = "State of tool '%s' is now %s" % ( tool.name, state )
        if redirect:
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='browse_tools',
                                                       webapp=webapp,
                                                       message=message,
                                                       status=status ) )
    @web.expose
    @web.require_admin
    def edit_category( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message = "No category ids received for editing"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='manage_categories',
                                                       webapp=webapp,
                                                       message=message,
                                                       status='error' ) )
        category = get_category( trans, id )
        if params.get( 'edit_category_button', False ):
            new_name = util.restore_text( params.get( 'name', '' ) ).strip()
            new_description = util.restore_text( params.get( 'description', '' ) ).strip()
            if category.name != new_name or category.description != new_description:
                if not new_name:
                    message = 'Enter a valid name'
                    status = 'error'
                elif category.name != new_name and \
                    trans.sa_session.query( trans.app.model.Category ).filter( trans.app.model.Category.table.c.name==new_name ).first():
                    message = 'A category with that name already exists'
                    status = 'error'
                else:
                    category.name = new_name
                    category.description = new_description
                    trans.sa_session.add( category )
                    trans.sa_session.flush()
                    message = "The information has been saved for category '%s'" % ( category.name )
                    return trans.response.send_redirect( web.url_for( controller='admin',
                                                                      action='manage_categories',
                                                                      webapp=webapp,
                                                                      message=util.sanitize_text( message ),
                                                                      status='done' ) )
        return trans.fill_template( '/webapps/community/category/edit_category.mako',
                                    category=category,
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def mark_category_deleted( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        id = kwd.get( 'id', None )
        if not id:
            message = "No category ids received for deleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='manage_categories',
                                                       webapp=webapp,
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Deleted %d categories: " % len( ids )
        for category_id in ids:
            category = get_category( trans, category_id )
            category.deleted = True
            trans.sa_session.add( category )
            trans.sa_session.flush()
            message += " %s " % category.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='manage_categories',
                                                   webapp=webapp,
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
    @web.expose
    @web.require_admin
    def undelete_category( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        id = kwd.get( 'id', None )
        if not id:
            message = "No category ids received for undeleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='manage_categories',
                                                       webapp=webapp,
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        count = 0
        undeleted_categories = ""
        for category_id in ids:
            category = get_category( trans, category_id )
            if not category.deleted:
                message = "Category '%s' has not been deleted, so it cannot be undeleted." % category.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='manage_categories',
                                                           webapp=webapp,
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            category.deleted = False
            trans.sa_session.add( category )
            trans.sa_session.flush()
            count += 1
            undeleted_categories += " %s" % category.name
        message = "Undeleted %d categories: %s" % ( count, undeleted_categories )
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='manage_categories',
                                                   webapp=webapp,
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
    @web.expose
    @web.require_admin
    def purge_category( self, trans, **kwd ):
        # This method should only be called for a Category that has previously been deleted.
        # Purging a deleted Category deletes all of the following from the database:
        # - ToolCategoryAssociations where category_id == Category.id
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        id = kwd.get( 'id', None )
        if not id:
            message = "No category ids received for purging"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='manage_categories',
                                                       webapp=webapp,
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Purged %d categories: " % len( ids )
        for category_id in ids:
            category = get_category( trans, category_id )
            if not category.deleted:
                message = "Category '%s' has not been deleted, so it cannot be purged." % category.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='manage_categories',
                                                           webapp=webapp,
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            # Delete ToolCategoryAssociations
            for tca in category.tools:
                trans.sa_session.delete( tca )
            trans.sa_session.flush()
            message += " %s " % category.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='manage_categories',
                                                   webapp=webapp,
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

## ---- Utility methods -------------------------------------------------------

def get_tools_by_state( trans, state ):
    # TODO: write this as a query using eagerload - will be much faster.
    ids = []
    if state == trans.model.Tool.states.NEW:
        for tool in get_tools( trans ):
            if tool.is_new():
                ids.append( tool.id )
    elif state == trans.model.Tool.states.ERROR:
        for tool in get_tools( trans ):
            if tool.is_error():
                ids.append( tool.id )
    elif state == trans.model.Tool.states.DELETED:
        for tool in get_tools( trans ):
            if tool.is_deleted():
                ids.append( tool.id )
    elif state == trans.model.Tool.states.WAITING:
        for tool in get_tools( trans ):
            if tool.is_waiting():
                ids.append( tool.id )
    elif state == trans.model.Tool.states.APPROVED:
        for tool in get_tools( trans ):
            if tool.is_approved():
                ids.append( tool.id )
    elif state == trans.model.Tool.states.REJECTED:
        for tool in get_tools( trans ):
            if tool.is_rejected():
                ids.append( tool.id )
    elif state == trans.model.Tool.states.ARCHIVED:
        for tool in get_tools( trans ):
            if tool.is_archived():
                ids.append( tool.id )
    return ids
