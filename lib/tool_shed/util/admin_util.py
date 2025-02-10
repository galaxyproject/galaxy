import logging
import time
from typing import Optional

from sqlalchemy import (
    false,
    func,
    select,
)

from galaxy import (
    util,
    web,
)
from galaxy.model import (
    Library,
    LibraryDatasetDatasetAssociation,
)
from galaxy.security.validate_user_input import validate_password
from galaxy.util import inflector
from galaxy.util.hash_util import new_secure_hash_v2
from galaxy.web.form_builder import CheckboxField
from galaxy.web.legacy_framework.grids import (
    Grid,
    GridOperation,
)
from tool_shed.util.web_util import escape

log = logging.getLogger(__name__)
compliance_log = logging.getLogger("COMPLIANCE")


class Admin:
    # Override these
    user_list_grid: Optional[Grid] = None
    role_list_grid: Optional[Grid] = None
    group_list_grid: Optional[Grid] = None
    delete_operation: Optional[GridOperation] = None
    undelete_operation: Optional[GridOperation] = None
    purge_operation: Optional[GridOperation] = None

    @web.expose
    @web.require_admin
    def index(self, trans, **kwd):
        message = escape(kwd.get("message", ""))
        status = kwd.get("status", "done")
        return trans.fill_template("/webapps/tool_shed/admin/index.mako", message=message, status=status)

    @web.expose
    @web.require_admin
    def center(self, trans, **kwd):
        message = escape(kwd.get("message", ""))
        status = kwd.get("status", "done")
        return trans.fill_template("/webapps/tool_shed/admin/center.mako", message=message, status=status)

    @web.expose
    @web.require_admin
    def roles(self, trans, **kwargs):
        if "operation" in kwargs:
            operation = kwargs["operation"].lower().replace("+", " ")
            if operation == "roles":
                return self.role(trans, **kwargs)
            if operation == "create":
                return self.create_role(trans, **kwargs)
            if operation == "delete":
                return self.mark_role_deleted(trans, **kwargs)
            if operation == "undelete":
                return self.undelete_role(trans, **kwargs)
            if operation == "purge":
                return self.purge_role(trans, **kwargs)
            if operation == "manage users and groups":
                return self.manage_users_and_groups_for_role(trans, **kwargs)
            if operation == "manage role associations":
                # This is currently used only in the Tool Shed.
                return self.manage_role_associations(trans, **kwargs)
            if operation == "rename":
                return self.rename_role(trans, **kwargs)
        # Render the list view
        return self.role_list_grid(trans, **kwargs)

    @web.expose
    @web.require_admin
    def create_role(self, trans, **kwd):
        params = util.Params(kwd)
        message = util.restore_text(params.get("message", ""))
        status = params.get("status", "done")
        name = util.restore_text(params.get("name", ""))
        description = util.restore_text(params.get("description", ""))
        in_users = util.listify(params.get("in_users", []))
        out_users = util.listify(params.get("out_users", []))
        in_groups = util.listify(params.get("in_groups", []))
        out_groups = util.listify(params.get("out_groups", []))
        create_group_for_role = params.get("create_group_for_role", "")
        create_group_for_role_checked = CheckboxField.is_checked(create_group_for_role)
        ok = True

        if params.get("create_role_button", False):
            if not name or not description:
                message = "Enter a valid name and a description."
                status = "error"
                ok = False
            elif get_role_id(trans.sa_session, trans.app.model.Role, name):
                message = "Role names must be unique and a role with that name already exists, so choose another name."
                status = "error"
                ok = False
            else:
                # Create the role
                role = trans.app.model.Role(name=name, description=description, type=trans.app.model.Role.types.ADMIN)
                trans.sa_session.add(role)
                # Create the UserRoleAssociations
                for user in [trans.sa_session.get(trans.app.model.User, x) for x in in_users]:
                    ura = trans.app.model.UserRoleAssociation(user, role)
                    trans.sa_session.add(ura)
                # Create the GroupRoleAssociations
                for group in [trans.sa_session.get(trans.app.model.Group, x) for x in in_groups]:
                    gra = trans.app.model.GroupRoleAssociation(group, role)
                    trans.sa_session.add(gra)
                if create_group_for_role_checked:
                    # Create the group
                    group = trans.app.model.Group(name=name)
                    trans.sa_session.add(group)
                    # Associate the group with the role
                    gra = trans.model.GroupRoleAssociation(group, role)
                    trans.sa_session.add(gra)
                    num_in_groups = len(in_groups) + 1
                else:
                    num_in_groups = len(in_groups)
                trans.sa_session.commit()
                message = f"Role '{role.name}' has been created with {len(in_users)} associated users and {num_in_groups} associated groups.  "
                if create_group_for_role_checked:
                    message += (
                        "One of the groups associated with this role is the newly created group with the same name."
                    )
                trans.response.send_redirect(
                    web.url_for(controller="admin", action="roles", message=util.sanitize_text(message), status="done")
                )
        if ok:
            for user in get_current_users(trans.sa_session, trans.app.model.User):
                out_users.append((user.id, user.email))
            for group in get_current_groups(trans.sa_session, trans.app.model.Group):
                out_groups.append((group.id, group.name))
        return trans.fill_template(
            "/webapps/tool_shed/admin/dataset_security/role/role_create.mako",
            name=name,
            description=description,
            in_users=in_users,
            out_users=out_users,
            in_groups=in_groups,
            out_groups=out_groups,
            create_group_for_role_checked=create_group_for_role_checked,
            message=message,
            status=status,
        )

    @web.expose
    @web.require_admin
    def rename_role(self, trans, **kwd):
        params = util.Params(kwd)
        message = util.restore_text(params.get("message", ""))
        status = params.get("status", "done")
        id = params.get("id", None)
        if not id:
            message = "No role ids received for renaming"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="roles", message=message, status="error")
            )
        role = get_role(trans, id)
        if params.get("rename_role_button", False):
            old_name = role.name
            new_name = util.restore_text(params.name)
            new_description = util.restore_text(params.description)
            if not new_name:
                message = "Enter a valid name"
                status = "error"
            else:
                if get_role_id(trans.sa_session, trans.app.model.Role, new_name) != role.id:
                    message = "A role with that name already exists"
                    status = "error"
                else:
                    if not (role.name == new_name and role.description == new_description):
                        role.name = new_name
                        role.description = new_description
                        trans.sa_session.add(role)
                        trans.sa_session.commit()
                        message = f"Role '{old_name}' has been renamed to '{new_name}'"
                    return trans.response.send_redirect(
                        web.url_for(
                            controller="admin", action="roles", message=util.sanitize_text(message), status="done"
                        )
                    )
        return trans.fill_template(
            "/webapps/tool_shed/admin/dataset_security/role/role_rename.mako", role=role, message=message, status=status
        )

    @web.expose
    @web.require_admin
    def manage_users_and_groups_for_role(self, trans, **kwd):
        params = util.Params(kwd)
        message = util.restore_text(params.get("message", ""))
        status = params.get("status", "done")
        id = params.get("id", None)
        if not id:
            message = "No role ids received for managing users and groups"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="roles", message=message, status="error")
            )
        role = get_role(trans, id)
        if params.get("role_members_edit_button", False):
            in_users = [trans.sa_session.get(trans.app.model.User, x) for x in util.listify(params.in_users)]
            if trans.webapp.name == "galaxy":
                for ura in role.users:
                    user = trans.sa_session.get(trans.app.model.User, ura.user_id)
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
                        trans.sa_session.commit()
            in_groups = [trans.sa_session.get(trans.app.model.Group, x) for x in util.listify(params.in_groups)]
            trans.app.security_agent.set_entity_role_associations(roles=[role], users=in_users, groups=in_groups)
            trans.sa_session.refresh(role)
            message = f"Role '{role.name}' has been updated with {len(in_users)} associated users and {len(in_groups)} associated groups"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="roles", message=util.sanitize_text(message), status=status)
            )
        in_users = []
        out_users = []
        in_groups = []
        out_groups = []
        for user in get_current_users(trans.sa_session, trans.app.model.User):
            if user in [x.user for x in role.users]:
                in_users.append((user.id, user.email))
            else:
                out_users.append((user.id, user.email))
        for group in get_current_groups(trans.sa_session, trans.app.model.Group):
            if group in [x.group for x in role.groups]:
                in_groups.append((group.id, group.name))
            else:
                out_groups.append((group.id, group.name))
        library_dataset_actions = {}
        if trans.webapp.name == "galaxy" and len(role.dataset_actions) < 25:
            # Build a list of tuples that are LibraryDatasetDatasetAssociationss followed by a list of actions
            # whose DatasetPermissions is associated with the Role
            # [ ( LibraryDatasetDatasetAssociation [ action, action ] ) ]
            for dp in role.dataset_actions:
                for ldda in get_ldda_by_dataset(trans.sa_session, dp.dataset_id):
                    root_found = False
                    folder_path = ""
                    folder = ldda.library_dataset.folder
                    while not root_found:
                        folder_path = f"{folder.name} / {folder_path}"
                        if not folder.parent:
                            root_found = True
                        else:
                            folder = folder.parent
                    folder_path = f"{folder_path} {ldda.name}"
                    library = get_library_by_folder(trans.sa_session, folder.id)
                    if library not in library_dataset_actions:
                        library_dataset_actions[library] = {}
                    try:
                        library_dataset_actions[library][folder_path].append(dp.action)
                    except Exception:
                        library_dataset_actions[library][folder_path] = [dp.action]
        else:
            message = "Not showing associated datasets, there are too many."
            status = "info"
        return trans.fill_template(
            "/webapps/tool_shed/admin/dataset_security/role/role.mako",
            role=role,
            in_users=in_users,
            out_users=out_users,
            in_groups=in_groups,
            out_groups=out_groups,
            library_dataset_actions=library_dataset_actions,
            message=message,
            status=status,
        )

    @web.expose
    @web.require_admin
    def mark_role_deleted(self, trans, **kwd):
        id = kwd.get("id", None)
        if not id:
            message = "No role ids received for deleting"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="roles", message=message, status="error")
            )
        ids = util.listify(id)
        message = f"Deleted {len(ids)} roles: "
        for role_id in ids:
            role = get_role(trans, role_id)
            role.deleted = True
            trans.sa_session.add(role)
            trans.sa_session.commit()
            message += f" {role.name} "
        trans.response.send_redirect(
            web.url_for(controller="admin", action="roles", message=util.sanitize_text(message), status="done")
        )

    @web.expose
    @web.require_admin
    def undelete_role(self, trans, **kwd):
        id = kwd.get("id", None)
        if not id:
            message = "No role ids received for undeleting"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="roles", message=message, status="error")
            )
        ids = util.listify(id)
        undeleted_roles = []
        for role_id in ids:
            role = get_role(trans, role_id)
            if not role.deleted:
                message = f"Role '{role.name}' has not been deleted, so it cannot be undeleted."
                trans.response.send_redirect(
                    web.url_for(controller="admin", action="roles", message=util.sanitize_text(message), status="error")
                )
            role.deleted = False
            trans.sa_session.add(role)
            trans.sa_session.commit()
            undeleted_roles.append(role.name)
        message = "Undeleted {} roles: {}".format(len(undeleted_roles), " ".join(undeleted_roles))
        trans.response.send_redirect(
            web.url_for(controller="admin", action="roles", message=util.sanitize_text(message), status="done")
        )

    @web.expose
    @web.require_admin
    def purge_role(self, trans, **kwd):
        # This method should only be called for a Role that has previously been deleted.
        # Purging a deleted Role deletes all of the following from the database:
        # - UserRoleAssociations where role_id == Role.id
        # - DefaultUserPermissions where role_id == Role.id
        # - DefaultHistoryPermissions where role_id == Role.id
        # - GroupRoleAssociations where role_id == Role.id
        # - DatasetPermissionss where role_id == Role.id
        id = kwd.get("id", None)
        if not id:
            message = "No role ids received for purging"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="roles", message=util.sanitize_text(message), status="error")
            )
        ids = util.listify(id)
        message = f"Purged {len(ids)} roles: "
        for role_id in ids:
            role = get_role(trans, role_id)
            if not role.deleted:
                message = f"Role '{role.name}' has not been deleted, so it cannot be purged."
                trans.response.send_redirect(
                    web.url_for(controller="admin", action="roles", message=util.sanitize_text(message), status="error")
                )
            # Delete UserRoleAssociations
            for ura in role.users:
                user = trans.sa_session.get(trans.app.model.User, ura.user_id)
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
            trans.sa_session.commit()
            message += f" {role.name} "
        trans.response.send_redirect(
            web.url_for(controller="admin", action="roles", message=util.sanitize_text(message), status="done")
        )

    @web.expose
    @web.require_admin
    def groups(self, trans, **kwargs):
        if "operation" in kwargs:
            operation = kwargs["operation"].lower().replace("+", " ")
            if operation == "groups":
                return self.group(trans, **kwargs)
            if operation == "create":
                return self.create_group(trans, **kwargs)
            if operation == "delete":
                return self.mark_group_deleted(trans, **kwargs)
            if operation == "undelete":
                return self.undelete_group(trans, **kwargs)
            if operation == "purge":
                return self.purge_group(trans, **kwargs)
            if operation == "manage users and roles":
                return self.manage_users_and_roles_for_group(trans, **kwargs)
            if operation == "rename":
                return self.rename_group(trans, **kwargs)
        # Render the list view
        return self.group_list_grid(trans, **kwargs)

    @web.expose
    @web.require_admin
    def rename_group(self, trans, **kwd):
        params = util.Params(kwd)
        message = util.restore_text(params.get("message", ""))
        status = params.get("status", "done")
        id = params.get("id", None)
        if not id:
            message = "No group ids received for renaming"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="groups", message=message, status="error")
            )
        group = get_group(trans, id)
        if params.get("rename_group_button", False):
            old_name = group.name
            new_name = util.restore_text(params.name)
            if not new_name:
                message = "Enter a valid name"
                status = "error"
            else:
                if get_group_id(trans.sa_session, trans.app.model.Group, new_name) != group.id:
                    message = "A group with that name already exists"
                    status = "error"
                else:
                    if group.name != new_name:
                        group.name = new_name
                        trans.sa_session.add(group)
                        trans.sa_session.commit()
                        message = f"Group '{old_name}' has been renamed to '{new_name}'"
                    return trans.response.send_redirect(
                        web.url_for(
                            controller="admin", action="groups", message=util.sanitize_text(message), status="done"
                        )
                    )
        return trans.fill_template(
            "/webapps/tool_shed/admin/dataset_security/group/group_rename.mako",
            group=group,
            message=message,
            status=status,
        )

    @web.expose
    @web.require_admin
    def manage_users_and_roles_for_group(self, trans, **kwd):
        params = util.Params(kwd)
        message = util.restore_text(params.get("message", ""))
        status = params.get("status", "done")
        group = get_group(trans, params.id)
        if params.get("group_roles_users_edit_button", False):
            in_roles = [trans.sa_session.get(trans.app.model.Role, x) for x in util.listify(params.in_roles)]
            in_users = [trans.sa_session.get(trans.app.model.User, x) for x in util.listify(params.in_users)]
            trans.app.security_agent.set_entity_group_associations(groups=[group], roles=in_roles, users=in_users)
            trans.sa_session.refresh(group)
            message += f"Group '{group.name}' has been updated with {len(in_roles)} associated roles and {len(in_users)} associated users"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="groups", message=util.sanitize_text(message), status=status)
            )
        in_roles = []
        out_roles = []
        in_users = []
        out_users = []
        for role in get_current_roles(trans.sa_session, trans.app.model.Role):
            if role in [x.role for x in group.roles]:
                in_roles.append((role.id, role.name))
            else:
                out_roles.append((role.id, role.name))
        for user in get_current_users(trans.sa_session, trans.app.model.User):
            if user in [x.user for x in group.users]:
                in_users.append((user.id, user.email))
            else:
                out_users.append((user.id, user.email))
        message += f"Group {group.name} is currently associated with {len(in_roles)} roles and {len(in_users)} users"
        return trans.fill_template(
            "/webapps/tool_shed/admin/dataset_security/group/group.mako",
            group=group,
            in_roles=in_roles,
            out_roles=out_roles,
            in_users=in_users,
            out_users=out_users,
            message=message,
            status=status,
        )

    @web.expose
    @web.require_admin
    def create_group(self, trans, **kwd):
        params = util.Params(kwd)
        message = util.restore_text(params.get("message", ""))
        status = params.get("status", "done")
        name = util.restore_text(params.get("name", ""))
        in_users = util.listify(params.get("in_users", []))
        out_users = util.listify(params.get("out_users", []))
        in_roles = util.listify(params.get("in_roles", []))
        out_roles = util.listify(params.get("out_roles", []))
        create_role_for_group = params.get("create_role_for_group", "")
        create_role_for_group_checked = CheckboxField.is_checked(create_role_for_group)
        ok = True
        if params.get("create_group_button", False):
            if not name:
                message = "Enter a valid name."
                status = "error"
                ok = False
            elif get_group_id(trans.sa_session, trans.app.model.Group, name):
                message = (
                    "Group names must be unique and a group with that name already exists, so choose another name."
                )
                status = "error"
                ok = False
            else:
                # Create the group
                group = trans.app.model.Group(name=name)
                trans.sa_session.add(group)
                trans.sa_session.commit()
                # Create the UserRoleAssociations
                for user in [trans.sa_session.get(trans.app.model.User, x) for x in in_users]:
                    uga = trans.app.model.UserGroupAssociation(user, group)
                    trans.sa_session.add(uga)
                # Create the GroupRoleAssociations
                for role in [trans.sa_session.get(trans.app.model.Role, x) for x in in_roles]:
                    gra = trans.app.model.GroupRoleAssociation(group, role)
                    trans.sa_session.add(gra)
                if create_role_for_group_checked:
                    # Create the role
                    role = trans.app.model.Role(name=name, description=f"Role for group {name}")
                    trans.sa_session.add(role)
                    # Associate the role with the group
                    gra = trans.model.GroupRoleAssociation(group, role)
                    trans.sa_session.add(gra)
                    num_in_roles = len(in_roles) + 1
                else:
                    num_in_roles = len(in_roles)
                trans.sa_session.commit()
                message = f"Group '{group.name}' has been created with {len(in_users)} associated users and {num_in_roles} associated roles.  "
                if create_role_for_group_checked:
                    message += (
                        "One of the roles associated with this group is the newly created role with the same name."
                    )
                trans.response.send_redirect(
                    web.url_for(controller="admin", action="groups", message=util.sanitize_text(message), status="done")
                )
        if ok:
            for user in get_current_users(trans.sa_session, trans.app.model.User):
                out_users.append((user.id, user.email))
            for role in get_current_roles(trans.sa_session, trans.app.model.Role):
                out_roles.append((role.id, role.name))
        return trans.fill_template(
            "/webapps/tool_shed/admin/dataset_security/group/group_create.mako",
            name=name,
            in_users=in_users,
            out_users=out_users,
            in_roles=in_roles,
            out_roles=out_roles,
            create_role_for_group_checked=create_role_for_group_checked,
            message=message,
            status=status,
        )

    @web.expose
    @web.require_admin
    def mark_group_deleted(self, trans, **kwd):
        params = util.Params(kwd)
        id = params.get("id", None)
        if not id:
            message = "No group ids received for marking deleted"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="groups", message=message, status="error")
            )
        ids = util.listify(id)
        message = f"Deleted {len(ids)} groups: "
        for group_id in ids:
            group = get_group(trans, group_id)
            group.deleted = True
            trans.sa_session.add(group)
            trans.sa_session.commit()
            message += f" {group.name} "
        trans.response.send_redirect(
            web.url_for(controller="admin", action="groups", message=util.sanitize_text(message), status="done")
        )

    @web.expose
    @web.require_admin
    def undelete_group(self, trans, **kwd):
        id = kwd.get("id", None)
        if not id:
            message = "No group ids received for undeleting"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="groups", message=message, status="error")
            )
        ids = util.listify(id)
        undeleted_groups = []
        for group_id in ids:
            group = get_group(trans, group_id)
            if not group.deleted:
                message = f"Group '{group.name}' has not been deleted, so it cannot be undeleted."
                trans.response.send_redirect(
                    web.url_for(
                        controller="admin", action="groups", message=util.sanitize_text(message), status="error"
                    )
                )
            group.deleted = False
            trans.sa_session.add(group)
            trans.sa_session.commit()
            undeleted_groups.append(group.name)
        message = "Undeleted {} groups: {}".format(len(undeleted_groups), " ".join(undeleted_groups))
        trans.response.send_redirect(
            web.url_for(controller="admin", action="groups", message=util.sanitize_text(message), status="done")
        )

    @web.expose
    @web.require_admin
    def purge_group(self, trans, **kwd):
        # This method should only be called for a Group that has previously been deleted.
        # Purging a deleted Group simply deletes all UserGroupAssociations and GroupRoleAssociations.
        id = kwd.get("id", None)
        if not id:
            message = "No group ids received for purging"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="groups", message=util.sanitize_text(message), status="error")
            )
        ids = util.listify(id)
        message = f"Purged {len(ids)} groups: "
        for group_id in ids:
            group = get_group(trans, group_id)
            if not group.deleted:
                # We should never reach here, but just in case there is a bug somewhere...
                message = f"Group '{group.name}' has not been deleted, so it cannot be purged."
                trans.response.send_redirect(
                    web.url_for(
                        controller="admin", action="groups", message=util.sanitize_text(message), status="error"
                    )
                )
            # Delete UserGroupAssociations
            for uga in group.users:
                trans.sa_session.delete(uga)
            # Delete GroupRoleAssociations
            for gra in group.roles:
                trans.sa_session.delete(gra)
            trans.sa_session.commit()
            message += f" {group.name} "
        trans.response.send_redirect(
            web.url_for(controller="admin", action="groups", message=util.sanitize_text(message), status="done")
        )

    @web.expose
    @web.require_admin
    def create_new_user(self, trans, **kwd):
        return trans.response.send_redirect(web.url_for(controller="user", action="create", cntrller="admin"))

    @web.expose
    @web.require_admin
    def reset_user_password(self, trans, **kwd):
        user_id = kwd.get("id", None)
        if not user_id:
            message = "No users received for resetting passwords."
            trans.response.send_redirect(
                web.url_for(controller="admin", action="users", message=message, status="error")
            )
        user_ids = util.listify(user_id)
        if "reset_user_password_button" in kwd:
            message = ""
            status = ""
            for user_id in user_ids:
                user = get_user(trans, user_id)
                password = kwd.get("password", None)
                confirm = kwd.get("confirm", None)
                message = validate_password(trans, password, confirm)
                if message:
                    status = "error"
                    break
                else:
                    user.set_password_cleartext(password)
                    trans.sa_session.add(user)
                    trans.sa_session.commit()
            if not message and not status:
                message = "Passwords reset for {} {}.".format(
                    len(user_ids), inflector.cond_plural(len(user_ids), "user")
                )
                status = "done"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="users", message=util.sanitize_text(message), status=status)
            )
        users = [get_user(trans, user_id) for user_id in user_ids]
        if len(user_ids) > 1:
            user_id = ",".join(user_ids)
        return trans.fill_template(
            "/webapps/tool_shed/admin/user/reset_password.mako", id=user_id, users=users, password="", confirm=""
        )

    @web.expose
    @web.require_admin
    def mark_user_deleted(self, trans, **kwd):
        id = kwd.get("id", None)
        if not id:
            message = "No user ids received for deleting"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="users", message=message, status="error")
            )
        ids = util.listify(id)
        message = f"Deleted {len(ids)} users: "
        for user_id in ids:
            user = get_user(trans, user_id)
            user.deleted = True

            compliance_log.info(f"delete-user-event: {user_id}")
            # See lib/galaxy/webapps/tool_shed/controllers/admin.py
            pseudorandom_value = str(int(time.time()))
            email_hash = new_secure_hash_v2(user.email + pseudorandom_value)
            uname_hash = new_secure_hash_v2(user.username + pseudorandom_value)
            for role in user.all_roles():
                print(
                    role, self.app.config.redact_username_during_deletion, self.app.config.redact_email_during_deletion
                )
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

            trans.sa_session.add(user)
            trans.sa_session.commit()
            message += f" {user.email} "
        trans.response.send_redirect(
            web.url_for(controller="admin", action="users", message=util.sanitize_text(message), status="done")
        )

    @web.expose
    @web.require_admin
    def undelete_user(self, trans, **kwd):
        id = kwd.get("id", None)
        if not id:
            message = "No user ids received for undeleting"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="users", message=message, status="error")
            )
        ids = util.listify(id)
        undeleted_users = []
        for user_id in ids:
            user = get_user(trans, user_id)
            if not user.deleted:
                message = f"User '{user.email}' has not been deleted, so it cannot be undeleted."
                trans.response.send_redirect(
                    web.url_for(controller="admin", action="users", message=util.sanitize_text(message), status="error")
                )
            user.deleted = False
            trans.sa_session.add(user)
            trans.sa_session.commit()
            undeleted_users.append(user.email)
        message = "Undeleted {} users: {}".format(len(undeleted_users), " ".join(undeleted_users))
        trans.response.send_redirect(
            web.url_for(controller="admin", action="users", message=util.sanitize_text(message), status="done")
        )

    @web.expose
    @web.require_admin
    def purge_user(self, trans, **kwd):
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
        id = kwd.get("id", None)
        if not id:
            message = "No user ids received for purging"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="users", message=util.sanitize_text(message), status="error")
            )
        ids = util.listify(id)
        message = f"Purged {len(ids)} users: "
        for user_id in ids:
            user = get_user(trans, user_id)
            if not user.deleted:
                # We should never reach here, but just in case there is a bug somewhere...
                message = f"User '{user.email}' has not been deleted, so it cannot be purged."
                trans.response.send_redirect(
                    web.url_for(controller="admin", action="users", message=util.sanitize_text(message), status="error")
                )
            private_role = trans.app.security_agent.get_private_user_role(user)
            # Delete History
            for h in user.active_histories:
                trans.sa_session.refresh(h)
                for hda in h.active_datasets:
                    # Delete HistoryDatasetAssociation
                    d = trans.sa_session.get(trans.app.model.Dataset, hda.dataset_id)
                    # Delete Dataset
                    if not d.deleted:
                        d.deleted = True
                        trans.sa_session.add(d)
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
            trans.sa_session.commit()
            message += f"{user.email} "
        trans.response.send_redirect(
            web.url_for(controller="admin", action="users", message=util.sanitize_text(message), status="done")
        )

    @web.expose
    @web.require_admin
    def users(self, trans, **kwd):
        if "operation" in kwd:
            operation = kwd["operation"].lower()
            if operation == "roles":
                return self.user(trans, **kwd)
            elif operation == "reset password":
                return self.reset_user_password(trans, **kwd)
            elif operation == "delete":
                return self.mark_user_deleted(trans, **kwd)
            elif operation == "undelete":
                return self.undelete_user(trans, **kwd)
            elif operation == "purge":
                return self.purge_user(trans, **kwd)
            elif operation == "create":
                return self.create_new_user(trans, **kwd)
            elif operation == "manage roles and groups":
                return self.manage_roles_and_groups_for_user(trans, **kwd)

        if trans.app.config.allow_user_deletion:
            if self.delete_operation not in self.user_list_grid.operations:
                self.user_list_grid.operations.append(self.delete_operation)
            if self.undelete_operation not in self.user_list_grid.operations:
                self.user_list_grid.operations.append(self.undelete_operation)
            if self.purge_operation not in self.user_list_grid.operations:
                self.user_list_grid.operations.append(self.purge_operation)
        # Render the list view
        return self.user_list_grid(trans, **kwd)

    @web.expose
    @web.require_admin
    def name_autocomplete_data(self, trans, q=None, limit=None, timestamp=None):
        """Return autocomplete data for user emails"""
        emails = get_user_emails_by_prefix(trans.sa_session, trans.app.model.User, q)
        return "\n".join(emails)

    @web.expose
    @web.require_admin
    def manage_roles_and_groups_for_user(self, trans, **kwd):
        user_id = kwd.get("id", None)
        message = ""
        status = ""
        if not user_id:
            message += f"Invalid user id ({str(user_id)}) received"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="users", message=util.sanitize_text(message), status="error")
            )
        user = get_user(trans, user_id)
        private_role = trans.app.security_agent.get_private_user_role(user)
        if kwd.get("user_roles_groups_edit_button", False):
            # Make sure the user is not dis-associating himself from his private role
            out_roles = kwd.get("out_roles", [])
            if out_roles:
                out_roles = [trans.sa_session.get(trans.app.model.Role, x) for x in util.listify(out_roles)]
            if private_role in out_roles:
                message += "You cannot eliminate a user's private role association.  "
                status = "error"
            in_roles = kwd.get("in_roles", [])
            if in_roles:
                in_roles = [trans.sa_session.get(trans.app.model.Role, x) for x in util.listify(in_roles)]
            out_groups = kwd.get("out_groups", [])
            if out_groups:
                out_groups = [trans.sa_session.get(trans.app.model.Group, x) for x in util.listify(out_groups)]
            in_groups = kwd.get("in_groups", [])
            if in_groups:
                in_groups = [trans.sa_session.get(trans.app.model.Group, x) for x in util.listify(in_groups)]
            if in_roles:
                trans.app.security_agent.set_entity_user_associations(users=[user], roles=in_roles, groups=in_groups)
                trans.sa_session.refresh(user)
                message += f"User '{user.email}' has been updated with {len(in_roles)} associated roles and {len(in_groups)} associated groups (private roles are not displayed)"
                trans.response.send_redirect(
                    web.url_for(controller="admin", action="users", message=util.sanitize_text(message), status="done")
                )
        in_roles = []
        out_roles = []
        in_groups = []
        out_groups = []
        for role in get_current_roles(trans.sa_session, trans.app.model.Role):
            if role in [x.role for x in user.roles]:
                in_roles.append((role.id, role.name))
            elif role.type != trans.app.model.Role.types.PRIVATE:
                # There is a 1 to 1 mapping between a user and a PRIVATE role, so private roles should
                # not be listed in the roles form fields, except for the currently selected user's private
                # role, which should always be in in_roles.  The check above is added as an additional
                # precaution, since for a period of time we were including private roles in the form fields.
                out_roles.append((role.id, role.name))
        for group in get_current_groups(trans.sa_session, trans.app.model.Group):
            if group in [x.group for x in user.groups]:
                in_groups.append((group.id, group.name))
            else:
                out_groups.append((group.id, group.name))
        message += f"User '{user.email}' is currently associated with {len(in_roles)} roles and is a member of {len(in_groups)} groups"
        if not status:
            status = "done"
        return trans.fill_template(
            "/webapps/tool_shed/admin/user/user.mako",
            user=user,
            in_roles=in_roles,
            out_roles=out_roles,
            in_groups=in_groups,
            out_groups=out_groups,
            message=message,
            status=status,
        )


# ---- Utility methods -------------------------------------------------------


def get_user(trans, user_id):
    """Get a User from the database by id."""
    user = trans.sa_session.get(trans.model.User, trans.security.decode_id(user_id))
    if not user:
        return trans.show_error_message(f"User not found for id ({str(user_id)})")
    return user


def get_role(trans, id):
    """Get a Role from the database by id."""
    # Load user from database
    id = trans.security.decode_id(id)
    role = trans.sa_session.get(trans.model.Role, id)
    if not role:
        return trans.show_error_message(f"Role not found for id ({str(id)})")
    return role


def get_group(trans, id):
    """Get a Group from the database by id."""
    # Load user from database
    id = trans.security.decode_id(id)
    group = trans.sa_session.get(trans.model.Group, id)
    if not group:
        return trans.show_error_message(f"Group not found for id ({str(id)})")
    return group


def get_role_id(session, role_model, name):
    stmt = select(role_model.id).where(role_model.name == name).limit(1)
    return session.scalars(stmt).first()


def get_group_id(session, group_model, name):
    stmt = select(group_model.id).where(group_model.name == name).limit(1)
    return session.scalars(stmt).first()


def get_current_users(session, user_model):
    stmt = select(user_model).where(user_model.deleted == false()).order_by(user_model.email)
    return session.scalars(stmt)


def get_current_groups(session, group_model):
    stmt = select(group_model).where(group_model.deleted == false()).order_by(group_model.name)
    return session.scalars(stmt)


def get_current_roles(session, role_model):
    stmt = select(role_model).where(role_model.deleted == false()).order_by(role_model.name)
    return session.scalars(stmt)


def get_ldda_by_dataset(session, dataset_id):
    stmt = select(LibraryDatasetDatasetAssociation).where(LibraryDatasetDatasetAssociation.dataset_id == dataset_id)
    return session.scalars(stmt)


def get_library_by_folder(session, folder_id):
    stmt = select(Library).where(Library.folder_id == folder_id).limit(1)
    return session.scalars(stmt).first()


def get_user_emails_by_prefix(session, user_model, prefix):
    stmt = (
        select(user_model.email)
        .where(user_model.deleted == false())
        .where(func.lower(user_model.email).like(f"{prefix.lower()}%"))
    )
    return session.scalars(stmt)
