import logging

from markupsafe import escape
from sqlalchemy import and_

from galaxy.web.framework.helpers import time_ago
from galaxy.web.legacy_framework import grids
from tool_shed.grids.repository_grids import (
    CategoryGrid,
    RepositoryGrid,
)
from tool_shed.util import hg_util
from tool_shed.webapp import model

log = logging.getLogger(__name__)


class UserGrid(grids.Grid):
    class UserLoginColumn(grids.TextColumn):
        def get_value(self, trans, grid, user):
            return escape(user.email)

    class UserNameColumn(grids.TextColumn):
        def get_value(self, trans, grid, user):
            if user.username:
                return escape(user.username)
            return "not set"

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
                return "yes"
            return "no"

    class LastLoginColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            if user.current_galaxy_session:
                return self.format(user.current_galaxy_session.update_time)
            return "never"

    class StatusColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            if user.purged:
                return "purged"
            elif user.deleted:
                return "deleted"
            return ""

    class EmailColumn(grids.GridColumn):
        def filter(self, trans, user, query, column_filter):
            if column_filter == "All":
                return query
            return query.filter(
                and_(model.Tool.table.c.user_id == model.User.table.c.id, model.User.table.c.email == column_filter)
            )

    title = "Users"
    model_class = model.User
    default_sort_key = "email"
    columns = [
        UserLoginColumn(
            "Email",
            key="email",
            link=(lambda item: dict(operation="information", id=item.id)),
            attach_popup=True,
            filterable="advanced",
        ),
        UserNameColumn("User Name", key="username", attach_popup=False, filterable="advanced"),
        GroupsColumn("Groups", attach_popup=False),
        RolesColumn("Roles", attach_popup=False),
        ExternalColumn("External", attach_popup=False),
        LastLoginColumn("Last Login", format=time_ago),
        StatusColumn("Status", attach_popup=False),
        # Columns that are valid for filtering but are not visible.
        EmailColumn("Email", key="email", visible=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search",
            cols_to_filter=[columns[0], columns[1]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )
    global_actions = [grids.GridAction("Create new user", dict(controller="admin", action="users", operation="create"))]
    operations = [
        grids.GridOperation(
            "Manage Roles and Groups",
            condition=(lambda item: not item.deleted),
            allow_multiple=False,
            url_args=dict(action="manage_roles_and_groups_for_user"),
        ),
        grids.GridOperation(
            "Reset Password",
            condition=(lambda item: not item.deleted),
            allow_multiple=True,
            allow_popup=False,
            url_args=dict(action="reset_user_password"),
        ),
    ]
    standard_filters = [
        grids.GridColumnFilter("Active", args=dict(deleted=False)),
        grids.GridColumnFilter("Deleted", args=dict(deleted=True, purged=False)),
        grids.GridColumnFilter("Purged", args=dict(purged=True)),
        grids.GridColumnFilter("All", args=dict(deleted="All")),
    ]

    use_paging = False

    def get_current_item(self, trans, **kwargs):
        return trans.user


class RoleGrid(grids.Grid):
    class NameColumn(grids.TextColumn):
        def get_value(self, trans, grid, role):
            return escape(str(role.name))

    class DescriptionColumn(grids.TextColumn):
        def get_value(self, trans, grid, role):
            if role.description:
                return str(role.description)
            return ""

    class TypeColumn(grids.TextColumn):
        def get_value(self, trans, grid, role):
            return str(role.type)

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

    class RepositoriesColumn(grids.GridColumn):
        def get_value(self, trans, grid, role):
            if role.repositories:
                return len(role.repositories)
            return 0

    class UsersColumn(grids.GridColumn):
        def get_value(self, trans, grid, role):
            if role.users:
                return len(role.users)
            return 0

    title = "Roles"
    model_class = model.Role
    default_sort_key = "name"
    columns = [
        NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(operation="Manage role associations", id=item.id)),
            attach_popup=True,
            filterable="advanced",
        ),
        DescriptionColumn("Description", key="description", attach_popup=False, filterable="advanced"),
        GroupsColumn("Groups", attach_popup=False),
        RepositoriesColumn("Repositories", attach_popup=False),
        UsersColumn("Users", attach_popup=False),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn("Deleted", key="deleted", visible=False, filterable="advanced"),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search", cols_to_filter=[columns[0]], key="free-text-search", visible=False, filterable="standard"
        )
    )
    global_actions = [grids.GridAction("Add new role", dict(controller="admin", action="roles", operation="create"))]
    # Repository admin roles currently do not have any operations since they are managed automatically based
    # on other events.  For example, if a repository is renamed, its associated admin role is automatically
    # renamed accordingly and if a repository is deleted its associated admin role is automatically deleted.
    operations = [
        grids.GridOperation(
            "Rename",
            condition=(lambda item: not item.deleted and not item.is_repository_admin_role),
            allow_multiple=False,
            url_args=dict(action="rename_role"),
        ),
        grids.GridOperation(
            "Delete",
            condition=(lambda item: not item.deleted and not item.is_repository_admin_role),
            allow_multiple=True,
            url_args=dict(action="mark_role_deleted"),
        ),
        grids.GridOperation(
            "Undelete",
            condition=(lambda item: item.deleted and not item.is_repository_admin_role),
            allow_multiple=True,
            url_args=dict(action="undelete_role"),
        ),
        grids.GridOperation(
            "Purge",
            condition=(lambda item: item.deleted and not item.is_repository_admin_role),
            allow_multiple=True,
            url_args=dict(action="purge_role"),
        ),
    ]
    standard_filters = [
        grids.GridColumnFilter("Active", args=dict(deleted=False)),
        grids.GridColumnFilter("Deleted", args=dict(deleted=True)),
        grids.GridColumnFilter("All", args=dict(deleted="All")),
    ]

    use_paging = False

    def apply_query_filter(self, trans, query, **kwd):
        return query.filter(model.Role.type != model.Role.types.PRIVATE)


class GroupGrid(grids.Grid):
    class NameColumn(grids.TextColumn):
        def get_value(self, trans, grid, group):
            return str(group.name)

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
            if group.users:
                return len(group.users)
            return 0

    title = "Groups"
    model_class = model.Group
    default_sort_key = "name"
    columns = [
        NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(operation="Manage users and roles", id=item.id)),
            attach_popup=True,
        ),
        UsersColumn("Users", attach_popup=False),
        RolesColumn("Roles", attach_popup=False),
        StatusColumn("Status", attach_popup=False),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn("Deleted", key="deleted", visible=False, filterable="advanced"),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search", cols_to_filter=[columns[0]], key="free-text-search", visible=False, filterable="standard"
        )
    )
    global_actions = [grids.GridAction("Add new group", dict(controller="admin", action="groups", operation="create"))]
    operations = [
        grids.GridOperation(
            "Rename",
            condition=(lambda item: not item.deleted),
            allow_multiple=False,
            url_args=dict(action="rename_group"),
        ),
        grids.GridOperation(
            "Delete",
            condition=(lambda item: not item.deleted),
            allow_multiple=True,
            url_args=dict(action="mark_group_deleted"),
        ),
        grids.GridOperation(
            "Undelete",
            condition=(lambda item: item.deleted),
            allow_multiple=True,
            url_args=dict(action="undelete_group"),
        ),
        grids.GridOperation(
            "Purge", condition=(lambda item: item.deleted), allow_multiple=True, url_args=dict(action="purge_group")
        ),
    ]
    standard_filters = [
        grids.GridColumnFilter("Active", args=dict(deleted=False)),
        grids.GridColumnFilter("Deleted", args=dict(deleted=True)),
        grids.GridColumnFilter("All", args=dict(deleted="All")),
    ]

    use_paging = False


class ManageCategoryGrid(CategoryGrid):
    columns = list(CategoryGrid.columns)
    # Override the NameColumn to include an Edit link
    columns[0] = CategoryGrid.NameColumn(
        "Name",
        key="Category.name",
        link=(lambda item: dict(operation="Edit", id=item.id)),
        model_class=model.Category,
        attach_popup=False,
    )
    global_actions = [
        grids.GridAction("Add new category", dict(controller="admin", action="manage_categories", operation="create"))
    ]


class AdminRepositoryGrid(RepositoryGrid):
    class DeletedColumn(grids.BooleanColumn):
        def get_value(self, trans, grid, repository):
            if repository.deleted:
                return "yes"
            return ""

    columns = [
        RepositoryGrid.NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=True,
        ),
        RepositoryGrid.HeadsColumn("Heads"),
        RepositoryGrid.UserColumn(
            "Owner",
            model_class=model.User,
            link=(lambda item: dict(operation="repositories_by_user", id=item.id)),
            attach_popup=False,
            key="User.username",
        ),
        RepositoryGrid.DeprecatedColumn("Deprecated", key="deprecated", attach_popup=False),
        # Columns that are valid for filtering but are not visible.
        DeletedColumn("Deleted", key="deleted", attach_popup=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name",
            cols_to_filter=[columns[0]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )
    operations = list(RepositoryGrid.operations)
    operations.append(
        grids.GridOperation(
            "Delete", allow_multiple=False, condition=(lambda item: not item.deleted), async_compatible=False
        )
    )
    operations.append(
        grids.GridOperation(
            "Undelete", allow_multiple=False, condition=(lambda item: item.deleted), async_compatible=False
        )
    )

    def build_initial_query(self, trans, **kwd):
        return trans.sa_session.query(model.Repository).join(model.User.table)


class RepositoryMetadataGrid(grids.Grid):
    class IdColumn(grids.IntegerColumn):
        def get_value(self, trans, grid, repository_metadata):
            return repository_metadata.id

    class NameColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            return escape(repository_metadata.repository.name)

    class OwnerColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            return escape(repository_metadata.repository.user.username)

    class RevisionColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            repository = repository_metadata.repository
            return hg_util.get_revision_label(
                trans.app, repository, repository_metadata.changeset_revision, include_date=True, include_hash=True
            )

    class ToolsColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            tools_str = "0"
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if "tools" in metadata:
                        # We used to display the following, but grid was too cluttered.
                        # for tool_metadata_dict in metadata[ 'tools' ]:
                        #    tools_str += '%s <b>%s</b><br/>' % ( tool_metadata_dict[ 'id' ], tool_metadata_dict[ 'version' ] )
                        return "%d" % len(metadata["tools"])
            return tools_str

    class DatatypesColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            datatypes_str = "0"
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if "datatypes" in metadata:
                        # We used to display the following, but grid was too cluttered.
                        # for datatype_metadata_dict in metadata[ 'datatypes' ]:
                        #    datatypes_str += '%s<br/>' % datatype_metadata_dict[ 'extension' ]
                        return "%d" % len(metadata["datatypes"])
            return datatypes_str

    class WorkflowsColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            workflows_str = "0"
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if "workflows" in metadata:
                        # We used to display the following, but grid was too cluttered.
                        # workflows_str += '<b>Workflows:</b><br/>'
                        # metadata[ 'workflows' ] is a list of tuples where each contained tuple is
                        # [ <relative path to the .ga file in the repository>, <exported workflow dict> ]
                        # workflow_tups = metadata[ 'workflows' ]
                        # workflow_metadata_dicts = [ workflow_tup[1] for workflow_tup in workflow_tups ]
                        # for workflow_metadata_dict in workflow_metadata_dicts:
                        #    workflows_str += '%s<br/>' % workflow_metadata_dict[ 'name' ]
                        return "%d" % len(metadata["workflows"])
            return workflows_str

    class DeletedColumn(grids.BooleanColumn):
        def get_value(self, trans, grid, repository_metadata):
            if repository_metadata.repository.deleted:
                return "yes"
            return ""

    class DeprecatedColumn(grids.BooleanColumn):
        def get_value(self, trans, grid, repository_metadata):
            if repository_metadata.repository.deprecated:
                return "yes"
            return ""

    class MaliciousColumn(grids.BooleanColumn):
        def get_value(self, trans, grid, repository_metadata):
            if repository_metadata.malicious:
                return "yes"
            return ""

    # Grid definition
    title = "Repository Metadata"
    model_class = model.RepositoryMetadata
    default_sort_key = "name"
    use_hide_message = False
    columns = [
        IdColumn("Id", visible=False, attach_popup=False),
        NameColumn(
            "Name",
            key="name",
            model_class=model.Repository,
            link=(lambda item: dict(operation="view_or_manage_repository_revision", id=item.id)),
            attach_popup=True,
        ),
        OwnerColumn("Owner", attach_popup=False),
        RevisionColumn("Revision", attach_popup=False),
        ToolsColumn("Tools", attach_popup=False),
        DatatypesColumn("Datatypes", attach_popup=False),
        WorkflowsColumn("Workflows", attach_popup=False),
        DeletedColumn("Deleted", attach_popup=False),
        DeprecatedColumn("Deprecated", attach_popup=False),
        MaliciousColumn("Malicious", attach_popup=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name",
            cols_to_filter=[columns[1]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )
    operations = [
        grids.GridOperation(
            "Delete",
            allow_multiple=False,
            allow_popup=True,
            async_compatible=False,
            confirm="Repository metadata records cannot be recovered after they are deleted. Click OK to delete the selected items.",
        )
    ]

    def build_initial_query(self, trans, **kwd):
        return trans.sa_session.query(model.RepositoryMetadata).join(model.Repository.table)
