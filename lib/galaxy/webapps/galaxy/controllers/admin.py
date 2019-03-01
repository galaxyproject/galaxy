import imp
import logging
import os
import time
from datetime import datetime, timedelta
from string import punctuation as PUNCTUATION

import six
from sqlalchemy import and_, false, or_

import galaxy.queue_worker
from galaxy import (
    model,
    util,
    web
)
from galaxy.actions.admin import AdminActions
from galaxy.exceptions import ActionInputError, MessageException
from galaxy.model import tool_shed_install as install_model
from galaxy.util import (
    nice_size,
    sanitize_text,
    url_get
)
from galaxy.util.hash_util import new_secure_hash
from galaxy.util.odict import odict
from galaxy.web import url_for
from galaxy.web.base import controller
from galaxy.web.base.controller import UsesQuotaMixin
from galaxy.web.framework.helpers import grids, time_ago
from galaxy.web.params import QuotaParamParser
from tool_shed.util import (
    common_util,
    encoding_util,
    repository_util
)
from tool_shed.util.web_util import escape


log = logging.getLogger(__name__)
compliance_log = logging.getLogger('COMPLIANCE')


class UserListGrid(grids.Grid):

    class EmailColumn(grids.TextColumn):
        def get_value(self, trans, grid, user):
            return escape(user.email)

    class UserNameColumn(grids.TextColumn):
        def get_value(self, trans, grid, user):
            if user.username:
                return escape(user.username)
            return 'not set'

    class StatusColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            if user.purged:
                return "purged"
            elif user.deleted:
                return "deleted"
            return ""

    class GroupsColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            if user.groups:
                return len(user.groups)
            return 0

    class RolesColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            if user.roles:
                return len(user.roles)
            return 0

    class ExternalColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            if user.external:
                return 'yes'
            return 'no'

    class LastLoginColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            if user.galaxy_sessions:
                return self.format(user.galaxy_sessions[0].update_time)
            return 'never'

    class TimeCreatedColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            return user.create_time.strftime('%x')

    class ActivatedColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            if user.active:
                return 'Y'
            else:
                return 'N'

    class APIKeyColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            if user.api_keys:
                return user.api_keys[0].key
            else:
                return ""

    # Grid definition
    title = "Users"
    title_id = "users-grid"
    model_class = model.User
    default_sort_key = "email"
    columns = [
        EmailColumn("Email",
                    key="email",
                    model_class=model.User,
                    link=(lambda item: dict(controller="user", action="information", id=item.id, webapp="galaxy")),
                    attach_popup=True,
                    filterable="advanced",
                    target="top"),
        UserNameColumn("User Name",
                       key="username",
                       model_class=model.User,
                       attach_popup=False,
                       filterable="advanced"),
        GroupsColumn("Groups", attach_popup=False),
        RolesColumn("Roles", attach_popup=False),
        ExternalColumn("External", attach_popup=False),
        LastLoginColumn("Last Login", format=time_ago),
        StatusColumn("Status", attach_popup=False),
        TimeCreatedColumn("Created", attach_popup=False),
        ActivatedColumn("Activated", attach_popup=False),
        APIKeyColumn("API Key", attach_popup=False),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn("Deleted", key="deleted", visible=False, filterable="advanced")
    ]
    columns.append(grids.MulticolFilterColumn("Search",
                                              cols_to_filter=[columns[0], columns[1]],
                                              key="free-text-search",
                                              visible=False,
                                              filterable="standard"))
    global_actions = [
        grids.GridAction("Create new user", url_args=dict(action="users/create"))
    ]
    operations = [
        grids.GridOperation("Manage Information",
                            condition=(lambda item: not item.deleted),
                            allow_multiple=False,
                            url_args=dict(controller="user", action="information", webapp="galaxy")),
        grids.GridOperation("Manage Roles and Groups",
                            condition=(lambda item: not item.deleted),
                            allow_multiple=False,
                            url_args=dict(action="form/manage_roles_and_groups_for_user")),
        grids.GridOperation("Reset Password",
                            condition=(lambda item: not item.deleted),
                            allow_multiple=True,
                            url_args=dict(action="form/reset_user_password"),
                            target="top"),
        grids.GridOperation("Recalculate Disk Usage",
                            condition=(lambda item: not item.deleted),
                            allow_multiple=False),
        grids.GridOperation("Generate New API Key",
                            allow_multiple=False,
                            async_compatible=True)

    ]
    standard_filters = [
        grids.GridColumnFilter("Active", args=dict(deleted=False)),
        grids.GridColumnFilter("Deleted", args=dict(deleted=True, purged=False)),
        grids.GridColumnFilter("Purged", args=dict(purged=True)),
        grids.GridColumnFilter("All", args=dict(deleted='All'))
    ]
    num_rows_per_page = 50
    use_paging = True

    def get_current_item(self, trans, **kwargs):
        return trans.user


class RoleListGrid(grids.Grid):

    class NameColumn(grids.TextColumn):
        def get_value(self, trans, grid, role):
            return escape(role.name)

    class DescriptionColumn(grids.TextColumn):
        def get_value(self, trans, grid, role):
            if role.description:
                return escape(role.description)
            return ''

    class TypeColumn(grids.TextColumn):
        def get_value(self, trans, grid, role):
            return role.type

    class StatusColumn(grids.GridColumn):
        def get_value(self, trans, grid, role):
            if role.deleted:
                return "deleted"
            return ""

    class GroupsColumn(grids.GridColumn):
        def get_value(self, trans, grid, role):
            if role.groups:
                return len(role.groups)
            return 0

    class UsersColumn(grids.GridColumn):
        def get_value(self, trans, grid, role):
            if role.users:
                return len(role.users)
            return 0

    # Grid definition
    title = "Roles"
    title_id = "roles-grid"
    model_class = model.Role
    default_sort_key = "name"
    columns = [
        NameColumn("Name",
                   key="name",
                   link=(lambda item: dict(action="form/manage_users_and_groups_for_role", id=item.id, webapp="galaxy")),
                   model_class=model.Role,
                   attach_popup=True,
                   filterable="advanced",
                   target="top"),
        DescriptionColumn("Description",
                          key='description',
                          model_class=model.Role,
                          attach_popup=False,
                          filterable="advanced"),
        TypeColumn("Type",
                   key='type',
                   model_class=model.Role,
                   attach_popup=False,
                   filterable="advanced"),
        GroupsColumn("Groups", attach_popup=False),
        UsersColumn("Users", attach_popup=False),
        StatusColumn("Status", attach_popup=False),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn("Deleted", key="deleted", visible=False, filterable="advanced"),
        grids.GridColumn("Last Updated", key="update_time", format=time_ago)
    ]
    columns.append(grids.MulticolFilterColumn("Search",
                                              cols_to_filter=[columns[0], columns[1], columns[2]],
                                              key="free-text-search",
                                              visible=False,
                                              filterable="standard"))
    global_actions = [
        grids.GridAction("Add new role", url_args=dict(action="form/create_role"))
    ]
    operations = [grids.GridOperation("Edit Name/Description",
                                      condition=(lambda item: not item.deleted),
                                      allow_multiple=False,
                                      url_args=dict(action="form/rename_role")),
                  grids.GridOperation("Edit Permissions",
                                      condition=(lambda item: not item.deleted),
                                      allow_multiple=False,
                                      url_args=dict(action="form/manage_users_and_groups_for_role", webapp="galaxy")),
                  grids.GridOperation("Delete",
                                      condition=(lambda item: not item.deleted),
                                      allow_multiple=True),
                  grids.GridOperation("Undelete",
                                      condition=(lambda item: item.deleted),
                                      allow_multiple=True),
                  grids.GridOperation("Purge",
                                      condition=(lambda item: item.deleted),
                                      allow_multiple=True)]
    standard_filters = [
        grids.GridColumnFilter("Active", args=dict(deleted=False)),
        grids.GridColumnFilter("Deleted", args=dict(deleted=True)),
        grids.GridColumnFilter("All", args=dict(deleted='All'))
    ]
    num_rows_per_page = 50
    use_paging = True

    def apply_query_filter(self, trans, query, **kwargs):
        return query.filter(model.Role.type != model.Role.types.PRIVATE)


class GroupListGrid(grids.Grid):

    class NameColumn(grids.TextColumn):
        def get_value(self, trans, grid, group):
            return escape(group.name)

    class StatusColumn(grids.GridColumn):
        def get_value(self, trans, grid, group):
            if group.deleted:
                return "deleted"
            return ""

    class RolesColumn(grids.GridColumn):
        def get_value(self, trans, grid, group):
            if group.roles:
                return len(group.roles)
            return 0

    class UsersColumn(grids.GridColumn):
        def get_value(self, trans, grid, group):
            if group.members:
                return len(group.members)
            return 0

    # Grid definition
    title = "Groups"
    title_id = "groups-grid"
    model_class = model.Group
    default_sort_key = "name"
    columns = [
        NameColumn("Name",
                   key="name",
                   link=(lambda item: dict(action="form/manage_users_and_roles_for_group", id=item.id, webapp="galaxy")),
                   model_class=model.Group,
                   attach_popup=True,
                   filterable="advanced"),
        UsersColumn("Users", attach_popup=False),
        RolesColumn("Roles", attach_popup=False),
        StatusColumn("Status", attach_popup=False),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn("Deleted", key="deleted", visible=False, filterable="advanced"),
        grids.GridColumn("Last Updated", key="update_time", format=time_ago)
    ]
    columns.append(grids.MulticolFilterColumn("Search",
                                              cols_to_filter=[columns[0]],
                                              key="free-text-search",
                                              visible=False,
                                              filterable="standard"))
    global_actions = [
        grids.GridAction("Add new group", url_args=dict(action="form/create_group"))
    ]
    operations = [grids.GridOperation("Edit Name",
                                      condition=(lambda item: not item.deleted),
                                      allow_multiple=False,
                                      url_args=dict(action="form/rename_group")),
                  grids.GridOperation("Edit Permissions",
                                      condition=(lambda item: not item.deleted),
                                      allow_multiple=False,
                                      url_args=dict(action="form/manage_users_and_roles_for_group", webapp="galaxy")),
                  grids.GridOperation("Delete",
                                      condition=(lambda item: not item.deleted),
                                      allow_multiple=True),
                  grids.GridOperation("Undelete",
                                      condition=(lambda item: item.deleted),
                                      allow_multiple=True),
                  grids.GridOperation("Purge",
                                      condition=(lambda item: item.deleted),
                                      allow_multiple=True)]
    standard_filters = [
        grids.GridColumnFilter("Active", args=dict(deleted=False)),
        grids.GridColumnFilter("Deleted", args=dict(deleted=True)),
        grids.GridColumnFilter("All", args=dict(deleted='All'))
    ]
    num_rows_per_page = 50
    use_paging = True


class QuotaListGrid(grids.Grid):

    class NameColumn(grids.TextColumn):
        def get_value(self, trans, grid, quota):
            return escape(quota.name)

    class DescriptionColumn(grids.TextColumn):
        def get_value(self, trans, grid, quota):
            if quota.description:
                return escape(quota.description)
            return ''

    class AmountColumn(grids.TextColumn):
        def get_value(self, trans, grid, quota):
            return quota.operation + quota.display_amount

    class StatusColumn(grids.GridColumn):
        def get_value(self, trans, grid, quota):
            if quota.deleted:
                return "deleted"
            elif quota.default:
                return "<strong>default for %s users</strong>" % quota.default[0].type
            return ""

    class UsersColumn(grids.GridColumn):
        def get_value(self, trans, grid, quota):
            if quota.users:
                return len(quota.users)
            return 0

    class GroupsColumn(grids.GridColumn):
        def get_value(self, trans, grid, quota):
            if quota.groups:
                return len(quota.groups)
            return 0

    # Grid definition
    title = "Quotas"
    model_class = model.Quota
    default_sort_key = "name"
    columns = [
        NameColumn("Name",
                   key="name",
                   link=(lambda item: dict(action="form/edit_quota", id=item.id)),
                   model_class=model.Quota,
                   attach_popup=True,
                   filterable="advanced"),
        DescriptionColumn("Description",
                          key='description',
                          model_class=model.Quota,
                          attach_popup=False,
                          filterable="advanced"),
        AmountColumn("Amount",
                     key='amount',
                     model_class=model.Quota,
                     attach_popup=False),
        UsersColumn("Users", attach_popup=False),
        GroupsColumn("Groups", attach_popup=False),
        StatusColumn("Status", attach_popup=False),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn("Deleted", key="deleted", visible=False, filterable="advanced")
    ]
    columns.append(grids.MulticolFilterColumn("Search",
                                              cols_to_filter=[columns[0], columns[1]],
                                              key="free-text-search",
                                              visible=False,
                                              filterable="standard"))
    global_actions = [
        grids.GridAction("Add new quota", dict(action="form/create_quota"))
    ]
    operations = [grids.GridOperation("Rename",
                                      condition=(lambda item: not item.deleted),
                                      allow_multiple=False,
                                      url_args=dict(action="form/rename_quota")),
                  grids.GridOperation("Change amount",
                                      condition=(lambda item: not item.deleted),
                                      allow_multiple=False,
                                      url_args=dict(action="form/edit_quota")),
                  grids.GridOperation("Manage users and groups",
                                      condition=(lambda item: not item.default and not item.deleted),
                                      allow_multiple=False,
                                      url_args=dict(action="form/manage_users_and_groups_for_quota")),
                  grids.GridOperation("Set as different type of default",
                                      condition=(lambda item: item.default),
                                      allow_multiple=False,
                                      url_args=dict(action="form/set_quota_default")),
                  grids.GridOperation("Set as default",
                                      condition=(lambda item: not item.default and not item.deleted),
                                      allow_multiple=False,
                                      url_args=dict(action="form/set_quota_default")),
                  grids.GridOperation("Unset as default",
                                      condition=(lambda item: item.default and not item.deleted),
                                      allow_multiple=False),
                  grids.GridOperation("Delete",
                                      condition=(lambda item: not item.deleted and not item.default),
                                      allow_multiple=True),
                  grids.GridOperation("Undelete",
                                      condition=(lambda item: item.deleted),
                                      allow_multiple=True),
                  grids.GridOperation("Purge",
                                      condition=(lambda item: item.deleted),
                                      allow_multiple=True)]
    standard_filters = [
        grids.GridColumnFilter("Active", args=dict(deleted=False)),
        grids.GridColumnFilter("Deleted", args=dict(deleted=True)),
        grids.GridColumnFilter("All", args=dict(deleted='All'))
    ]
    num_rows_per_page = 50
    use_paging = True


class ToolVersionListGrid(grids.Grid):

    class ToolIdColumn(grids.TextColumn):
        def get_value(self, trans, grid, tool_version):
            toolbox = trans.app.toolbox
            if toolbox.has_tool(tool_version.tool_id, exact=True):
                link = url_for(controller='tool_runner', tool_id=tool_version.tool_id)
                link_str = '<a target="_blank" href="%s">' % link
                return '<div class="count-box state-color-ok">%s%s</a></div>' % (link_str, tool_version.tool_id)
            return tool_version.tool_id

    class ToolVersionsColumn(grids.TextColumn):
        def get_value(self, trans, grid, tool_version):
            tool_ids_str = ''
            toolbox = trans.app.toolbox
            tool = toolbox._tools_by_id.get(tool_version.tool_id)
            if tool:
                for tool_id in tool.lineage.tool_ids:
                    if toolbox.has_tool(tool_id, exact=True):
                        link = url_for(controller='tool_runner', tool_id=tool_id)
                        link_str = '<a target="_blank" href="%s">' % link
                        tool_ids_str += '<div class="count-box state-color-ok">%s%s</a></div><br/>' % (link_str, tool_id)
                    else:
                        tool_ids_str += '%s<br/>' % tool_version.tool_id
            else:
                tool_ids_str += '%s<br/>' % tool_version.tool_id
            return tool_ids_str

    # Grid definition
    title = "Tool versions"
    model_class = install_model.ToolVersion
    default_sort_key = "tool_id"
    columns = [
        ToolIdColumn("Tool id",
                     key='tool_id',
                     attach_popup=False),
        ToolVersionsColumn("Version lineage by tool id (parent/child ordered)")
    ]
    columns.append(grids.MulticolFilterColumn("Search tool id",
                                              cols_to_filter=[columns[0]],
                                              key="free-text-search",
                                              visible=False,
                                              filterable="standard"))
    global_actions = []
    operations = []
    standard_filters = []
    default_filter = {}
    num_rows_per_page = 50
    use_paging = True

    def build_initial_query(self, trans, **kwd):
        return trans.install_model.context.query(self.model_class)


class AdminGalaxy(controller.JSAppLauncher, AdminActions, UsesQuotaMixin, QuotaParamParser):

    user_list_grid = UserListGrid()
    role_list_grid = RoleListGrid()
    group_list_grid = GroupListGrid()
    quota_list_grid = QuotaListGrid()
    tool_version_list_grid = ToolVersionListGrid()
    delete_operation = grids.GridOperation("Delete", condition=(lambda item: not item.deleted), allow_multiple=True)
    undelete_operation = grids.GridOperation("Undelete", condition=(lambda item: item.deleted and not item.purged), allow_multiple=True)
    purge_operation = grids.GridOperation("Purge", condition=(lambda item: item.deleted and not item.purged), allow_multiple=True)
    impersonate_operation = grids.GridOperation(
        "Impersonate",
        url_args=dict(controller="admin", action="impersonate"),
        allow_multiple=False
    )

    @web.expose
    @web.require_admin
    def index(self, trans, **kwd):
        return self.client(trans, **kwd)

    @web.expose
    @web.require_admin
    def client(self, trans, **kwd):
        """
        Endpoint for admin clientside routes.
        """
        message = escape(kwd.get('message', ''))
        status = kwd.get('status', 'done')
        settings = {
            'is_repo_installed': trans.install_model.context.query(trans.install_model.ToolShedRepository).first() is not None,
            'installing_repository_ids': repository_util.get_ids_of_tool_shed_repositories_being_installed(trans.app, as_string=True),
            'is_tool_shed_installed': bool(trans.app.tool_shed_registry and trans.app.tool_shed_registry.tool_sheds)
        }
        return self._bootstrapped_client(trans, app_name='admin', settings=settings, message=message, status=status)

    @web.expose
    @web.json
    @web.require_admin
    def data_tables_list(self, trans, **kwd):
        data = []
        message = kwd.get('message', '')
        status = kwd.get('status', 'done')
        sorted_data_tables = sorted(
            trans.app.tool_data_tables.get_tables().items()
        )

        for data_table_elem_name, data_table in sorted_data_tables:
            for filename, file_dict in data_table.filenames.iteritems():
                file_missing = ['file missing'] \
                    if not file_dict.get('found') else []
                data.append({
                    'name': data_table.name,
                    'filename': filename,
                    'tool_data_path': file_dict.get('tool_data_path'),
                    'errors': ', '.join(file_missing + [
                        error for error in file_dict.get('errors', [])
                    ]),
                })

        return {'data': data, 'message': message, 'status': status}

    @web.expose
    @web.json
    @web.require_admin
    def data_types_list(self, trans, **kwd):
        datatypes = []
        keys = set()
        message = kwd.get('message', '')
        status = kwd.get('status', 'done')
        for dtype in sorted(trans.app.datatypes_registry.datatype_elems,
                           key=lambda dtype: dtype.get('extension')):
            datatypes.append(dtype.attrib)
            keys |= set(dtype.attrib)
        return {'keys': list(keys), 'data': datatypes, 'message': message, 'status': status}

    @web.expose
    @web.json
    @web.require_admin
    def users_list(self, trans, **kwd):
        message = kwd.get('message', '')
        status = kwd.get('status', '')
        if 'operation' in kwd:
            id = kwd.get('id')
            if not id:
                message, status = ('Invalid user id (%s) received.' % str(id), 'error')
            ids = util.listify(id)
            operation = kwd['operation'].lower()
            if operation == 'delete':
                message, status = self._delete_user(trans, ids)
            elif operation == 'undelete':
                message, status = self._undelete_user(trans, ids)
            elif operation == 'purge':
                message, status = self._purge_user(trans, ids)
            elif operation == 'recalculate disk usage':
                message, status = self._recalculate_user(trans, id)
            elif operation == 'generate new api key':
                message, status = self._new_user_apikey(trans, id)
        if trans.app.config.allow_user_deletion:
            if self.delete_operation not in self.user_list_grid.operations:
                self.user_list_grid.operations.append(self.delete_operation)
            if self.undelete_operation not in self.user_list_grid.operations:
                self.user_list_grid.operations.append(self.undelete_operation)
            if self.purge_operation not in self.user_list_grid.operations:
                self.user_list_grid.operations.append(self.purge_operation)
        if trans.app.config.allow_user_impersonation:
            if self.impersonate_operation not in self.user_list_grid.operations:
                self.user_list_grid.operations.append(self.impersonate_operation)
        if message and status:
            kwd['message'] = util.sanitize_text(message)
            kwd['status'] = status
        return self.user_list_grid(trans, **kwd)

    @web.expose_api
    @web.require_admin
    def quotas_list(self, trans, payload=None, **kwargs):
        message = kwargs.get('message', '')
        status = kwargs.get('status', '')
        if 'operation' in kwargs:
            id = kwargs.get('id')
            if not id:
                return self.message_exception(trans, 'Invalid quota id (%s) received.' % str(id))
            quotas = []
            for quota_id in util.listify(id):
                try:
                    quotas.append(get_quota(trans, quota_id))
                except MessageException as e:
                    return self.message_exception(trans, str(e))
            operation = kwargs.pop('operation').lower()
            try:
                if operation == 'delete':
                    message = self._delete_quota(quotas)
                elif operation == 'undelete':
                    message = self._undelete_quota(quotas)
                elif operation == 'purge':
                    message = self._purge_quota(quotas)
                elif operation == 'unset as default':
                    message = self._unset_quota_default(quotas[0])
            except ActionInputError as e:
                message, status = (e.err_msg, 'error')
        if message:
            kwargs['message'] = util.sanitize_text(message)
            kwargs['status'] = status or 'done'
        return self.quota_list_grid(trans, **kwargs)

    @web.expose_api
    @web.require_admin
    def create_quota(self, trans, payload=None, **kwd):
        if trans.request.method == 'GET':
            all_users = []
            all_groups = []
            for user in trans.sa_session.query(trans.app.model.User) \
                                        .filter(trans.app.model.User.table.c.deleted == false()) \
                                        .order_by(trans.app.model.User.table.c.email):
                all_users.append((user.email, trans.security.encode_id(user.id)))
            for group in trans.sa_session.query(trans.app.model.Group) \
                                         .filter(trans.app.model.Group.table.c.deleted == false()) \
                                         .order_by(trans.app.model.Group.table.c.name):
                all_groups.append((group.name, trans.security.encode_id(group.id)))
            default_options = [('No', 'no')]
            for typ in trans.app.model.DefaultQuotaAssociation.types.__dict__.values():
                default_options.append(('Yes, ' + typ, typ))
            return {'title'  : 'Create Quota',
                    'inputs' : [
                        {
                            'name'    : 'name',
                            'label'   : 'Name'
                        }, {
                            'name'    : 'description',
                            'label'   : 'Description'
                        }, {
                            'name'    : 'amount',
                            'label'   : 'Amount',
                            'help'    : 'Examples: "10000MB", "99 gb", "0.2T", "unlimited"'
                        }, {
                            'name'    : 'operation',
                            'label'   : 'Assign, increase by amount, or decrease by amount?',
                            'options' : [('=', '='), ('+', '+'), ('-', '-')]
                        }, {
                            'name'    : 'default',
                            'label'   : 'Is this quota a default for a class of users (if yes, what type)?',
                            'options' : default_options,
                            'help'    : 'Warning: Any users or groups associated with this quota will be disassociated.'
                        },
                        build_select_input('in_groups', 'Groups', all_groups, []),
                        build_select_input('in_users', 'Users', all_users, [])]}
        else:
            try:
                quota, message = self._create_quota(util.Params(payload), decode_id=trans.security.decode_id)
                return {'message': message}
            except ActionInputError as e:
                return self.message_exception(trans, e.err_msg)

    @web.expose_api
    @web.require_admin
    def rename_quota(self, trans, payload=None, **kwd):
        id = kwd.get('id')
        if not id:
            return self.message_exception(trans, 'No quota id received for renaming.')
        quota = get_quota(trans, id)
        if trans.request.method == 'GET':
            return {
                'title'  : 'Change quota name and description for \'%s\'' % util.sanitize_text(quota.name),
                'inputs' : [{
                    'name'  : 'name',
                    'label' : 'Name',
                    'value' : quota.name
                }, {
                    'name'  : 'description',
                    'label' : 'Description',
                    'value' : quota.description
                }]
            }
        else:
            try:
                return {'message': self._rename_quota(quota, util.Params(payload))}
            except ActionInputError as e:
                return self.message_exception(trans, e.err_msg)

    @web.expose_api
    @web.require_admin
    def manage_users_and_groups_for_quota(self, trans, payload=None, **kwd):
        quota_id = kwd.get('id')
        if not quota_id:
            return self.message_exception(trans, 'Invalid quota id (%s) received' % str(quota_id))
        quota = get_quota(trans, quota_id)
        if trans.request.method == 'GET':
            in_users = []
            all_users = []
            in_groups = []
            all_groups = []
            for user in trans.sa_session.query(trans.app.model.User) \
                                        .filter(trans.app.model.User.table.c.deleted == false()) \
                                        .order_by(trans.app.model.User.table.c.email):
                if user in [x.user for x in quota.users]:
                    in_users.append(trans.security.encode_id(user.id))
                all_users.append((user.email, trans.security.encode_id(user.id)))
            for group in trans.sa_session.query(trans.app.model.Group) \
                                         .filter(trans.app.model.Group.table.c.deleted == false()) \
                                         .order_by(trans.app.model.Group.table.c.name):
                if group in [x.group for x in quota.groups]:
                    in_groups.append(trans.security.encode_id(group.id))
                all_groups.append((group.name, trans.security.encode_id(group.id)))
            return {'title'  : 'Quota \'%s\'' % quota.name,
                    'message': 'Quota \'%s\' is currently associated with %d user(s) and %d group(s).' %
                    (quota.name, len(in_users), len(in_groups)),
                    'status' : 'info',
                    'inputs' : [build_select_input('in_groups', 'Groups', all_groups, in_groups),
                                build_select_input('in_users', 'Users', all_users, in_users)]}
        else:
            try:
                return {'message': self._manage_users_and_groups_for_quota(quota, util.Params(payload), decode_id=trans.security.decode_id)}
            except ActionInputError as e:
                return self.message_exception(trans, e.err_msg)

    @web.expose_api
    @web.require_admin
    def edit_quota(self, trans, payload=None, **kwd):
        id = kwd.get('id')
        if not id:
            return self.message_exception(trans, 'No quota id received for renaming.')
        quota = get_quota(trans, id)
        if trans.request.method == 'GET':
            return {
                'title'  : 'Edit quota size for \'%s\'' % util.sanitize_text(quota.name),
                'inputs' : [{
                    'name'    : 'amount',
                    'label'   : 'Amount',
                    'value'   : quota.display_amount,
                    'help'    : 'Examples: "10000MB", "99 gb", "0.2T", "unlimited"'
                }, {
                    'name'    : 'operation',
                    'label'   : 'Assign, increase by amount, or decrease by amount?',
                    'options' : [('=', '='), ('+', '+'), ('-', '-')],
                    'value'   : quota.operation
                }]
            }
        else:
            try:
                return {'message': self._edit_quota(quota, util.Params(payload))}
            except ActionInputError as e:
                return self.message_exception(trans, e.err_msg)

    @web.expose_api
    @web.require_admin
    def set_quota_default(self, trans, payload=None, **kwd):
        id = kwd.get('id')
        if not id:
            return self.message_exception(trans, 'No quota id received for renaming.')
        quota = get_quota(trans, id)
        if trans.request.method == 'GET':
            default_value = quota.default[0].type if quota.default else 'no'
            default_options = [('No', 'no')]
            for typ in trans.app.model.DefaultQuotaAssociation.types.__dict__.values():
                default_options.append(('Yes, ' + typ, typ))
            return {
                'title'  : 'Set quota default for \'%s\'' % util.sanitize_text(quota.name),
                'inputs' : [{
                    'name'    : 'default',
                    'label'   : 'Assign, increase by amount, or decrease by amount?',
                    'options' : default_options,
                    'value'   : default_value,
                    'help'    : 'Warning: Any users or groups associated with this quota will be disassociated.'
                }]
            }
        else:
            try:
                return {'message': self._set_quota_default(quota, util.Params(payload))}
            except ActionInputError as e:
                return self.message_exception(trans, e.err_msg)

    @web.expose
    @web.require_admin
    def impersonate(self, trans, **kwd):
        if not trans.app.config.allow_user_impersonation:
            return trans.show_error_message("User impersonation is not enabled in this instance of Galaxy.")
        user = None
        user_id = kwd.get('id', None)
        if user_id is not None:
            try:
                user = trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(user_id))
                if user:
                    trans.handle_user_logout()
                    trans.handle_user_login(user)
                    return trans.show_message('You are now logged in as %s, <a target="_top" href="%s">return to the home page</a>' % (user.email, url_for(controller='root')), use_panels=True)
            except Exception:
                log.exception("Error fetching user for impersonation")
        return trans.response.send_redirect(web.url_for(controller='admin',
                                                        action='users',
                                                        message="Invalid user selected", status="error"))

    def check_for_tool_dependencies(self, trans, migration_stage):
        # Get the 000x_tools.xml file associated with migration_stage.
        tools_xml_file_path = os.path.abspath(os.path.join(trans.app.config.root, 'scripts', 'migrate_tools', '%04d_tools.xml' % migration_stage))
        tree = util.parse_xml(tools_xml_file_path)
        root = tree.getroot()
        tool_shed = root.get('name')
        shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(trans.app, tool_shed)
        repo_name_dependency_tups = []
        if shed_url:
            for elem in root:
                if elem.tag == 'repository':
                    tool_dependencies = []
                    tool_dependencies_dict = {}
                    repository_name = elem.get('name')
                    changeset_revision = elem.get('changeset_revision')
                    params = dict(name=repository_name, owner='devteam', changeset_revision=changeset_revision)
                    pathspec = ['repository', 'get_tool_dependencies']
                    text = url_get(shed_url, password_mgr=self.app.tool_shed_registry.url_auth(shed_url), pathspec=pathspec, params=params)
                    if text:
                        tool_dependencies_dict = encoding_util.tool_shed_decode(text)
                        for dependency_key, requirements_dict in tool_dependencies_dict.items():
                            tool_dependency_name = requirements_dict['name']
                            tool_dependency_version = requirements_dict['version']
                            tool_dependency_type = requirements_dict['type']
                            tool_dependency_readme = requirements_dict.get('readme', '')
                            tool_dependencies.append((tool_dependency_name, tool_dependency_version, tool_dependency_type, tool_dependency_readme))
                    repo_name_dependency_tups.append((repository_name, tool_dependencies))
        return repo_name_dependency_tups

    @web.expose
    @web.require_admin
    def review_tool_migration_stages(self, trans, **kwd):
        message = escape(util.restore_text(kwd.get('message', '')))
        status = util.restore_text(kwd.get('status', 'done'))
        migration_stages_dict = odict()
        migration_modules = []
        migration_scripts_dir = os.path.abspath(os.path.join(trans.app.config.root, 'lib', 'tool_shed', 'galaxy_install', 'migrate', 'versions'))
        migration_scripts_dir_contents = os.listdir(migration_scripts_dir)
        for item in migration_scripts_dir_contents:
            if os.path.isfile(os.path.join(migration_scripts_dir, item)) and item.endswith('.py'):
                module = item.replace('.py', '')
                migration_modules.append(module)
        if migration_modules:
            migration_modules.sort()
            # Remove the 0001_tools.py script since it is the seed.
            migration_modules = migration_modules[1:]
            # Reverse the list so viewing will be newest to oldest.
            migration_modules.reverse()
        for migration_module in migration_modules:
            migration_stage = int(migration_module.replace('_tools', ''))
            repo_name_dependency_tups = self.check_for_tool_dependencies(trans, migration_stage)
            open_file_obj, file_name, description = imp.find_module(migration_module, [migration_scripts_dir])
            imported_module = imp.load_module('upgrade', open_file_obj, file_name, description)
            migration_info = imported_module.__doc__
            open_file_obj.close()
            migration_stages_dict[migration_stage] = (migration_info, repo_name_dependency_tups)
        return trans.fill_template('admin/review_tool_migration_stages.mako',
                                   migration_stages_dict=migration_stages_dict,
                                   message=message,
                                   status=status)

    @web.expose
    @web.require_admin
    def center(self, trans, **kwd):
        message = escape(kwd.get('message', ''))
        status = kwd.get('status', 'done')
        is_repo_installed = trans.install_model.context.query(trans.install_model.ToolShedRepository).first() is not None
        installing_repository_ids = repository_util.get_ids_of_tool_shed_repositories_being_installed(trans.app, as_string=True)
        return trans.fill_template('/webapps/galaxy/admin/center.mako',
                                   is_repo_installed=is_repo_installed,
                                   installing_repository_ids=installing_repository_ids,
                                   message=message,
                                   status=status)

    @web.expose_api
    @web.require_admin
    def tool_versions_list(self, trans, **kwd):
        return self.tool_version_list_grid(trans, **kwd)

    @web.expose
    @web.json
    @web.require_admin
    def roles_list(self, trans, **kwargs):
        message = kwargs.get('message')
        status = kwargs.get('status')
        if 'operation' in kwargs:
            id = kwargs.get('id', None)
            if not id:
                message, status = ('Invalid role id (%s) received.' % str(id), 'error')
            ids = util.listify(id)
            operation = kwargs['operation'].lower().replace('+', ' ')
            if operation == 'delete':
                message, status = self._delete_role(trans, ids)
            elif operation == 'undelete':
                message, status = self._undelete_role(trans, ids)
            elif operation == 'purge':
                message, status = self._purge_role(trans, ids)
        if message and status:
            kwargs['message'] = util.sanitize_text(message)
            kwargs['status'] = status
        return self.role_list_grid(trans, **kwargs)

    @web.expose_api
    @web.require_admin
    def create_role(self, trans, payload=None, **kwd):
        if trans.request.method == 'GET':
            all_users = []
            all_groups = []
            for user in trans.sa_session.query(trans.app.model.User) \
                                        .filter(trans.app.model.User.table.c.deleted == false()) \
                                        .order_by(trans.app.model.User.table.c.email):
                all_users.append((user.email, trans.security.encode_id(user.id)))
            for group in trans.sa_session.query(trans.app.model.Group) \
                                         .filter(trans.app.model.Group.table.c.deleted == false()) \
                                         .order_by(trans.app.model.Group.table.c.name):
                all_groups.append((group.name, trans.security.encode_id(group.id)))
            return {
                'title'  : 'Create Role',
                'inputs' : [{
                    'name'  : 'name',
                    'label' : 'Name'
                }, {
                    'name'  : 'description',
                    'label' : 'Description'
                },
                    build_select_input('in_groups', 'Groups', all_groups, []),
                    build_select_input('in_users', 'Users', all_users, []), {
                    'name'  : 'auto_create',
                    'label' : 'Create a new group of the same name for this role:',
                    'type'  : 'boolean'
                }]}
        else:
            name = util.restore_text(payload.get('name', ''))
            description = util.restore_text(payload.get('description', ''))
            auto_create_checked = payload.get('auto_create') == 'true'
            in_users = [trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(x)) for x in util.listify(payload.get('in_users'))]
            in_groups = [trans.sa_session.query(trans.app.model.Group).get(trans.security.decode_id(x)) for x in util.listify(payload.get('in_groups'))]
            if not name or not description:
                return self.message_exception(trans, 'Enter a valid name and a description.')
            elif trans.sa_session.query(trans.app.model.Role).filter(trans.app.model.Role.table.c.name == name).first():
                return self.message_exception(trans, 'Role names must be unique and a role with that name already exists, so choose another name.')
            elif None in in_users or None in in_groups:
                return self.message_exception(trans, 'One or more invalid user/group id has been provided.')
            else:
                # Create the role
                role = trans.app.model.Role(name=name, description=description, type=trans.app.model.Role.types.ADMIN)
                trans.sa_session.add(role)
                # Create the UserRoleAssociations
                for user in in_users:
                    ura = trans.app.model.UserRoleAssociation(user, role)
                    trans.sa_session.add(ura)
                # Create the GroupRoleAssociations
                for group in in_groups:
                    gra = trans.app.model.GroupRoleAssociation(group, role)
                    trans.sa_session.add(gra)
                if auto_create_checked:
                    # Check if role with same name already exists
                    if trans.sa_session.query(trans.app.model.Group).filter(trans.app.model.Group.table.c.name == name).first():
                        return self.message_exception(trans, 'A group with that name already exists, so choose another name or disable group creation.')
                    # Create the group
                    group = trans.app.model.Group(name=name)
                    trans.sa_session.add(group)
                    # Associate the group with the role
                    gra = trans.model.GroupRoleAssociation(group, role)
                    trans.sa_session.add(gra)
                    num_in_groups = len(in_groups) + 1
                else:
                    num_in_groups = len(in_groups)
                trans.sa_session.flush()
                message = 'Role \'%s\' has been created with %d associated users and %d associated groups.' % (role.name, len(in_users), num_in_groups)
                if auto_create_checked:
                    message += 'One of the groups associated with this role is the newly created group with the same name.'
                return {'message' : message}

    @web.expose_api
    @web.require_admin
    def rename_role(self, trans, payload=None, **kwd):
        id = kwd.get('id')
        if not id:
            return self.message_exception(trans, 'No role id received for renaming.')
        role = get_role(trans, id)
        if trans.request.method == 'GET':
            return {
                'title'  : 'Change role name and description for \'%s\'' % util.sanitize_text(role.name),
                'inputs' : [{
                    'name'  : 'name',
                    'label' : 'Name',
                    'value' : role.name
                }, {
                    'name'  : 'description',
                    'label' : 'Description',
                    'value' : role.description
                }]
            }
        else:
            old_name = role.name
            new_name = util.restore_text(payload.get('name'))
            new_description = util.restore_text(payload.get('description'))
            if not new_name:
                return self.message_exception(trans, 'Enter a valid role name.')
            else:
                existing_role = trans.sa_session.query(trans.app.model.Role).filter(trans.app.model.Role.table.c.name == new_name).first()
                if existing_role and existing_role.id != role.id:
                    return self.message_exception(trans, 'A role with that name already exists.')
                else:
                    if not (role.name == new_name and role.description == new_description):
                        role.name = new_name
                        role.description = new_description
                        trans.sa_session.add(role)
                        trans.sa_session.flush()
            return {'message': 'Role \'%s\' has been renamed to \'%s\'.' % (old_name, new_name)}

    @web.expose_api
    @web.require_admin
    def manage_users_and_groups_for_role(self, trans, payload=None, **kwd):
        role_id = kwd.get('id')
        if not role_id:
            return self.message_exception(trans, 'Invalid role id (%s) received' % str(role_id))
        role = get_role(trans, role_id)
        if trans.request.method == 'GET':
            in_users = []
            all_users = []
            in_groups = []
            all_groups = []
            for user in trans.sa_session.query(trans.app.model.User) \
                                        .filter(trans.app.model.User.table.c.deleted == false()) \
                                        .order_by(trans.app.model.User.table.c.email):
                if user in [x.user for x in role.users]:
                    in_users.append(trans.security.encode_id(user.id))
                all_users.append((user.email, trans.security.encode_id(user.id)))
            for group in trans.sa_session.query(trans.app.model.Group) \
                                         .filter(trans.app.model.Group.table.c.deleted == false()) \
                                         .order_by(trans.app.model.Group.table.c.name):
                if group in [x.group for x in role.groups]:
                    in_groups.append(trans.security.encode_id(group.id))
                all_groups.append((group.name, trans.security.encode_id(group.id)))
            return {'title'  : 'Role \'%s\'' % role.name,
                    'message': 'Role \'%s\' is currently associated with %d user(s) and %d group(s).' %
                    (role.name, len(in_users), len(in_groups)),
                    'status' : 'info',
                    'inputs' : [build_select_input('in_groups', 'Groups', all_groups, in_groups),
                                build_select_input('in_users', 'Users', all_users, in_users)]}
        else:
            in_users = [trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(x)) for x in util.listify(payload.get('in_users'))]
            in_groups = [trans.sa_session.query(trans.app.model.Group).get(trans.security.decode_id(x)) for x in util.listify(payload.get('in_groups'))]
            if None in in_users or None in in_groups:
                return self.message_exception(trans, 'One or more invalid user/group id has been provided.')
            for ura in role.users:
                user = trans.sa_session.query(trans.app.model.User).get(ura.user_id)
                if user not in in_users:
                    # Delete DefaultUserPermissions for previously associated users that have been removed from the role
                    for dup in user.default_permissions:
                        if role == dup.role:
                            trans.sa_session.delete(dup)
                    # Delete DefaultHistoryPermissions for previously associated users that have been removed from the role
                    for history in user.histories:
                        for dhp in history.default_permissions:
                            if role == dhp.role:
                                trans.sa_session.delete(dhp)
                    trans.sa_session.flush()
            trans.app.security_agent.set_entity_role_associations(roles=[role], users=in_users, groups=in_groups)
            trans.sa_session.refresh(role)
            return {'message' : 'Role \'%s\' has been updated with %d associated users and %d associated groups.' % (role.name, len(in_users), len(in_groups))}

    def _delete_role(self, trans, ids):
        message = 'Deleted %d roles: ' % len(ids)
        for role_id in ids:
            role = get_role(trans, role_id)
            role.deleted = True
            trans.sa_session.add(role)
            trans.sa_session.flush()
            message += ' %s ' % role.name
        return (message, 'done')

    def _undelete_role(self, trans, ids):
        count = 0
        undeleted_roles = ""
        for role_id in ids:
            role = get_role(trans, role_id)
            if not role.deleted:
                return ("Role '%s' has not been deleted, so it cannot be undeleted." % role.name, "error")
            role.deleted = False
            trans.sa_session.add(role)
            trans.sa_session.flush()
            count += 1
            undeleted_roles += " %s" % role.name
        return ("Undeleted %d roles: %s" % (count, undeleted_roles), "done")

    def _purge_role(self, trans, ids):
        # This method should only be called for a Role that has previously been deleted.
        # Purging a deleted Role deletes all of the following from the database:
        # - UserRoleAssociations where role_id == Role.id
        # - DefaultUserPermissions where role_id == Role.id
        # - DefaultHistoryPermissions where role_id == Role.id
        # - GroupRoleAssociations where role_id == Role.id
        # - DatasetPermissionss where role_id == Role.id
        message = "Purged %d roles: " % len(ids)
        for role_id in ids:
            role = get_role(trans, role_id)
            if not role.deleted:
                return ("Role '%s' has not been deleted, so it cannot be purged." % role.name, "error")
            # Delete UserRoleAssociations
            for ura in role.users:
                user = trans.sa_session.query(trans.app.model.User).get(ura.user_id)
                # Delete DefaultUserPermissions for associated users
                for dup in user.default_permissions:
                    if role == dup.role:
                        trans.sa_session.delete(dup)
                # Delete DefaultHistoryPermissions for associated users
                for history in user.histories:
                    for dhp in history.default_permissions:
                        if role == dhp.role:
                            trans.sa_session.delete(dhp)
                trans.sa_session.delete(ura)
            # Delete GroupRoleAssociations
            for gra in role.groups:
                trans.sa_session.delete(gra)
            # Delete DatasetPermissionss
            for dp in role.dataset_actions:
                trans.sa_session.delete(dp)
            trans.sa_session.flush()
            message += " %s " % role.name
        return (message, "done")

    @web.expose_api
    @web.require_admin
    def groups_list(self, trans, **kwargs):
        message = kwargs.get('message')
        status = kwargs.get('status')
        if 'operation' in kwargs:
            id = kwargs.get('id')
            if not id:
                return self.message_exception(trans, 'Invalid group id (%s) received.' % str(id))
            ids = util.listify(id)
            operation = kwargs['operation'].lower().replace('+', ' ')
            if operation == 'delete':
                message, status = self._delete_group(trans, ids)
            elif operation == 'undelete':
                message, status = self._undelete_group(trans, ids)
            elif operation == 'purge':
                message, status = self._purge_group(trans, ids)
        if message and status:
            kwargs['message'] = util.sanitize_text(message)
            kwargs['status'] = status
        return self.group_list_grid(trans, **kwargs)

    @web.expose_api
    @web.require_admin
    def rename_group(self, trans, payload=None, **kwd):
        id = kwd.get('id')
        if not id:
            return self.message_exception(trans, 'No group id received for renaming.')
        group = get_group(trans, id)
        if trans.request.method == 'GET':
            return {
                'title'  : 'Change group name for \'%s\'' % util.sanitize_text(group.name),
                'inputs' : [{
                    'name'  : 'name',
                    'label' : 'Name',
                    'value' : group.name
                }]
            }
        else:
            old_name = group.name
            new_name = util.restore_text(payload.get('name'))
            if not new_name:
                return self.message_exception(trans, 'Enter a valid group name.')
            else:
                existing_group = trans.sa_session.query(trans.app.model.Group).filter(trans.app.model.Group.table.c.name == new_name).first()
                if existing_group and existing_group.id != group.id:
                    return self.message_exception(trans, 'A group with that name already exists.')
                else:
                    if not (group.name == new_name):
                        group.name = new_name
                        trans.sa_session.add(group)
                        trans.sa_session.flush()
            return {'message': 'Group \'%s\' has been renamed to \'%s\'.' % (old_name, new_name)}

    @web.expose_api
    @web.require_admin
    def manage_users_and_roles_for_group(self, trans, payload=None, **kwd):
        group_id = kwd.get('id')
        if not group_id:
            return self.message_exception(trans, 'Invalid group id (%s) received' % str(group_id))
        group = get_group(trans, group_id)
        if trans.request.method == 'GET':
            in_users = []
            all_users = []
            in_roles = []
            all_roles = []
            for user in trans.sa_session.query(trans.app.model.User) \
                                        .filter(trans.app.model.User.table.c.deleted == false()) \
                                        .order_by(trans.app.model.User.table.c.email):
                if user in [x.user for x in group.users]:
                    in_users.append(trans.security.encode_id(user.id))
                all_users.append((user.email, trans.security.encode_id(user.id)))
            for role in trans.sa_session.query(trans.app.model.Role) \
                                        .filter(trans.app.model.Role.table.c.deleted == false()) \
                                        .order_by(trans.app.model.Role.table.c.name):
                if role in [x.role for x in group.roles]:
                    in_roles.append(trans.security.encode_id(role.id))
                all_roles.append((role.name, trans.security.encode_id(role.id)))
            return {'title'  : 'Group \'%s\'' % group.name,
                    'message': 'Group \'%s\' is currently associated with %d user(s) and %d role(s).' %
                    (group.name, len(in_users), len(in_roles)),
                    'status' : 'info',
                    'inputs' : [build_select_input('in_roles', 'Roles', all_roles, in_roles),
                                build_select_input('in_users', 'Users', all_users, in_users)]}
        else:
            in_users = [trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(x)) for x in util.listify(payload.get('in_users'))]
            in_roles = [trans.sa_session.query(trans.app.model.Role).get(trans.security.decode_id(x)) for x in util.listify(payload.get('in_roles'))]
            if None in in_users or None in in_roles:
                return self.message_exception(trans, 'One or more invalid user/role id has been provided.')
            trans.app.security_agent.set_entity_group_associations(groups=[group], users=in_users, roles=in_roles)
            trans.sa_session.refresh(group)
            return {'message' : 'Group \'%s\' has been updated with %d associated users and %d associated roles.' % (group.name, len(in_users), len(in_roles))}

    @web.expose_api
    @web.require_admin
    def create_group(self, trans, payload=None, **kwd):
        if trans.request.method == 'GET':
            all_users = []
            all_roles = []
            for user in trans.sa_session.query(trans.app.model.User) \
                                        .filter(trans.app.model.User.table.c.deleted == false()) \
                                        .order_by(trans.app.model.User.table.c.email):
                all_users.append((user.email, trans.security.encode_id(user.id)))
            for role in trans.sa_session.query(trans.app.model.Role) \
                                        .filter(trans.app.model.Role.table.c.deleted == false()) \
                                        .order_by(trans.app.model.Role.table.c.name):
                all_roles.append((role.name, trans.security.encode_id(role.id)))
            return {
                'title'    : 'Create Group',
                'title_id' : 'create-group',
                'inputs' : [{
                    'name'  : 'name',
                    'label' : 'Name'
                },
                    build_select_input('in_roles', 'Roles', all_roles, []),
                    build_select_input('in_users', 'Users', all_users, []), {
                    'name'  : 'auto_create',
                    'label' : 'Create a new role of the same name for this group:',
                    'type'  : 'boolean'
                }]
            }
        else:
            name = util.restore_text(payload.get('name', ''))
            auto_create_checked = payload.get('auto_create') == 'true'
            in_users = [trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(x)) for x in util.listify(payload.get('in_users'))]
            in_roles = [trans.sa_session.query(trans.app.model.Role).get(trans.security.decode_id(x)) for x in util.listify(payload.get('in_roles'))]
            if not name:
                return self.message_exception(trans, 'Enter a valid name.')
            elif trans.sa_session.query(trans.app.model.Group).filter(trans.app.model.Group.table.c.name == name).first():
                return self.message_exception(trans, 'Group names must be unique and a group with that name already exists, so choose another name.')
            elif None in in_users or None in in_roles:
                return self.message_exception(trans, 'One or more invalid user/role id has been provided.')
            else:
                # Create the role
                group = trans.app.model.Group(name=name)
                trans.sa_session.add(group)
                # Create the UserRoleAssociations
                for user in in_users:
                    uga = trans.app.model.UserGroupAssociation(user, group)
                    trans.sa_session.add(uga)
                # Create the GroupRoleAssociations
                for role in in_roles:
                    gra = trans.app.model.GroupRoleAssociation(group, role)
                    trans.sa_session.add(gra)
                if auto_create_checked:
                    # Check if role with same name already exists
                    if trans.sa_session.query(trans.app.model.Role).filter(trans.app.model.Role.table.c.name == name).first():
                        return self.message_exception(trans, 'A role with that name already exists, so choose another name or disable role creation.')
                    # Create the role
                    role = trans.app.model.Role(name=name, description='Role for group %s' % name)
                    trans.sa_session.add(role)
                    # Associate the group with the role
                    gra = trans.model.GroupRoleAssociation(group, role)
                    trans.sa_session.add(gra)
                    num_in_roles = len(in_roles) + 1
                else:
                    num_in_roles = len(in_roles)
                trans.sa_session.flush()
                message = 'Group \'%s\' has been created with %d associated users and %d associated roles.' % (group.name, len(in_users), num_in_roles)
                if auto_create_checked:
                    message += 'One of the roles associated with this group is the newly created role with the same name.'
                return {'message' : message}

    def _delete_group(self, trans, ids):
        message = 'Deleted %d groups: ' % len(ids)
        for group_id in ids:
            group = get_group(trans, group_id)
            group.deleted = True
            trans.sa_session.add(group)
            trans.sa_session.flush()
            message += ' %s ' % group.name
        return (message, 'done')

    def _undelete_group(self, trans, ids):
        count = 0
        undeleted_groups = ""
        for group_id in ids:
            group = get_group(trans, group_id)
            if not group.deleted:
                return ("Group '%s' has not been deleted, so it cannot be undeleted." % group.name, "error")
            group.deleted = False
            trans.sa_session.add(group)
            trans.sa_session.flush()
            count += 1
            undeleted_groups += " %s" % group.name
        return ("Undeleted %d groups: %s" % (count, undeleted_groups), "done")

    def _purge_group(self, trans, ids):
        message = "Purged %d groups: " % len(ids)
        for group_id in ids:
            group = get_group(trans, group_id)
            if not group.deleted:
                return ("Group '%s' has not been deleted, so it cannot be purged." % group.name, "error")
            # Delete UserGroupAssociations
            for uga in group.users:
                trans.sa_session.delete(uga)
            # Delete GroupRoleAssociations
            for gra in group.roles:
                trans.sa_session.delete(gra)
            trans.sa_session.flush()
            message += " %s " % group.name
        return (message, "done")

    @web.expose
    @web.require_admin
    def create_new_user(self, trans, **kwd):
        return trans.response.send_redirect(web.url_for(controller='user',
                                                        action='create',
                                                        cntrller='admin'))

    @web.expose_api
    @web.require_admin
    def reset_user_password(self, trans, payload=None, **kwd):
        users = {user_id: get_user(trans, user_id) for user_id in util.listify(kwd.get('id'))}
        if users:
            if trans.request.method == 'GET':
                return {
                    'message': 'Changes password(s) for: %s.' % ', '.join(user.email for user in users.values()),
                    'status' : 'info',
                    'inputs' : [{'name' : 'password', 'label' : 'New password', 'type' : 'password'},
                                {'name' : 'confirm', 'label' : 'Confirm password', 'type' : 'password'}]
                }
            else:
                password = payload.get('password')
                confirm = payload.get('confirm')
                if len(password) < 6:
                    return self.message_exception(trans, 'Use a password of at least 6 characters.')
                elif password != confirm:
                    return self.message_exception(trans, 'Passwords do not match.')
                for user in users.values():
                    user.set_password_cleartext(password)
                    trans.sa_session.add(user)
                    trans.sa_session.flush()
                return {'message': 'Passwords reset for %d user(s).' % len(users)}
        else:
            return self.message_exception(trans, 'Please specify user ids.')

    def _delete_user(self, trans, ids):
        message = 'Deleted %d users: ' % len(ids)
        for user_id in ids:
            user = get_user(trans, user_id)
            user.deleted = True

            compliance_log.info('delete-user-event: %s' % user_id)

            # Maybe there is some case in the future where an admin needs
            # to prove that a user was using a server for some reason (e.g.
            # a court case.) So we make this painfully hard to recover (and
            # not immediately reversable) in line with GDPR, but still
            # leave open the possibility to prove someone was part of the
            # server just in case. By knowing the exact email + approximate
            # time of deletion, one could run through hashes for every
            # second of the surrounding days/weeks.
            pseudorandom_value = str(int(time.time()))
            # Replace email + username with a (theoretically) unreversable
            # hash. If provided with the username we can probably re-hash
            # to identify if it is needed for some reason.
            #
            # Deleting multiple times will re-hash the username/email
            email_hash = new_secure_hash(user.email + pseudorandom_value)
            uname_hash = new_secure_hash(user.username + pseudorandom_value)

            # We must also redact username
            for role in user.all_roles():
                if self.app.config.redact_username_during_deletion:
                    role.name = role.name.replace(user.username, uname_hash)
                    role.description = role.description.replace(user.username, uname_hash)

                if self.app.config.redact_email_during_deletion:
                    role.name = role.name.replace(user.email, email_hash)
                    role.description = role.description.replace(user.email, email_hash)

            if self.app.config.redact_email_during_deletion:
                user.email = email_hash
            if self.app.config.redact_username_during_deletion:
                user.username = uname_hash

            # Redact user addresses as well
            if self.app.config.redact_user_address_during_deletion:
                user_addresses = trans.sa_session.query(trans.app.model.UserAddress) \
                    .filter(trans.app.model.UserAddress.user_id == user.id).all()

                for addr in user_addresses:
                    addr.desc = new_secure_hash(addr.desc + pseudorandom_value)
                    addr.name = new_secure_hash(addr.name + pseudorandom_value)
                    addr.institution = new_secure_hash(addr.institution + pseudorandom_value)
                    addr.address = new_secure_hash(addr.address + pseudorandom_value)
                    addr.city = new_secure_hash(addr.city + pseudorandom_value)
                    addr.state = new_secure_hash(addr.state + pseudorandom_value)
                    addr.postal_code = new_secure_hash(addr.postal_code + pseudorandom_value)
                    addr.country = new_secure_hash(addr.country + pseudorandom_value)
                    addr.phone = new_secure_hash(addr.phone + pseudorandom_value)
                    trans.sa_session.add(addr)

            trans.sa_session.add(user)
            trans.sa_session.flush()
            message += ' %s ' % user.email
        return (message, 'done')

    def _undelete_user(self, trans, ids):
        count = 0
        undeleted_users = ""
        for user_id in ids:
            user = get_user(trans, user_id)
            if not user.deleted:
                message = 'User \'%s\' has not been deleted, so it cannot be undeleted.' % user.email
                return (message, 'error')
            user.deleted = False
            trans.sa_session.add(user)
            trans.sa_session.flush()
            count += 1
            undeleted_users += ' %s' % user.email
        message = 'Undeleted %d users: %s' % (count, undeleted_users)
        return (message, 'done')

    def _purge_user(self, trans, ids):
        # This method should only be called for a User that has previously been deleted.
        # We keep the User in the database ( marked as purged ), and stuff associated
        # with the user's private role in case we want the ability to unpurge the user
        # some time in the future.
        # Purging a deleted User deletes all of the following:
        # - History where user_id = User.id
        #    - HistoryDatasetAssociation where history_id = History.id
        # - UserGroupAssociation where user_id == User.id
        # - UserRoleAssociation where user_id == User.id EXCEPT FOR THE PRIVATE ROLE
        # - UserAddress where user_id == User.id
        # Purging Histories and Datasets must be handled via the cleanup_datasets.py script
        message = 'Purged %d users: ' % len(ids)
        for user_id in ids:
            user = get_user(trans, user_id)
            if not user.deleted:
                return ('User \'%s\' has not been deleted, so it cannot be purged.' % user.email, 'error')
            private_role = trans.app.security_agent.get_private_user_role(user)
            # Delete History
            for h in user.active_histories:
                trans.sa_session.refresh(h)
                for hda in h.active_datasets:
                    # Delete HistoryDatasetAssociation
                    hda.deleted = True
                    trans.sa_session.add(hda)
                h.deleted = True
                trans.sa_session.add(h)
            # Delete UserGroupAssociations
            for uga in user.groups:
                trans.sa_session.delete(uga)
            # Delete UserRoleAssociations EXCEPT FOR THE PRIVATE ROLE
            for ura in user.roles:
                if ura.role_id != private_role.id:
                    trans.sa_session.delete(ura)
            # Delete UserAddresses
            for address in user.addresses:
                trans.sa_session.delete(address)
            # Purge the user
            user.purged = True
            trans.sa_session.add(user)
            trans.sa_session.flush()
            message += '%s ' % user.email
        return (message, 'done')

    def _recalculate_user(self, trans, user_id):
        user = trans.sa_session.query(trans.model.User).get(trans.security.decode_id(user_id))
        if not user:
            return ('User not found for id (%s)' % sanitize_text(str(user_id)), 'error')
        current = user.get_disk_usage()
        user.calculate_and_set_disk_usage()
        new = user.get_disk_usage()
        if new in (current, None):
            message = 'Usage is unchanged at %s.' % nice_size(current)
        else:
            message = 'Usage has changed by %s to %s.' % (nice_size(new - current), nice_size(new))
        return (message, 'done')

    def _new_user_apikey(self, trans, user_id):
        user = trans.sa_session.query(trans.model.User).get(trans.security.decode_id(user_id))
        if not user:
            return ('User not found for id (%s)' % sanitize_text(str(user_id)), 'error')
        new_key = trans.app.model.APIKeys(
            user_id=trans.security.decode_id(user_id),
            key=trans.app.security.get_new_guid()
        )
        trans.sa_session.add(new_key)
        trans.sa_session.flush()
        return ("New key '%s' generated for requested user '%s'." % (new_key.key, user.email), "done")

    @web.expose_api
    @web.require_admin
    def manage_roles_and_groups_for_user(self, trans, payload=None, **kwd):
        user_id = kwd.get('id')
        if not user_id:
            return self.message_exception(trans, 'Invalid user id (%s) received' % str(user_id))
        user = get_user(trans, user_id)
        if trans.request.method == 'GET':
            in_roles = []
            all_roles = []
            in_groups = []
            all_groups = []
            for role in trans.sa_session.query(trans.app.model.Role).filter(trans.app.model.Role.table.c.deleted == false()) \
                    .order_by(trans.app.model.Role.table.c.name):
                if role in [x.role for x in user.roles]:
                    in_roles.append(trans.security.encode_id(role.id))
                if role.type != trans.app.model.Role.types.PRIVATE:
                    # There is a 1 to 1 mapping between a user and a PRIVATE role, so private roles should
                    # not be listed in the roles form fields, except for the currently selected user's private
                    # role, which should always be in in_roles.  The check above is added as an additional
                    # precaution, since for a period of time we were including private roles in the form fields.
                    all_roles.append((role.name, trans.security.encode_id(role.id)))
            for group in trans.sa_session.query(trans.app.model.Group).filter(trans.app.model.Group.table.c.deleted == false()) \
                    .order_by(trans.app.model.Group.table.c.name):
                if group in [x.group for x in user.groups]:
                    in_groups.append(trans.security.encode_id(group.id))
                all_groups.append((group.name, trans.security.encode_id(group.id)))
            return {'title'  : 'Roles and groups for \'%s\'' % user.email,
                    'message': 'User \'%s\' is currently associated with %d role(s) and is a member of %d group(s).' %
                    (user.email, len(in_roles) - 1, len(in_groups)),
                    'status' : 'info',
                    'inputs' : [build_select_input('in_roles', 'Roles', all_roles, in_roles),
                                build_select_input('in_groups', 'Groups', all_groups, in_groups)]}
        else:
            in_roles = [trans.sa_session.query(trans.app.model.Role).get(trans.security.decode_id(x)) for x in util.listify(payload.get('in_roles'))]
            in_groups = [trans.sa_session.query(trans.app.model.Group).get(trans.security.decode_id(x)) for x in util.listify(payload.get('in_groups'))]
            if None in in_groups or None in in_roles:
                return self.message_exception(trans, 'One or more invalid role/group id has been provided.')

            # make sure the user is not dis-associating himself from his private role
            private_role = trans.app.security_agent.get_private_user_role(user)
            if private_role not in in_roles:
                in_roles.append(private_role)

            trans.app.security_agent.set_entity_user_associations(users=[user], roles=in_roles, groups=in_groups)
            trans.sa_session.refresh(user)
            return {'message' : 'User \'%s\' has been updated with %d associated roles and %d associated groups (private roles are not displayed).' % (user.email, len(in_roles) - 1, len(in_groups))}

    @web.expose
    @web.require_admin
    def jobs(self, trans, stop=[], stop_msg=None, cutoff=180, job_lock=None, ajl_submit=None, **kwd):
        deleted = []
        msg = None
        status = None
        job_ids = util.listify(stop)
        if job_ids and stop_msg in [None, '']:
            msg = 'Please enter an error message to display to the user describing why the job was terminated'
            status = 'error'
        elif job_ids:
            if stop_msg[-1] not in PUNCTUATION:
                stop_msg += '.'
            for job_id in job_ids:
                error_msg = "This job was stopped by an administrator: %s  <a href='%s' target='_blank'>Contact support</a> for additional help." \
                    % (stop_msg, self.app.config.get("support_url", "https://galaxyproject.org/support/"))
                if trans.app.config.track_jobs_in_database:
                    job = trans.sa_session.query(trans.app.model.Job).get(job_id)
                    job.stderr = error_msg
                    job.set_state(trans.app.model.Job.states.DELETED_NEW)
                    trans.sa_session.add(job)
                else:
                    trans.app.job_manager.stop(job, message=error_msg)
                deleted.append(str(job_id))
        if deleted:
            msg = 'Queued job'
            if len(deleted) > 1:
                msg += 's'
            msg += ' for deletion: '
            msg += ', '.join(deleted)
            status = 'done'
            trans.sa_session.flush()
        if ajl_submit:
            if job_lock == 'on':
                galaxy.queue_worker.send_control_task(trans.app, 'admin_job_lock',
                                                      kwargs={'job_lock': True})
                job_lock = True
            else:
                galaxy.queue_worker.send_control_task(trans.app, 'admin_job_lock',
                                                      kwargs={'job_lock': False})
                job_lock = False
        else:
            job_lock = trans.app.job_manager.job_lock
        cutoff_time = datetime.utcnow() - timedelta(seconds=int(cutoff))
        jobs = trans.sa_session.query(trans.app.model.Job) \
                               .filter(and_(trans.app.model.Job.table.c.update_time < cutoff_time,
                                            or_(trans.app.model.Job.state == trans.app.model.Job.states.NEW,
                                                trans.app.model.Job.state == trans.app.model.Job.states.QUEUED,
                                                trans.app.model.Job.state == trans.app.model.Job.states.RUNNING,
                                                trans.app.model.Job.state == trans.app.model.Job.states.UPLOAD))) \
                               .order_by(trans.app.model.Job.table.c.update_time.desc()).all()
        recent_jobs = trans.sa_session.query(trans.app.model.Job) \
            .filter(and_(trans.app.model.Job.table.c.update_time > cutoff_time,
                         or_(trans.app.model.Job.state == trans.app.model.Job.states.ERROR,
                             trans.app.model.Job.state == trans.app.model.Job.states.OK))) \
            .order_by(trans.app.model.Job.table.c.update_time.desc()).all()
        last_updated = {}
        for job in jobs:
            delta = datetime.utcnow() - job.update_time
            if delta.days > 0:
                last_updated[job.id] = '%s hours' % (delta.days * 24 + int(delta.seconds / 60 / 60))
            elif delta > timedelta(minutes=59):
                last_updated[job.id] = '%s hours' % int(delta.seconds / 60 / 60)
            else:
                last_updated[job.id] = '%s minutes' % int(delta.seconds / 60)
        finished = {}
        for job in recent_jobs:
            delta = datetime.utcnow() - job.update_time
            if delta.days > 0:
                finished[job.id] = '%s hours' % (delta.days * 24 + int(delta.seconds / 60 / 60))
            elif delta > timedelta(minutes=59):
                finished[job.id] = '%s hours' % int(delta.seconds / 60 / 60)
            else:
                finished[job.id] = '%s minutes' % int(delta.seconds / 60)
        return trans.fill_template('/admin/jobs.mako',
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
    def job_info(self, trans, jobid=None):
        job = None
        if jobid is not None:
            job = trans.sa_session.query(trans.app.model.Job).get(jobid)
        return trans.fill_template('/webapps/reports/job_info.mako',
                                   job=job,
                                   message="<a href='jobs'>Back</a>")

    @web.expose
    @web.require_admin
    def manage_tool_dependencies(self,
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
        return trans.fill_template('/webapps/galaxy/admin/manage_dependencies.mako',
                                   tools=tools_by_id,
                                   requirements_status=view.toolbox_requirements_status,
                                   tool_ids_by_requirements=view.tool_ids_by_requirements,
                                   unused_environments=view.unused_dependency_paths,
                                   viewkey=viewkey)

    @web.expose
    @web.require_admin
    def sanitize_whitelist(self, trans, submit_whitelist=False, tools_to_whitelist=[]):
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
        return trans.fill_template('/webapps/galaxy/admin/sanitize_whitelist.mako',
                                   sanitize_all=trans.app.config.sanitize_all_html,
                                   tools=trans.app.toolbox.tools_by_id)


# ---- Utility methods -------------------------------------------------------

def build_select_input(name, label, options, value):
    return {'type'      : 'select',
            'multiple'  : True,
            'optional'  : True,
            'individual': True,
            'name'      : name,
            'label'     : label,
            'options'   : options,
            'value'     : value}


def get_user(trans, user_id):
    """Get a User from the database by id."""
    user = trans.sa_session.query(trans.model.User).get(trans.security.decode_id(user_id))
    if not user:
        return trans.show_error_message("User not found for id (%s)" % str(user_id))
    return user


def get_role(trans, id):
    """Get a Role from the database by id."""
    # Load user from database
    id = trans.security.decode_id(id)
    role = trans.sa_session.query(trans.model.Role).get(id)
    if not role:
        return trans.show_error_message("Role not found for id (%s)" % str(id))
    return role


def get_group(trans, id):
    """Get a Group from the database by id."""
    # Load user from database
    id = trans.security.decode_id(id)
    group = trans.sa_session.query(trans.model.Group).get(id)
    if not group:
        return trans.show_error_message("Group not found for id (%s)" % str(id))
    return group


def get_quota(trans, id):
    """Get a Quota from the database by id."""
    # Load user from database
    id = trans.security.decode_id(id)
    quota = trans.sa_session.query(trans.model.Quota).get(id)
    return quota
