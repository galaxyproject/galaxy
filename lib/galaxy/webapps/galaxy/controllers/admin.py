import logging
from typing import Set

from sqlalchemy import (
    false,
    func,
    true,
)
from typing_extensions import TypedDict

from galaxy import (
    model,
    util,
    web,
)
from galaxy.exceptions import ActionInputError
from galaxy.managers.quotas import QuotaManager
from galaxy.model.base import transaction
from galaxy.model.index_filter_util import (
    raw_text_column_filter,
    text_column_filter,
)
from galaxy.security.validate_user_input import validate_password
from galaxy.structured_app import StructuredApp
from galaxy.util.search import (
    FilteredTerm,
    parse_filters_structured,
    RawTextTerm,
)
from galaxy.web import url_for
from galaxy.web.framework.helpers import (
    grids,
    time_ago,
)
from galaxy.webapps.base import controller

log = logging.getLogger(__name__)


class UserListGrid(grids.GridData):
    class StatusColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            if user.purged:
                return "Purged"
            elif user.deleted:
                return "Deleted"
            return "Available"

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

    class LastLoginColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            if user.galaxy_sessions:
                return self.format(user.current_galaxy_session.update_time)
            return "never"

        def sort(self, trans, query, ascending, column_name=None):
            last_login_subquery = (
                trans.sa_session.query(
                    model.GalaxySession.table.c.user_id,
                    func.max(model.GalaxySession.table.c.update_time).label("last_login"),
                )
                .group_by(model.GalaxySession.table.c.user_id)
                .subquery()
            )
            query = query.outerjoin((last_login_subquery, model.User.table.c.id == last_login_subquery.c.user_id))

            if not ascending:
                query = query.order_by((last_login_subquery.c.last_login).desc().nullslast())
            else:
                query = query.order_by((last_login_subquery.c.last_login).asc().nullsfirst())
            return query

    class DiskUsageColumn(grids.GridColumn):
        def get_value(self, trans, grid, user):
            return user.get_disk_usage(nice_size=True)

        def sort(self, trans, query, ascending, column_name=None):
            if column_name is None:
                column_name = self.key
            column = self.model_class.table.c.get(column_name)
            if column is None:
                column = getattr(self.model_class, column_name)
            if ascending:
                query = query.order_by(func.coalesce(column, 0).asc())
            else:
                query = query.order_by(func.coalesce(column, 0).desc())
            return query

    # Grid definition
    title = "Users"
    title_id = "users-grid"
    model_class = model.User
    default_sort_key = "email"
    columns = [
        grids.GridColumn("Email", key="email"),
        grids.GridColumn("User Name", key="username"),
        LastLoginColumn("Last Login", key="last_login", format=time_ago),
        DiskUsageColumn("Disk Usage", key="disk_usage"),
        StatusColumn("Status", key="status"),
        grids.GridColumn("Created", key="create_time"),
        grids.GridColumn("Activated", key="active", escape=False),
        GroupsColumn("Groups", key="groups"),
        RolesColumn("Roles", key="roles"),
        grids.GridColumn("External", key="external", escape=False),
        grids.GridColumn("Deleted", key="deleted", escape=False),
        grids.GridColumn("Purged", key="purged", escape=False),
    ]

    def apply_query_filter(self, query, **kwargs):
        INDEX_SEARCH_FILTERS = {
            "email": "email",
            "username": "username",
            "is": "is",
        }
        deleted = False
        purged = False
        if search_query := kwargs.get("search"):
            parsed_search = parse_filters_structured(search_query, INDEX_SEARCH_FILTERS)
            for term in parsed_search.terms:
                if isinstance(term, FilteredTerm):
                    key = term.filter
                    q = term.text
                    if key == "email":
                        query = query.filter(text_column_filter(self.model_class.email, term))
                    elif key == "username":
                        query = query.filter(text_column_filter(self.model_class.username, term))
                    elif key == "is":
                        if q == "deleted":
                            deleted = True
                        elif q == "purged":
                            purged = True
                elif isinstance(term, RawTextTerm):
                    query = query.filter(
                        raw_text_column_filter(
                            [
                                self.model_class.email,
                                self.model_class.username,
                            ],
                            term,
                        )
                    )
        if purged:
            query = query.filter(self.model_class.purged == true())
        else:
            query = query.filter(self.model_class.deleted == (true() if deleted else false()))
        return query


class RoleListGrid(grids.GridData):
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
        grids.GridColumn("Name", key="name"),
        grids.GridColumn("Description", key="description"),
        grids.GridColumn("Type", key="type"),
        GroupsColumn("Groups", key="groups"),
        UsersColumn("Users", key="users"),
        grids.GridColumn("Deleted", key="deleted", escape=False),
        grids.GridColumn("Purged", key="purged", escape=False),
        grids.GridColumn("Last Updated", key="update_time"),
    ]

    def apply_query_filter(self, query, **kwargs):
        INDEX_SEARCH_FILTERS = {
            "description": "description",
            "name": "name",
            "is": "is",
        }
        deleted = False
        query = query.filter(self.model_class.type != self.model_class.types.PRIVATE)
        if search_query := kwargs.get("search"):
            parsed_search = parse_filters_structured(search_query, INDEX_SEARCH_FILTERS)
            for term in parsed_search.terms:
                if isinstance(term, FilteredTerm):
                    key = term.filter
                    q = term.text
                    if key == "name":
                        query = query.filter(text_column_filter(self.model_class.name, term))
                    if key == "description":
                        query = query.filter(text_column_filter(self.model_class.description, term))
                    elif key == "is":
                        if q == "deleted":
                            deleted = True
                elif isinstance(term, RawTextTerm):
                    query = query.filter(
                        raw_text_column_filter(
                            [
                                self.model_class.description,
                                self.model_class.name,
                            ],
                            term,
                        )
                    )
        query = query.filter(self.model_class.deleted == (true() if deleted else false()))
        return query


class GroupListGrid(grids.GridData):
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

    # Grid definition
    title = "Groups"
    title_id = "groups-grid"
    model_class = model.Group
    default_sort_key = "name"
    columns = [
        grids.GridColumn("Name", key="name"),
        UsersColumn("Users", key="users"),
        RolesColumn("Roles", key="roles"),
        grids.GridColumn("Deleted", key="deleted", escape=False),
        grids.GridColumn("Last Updated", key="update_time"),
    ]

    def apply_query_filter(self, query, **kwargs):
        INDEX_SEARCH_FILTERS = {
            "name": "name",
            "is": "is",
        }
        deleted = False
        if search_query := kwargs.get("search"):
            parsed_search = parse_filters_structured(search_query, INDEX_SEARCH_FILTERS)
            for term in parsed_search.terms:
                if isinstance(term, FilteredTerm):
                    key = term.filter
                    q = term.text
                    if key == "name":
                        query = query.filter(text_column_filter(self.model_class.name, term))
                    elif key == "is":
                        if q == "deleted":
                            deleted = True
                elif isinstance(term, RawTextTerm):
                    query = query.filter(
                        raw_text_column_filter(
                            [
                                self.model_class.name,
                            ],
                            term,
                        )
                    )
        query = query.filter(self.model_class.deleted == (true() if deleted else false()))
        return query


class QuotaListGrid(grids.GridData):
    class AmountColumn(grids.GridColumn):
        def get_value(self, trans, grid, quota):
            return quota.operation + quota.display_amount

    class DefaultTypeColumn(grids.GridColumn):
        def get_value(self, trans, grid, quota):
            if quota.default:
                return quota.default[0].type
            return None

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
        grids.GridColumn("Name", key="name"),
        grids.GridColumn("Description", key="description"),
        AmountColumn("Amount", key="amount", model_class=model.Quota),
        UsersColumn("Users", key="users"),
        GroupsColumn("Groups", key="groups"),
        grids.GridColumn("Source", key="quota_source_label", escape=False),
        DefaultTypeColumn("Type", key="default_type"),
        grids.GridColumn("Deleted", key="deleted", escape=False),
        grids.GridColumn("Updated", key="update_time"),
    ]

    def apply_query_filter(self, query, **kwargs):
        INDEX_SEARCH_FILTERS = {
            "name": "name",
            "description": "description",
            "is": "is",
        }
        deleted = False
        if search_query := kwargs.get("search"):
            parsed_search = parse_filters_structured(search_query, INDEX_SEARCH_FILTERS)
            for term in parsed_search.terms:
                if isinstance(term, FilteredTerm):
                    key = term.filter
                    q = term.text
                    if key == "name":
                        query = query.filter(text_column_filter(self.model_class.name, term))
                    if key == "description":
                        query = query.filter(text_column_filter(self.model_class.description, term))
                    elif key == "is":
                        if q == "deleted":
                            deleted = True
                elif isinstance(term, RawTextTerm):
                    query = query.filter(
                        raw_text_column_filter(
                            [
                                self.model_class.name,
                                self.model_class.description,
                            ],
                            term,
                        )
                    )
        query = query.filter(self.model_class.deleted == (true() if deleted else false()))
        return query


# TODO: Convert admin UI to use the API and drop this.
class DatatypesEntryT(TypedDict):
    status: str
    keys: list
    data: list
    message: str


class AdminGalaxy(controller.JSAppLauncher):
    user_list_grid = UserListGrid()
    role_list_grid = RoleListGrid()
    group_list_grid = GroupListGrid()
    quota_list_grid = QuotaListGrid()

    def __init__(self, app: StructuredApp):
        super().__init__(app)
        self.quota_manager: QuotaManager = QuotaManager(app)

    @web.expose
    @web.json
    @web.require_admin
    def data_tables_list(self, trans, **kwd):
        data = []
        message = kwd.get("message", "")
        status = kwd.get("status", "done")
        sorted_data_tables = sorted(trans.app.tool_data_tables.get_tables().items())

        for _data_table_elem_name, data_table in sorted_data_tables:
            for filename, file_dict in data_table.filenames.items():
                file_missing = ["file missing"] if not file_dict.get("found") else []
                data.append(
                    {
                        "name": data_table.name,
                        "filename": filename,
                        "tool_data_path": file_dict.get("tool_data_path"),
                        "errors": ", ".join(file_missing + list(file_dict.get("errors", []))),
                    }
                )

        return {"data": data, "message": message, "status": status}

    @web.expose
    @web.json
    @web.require_admin
    def data_types_list(self, trans, **kwd) -> DatatypesEntryT:
        datatypes = []
        keys: Set[str] = set()
        message = kwd.get("message", "")
        status = kwd.get("status", "done")
        for dtype in sorted(trans.app.datatypes_registry.datatype_elems, key=lambda dt: dt.get("extension")):
            attrib = dict(dtype.attrib)
            datatypes.append(attrib)
            keys |= set(attrib.keys())
        return {"keys": list(keys), "data": datatypes, "message": message, "status": status}

    @web.expose
    @web.json
    @web.require_admin
    def users_list(self, trans, **kwd):
        return self.user_list_grid(trans, **kwd)

    @web.legacy_expose_api
    @web.require_admin
    def quotas_list(self, trans, payload=None, **kwargs):
        return self.quota_list_grid(trans, **kwargs)

    @web.legacy_expose_api
    @web.require_admin
    def create_quota(self, trans, payload=None, **kwd):
        if trans.request.method == "GET":
            all_users = []
            all_groups = []
            labels = trans.app.object_store.get_quota_source_map().get_quota_source_labels()
            label_options = [("Default Quota", "__default__")]
            label_options.extend([(label, label) for label in labels])
            for user in (
                trans.sa_session.query(trans.app.model.User)
                .filter(trans.app.model.User.table.c.deleted == false())
                .order_by(trans.app.model.User.table.c.email)
            ):
                all_users.append((user.email, trans.security.encode_id(user.id)))
            for group in (
                trans.sa_session.query(trans.app.model.Group)
                .filter(trans.app.model.Group.deleted == false())
                .order_by(trans.app.model.Group.name)
            ):
                all_groups.append((group.name, trans.security.encode_id(group.id)))
            default_options = [("No", "no")]
            for type_ in trans.app.model.DefaultQuotaAssociation.types:
                default_options.append((f"Yes, {type_}", type_))
            rval = {
                "title": "Create Quota",
                "inputs": [
                    {"name": "name", "label": "Name"},
                    {"name": "description", "label": "Description"},
                    {"name": "amount", "label": "Amount", "help": 'Examples: "10000MB", "99 gb", "0.2T", "unlimited"'},
                    {
                        "name": "operation",
                        "label": "Assign, increase by amount, or decrease by amount?",
                        "options": [("=", "="), ("+", "+"), ("-", "-")],
                    },
                    {
                        "name": "default",
                        "label": "Is this quota a default for a class of users (if yes, what type)?",
                        "options": default_options,
                        "help": "Warning: Any users or groups associated with this quota will be disassociated.",
                    },
                ],
            }
            if len(label_options) > 1:
                rval["inputs"].append(
                    {
                        "name": "quota_source_label",
                        "label": "Apply quota to labeled object stores.",
                        "options": label_options,
                    }
                )
            rval["inputs"].extend(
                [
                    build_select_input("in_groups", "Groups", all_groups, []),
                    build_select_input("in_users", "Users", all_users, []),
                ]
            )
            return rval
        else:
            try:
                quota_source_label = payload.get("quota_source_label")
                if quota_source_label == "__default__":
                    payload["quota_source_label"] = None
                quota, message = self.quota_manager.create_quota(payload, decode_id=trans.security.decode_id)
                return {"message": message}
            except ActionInputError as e:
                return self.message_exception(trans, e.err_msg)

    @web.legacy_expose_api
    @web.require_admin
    def rename_quota(self, trans, payload=None, **kwd):
        id = kwd.get("id")
        if not id:
            return self.message_exception(trans, "No quota id received for renaming.")
        quota = get_quota(trans, id)
        if trans.request.method == "GET":
            return {
                "title": f"Change quota name and description for '{quota.name}'",
                "inputs": [
                    {"name": "name", "label": "Name", "value": quota.name},
                    {"name": "description", "label": "Description", "value": quota.description},
                ],
            }
        else:
            try:
                return {"message": self.quota_manager.rename_quota(quota, util.Params(payload))}
            except ActionInputError as e:
                return self.message_exception(trans, e.err_msg)

    @web.legacy_expose_api
    @web.require_admin
    def manage_users_and_groups_for_quota(self, trans, payload=None, **kwd):
        quota_id = kwd.get("id")
        if not quota_id:
            return self.message_exception(trans, f"Invalid quota id ({str(quota_id)}) received")
        quota = get_quota(trans, quota_id)
        if trans.request.method == "GET":
            in_users = []
            all_users = []
            in_groups = []
            all_groups = []
            for user in (
                trans.sa_session.query(trans.app.model.User)
                .filter(trans.app.model.User.table.c.deleted == false())
                .order_by(trans.app.model.User.table.c.email)
            ):
                if user in [x.user for x in quota.users]:
                    in_users.append(trans.security.encode_id(user.id))
                all_users.append((user.email, trans.security.encode_id(user.id)))
            for group in (
                trans.sa_session.query(trans.app.model.Group)
                .filter(trans.app.model.Group.deleted == false())
                .order_by(trans.app.model.Group.name)
            ):
                if group in [x.group for x in quota.groups]:
                    in_groups.append(trans.security.encode_id(group.id))
                all_groups.append((group.name, trans.security.encode_id(group.id)))
            return {
                "title": f"Quota '{quota.name}'",
                "message": "Quota '%s' is currently associated with %d user(s) and %d group(s)."
                % (quota.name, len(in_users), len(in_groups)),
                "status": "info",
                "inputs": [
                    build_select_input("in_groups", "Groups", all_groups, in_groups),
                    build_select_input("in_users", "Users", all_users, in_users),
                ],
            }
        else:
            try:
                return {
                    "message": self.quota_manager.manage_users_and_groups_for_quota(
                        quota, util.Params(payload), decode_id=trans.security.decode_id
                    )
                }
            except ActionInputError as e:
                return self.message_exception(trans, e.err_msg)

    @web.legacy_expose_api
    @web.require_admin
    def edit_quota(self, trans, payload=None, **kwd):
        id = kwd.get("id")
        if not id:
            return self.message_exception(trans, "No quota id received for renaming.")
        quota = get_quota(trans, id)
        if trans.request.method == "GET":
            return {
                "title": f"Edit quota size for '{quota.name}'",
                "inputs": [
                    {
                        "name": "amount",
                        "label": "Amount",
                        "value": quota.display_amount,
                        "help": 'Examples: "10000MB", "99 gb", "0.2T", "unlimited"',
                    },
                    {
                        "name": "operation",
                        "label": "Assign, increase by amount, or decrease by amount?",
                        "options": [("=", "="), ("+", "+"), ("-", "-")],
                        "value": quota.operation,
                    },
                ],
            }
        else:
            try:
                return {"message": self.quota_manager.edit_quota(quota, util.Params(payload))}
            except ActionInputError as e:
                return self.message_exception(trans, e.err_msg)

    @web.legacy_expose_api
    @web.require_admin
    def set_quota_default(self, trans, payload=None, **kwd):
        id = kwd.get("id")
        if not id:
            return self.message_exception(trans, "No quota id received for renaming.")
        quota = get_quota(trans, id)
        if trans.request.method == "GET":
            default_value = quota.default[0].type if quota.default else "no"
            default_options = [("No", "no")]
            for typ in trans.app.model.DefaultQuotaAssociation.types.__members__.values():
                default_options.append((f"Yes, {typ}", typ))
            return {
                "title": f"Set quota default for '{quota.name}'",
                "inputs": [
                    {
                        "name": "default",
                        "label": "Is this quota a default for a class of users (if yes, what type)?",
                        "options": default_options,
                        "value": default_value,
                        "help": "Warning: Any users or groups associated with this quota will be disassociated.",
                    }
                ],
            }
        else:
            try:
                return {"message": self.quota_manager.set_quota_default(quota, util.Params(payload))}
            except ActionInputError as e:
                return self.message_exception(trans, e.err_msg)

    @web.expose
    @web.require_admin
    def impersonate(self, trans, **kwd):
        if not trans.app.config.allow_user_impersonation:
            return trans.show_error_message("User impersonation is not enabled in this instance of Galaxy.")
        user = None
        if (user_id := kwd.get("id", None)) is not None:
            try:
                user = trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(user_id))
                if user:
                    trans.handle_user_logout()
                    trans.handle_user_login(user)
                    return trans.show_message(
                        f"You are now logged in as {user.email}, <a target=\"_top\" href=\"{url_for(controller='root')}\">return to the home page</a>",
                        use_panels=True,
                    )
            except Exception:
                log.exception("Error fetching user for impersonation")
        return trans.response.send_redirect(
            web.url_for(controller="admin", action="users", message="Invalid user selected", status="error")
        )

    @web.expose
    @web.json
    @web.require_admin
    def roles_list(self, trans, **kwargs):
        return self.role_list_grid(trans, **kwargs)

    @web.legacy_expose_api
    @web.require_admin
    def create_role(self, trans, payload=None, **kwd):
        if trans.request.method == "GET":
            all_users = []
            all_groups = []
            for user in (
                trans.sa_session.query(trans.app.model.User)
                .filter(trans.app.model.User.table.c.deleted == false())
                .order_by(trans.app.model.User.table.c.email)
            ):
                all_users.append((user.email, trans.security.encode_id(user.id)))
            for group in (
                trans.sa_session.query(trans.app.model.Group)
                .filter(trans.app.model.Group.deleted == false())
                .order_by(trans.app.model.Group.name)
            ):
                all_groups.append((group.name, trans.security.encode_id(group.id)))
            return {
                "title": "Create Role",
                "inputs": [
                    {"name": "name", "label": "Name"},
                    {"name": "description", "label": "Description"},
                    build_select_input("in_groups", "Groups", all_groups, []),
                    build_select_input("in_users", "Users", all_users, []),
                    {
                        "name": "auto_create",
                        "label": "Create a new group of the same name for this role:",
                        "type": "boolean",
                        "optional": True,
                    },
                ],
            }
        else:
            name = util.restore_text(payload.get("name", ""))
            description = util.restore_text(payload.get("description", ""))
            auto_create_checked = payload.get("auto_create")
            in_users = [
                trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(x))
                for x in util.listify(payload.get("in_users"))
            ]
            in_groups = [
                trans.sa_session.query(trans.app.model.Group).get(trans.security.decode_id(x))
                for x in util.listify(payload.get("in_groups"))
            ]
            if not name or not description:
                return self.message_exception(trans, "Enter a valid name and a description.")
            elif trans.sa_session.query(trans.app.model.Role).filter(trans.app.model.Role.name == name).first():
                return self.message_exception(
                    trans, "Role names must be unique and a role with that name already exists, so choose another name."
                )
            elif None in in_users or None in in_groups:
                return self.message_exception(trans, "One or more invalid user/group id has been provided.")
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
                    if trans.sa_session.query(trans.app.model.Group).filter(trans.app.model.Group.name == name).first():
                        return self.message_exception(
                            trans,
                            "A group with that name already exists, so choose another name or disable group creation.",
                        )
                    # Create the group
                    group = trans.app.model.Group(name=name)
                    trans.sa_session.add(group)
                    # Associate the group with the role
                    gra = trans.model.GroupRoleAssociation(group, role)
                    trans.sa_session.add(gra)
                    num_in_groups = len(in_groups) + 1
                else:
                    num_in_groups = len(in_groups)
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
                message = f"Role '{role.name}' has been created with {len(in_users)} associated users and {num_in_groups} associated groups."
                if auto_create_checked:
                    message += (
                        "One of the groups associated with this role is the newly created group with the same name."
                    )
                return {"message": message}

    @web.legacy_expose_api
    @web.require_admin
    def rename_role(self, trans, payload=None, **kwd):
        id = kwd.get("id")
        if not id:
            return self.message_exception(trans, "No role id received for renaming.")
        role = get_role(trans, id)
        if trans.request.method == "GET":
            return {
                "title": f"Change role name and description for '{role.name}'",
                "inputs": [
                    {"name": "name", "label": "Name", "value": role.name},
                    {"name": "description", "label": "Description", "value": role.description},
                ],
            }
        else:
            old_name = role.name
            new_name = util.restore_text(payload.get("name"))
            new_description = util.restore_text(payload.get("description"))
            if not new_name:
                return self.message_exception(trans, "Enter a valid role name.")
            else:
                existing_role = (
                    trans.sa_session.query(trans.app.model.Role).filter(trans.app.model.Role.name == new_name).first()
                )
                if existing_role and existing_role.id != role.id:
                    return self.message_exception(trans, "A role with that name already exists.")
                else:
                    if not (role.name == new_name and role.description == new_description):
                        role.name = new_name
                        role.description = new_description
                        trans.sa_session.add(role)
                        with transaction(trans.sa_session):
                            trans.sa_session.commit()
            return {"message": f"Role '{old_name}' has been renamed to '{new_name}'."}

    @web.legacy_expose_api
    @web.require_admin
    def manage_users_and_groups_for_role(self, trans, payload=None, **kwd):
        role_id = kwd.get("id")
        if not role_id:
            return self.message_exception(trans, f"Invalid role id ({str(role_id)}) received")
        role = get_role(trans, role_id)
        if trans.request.method == "GET":
            in_users = []
            all_users = []
            in_groups = []
            all_groups = []
            for user in (
                trans.sa_session.query(trans.app.model.User)
                .filter(trans.app.model.User.table.c.deleted == false())
                .order_by(trans.app.model.User.table.c.email)
            ):
                if user in [x.user for x in role.users]:
                    in_users.append(trans.security.encode_id(user.id))
                all_users.append((user.email, trans.security.encode_id(user.id)))
            for group in (
                trans.sa_session.query(trans.app.model.Group)
                .filter(trans.app.model.Group.deleted == false())
                .order_by(trans.app.model.Group.name)
            ):
                if group in [x.group for x in role.groups]:
                    in_groups.append(trans.security.encode_id(group.id))
                all_groups.append((group.name, trans.security.encode_id(group.id)))
            return {
                "title": f"Role '{role.name}'",
                "message": "Role '%s' is currently associated with %d user(s) and %d group(s)."
                % (role.name, len(in_users), len(in_groups)),
                "status": "info",
                "inputs": [
                    build_select_input("in_groups", "Groups", all_groups, in_groups),
                    build_select_input("in_users", "Users", all_users, in_users),
                ],
            }
        else:
            in_users = [
                trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(x))
                for x in util.listify(payload.get("in_users"))
            ]
            in_groups = [
                trans.sa_session.query(trans.app.model.Group).get(trans.security.decode_id(x))
                for x in util.listify(payload.get("in_groups"))
            ]
            if None in in_users or None in in_groups:
                return self.message_exception(trans, "One or more invalid user/group id has been provided.")
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
                    with transaction(trans.sa_session):
                        trans.sa_session.commit()
            trans.app.security_agent.set_entity_role_associations(roles=[role], users=in_users, groups=in_groups)
            trans.sa_session.refresh(role)
            return {
                "message": f"Role '{role.name}' has been updated with {len(in_users)} associated users and {len(in_groups)} associated groups."
            }

    @web.legacy_expose_api
    @web.require_admin
    def groups_list(self, trans, **kwargs):
        return self.group_list_grid(trans, **kwargs)

    @web.legacy_expose_api
    @web.require_admin
    def rename_group(self, trans, payload=None, **kwd):
        id = kwd.get("id")
        if not id:
            return self.message_exception(trans, "No group id received for renaming.")
        group = get_group(trans, id)
        if trans.request.method == "GET":
            return {
                "title": f"Change group name for '{group.name}'",
                "inputs": [{"name": "name", "label": "Name", "value": group.name}],
            }
        else:
            old_name = group.name
            new_name = util.restore_text(payload.get("name"))
            if not new_name:
                return self.message_exception(trans, "Enter a valid group name.")
            else:
                existing_group = (
                    trans.sa_session.query(trans.app.model.Group).filter(trans.app.model.Group.name == new_name).first()
                )
                if existing_group and existing_group.id != group.id:
                    return self.message_exception(trans, "A group with that name already exists.")
                else:
                    if not (group.name == new_name):
                        group.name = new_name
                        trans.sa_session.add(group)
                        with transaction(trans.sa_session):
                            trans.sa_session.commit()
            return {"message": f"Group '{old_name}' has been renamed to '{new_name}'."}

    @web.legacy_expose_api
    @web.require_admin
    def manage_users_and_roles_for_group(self, trans, payload=None, **kwd):
        group_id = kwd.get("id")
        if not group_id:
            return self.message_exception(trans, f"Invalid group id ({str(group_id)}) received")
        group = get_group(trans, group_id)
        if trans.request.method == "GET":
            in_users = []
            all_users = []
            in_roles = []
            all_roles = []
            for user in (
                trans.sa_session.query(trans.app.model.User)
                .filter(trans.app.model.User.table.c.deleted == false())
                .order_by(trans.app.model.User.table.c.email)
            ):
                if user in [x.user for x in group.users]:
                    in_users.append(trans.security.encode_id(user.id))
                all_users.append((user.email, trans.security.encode_id(user.id)))
            for role in (
                trans.sa_session.query(trans.app.model.Role)
                .filter(trans.app.model.Role.deleted == false())
                .order_by(trans.app.model.Role.name)
            ):
                if role in [x.role for x in group.roles]:
                    in_roles.append(trans.security.encode_id(role.id))
                all_roles.append((role.name, trans.security.encode_id(role.id)))
            return {
                "title": f"Group '{group.name}'",
                "message": "Group '%s' is currently associated with %d user(s) and %d role(s)."
                % (group.name, len(in_users), len(in_roles)),
                "status": "info",
                "inputs": [
                    build_select_input("in_roles", "Roles", all_roles, in_roles),
                    build_select_input("in_users", "Users", all_users, in_users),
                ],
            }
        else:
            in_users = [
                trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(x))
                for x in util.listify(payload.get("in_users"))
            ]
            in_roles = [
                trans.sa_session.query(trans.app.model.Role).get(trans.security.decode_id(x))
                for x in util.listify(payload.get("in_roles"))
            ]
            if None in in_users or None in in_roles:
                return self.message_exception(trans, "One or more invalid user/role id has been provided.")
            trans.app.security_agent.set_entity_group_associations(groups=[group], users=in_users, roles=in_roles)
            trans.sa_session.refresh(group)
            return {
                "message": f"Group '{group.name}' has been updated with {len(in_users)} associated users and {len(in_roles)} associated roles."
            }

    @web.legacy_expose_api
    @web.require_admin
    def create_group(self, trans, payload=None, **kwd):
        if trans.request.method == "GET":
            all_users = []
            all_roles = []
            for user in (
                trans.sa_session.query(trans.app.model.User)
                .filter(trans.app.model.User.table.c.deleted == false())
                .order_by(trans.app.model.User.table.c.email)
            ):
                all_users.append((user.email, trans.security.encode_id(user.id)))
            for role in (
                trans.sa_session.query(trans.app.model.Role)
                .filter(trans.app.model.Role.deleted == false())
                .order_by(trans.app.model.Role.name)
            ):
                all_roles.append((role.name, trans.security.encode_id(role.id)))
            return {
                "title": "Create Group",
                "title_id": "create-group",
                "inputs": [
                    {"name": "name", "label": "Name"},
                    build_select_input("in_roles", "Roles", all_roles, []),
                    build_select_input("in_users", "Users", all_users, []),
                    {
                        "name": "auto_create",
                        "label": "Create a new role of the same name for this group:",
                        "type": "boolean",
                        "optional": True,
                    },
                ],
            }
        else:
            name = util.restore_text(payload.get("name", ""))
            auto_create_checked = payload.get("auto_create")
            in_users = [
                trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(x))
                for x in util.listify(payload.get("in_users"))
            ]
            in_roles = [
                trans.sa_session.query(trans.app.model.Role).get(trans.security.decode_id(x))
                for x in util.listify(payload.get("in_roles"))
            ]
            if not name:
                return self.message_exception(trans, "Enter a valid name.")
            elif trans.sa_session.query(trans.app.model.Group).filter(trans.app.model.Group.name == name).first():
                return self.message_exception(
                    trans,
                    "Group names must be unique and a group with that name already exists, so choose another name.",
                )
            elif None in in_users or None in in_roles:
                return self.message_exception(trans, "One or more invalid user/role id has been provided.")
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
                    if trans.sa_session.query(trans.app.model.Role).filter(trans.app.model.Role.name == name).first():
                        return self.message_exception(
                            trans,
                            "A role with that name already exists, so choose another name or disable role creation.",
                        )
                    # Create the role
                    role = trans.app.model.Role(name=name, description=f"Role for group {name}")
                    trans.sa_session.add(role)
                    # Associate the group with the role
                    gra = trans.model.GroupRoleAssociation(group, role)
                    trans.sa_session.add(gra)
                    num_in_roles = len(in_roles) + 1
                else:
                    num_in_roles = len(in_roles)
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
                message = "Group '%s' has been created with %d associated users and %d associated roles." % (
                    group.name,
                    len(in_users),
                    num_in_roles,
                )
                if auto_create_checked:
                    message += (
                        "One of the roles associated with this group is the newly created role with the same name."
                    )
                return {"message": message}

    @web.expose
    @web.require_admin
    def create_new_user(self, trans, **kwd):
        return trans.response.send_redirect(web.url_for(controller="user", action="create", cntrller="admin"))

    @web.legacy_expose_api
    @web.require_admin
    def reset_user_password(self, trans, payload=None, **kwd):
        users = {user_id: get_user(trans, user_id) for user_id in util.listify(kwd.get("id"))}
        if users:
            if trans.request.method == "GET":
                return {
                    "message": f"Changes password(s) for: {', '.join(user.email for user in users.values())}.",
                    "status": "info",
                    "inputs": [
                        {"name": "password", "label": "New password", "type": "password"},
                        {"name": "confirm", "label": "Confirm password", "type": "password"},
                    ],
                }
            else:
                password = payload.get("password")
                confirm = payload.get("confirm")
                message = validate_password(trans, password, confirm)
                if message:
                    return self.message_exception(trans, message)
                for user in users.values():
                    user.set_password_cleartext(password)
                    trans.sa_session.add(user)
                    with transaction(trans.sa_session):
                        trans.sa_session.commit()
                return {"message": "Passwords reset for %d user(s)." % len(users)}
        else:
            return self.message_exception(trans, "Please specify user ids.")

    @web.legacy_expose_api
    @web.require_admin
    def manage_roles_and_groups_for_user(self, trans, payload=None, **kwd):
        user_id = kwd.get("id")
        if not user_id:
            return self.message_exception(trans, f"Invalid user id ({str(user_id)}) received")
        user = get_user(trans, user_id)
        if trans.request.method == "GET":
            in_roles = []
            all_roles = []
            in_groups = []
            all_groups = []
            for role in (
                trans.sa_session.query(trans.app.model.Role)
                .filter(trans.app.model.Role.deleted == false())
                .order_by(trans.app.model.Role.name)
            ):
                if role in [x.role for x in user.roles]:
                    in_roles.append(trans.security.encode_id(role.id))
                if role.type != trans.app.model.Role.types.PRIVATE:
                    # There is a 1 to 1 mapping between a user and a PRIVATE role, so private roles should
                    # not be listed in the roles form fields, except for the currently selected user's private
                    # role, which should always be in in_roles.  The check above is added as an additional
                    # precaution, since for a period of time we were including private roles in the form fields.
                    all_roles.append((role.name, trans.security.encode_id(role.id)))
            for group in (
                trans.sa_session.query(trans.app.model.Group)
                .filter(trans.app.model.Group.deleted == false())
                .order_by(trans.app.model.Group.name)
            ):
                if group in [x.group for x in user.groups]:
                    in_groups.append(trans.security.encode_id(group.id))
                all_groups.append((group.name, trans.security.encode_id(group.id)))
            return {
                "title": f"Roles and groups for '{user.email}'",
                "message": f"User '{user.email}' is currently associated with {len(in_roles) - 1} role(s) and is a member of {len(in_groups)} group(s).",
                "status": "info",
                "inputs": [
                    build_select_input("in_roles", "Roles", all_roles, in_roles),
                    build_select_input("in_groups", "Groups", all_groups, in_groups),
                ],
            }
        else:
            in_roles = [
                trans.sa_session.query(trans.app.model.Role).get(trans.security.decode_id(x))
                for x in util.listify(payload.get("in_roles"))
            ]
            in_groups = [
                trans.sa_session.query(trans.app.model.Group).get(trans.security.decode_id(x))
                for x in util.listify(payload.get("in_groups"))
            ]
            if None in in_groups or None in in_roles:
                return self.message_exception(trans, "One or more invalid role/group id has been provided.")

            # make sure the user is not dis-associating himself from his private role
            private_role = trans.app.security_agent.get_private_user_role(user)
            if private_role not in in_roles:
                in_roles.append(private_role)

            trans.app.security_agent.set_entity_user_associations(users=[user], roles=in_roles, groups=in_groups)
            trans.sa_session.refresh(user)
            return {
                "message": f"User '{user.email}' has been updated with {len(in_roles) - 1} associated roles and {len(in_groups)} associated groups (private roles are not displayed)."
            }


# ---- Utility methods -------------------------------------------------------


def build_select_input(name, label, options, value):
    return {
        "type": "select",
        "multiple": True,
        "optional": True,
        "individual": True,
        "name": name,
        "label": label,
        "options": options,
        "value": value,
    }


def get_user(trans, user_id):
    """Get a User from the database by id."""
    user = trans.sa_session.query(trans.model.User).get(trans.security.decode_id(user_id))
    if not user:
        return trans.show_error_message(f"User not found for id ({str(user_id)})")
    return user


def get_role(trans, id):
    """Get a Role from the database by id."""
    # Load user from database
    id = trans.security.decode_id(id)
    role = trans.sa_session.query(trans.model.Role).get(id)
    if not role:
        return trans.show_error_message(f"Role not found for id ({str(id)})")
    return role


def get_group(trans, id):
    """Get a Group from the database by id."""
    # Load user from database
    id = trans.security.decode_id(id)
    group = trans.sa_session.query(trans.model.Group).get(id)
    if not group:
        return trans.show_error_message(f"Group not found for id ({str(id)})")
    return group


def get_quota(trans, id):
    """Get a Quota from the database by id."""
    # Load user from database
    id = trans.security.decode_id(id)
    quota = trans.sa_session.query(trans.model.Quota).get(id)
    return quota
