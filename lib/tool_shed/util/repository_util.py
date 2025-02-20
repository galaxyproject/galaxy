import configparser
import logging
import os
import re
import tempfile
from typing import (
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
)

from markupsafe import escape
from sqlalchemy import (
    delete,
    false,
    select,
)
from sqlalchemy.orm import joinedload

import tool_shed.dependencies.repository
from galaxy import (
    util,
    web,
)
from galaxy.tool_shed.util.repository_util import (
    create_or_update_tool_shed_repository,
    extract_components_from_tuple,
    generate_tool_shed_repository_install_dir,
    get_absolute_path_to_file_in_repository,
    get_installed_repository,
    get_installed_tool_shed_repository,
    get_prior_import_or_install_required_dict,
    get_repo_info_tuple_contents,
    get_repository_admin_role_name,
    get_repository_and_repository_dependencies_from_repo_info_dict,
    get_repository_by_id,
    get_repository_by_name,
    get_repository_by_name_and_owner,
    get_repository_dependency_types,
    get_repository_for_dependency_relationship,
    get_repository_ids_requiring_prior_import_or_install,
    get_repository_owner,
    get_repository_owner_from_clone_url,
    get_repository_query,
    get_role_by_id,
    get_tool_shed_from_clone_url,
    get_tool_shed_repository_by_id,
    get_tool_shed_status_for_installed_repository,
    is_tool_shed_client,
    repository_was_previously_installed,
    set_repository_attributes,
)
from tool_shed.util.common_util import generate_clone_url_for
from tool_shed.util.hg_util import (
    changeset2rev,
    create_hgrc_file,
    get_hgrc_path,
    init_repository,
)
from tool_shed.util.metadata_util import (
    get_next_downloadable_changeset_revision,
    get_repository_metadata_by_changeset_revision,
    repository_metadata_by_changeset_revision,
)

if TYPE_CHECKING:
    from tool_shed.context import (
        ProvidesRepositoriesContext,
        ProvidesUserContext,
    )
    from tool_shed.structured_app import ToolShedApp
    from tool_shed.webapp.model import Repository


log = logging.getLogger(__name__)

VALID_REPOSITORYNAME_RE = re.compile(r"^[a-z0-9\_]+$")


def create_repo_info_dict(
    app: "ToolShedApp",
    repository_clone_url,
    changeset_revision,
    ctx_rev,
    repository_owner,
    repository_name=None,
    repository=None,
    repository_metadata=None,
    tool_dependencies=None,
    repository_dependencies=None,
    trans=None,
):
    """
    Return a dictionary that includes all of the information needed to install a repository into a local
    Galaxy instance.  The dictionary will also contain the recursive list of repository dependencies defined
    for the repository, as well as the defined tool dependencies.

    This method is called from Galaxy under four scenarios:
    1. During the tool shed repository installation process via the tool shed's get_repository_information()
    method.  In this case both the received repository and repository_metadata will be objects, but
    tool_dependencies and repository_dependencies will be None.
    2. When getting updates for an installed repository where the updates include newly defined repository
    dependency definitions.  This scenario is similar to 1. above. The tool shed's get_repository_information()
    method is the caller, and both the received repository and repository_metadata will be objects, but
    tool_dependencies and repository_dependencies will be None.
    3. When a tool shed repository that was uninstalled from a Galaxy instance is being reinstalled with no
    updates available.  In this case, both repository and repository_metadata will be None, but tool_dependencies
    and repository_dependencies will be objects previously retrieved from the tool shed if the repository includes
    definitions for them.
    4. When a tool shed repository that was uninstalled from a Galaxy instance is being reinstalled with updates
    available.  In this case, this method is reached via the tool shed's get_updated_repository_information()
    method, and both repository and repository_metadata will be objects but tool_dependencies and
    repository_dependencies will be None.
    """
    repo_info_dict = {}
    repository = get_repository_by_name_and_owner(app, repository_name, repository_owner)
    if app.name == "tool_shed":
        # We're in the tool shed.
        repository_metadata = repository_metadata_by_changeset_revision(app.model, repository.id, changeset_revision)
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                if trans is not None:
                    tool_shed_url = trans.repositories_hostname
                else:
                    tool_shed_url = web.url_for("/", qualified=True).rstrip("/")
                rb = tool_shed.dependencies.repository.relation_builder.RelationBuilder(
                    app, repository, repository_metadata, tool_shed_url, trans=trans
                )
                # Get a dictionary of all repositories upon which the contents of the received repository depends.
                repository_dependencies = rb.get_repository_dependencies_for_changeset_revision()
                tool_dependencies = metadata.get("tool_dependencies", {})
    if tool_dependencies:
        new_tool_dependencies = {}
        for dependency_key, requirements_dict in tool_dependencies.items():
            if dependency_key in ["set_environment"]:
                new_set_environment_dict_list = []
                for set_environment_dict in requirements_dict:
                    set_environment_dict["repository_name"] = repository_name
                    set_environment_dict["repository_owner"] = repository_owner
                    set_environment_dict["changeset_revision"] = changeset_revision
                    new_set_environment_dict_list.append(set_environment_dict)
                new_tool_dependencies[dependency_key] = new_set_environment_dict_list
            else:
                requirements_dict["repository_name"] = repository_name
                requirements_dict["repository_owner"] = repository_owner
                requirements_dict["changeset_revision"] = changeset_revision
                new_tool_dependencies[dependency_key] = requirements_dict
        tool_dependencies = new_tool_dependencies
    repo_info_dict[repository.name] = (
        repository.description,
        repository_clone_url,
        changeset_revision,
        ctx_rev,
        repository_owner,
        repository_dependencies,
        tool_dependencies,
    )
    return repo_info_dict


def create_repository_admin_role(app: "ToolShedApp", repository: "Repository"):
    """
    Create a new role with name-spaced name based on the repository name and its owner's public user
    name.  This will ensure that the role name is unique.
    """
    sa_session = app.model.session
    name = get_repository_admin_role_name(str(repository.name), str(repository.user.username))
    description = "A user or group member with this role can administer this repository."
    role = app.model.Role(name=name, description=description, type=app.model.Role.types.SYSTEM)
    sa_session.add(role)
    # Associate the role with the repository owner.
    app.model.UserRoleAssociation(repository.user, role)
    # Associate the role with the repository.
    rra = app.model.RepositoryRoleAssociation(repository, role)
    sa_session.add(rra)
    return role


def create_repository(
    app: "ToolShedApp",
    name: str,
    type: str,
    description,
    long_description,
    user,
    category_ids: Optional[List[str]] = None,
    remote_repository_url=None,
    homepage_url=None,
) -> Tuple["Repository", str]:
    """Create a new ToolShed repository"""
    category_ids = category_ids or []
    sa_session = app.model.session
    # Add the repository record to the database.
    repository = app.model.Repository(
        name=name,
        type=type,
        remote_repository_url=remote_repository_url,
        homepage_url=homepage_url,
        description=description,
        long_description=long_description,
        user=user,
    )
    sa_session.add(repository)
    if category_ids:
        # Create category associations
        for category_id in category_ids:
            category = sa_session.get(app.model.Category, app.security.decode_id(category_id))
            rca = app.model.RepositoryCategoryAssociation(repository, category)
            sa_session.add(rca)
    # Create an admin role for the repository.
    create_repository_admin_role(app, repository)
    # Create a temporary repo_path on disk.
    repository_path = tempfile.mkdtemp(
        dir=app.config.file_path,
        prefix=f"{repository.user.username}-{repository.name}",
    )
    # Created directory is readable, writable, and searchable only by the creating user ID,
    # but we need to make it world-readable so non-shed user can serve files (e.g. hgweb run as different user).
    os.chmod(repository_path, util.RWXR_XR_X)
    # Create the local repository.
    init_repository(repo_path=repository_path)
    # Create a .hg/hgrc file for the local repository.
    create_hgrc_file(app, repository, repo_path=repository_path)
    # Add an entry in the hgweb.config file for the local repository.
    lhs = f"{app.config.hgweb_repo_prefix}{repository.user.username}/{repository.name}"
    # Flush to get the id.
    session = sa_session()
    session.commit()
    final_repository_path = repository.ensure_hg_repository_path(app.config.file_path)
    os.rename(repository_path, final_repository_path)
    app.hgweb_config_manager.add_entry(lhs, final_repository_path)
    # Update the repository registry.
    app.repository_registry.add_entry(repository)
    message = f"Repository <b>{escape(str(repository.name))}</b> has been created."
    return repository, message


def generate_sharable_link_for_repository_in_tool_shed(
    repository: "Repository", changeset_revision: Optional[str] = None
) -> str:
    """Generate the URL for sharing a repository that is in the tool shed."""
    base_url = web.url_for("/", qualified=True).rstrip("/")
    sharable_url = f"{base_url}/view/{repository.user.username}/{repository.name}"
    if changeset_revision:
        sharable_url += f"/{changeset_revision}"
    return sharable_url


def get_repository_in_tool_shed(app, id, eagerload_columns=None):
    """Get a repository on the tool shed side from the database via id."""
    q = get_repository_query(app)
    if eagerload_columns:
        q = q.options(joinedload(*eagerload_columns))
    return q.get(app.security.decode_id(id))


def get_repo_info_dict(trans: "ProvidesRepositoriesContext", repository_id, changeset_revision):
    app = trans.app
    repository = get_repository_in_tool_shed(app, repository_id)
    repository_clone_url = generate_clone_url_for(trans, repository)
    repository_metadata = get_repository_metadata_by_changeset_revision(app, repository_id, changeset_revision)
    if not repository_metadata:
        # The received changeset_revision is no longer installable, so get the next changeset_revision
        # in the repository's changelog.  This generally occurs only with repositories of type
        # repository_suite_definition or tool_dependency_definition.
        next_downloadable_changeset_revision = get_next_downloadable_changeset_revision(
            app, repository, changeset_revision
        )
        if next_downloadable_changeset_revision and next_downloadable_changeset_revision != changeset_revision:
            repository_metadata = get_repository_metadata_by_changeset_revision(
                app, repository_id, next_downloadable_changeset_revision
            )
    if repository_metadata:
        # For now, we'll always assume that we'll get repository_metadata, but if we discover our assumption
        # is not valid we'll have to enhance the callers to handle repository_metadata values of None in the
        # returned repo_info_dict.
        metadata = repository_metadata.metadata
        if "tools" in metadata:
            includes_tools = True
        else:
            includes_tools = False
        includes_tools_for_display_in_tool_panel = repository_metadata.includes_tools_for_display_in_tool_panel
        repository_dependencies_dict = metadata.get("repository_dependencies", {})
        repository_dependencies = repository_dependencies_dict.get("repository_dependencies", [])
        (
            has_repository_dependencies,
            has_repository_dependencies_only_if_compiling_contained_td,
        ) = get_repository_dependency_types(repository_dependencies)
        if "tool_dependencies" in metadata:
            includes_tool_dependencies = True
        else:
            includes_tool_dependencies = False
    else:
        # Here's where we may have to handle enhancements to the callers. See above comment.
        includes_tools = False
        has_repository_dependencies = False
        has_repository_dependencies_only_if_compiling_contained_td = False
        includes_tool_dependencies = False
        includes_tools_for_display_in_tool_panel = False
    repo_path = repository.repo_path(app)
    ctx_rev = str(changeset2rev(repo_path, changeset_revision))
    repo_info_dict = create_repo_info_dict(
        app=app,
        repository_clone_url=repository_clone_url,
        changeset_revision=changeset_revision,
        ctx_rev=ctx_rev,
        repository_owner=repository.user.username,
        repository_name=repository.name,
        repository=repository,
        repository_metadata=repository_metadata,
        tool_dependencies=None,
        repository_dependencies=None,
        trans=trans,
    )
    return (
        repo_info_dict,
        includes_tools,
        includes_tool_dependencies,
        includes_tools_for_display_in_tool_panel,
        has_repository_dependencies,
        has_repository_dependencies_only_if_compiling_contained_td,
    )


def get_repositories_by_category(
    app: "ToolShedApp", category_id, installable=False, sort_order="asc", sort_key="name", page=None, per_page=25
):
    repositories = []
    for repository in get_repositories(
        app.model.session,
        app.model.Repository,
        app.model.RepositoryCategoryAssociation,
        app.model.User,
        app.model.RepositoryMetadata,
        category_id,
        installable,
        sort_order,
        sort_key,
        page,
        per_page,
    ):
        default_value_mapper = {
            "id": app.security.encode_id,
            "user_id": app.security.encode_id,
            "repository_id": app.security.encode_id,
        }
        repository_dict = repository.to_dict(value_mapper=default_value_mapper)
        repository_dict["metadata"] = {}
        for changeset, changehash in repository.installable_revisions(app):
            metadata = repository_metadata_by_changeset_revision(app.model, repository.id, changehash)
            assert metadata
            repository_dict["metadata"][f"{changeset}:{changehash}"] = metadata.to_dict(
                value_mapper=default_value_mapper
            )
        if installable:
            if len(repository.installable_revisions(app)):
                repositories.append(repository_dict)
        else:
            repositories.append(repository_dict)
    return repositories


def handle_role_associations(app: "ToolShedApp", role, repository, **kwd):
    sa_session = app.model.session
    message = escape(kwd.get("message", ""))
    status = kwd.get("status", "done")
    repository_owner = repository.user
    if kwd.get("manage_role_associations_button", False):
        in_users_list = util.listify(kwd.get("in_users", []))
        in_users = [sa_session.get(app.model.User, x) for x in in_users_list]
        # Make sure the repository owner is always associated with the repostory's admin role.
        owner_associated = False
        for user in in_users:
            if user.id == repository_owner.id:
                owner_associated = True
                break
        if not owner_associated:
            in_users.append(repository_owner)
            message += "The repository owner must always be associated with the repository's administrator role.  "
            status = "error"
        in_groups_list = util.listify(kwd.get("in_groups", []))
        in_groups = [sa_session.get(app.model.Group, x) for x in in_groups_list]
        in_repositories = [repository]
        app.security_agent.set_entity_role_associations(
            roles=[role], users=in_users, groups=in_groups, repositories=in_repositories
        )
        sa_session.refresh(role)
        message += f"Role <b>{escape(str(role.name))}</b> has been associated with {len(in_users)} users, {len(in_groups)} groups and {len(in_repositories)} repositories.  "
    in_users = []
    out_users = []
    in_groups = []
    out_groups = []
    for user in get_current_users(sa_session, app.model.User):
        if user in [x.user for x in role.users]:
            in_users.append((user.id, user.email))
        else:
            out_users.append((user.id, user.email))
    for group in get_current_groups(sa_session, app.model.Group):
        if group in [x.group for x in role.groups]:
            in_groups.append((group.id, group.name))
        else:
            out_groups.append((group.id, group.name))
    associations_dict = dict(
        in_users=in_users,
        out_users=out_users,
        in_groups=in_groups,
        out_groups=out_groups,
        message=message,
        status=status,
    )
    return associations_dict


def change_repository_name_in_hgrc_file(hgrc_file: str, new_name: str) -> None:
    config = configparser.ConfigParser()
    config.read(hgrc_file)
    config.set("web", "name", new_name)
    with open(hgrc_file, "w") as fh:
        config.write(fh)


def update_repository(trans: "ProvidesUserContext", id: str, **kwds) -> Tuple[Optional["Repository"], Optional[str]]:
    """Update an existing ToolShed repository"""
    app = trans.app
    sa_session = app.model.session
    repository = sa_session.get(app.model.Repository, app.security.decode_id(id))
    if repository is None:
        return None, "Unknown repository ID"

    if not (trans.user_is_admin or app.security_agent.user_can_administer_repository(trans.user, repository)):
        message = "You are not the owner of this repository, so you cannot administer it."
        return None, message

    return update_validated_repository(trans, repository, **kwds)


def update_validated_repository(
    trans: "ProvidesUserContext", repository: "Repository", **kwds
) -> Tuple[Optional["Repository"], Optional[str]]:
    """Update an existing ToolShed repository metadata once permissions have been checked."""
    app = trans.app
    sa_session = app.model.session
    message = None
    flush_needed = False

    # Allowlist properties that can be changed via this method
    for key in ("type", "description", "long_description", "remote_repository_url", "homepage_url"):
        # If that key is available, not None and different than what's in the model
        if key in kwds and kwds[key] is not None and kwds[key] != getattr(repository, key):
            setattr(repository, key, kwds[key])
            flush_needed = True

    if "category_ids" in kwds and isinstance(kwds["category_ids"], list):

        # Remove existing category associations
        delete_repository_category_associations(sa_session, app.model.RepositoryCategoryAssociation, repository.id)

        # Then (re)create category associations
        for category_id in kwds["category_ids"]:
            category = sa_session.get(app.model.Category, app.security.decode_id(category_id))
            if category:
                rca = app.model.RepositoryCategoryAssociation(repository, category)
                sa_session.add(rca)
            else:
                pass
        flush_needed = True

    # However some properties are special, like 'name'
    if "name" in kwds and kwds["name"] is not None and repository.name != kwds["name"]:
        if repository.times_downloaded != 0:
            message = "Repository names cannot be changed if the repository has been cloned."
        else:
            message = validate_repository_name(trans.app, kwds["name"], trans.user)
        if message:
            return None, message

        repo_dir = repository.repo_path(app)
        # Change the entry in the hgweb.config file for the repository.
        old_lhs = f"{trans.app.config.hgweb_repo_prefix}{repository.user.username}/{repository.name}"
        new_lhs = f"{trans.app.config.hgweb_repo_prefix}{repository.user.username}/{kwds['name']}"
        trans.app.hgweb_config_manager.change_entry(old_lhs, new_lhs, repo_dir)

        # Change the entry in the repository's hgrc file.
        hgrc_file = get_hgrc_path(repo_dir)
        change_repository_name_in_hgrc_file(hgrc_file, kwds["name"])

        # Rename the repository's admin role to match the new repository name.
        repository_admin_role = repository.admin_role
        repository_admin_role.name = get_repository_admin_role_name(str(kwds["name"]), str(repository.user.username))
        trans.sa_session.add(repository_admin_role)
        repository.name = kwds["name"]
        flush_needed = True

    if flush_needed:
        trans.sa_session.add(repository)
        trans.sa_session.commit()
        message = "The repository information has been updated."
    else:
        message = None
    return repository, message


def validate_repository_name(app: "ToolShedApp", name, user):
    """
    Validate whether the given name qualifies as a new TS repo name.
    Repository names must be unique for each user, must be at least two characters
    in length and must contain only lower-case letters, numbers, and the '_' character.
    """
    if name in ["None", None, ""]:
        return "Enter the required repository name."
    if name in ["repos"]:
        return f"The term '{name}' is a reserved word in the Tool Shed, so it cannot be used as a repository name."
    check_existing = get_repository_by_name_and_owner(app, name, user.username)
    if check_existing is not None:
        if check_existing.deleted:
            return f"You own a deleted repository named <b>{escape(name)}</b>, please choose a different name."
        else:
            return f"You already own a repository named <b>{escape(name)}</b>, please choose a different name."
    if len(name) < 2:
        return "Repository names must be at least 2 characters in length."
    if len(name) > 80:
        return "Repository names cannot be more than 80 characters in length."
    if not (VALID_REPOSITORYNAME_RE.match(name)):
        return "Repository names must contain only lower-case letters, numbers and underscore."
    return ""


def get_repositories(
    session,
    repository_model,
    repository_category_assoc_model,
    user_model,
    repository_metadata_model,
    category_id,
    installable,
    sort_order,
    sort_key,
    page,
    per_page,
):
    Repository = repository_model
    RepositoryCategoryAssociation = repository_category_assoc_model
    User = user_model
    RepositoryMetadata = repository_metadata_model

    stmt = (
        select(Repository)
        .join(
            RepositoryCategoryAssociation,
            Repository.id == RepositoryCategoryAssociation.repository_id,
        )
        .join(User, User.id == Repository.user_id)
        .where(RepositoryCategoryAssociation.category_id == category_id)
    )
    if installable:
        stmt1 = select(RepositoryMetadata.repository_id)
        stmt = stmt.where(Repository.id.in_(stmt1))

    if sort_key == "owner":
        sort_by = User.username
    else:
        sort_by = Repository.name
    if sort_order == "desc":
        sort_by = sort_by.desc()
    stmt = stmt.order_by(sort_by)

    if page is not None:
        page = int(page)
        stmt = stmt.limit(per_page)
        if page > 1:
            stmt = stmt.offset((page - 1) * per_page)

    return session.scalars(stmt)


def get_current_users(session, user_model):
    stmt = select(user_model).where(user_model.deleted == false()).order_by(user_model.email)
    return session.scalars(stmt)


def get_current_groups(session, group_model):
    stmt = select(group_model).where(group_model.deleted == false()).order_by(group_model.name)
    return session.scalars(stmt)


def delete_repository_category_associations(session, repository_category_assoc_model, repository_id):
    stmt = delete(repository_category_assoc_model).where(repository_category_assoc_model.repository_id == repository_id)
    return session.execute(stmt)


__all__ = (
    "change_repository_name_in_hgrc_file",
    "create_or_update_tool_shed_repository",
    "create_repo_info_dict",
    "create_repository_admin_role",
    "create_repository",
    "extract_components_from_tuple",
    "generate_sharable_link_for_repository_in_tool_shed",
    "generate_tool_shed_repository_install_dir",
    "get_absolute_path_to_file_in_repository",
    "get_installed_repository",
    "get_installed_tool_shed_repository",
    "get_prior_import_or_install_required_dict",
    "get_repo_info_dict",
    "get_repo_info_tuple_contents",
    "get_repositories_by_category",
    "get_repository_admin_role_name",
    "get_repository_and_repository_dependencies_from_repo_info_dict",
    "get_repository_by_id",
    "get_repository_by_name",
    "get_repository_by_name_and_owner",
    "get_repository_dependency_types",
    "get_repository_for_dependency_relationship",
    "get_repository_ids_requiring_prior_import_or_install",
    "get_repository_in_tool_shed",
    "get_repository_owner",
    "get_repository_owner_from_clone_url",
    "get_repository_query",
    "get_role_by_id",
    "get_tool_shed_from_clone_url",
    "get_tool_shed_repository_by_id",
    "get_tool_shed_status_for_installed_repository",
    "handle_role_associations",
    "is_tool_shed_client",
    "repository_was_previously_installed",
    "set_repository_attributes",
    "update_repository",
    "validate_repository_name",
)
