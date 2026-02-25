import json
import logging
import os

from galaxy import (
    util,
    web,
)
from galaxy.util.tool_shed import encoding_util
from galaxy.webapps.base.controller import BaseUIController
from tool_shed.util import (
    common_util,
    hg_util,
    metadata_util,
    repository_util,
)
from tool_shed.webapp.model.db import get_repository_by_name_and_owner

log = logging.getLogger(__name__)


class RepositoryController(BaseUIController):
    """Tool Shed repository controller.

    WARNING: The /repository/* endpoints below are called by Galaxy's install
    client code (lib/galaxy/tool_shed/galaxy_install/) as server-to-server RPC.
    They must remain available and backward-compatible for older Galaxy instances.
    See lib/tool_shed/test/functional/api_notes.md for details.
    """

    @web.expose
    def display_image_in_repository(self, trans, **kwd):
        """
        Open an image file that is contained in a repository for display.
        Images can be referenced from README.rst or Galaxy tool help sections.
        """
        repository_id = kwd.get("repository_id", None)
        relative_path_to_image_file = kwd.get("image_file", None)
        if repository_id and relative_path_to_image_file:
            repository = repository_util.get_repository_in_tool_shed(trans.app, repository_id)
            if repository:
                repo_files_dir = repository.repo_path(trans.app)
                path_to_file = repository_util.get_absolute_path_to_file_in_repository(
                    repo_files_dir, relative_path_to_image_file
                )
                if os.path.exists(path_to_file):
                    file_name = os.path.basename(relative_path_to_image_file)
                    try:
                        extension = file_name.split(".")[-1]
                    except Exception:
                        extension = None
                    if extension:
                        mimetype = trans.app.datatypes_registry.get_mimetype_by_extension(extension)
                        if mimetype:
                            trans.response.set_content_type(mimetype)
                    return open(path_to_file, "rb")

    # -------------------------------------------------------------------------
    # Galaxy install-client RPC endpoints
    #
    # These are called by Galaxy during repository installation, update checks,
    # and dependency resolution. They are NOT user-facing UI endpoints.
    # -------------------------------------------------------------------------

    @web.expose
    def get_ctx_rev(self, trans, **kwd):
        """Given a repository and changeset_revision, return the correct ctx.rev() value."""
        repository_name = kwd["name"]
        repository_owner = kwd["owner"]
        changeset_revision = kwd["changeset_revision"]
        repository = get_repository_by_name_and_owner(trans.sa_session, repository_name, repository_owner)
        repo = repository.hg_repo
        if ctx := hg_util.get_changectx_for_changeset(repo, changeset_revision):
            return str(ctx.rev())
        return ""

    @web.expose
    def get_changeset_revision_and_ctx_rev(self, trans, **kwd):
        """Handle a request from a local Galaxy instance to retrieve the changeset revision
        hash to which an installed repository can be updated."""

        def has_galaxy_utilities(repository_metadata):
            has_galaxy_utilities_dict = dict(
                includes_data_managers=False,
                includes_datatypes=False,
                includes_tools=False,
                includes_tools_for_display_in_tool_panel=False,
                has_repository_dependencies=False,
                has_repository_dependencies_only_if_compiling_contained_td=False,
                includes_tool_dependencies=False,
                includes_workflows=False,
            )
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if "data_manager" in metadata:
                        has_galaxy_utilities_dict["includes_data_managers"] = True
                    if "datatypes" in metadata:
                        has_galaxy_utilities_dict["includes_datatypes"] = True
                    if "tools" in metadata:
                        has_galaxy_utilities_dict["includes_tools"] = True
                    if "tool_dependencies" in metadata:
                        has_galaxy_utilities_dict["includes_tool_dependencies"] = True
                    repository_dependencies_dict = metadata.get("repository_dependencies", {})
                    repository_dependencies = repository_dependencies_dict.get("repository_dependencies", [])
                    (
                        has_repository_dependencies,
                        has_repository_dependencies_only_if_compiling_contained_td,
                    ) = repository_util.get_repository_dependency_types(repository_dependencies)
                    has_galaxy_utilities_dict["has_repository_dependencies"] = has_repository_dependencies
                    has_galaxy_utilities_dict["has_repository_dependencies_only_if_compiling_contained_td"] = (
                        has_repository_dependencies_only_if_compiling_contained_td
                    )
                    if "workflows" in metadata:
                        has_galaxy_utilities_dict["includes_workflows"] = True
            return has_galaxy_utilities_dict

        name = kwd.get("name", None)
        owner = kwd.get("owner", None)
        changeset_revision = kwd.get("changeset_revision", None)
        repository = get_repository_by_name_and_owner(trans.sa_session, name, owner)
        repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision(
            trans.app, trans.security.encode_id(repository.id), changeset_revision
        )
        has_galaxy_utilities_dict = has_galaxy_utilities(repository_metadata)
        includes_data_managers = has_galaxy_utilities_dict["includes_data_managers"]
        includes_datatypes = has_galaxy_utilities_dict["includes_datatypes"]
        includes_tools = has_galaxy_utilities_dict["includes_tools"]
        includes_tools_for_display_in_tool_panel = has_galaxy_utilities_dict[
            "includes_tools_for_display_in_tool_panel"
        ]
        includes_tool_dependencies = has_galaxy_utilities_dict["includes_tool_dependencies"]
        has_repository_dependencies = has_galaxy_utilities_dict["has_repository_dependencies"]
        has_repository_dependencies_only_if_compiling_contained_td = has_galaxy_utilities_dict[
            "has_repository_dependencies_only_if_compiling_contained_td"
        ]
        includes_workflows = has_galaxy_utilities_dict["includes_workflows"]
        repo = repository.hg_repo
        # Default to the received changeset revision and ctx_rev.
        update_to_ctx = hg_util.get_changectx_for_changeset(repo, changeset_revision)
        ctx_rev = str(update_to_ctx.rev())
        latest_changeset_revision = changeset_revision
        update_dict = dict(
            changeset_revision=changeset_revision,
            ctx_rev=ctx_rev,
            includes_data_managers=includes_data_managers,
            includes_datatypes=includes_datatypes,
            includes_tools=includes_tools,
            includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
            includes_tool_dependencies=includes_tool_dependencies,
            has_repository_dependencies=has_repository_dependencies,
            has_repository_dependencies_only_if_compiling_contained_td=has_repository_dependencies_only_if_compiling_contained_td,
            includes_workflows=includes_workflows,
        )
        if changeset_revision == repository.tip():
            # If changeset_revision is the repository tip, there are no additional updates.
            return encoding_util.tool_shed_encode(update_dict)
        else:
            if repository_metadata:
                # If changeset_revision is in the repository_metadata table, no additional updates.
                return encoding_util.tool_shed_encode(update_dict)
            else:
                # The changeset_revision has been updated since install. Find the update target.
                update_to_changeset_hash = None
                for changeset in repo.changelog:
                    includes_tools = False
                    has_repository_dependencies = False
                    has_repository_dependencies_only_if_compiling_contained_td = False
                    changeset_hash = str(repo[changeset])
                    if update_to_changeset_hash:
                        update_to_repository_metadata = (
                            metadata_util.get_repository_metadata_by_changeset_revision(
                                trans.app, trans.security.encode_id(repository.id), changeset_hash
                            )
                        )
                        if update_to_repository_metadata:
                            has_galaxy_utilities_dict = has_galaxy_utilities(repository_metadata)
                            includes_data_managers = has_galaxy_utilities_dict["includes_data_managers"]
                            includes_datatypes = has_galaxy_utilities_dict["includes_datatypes"]
                            includes_tools = has_galaxy_utilities_dict["includes_tools"]
                            includes_tools_for_display_in_tool_panel = has_galaxy_utilities_dict[
                                "includes_tools_for_display_in_tool_panel"
                            ]
                            includes_tool_dependencies = has_galaxy_utilities_dict["includes_tool_dependencies"]
                            has_repository_dependencies = has_galaxy_utilities_dict["has_repository_dependencies"]
                            has_repository_dependencies_only_if_compiling_contained_td = has_galaxy_utilities_dict[
                                "has_repository_dependencies_only_if_compiling_contained_td"
                            ]
                            includes_workflows = has_galaxy_utilities_dict["includes_workflows"]
                            if changeset_hash == repository.tip():
                                update_to_ctx = hg_util.get_changectx_for_changeset(repo, changeset_hash)
                                latest_changeset_revision = changeset_hash
                            else:
                                update_to_ctx = hg_util.get_changectx_for_changeset(
                                    repo, update_to_changeset_hash
                                )
                                latest_changeset_revision = update_to_changeset_hash
                            break
                    elif not update_to_changeset_hash and changeset_hash == changeset_revision:
                        update_to_changeset_hash = changeset_hash
                update_dict["includes_data_managers"] = includes_data_managers
                update_dict["includes_datatypes"] = includes_datatypes
                update_dict["includes_tools"] = includes_tools
                update_dict["includes_tools_for_display_in_tool_panel"] = (
                    includes_tools_for_display_in_tool_panel
                )
                update_dict["includes_tool_dependencies"] = includes_tool_dependencies
                update_dict["includes_workflows"] = includes_workflows
                update_dict["has_repository_dependencies"] = has_repository_dependencies
                update_dict["has_repository_dependencies_only_if_compiling_contained_td"] = (
                    has_repository_dependencies_only_if_compiling_contained_td
                )
                update_dict["changeset_revision"] = str(latest_changeset_revision)
        update_dict["ctx_rev"] = str(update_to_ctx.rev())
        return encoding_util.tool_shed_encode(update_dict)

    @web.json
    def get_repository_dependencies(self, trans, **kwd):
        """Return an encoded dictionary of all repositories upon which the contents of the
        received repository depends."""
        name = kwd.get("name", None)
        owner = kwd.get("owner", None)
        changeset_revision = kwd.get("changeset_revision", None)
        repository = get_repository_by_name_and_owner(trans.sa_session, name, owner)
        dependencies = repository.get_repository_dependencies(
            trans.app, changeset_revision, web.url_for("/", qualified=True)
        )
        if dependencies:
            return encoding_util.tool_shed_encode(dependencies)
        return ""

    @web.json
    def get_repository_information(self, trans, repository_ids, changeset_revisions, **kwd):
        """Generate a list of dictionaries, each containing the information about a repository
        needed for installing it into a local Galaxy instance."""
        includes_tools = False
        includes_tools_for_display_in_tool_panel = False
        has_repository_dependencies = False
        has_repository_dependencies_only_if_compiling_contained_td = False
        includes_tool_dependencies = False
        repo_info_dicts = []
        for tup in zip(util.listify(repository_ids), util.listify(changeset_revisions)):
            repository_id, changeset_revision = tup
            (
                repo_info_dict,
                cur_includes_tools,
                cur_includes_tool_dependencies,
                cur_includes_tools_for_display_in_tool_panel,
                cur_has_repository_dependencies,
                cur_has_repository_dependencies_only_if_compiling_contained_td,
            ) = repository_util.get_repo_info_dict(trans, repository_id, changeset_revision)
            if cur_has_repository_dependencies and not has_repository_dependencies:
                has_repository_dependencies = True
            if (
                cur_has_repository_dependencies_only_if_compiling_contained_td
                and not has_repository_dependencies_only_if_compiling_contained_td
            ):
                has_repository_dependencies_only_if_compiling_contained_td = True
            if cur_includes_tools and not includes_tools:
                includes_tools = True
            if cur_includes_tool_dependencies and not includes_tool_dependencies:
                includes_tool_dependencies = True
            if cur_includes_tools_for_display_in_tool_panel and not includes_tools_for_display_in_tool_panel:
                includes_tools_for_display_in_tool_panel = True
            repo_info_dicts.append(encoding_util.tool_shed_encode(repo_info_dict))
        return dict(
            includes_tools=includes_tools,
            includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
            has_repository_dependencies=has_repository_dependencies,
            has_repository_dependencies_only_if_compiling_contained_td=has_repository_dependencies_only_if_compiling_contained_td,
            includes_tool_dependencies=includes_tool_dependencies,
            repo_info_dicts=repo_info_dicts,
        )

    @web.json
    def get_required_repo_info_dict(self, trans, encoded_str=None):
        """Retrieve and return a dictionary that includes a list of dictionaries that each
        contain all of the information needed to install the list of repositories defined by
        the received encoded_str."""
        repo_info_dict = {}
        if encoded_str:
            encoded_required_repository_str = encoding_util.tool_shed_decode(encoded_str)
            encoded_required_repository_tups = encoded_required_repository_str.split(encoding_util.encoding_sep2)
            decoded_required_repository_tups = []
            for encoded_required_repository_tup in encoded_required_repository_tups:
                decoded_required_repository_tups.append(
                    encoded_required_repository_tup.split(encoding_util.encoding_sep)
                )
            encoded_repository_ids = []
            changeset_revisions = []
            for required_repository_tup in decoded_required_repository_tups:
                (
                    tool_shed,
                    name,
                    owner,
                    changeset_revision,
                    prior_installation_required,
                    only_if_compiling_contained_td,
                ) = common_util.parse_repository_dependency_tuple(required_repository_tup)
                repository = get_repository_by_name_and_owner(trans.sa_session, name, owner)
                encoded_repository_ids.append(trans.security.encode_id(repository.id))
                changeset_revisions.append(changeset_revision)
            if encoded_repository_ids and changeset_revisions:
                repo_info_dict = json.loads(
                    self.get_repository_information(trans, encoded_repository_ids, changeset_revisions)
                )
        return repo_info_dict

    @web.expose
    def get_repository_type(self, trans, **kwd):
        """Given a repository name and owner, return the type."""
        repository_name = kwd["name"]
        repository_owner = kwd["owner"]
        repository = get_repository_by_name_and_owner(trans.sa_session, repository_name, repository_owner)
        return str(repository.type)

    @web.expose
    def get_tool_dependencies(self, trans, **kwd):
        """Handle a request from a Galaxy instance to get the tool_dependencies entry from
        the metadata for a specified changeset revision."""
        name = kwd.get("name", None)
        owner = kwd.get("owner", None)
        changeset_revision = kwd.get("changeset_revision", None)
        repository = get_repository_by_name_and_owner(trans.sa_session, name, owner)
        dependencies = repository.get_tool_dependencies(trans.app, changeset_revision)
        if len(dependencies) > 0:
            return encoding_util.tool_shed_encode(dependencies)
        return ""

    @web.expose
    def next_installable_changeset_revision(self, trans, **kwd):
        """Handle a request from a Galaxy instance where the changeset_revision defined for
        a repository in a dependency definition file is older than the changeset_revision
        associated with the installed repository."""
        name = kwd.get("name", None)
        owner = kwd.get("owner", None)
        changeset_revision = kwd.get("changeset_revision", None)
        repository = get_repository_by_name_and_owner(trans.sa_session, name, owner)
        next_changeset_revision = metadata_util.get_next_downloadable_changeset_revision(
            trans.app, repository, changeset_revision
        )
        if next_changeset_revision and next_changeset_revision != changeset_revision:
            return next_changeset_revision
        return ""

    @web.expose
    def previous_changeset_revisions(self, trans, from_tip=False, **kwd):
        """Handle a request from a local Galaxy instance. Returns comma-separated changeset
        hashes between the previous metadata revision and the given revision."""
        name = kwd.get("name", None)
        owner = kwd.get("owner", None)
        if name is not None and owner is not None:
            repository = get_repository_by_name_and_owner(trans.sa_session, name, owner)
            from_tip = util.string_as_bool(from_tip)
            if from_tip:
                changeset_revision = repository.tip()
            else:
                changeset_revision = kwd.get("changeset_revision", None)
            if changeset_revision is not None:
                repo = repository.hg_repo
                lower_bound_changeset_revision = metadata_util.get_previous_metadata_changeset_revision(
                    trans.app, repository, changeset_revision, downloadable=True
                )
                changeset_hashes = []
                for changeset in hg_util.reversed_lower_upper_bounded_changelog(
                    repo, lower_bound_changeset_revision, changeset_revision
                ):
                    changeset_hashes.append(str(repo[changeset]))
                if changeset_hashes:
                    changeset_hashes_str = ",".join(changeset_hashes)
                    return changeset_hashes_str
        return ""

    @web.expose
    def updated_changeset_revisions(self, trans, **kwd):
        """Handle a request from a local Galaxy instance to retrieve the list of changeset
        revisions to which an installed repository can be updated. Returns a comma-separated
        string of changeset revision hashes."""
        name = kwd.get("name", None)
        owner = kwd.get("owner", None)
        changeset_revision = kwd.get("changeset_revision", None)
        if name and owner and changeset_revision:
            return metadata_util.get_updated_changeset_revisions(trans.app, name, owner, changeset_revision)
        return ""
