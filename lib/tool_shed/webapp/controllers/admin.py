import logging

import tool_shed.grids.admin_grids as admin_grids
from galaxy import (
    util,
    web,
)
from galaxy.util import inflector
from galaxy.web.legacy_framework import grids
from galaxy.webapps.base.controller import BaseUIController
from tool_shed.metadata import repository_metadata_manager
from tool_shed.util import (
    metadata_util,
    repository_util,
)
from tool_shed.util import shed_util_common as suc
from tool_shed.util.admin_util import Admin
from tool_shed.util.web_util import escape

log = logging.getLogger(__name__)


class AdminController(BaseUIController, Admin):

    user_list_grid = admin_grids.UserGrid()
    role_list_grid = admin_grids.RoleGrid()
    group_list_grid = admin_grids.GroupGrid()
    manage_category_grid = admin_grids.ManageCategoryGrid()
    repository_grid = admin_grids.AdminRepositoryGrid()
    repository_metadata_grid = admin_grids.RepositoryMetadataGrid()

    delete_operation = grids.GridOperation("Delete", condition=(lambda item: not item.deleted), allow_multiple=True)
    undelete_operation = grids.GridOperation(
        "Undelete", condition=(lambda item: item.deleted and not item.purged), allow_multiple=True
    )
    purge_operation = grids.GridOperation(
        "Purge", condition=(lambda item: item.deleted and not item.purged), allow_multiple=True
    )

    @web.expose
    @web.require_admin
    def browse_repositories(self, trans, **kwd):
        # We add parameters to the keyword dict in this method in order to rename the param
        # with an "f-" prefix, simulating filtering by clicking a search link.  We have
        # to take this approach because the "-" character is illegal in HTTP requests.
        if "operation" in kwd:
            operation = kwd["operation"].lower()
            if operation == "view_or_manage_repository":
                return trans.response.send_redirect(
                    web.url_for(controller="repository", action="browse_repositories", **kwd)
                )
            elif operation == "edit_repository":
                return trans.response.send_redirect(
                    web.url_for(controller="repository", action="edit_repository", **kwd)
                )
            elif operation == "repositories_by_user":
                # Eliminate the current filters if any exist.
                for k in list(kwd.keys()):
                    if k.startswith("f-"):
                        del kwd[k]
                if "user_id" in kwd:
                    user = suc.get_user(trans.app, kwd["user_id"])
                    kwd["f-email"] = user.email
                    del kwd["user_id"]
                else:
                    # The received id is the repository id, so we need to get the id of the user
                    # that uploaded the repository.
                    repository_id = kwd.get("id", None)
                    repository = repository_util.get_repository_in_tool_shed(trans.app, repository_id)
                    kwd["f-email"] = repository.user.email
            elif operation == "repositories_by_category":
                # Eliminate the current filters if any exist.
                for k in list(kwd.keys()):
                    if k.startswith("f-"):
                        del kwd[k]
                category_id = kwd.get("id", None)
                category = suc.get_category(trans.app, category_id)
                kwd["f-Category.name"] = category.name
            elif operation == "receive email alerts":
                if kwd["id"]:
                    kwd["caller"] = "browse_repositories"
                    return trans.response.send_redirect(
                        web.url_for(controller="repository", action="set_email_alerts", **kwd)
                    )
                else:
                    del kwd["operation"]
            elif operation == "delete":
                return self.delete_repository(trans, **kwd)
            elif operation == "undelete":
                return self.undelete_repository(trans, **kwd)
        # The changeset_revision_select_field in the RepositoryGrid performs a refresh_on_change
        # which sends in request parameters like changeset_revison_1, changeset_revision_2, etc.  One
        # of the many select fields on the grid performed the refresh_on_change, so we loop through
        # all of the received values to see which value is not the repository tip.  If we find it, we
        # know the refresh_on_change occurred, and we have the necessary repository id and change set
        # revision to pass on.
        for k, v in kwd.items():
            changeset_revision_str = "changeset_revision_"
            if k.startswith(changeset_revision_str):
                repository_id = trans.security.encode_id(int(k.lstrip(changeset_revision_str)))
                repository = repository_util.get_repository_in_tool_shed(trans.app, repository_id)
                if repository.tip() != v:
                    return trans.response.send_redirect(
                        web.url_for(
                            controller="repository",
                            action="browse_repositories",
                            operation="view_or_manage_repository",
                            id=trans.security.encode_id(repository.id),
                            changeset_revision=v,
                        )
                    )
        # Render the list view
        return self.repository_grid(trans, **kwd)

    @web.expose
    @web.require_admin
    def browse_repository_metadata(self, trans, **kwd):
        if "operation" in kwd:
            operation = kwd["operation"].lower()
            if operation == "delete":
                return self.delete_repository_metadata(trans, **kwd)
            if operation == "view_or_manage_repository_revision":
                # The received id is a RepositoryMetadata object id, so we need to get the
                # associated Repository and redirect to view_or_manage_repository with the
                # changeset_revision.
                repository_metadata = metadata_util.get_repository_metadata_by_id(trans.app, kwd["id"])
                repository = repository_metadata.repository
                kwd["id"] = trans.security.encode_id(repository.id)
                kwd["changeset_revision"] = repository_metadata.changeset_revision
                kwd["operation"] = "view_or_manage_repository"
                return trans.response.send_redirect(
                    web.url_for(controller="repository", action="browse_repositories", **kwd)
                )
        return self.repository_metadata_grid(trans, **kwd)

    @web.expose
    @web.require_admin
    def create_category(self, trans, **kwd):
        message = escape(kwd.get("message", ""))
        status = kwd.get("status", "done")
        name = kwd.get("name", "").strip()
        description = kwd.get("description", "").strip()
        if kwd.get("create_category_button", False):
            if not name or not description:
                message = "Enter a valid name and a description"
                status = "error"
            elif suc.get_category_by_name(trans.app, name):
                message = "A category with that name already exists"
                status = "error"
            else:
                # Create the category
                category = trans.app.model.Category(name=name, description=description)
                trans.sa_session.add(category)
                trans.sa_session.flush()
                # Update the Tool Shed's repository registry.
                trans.app.repository_registry.add_category_entry(category)
                message = f"Category '{escape(category.name)}' has been created"
                status = "done"
                trans.response.send_redirect(
                    web.url_for(controller="admin", action="manage_categories", message=message, status=status)
                )
        return trans.fill_template(
            "/webapps/tool_shed/category/create_category.mako",
            name=name,
            description=description,
            message=message,
            status=status,
        )

    @web.expose
    @web.require_admin
    def delete_repository(self, trans, **kwd):
        message = escape(kwd.get("message", ""))
        status = kwd.get("status", "done")
        id = kwd.get("id", None)
        if id:
            # Deleting multiple items is currently not allowed (allow_multiple=False), so there will only be 1 id.
            ids = util.listify(id)
            count = 0
            deleted_repositories = ""
            for repository_id in ids:
                repository = repository_util.get_repository_in_tool_shed(trans.app, repository_id)
                if repository:
                    if not repository.deleted:
                        # Mark all installable repository_metadata records as not installable.
                        for repository_metadata in repository.downloadable_revisions:
                            repository_metadata.downloadable = False
                            trans.sa_session.add(repository_metadata)
                        # Mark the repository admin role as deleted.
                        repository_admin_role = repository.admin_role
                        if repository_admin_role is not None:
                            repository_admin_role.deleted = True
                            trans.sa_session.add(repository_admin_role)
                        repository.deleted = True
                        trans.sa_session.add(repository)
                        trans.sa_session.flush()
                        # Update the repository registry.
                        trans.app.repository_registry.remove_entry(repository)
                        count += 1
                        deleted_repositories += f" {repository.name} "
            if count:
                message = "Deleted %d %s: %s" % (
                    count,
                    inflector.cond_plural(len(ids), "repository"),
                    escape(deleted_repositories),
                )
            else:
                message = "All selected repositories were already marked deleted."
        else:
            message = "No repository ids received for deleting."
            status = "error"
        trans.response.send_redirect(
            web.url_for(
                controller="admin", action="browse_repositories", message=util.sanitize_text(message), status=status
            )
        )

    @web.expose
    @web.require_admin
    def delete_repository_metadata(self, trans, **kwd):
        message = escape(kwd.get("message", ""))
        status = kwd.get("status", "done")
        id = kwd.get("id", None)
        if id:
            ids = util.listify(id)
            count = 0
            for repository_metadata_id in ids:
                repository_metadata = metadata_util.get_repository_metadata_by_id(trans.app, repository_metadata_id)
                trans.sa_session.delete(repository_metadata)
                trans.sa_session.flush()
                count += 1
            if count:
                message = "Deleted %d repository metadata %s" % (count, inflector.cond_plural(len(ids), "record"))
        else:
            message = "No repository metadata ids received for deleting."
            status = "error"
        trans.response.send_redirect(
            web.url_for(
                controller="admin",
                action="browse_repository_metadata",
                message=util.sanitize_text(message),
                status=status,
            )
        )

    @web.expose
    @web.require_admin
    def edit_category(self, trans, **kwd):
        """Handle requests to edit TS category name or description"""
        message = escape(kwd.get("message", ""))
        status = kwd.get("status", "done")
        id = kwd.get("id", None)
        if not id:
            message = "No category ids received for editing"
            trans.response.send_redirect(
                web.url_for(controller="admin", action="manage_categories", message=message, status="error")
            )
        category = suc.get_category(trans.app, id)
        original_category_name = str(category.name)
        original_category_description = str(category.description)
        if kwd.get("edit_category_button", False):
            flush_needed = False
            new_name = kwd.get("name", "").strip()
            new_description = kwd.get("description", "").strip()
            if original_category_name != new_name:
                if not new_name:
                    message = "Enter a valid name"
                    status = "error"
                elif original_category_name != new_name and suc.get_category_by_name(trans.app, new_name):
                    message = "A category with that name already exists"
                    status = "error"
                else:
                    category.name = new_name
                    flush_needed = True
            if original_category_description != new_description:
                category.description = new_description
                if not flush_needed:
                    flush_needed = True
            if flush_needed:
                trans.sa_session.add(category)
                trans.sa_session.flush()
                if original_category_name != new_name:
                    # Update the Tool Shed's repository registry.
                    trans.app.repository_registry.edit_category_entry(original_category_name, new_name)
                message = f"The information has been saved for category '{escape(category.name)}'"
                status = "done"
                return trans.response.send_redirect(
                    web.url_for(controller="admin", action="manage_categories", message=message, status=status)
                )
        return trans.fill_template(
            "/webapps/tool_shed/category/edit_category.mako", category=category, message=message, status=status
        )

    @web.expose
    @web.require_admin
    def manage_categories(self, trans, **kwd):
        if "f-free-text-search" in kwd:
            # Trick to enable searching repository name, description from the CategoryGrid.
            # What we've done is rendered the search box for the RepositoryGrid on the grid.mako
            # template for the CategoryGrid.  See ~/templates/webapps/tool_shed/category/grid.mako.
            # Since we are searching repositories and not categories, redirect to browse_repositories().
            return trans.response.send_redirect(web.url_for(controller="admin", action="browse_repositories", **kwd))
        if "operation" in kwd:
            operation = kwd["operation"].lower()
            if operation == "create":
                return trans.response.send_redirect(web.url_for(controller="admin", action="create_category", **kwd))
            elif operation == "delete":
                return trans.response.send_redirect(
                    web.url_for(controller="admin", action="mark_category_deleted", **kwd)
                )
            elif operation == "undelete":
                return trans.response.send_redirect(web.url_for(controller="admin", action="undelete_category", **kwd))
            elif operation == "purge":
                return trans.response.send_redirect(web.url_for(controller="admin", action="purge_category", **kwd))
            elif operation == "edit":
                return trans.response.send_redirect(web.url_for(controller="admin", action="edit_category", **kwd))
        return self.manage_category_grid(trans, **kwd)

    @web.expose
    @web.require_admin
    def regenerate_statistics(self, trans, **kwd):
        message = escape(kwd.get("message", ""))
        status = kwd.get("status", "done")
        if "regenerate_statistics_button" in kwd:
            trans.app.shed_counter.generate_statistics()
            message = "Successfully regenerated statistics"
        return trans.fill_template("/webapps/tool_shed/admin/statistics.mako", message=message, status=status)

    @web.expose
    @web.require_admin
    def manage_role_associations(self, trans, **kwd):
        """Manage users, groups and repositories associated with a role."""
        role_id = kwd.get("id", None)
        role = repository_util.get_role_by_id(trans.app, role_id)
        # We currently only have a single role associated with a repository, the repository admin role.
        repository_role_association = role.repositories[0]
        repository = repository_role_association.repository
        associations_dict = repository_util.handle_role_associations(trans.app, role, repository, **kwd)
        in_users = associations_dict.get("in_users", [])
        out_users = associations_dict.get("out_users", [])
        in_groups = associations_dict.get("in_groups", [])
        out_groups = associations_dict.get("out_groups", [])
        message = associations_dict.get("message", "")
        status = associations_dict.get("status", "done")
        return trans.fill_template(
            "/webapps/tool_shed/role/role.mako",
            in_admin_controller=True,
            repository=repository,
            role=role,
            in_users=in_users,
            out_users=out_users,
            in_groups=in_groups,
            out_groups=out_groups,
            message=message,
            status=status,
        )

    @web.expose
    @web.require_admin
    def reset_metadata_on_selected_repositories_in_tool_shed(self, trans, **kwd):
        rmm = repository_metadata_manager.RepositoryMetadataManager(trans.app, trans.user)
        if "reset_metadata_on_selected_repositories_button" in kwd:
            message, status = rmm.reset_metadata_on_selected_repositories(**kwd)
        else:
            message = escape(util.restore_text(kwd.get("message", "")))
            status = kwd.get("status", "done")
        repositories_select_field = rmm.build_repository_ids_select_field(
            name="repository_ids", multiple=True, display="checkboxes", my_writable=False
        )
        return trans.fill_template(
            "/webapps/tool_shed/common/reset_metadata_on_selected_repositories.mako",
            repositories_select_field=repositories_select_field,
            message=message,
            status=status,
        )

    @web.expose
    @web.require_admin
    def undelete_repository(self, trans, **kwd):
        message = escape(kwd.get("message", ""))
        id = kwd.get("id", None)
        if id:
            # Undeleting multiple items is currently not allowed (allow_multiple=False), so there will only be 1 id.
            ids = util.listify(id)
            count = 0
            undeleted_repositories = ""
            for repository_id in ids:
                repository = repository_util.get_repository_in_tool_shed(trans.app, repository_id)
                if repository:
                    if repository.deleted:
                        # Inspect all repository_metadata records to determine those that are installable, and mark
                        # them accordingly.
                        for repository_metadata in repository.metadata_revisions:
                            metadata = repository_metadata.metadata
                            if metadata:
                                if metadata_util.is_downloadable(metadata):
                                    repository_metadata.downloadable = True
                                    trans.sa_session.add(repository_metadata)
                        # Mark the repository admin role as not deleted.
                        repository_admin_role = repository.admin_role
                        if repository_admin_role is not None:
                            repository_admin_role.deleted = False
                            trans.sa_session.add(repository_admin_role)
                        repository.deleted = False
                        trans.sa_session.add(repository)
                        trans.sa_session.flush()
                        if not repository.deprecated:
                            # Update the repository registry.
                            trans.app.repository_registry.add_entry(repository)
                        count += 1
                        undeleted_repositories += f" {repository.name}"
            if count:
                message = "Undeleted %d %s: %s" % (
                    count,
                    inflector.cond_plural(count, "repository"),
                    undeleted_repositories,
                )
            else:
                message = "No selected repositories were marked deleted, so they could not be undeleted."
        else:
            message = "No repository ids received for undeleting."
        trans.response.send_redirect(
            web.url_for(
                controller="admin", action="browse_repositories", message=util.sanitize_text(message), status="done"
            )
        )

    @web.expose
    @web.require_admin
    def mark_category_deleted(self, trans, **kwd):
        # TODO: We should probably eliminate the Category.deleted column since it really makes no
        # sense to mark a category as deleted (category names and descriptions can be changed instead).
        # If we do this, and the following 2 methods can be eliminated.
        message = escape(kwd.get("message", ""))
        id = kwd.get("id", None)
        if id:
            ids = util.listify(id)
            message = "Deleted %d categories: " % len(ids)
            for category_id in ids:
                category = suc.get_category(trans.app, category_id)
                category.deleted = True
                trans.sa_session.add(category)
                trans.sa_session.flush()
                # Update the Tool Shed's repository registry.
                trans.app.repository_registry.remove_category_entry(category)
                message += f" {escape(category.name)} "
        else:
            message = "No category ids received for deleting."
        trans.response.send_redirect(
            web.url_for(
                controller="admin", action="manage_categories", message=util.sanitize_text(message), status="done"
            )
        )

    @web.expose
    @web.require_admin
    def purge_category(self, trans, **kwd):
        # This method should only be called for a Category that has previously been deleted.
        # Purging a deleted Category deletes all of the following from the database:
        # - RepoitoryCategoryAssociations where category_id == Category.id
        message = escape(kwd.get("message", ""))
        id = kwd.get("id", None)
        if id:
            ids = util.listify(id)
            count = 0
            purged_categories = ""
            message = "Purged %d categories: " % len(ids)
            for category_id in ids:
                category = suc.get_category(trans.app, category_id)
                if category.deleted:
                    # Delete RepositoryCategoryAssociations
                    for rca in category.repositories:
                        trans.sa_session.delete(rca)
                    trans.sa_session.flush()
                    purged_categories += f" {category.name} "
            message = "Purged %d categories: %s" % (count, escape(purged_categories))
        else:
            message = "No category ids received for purging."
        trans.response.send_redirect(
            web.url_for(
                controller="admin", action="manage_categories", message=util.sanitize_text(message), status="done"
            )
        )

    @web.expose
    @web.require_admin
    def undelete_category(self, trans, **kwd):
        message = escape(kwd.get("message", ""))
        id = kwd.get("id", None)
        if id:
            ids = util.listify(id)
            count = 0
            undeleted_categories = ""
            for category_id in ids:
                category = suc.get_category(trans.app, category_id)
                if category.deleted:
                    category.deleted = False
                    trans.sa_session.add(category)
                    trans.sa_session.flush()
                    # Update the Tool Shed's repository registry.
                    trans.app.repository_registry.add_category_entry(category)
                    count += 1
                    undeleted_categories += f" {category.name}"
            message = "Undeleted %d categories: %s" % (count, escape(undeleted_categories))
        else:
            message = "No category ids received for undeleting."
        trans.response.send_redirect(
            web.url_for(
                controller="admin", action="manage_categories", message=util.sanitize_text(message), status="done"
            )
        )
