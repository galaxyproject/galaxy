import imp
import logging
import os
from datetime import datetime, timedelta
import six
from string import punctuation as PUNCTUATION
from sqlalchemy.sql import expression
from sqlalchemy import and_, false, func, or_

import galaxy.queue_worker
from galaxy import util
from galaxy import model
from galaxy import web
from galaxy.actions.admin import AdminActions
from galaxy.exceptions import MessageException
from galaxy.model import tool_shed_install as install_model
from galaxy.util import nice_size, sanitize_text, url_get
from galaxy.util.odict import odict
from galaxy.web import url_for
from galaxy.web.base import controller
from galaxy.web.base.controller import UsesQuotaMixin
from galaxy.web.form_builder import CheckboxField
from galaxy.web.framework.helpers import grids, time_ago
from galaxy.web.params import QuotaParamParser
from galaxy.tools import global_tool_errors
from tool_shed.util import common_util
from tool_shed.util import encoding_util
from tool_shed.util import repository_util
from tool_shed.util.web_util import escape


log = logging.getLogger( __name__ )


class UserListGrid( grids.Grid ):

    class EmailColumn( grids.TextColumn ):
        def get_value( self, trans, grid, user ):
            return escape(user.email)

    class UserNameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, user ):
            if user.username:
                return escape(user.username)
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

    class TimeCreatedColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            return user.create_time.strftime('%x')

    class ActivatedColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            if user.active:
                return 'Y'
            else:
                return 'N'

    # Grid definition
    title = "Users"
    model_class = model.User
    default_sort_key = "email"
    columns = [
        EmailColumn( "Email",
                     key="email",
                     model_class=model.User,
                     link=( lambda item: dict( controller="user", action="information", id=item.id, webapp="galaxy" ) ),
                     attach_popup=True,
                     filterable="advanced",
                     target="top" ),
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
        TimeCreatedColumn( "Created", attach_popup=False ),
        ActivatedColumn( "Activated", attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search",
                                                cols_to_filter=[ columns[0], columns[1] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = [
        grids.GridAction( "Create new user", url_args=dict( webapp="galaxy", action="create_new_user" ) )
    ]
    operations = [
        grids.GridOperation( "Manage Roles and Groups",
                             condition=( lambda item: not item.deleted ),
                             allow_multiple=False,
                             url_args=dict( webapp="galaxy", action="manage_roles_and_groups_for_user" ) ),
        grids.GridOperation( "Reset Password",
                             condition=( lambda item: not item.deleted ),
                             allow_multiple=True,
                             url_args=dict( webapp="galaxy", action="reset_user_password" ),
                             target="top" ),
        grids.GridOperation( "Recalculate Disk Usage",
                             condition=( lambda item: not item.deleted ),
                             allow_multiple=False )
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
            return escape(role.name)

    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, role ):
            if role.description:
                return escape(role.description)
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
    title = "Roles"
    model_class = model.Role
    template = '/admin/dataset_security/role/grid.mako'
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
            return escape(group.name)

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
    title = "Groups"
    model_class = model.Group
    template = '/admin/dataset_security/group/grid.mako'
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
            return escape(quota.name)

    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, quota ):
            if quota.description:
                return escape(quota.description)
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
    title = "Quotas"
    model_class = model.Quota
    template = '/admin/quota/grid.mako'
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
            toolbox = trans.app.toolbox
            if toolbox.has_tool( tool_version.tool_id, exact=True ):
                link = url_for( controller='tool_runner', tool_id=tool_version.tool_id )
                link_str = '<a target="_blank" href="%s">' % link
                return '<div class="count-box state-color-ok">%s%s</a></div>' % ( link_str, tool_version.tool_id )
            return tool_version.tool_id

    class ToolVersionsColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_version ):
            tool_ids_str = ''
            toolbox = trans.app.toolbox
            tool = toolbox._tools_by_id.get(tool_version.tool_id)
            if tool:
                for tool_id in tool.lineage.tool_ids:
                    if toolbox.has_tool( tool_id, exact=True ):
                        link = url_for( controller='tool_runner', tool_id=tool_id )
                        link_str = '<a target="_blank" href="%s">' % link
                        tool_ids_str += '<div class="count-box state-color-ok">%s%s</a></div><br/>' % ( link_str, tool_id )
                    else:
                        tool_ids_str += '%s<br/>' % tool_version.tool_id
            else:
                tool_ids_str += '%s<br/>' % tool_version.tool_id
            return tool_ids_str

    # Grid definition
    title = "Tool versions"
    model_class = install_model.ToolVersion
    template = '/admin/tool_version/grid.mako'
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
        return trans.install_model.context.query( self.model_class )


class AdminGalaxy( controller.JSAppLauncher, AdminActions, UsesQuotaMixin, QuotaParamParser ):

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
    def index( self, trans, **kwd ):
        message = escape( kwd.get( 'message', ''  ) )
        status = kwd.get( 'status', 'done' )
        settings = {
            'is_repo_installed'          : trans.install_model.context.query( trans.install_model.ToolShedRepository ).first() is not None,
            'installing_repository_ids'  : repository_util.get_ids_of_tool_shed_repositories_being_installed( trans.app, as_string=True ),
            'is_tool_shed_installed'     : bool( trans.app.tool_shed_registry and trans.app.tool_shed_registry.tool_sheds )
        }
        return self.template( trans, 'admin', settings=settings, message=message, status=status )

    @web.expose
    @web.json
    @web.require_admin
    def users_list( self, trans, **kwd ):
        message = kwd.get( 'message' )
        status  = kwd.get( 'status' )
        if 'operation' in kwd:
            id = kwd.get( 'id', None )
            if not id:
                message, status = ( 'Invalid user id (%s) received.' % str( id ), 'error' )
            ids = util.listify( id )
            operation = kwd['operation'].lower()
            if operation == 'delete':
                message, status = self.mark_user_deleted( trans, ids )
            elif operation == 'undelete':
                message, status = self.undelete_user( trans, ids )
            elif operation == 'purge':
                message, status = self.purge_user( trans, ids )
            elif operation == 'recalculate disk usage':
                message, status = self.recalculate_user_disk_usage( trans, id )
        if trans.app.config.allow_user_deletion:
            if self.delete_operation not in self.user_list_grid.operations:
                self.user_list_grid.operations.append( self.delete_operation )
            if self.undelete_operation not in self.user_list_grid.operations:
                self.user_list_grid.operations.append( self.undelete_operation )
            if self.purge_operation not in self.user_list_grid.operations:
                self.user_list_grid.operations.append( self.purge_operation )
        if message and status:
            kwd[ 'message' ] = util.sanitize_text( message )
            kwd[ 'status' ] = status
        kwd[ 'dict_format' ] = True
        return self.user_list_grid( trans, **kwd )

    @web.expose
    @web.require_admin
    def tool_versions( self, trans, **kwd ):
        if 'message' not in kwd or not kwd[ 'message' ]:
            kwd[ 'message' ] = 'Tool ids for tools that are currently loaded into the tool panel are highlighted in green (click to display).'
        return self.tool_version_list_grid( trans, **kwd )

    @web.expose
    @web.require_admin
    def roles( self, trans, **kwargs ):
        if 'operation' in kwargs:
            operation = kwargs[ 'operation' ].lower().replace( '+', ' ' )
            if operation == "roles":
                return self.role( trans, **kwargs )
            if operation == "create":
                return self.create_role( trans, **kwargs )
            if operation == "delete":
                return self.mark_role_deleted( trans, **kwargs )
            if operation == "undelete":
                return self.undelete_role( trans, **kwargs )
            if operation == "purge":
                return self.purge_role( trans, **kwargs )
            if operation == "manage users and groups":
                return self.manage_users_and_groups_for_role( trans, **kwargs )
            if operation == "manage role associations":
                # This is currently used only in the Tool Shed.
                return self.manage_role_associations( trans, **kwargs )
            if operation == "rename":
                return self.rename_role( trans, **kwargs )
        # Render the list view
        return self.role_list_grid( trans, **kwargs )

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
                                                                  message=sanitize_text( message ),
                                                                  status='done' ) )
            except MessageException as e:
                params.message = str( e )
                params.status = 'error'
        in_users = map( int, params.in_users )
        in_groups = map( int, params.in_groups )
        new_in_users = []
        new_in_groups = []
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted == expression.false() ) \
                                    .order_by( trans.app.model.User.table.c.email ):
            if user.id in in_users:
                new_in_users.append( ( user.id, user.email ) )
            else:
                params.out_users.append( ( user.id, user.email ) )
        for group in trans.sa_session.query( trans.app.model.Group ) \
                                     .filter( trans.app.model.Group.table.c.deleted == expression.false() ) \
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
                                    .filter( trans.app.model.User.table.c.deleted == expression.false() ) \
                                    .order_by( trans.app.model.User.table.c.email ):
            if user in [ x.user for x in quota.users ]:
                in_users.append( ( user.id, user.email ) )
            else:
                out_users.append( ( user.id, user.email ) )
        for group in trans.sa_session.query( trans.app.model.Group ) \
                                     .filter( trans.app.model.Group.table.c.deleted == expression.false()) \
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
                                                          message=sanitize_text( params.message ),
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
                                                          message=sanitize_text( params.message ),
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
                                                          message=sanitize_text( params.message ),
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
                                                          message=sanitize_text( params.message ),
                                                          status='error' ) )

    def _quota_op( self, trans, do_op, op_method, kwd, listify=False ):
        params = self.get_quota_params( kwd )
        if listify:
            quota = []
            messages = []
            for id in util.listify( params.id ):
                try:
                    quota.append( self.get_quota( trans, id ) )
                except MessageException as e:
                    messages.append( str( e ) )
            if messages:
                return None, trans.response.send_redirect( web.url_for( controller='admin',
                                                                        action='quotas',
                                                                        webapp=params.webapp,
                                                                        message=sanitize_text( ', '.join( messages ) ),
                                                                        status='error' ) )
        else:
            try:
                quota = self.get_quota( trans, params.id, deleted=False )
            except MessageException as e:
                return None, trans.response.send_redirect( web.url_for( controller='admin',
                                                                        action='quotas',
                                                                        webapp=params.webapp,
                                                                        message=sanitize_text( str( e ) ),
                                                                        status='error' ) )
        if do_op is True or ( do_op is not False and params.get( do_op, False ) ):
            try:
                message = op_method( quota, params )
                return None, trans.response.send_redirect( web.url_for( controller='admin',
                                                                        action='quotas',
                                                                        webapp=params.webapp,
                                                                        message=sanitize_text( message ),
                                                                        status='done' ) )
            except MessageException as e:
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
                trans.handle_user_logout()
                trans.handle_user_login(user)
                message = 'You are now logged in as %s, <a target="_top" href="%s">return to the home page</a>' % ( email, url_for( controller='root' ) )
                emails = []
            else:
                message = 'Invalid user selected'
                status = 'error'
        if emails is None:
            emails = [ u.email for u in trans.sa_session.query( trans.app.model.User ).enable_eagerloads( False ).all() ]
        return trans.fill_template( 'admin/impersonate.mako', emails=emails, message=message, status=status )

    def check_for_tool_dependencies( self, trans, migration_stage ):
        # Get the 000x_tools.xml file associated with migration_stage.
        tools_xml_file_path = os.path.abspath( os.path.join( trans.app.config.root, 'scripts', 'migrate_tools', '%04d_tools.xml' % migration_stage ) )
        tree = util.parse_xml( tools_xml_file_path )
        root = tree.getroot()
        tool_shed = root.get( 'name' )
        shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( trans.app, tool_shed )
        repo_name_dependency_tups = []
        if shed_url:
            for elem in root:
                if elem.tag == 'repository':
                    tool_dependencies = []
                    tool_dependencies_dict = {}
                    repository_name = elem.get( 'name' )
                    changeset_revision = elem.get( 'changeset_revision' )
                    params = dict( name=repository_name, owner='devteam', changeset_revision=changeset_revision )
                    pathspec = [ 'repository', 'get_tool_dependencies' ]
                    text = url_get( shed_url, password_mgr=self.app.tool_shed_registry.url_auth( shed_url ), pathspec=pathspec, params=params )
                    if text:
                        tool_dependencies_dict = encoding_util.tool_shed_decode( text )
                        for dependency_key, requirements_dict in tool_dependencies_dict.items():
                            tool_dependency_name = requirements_dict[ 'name' ]
                            tool_dependency_version = requirements_dict[ 'version' ]
                            tool_dependency_type = requirements_dict[ 'type' ]
                            tool_dependency_readme = requirements_dict.get( 'readme', '' )
                            tool_dependencies.append( ( tool_dependency_name, tool_dependency_version, tool_dependency_type, tool_dependency_readme ) )
                    repo_name_dependency_tups.append( ( repository_name, tool_dependencies ) )
        return repo_name_dependency_tups

    @web.expose
    @web.require_admin
    def review_tool_migration_stages( self, trans, **kwd ):
        message = escape( util.restore_text( kwd.get( 'message', '' ) ) )
        status = util.restore_text( kwd.get( 'status', 'done' ) )
        migration_stages_dict = odict()
        migration_modules = []
        migration_scripts_dir = os.path.abspath( os.path.join( trans.app.config.root, 'lib', 'tool_shed', 'galaxy_install', 'migrate', 'versions' ) )
        migration_scripts_dir_contents = os.listdir( migration_scripts_dir )
        for item in migration_scripts_dir_contents:
            if os.path.isfile( os.path.join( migration_scripts_dir, item ) ) and item.endswith( '.py' ):
                module = item.replace( '.py', '' )
                migration_modules.append( module )
        if migration_modules:
            migration_modules.sort()
            # Remove the 0001_tools.py script since it is the seed.
            migration_modules = migration_modules[ 1: ]
            # Reverse the list so viewing will be newest to oldest.
            migration_modules.reverse()
        for migration_module in migration_modules:
            migration_stage = int( migration_module.replace( '_tools', '' ) )
            repo_name_dependency_tups = self.check_for_tool_dependencies( trans, migration_stage )
            open_file_obj, file_name, description = imp.find_module( migration_module, [ migration_scripts_dir ] )
            imported_module = imp.load_module( 'upgrade', open_file_obj, file_name, description )
            migration_info = imported_module.__doc__
            open_file_obj.close()
            migration_stages_dict[ migration_stage ] = ( migration_info, repo_name_dependency_tups )
        return trans.fill_template( 'admin/review_tool_migration_stages.mako',
                                    migration_stages_dict=migration_stages_dict,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def tool_errors( self, trans, **kwd ):
        return trans.fill_template('admin/tool_errors.mako', tool_errors=global_tool_errors.error_stack)

    @web.expose
    @web.require_admin
    def view_datatypes_registry( self, trans, **kwd ):
        message = escape( util.restore_text( kwd.get( 'message', '' ) ) )
        status = util.restore_text( kwd.get( 'status', 'done' ) )
        return trans.fill_template( 'admin/view_datatypes_registry.mako', message=message, status=status )

    @web.expose
    @web.require_admin
    def view_tool_data_tables( self, trans, **kwd ):
        message = escape( util.restore_text( kwd.get( 'message', '' ) ) )
        status = util.restore_text( kwd.get( 'status', 'done' ) )
        return trans.fill_template( 'admin/view_data_tables_registry.mako', message=message, status=status )

    @web.expose
    @web.require_admin
    def display_applications( self, trans, **kwd ):
        return trans.fill_template( 'admin/view_display_applications.mako', display_applications=trans.app.datatypes_registry.display_applications )

    @web.expose
    @web.require_admin
    def reload_display_application( self, trans, **kwd ):
        galaxy.queue_worker.send_control_task(trans.app,
                                              'reload_display_application',
                                              noop_self=True,
                                              kwargs={'display_application_ids': kwd.get( 'id' )} )
        reloaded, failed = trans.app.datatypes_registry.reload_display_applications( kwd.get( 'id' ) )
        if not reloaded and failed:
            return trans.show_error_message( 'Unable to reload any of the %i requested display applications ("%s").'
                                             % ( len( failed ), '", "'.join( failed ) ) )
        if failed:
            return trans.show_warn_message( 'Reloaded %i display applications ("%s"), but failed to reload %i display applications ("%s").'
                                            % ( len( reloaded ), '", "'.join( reloaded ), len( failed ), '", "'.join( failed ) ) )
        if not reloaded:
            return trans.show_warn_message( 'You need to request at least one display application to reload.' )
        return trans.show_ok_message( 'Reloaded %i requested display applications ("%s").' % ( len( reloaded ), '", "'.join( reloaded ) ) )

    @web.expose
    @web.require_admin
    def center( self, trans, **kwd ):
        message = escape( kwd.get( 'message', ''  ) )
        status = kwd.get( 'status', 'done' )
        is_repo_installed = trans.install_model.context.query( trans.install_model.ToolShedRepository ).first() is not None
        installing_repository_ids = repository_util.get_ids_of_tool_shed_repositories_being_installed( trans.app, as_string=True )
        return trans.fill_template( '/webapps/galaxy/admin/center.mako',
                                    is_repo_installed=is_repo_installed,
                                    installing_repository_ids=installing_repository_ids,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def package_tool( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        toolbox = self.app.toolbox
        tool_id = None
        if params.get( 'package_tool_button', False ):
            tool_id = params.get('tool_id', None)
            try:
                tool_tarball = trans.app.toolbox.package_tool( trans, tool_id )
                trans.response.set_content_type( 'application/x-gzip' )
                download_file = open( tool_tarball )
                os.unlink( tool_tarball )
                tarball_path, filename = os.path.split( tool_tarball )
                trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.tgz"' % ( tool_id )
                return download_file
            except Exception:
                return trans.fill_template( '/admin/package_tool.mako',
                                            tool_id=tool_id,
                                            toolbox=toolbox,
                                            message=message,
                                            status='error' )

    @web.expose
    @web.require_admin
    def reload_tool( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        toolbox = self.app.toolbox
        tool_id = None
        if params.get( 'reload_tool_button', False ):
            tool_id = kwd.get( 'tool_id', None )
            galaxy.queue_worker.send_control_task(trans.app, 'reload_tool', noop_self=True, kwargs={'tool_id': tool_id} )
            message, status = trans.app.toolbox.reload_tool_by_id( tool_id )
        return trans.fill_template( '/admin/reload_tool.mako',
                                    tool_id=tool_id,
                                    toolbox=toolbox,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def tool_versions( self, trans, **kwd ):
        if 'message' not in kwd or not kwd[ 'message' ]:
            kwd[ 'message' ] = 'Tool ids for tools that are currently loaded into the tool panel are highlighted in green (click to display).'
        return self.tool_version_list_grid( trans, **kwd )

    @web.expose
    @web.require_admin
    def roles( self, trans, **kwargs ):
        if 'operation' in kwargs:
            operation = kwargs[ 'operation' ].lower().replace( '+', ' ' )
            if operation == "roles":
                return self.role( trans, **kwargs )
            if operation == "create":
                return self.create_role( trans, **kwargs )
            if operation == "delete":
                return self.mark_role_deleted( trans, **kwargs )
            if operation == "undelete":
                return self.undelete_role( trans, **kwargs )
            if operation == "purge":
                return self.purge_role( trans, **kwargs )
            if operation == "manage users and groups":
                return self.manage_users_and_groups_for_role( trans, **kwargs )
            if operation == "manage role associations":
                # This is currently used only in the Tool Shed.
                return self.manage_role_associations( trans, **kwargs )
            if operation == "rename":
                return self.rename_role( trans, **kwargs )
        # Render the list view
        return self.role_list_grid( trans, **kwargs )

    @web.expose
    @web.require_admin
    def create_role( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        name = util.restore_text( params.get( 'name', '' ) )
        description = util.restore_text( params.get( 'description', '' ) )
        in_users = util.listify( params.get( 'in_users', [] ) )
        out_users = util.listify( params.get( 'out_users', [] ) )
        in_groups = util.listify( params.get( 'in_groups', [] ) )
        out_groups = util.listify( params.get( 'out_groups', [] ) )
        create_group_for_role = params.get( 'create_group_for_role', '' )
        create_group_for_role_checked = CheckboxField.is_checked( create_group_for_role )
        ok = True
        if params.get( 'create_role_button', False ):
            if not name or not description:
                message = "Enter a valid name and a description."
                status = 'error'
                ok = False
            elif trans.sa_session.query( trans.app.model.Role ).filter( trans.app.model.Role.table.c.name == name ).first():
                message = "Role names must be unique and a role with that name already exists, so choose another name."
                status = 'error'
                ok = False
            else:
                # Create the role
                role = trans.app.model.Role( name=name, description=description, type=trans.app.model.Role.types.ADMIN )
                trans.sa_session.add( role )
                # Create the UserRoleAssociations
                for user in [ trans.sa_session.query( trans.app.model.User ).get( x ) for x in in_users ]:
                    ura = trans.app.model.UserRoleAssociation( user, role )
                    trans.sa_session.add( ura )
                # Create the GroupRoleAssociations
                for group in [ trans.sa_session.query( trans.app.model.Group ).get( x ) for x in in_groups ]:
                    gra = trans.app.model.GroupRoleAssociation( group, role )
                    trans.sa_session.add( gra )
                if create_group_for_role_checked:
                    # Create the group
                    group = trans.app.model.Group( name=name )
                    trans.sa_session.add( group )
                    # Associate the group with the role
                    gra = trans.model.GroupRoleAssociation( group, role )
                    trans.sa_session.add( gra )
                    num_in_groups = len( in_groups ) + 1
                else:
                    num_in_groups = len( in_groups )
                trans.sa_session.flush()
                message = "Role '%s' has been created with %d associated users and %d associated groups.  " \
                    % ( role.name, len( in_users ), num_in_groups )
                if create_group_for_role_checked:
                    message += 'One of the groups associated with this role is the newly created group with the same name.'
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='roles',
                                                           message=util.sanitize_text( message ),
                                                           status='done' ) )
        if ok:
            for user in trans.sa_session.query( trans.app.model.User ) \
                                        .filter( trans.app.model.User.table.c.deleted == false() ) \
                                        .order_by( trans.app.model.User.table.c.email ):
                out_users.append( ( user.id, user.email ) )
            for group in trans.sa_session.query( trans.app.model.Group ) \
                                         .filter( trans.app.model.Group.table.c.deleted == false() ) \
                                         .order_by( trans.app.model.Group.table.c.name ):
                out_groups.append( ( group.id, group.name ) )
        return trans.fill_template( '/admin/dataset_security/role/role_create.mako',
                                    name=name,
                                    description=description,
                                    in_users=in_users,
                                    out_users=out_users,
                                    in_groups=in_groups,
                                    out_groups=out_groups,
                                    create_group_for_role_checked=create_group_for_role_checked,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def rename_role( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message = "No role ids received for renaming"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       message=message,
                                                       status='error' ) )
        role = get_role( trans, id )
        if params.get( 'rename_role_button', False ):
            old_name = role.name
            new_name = util.restore_text( params.name )
            new_description = util.restore_text( params.description )
            if not new_name:
                message = 'Enter a valid name'
                status = 'error'
            else:
                existing_role = trans.sa_session.query( trans.app.model.Role ).filter( trans.app.model.Role.table.c.name == new_name ).first()
                if existing_role and existing_role.id != role.id:
                    message = 'A role with that name already exists'
                    status = 'error'
                else:
                    if not ( role.name == new_name and role.description == new_description ):
                        role.name = new_name
                        role.description = new_description
                        trans.sa_session.add( role )
                        trans.sa_session.flush()
                        message = "Role '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( controller='admin',
                                                                      action='roles',
                                                                      message=util.sanitize_text( message ),
                                                                      status='done' ) )
        return trans.fill_template( '/admin/dataset_security/role/role_rename.mako',
                                    role=role,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def manage_users_and_groups_for_role( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message = "No role ids received for managing users and groups"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       message=message,
                                                       status='error' ) )
        role = get_role( trans, id )
        if params.get( 'role_members_edit_button', False ):
            in_users = [ trans.sa_session.query( trans.app.model.User ).get( x ) for x in util.listify( params.in_users ) ]
            if trans.webapp.name == 'galaxy':
                for ura in role.users:
                    user = trans.sa_session.query( trans.app.model.User ).get( ura.user_id )
                    if user not in in_users:
                        # Delete DefaultUserPermissions for previously associated users that have been removed from the role
                        for dup in user.default_permissions:
                            if role == dup.role:
                                trans.sa_session.delete( dup )
                        # Delete DefaultHistoryPermissions for previously associated users that have been removed from the role
                        for history in user.histories:
                            for dhp in history.default_permissions:
                                if role == dhp.role:
                                    trans.sa_session.delete( dhp )
                        trans.sa_session.flush()
            in_groups = [ trans.sa_session.query( trans.app.model.Group ).get( x ) for x in util.listify( params.in_groups ) ]
            trans.app.security_agent.set_entity_role_associations( roles=[ role ], users=in_users, groups=in_groups )
            trans.sa_session.refresh( role )
            message = "Role '%s' has been updated with %d associated users and %d associated groups" % ( role.name, len( in_users ), len( in_groups ) )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       message=util.sanitize_text( message ),
                                                       status=status ) )
        in_users = []
        out_users = []
        in_groups = []
        out_groups = []
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted == false() ) \
                                    .order_by( trans.app.model.User.table.c.email ):
            if user in [ x.user for x in role.users ]:
                in_users.append( ( user.id, user.email ) )
            else:
                out_users.append( ( user.id, user.email ) )
        for group in trans.sa_session.query( trans.app.model.Group ) \
                                     .filter( trans.app.model.Group.table.c.deleted == false() ) \
                                     .order_by( trans.app.model.Group.table.c.name ):
            if group in [ x.group for x in role.groups ]:
                in_groups.append( ( group.id, group.name ) )
            else:
                out_groups.append( ( group.id, group.name ) )
        library_dataset_actions = {}
        if trans.webapp.name == 'galaxy' and len(role.dataset_actions) < 25:
            # Build a list of tuples that are LibraryDatasetDatasetAssociationss followed by a list of actions
            # whose DatasetPermissions is associated with the Role
            # [ ( LibraryDatasetDatasetAssociation [ action, action ] ) ]
            for dp in role.dataset_actions:
                for ldda in trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ) \
                                            .filter( trans.app.model.LibraryDatasetDatasetAssociation.dataset_id == dp.dataset_id ):
                    root_found = False
                    folder_path = ''
                    folder = ldda.library_dataset.folder
                    while not root_found:
                        folder_path = '%s / %s' % ( folder.name, folder_path )
                        if not folder.parent:
                            root_found = True
                        else:
                            folder = folder.parent
                    folder_path = '%s %s' % ( folder_path, ldda.name )
                    library = trans.sa_session.query( trans.app.model.Library ) \
                                              .filter( trans.app.model.Library.table.c.root_folder_id == folder.id ) \
                                              .first()
                    if library not in library_dataset_actions:
                        library_dataset_actions[ library ] = {}
                    try:
                        library_dataset_actions[ library ][ folder_path ].append( dp.action )
                    except:
                        library_dataset_actions[ library ][ folder_path ] = [ dp.action ]
        else:
            message = "Not showing associated datasets, there are too many."
            status = 'info'
        return trans.fill_template( '/admin/dataset_security/role/role.mako',
                                    role=role,
                                    in_users=in_users,
                                    out_users=out_users,
                                    in_groups=in_groups,
                                    out_groups=out_groups,
                                    library_dataset_actions=library_dataset_actions,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def mark_role_deleted( self, trans, **kwd ):
        id = kwd.get( 'id', None )
        if not id:
            message = "No role ids received for deleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Deleted %d roles: " % len( ids )
        for role_id in ids:
            role = get_role( trans, role_id )
            role.deleted = True
            trans.sa_session.add( role )
            trans.sa_session.flush()
            message += " %s " % role.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='roles',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def undelete_role( self, trans, **kwd ):
        id = kwd.get( 'id', None )
        if not id:
            message = "No role ids received for undeleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        count = 0
        undeleted_roles = ""
        for role_id in ids:
            role = get_role( trans, role_id )
            if not role.deleted:
                message = "Role '%s' has not been deleted, so it cannot be undeleted." % role.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='roles',
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            role.deleted = False
            trans.sa_session.add( role )
            trans.sa_session.flush()
            count += 1
            undeleted_roles += " %s" % role.name
        message = "Undeleted %d roles: %s" % ( count, undeleted_roles )
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='roles',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def purge_role( self, trans, **kwd ):
        # This method should only be called for a Role that has previously been deleted.
        # Purging a deleted Role deletes all of the following from the database:
        # - UserRoleAssociations where role_id == Role.id
        # - DefaultUserPermissions where role_id == Role.id
        # - DefaultHistoryPermissions where role_id == Role.id
        # - GroupRoleAssociations where role_id == Role.id
        # - DatasetPermissionss where role_id == Role.id
        id = kwd.get( 'id', None )
        if not id:
            message = "No role ids received for purging"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Purged %d roles: " % len( ids )
        for role_id in ids:
            role = get_role( trans, role_id )
            if not role.deleted:
                message = "Role '%s' has not been deleted, so it cannot be purged." % role.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='roles',
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            # Delete UserRoleAssociations
            for ura in role.users:
                user = trans.sa_session.query( trans.app.model.User ).get( ura.user_id )
                # Delete DefaultUserPermissions for associated users
                for dup in user.default_permissions:
                    if role == dup.role:
                        trans.sa_session.delete( dup )
                # Delete DefaultHistoryPermissions for associated users
                for history in user.histories:
                    for dhp in history.default_permissions:
                        if role == dhp.role:
                            trans.sa_session.delete( dhp )
                trans.sa_session.delete( ura )
            # Delete GroupRoleAssociations
            for gra in role.groups:
                trans.sa_session.delete( gra )
            # Delete DatasetPermissionss
            for dp in role.dataset_actions:
                trans.sa_session.delete( dp )
            trans.sa_session.flush()
            message += " %s " % role.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='roles',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def groups( self, trans, **kwargs ):
        if 'operation' in kwargs:
            operation = kwargs[ 'operation' ].lower().replace( '+', ' ' )
            if operation == "groups":
                return self.group( trans, **kwargs )
            if operation == "create":
                return self.create_group( trans, **kwargs )
            if operation == "delete":
                return self.mark_group_deleted( trans, **kwargs )
            if operation == "undelete":
                return self.undelete_group( trans, **kwargs )
            if operation == "purge":
                return self.purge_group( trans, **kwargs )
            if operation == "manage users and roles":
                return self.manage_users_and_roles_for_group( trans, **kwargs )
            if operation == "rename":
                return self.rename_group( trans, **kwargs )
        # Render the list view
        return self.group_list_grid( trans, **kwargs )

    @web.expose
    @web.require_admin
    def rename_group( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message = "No group ids received for renaming"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       message=message,
                                                       status='error' ) )
        group = get_group( trans, id )
        if params.get( 'rename_group_button', False ):
            old_name = group.name
            new_name = util.restore_text( params.name )
            if not new_name:
                message = 'Enter a valid name'
                status = 'error'
            else:
                existing_group = trans.sa_session.query( trans.app.model.Group ).filter( trans.app.model.Group.table.c.name == new_name ).first()
                if existing_group and existing_group.id != group.id:
                    message = 'A group with that name already exists'
                    status = 'error'
                else:
                    if group.name != new_name:
                        group.name = new_name
                        trans.sa_session.add( group )
                        trans.sa_session.flush()
                        message = "Group '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( controller='admin',
                                                                      action='groups',
                                                                      message=util.sanitize_text( message ),
                                                                      status='done' ) )
        return trans.fill_template( '/admin/dataset_security/group/group_rename.mako',
                                    group=group,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def manage_users_and_roles_for_group( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        group = get_group( trans, params.id )
        if params.get( 'group_roles_users_edit_button', False ):
            in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( params.in_roles ) ]
            in_users = [ trans.sa_session.query( trans.app.model.User ).get( x ) for x in util.listify( params.in_users ) ]
            trans.app.security_agent.set_entity_group_associations( groups=[ group ], roles=in_roles, users=in_users )
            trans.sa_session.refresh( group )
            message += "Group '%s' has been updated with %d associated roles and %d associated users" % ( group.name, len( in_roles ), len( in_users ) )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       message=util.sanitize_text( message ),
                                                       status=status ) )
        in_roles = []
        out_roles = []
        in_users = []
        out_users = []
        for role in trans.sa_session.query(trans.app.model.Role ) \
                                    .filter( trans.app.model.Role.table.c.deleted == false() ) \
                                    .order_by( trans.app.model.Role.table.c.name ):
            if role in [ x.role for x in group.roles ]:
                in_roles.append( ( role.id, role.name ) )
            else:
                out_roles.append( ( role.id, role.name ) )
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted == false() ) \
                                    .order_by( trans.app.model.User.table.c.email ):
            if user in [ x.user for x in group.users ]:
                in_users.append( ( user.id, user.email ) )
            else:
                out_users.append( ( user.id, user.email ) )
        message += 'Group %s is currently associated with %d roles and %d users' % ( group.name, len( in_roles ), len( in_users ) )
        return trans.fill_template( '/admin/dataset_security/group/group.mako',
                                    group=group,
                                    in_roles=in_roles,
                                    out_roles=out_roles,
                                    in_users=in_users,
                                    out_users=out_users,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def create_group( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        name = util.restore_text( params.get( 'name', '' ) )
        in_users = util.listify( params.get( 'in_users', [] ) )
        out_users = util.listify( params.get( 'out_users', [] ) )
        in_roles = util.listify( params.get( 'in_roles', [] ) )
        out_roles = util.listify( params.get( 'out_roles', [] ) )
        create_role_for_group = params.get( 'create_role_for_group', '' )
        create_role_for_group_checked = CheckboxField.is_checked( create_role_for_group )
        ok = True
        if params.get( 'create_group_button', False ):
            if not name:
                message = "Enter a valid name."
                status = 'error'
                ok = False
            elif trans.sa_session.query( trans.app.model.Group ).filter( trans.app.model.Group.table.c.name == name ).first():
                message = "Group names must be unique and a group with that name already exists, so choose another name."
                status = 'error'
                ok = False
            else:
                # Create the group
                group = trans.app.model.Group( name=name )
                trans.sa_session.add( group )
                trans.sa_session.flush()
                # Create the UserRoleAssociations
                for user in [ trans.sa_session.query( trans.app.model.User ).get( x ) for x in in_users ]:
                    uga = trans.app.model.UserGroupAssociation( user, group )
                    trans.sa_session.add( uga )
                # Create the GroupRoleAssociations
                for role in [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in in_roles ]:
                    gra = trans.app.model.GroupRoleAssociation( group, role )
                    trans.sa_session.add( gra )
                if create_role_for_group_checked:
                    # Create the role
                    role = trans.app.model.Role( name=name, description='Role for group %s' % name )
                    trans.sa_session.add( role )
                    # Associate the role with the group
                    gra = trans.model.GroupRoleAssociation( group, role )
                    trans.sa_session.add( gra )
                    num_in_roles = len( in_roles ) + 1
                else:
                    num_in_roles = len( in_roles )
                trans.sa_session.flush()
                message = "Group '%s' has been created with %d associated users and %d associated roles.  " \
                    % ( group.name, len( in_users ), num_in_roles )
                if create_role_for_group_checked:
                    message += 'One of the roles associated with this group is the newly created role with the same name.'
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='groups',
                                                           message=util.sanitize_text( message ),
                                                           status='done' ) )
        if ok:
            for user in trans.sa_session.query( trans.app.model.User ) \
                                        .filter( trans.app.model.User.table.c.deleted == false() ) \
                                        .order_by( trans.app.model.User.table.c.email ):
                out_users.append( ( user.id, user.email ) )
            for role in trans.sa_session.query( trans.app.model.Role ) \
                                        .filter( trans.app.model.Role.table.c.deleted == false() ) \
                                        .order_by( trans.app.model.Role.table.c.name ):
                out_roles.append( ( role.id, role.name ) )
        return trans.fill_template( '/admin/dataset_security/group/group_create.mako',
                                    name=name,
                                    in_users=in_users,
                                    out_users=out_users,
                                    in_roles=in_roles,
                                    out_roles=out_roles,
                                    create_role_for_group_checked=create_role_for_group_checked,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def mark_group_deleted( self, trans, **kwd ):
        params = util.Params( kwd )
        id = params.get( 'id', None )
        if not id:
            message = "No group ids received for marking deleted"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Deleted %d groups: " % len( ids )
        for group_id in ids:
            group = get_group( trans, group_id )
            group.deleted = True
            trans.sa_session.add( group )
            trans.sa_session.flush()
            message += " %s " % group.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='groups',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def undelete_group( self, trans, **kwd ):
        id = kwd.get( 'id', None )
        if not id:
            message = "No group ids received for undeleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        count = 0
        undeleted_groups = ""
        for group_id in ids:
            group = get_group( trans, group_id )
            if not group.deleted:
                message = "Group '%s' has not been deleted, so it cannot be undeleted." % group.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='groups',
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            group.deleted = False
            trans.sa_session.add( group )
            trans.sa_session.flush()
            count += 1
            undeleted_groups += " %s" % group.name
        message = "Undeleted %d groups: %s" % ( count, undeleted_groups )
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='groups',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def purge_group( self, trans, **kwd ):
        # This method should only be called for a Group that has previously been deleted.
        # Purging a deleted Group simply deletes all UserGroupAssociations and GroupRoleAssociations.
        id = kwd.get( 'id', None )
        if not id:
            message = "No group ids received for purging"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Purged %d groups: " % len( ids )
        for group_id in ids:
            group = get_group( trans, group_id )
            if not group.deleted:
                # We should never reach here, but just in case there is a bug somewhere...
                message = "Group '%s' has not been deleted, so it cannot be purged." % group.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='groups',
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            # Delete UserGroupAssociations
            for uga in group.users:
                trans.sa_session.delete( uga )
            # Delete GroupRoleAssociations
            for gra in group.roles:
                trans.sa_session.delete( gra )
            trans.sa_session.flush()
            message += " %s " % group.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='groups',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def create_new_user( self, trans, **kwd ):
        return trans.response.send_redirect( web.url_for( controller='user',
                                                          action='create',
                                                          cntrller='admin' ) )

    @web.expose
    @web.require_admin
    def reset_user_password( self, trans, **kwd ):
        user_id = kwd.get( 'id', None )
        message = ''
        status = ''
        users = []
        if user_id:
            user_ids = util.listify( user_id )
            if 'reset_user_password_button' in kwd:
                message = ''
                status = ''
                for user_id in user_ids:
                    user = get_user( trans, user_id )
                    password = kwd.get( 'password', None )
                    confirm = kwd.get( 'confirm', None )
                    if len( password ) < 6:
                        message = "Use a password of at least 6 characters."
                        status = 'error'
                        break
                    elif password != confirm:
                        message = "Passwords do not match."
                        status = 'error'
                        break
                    else:
                        user.set_password_cleartext( password )
                        trans.sa_session.add( user )
                        trans.sa_session.flush()
                if not message and not status:
                    trans.response.send_redirect( web.url_for( controller='admin',
                                                               action='users',
                                                               message=util.sanitize_text( message ),
                                                               status=status ) )
            users = [ get_user( trans, user_id ) for user_id in user_ids ]
            if len( user_ids ) > 1:
                user_id = ','.join( user_ids )
        else:
            message = 'No users received for resetting passwords.'
            status = 'error'
        return trans.fill_template( '/admin/user/reset_password.mako',
                                    id=user_id,
                                    message=util.sanitize_text( message ),
                                    status=status,
                                    users=users,
                                    password='',
                                    confirm='' )

    @web.expose
    @web.require_admin
    def mark_user_deleted( self, trans, ids ):
        message = 'Deleted %d users: ' % len( ids )
        for user_id in ids:
            user = get_user( trans, user_id )
            user.deleted = True
            trans.sa_session.add( user )
            trans.sa_session.flush()
            message += ' %s ' % user.email
        return ( message, 'done' )

    @web.expose
    @web.require_admin
    def undelete_user( self, trans, ids ):
        count = 0
        undeleted_users = ""
        for user_id in ids:
            user = get_user( trans, user_id )
            if not user.deleted:
                message = 'User \'%s\' has not been deleted, so it cannot be undeleted.' % user.email
                return ( message, 'error' )
            user.deleted = False
            trans.sa_session.add( user )
            trans.sa_session.flush()
            count += 1
            undeleted_users += ' %s' % user.email
        message = 'Undeleted %d users: %s' % ( count, undeleted_users )
        return ( message, 'done' )

    @web.expose
    @web.require_admin
    def purge_user( self, trans, ids ):
        # This method should only be called for a User that has previously been deleted.
        # We keep the User in the database ( marked as purged ), and stuff associated
        # with the user's private role in case we want the ability to unpurge the user
        # some time in the future.
        # Purging a deleted User deletes all of the following:
        # - History where user_id = User.id
        #    - HistoryDatasetAssociation where history_id = History.id
        #    - Dataset where HistoryDatasetAssociation.dataset_id = Dataset.id
        # - UserGroupAssociation where user_id == User.id
        # - UserRoleAssociation where user_id == User.id EXCEPT FOR THE PRIVATE ROLE
        # - UserAddress where user_id == User.id
        # Purging Histories and Datasets must be handled via the cleanup_datasets.py script
        message = 'Purged %d users: ' % len( ids )
        for user_id in ids:
            user = get_user( trans, user_id )
            if not user.deleted:
                return ( 'User \'%s\' has not been deleted, so it cannot be purged.' % user.email, 'error' )
            private_role = trans.app.security_agent.get_private_user_role( user )
            # Delete History
            for h in user.active_histories:
                trans.sa_session.refresh( h )
                for hda in h.active_datasets:
                    # Delete HistoryDatasetAssociation
                    d = trans.sa_session.query( trans.app.model.Dataset ).get( hda.dataset_id )
                    # Delete Dataset
                    if not d.deleted:
                        d.deleted = True
                        trans.sa_session.add( d )
                    hda.deleted = True
                    trans.sa_session.add( hda )
                h.deleted = True
                trans.sa_session.add( h )
            # Delete UserGroupAssociations
            for uga in user.groups:
                trans.sa_session.delete( uga )
            # Delete UserRoleAssociations EXCEPT FOR THE PRIVATE ROLE
            for ura in user.roles:
                if ura.role_id != private_role.id:
                    trans.sa_session.delete( ura )
            # Delete UserAddresses
            for address in user.addresses:
                trans.sa_session.delete( address )
            # Purge the user
            user.purged = True
            trans.sa_session.add( user )
            trans.sa_session.flush()
            message += '%s ' % user.email
        return ( message, 'done' )

    @web.expose
    @web.require_admin
    def recalculate_user_disk_usage( self, trans, user_id ):
        user = trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( user_id ) )
        if not user:
            return ( 'User not found for id (%s)' % sanitize_text( str( user_id ) ), 'error' )
        current = user.get_disk_usage()
        user.calculate_and_set_disk_usage()
        new = user.get_disk_usage()
        if new in ( current, None ):
            message = 'Usage is unchanged at %s.' % nice_size( current )
        else:
            message = 'Usage has changed by %s to %s.' % ( nice_size( new - current ), nice_size( new )  )
        return ( message, 'done' )

    @web.expose
    @web.require_admin
    def name_autocomplete_data( self, trans, q=None, limit=None, timestamp=None ):
        """Return autocomplete data for user emails"""
        ac_data = ""
        for user in trans.sa_session.query( trans.app.model.User ).filter_by( deleted=False ).filter( func.lower( trans.app.model.User.email ).like( q.lower() + "%" ) ):
            ac_data = ac_data + user.email + "\n"
        return ac_data

    @web.expose
    @web.require_admin
    def manage_roles_and_groups_for_user( self, trans, **kwd ):
        user_id = kwd.get( 'id', None )
        message = ''
        status = ''
        if not user_id:
            message += "Invalid user id (%s) received" % str( user_id )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        user = get_user( trans, user_id )
        private_role = trans.app.security_agent.get_private_user_role( user )
        if kwd.get( 'user_roles_groups_edit_button', False ):
            # Make sure the user is not dis-associating himself from his private role
            out_roles = kwd.get( 'out_roles', [] )
            if out_roles:
                out_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( out_roles ) ]
            if private_role in out_roles:
                message += "You cannot eliminate a user's private role association.  "
                status = 'error'
            in_roles = kwd.get( 'in_roles', [] )
            if in_roles:
                in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( in_roles ) ]
            out_groups = kwd.get( 'out_groups', [] )
            if out_groups:
                out_groups = [ trans.sa_session.query( trans.app.model.Group ).get( x ) for x in util.listify( out_groups ) ]
            in_groups = kwd.get( 'in_groups', [] )
            if in_groups:
                in_groups = [ trans.sa_session.query( trans.app.model.Group ).get( x ) for x in util.listify( in_groups ) ]
            if in_roles:
                trans.app.security_agent.set_entity_user_associations( users=[ user ], roles=in_roles, groups=in_groups )
                trans.sa_session.refresh( user )
                message += "User '%s' has been updated with %d associated roles and %d associated groups (private roles are not displayed)" % \
                    ( user.email, len( in_roles ), len( in_groups ) )
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='users',
                                                           message=util.sanitize_text( message ),
                                                           status='done' ) )
        in_roles = []
        out_roles = []
        in_groups = []
        out_groups = []
        for role in trans.sa_session.query( trans.app.model.Role ).filter( trans.app.model.Role.table.c.deleted == false() ) \
                                                                  .order_by( trans.app.model.Role.table.c.name ):
            if role in [ x.role for x in user.roles ]:
                in_roles.append( ( role.id, role.name ) )
            elif role.type != trans.app.model.Role.types.PRIVATE:
                # There is a 1 to 1 mapping between a user and a PRIVATE role, so private roles should
                # not be listed in the roles form fields, except for the currently selected user's private
                # role, which should always be in in_roles.  The check above is added as an additional
                # precaution, since for a period of time we were including private roles in the form fields.
                out_roles.append( ( role.id, role.name ) )
        for group in trans.sa_session.query( trans.app.model.Group ).filter( trans.app.model.Group.table.c.deleted == false() ) \
                                                                    .order_by( trans.app.model.Group.table.c.name ):
            if group in [ x.group for x in user.groups ]:
                in_groups.append( ( group.id, group.name ) )
            else:
                out_groups.append( ( group.id, group.name ) )
        message += "User '%s' is currently associated with %d roles and is a member of %d groups" % \
            ( user.email, len( in_roles ), len( in_groups ) )
        if not status:
            status = 'done'
        return trans.fill_template( '/admin/user/user.mako',
                                    user=user,
                                    in_roles=in_roles,
                                    out_roles=out_roles,
                                    in_groups=in_groups,
                                    out_groups=out_groups,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def jobs( self, trans, stop=[], stop_msg=None, cutoff=180, job_lock=None, ajl_submit=None, **kwd ):
        deleted = []
        msg = None
        status = None
        job_ids = util.listify( stop )
        if job_ids and stop_msg in [ None, '' ]:
            msg = 'Please enter an error message to display to the user describing why the job was terminated'
            status = 'error'
        elif job_ids:
            if stop_msg[-1] not in PUNCTUATION:
                stop_msg += '.'
            for job_id in job_ids:
                error_msg = "This job was stopped by an administrator: %s  <a href='%s' target='_blank'>Contact support</a> for additional help." \
                    % ( stop_msg, self.app.config.get("support_url", "https://galaxyproject.org/support/" ) )
                if trans.app.config.track_jobs_in_database:
                    job = trans.sa_session.query( trans.app.model.Job ).get( job_id )
                    job.stderr = error_msg
                    job.set_state( trans.app.model.Job.states.DELETED_NEW )
                    trans.sa_session.add( job )
                else:
                    trans.app.job_manager.job_stop_queue.put( job_id, error_msg=error_msg )
                deleted.append( str( job_id ) )
        if deleted:
            msg = 'Queued job'
            if len( deleted ) > 1:
                msg += 's'
            msg += ' for deletion: '
            msg += ', '.join( deleted )
            status = 'done'
            trans.sa_session.flush()
        if ajl_submit:
            if job_lock == 'on':
                galaxy.queue_worker.send_control_task(trans.app, 'admin_job_lock',
                                                      kwargs={'job_lock': True } )
                job_lock = True
            else:
                galaxy.queue_worker.send_control_task(trans.app, 'admin_job_lock',
                                                      kwargs={'job_lock': False } )
                job_lock = False
        else:
            job_lock = trans.app.job_manager.job_lock
        cutoff_time = datetime.utcnow() - timedelta( seconds=int( cutoff ) )
        jobs = trans.sa_session.query( trans.app.model.Job ) \
                               .filter( and_( trans.app.model.Job.table.c.update_time < cutoff_time,
                                              or_( trans.app.model.Job.state == trans.app.model.Job.states.NEW,
                                                   trans.app.model.Job.state == trans.app.model.Job.states.QUEUED,
                                                   trans.app.model.Job.state == trans.app.model.Job.states.RUNNING,
                                                   trans.app.model.Job.state == trans.app.model.Job.states.UPLOAD ) ) ) \
                               .order_by( trans.app.model.Job.table.c.update_time.desc() ).all()
        recent_jobs = trans.sa_session.query( trans.app.model.Job ) \
            .filter( and_( trans.app.model.Job.table.c.update_time > cutoff_time,
                           or_( trans.app.model.Job.state == trans.app.model.Job.states.ERROR,
                                trans.app.model.Job.state == trans.app.model.Job.states.OK) ) ) \
            .order_by( trans.app.model.Job.table.c.update_time.desc() ).all()
        last_updated = {}
        for job in jobs:
            delta = datetime.utcnow() - job.update_time
            if delta.days > 0:
                last_updated[job.id] = '%s hours' % ( delta.days * 24 + int( delta.seconds / 60 / 60 ) )
            elif delta > timedelta( minutes=59 ):
                last_updated[job.id] = '%s hours' % int( delta.seconds / 60 / 60 )
            else:
                last_updated[job.id] = '%s minutes' % int( delta.seconds / 60 )
        finished = {}
        for job in recent_jobs:
            delta = datetime.utcnow() - job.update_time
            if delta.days > 0:
                finished[job.id] = '%s hours' % ( delta.days * 24 + int( delta.seconds / 60 / 60 ) )
            elif delta > timedelta( minutes=59 ):
                finished[job.id] = '%s hours' % int( delta.seconds / 60 / 60 )
            else:
                finished[job.id] = '%s minutes' % int( delta.seconds / 60 )
        return trans.fill_template( '/admin/jobs.mako',
                                    jobs=jobs,
                                    recent_jobs=recent_jobs,
                                    last_updated=last_updated,
                                    finished=finished,
                                    cutoff=cutoff,
                                    msg=msg,
                                    status=status,
                                    job_lock=job_lock)

    @web.expose
    @web.require_admin
    def job_info( self, trans, jobid=None ):
        job = None
        if jobid is not None:
            job = trans.sa_session.query( trans.app.model.Job ).get(jobid)
        return trans.fill_template( '/webapps/reports/job_info.mako',
                                    job=job,
                                    message="<a href='jobs'>Back</a>" )

    @web.expose
    @web.require_admin
    def manage_tool_dependencies( self,
                                  trans,
                                  install_dependencies=False,
                                  uninstall_dependencies=False,
                                  remove_unused_dependencies=False,
                                  selected_tool_ids=None,
                                  selected_environments_to_uninstall=None,
                                  viewkey='View tool-centric dependencies'):
        if not selected_tool_ids:
            selected_tool_ids = []
        if not selected_environments_to_uninstall:
            selected_environments_to_uninstall = []
        tools_by_id = trans.app.toolbox.tools_by_id
        view = six.next(six.itervalues(trans.app.toolbox.tools_by_id))._view
        if selected_tool_ids:
            # install the dependencies for the tools in the selected_tool_ids list
            if not isinstance(selected_tool_ids, list):
                selected_tool_ids = [selected_tool_ids]
            requirements = set([tools_by_id[tid].tool_requirements for tid in selected_tool_ids])
            if install_dependencies:
                [view.install_dependencies(r) for r in requirements]
            elif uninstall_dependencies:
                [view.uninstall_dependencies(index=None, requirements=r) for r in requirements]
        if selected_environments_to_uninstall and remove_unused_dependencies:
            if not isinstance(selected_environments_to_uninstall, list):
                selected_environments_to_uninstall = [selected_environments_to_uninstall]
            view.remove_unused_dependency_paths(selected_environments_to_uninstall)
        return trans.fill_template( '/webapps/galaxy/admin/manage_dependencies.mako',
                                    tools=tools_by_id,
                                    requirements_status=view.toolbox_requirements_status,
                                    tool_ids_by_requirements=view.tool_ids_by_requirements,
                                    unused_environments=view.unused_dependency_paths,
                                    viewkey=viewkey )

    @web.expose
    @web.require_admin
    def sanitize_whitelist( self, trans, submit_whitelist=False, tools_to_whitelist=[]):
        if submit_whitelist:
            # write the configured sanitize_whitelist_file with new whitelist
            # and update in-memory list.
            with open(trans.app.config.sanitize_whitelist_file, 'wt') as f:
                if isinstance(tools_to_whitelist, six.string_types):
                    tools_to_whitelist = [tools_to_whitelist]
                new_whitelist = sorted([tid for tid in tools_to_whitelist if tid in trans.app.toolbox.tools_by_id])
                f.write("\n".join(new_whitelist))
            trans.app.config.sanitize_whitelist = new_whitelist
            galaxy.queue_worker.send_control_task(trans.app, 'reload_sanitize_whitelist', noop_self=True)
            # dispatch a message to reload list for other processes
        return trans.fill_template( '/webapps/galaxy/admin/sanitize_whitelist.mako',
                                    sanitize_all=trans.app.config.sanitize_all_html,
                                    tools=trans.app.toolbox.tools_by_id )


# ---- Utility methods -------------------------------------------------------


def get_user( trans, user_id ):
    """Get a User from the database by id."""
    user = trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( user_id ) )
    if not user:
        return trans.show_error_message( "User not found for id (%s)" % str( user_id ) )
    return user


def get_role( trans, id ):
    """Get a Role from the database by id."""
    # Load user from database
    id = trans.security.decode_id( id )
    role = trans.sa_session.query( trans.model.Role ).get( id )
    if not role:
        return trans.show_error_message( "Role not found for id (%s)" % str( id ) )
    return role


def get_group( trans, id ):
    """Get a Group from the database by id."""
    # Load user from database
    id = trans.security.decode_id( id )
    group = trans.sa_session.query( trans.model.Group ).get( id )
    if not group:
        return trans.show_error_message( "Group not found for id (%s)" % str( id ) )
    return group


def get_quota( trans, id ):
    """Get a Quota from the database by id."""
    # Load user from database
    id = trans.security.decode_id( id )
    quota = trans.sa_session.query( trans.model.Quota ).get( id )
    return quota
