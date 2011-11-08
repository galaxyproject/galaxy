from galaxy.web.base.controller import *
from galaxy import model
from galaxy.model.orm import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.tools.search import ToolBoxSearch
from galaxy.tools import json_fix
import logging
log = logging.getLogger( __name__ )

from galaxy.actions.admin import AdminActions
from galaxy.web.params import QuotaParamParser
from galaxy.exceptions import *

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
    #TODO: enhance to account for trans.app.config.allow_user_deletion here so that we can eliminate these operations if 
    # the setting is False
    #operations.append( grids.GridOperation( "Delete", condition=( lambda item: not item.deleted ), allow_multiple=True ) )
    #operations.append( grids.GridOperation( "Undelete", condition=( lambda item: item.deleted and not item.purged ), allow_multiple=True ) )
    #operations.append( grids.GridOperation( "Purge", condition=( lambda item: item.deleted and not item.purged ), allow_multiple=True ) )
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

class RepositoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.description
    class OwnerColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.owner
    class RevisionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.changeset_revision
    class ToolShedColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.tool_shed
    # Grid definition
    title = "Tool shed repositories"
    model_class = model.ToolShedRepository
    template='/admin/tool_shed_repository/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="manage_repository", id=item.id, webapp="galaxy" ) ),
                    attach_popup=False ),
        DescriptionColumn( "Description" ),
        OwnerColumn( "Owner" ),
        RevisionColumn( "Revision" ),
        ToolShedColumn( "Tool shed" ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted",
                             key="deleted",
                             visible=False,
                             filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name", 
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    standard_filters = []
    default_filter = dict( deleted="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class ) \
                               .filter( self.model_class.table.c.deleted == False )

class AdminGalaxy( BaseUIController, Admin, AdminActions, UsesQuota, QuotaParamParser ):
    
    user_list_grid = UserListGrid()
    role_list_grid = RoleListGrid()
    group_list_grid = GroupListGrid()
    quota_list_grid = QuotaListGrid()
    repository_list_grid = RepositoryListGrid()

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
    def browse_tool_shed_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = get_repository( trans, kwd[ 'id' ] )
        relative_install_dir = self.__get_relative_install_dir( trans, repository )
        repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, repository.name ) )
        tool_dicts = []
        workflow_dicts = []
        for root, dirs, files in os.walk( repo_files_dir ):
            if not root.find( '.hg' ) >= 0 and not root.find( 'hgrc' ) >= 0:
                if '.hg' in dirs:
                    # Don't visit .hg directories.
                    dirs.remove( '.hg' )
                if 'hgrc' in files:
                     # Don't include hgrc files.
                    files.remove( 'hgrc' )
                for name in files:
                    # Find all tool configs.
                    if name.endswith( '.xml' ):
                        try:
                            full_path = os.path.abspath( os.path.join( root, name ) )
                            tool = trans.app.toolbox.load_tool( full_path )
                            if tool is not None:
                                tool_config = os.path.join( root, name )
                                # Handle tool.requirements.
                                tool_requirements = []
                                for tr in tool.requirements:
                                    name=tr.name
                                    type=tr.type
                                    if type == 'fabfile':
                                        version = None
                                        fabfile = tr.fabfile
                                        method = tr.method
                                    else:
                                        version = tr.version
                                        fabfile = None
                                        method = None
                                    requirement_dict = dict( name=name,
                                                             type=type,
                                                             version=version,
                                                             fabfile=fabfile,
                                                             method=method )
                                    tool_requirements.append( requirement_dict )
                                tool_dict = dict( id=tool.id,
                                                  old_id=tool.old_id,
                                                  name=tool.name,
                                                  version=tool.version,
                                                  description=tool.description,
                                                  requirements=tool_requirements,
                                                  tool_config=tool_config )
                                tool_dicts.append( tool_dict )
                        except Exception, e:
                            # The file is not a Galaxy tool config.
                            pass
                    # Find all exported workflows
                    elif name.endswith( '.ga' ):
                        try:
                            full_path = os.path.abspath( os.path.join( root, name ) )
                            # Convert workflow data from json
                            fp = open( full_path, 'rb' )
                            workflow_text = fp.read()
                            fp.close()
                            workflow_dict = from_json_string( workflow_text )
                            if workflow_dict[ 'a_galaxy_workflow' ] == 'true':
                                workflow_dicts.append( dict( full_path=full_path, workflow_dict=workflow_dict ) )
                        except Exception, e:
                            # The file is not a Galaxy workflow.
                            pass
        return trans.fill_template( '/admin/tool_shed_repository/browse_repository.mako',
                                    repository=repository,
                                    tool_dicts=tool_dicts,
                                    workflow_dicts=workflow_dicts,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def browse_tool_shed_repositories( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd.pop( 'operation' ).lower()
            if operation == "manage_repository":
                return self.manage_tool_shed_repository( trans, **kwd )
        # Render the list view
        return self.repository_list_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def browse_tool_sheds( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/galaxy/admin/tool_sheds.mako',
                                    webapp='galaxy',
                                    message=message,
                                    status='error' )
    @web.expose
    @web.require_admin
    def find_tools_in_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = trans.request.host
        url = '%s/repository/find_tools?galaxy_url=%s&webapp=galaxy' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def find_workflows_in_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = trans.request.host
        url = '%s/repository/find_workflows?galaxy_url=%s&webapp=galaxy' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def browse_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = trans.request.host
        url = '%s/repository/browse_valid_repositories?galaxy_url=%s&webapp=galaxy' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def install_tool_shed_repository( self, trans, **kwd ):
        if not trans.app.toolbox.shed_tool_confs:
            message = 'The <b>tool_config_file</b> setting in <b>universe_wsgi.ini</b> must include at least one shed tool configuration file name with a '
            message += '<b>&lt;toolbox&gt;</b> tag that includes a <b>tool_path</b> attribute value which is a directory relative to the Galaxy installation '
            message += 'directory in order to automatically install tools from a Galaxy tool shed (e.g., the file name <b>shed_tool_conf.xml</b> whose '
            message += '<b>&lt;toolbox&gt;</b> tag is <b>&lt;toolbox tool_path="../shed_tools"&gt;</b>).<p/>See the '
            message += '<a href="http://wiki.g2.bx.psu.edu/Tool%20Shed#Automatic_installation_of_Galaxy_tool_shed_repository_tools_into_a_local_Galaxy_instance" '
            message += 'target="_blank">Automatic installation of Galaxy tool shed repository tools into a local Galaxy instance</a> section of the '
            message += '<a href="http://wiki.g2.bx.psu.edu/Tool%20Shed" target="_blank">Galaxy tool shed wiki</a> for all of the details.'
            return trans.show_error_message( message )
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        tool_shed_url = kwd[ 'tool_shed_url' ]
        repo_info_dict = kwd[ 'repo_info_dict' ]
        if kwd.get( 'select_tool_panel_section_button', False ):
            shed_tool_conf = kwd[ 'shed_tool_conf' ]
            # Get the tool path.
            for k, tool_path in trans.app.toolbox.shed_tool_confs.items():
                if k == shed_tool_conf:
                    break
            if 'tool_panel_section' in kwd:
                section_key = 'section_%s' % kwd[ 'tool_panel_section' ]
                tool_section = trans.app.toolbox.tool_panel[ section_key ]
                # Decode the encoded repo_info_dict param value.
                repo_info_dict = tool_shed_decode( repo_info_dict )
                # Clone the repository to the configured location.
                current_working_dir = os.getcwd()
                for name, repo_info_tuple in repo_info_dict.items():
                    description, repository_clone_url, changeset_revision = repo_info_tuple
                    clone_dir = os.path.join( tool_path, self.__generate_tool_path( repository_clone_url, changeset_revision ) )
                    if os.path.exists( clone_dir ):
                        # Repository and revision has already been cloned.
                        # TODO: implement the ability to re-install or revert an existing repository.
                        message += 'Revision <b>%s</b> of repository <b>%s</b> has already been installed.  Updating an existing repository is not yet supported.<br/>' % \
                        ( changeset_revision, name )
                        status = 'error'
                    else:
                        os.makedirs( clone_dir )
                        log.debug( 'Cloning %s...' % repository_clone_url )
                        cmd = 'hg clone %s' % repository_clone_url
                        tmp_name = tempfile.NamedTemporaryFile().name
                        tmp_stderr = open( tmp_name, 'wb' )
                        os.chdir( clone_dir )
                        proc = subprocess.Popen( args=cmd, shell=True, stderr=tmp_stderr.fileno() )
                        returncode = proc.wait()
                        os.chdir( current_working_dir )
                        tmp_stderr.close()
                        if returncode == 0:
                            # Add a new record to the tool_shed_repository table if one doesn't
                            # already exist.  If one exists but is marked deleted, undelete it.
                            self.__create_or_undelete_tool_shed_repository( trans, name, description, changeset_revision, repository_clone_url )
                            # Update the cloned repository to changeset_revision.
                            repo_files_dir = os.path.join( clone_dir, name )
                            log.debug( 'Updating cloned repository to revision "%s"...' % changeset_revision )
                            cmd = 'hg update -r %s' % changeset_revision
                            tmp_name = tempfile.NamedTemporaryFile().name
                            tmp_stderr = open( tmp_name, 'wb' )
                            os.chdir( repo_files_dir )
                            proc = subprocess.Popen( cmd, shell=True, stderr=tmp_stderr.fileno() )
                            returncode = proc.wait()
                            os.chdir( current_working_dir )
                            tmp_stderr.close()
                            if returncode == 0:
                                sample_files, repository_tools_tups = self.__get_repository_tools_and_sample_files( trans, tool_path, repo_files_dir )
                                if repository_tools_tups:
                                    # Handle missing data table entries for tool parameters that are dynamically generated select lists.
                                    repository_tools_tups = self.__handle_missing_data_table_entry( trans, tool_path, sample_files, repository_tools_tups )
                                    # Handle missing index files for tool parameters that are dynamically generated select lists.
                                    repository_tools_tups = self.__handle_missing_index_file( trans, tool_path, sample_files, repository_tools_tups )
                                    # Handle tools that use fabric scripts to install dependencies.
                                    self.__handle_tool_dependencies( current_working_dir, repo_files_dir, repository_tools_tups )
                                    # Generate an in-memory tool conf section that includes the new tools.
                                    new_tool_section = self.__generate_tool_panel_section( name,
                                                                                           repository_clone_url,
                                                                                           changeset_revision,
                                                                                           tool_section,
                                                                                           repository_tools_tups )
                                    # Create a temporary file to persist the in-memory tool section
                                    # TODO: Figure out how to do this in-memory using xml.etree.
                                    tmp_name = tempfile.NamedTemporaryFile().name
                                    persisted_new_tool_section = open( tmp_name, 'wb' )
                                    persisted_new_tool_section.write( new_tool_section )
                                    persisted_new_tool_section.close()
                                    # Parse the persisted tool panel section
                                    tree = ElementTree.parse( tmp_name )
                                    root = tree.getroot()
                                    ElementInclude.include( root )
                                    # Load the tools in the section into the tool panel.
                                    trans.app.toolbox.load_section_tag_set( root, trans.app.toolbox.tool_panel, tool_path )
                                    # Remove the temporary file
                                    try:
                                        os.unlink( tmp_name )
                                    except:
                                        pass
                                    # Append the new section to the shed_tool_config file.
                                    self.__add_shed_tool_conf_entry( trans, shed_tool_conf, new_tool_section )
                                    if trans.app.toolbox_search.enabled:
                                        # If search support for tools is enabled, index the new installed tools.
                                        trans.app.toolbox_search = ToolBoxSearch( trans.app.toolbox )
                                message += 'Revision <b>%s</b> of repository <b>%s</b> has been loaded into tool panel section <b>%s</b>.<br/>' % \
                                    ( changeset_revision, name, tool_section.name )
                                #return trans.show_ok_message( message )
                            else:
                                tmp_stderr = open( tmp_name, 'rb' )
                                message += '%s<br/>' % tmp_stderr.read()
                                tmp_stderr.close()
                                status = 'error'
                        else:
                            tmp_stderr = open( tmp_name, 'rb' )
                            message += '%s<br/>' % tmp_stderr.read()
                            tmp_stderr.close()
                            status = 'error'
            else:
                message = 'Choose the section in your tool panel to contain the installed tools.'
                status = 'error'
        if len( trans.app.toolbox.shed_tool_confs.keys() ) > 1:
            shed_tool_conf_select_field = build_shed_tool_conf_select_field( trans )
            shed_tool_conf = None
        else:
            shed_tool_conf = trans.app.toolbox.shed_tool_confs.keys()[0].lstrip( './' )
            shed_tool_conf_select_field = None
        tool_panel_section_select_field = build_tool_panel_section_select_field( trans )
        return trans.fill_template( '/admin/select_tool_panel_section.mako',
                                    tool_shed_url=tool_shed_url,
                                    repo_info_dict=repo_info_dict,
                                    shed_tool_conf=shed_tool_conf,
                                    shed_tool_conf_select_field=shed_tool_conf_select_field,
                                    tool_panel_section_select_field=tool_panel_section_select_field,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def manage_tool_shed_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository_id = params.get( 'id', None )
        repository = get_repository( trans, repository_id )
        description = util.restore_text( params.get( 'description', repository.description ) )
        if params.get( 'edit_repository_button', False ):
            if description != repository.description:
                repository.description = description
                trans.sa_session.add( repository )
                trans.sa_session.flush()
            message = "The repository information has been updated."
        relative_install_dir = self.__get_relative_install_dir( trans, repository )
        if relative_install_dir:
            repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, repository.name ) )
        else:
            repo_files_dir = 'unknown'
        return trans.fill_template( '/admin/tool_shed_repository/manage_repository.mako',
                                    repository=repository,
                                    description=description,
                                    repo_files_dir=repo_files_dir,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def check_for_updates( self, trans, **kwd ):
        params = util.Params( kwd )
        repository = get_repository( trans, kwd[ 'id' ] )
        galaxy_url = trans.request.host
        # Send a request to the relevant tool shed to see if there are any updates.
        # TODO: support https in the following url.
        url = 'http://%s/repository/check_for_updates?galaxy_url=%s&name=%s&owner=%s&changeset_revision=%s&webapp=galaxy' % \
            ( repository.tool_shed, galaxy_url, repository.name, repository.owner, repository.changeset_revision )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def update_to_changeset_revision( self, trans, **kwd ):
        """Update a cloned repository to the latest revision possible."""
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        tool_shed_url = kwd[ 'tool_shed_url' ]
        name = params.get( 'name', None )
        owner = params.get( 'owner', None )
        changeset_revision = params.get( 'changeset_revision', None )
        latest_changeset_revision = params.get( 'latest_changeset_revision', None )
        repository = get_repository_by_shed_name_owner_changeset_revision( trans, tool_shed_url, name, owner, changeset_revision )
        if changeset_revision and latest_changeset_revision:
            if changeset_revision == latest_changeset_revision:
                message = "The cloned tool shed repository named '%s' is current (there are no updates available)." % name
            else:
                current_working_dir = os.getcwd()
                relative_install_dir = self.__get_relative_install_dir( trans, repository )
                if relative_install_dir:
                    # Update the cloned repository to changeset_revision.
                    repo_files_dir = os.path.join( relative_install_dir, name )
                    log.debug( "Updating cloned repository named '%s' from revision '%s' to revision '%s'..." % \
                        ( name, changeset_revision, latest_changeset_revision ) )
                    cmd = 'hg pull'
                    tmp_name = tempfile.NamedTemporaryFile().name
                    tmp_stderr = open( tmp_name, 'wb' )
                    os.chdir( repo_files_dir )
                    proc = subprocess.Popen( cmd, shell=True, stderr=tmp_stderr.fileno() )
                    returncode = proc.wait()
                    os.chdir( current_working_dir )
                    tmp_stderr.close()
                    if returncode == 0:
                        cmd = 'hg update -r %s' % latest_changeset_revision
                        tmp_name = tempfile.NamedTemporaryFile().name
                        tmp_stderr = open( tmp_name, 'wb' )
                        os.chdir( repo_files_dir )
                        proc = subprocess.Popen( cmd, shell=True, stderr=tmp_stderr.fileno() )
                        returncode = proc.wait()
                        os.chdir( current_working_dir )
                        tmp_stderr.close()
                        if returncode == 0:
                            # Update the repository changeset_revision in the database.
                            repository.changeset_revision = latest_changeset_revision
                            trans.sa_session.add( repository )
                            trans.sa_session.flush()
                            message = "The cloned repository named '%s' has been updated to change set revision '%s'." % \
                                ( name, latest_changeset_revision )
                        else:
                            tmp_stderr = open( tmp_name, 'rb' )
                            message = tmp_stderr.read()
                            tmp_stderr.close()
                            status = 'error'
                    else:
                        tmp_stderr = open( tmp_name, 'rb' )
                        message = tmp_stderr.read()
                        tmp_stderr.close()
                        status = 'error'
                else:
                    message = "The directory containing the cloned repository named '%s' cannot be found." % name
                    status = 'error'
        else:
            message = "The latest changeset revision could not be retrieved for the repository named '%s'." % name
            status = 'error'
        return trans.response.send_redirect( web.url_for( controller='admin',
                                                          action='manage_tool_shed_repository',
                                                          id=trans.security.encode_id( repository.id ),
                                                          message=message,
                                                          status=status ) )
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

    def __get_relative_install_dir( self, trans, repository ):
        # Get the directory where the repository is install.
        tool_shed = self.__clean_tool_shed_url( repository.tool_shed )
        partial_install_dir = '%s/repos/%s/%s/%s' % ( tool_shed, repository.owner, repository.name, repository.changeset_revision )
        # Get the relative tool installation paths from each of the shed tool configs.
        shed_tool_confs = trans.app.toolbox.shed_tool_confs
        relative_install_dir = None
        # The shed_tool_confs dictionary contains { shed_conf_filename : tool_path } pairs.
        for shed_conf_filename, tool_path in shed_tool_confs.items():
            relative_install_dir = os.path.join( tool_path, partial_install_dir )
            if os.path.isdir( relative_install_dir ):
                break
        return relative_install_dir
    def __handle_missing_data_table_entry( self, trans, tool_path, sample_files, repository_tools_tups ):
        # Inspect each tool to see if any have input parameters that are dynamically
        # generated select lists that require entries in the tool_data_table_conf.xml file.
        missing_data_table_entry = False
        for index, repository_tools_tup in enumerate( repository_tools_tups ):
            tup_path, repository_tool = repository_tools_tup
            if repository_tool.params_with_missing_data_table_entry:
                missing_data_table_entry = True
                break
        if missing_data_table_entry:
            # The repository must contain a tool_data_table_conf.xml.sample file that includes
            # all required entries for all tools in the repository.
            for sample_file in sample_files:
                head, tail = os.path.split( sample_file )
                if tail == 'tool_data_table_conf.xml.sample':
                    break
            error, correction_msg = handle_sample_tool_data_table_conf_file( trans, sample_file )
            if error:
                # TODO: Do more here than logging an exception.
                log.debug( exception_msg )
            # Reload the tool into the local list of repository_tools_tups.
            repository_tool = trans.app.toolbox.load_tool( os.path.join( tool_path, tup_path ) )
            repository_tools_tups[ index ] = ( tup_path, repository_tool )
        return repository_tools_tups
    def __handle_missing_index_file( self, trans, tool_path, sample_files, repository_tools_tups ):
        # Inspect each tool to see if it has any input parameters that
        # are dynamically generated select lists that depend on a .loc file.
        missing_files_handled = []
        for index, repository_tools_tup in enumerate( repository_tools_tups ):
            tup_path, repository_tool = repository_tools_tup
            params_with_missing_index_file = repository_tool.params_with_missing_index_file
            for param in params_with_missing_index_file:
                options = param.options
                missing_head, missing_tail = os.path.split( options.missing_index_file )
                if missing_tail not in missing_files_handled:
                    # The repository must contain the required xxx.loc.sample file.
                    for sample_file in sample_files:
                        sample_head, sample_tail = os.path.split( sample_file )
                        if sample_tail == '%s.sample' % missing_tail:
                            copy_sample_loc_file( trans, sample_file )
                            if options.tool_data_table and options.tool_data_table.missing_index_file:
                                options.tool_data_table.handle_found_index_file( options.missing_index_file )
                            missing_files_handled.append( missing_tail )
                            break
            # Reload the tool into the local list of repository_tools_tups.
            repository_tool = trans.app.toolbox.load_tool( os.path.join( tool_path, tup_path ) )
            repository_tools_tups[ index ] = ( tup_path, repository_tool )
        return repository_tools_tups
    def __handle_tool_dependencies( self, current_working_dir, repo_files_dir, repository_tools_tups ):
        # Inspect each tool to see if it includes a "requirement" that refers to a fabric
        # script.  For those that do, execute the fabric script to install tool dependencies.
        for index, repository_tools_tup in enumerate( repository_tools_tups ):
            tup_path, repository_tool = repository_tools_tup
            for requirement in repository_tool.requirements:
                if requirement.type == 'fabfile':
                    log.debug( 'Executing fabric script to install dependencies for tool "%s"...' % repository_tool.name )
                    fabfile = requirement.fabfile
                    method = requirement.method
                    # Find the relative path to the fabfile.
                    relative_fabfile_path = None
                    for root, dirs, files in os.walk( repo_files_dir ):
                        for name in files:
                            if name == fabfile:
                                relative_fabfile_path = os.path.join( root, name )
                                break
                    if relative_fabfile_path:
                        # cmd will look something like: fab -f fabfile.py install_bowtie
                        cmd = 'fab -f %s %s' % ( relative_fabfile_path, method )
                        tmp_name = tempfile.NamedTemporaryFile().name
                        tmp_stderr = open( tmp_name, 'wb' )
                        os.chdir( repo_files_dir )
                        proc = subprocess.Popen( cmd, shell=True, stderr=tmp_stderr.fileno() )
                        returncode = proc.wait()
                        os.chdir( current_working_dir )
                        tmp_stderr.close()
                        if returncode != 0:
                            # TODO: do something more here than logging the problem.
                            tmp_stderr = open( tmp_name, 'rb' )
                            error = tmp_stderr.read()
                            tmp_stderr.close()
                            log.debug( 'Problem installing dependencies for tool "%s"\n%s' % ( repository_tool.name, error ) )
    def __get_repository_tools_and_sample_files( self, trans, tool_path, repo_files_dir ):
        # The sample_files list contains all files whose name ends in .sample
        sample_files = []
        # Find all special .sample files first.
        for root, dirs, files in os.walk( repo_files_dir ):
            if root.find( '.hg' ) < 0:
                for name in files:
                    if name.endswith( '.sample' ):
                        sample_files.append( os.path.abspath( os.path.join( root, name ) ) )
        # The repository_tools_tups list contains tuples of ( relative_path_to_tool_config, tool ) pairs
        repository_tools_tups = []
        for root, dirs, files in os.walk( repo_files_dir ):
            if root.find( '.hg' ) < 0 and root.find( 'hgrc' ) < 0:
                if '.hg' in dirs:
                    dirs.remove( '.hg' )
                if 'hgrc' in files:
                    files.remove( 'hgrc' )
                for name in files:
                    # Find all tool configs.
                    if name.endswith( '.xml' ):
                        relative_path = os.path.join( root, name )
                        full_path = os.path.abspath( os.path.join( root, name ) )
                        try:
                            repository_tool = trans.app.toolbox.load_tool( full_path )
                            if repository_tool:
                                # At this point, we need to lstrip tool_path from relative_path.
                                tup_path = relative_path.replace( tool_path, '' ).lstrip( '/' )
                                repository_tools_tups.append( ( tup_path, repository_tool ) )
                        except Exception, e:
                            # We have an invalid .xml file, so not a tool config.
                            log.debug( "Ignoring invalid tool config (%s). Error: %s" % ( str( relative_path ), str( e ) ) )
        return sample_files, repository_tools_tups
    def __create_or_undelete_tool_shed_repository( self, trans, name, description, changeset_revision, repository_clone_url ):
        tmp_url = self.__clean_repository_clone_url( repository_clone_url )
        tool_shed = tmp_url.split( 'repos' )[ 0 ].rstrip( '/' )
        owner = self.__get_repository_owner( tmp_url )
        flush_needed = False
        tool_shed_repository = get_repository_by_shed_name_owner_changeset_revision( trans, tool_shed, name, owner, changeset_revision )
        if tool_shed_repository:
            if tool_shed_repository.deleted:
                tool_shed_repository.deleted = False
                flush_needed = True
        else:
            tool_shed_repository = trans.model.ToolShedRepository( tool_shed=tool_shed,
                                                                   name=name,
                                                                   description=description,
                                                                   owner=owner,
                                                                   changeset_revision=changeset_revision )
            flush_needed = True
        if flush_needed:
            trans.sa_session.add( tool_shed_repository )
            trans.sa_session.flush()
    def __add_shed_tool_conf_entry( self, trans, shed_tool_conf, new_tool_section ):
        # Add an entry in the shed_tool_conf file. An entry looks something like:
        # <section name="Filter and Sort" id="filter">
        #    <tool file="filter/filtering.xml" guid="toolshed.g2.bx.psu.edu/repos/test/filter/1.0.2"/>
        # </section>
        # Make a backup of the hgweb.config file since we're going to be changing it.
        if not os.path.exists( shed_tool_conf ):
            output = open( shed_tool_conf, 'w' )
            output.write( '<?xml version="1.0"?>\n' )
            output.write( '<toolbox tool_path="%s">\n' % tool_path )
            output.write( '</toolbox>\n' )
            output.close()
        self.__make_shed_tool_conf_copy( trans, shed_tool_conf )
        tmp_fd, tmp_fname = tempfile.mkstemp()
        new_shed_tool_conf = open( tmp_fname, 'wb' )
        for i, line in enumerate( open( shed_tool_conf ) ):
            if line.startswith( '</toolbox>' ):
                # We're at the end of the original config file, so add our entry.
                new_shed_tool_conf.write( new_tool_section )
                new_shed_tool_conf.write( line )
            else:
                new_shed_tool_conf.write( line )
        new_shed_tool_conf.close()
        shutil.move( tmp_fname, os.path.abspath( shed_tool_conf ) )
    def __make_shed_tool_conf_copy( self, trans, shed_tool_conf ):
        # Make a backup of the shed_tool_conf file.
        today = date.today()
        backup_date = today.strftime( "%Y_%m_%d" )
        shed_tool_conf_copy = '%s/%s_%s_backup' % ( trans.app.config.root, shed_tool_conf, backup_date )
        shutil.copy( os.path.abspath( shed_tool_conf ), os.path.abspath( shed_tool_conf_copy ) )
    def __clean_tool_shed_url( self, tool_shed_url ):
        if tool_shed_url.find( ':' ) > 0:
            # Eliminate the port, if any, since it will result in an invalid directory name.
            return tool_shed_url.split( ':' )[ 0 ]
        return tool_shed_url.rstrip( '/' )
    def __clean_repository_clone_url( self, repository_clone_url ):
        if repository_clone_url.find( '@' ) > 0:
            # We have an url that includes an authenticated user, something like:
            # http://test@bx.psu.edu:9009/repos/some_username/column
            items = repository_clone_url.split( '@' )
            tmp_url = items[ 1 ]
        elif repository_clone_url.find( '//' ) > 0:
            # We have an url that includes only a protocol, something like:
            # http://bx.psu.edu:9009/repos/some_username/column
            items = repository_clone_url.split( '//' )
            tmp_url = items[ 1 ]
        else:
            tmp_url = repository_clone_url
        return tmp_url
    def __get_repository_owner( self, cleaned_repository_url ):
        items = cleaned_repository_url.split( 'repos' )
        repo_path = items[ 1 ]
        return repo_path.lstrip( '/' ).split( '/' )[ 0 ]
    def __generate_tool_path( self, repository_clone_url, changeset_revision ):
        """
        Generate a tool path that guarantees repositories with the same name will always be installed
        in different directories.  The tool path will be of the form:
        <tool shed url>/repos/<repository owner>/<repository name>/<changeset revision>
        http://test@bx.psu.edu:9009/repos/test/filter
        """
        tmp_url = self.__clean_repository_clone_url( repository_clone_url )
        # Now tmp_url is something like: bx.psu.edu:9009/repos/some_username/column
        items = tmp_url.split( 'repos' )
        tool_shed_url = items[ 0 ]
        repo_path = items[ 1 ]
        tool_shed_url = self.__clean_tool_shed_url( tool_shed_url )
        return '%s/repos%s/%s' % ( tool_shed_url, repo_path, changeset_revision )
    def __generate_tool_guid( self, repository_clone_url, tool ):
        """
        Generate a guid for the installed tool.  It is critical that this guid matches the guid for
        the tool in the Galaxy tool shed from which it is being installed.  The form of the guid is    
        <tool shed host>/repos/<repository owner>/<repository name>/<tool id>/<tool version>
        """
        tmp_url = self.__clean_repository_clone_url( repository_clone_url )
        return '%s/%s/%s' % ( tmp_url, tool.id, tool.version )
    def __generate_tool_panel_section( self, repository_name, repository_clone_url, changeset_revision, tool_section, repository_tools_tups ):
        """
        Write an in-memory tool panel section so we can load it into the tool panel and then
        append it to the appropriate shed tool config.
        TODO: re-write using ElementTree.
        """
        tmp_url = self.__clean_repository_clone_url( repository_clone_url )
        section_str = ''
        section_str += '    <section name="%s" id="%s">\n' % ( tool_section.name, tool_section.id )
        for repository_tool_tup in repository_tools_tups:
            tool_file_path, tool = repository_tool_tup
            guid = self.__generate_tool_guid( repository_clone_url, tool )
            section_str += '        <tool file="%s" guid="%s">\n' % ( tool_file_path, guid )
            section_str += '            <tool_shed>%s</tool_shed>\n' % tmp_url.split( 'repos' )[ 0 ].rstrip( '/' )
            section_str += '            <repository_name>%s</repository_name>\n' % repository_name
            section_str += '            <repository_owner>%s</repository_owner>\n' % self.__get_repository_owner( tmp_url )
            section_str += '            <changeset_revision>%s</changeset_revision>\n' % changeset_revision
            section_str += '            <id>%s</id>\n' % tool.id
            section_str += '            <version>%s</version>\n' % tool.version
            section_str += '        </tool>\n'
        section_str += '    </section>\n'
        return section_str

## ---- Utility methods -------------------------------------------------------

def build_shed_tool_conf_select_field( trans ):
    """Build a SelectField whose options are the keys in trans.app.toolbox.shed_tool_confs."""
    options = []
    for shed_tool_conf_filename, tool_path in trans.app.toolbox.shed_tool_confs.items():
        options.append( ( shed_tool_conf_filename.lstrip( './' ), shed_tool_conf_filename ) )
    select_field = SelectField( name='shed_tool_conf' )
    for option_tup in options:
        select_field.add_option( option_tup[0], option_tup[1] )
    return select_field
def build_tool_panel_section_select_field( trans ):
    """Build a SelectField whose options are the sections of the current in-memory toolbox."""
    options = []
    for k, tool_section in trans.app.toolbox.tool_panel.items():
        options.append( ( tool_section.name, tool_section.id ) )
    select_field = SelectField( name='tool_panel_section', display='radio' )
    for option_tup in options:
        select_field.add_option( option_tup[0], option_tup[1] )
    return select_field
def get_repository( trans, id ):
    """Get a tool_shed_repository from the database via id"""
    return trans.sa_session.query( trans.model.ToolShedRepository ).get( trans.security.decode_id( id ) )
def get_repository_by_name_owner_changeset_revision( trans, name, owner, changeset_revision ):
    """Get a repository from the database via name owner and changeset_revision"""
    return trans.sa_session.query( trans.model.ToolShedRepository ) \
                             .filter( and_( trans.model.ToolShedRepository.table.c.name == name,
                                            trans.model.ToolShedRepository.table.c.owner == owner,
                                            trans.model.ToolShedRepository.table.c.changeset_revision == changeset_revision ) ) \
                             .first()
def get_repository_by_shed_name_owner_changeset_revision( trans, tool_shed, name, owner, changeset_revision ):
    return trans.sa_session.query( trans.model.ToolShedRepository ) \
                           .filter( and_( trans.model.ToolShedRepository.table.c.tool_shed == tool_shed,
                                          trans.model.ToolShedRepository.table.c.name == name,
                                          trans.model.ToolShedRepository.table.c.owner == owner,
                                          trans.model.ToolShedRepository.table.c.changeset_revision == changeset_revision ) ) \
                           .first()

