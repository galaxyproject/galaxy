import logging

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
from galaxy.model.index_filter_util import (
    raw_text_column_filter,
    text_column_filter,
)
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
from galaxy.webapps.base.webapp import GalaxyWebTransaction

log = logging.getLogger(__name__)


class UserListGrid(grids.GridData):
    class StatusColumn(grids.GridColumn):
        def get_value(self, trans: GalaxyWebTransaction, grid, user):
            if user.purged:
                return "Purged"
            elif user.deleted:
                return "Deleted"
            return "Available"

    class GroupsColumn(grids.GridColumn):
        def get_value(self, trans: GalaxyWebTransaction, grid, user):
            if user.groups:
                return len(user.groups)
            return 0

    class RolesColumn(grids.GridColumn):
        def get_value(self, trans: GalaxyWebTransaction, grid, user):
            if user.roles:
                return len(user.roles)
            return 0

    class LastLoginColumn(grids.GridColumn):
        def get_value(self, trans: GalaxyWebTransaction, grid, user):
            if user.galaxy_sessions:
                return self.format(user.current_galaxy_session.update_time)
            return "never"

        def sort(self, trans: GalaxyWebTransaction, query, ascending, column_name=None):
            last_login_subquery = (
                trans.sa_session.query(
                    model.GalaxySession.table.c.user_id,
                    func.max(model.GalaxySession.table.c.update_time).label("last_login"),
                )
                .group_by(model.GalaxySession.table.c.user_id)
                .subquery()
            )
            query = query.outerjoin(last_login_subquery, model.User.table.c.id == last_login_subquery.c.user_id)

            if not ascending:
                query = query.order_by((last_login_subquery.c.last_login).desc().nullslast())
            else:
                query = query.order_by((last_login_subquery.c.last_login).asc().nullsfirst())
            return query

    class DiskUsageColumn(grids.GridColumn):
        def get_value(self, trans: GalaxyWebTransaction, grid, user):
            return user.get_disk_usage(nice_size=True)

        def sort(self, trans: GalaxyWebTransaction, query, ascending, column_name=None):
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
        def get_value(self, trans: GalaxyWebTransaction, grid, role):
            if role.groups:
                return len(role.groups)
            return 0

    class UsersColumn(grids.GridColumn):
        def get_value(self, trans: GalaxyWebTransaction, grid, role):
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
        def get_value(self, trans: GalaxyWebTransaction, grid, group):
            if group.roles:
                return len(group.roles)
            return 0

    class UsersColumn(grids.GridColumn):
        def get_value(self, trans: GalaxyWebTransaction, grid, group):
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
        def get_value(self, trans: GalaxyWebTransaction, grid, quota):
            return quota.operation + quota.display_amount

    class DefaultTypeColumn(grids.GridColumn):
        def get_value(self, trans: GalaxyWebTransaction, grid, quota):
            if quota.default:
                return quota.default[0].type
            return None

    class UsersColumn(grids.GridColumn):
        def get_value(self, trans: GalaxyWebTransaction, grid, quota):
            if quota.users:
                return len(quota.users)
            return 0

    class GroupsColumn(grids.GridColumn):
        def get_value(self, trans: GalaxyWebTransaction, grid, quota):
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


class AdminGalaxy(controller.BaseUIController):
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
    def data_tables_list(self, trans: GalaxyWebTransaction, **kwd):
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
    def data_types_list(self, trans: GalaxyWebTransaction, **kwd) -> DatatypesEntryT:
        datatypes = []
        keys: set[str] = set()
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
    def users_list(self, trans: GalaxyWebTransaction, **kwd):
        return self.user_list_grid(trans, **kwd)

    @web.legacy_expose_api
    @web.require_admin
    def quotas_list(self, trans: GalaxyWebTransaction, payload=None, **kwargs):
        return self.quota_list_grid(trans, **kwargs)

    @web.legacy_expose_api
    @web.require_admin
    def rename_quota(self, trans: GalaxyWebTransaction, payload=None, **kwd):
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
    def edit_quota(self, trans: GalaxyWebTransaction, payload=None, **kwd):
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
    def set_quota_default(self, trans: GalaxyWebTransaction, payload=None, **kwd):
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
    def impersonate(self, trans: GalaxyWebTransaction, **kwd):
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
                        f'You are now logged in as {user.email}, <a target="_top" href="{url_for("/")}">return to the home page</a>',
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
    def roles_list(self, trans: GalaxyWebTransaction, **kwargs):
        return self.role_list_grid(trans, **kwargs)

    @web.legacy_expose_api
    @web.require_admin
    def groups_list(self, trans: GalaxyWebTransaction, **kwargs):
        return self.group_list_grid(trans, **kwargs)

    @web.expose
    @web.require_admin
    def create_new_user(self, trans: GalaxyWebTransaction, **kwd):
        return trans.response.send_redirect(web.url_for(controller="user", action="create", cntrller="admin"))


# ---- Utility methods -------------------------------------------------------


def get_quota(trans: GalaxyWebTransaction, id):
    """Get a Quota from the database by id."""
    # Load user from database
    id = trans.security.decode_id(id)
    quota = trans.sa_session.query(trans.model.Quota).get(id)
    return quota
