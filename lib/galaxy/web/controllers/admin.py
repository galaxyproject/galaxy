from galaxy.web.base.controller import *
from galaxy import model
from galaxy.model.orm import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.tools.search import ToolBoxSearch
from galaxy.tools import ToolSection, json_fix
from galaxy.util import parse_xml, inflector
from galaxy.actions.admin import AdminActions
from galaxy.web.params import QuotaParamParser
from galaxy.exceptions import *
import galaxy.datatypes.registry
import logging

log = logging.getLogger( __name__ )

class UserListGrid( grids.Grid ):
    class EmailColumn( grids.TextColumn ):
        def get_value( self, trans, grid, user ):
            return user.email
    class UserNameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, user ):
            if user.username:
                return user.username
            return 'not set'
    class StatusColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            if user.purged:
                return "purged"
            elif user.deleted:
                return "deleted"
            return ""
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

    # Grid definition
    webapp = "galaxy"
    title = "Users"
    model_class = model.User
    template='/admin/user/grid.mako'
    default_sort_key = "email"
    columns = [
        EmailColumn( "Email",
                     key="email",
                     model_class=model.User,
                     link=( lambda item: dict( operation="information", id=item.id, webapp="galaxy" ) ),
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
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = [
        grids.GridAction( "Create new user", dict( controller='admin', action='users', operation='create', webapp="galaxy" ) )
    ]
    operations = [
        grids.GridOperation( "Manage Roles and Groups",
                             condition=( lambda item: not item.deleted ),
                             allow_multiple=False,
                             url_args=dict( webapp="galaxy", action="manage_roles_and_groups_for_user" ) ),
        grids.GridOperation( "Reset Password",
                             condition=( lambda item: not item.deleted ),
                             allow_multiple=True,
                             allow_popup=False,
                             url_args=dict( webapp="galaxy", action="reset_user_password" ) )
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
    def get_current_item( self, trans, **kwargs ):
        return trans.user

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
    webapp = "galaxy"
    title = "Roles"
    model_class = model.Role
    template='/admin/dataset_security/role/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="Manage users and groups", id=item.id, webapp="galaxy" ) ),
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
        grids.DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1], columns[2] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = [
        grids.GridAction( "Add new role", dict( controller='admin', action='roles', operation='create' ) )
    ]
    operations = [ grids.GridOperation( "Edit",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=False,
                                        url_args=dict( webapp="galaxy", action="rename_role" ) ),
                   grids.GridOperation( "Delete",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="galaxy", action="mark_role_deleted" ) ),
                   grids.GridOperation( "Undelete",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="galaxy", action="undelete_role" ) ),
                   grids.GridOperation( "Purge",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="galaxy", action="purge_role" ) ) ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def apply_query_filter( self, trans, query, **kwargs ):
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
    webapp = "galaxy"
    title = "Groups"
    model_class = model.Group
    template='/admin/dataset_security/group/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="Manage users and roles", id=item.id, webapp="galaxy" ) ),
                    model_class=model.Group,
                    attach_popup=True,
                    filterable="advanced" ),
        UsersColumn( "Users", attach_popup=False ),
        RolesColumn( "Roles", attach_popup=False ),
        StatusColumn( "Status", attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1], columns[2] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = [
        grids.GridAction( "Add new group", dict( controller='admin', action='groups', operation='create', webapp="galaxy" ) )
    ]
    operations = [ grids.GridOperation( "Rename",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=False,
                                        url_args=dict( webapp="galaxy", action="rename_group" ) ),
                   grids.GridOperation( "Delete",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="galaxy", action="mark_group_deleted" ) ),
                   grids.GridOperation( "Undelete",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="galaxy", action="undelete_group" ) ),
                   grids.GridOperation( "Purge",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="galaxy", action="purge_group" ) ) ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True

class QuotaListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, quota ):
            return quota.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, quota ):
            if quota.description:
                return quota.description
            return ''
    class AmountColumn( grids.TextColumn ):
        def get_value( self, trans, grid, quota ):
            return quota.operation + quota.display_amount
    class StatusColumn( grids.GridColumn ):
        def get_value( self, trans, grid, quota ):
            if quota.deleted:
                return "deleted"
            elif quota.default:
                return "<strong>default for %s users</strong>" % quota.default[0].type
            return ""
    class UsersColumn( grids.GridColumn ):
        def get_value( self, trans, grid, quota ):
            if quota.users:
                return len( quota.users )
            return 0
    class GroupsColumn( grids.GridColumn ):
        def get_value( self, trans, grid, quota ):
            if quota.groups:
                return len( quota.groups )
            return 0

    # Grid definition
    webapp = "galaxy"
    title = "Quotas"
    model_class = model.Quota
    template='/admin/quota/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="Change amount", id=item.id, webapp="galaxy" ) ),
                    model_class=model.Quota,
                    attach_popup=True,
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key='description',
                           model_class=model.Quota,
                           attach_popup=False,
                           filterable="advanced" ),
        AmountColumn( "Amount",
                    key='amount',
                    model_class=model.Quota,
                    attach_popup=False,
                    filterable="advanced" ),
        UsersColumn( "Users", attach_popup=False ),
        GroupsColumn( "Groups", attach_popup=False ),
        StatusColumn( "Status", attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1], columns[2] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = [
        grids.GridAction( "Add new quota", dict( controller='admin', action='quotas', operation='create' ) )
    ]
    operations = [ grids.GridOperation( "Rename",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=False,
                                        url_args=dict( webapp="galaxy", action="rename_quota" ) ),
                   grids.GridOperation( "Change amount",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=False,
                                        url_args=dict( webapp="galaxy", action="edit_quota" ) ),
                   grids.GridOperation( "Manage users and groups",
                                        condition=( lambda item: not item.default and not item.deleted ),
                                        allow_multiple=False,
                                        url_args=dict( webapp="galaxy", action="manage_users_and_groups_for_quota" ) ),
                   grids.GridOperation( "Set as different type of default",
                                        condition=( lambda item: item.default ),
                                        allow_multiple=False,
                                        url_args=dict( webapp="galaxy", action="set_quota_default" ) ),
                   grids.GridOperation( "Set as default",
                                        condition=( lambda item: not item.default and not item.deleted ),
                                        allow_multiple=False,
                                        url_args=dict( webapp="galaxy", action="set_quota_default" ) ),
                   grids.GridOperation( "Unset as default",
                                        condition=( lambda item: item.default and not item.deleted ),
                                        allow_multiple=False,
                                        url_args=dict( webapp="galaxy", action="unset_quota_default" ) ),
                   grids.GridOperation( "Delete",
                                        condition=( lambda item: not item.deleted and not item.default ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="galaxy", action="mark_quota_deleted" ) ),
                   grids.GridOperation( "Undelete",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="galaxy", action="undelete_quota" ) ),
                   grids.GridOperation( "Purge",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="galaxy", action="purge_quota" ) ) ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True

class ToolVersionListGrid( grids.Grid ):
    class ToolIdColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_version ):
            if tool_version.tool_id in trans.app.toolbox.tools_by_id:
                link = url_for( controller='tool_runner', tool_id=tool_version.tool_id )
                link_str = '<a href="%s">' % link
                return '<div class="count-box state-color-ok">%s%s</a></div>' % ( link_str, tool_version.tool_id )
            return tool_version.tool_id
    class ToolVersionsColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_version ):
            tool_ids_str = ''
            for tool_id in tool_version.get_version_ids( trans.app ):
                if tool_id in trans.app.toolbox.tools_by_id:
                    link = url_for( controller='tool_runner', tool_id=tool_version.tool_id )
                    link_str = '<a href="%s">' % link
                    tool_ids_str += '<div class="count-box state-color-ok">%s%s</a></div><br/>' % ( link_str, tool_id )
                else:
                    tool_ids_str += '%s<br/>' % tool_id
            return tool_ids_str
    # Grid definition
    title = "Tool versions"
    model_class = model.ToolVersion
    template='/admin/tool_version/grid.mako'
    default_sort_key = "tool_id"
    columns = [
        ToolIdColumn( "Tool id",
                      key='tool_id',
                      attach_popup=False ),
        ToolVersionsColumn( "Version lineage by tool id (parent/child ordered)" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search tool id", 
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = []
    operations = []
    standard_filters = []
    default_filter = {}
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class )

class AdminGalaxy( BaseUIController, Admin, AdminActions, UsesQuota, QuotaParamParser ):
    
    user_list_grid = UserListGrid()
    role_list_grid = RoleListGrid()
    group_list_grid = GroupListGrid()
    quota_list_grid = QuotaListGrid()
    tool_version_list_grid = ToolVersionListGrid()
    delete_operation = grids.GridOperation( "Delete", condition=( lambda item: not item.deleted ), allow_multiple=True )
    undelete_operation = grids.GridOperation( "Undelete", condition=( lambda item: item.deleted and not item.purged ), allow_multiple=True )
    purge_operation = grids.GridOperation( "Purge", condition=( lambda item: item.deleted and not item.purged ), allow_multiple=True )

    @web.expose
    @web.require_admin
    def quotas( self, trans, **kwargs ):
        if 'operation' in kwargs:
            operation = kwargs.pop('operation').lower()
            if operation == "quotas":
                return self.quota( trans, **kwargs )
            if operation == "create":
                return self.create_quota( trans, **kwargs )
            if operation == "delete":
                return self.mark_quota_deleted( trans, **kwargs )
            if operation == "undelete":
                return self.undelete_quota( trans, **kwargs )
            if operation == "purge":
                return self.purge_quota( trans, **kwargs )
            if operation == "change amount":
                return self.edit_quota( trans, **kwargs )
            if operation == "manage users and groups":
                return self.manage_users_and_groups_for_quota( trans, **kwargs )
            if operation == "rename":
                return self.rename_quota( trans, **kwargs )
            if operation == "edit":
                return self.edit_quota( trans, **kwargs )
        # Render the list view
        return self.quota_list_grid( trans, **kwargs )
    @web.expose
    @web.require_admin
    def create_quota( self, trans, **kwd ):
        params = self.get_quota_params( kwd )
        if params.get( 'create_quota_button', False ):
            try:
                quota, message = self._create_quota( params )
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='quotas',
                                                                  webapp=params.webapp,
                                                                  message=util.sanitize_text( message ),
                                                                  status='done' ) )
            except MessageException, e:
                params.message = str( e )
                params.status = 'error'
        in_users = map( int, params.in_users )
        in_groups = map( int, params.in_groups )
        new_in_users = []
        new_in_groups = []
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted==False ) \
                                    .order_by( trans.app.model.User.table.c.email ):
            if user.id in in_users:
                new_in_users.append( ( user.id, user.email ) )
            else:
                params.out_users.append( ( user.id, user.email ) )
        for group in trans.sa_session.query( trans.app.model.Group ) \
                                     .filter( trans.app.model.Group.table.c.deleted==False ) \
                                     .order_by( trans.app.model.Group.table.c.name ):
            if group.id in in_groups:
                new_in_groups.append( ( group.id, group.name ) )
            else:
                params.out_groups.append( ( group.id, group.name ) )
        return trans.fill_template( '/admin/quota/quota_create.mako',
                                    webapp=params.webapp,
                                    name=params.name,
                                    description=params.description,
                                    amount=params.amount,
                                    operation=params.operation,
                                    default=params.default,
                                    in_users=new_in_users,
                                    out_users=params.out_users,
                                    in_groups=new_in_groups,
                                    out_groups=params.out_groups,
                                    message=params.message,
                                    status=params.status )
    @web.expose
    @web.require_admin
    def rename_quota( self, trans, **kwd ):
        quota, params = self._quota_op( trans, 'rename_quota_button', self._rename_quota, kwd )
        if not quota:
            return
        return trans.fill_template( '/admin/quota/quota_rename.mako',
                                    id=params.id,
                                    name=params.name or quota.name,
                                    description=params.description or quota.description,
                                    webapp=params.webapp,
                                    message=params.message,
                                    status=params.status )
    @web.expose
    @web.require_admin
    def manage_users_and_groups_for_quota( self, trans, **kwd ):
        quota, params = self._quota_op( trans, 'quota_members_edit_button', self._manage_users_and_groups_for_quota, kwd )
        if not quota:
            return
        in_users = []
        out_users = []
        in_groups = []
        out_groups = []
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted==False ) \
                                    .order_by( trans.app.model.User.table.c.email ):
            if user in [ x.user for x in quota.users ]:
                in_users.append( ( user.id, user.email ) )
            else:
                out_users.append( ( user.id, user.email ) )
        for group in trans.sa_session.query( trans.app.model.Group ) \
                                     .filter( trans.app.model.Group.table.c.deleted==False ) \
                                     .order_by( trans.app.model.Group.table.c.name ):
            if group in [ x.group for x in quota.groups ]:
                in_groups.append( ( group.id, group.name ) )
            else:
                out_groups.append( ( group.id, group.name ) )
        return trans.fill_template( '/admin/quota/quota.mako',
                                    id=params.id,
                                    name=quota.name,
                                    in_users=in_users,
                                    out_users=out_users,
                                    in_groups=in_groups,
                                    out_groups=out_groups,
                                    webapp=params.webapp,
                                    message=params.message,
                                    status=params.status )
    @web.expose
    @web.require_admin
    def edit_quota( self, trans, **kwd ):
        quota, params = self._quota_op( trans, 'edit_quota_button', self._edit_quota, kwd )
        if not quota:
            return
        return trans.fill_template( '/admin/quota/quota_edit.mako',
                                    id=params.id,
                                    operation=params.operation or quota.operation,
                                    display_amount=params.amount or quota.display_amount,
                                    webapp=params.webapp,
                                    message=params.message,
                                    status=params.status )
    @web.expose
    @web.require_admin
    def set_quota_default( self, trans, **kwd ):
        quota, params = self._quota_op( trans, 'set_default_quota_button', self._set_quota_default, kwd )
        if not quota:
            return
        if params.default:
            default = params.default
        elif quota.default:
            default = quota.default[0].type
        else:
            default = "no"
        return trans.fill_template( '/admin/quota/quota_set_default.mako',
                                    id=params.id,
                                    default=default,
                                    webapp=params.webapp,
                                    message=params.message,
                                    status=params.status )
    @web.expose
    @web.require_admin
    def unset_quota_default( self, trans, **kwd ):
        quota, params = self._quota_op( trans, True, self._unset_quota_default, kwd )
        if not quota:
            return
        return trans.response.send_redirect( web.url_for( controller='admin',
                                                          action='quotas',
                                                          webapp=params.webapp,
                                                          message=util.sanitize_text( params.message ),
                                                          status='error' ) )
    @web.expose
    @web.require_admin
    def mark_quota_deleted( self, trans, **kwd ):
        quota, params = self._quota_op( trans, True, self._mark_quota_deleted, kwd, listify=True )
        if not quota:
            return
        return trans.response.send_redirect( web.url_for( controller='admin',
                                                          action='quotas',
                                                          webapp=params.webapp,
                                                          message=util.sanitize_text( params.message ),
                                                          status='error' ) )
    @web.expose
    @web.require_admin
    def undelete_quota( self, trans, **kwd ):
        quota, params = self._quota_op( trans, True, self._undelete_quota, kwd, listify=True )
        if not quota:
            return
        return trans.response.send_redirect( web.url_for( controller='admin',
                                                          action='quotas',
                                                          webapp=params.webapp,
                                                          message=util.sanitize_text( params.message ),
                                                          status='error' ) )
    @web.expose
    @web.require_admin
    def purge_quota( self, trans, **kwd ):
        quota, params = self._quota_op( trans, True, self._purge_quota, kwd, listify=True )
        if not quota:
            return
        return trans.response.send_redirect( web.url_for( controller='admin',
                                                          action='quotas',
                                                          webapp=params.webapp,
                                                          message=util.sanitize_text( params.message ),
                                                          status='error' ) )
    def _quota_op( self, trans, do_op, op_method, kwd, listify=False ):
        params = self.get_quota_params( kwd )
        if listify:
            quota = []
            messages = []
            for id in util.listify( params.id ):
                try:
                    quota.append( self.get_quota( trans, id ) )
                except MessageException, e:
                    messages.append( str( e ) )
            if messages:
                return None, trans.response.send_redirect( web.url_for( controller='admin',
                                                                        action='quotas',
                                                                        webapp=params.webapp,
                                                                        message=util.sanitize_text( ', '.join( messages ) ),
                                                                        status='error' ) )
        else:
            try:
                quota = self.get_quota( trans, params.id, deleted=False )
            except MessageException, e:
                return None, trans.response.send_redirect( web.url_for( controller='admin',
                                                                        action='quotas',
                                                                        webapp=params.webapp,
                                                                        message=util.sanitize_text( str( e ) ),
                                                                        status='error' ) )
        if do_op == True or ( do_op != False and params.get( do_op, False ) ):
            try:
                message = op_method( quota, params ) 
                return None, trans.response.send_redirect( web.url_for( controller='admin',
                                                                        action='quotas',
                                                                        webapp=params.webapp,
                                                                        message=util.sanitize_text( message ),
                                                                        status='done' ) )
            except MessageException, e:
                params.message = e.err_msg
                params.status = e.type
        return quota, params
    @web.expose
    @web.require_admin
    def impersonate( self, trans, email=None, **kwd ):
        if not trans.app.config.allow_user_impersonation:
            return trans.show_error_message( "User impersonation is not enabled in this instance of Galaxy." )
        message = ''
        status = 'done'
        emails = None
        if email is not None:
            user = trans.sa_session.query( trans.app.model.User ).filter_by( email=email ).first()
            if user:
                trans.set_user( user )
                message = 'You are now logged in as %s, <a target="_top" href="%s">return to the home page</a>' % ( email, url_for( controller='root' ) )
                emails = []
            else:
                message = 'Invalid user selected'
                status = 'error'
        if emails is None:
            emails = [ u.email for u in trans.sa_session.query( trans.app.model.User ).enable_eagerloads( False ).all() ]
        return trans.fill_template( 'admin/impersonate.mako', emails=emails, message=message, status=status )
      