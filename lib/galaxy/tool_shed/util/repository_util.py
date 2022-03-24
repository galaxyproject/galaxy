import logging
import os
import re
import shutil
from urllib.error import HTTPError

from markupsafe import escape
from sqlalchemy import (
    and_,
    false,
    or_,
)
from sqlalchemy.orm import joinedload

from galaxy import (
    util,
    web,
)
from galaxy.tool_shed.util import basic_util
from galaxy.util.tool_shed import (
    common_util,
    encoding_util,
)

log = logging.getLogger(__name__)

VALID_REPOSITORYNAME_RE = re.compile(r"^[a-z0-9\_]+$")


def check_for_updates(app, model, repository_id=None):
    message = ""
    status = "ok"
    if repository_id is None:
        success_count = 0
        repository_names_not_updated = []
        updated_count = 0
        for repository in model.context.query(model.ToolShedRepository).filter(
            model.ToolShedRepository.table.c.deleted == false()
        ):
            ok, updated = check_or_update_tool_shed_status_for_installed_repository(app, repository)
            if ok:
                success_count += 1
            else:
                repository_names_not_updated.append(f"<b>{escape(str(repository.name))}</b>")
            if updated:
                updated_count += 1
        message = "Checked the status in the tool shed for %d repositories.  " % success_count
        message += "Updated the tool shed status for %d repositories.  " % updated_count
        if repository_names_not_updated:
            message += "Unable to retrieve status from the tool shed for the following repositories:\n"
            message += ", ".join(repository_names_not_updated)
    else:
        repository = get_tool_shed_repository_by_id(app, repository_id)
        ok, updated = check_or_update_tool_shed_status_for_installed_repository(app, repository)
        if ok:
            if updated:
                message = f"The tool shed status for repository <b>{escape(str(repository.name))}</b> has been updated."
            else:
                message = (
                    f"The status has not changed in the tool shed for repository <b>{escape(str(repository.name))}</b>."
                )
        else:
            message = (
                f"Unable to retrieve status from the tool shed for repository <b>{escape(str(repository.name))}</b>."
            )
            status = "error"
    return message, status


def check_or_update_tool_shed_status_for_installed_repository(app, repository):
    updated = False
    tool_shed_status_dict = get_tool_shed_status_for_installed_repository(app, repository)
    if tool_shed_status_dict:
        ok = True
        if tool_shed_status_dict != repository.tool_shed_status:
            repository.tool_shed_status = tool_shed_status_dict
            app.install_model.context.add(repository)
            app.install_model.context.flush()
            updated = True
    else:
        ok = False
    return ok, updated


def create_or_update_tool_shed_repository(
    app,
    name,
    description,
    installed_changeset_revision,
    ctx_rev,
    repository_clone_url,
    status,
    metadata_dict=None,
    current_changeset_revision=None,
    owner="",
    dist_to_shed=False,
):
    """
    Update a tool shed repository record in the Galaxy database with the new information received.
    If a record defined by the received tool shed, repository name and owner does not exist, create
    a new record with the received information.
    """
    metadata_dict = metadata_dict or {}
    # The received value for dist_to_shed will be True if the ToolMigrationManager is installing a repository
    # that contains tools or datatypes that used to be in the Galaxy distribution, but have been moved
    # to the main Galaxy tool shed.
    if current_changeset_revision is None:
        # The current_changeset_revision is not passed if a repository is being installed for the first
        # time.  If a previously installed repository was later uninstalled, this value should be received
        # as the value of that change set to which the repository had been updated just prior to it being
        # uninstalled.
        current_changeset_revision = installed_changeset_revision
    context = app.install_model.context
    tool_shed = get_tool_shed_from_clone_url(repository_clone_url)
    if not owner:
        owner = get_repository_owner_from_clone_url(repository_clone_url)
    includes_datatypes = "datatypes" in metadata_dict
    if status in [app.install_model.ToolShedRepository.installation_status.DEACTIVATED]:
        deleted = True
        uninstalled = False
    elif status in [app.install_model.ToolShedRepository.installation_status.UNINSTALLED]:
        deleted = True
        uninstalled = True
    else:
        deleted = False
        uninstalled = False
    tool_shed_repository = get_installed_repository(
        app, tool_shed=tool_shed, name=name, owner=owner, installed_changeset_revision=installed_changeset_revision
    )
    if tool_shed_repository:
        log.debug(
            "Updating an existing row for repository '%s' in the tool_shed_repository table, status set to '%s'.",
            name,
            status,
        )
        tool_shed_repository.description = description
        tool_shed_repository.changeset_revision = current_changeset_revision
        tool_shed_repository.ctx_rev = ctx_rev
        tool_shed_repository.metadata_ = metadata_dict
        tool_shed_repository.includes_datatypes = includes_datatypes
        tool_shed_repository.deleted = deleted
        tool_shed_repository.uninstalled = uninstalled
        tool_shed_repository.status = status
    else:
        log.debug(
            "Adding new row for repository '%s' in the tool_shed_repository table, status set to '%s'.", name, status
        )
        tool_shed_repository = app.install_model.ToolShedRepository(
            tool_shed=tool_shed,
            name=name,
            description=description,
            owner=owner,
            installed_changeset_revision=installed_changeset_revision,
            changeset_revision=current_changeset_revision,
            ctx_rev=ctx_rev,
            metadata_=metadata_dict,
            includes_datatypes=includes_datatypes,
            dist_to_shed=dist_to_shed,
            deleted=deleted,
            uninstalled=uninstalled,
            status=status,
        )
    context.add(tool_shed_repository)
    context.flush()
    return tool_shed_repository


def extract_components_from_tuple(repository_components_tuple):
    """Extract the repository components from the provided tuple in a backward-compatible manner."""
    toolshed = repository_components_tuple[0]
    name = repository_components_tuple[1]
    owner = repository_components_tuple[2]
    changeset_revision = repository_components_tuple[3]
    components_list = [toolshed, name, owner, changeset_revision]
    if len(repository_components_tuple) == 5:
        toolshed, name, owner, changeset_revision, prior_installation_required = repository_components_tuple
        components_list = [toolshed, name, owner, changeset_revision, prior_installation_required]
    elif len(repository_components_tuple) == 6:
        (
            toolshed,
            name,
            owner,
            changeset_revision,
            prior_installation_required,
            only_if_compiling_contained_td,
        ) = repository_components_tuple
        components_list = [
            toolshed,
            name,
            owner,
            changeset_revision,
            prior_installation_required,
            only_if_compiling_contained_td,
        ]
    return components_list


def generate_tool_shed_repository_install_dir(repository_clone_url, changeset_revision):
    """
    Generate a repository installation directory that guarantees repositories with the same
    name will always be installed in different directories.  The tool path will be of the form:
    <tool shed url>/repos/<repository owner>/<repository name>/<installed changeset revision>
    """
    tmp_url = common_util.remove_protocol_and_user_from_clone_url(repository_clone_url)
    # Now tmp_url is something like: bx.psu.edu:9009/repos/some_username/column
    items = tmp_url.split("/repos/")
    tool_shed_url = items[0]
    repo_path = items[1]
    tool_shed_url = common_util.remove_port_from_tool_shed_url(tool_shed_url)
    return "/".join((tool_shed_url, "repos", repo_path, changeset_revision))


def get_absolute_path_to_file_in_repository(repo_files_dir, file_name):
    """Return the absolute path to a specified disk file contained in a repository."""
    stripped_file_name = basic_util.strip_path(file_name)
    file_path = None
    for root, _, files in os.walk(repo_files_dir):
        if root.find(".hg") < 0:
            for name in files:
                if name == stripped_file_name:
                    return os.path.abspath(os.path.join(root, name))
    return file_path


def get_ids_of_tool_shed_repositories_being_installed(app, as_string=False):
    installing_repository_ids = []
    new_status = app.install_model.ToolShedRepository.installation_status.NEW
    cloning_status = app.install_model.ToolShedRepository.installation_status.CLONING
    setting_tool_versions_status = app.install_model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS
    installing_dependencies_status = (
        app.install_model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES
    )
    loading_datatypes_status = app.install_model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES
    for tool_shed_repository in app.install_model.context.query(app.install_model.ToolShedRepository).filter(
        or_(
            app.install_model.ToolShedRepository.status == new_status,
            app.install_model.ToolShedRepository.status == cloning_status,
            app.install_model.ToolShedRepository.status == setting_tool_versions_status,
            app.install_model.ToolShedRepository.status == installing_dependencies_status,
            app.install_model.ToolShedRepository.status == loading_datatypes_status,
        )
    ):
        installing_repository_ids.append(app.security.encode_id(tool_shed_repository.id))
    if as_string:
        return ",".join(installing_repository_ids)
    return installing_repository_ids


def get_installed_repository(
    app,
    tool_shed=None,
    name=None,
    owner=None,
    changeset_revision=None,
    installed_changeset_revision=None,
    repository_id=None,
    from_cache=False,
):
    """
    Return a tool shed repository database record defined by the combination of a toolshed, repository name,
    repository owner and either current or originally installed changeset_revision.
    """
    # We store the port, if one exists, in the database.
    tool_shed = common_util.remove_protocol_from_tool_shed_url(tool_shed)
    if from_cache:
        tsr_cache = getattr(app, "tool_shed_repository_cache", None)
        if tsr_cache:
            return app.tool_shed_repository_cache.get_installed_repository(
                tool_shed=tool_shed,
                name=name,
                owner=owner,
                installed_changeset_revision=installed_changeset_revision,
                changeset_revision=changeset_revision,
                repository_id=repository_id,
            )
    query = app.install_model.context.query(app.install_model.ToolShedRepository)
    if repository_id:
        clause_list = [app.install_model.ToolShedRepository.table.c.id == repository_id]
    else:
        clause_list = [
            app.install_model.ToolShedRepository.table.c.tool_shed == tool_shed,
            app.install_model.ToolShedRepository.table.c.name == name,
            app.install_model.ToolShedRepository.table.c.owner == owner,
        ]
    if changeset_revision is not None:
        clause_list.append(app.install_model.ToolShedRepository.table.c.changeset_revision == changeset_revision)
    if installed_changeset_revision is not None:
        clause_list.append(
            app.install_model.ToolShedRepository.table.c.installed_changeset_revision == installed_changeset_revision
        )
    return query.filter(and_(*clause_list)).first()


def get_installed_tool_shed_repository(app, id):
    """Get a tool shed repository record from the Galaxy database defined by the id."""
    rval = []
    if isinstance(id, list):
        return_list = True
    else:
        id = [id]
        return_list = False
    repository_ids = [app.security.decode_id(i) for i in id]
    rval = [get_installed_repository(app=app, repository_id=repo_id, from_cache=False) for repo_id in repository_ids]
    if return_list:
        return rval
    return rval[0]


def get_prior_import_or_install_required_dict(app, tsr_ids, repo_info_dicts):
    """
    This method is used in the Tool Shed when exporting a repository and its dependencies,
    and in Galaxy when a repository and its dependencies are being installed.  Return a
    dictionary whose keys are the received tsr_ids and whose values are a list of tsr_ids,
    each of which is contained in the received list of tsr_ids and whose associated repository
    must be imported or installed prior to the repository associated with the tsr_id key.
    """
    # Initialize the dictionary.
    prior_import_or_install_required_dict = {}
    for tsr_id in tsr_ids:
        prior_import_or_install_required_dict[tsr_id] = []
    # Inspect the repository dependencies for each repository about to be installed and populate the dictionary.
    for repo_info_dict in repo_info_dicts:
        repository, repository_dependencies = get_repository_and_repository_dependencies_from_repo_info_dict(
            app, repo_info_dict
        )
        if repository:
            encoded_repository_id = app.security.encode_id(repository.id)
            if encoded_repository_id in tsr_ids:
                # We've located the database table record for one of the repositories we're about to install, so find out if it has any repository
                # dependencies that require prior installation.
                prior_import_or_install_ids = get_repository_ids_requiring_prior_import_or_install(
                    app, tsr_ids, repository_dependencies
                )
                prior_import_or_install_required_dict[encoded_repository_id] = prior_import_or_install_ids
    return prior_import_or_install_required_dict


def get_repo_info_tuple_contents(repo_info_tuple):
    """Take care in handling the repo_info_tuple as it evolves over time as new tool shed features are introduced."""
    if len(repo_info_tuple) == 6:
        (
            description,
            repository_clone_url,
            changeset_revision,
            ctx_rev,
            repository_owner,
            tool_dependencies,
        ) = repo_info_tuple
        repository_dependencies = None
    elif len(repo_info_tuple) == 7:
        (
            description,
            repository_clone_url,
            changeset_revision,
            ctx_rev,
            repository_owner,
            repository_dependencies,
            tool_dependencies,
        ) = repo_info_tuple
    return (
        description,
        repository_clone_url,
        changeset_revision,
        ctx_rev,
        repository_owner,
        repository_dependencies,
        tool_dependencies,
    )


def get_repository_admin_role_name(repository_name, repository_owner):
    return f"{repository_name}_{repository_owner}_admin"


def get_repository_and_repository_dependencies_from_repo_info_dict(app, repo_info_dict):
    """Return a tool_shed_repository or repository record defined by the information in the received repo_info_dict."""
    repository_name = list(repo_info_dict.keys())[0]
    repo_info_tuple = repo_info_dict[repository_name]
    (
        description,
        repository_clone_url,
        changeset_revision,
        ctx_rev,
        repository_owner,
        repository_dependencies,
        tool_dependencies,
    ) = get_repo_info_tuple_contents(repo_info_tuple)
    if hasattr(app, "install_model"):
        # In a tool shed client (Galaxy, or something install repositories like Galaxy)
        tool_shed = get_tool_shed_from_clone_url(repository_clone_url)
        repository = get_repository_for_dependency_relationship(
            app, tool_shed, repository_name, repository_owner, changeset_revision
        )
    else:
        # We're in the tool shed.
        repository = get_repository_by_name_and_owner(app, repository_name, repository_owner)
    return repository, repository_dependencies


def get_repository_by_id(app, id):
    """Get a repository from the database via id."""
    if is_tool_shed_client(app):
        return app.install_model.context.query(app.install_model.ToolShedRepository).get(app.security.decode_id(id))
    else:
        sa_session = app.model.session
        return sa_session.query(app.model.Repository).get(app.security.decode_id(id))


def get_repository_by_name_and_owner(app, name, owner, eagerload_columns=None):
    """Get a repository from the database via name and owner"""
    repository_query = get_repository_query(app)
    if is_tool_shed_client(app):
        return repository_query.filter(
            and_(
                app.install_model.ToolShedRepository.table.c.name == name,
                app.install_model.ToolShedRepository.table.c.owner == owner,
            )
        ).first()
    # We're in the tool shed.
    q = repository_query.filter(
        and_(
            app.model.Repository.table.c.name == name,
            app.model.User.table.c.username == owner,
            app.model.Repository.table.c.user_id == app.model.User.table.c.id,
        )
    )
    if eagerload_columns:
        q = q.options(joinedload(*eagerload_columns))
    return q.first()


def get_repository_by_name(app, name):
    """Get a repository from the database via name."""
    return get_repository_query(app).filter_by(name=name).first()


def get_repository_dependency_types(repository_dependencies):
    """
    Inspect the received list of repository_dependencies tuples and return boolean values
    for has_repository_dependencies and has_repository_dependencies_only_if_compiling_contained_td.
    """
    # Set has_repository_dependencies, which will be True only if at least one repository_dependency
    # is defined with the value of
    # only_if_compiling_contained_td as False.
    has_repository_dependencies = False
    for rd_tup in repository_dependencies:
        (
            tool_shed,
            name,
            owner,
            changeset_revision,
            prior_installation_required,
            only_if_compiling_contained_td,
        ) = common_util.parse_repository_dependency_tuple(rd_tup)
        if not util.asbool(only_if_compiling_contained_td):
            has_repository_dependencies = True
            break
    # Set has_repository_dependencies_only_if_compiling_contained_td, which will be True only if at
    # least one repository_dependency is defined with the value of only_if_compiling_contained_td as True.
    has_repository_dependencies_only_if_compiling_contained_td = False
    for rd_tup in repository_dependencies:
        (
            tool_shed,
            name,
            owner,
            changeset_revision,
            prior_installation_required,
            only_if_compiling_contained_td,
        ) = common_util.parse_repository_dependency_tuple(rd_tup)
        if util.asbool(only_if_compiling_contained_td):
            has_repository_dependencies_only_if_compiling_contained_td = True
            break
    return has_repository_dependencies, has_repository_dependencies_only_if_compiling_contained_td


def get_repository_for_dependency_relationship(app, tool_shed, name, owner, changeset_revision):
    """
    Return an installed tool_shed_repository database record that is defined by either the current changeset
    revision or the installed_changeset_revision.
    """
    # This method is used only in Galaxy, not the Tool Shed.  We store the port (if one exists) in the database.
    tool_shed = common_util.remove_protocol_from_tool_shed_url(tool_shed)
    if tool_shed is None or name is None or owner is None or changeset_revision is None:
        message = "Unable to retrieve the repository record from the database because one or more of the following "
        message += f"required parameters is None: tool_shed: {tool_shed}, name: {name}, owner: {owner}, changeset_revision: {changeset_revision}"
        raise Exception(message)
    repository = get_installed_repository(
        app=app, tool_shed=tool_shed, name=name, owner=owner, installed_changeset_revision=changeset_revision
    )
    if not repository:
        repository = get_installed_repository(
            app=app, tool_shed=tool_shed, name=name, owner=owner, changeset_revision=changeset_revision
        )
    if not repository:
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(app, tool_shed)
        repository_clone_url = os.path.join(tool_shed_url, "repos", owner, name)
        repo_info_tuple = (None, repository_clone_url, changeset_revision, None, owner, None, None)
        repository, pcr = repository_was_previously_installed(app, tool_shed_url, name, repo_info_tuple)
    if not repository:
        # The received changeset_revision is no longer installable, so get the next changeset_revision
        # in the repository's changelog in the tool shed that is associated with repository_metadata.
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(app, tool_shed)
        params = dict(name=name, owner=owner, changeset_revision=changeset_revision)
        pathspec = ["repository", "next_installable_changeset_revision"]
        text = util.url_get(
            tool_shed_url, auth=app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params
        )
        if text:
            repository = get_installed_repository(
                app=app, tool_shed=tool_shed, name=name, owner=owner, changeset_revision=text
            )
    return repository


def get_repository_ids_requiring_prior_import_or_install(app, tsr_ids, repository_dependencies):
    """
    This method is used in the Tool Shed when exporting a repository and its dependencies,
    and in Galaxy when a repository and its dependencies are being installed.  Inspect the
    received repository_dependencies and determine if the encoded id of each required
    repository is in the received tsr_ids.  If so, then determine whether that required
    repository should be imported / installed prior to its dependent repository.  Return a
    list of encoded repository ids, each of which is contained in the received list of tsr_ids,
    and whose associated repositories must be imported / installed prior to the dependent
    repository associated with the received repository_dependencies.
    """
    prior_tsr_ids = []
    if repository_dependencies:
        for key, rd_tups in repository_dependencies.items():
            if key in ["description", "root_key"]:
                continue
            for rd_tup in rd_tups:
                (
                    tool_shed,
                    name,
                    owner,
                    changeset_revision,
                    prior_installation_required,
                    only_if_compiling_contained_td,
                ) = common_util.parse_repository_dependency_tuple(rd_tup)
                # If only_if_compiling_contained_td is False, then the repository dependency
                # is not required to be installed prior to the dependent repository even if
                # prior_installation_required is True.  This is because the only meaningful
                # content of the repository dependency is its contained tool dependency, which
                # is required in order to compile the dependent repository's tool dependency.
                # In the scenario where the repository dependency is not installed prior to the
                # dependent repository's tool dependency compilation process, the tool dependency
                # compilation framework will install the repository dependency prior to compilation
                # of the dependent repository's tool dependency.
                if not util.asbool(only_if_compiling_contained_td):
                    if util.asbool(prior_installation_required):
                        if is_tool_shed_client(app):
                            # We store the port, if one exists, in the database.
                            tool_shed = common_util.remove_protocol_from_tool_shed_url(tool_shed)
                            repository = get_repository_for_dependency_relationship(
                                app, tool_shed, name, owner, changeset_revision
                            )
                        else:
                            repository = get_repository_by_name_and_owner(app, name, owner)
                        if repository:
                            encoded_repository_id = app.security.encode_id(repository.id)
                            if encoded_repository_id in tsr_ids:
                                prior_tsr_ids.append(encoded_repository_id)
    return prior_tsr_ids


def get_repository_in_tool_shed(app, id, eagerload_columns=None):
    """Get a repository on the tool shed side from the database via id."""
    q = get_repository_query(app)
    if eagerload_columns:
        q = q.options(joinedload(*eagerload_columns))
    return q.get(app.security.decode_id(id))


def get_repository_owner(cleaned_repository_url):
    """Gvien a "cleaned" repository clone URL, return the owner of the repository."""
    items = cleaned_repository_url.split("/repos/")
    repo_path = items[1]
    if repo_path.startswith("/"):
        repo_path = repo_path.replace("/", "", 1)
    return repo_path.lstrip("/").split("/")[0]


def get_repository_owner_from_clone_url(repository_clone_url):
    """Given a repository clone URL, return the owner of the repository."""
    tmp_url = common_util.remove_protocol_and_user_from_clone_url(repository_clone_url)
    return get_repository_owner(tmp_url)


def get_repository_query(app):
    if is_tool_shed_client(app):
        query = app.install_model.context.query(app.install_model.ToolShedRepository)
    else:
        query = app.model.context.query(app.model.Repository)
    return query


def get_role_by_id(app, role_id):
    """Get a Role from the database by id."""
    sa_session = app.model.session
    return sa_session.query(app.model.Role).get(app.security.decode_id(role_id))


def get_tool_shed_from_clone_url(repository_clone_url):
    tmp_url = common_util.remove_protocol_and_user_from_clone_url(repository_clone_url)
    return tmp_url.split("/repos/")[0].rstrip("/")


def get_tool_shed_repository_by_id(app, repository_id):
    """Return a tool shed repository database record defined by the id."""
    # This method is used only in Galaxy, not the tool shed.
    return (
        app.install_model.context.query(app.install_model.ToolShedRepository)
        .filter(app.install_model.ToolShedRepository.table.c.id == app.security.decode_id(repository_id))
        .first()
    )


def get_tool_shed_status_for_installed_repository(app, repository):
    """
    Send a request to the tool shed to retrieve information about newer installable repository revisions,
    current revision updates, whether the repository revision is the latest downloadable revision, and
    whether the repository has been deprecated in the tool shed.  The received repository is a ToolShedRepository
    object from Galaxy.
    """
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(app, str(repository.tool_shed))
    params = dict(name=repository.name, owner=repository.owner, changeset_revision=repository.changeset_revision)
    pathspec = ["repository", "status_for_installed_repository"]
    try:
        encoded_tool_shed_status_dict = util.url_get(
            tool_shed_url, auth=app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params
        )
        tool_shed_status_dict = encoding_util.tool_shed_decode(encoded_tool_shed_status_dict)
        return tool_shed_status_dict
    except HTTPError as e:
        # This should handle backward compatility to the Galaxy 12/20/12 release.  We used to only handle updates for an installed revision
        # using a boolean value.
        log.debug(
            "Error attempting to get tool shed status for installed repository %s: %s\nAttempting older 'check_for_updates' method.\n"
            % (str(repository.name), str(e))
        )
        pathspec = ["repository", "check_for_updates"]
        params["from_update_manager"] = True
        try:
            # The value of text will be 'true' or 'false', depending upon whether there is an update available for the installed revision.
            text = util.url_get(
                tool_shed_url, auth=app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params
            )
            return dict(revision_update=text)
        except Exception:
            # The required tool shed may be unavailable, so default the revision_update value to 'false'.
            return dict(revision_update="false")
    except Exception:
        log.exception("Error attempting to get tool shed status for installed repository %s", str(repository.name))
        return {}


def is_tool_shed_client(app):
    """
    The tool shed and clients to the tool (i.e. Galaxy) require a lot
    of similar functionality in this file but with small differences. This
    method should determine if the app performing the action is the tool shed
    or a client of the tool shed.
    """
    return hasattr(app, "install_model")


def repository_was_previously_installed(app, tool_shed_url, repository_name, repo_info_tuple, from_tip=False):
    """
    Find out if a repository is already installed into Galaxy - there are several scenarios where this
    is necessary.  For example, this method will handle the case where the repository was previously
    installed using an older changeset_revsion, but later the repository was updated in the tool shed
    and now we're trying to install the latest changeset revision of the same repository instead of
    updating the one that was previously installed.  We'll look in the database instead of on disk since
    the repository may be currently uninstalled.
    """
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(app, tool_shed_url)
    (
        description,
        repository_clone_url,
        changeset_revision,
        ctx_rev,
        repository_owner,
        repository_dependencies,
        tool_dependencies,
    ) = get_repo_info_tuple_contents(repo_info_tuple)
    tool_shed = get_tool_shed_from_clone_url(repository_clone_url)
    # See if we can locate the repository using the value of changeset_revision.
    tool_shed_repository = get_installed_repository(
        app,
        tool_shed=tool_shed,
        name=repository_name,
        owner=repository_owner,
        installed_changeset_revision=changeset_revision,
    )
    if tool_shed_repository:
        return tool_shed_repository, changeset_revision
    # Get all previous changeset revisions from the tool shed for the repository back to, but excluding,
    # the previous valid changeset revision to see if it was previously installed using one of them.
    params = dict(
        galaxy_url=web.url_for("/", qualified=True),
        name=repository_name,
        owner=repository_owner,
        changeset_revision=changeset_revision,
        from_tip=str(from_tip),
    )
    pathspec = ["repository", "previous_changeset_revisions"]
    text = util.url_get(
        tool_shed_url, auth=app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params
    )
    if text:
        changeset_revisions = util.listify(text)
        for previous_changeset_revision in changeset_revisions:
            tool_shed_repository = get_installed_repository(
                app,
                tool_shed=tool_shed,
                name=repository_name,
                owner=repository_owner,
                installed_changeset_revision=previous_changeset_revision,
            )
            if tool_shed_repository:
                return tool_shed_repository, previous_changeset_revision
    return None, None


def set_repository_attributes(app, repository, status, error_message, deleted, uninstalled, remove_from_disk=False):
    if remove_from_disk:
        relative_install_dir = repository.repo_path(app)
        if relative_install_dir:
            clone_dir = os.path.abspath(relative_install_dir)
            try:
                shutil.rmtree(clone_dir)
                log.debug("Removed repository installation directory: %s", clone_dir)
            except Exception as e:
                log.debug("Error removing repository installation directory %s: %s", clone_dir, util.unicodify(e))
    repository.error_message = error_message
    repository.status = status
    repository.deleted = deleted
    repository.uninstalled = uninstalled
    app.install_model.context.add(repository)
    app.install_model.context.flush()


__all__ = (
    "check_for_updates",
    "check_or_update_tool_shed_status_for_installed_repository",
    "create_or_update_tool_shed_repository",
    "extract_components_from_tuple",
    "generate_tool_shed_repository_install_dir",
    "get_absolute_path_to_file_in_repository",
    "get_ids_of_tool_shed_repositories_being_installed",
    "get_installed_repository",
    "get_installed_tool_shed_repository",
    "get_prior_import_or_install_required_dict",
    "get_repo_info_tuple_contents",
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
    "is_tool_shed_client",
    "repository_was_previously_installed",
    "set_repository_attributes",
)
