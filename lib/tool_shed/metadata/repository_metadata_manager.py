import logging
import tempfile
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    false,
    select,
)

from galaxy import util
from galaxy.tool_shed.metadata.metadata_generator import (
    BaseMetadataGenerator,
    HandleResultT,
    InvalidFileT,
)
from galaxy.util import inflector
from galaxy.web.form_builder import SelectField
from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.repository_types import util as rt_util
from tool_shed.repository_types.metadata import TipOnly
from tool_shed.structured_app import ToolShedApp
from tool_shed.util import (
    basic_util,
    common_util,
    hg_util,
    metadata_util,
    repository_util,
    shed_util_common as suc,
    tool_util,
)
from tool_shed.util.metadata_util import repository_metadata_by_changeset_revision
from tool_shed.webapp.model import (
    Repository,
    RepositoryMetadata,
    User,
)
from tool_shed.webapp.model.db import get_repository_by_name_and_owner

log = logging.getLogger(__name__)


class ToolShedMetadataGenerator(BaseMetadataGenerator):
    """A MetadataGenerator building on ToolShed's app and repository constructs."""

    app: ToolShedApp
    repository: Optional[Repository]  # type:ignore[assignment]

    # why is mypy making me re-annotate these things from the base class, it didn't
    # when they were in the same file
    invalid_file_tups: List[InvalidFileT]
    repository_clone_url: Optional[str]

    def __init__(
        self,
        trans: ProvidesRepositoriesContext,
        repository: Optional[Repository] = None,
        changeset_revision: Optional[str] = None,
        repository_clone_url: Optional[str] = None,
        shed_config_dict: Optional[Dict[str, Any]] = None,
        relative_install_dir=None,
        repository_files_dir=None,
        resetting_all_metadata_on_repository=False,
        updating_installed_repository=False,
        persist=False,
        metadata_dict=None,
        user=None,
    ):
        self.trans = trans
        self.app = trans.app
        self.user = user
        self.repository = repository
        if changeset_revision is None and self.repository is not None:
            self.changeset_revision = self.repository.tip()
        else:
            self.changeset_revision = changeset_revision
        if repository_clone_url is None and self.repository is not None:
            self.repository_clone_url = common_util.generate_clone_url_for(self.trans, self.repository)
        else:
            self.repository_clone_url = repository_clone_url
        if shed_config_dict is None:
            self.shed_config_dict = {}
        else:
            self.shed_config_dict = shed_config_dict
        if relative_install_dir is None and self.repository is not None:
            relative_install_dir = self.repository.repo_path(self.app)
        if repository_files_dir is None and self.repository is not None:
            repository_files_dir = self.repository.repo_path(self.app)
        if metadata_dict is None:
            self.metadata_dict = {}
        else:
            self.metadata_dict = metadata_dict
        self.relative_install_dir = relative_install_dir
        self.repository_files_dir = repository_files_dir
        self.resetting_all_metadata_on_repository = resetting_all_metadata_on_repository
        self.updating_installed_repository = updating_installed_repository
        self.persist = persist
        self.invalid_file_tups = []
        self.sa_session = trans.app.model.session

    def initial_metadata_dict(self) -> Dict[str, Any]:
        return {}

    def set_repository(
        self, repository, relative_install_dir: Optional[str] = None, changeset_revision: Optional[str] = None
    ):
        self.repository = repository
        if relative_install_dir is None and self.repository is not None:
            relative_install_dir = repository.repo_path(self.app)
        if changeset_revision is None and self.repository is not None:
            self.set_changeset_revision(self.repository.tip())
        else:
            self.set_changeset_revision(changeset_revision)
        self.shed_config_dict = {}
        self._reset_attributes_after_repository_update(relative_install_dir)

    def handle_repository_elem(self, repository_elem, only_if_compiling_contained_td=False) -> HandleResultT:
        """
        Process the received repository_elem which is a <repository> tag either from a
        repository_dependencies.xml file or a tool_dependencies.xml file.  If the former,
        we're generating repository dependencies metadata for a repository in the Tool Shed.
        If the latter, we're generating package dependency metadata within Galaxy or the
        Tool Shed.
        """
        is_valid = True
        error_message = ""
        toolshed = repository_elem.get("toolshed", None)
        name = repository_elem.get("name", None)
        owner = repository_elem.get("owner", None)
        changeset_revision = repository_elem.get("changeset_revision", None)
        prior_installation_required = str(repository_elem.get("prior_installation_required", False))
        repository_dependency_tup = [
            toolshed,
            name,
            owner,
            changeset_revision,
            prior_installation_required,
            str(only_if_compiling_contained_td),
        ]
        if not toolshed:
            # Default to the current tool shed.
            toolshed = self.trans.repositories_hostname
            log.warning(f"\n\n\n\n\n\nin not toolshed with {toolshed}\n\n\n\n")
            # toolshed = str(url_for("/", qualified=True)).rstrip("/")
            repository_dependency_tup[0] = toolshed
        else:
            log.warning(f"moooocww.....{toolshed}\n\n\n\n\n")
        toolshed = common_util.remove_protocol_from_tool_shed_url(toolshed)

        if suc.tool_shed_is_this_tool_shed(toolshed, trans=self.trans):
            try:
                user = get_user_by_username(self.sa_session, owner)
            except Exception:
                error_message = (
                    f"Ignoring repository dependency definition for tool shed {toolshed}, name {name}, owner {owner}, "
                )
                error_message += f"changeset revision {changeset_revision} because the owner is invalid."
                log.debug(error_message)
                is_valid = False
                return repository_dependency_tup, is_valid, error_message
            try:
                repository = get_repository(self.sa_session, name, user.id)
            except Exception:
                error_message = f"Ignoring repository dependency definition for tool shed {toolshed},"
                error_message += f"name {name}, owner {owner}, "
                error_message += f"changeset revision {changeset_revision} because the name is invalid.  "
                log.debug(error_message)
                is_valid = False
                return repository_dependency_tup, is_valid, error_message
            repo = repository.hg_repo

            # The received changeset_revision may be None since defining it in the dependency definition is optional.
            # If this is the case, the default will be to set its value to the repository dependency tip revision.
            # This probably occurs only when handling circular dependency definitions.
            tip_ctx = repo[repo.changelog.tip()]
            # Make sure the repo.changlog includes at least 1 revision.
            if changeset_revision is None and tip_ctx.rev() >= 0:
                changeset_revision = str(tip_ctx)
                repository_dependency_tup = [
                    toolshed,
                    name,
                    owner,
                    changeset_revision,
                    prior_installation_required,
                    str(only_if_compiling_contained_td),
                ]
                return repository_dependency_tup, is_valid, error_message
            else:
                # Find the specified changeset revision in the repository's changelog to see if it's valid.
                found = False
                for changeset in repo.changelog:
                    changeset_hash = str(repo[changeset])
                    if changeset_hash == changeset_revision:
                        found = True
                        break
                if not found:
                    error_message = f"Ignoring repository dependency definition for tool shed {toolshed}, name {name}, owner {owner}, "
                    error_message += (
                        f"changeset revision {changeset_revision} because the changeset revision is invalid.  "
                    )
                    log.debug(error_message)
                    is_valid = False
                    return repository_dependency_tup, is_valid, error_message
        else:
            # Repository dependencies are currently supported within a single tool shed.
            error_message = "Repository dependencies are currently supported only within the same tool shed.  Ignoring "
            error_message += f"repository dependency definition  for tool shed {toolshed}, name {name}, owner {owner}, changeset revision {changeset_revision}.  "
            log.debug(error_message)
            is_valid = False
            return repository_dependency_tup, is_valid, error_message
        return repository_dependency_tup, is_valid, error_message


class RepositoryMetadataManager(ToolShedMetadataGenerator):
    def __init__(
        self,
        trans: ProvidesRepositoriesContext,
        repository=None,
        changeset_revision=None,
        repository_clone_url=None,
        shed_config_dict=None,
        relative_install_dir=None,
        repository_files_dir=None,
        resetting_all_metadata_on_repository=False,
        updating_installed_repository=False,
        persist=False,
        metadata_dict=None,
    ):
        super().__init__(
            trans,
            repository,
            changeset_revision,
            repository_clone_url,
            shed_config_dict,
            relative_install_dir,
            repository_files_dir,
            resetting_all_metadata_on_repository,
            updating_installed_repository,
            persist,
            metadata_dict=metadata_dict,
            user=trans.user,
        )
        app = trans.app
        user = trans.user
        self.sa_session = app.model.context
        self.app = app
        self.user = user
        # Repository metadata comparisons for changeset revisions.
        self.EQUAL = "equal"
        self.NO_METADATA = "no metadata"
        self.NOT_EQUAL_AND_NOT_SUBSET = "not equal and not subset"
        self.SUBSET = "subset"
        self.SUBSET_VALUES = [self.EQUAL, self.SUBSET]

    def _add_tool_versions(self, id: int, repository_metadata, changeset_revisions):
        # Build a dictionary of { 'tool id' : 'parent tool id' } pairs for each tool in repository_metadata.
        metadata = repository_metadata.metadata
        tool_versions_dict = {}
        for tool_dict in metadata.get("tools", []):
            # We have at least 2 changeset revisions to compare tool guids and tool ids.
            parent_id = self._get_parent_id(
                id, tool_dict["id"], tool_dict["version"], tool_dict["guid"], changeset_revisions
            )
            tool_versions_dict[tool_dict["guid"]] = parent_id
        if tool_versions_dict:
            repository_metadata.tool_versions = tool_versions_dict
            self.sa_session.add(repository_metadata)
            session = self.sa_session()
            session.commit()

    def build_repository_ids_select_field(
        self, name="repository_ids", multiple=True, display="checkboxes", my_writable=False
    ):
        """Generate the current list of repositories for resetting metadata."""
        repositories_select_field = SelectField(name=name, multiple=multiple, display=display)
        for repository in self.get_repositories_for_setting_metadata(my_writable=my_writable, order=True):
            owner = str(repository.user.username)
            option_label = f"{str(repository.name)} ({owner})"
            option_value = f"{self.app.security.encode_id(repository.id)}"
            repositories_select_field.add_option(option_label, option_value)
        return repositories_select_field

    def _clean_repository_metadata(self, changeset_revisions):
        assert self.repository
        # Delete all repository_metadata records associated with the repository that have
        # a changeset_revision that is not in changeset_revisions.  We sometimes see multiple
        # records with the same changeset revision value - no idea how this happens. We'll
        # assume we can delete the older records, so we'll order by update_time descending and
        # delete records that have the same changeset_revision we come across later.
        for repository_metadata in get_repository_metadata(self.sa_session, self.repository.id):
            changeset_revision = repository_metadata.changeset_revision
            if changeset_revision not in changeset_revisions:
                self.sa_session.delete(repository_metadata)
                session = self.sa_session()
                session.commit()

    def compare_changeset_revisions(self, ancestor_changeset_revision, ancestor_metadata_dict):
        """
        Compare the contents of two changeset revisions to determine if a new repository
        metadata revision should be created.
        """
        # The metadata associated with ancestor_changeset_revision is ancestor_metadata_dict.
        # This changeset_revision is an ancestor of self.changeset_revision which is associated
        # with self.metadata_dict.  A new repository_metadata record will be created only
        # when this method returns the constant value self.NOT_EQUAL_AND_NOT_SUBSET.
        ancestor_tools = ancestor_metadata_dict.get("tools", [])
        ancestor_guids = [tool_dict["guid"] for tool_dict in ancestor_tools]
        ancestor_guids.sort()
        ancestor_repository_dependencies_dict = ancestor_metadata_dict.get("repository_dependencies", {})
        ancestor_repository_dependencies = ancestor_repository_dependencies_dict.get("repository_dependencies", [])
        ancestor_tool_dependencies = ancestor_metadata_dict.get("tool_dependencies", {})
        ancestor_data_manager = ancestor_metadata_dict.get("data_manager", {})
        current_tools = self.metadata_dict.get("tools", [])
        current_guids = [tool_dict["guid"] for tool_dict in current_tools]
        current_guids.sort()
        current_repository_dependencies_dict = self.metadata_dict.get("repository_dependencies", {})
        current_repository_dependencies = current_repository_dependencies_dict.get("repository_dependencies", [])
        current_tool_dependencies = self.metadata_dict.get("tool_dependencies", {})
        current_data_manager = self.metadata_dict.get("data_manager", {})
        # Handle case where no metadata exists for either changeset.
        no_repository_dependencies = not ancestor_repository_dependencies and not current_repository_dependencies
        no_tool_dependencies = not ancestor_tool_dependencies and not current_tool_dependencies
        no_tools = not ancestor_guids and not current_guids
        no_data_manager = not ancestor_data_manager and not current_data_manager
        if no_repository_dependencies and no_tool_dependencies and no_tools and no_data_manager:
            return self.NO_METADATA
        repository_dependency_comparison = self.compare_repository_dependencies(
            ancestor_repository_dependencies, current_repository_dependencies
        )
        tool_dependency_comparison = self.compare_tool_dependencies(
            ancestor_tool_dependencies, current_tool_dependencies
        )
        data_manager_comparison = self.compare_data_manager(ancestor_data_manager, current_data_manager)
        # Handle case where all metadata is the same.
        if (
            ancestor_guids == current_guids
            and repository_dependency_comparison == self.EQUAL
            and tool_dependency_comparison == self.EQUAL
            and data_manager_comparison == self.EQUAL
        ):
            return self.EQUAL
        # Handle case where ancestor metadata is a subset of current metadata.
        # readme_file_is_subset = readme_file_comparision in [ self.EQUAL, self.SUBSET ]
        repository_dependency_is_subset = repository_dependency_comparison in self.SUBSET_VALUES
        tool_dependency_is_subset = tool_dependency_comparison in self.SUBSET_VALUES
        datamanager_is_subset = data_manager_comparison in self.SUBSET_VALUES
        if repository_dependency_is_subset and tool_dependency_is_subset and datamanager_is_subset:
            is_subset = True
            for guid in ancestor_guids:
                if guid not in current_guids:
                    is_subset = False
                    break
            if is_subset:
                return self.SUBSET
        return self.NOT_EQUAL_AND_NOT_SUBSET

    def compare_data_manager(self, ancestor_metadata, current_metadata):
        """Determine if ancestor_metadata is the same as or a subset of current_metadata for data_managers."""

        def __data_manager_dict_to_tuple_list(metadata_dict):
            # we do not check tool_guid or tool conf file name
            return {
                (
                    name,
                    tuple(sorted(value.get("data_tables", []))),
                    value.get("guid"),
                    value.get("version"),
                    value.get("name"),
                    value.get("id"),
                )
                for name, value in metadata_dict.items()
            }

        # only compare valid entries, any invalid entries are ignored
        ancestor_metadata = __data_manager_dict_to_tuple_list(ancestor_metadata.get("data_managers", {}))
        current_metadata = __data_manager_dict_to_tuple_list(current_metadata.get("data_managers", {}))
        # use set comparisons
        if ancestor_metadata.issubset(current_metadata):
            if ancestor_metadata == current_metadata:
                return self.EQUAL
            return self.SUBSET
        return self.NOT_EQUAL_AND_NOT_SUBSET

    def compare_repository_dependencies(self, ancestor_repository_dependencies, current_repository_dependencies):
        """
        Determine if ancestor_repository_dependencies is the same as or a subset of
        current_repository_dependencies.
        """
        # The list of repository_dependencies looks something like:
        # [["http://localhost:9009", "emboss_datatypes", "test", "ab03a2a5f407", "False", "False"]].
        # Create a string from each tuple in the list for easier comparison.
        if len(ancestor_repository_dependencies) <= len(current_repository_dependencies):
            for ancestor_tup in ancestor_repository_dependencies:
                (
                    a_tool_shed,
                    a_repo_name,
                    a_repo_owner,
                    a_changeset_revision,
                    a_prior_installation_required,
                    a_only_if_compiling_contained_td,
                ) = ancestor_tup
                cleaned_a_tool_shed = common_util.remove_protocol_from_tool_shed_url(a_tool_shed)
                found_in_current = False
                for current_tup in current_repository_dependencies:
                    (
                        c_tool_shed,
                        c_repo_name,
                        c_repo_owner,
                        c_changeset_revision,
                        c_prior_installation_required,
                        c_only_if_compiling_contained_td,
                    ) = current_tup
                    cleaned_c_tool_shed = common_util.remove_protocol_from_tool_shed_url(c_tool_shed)
                    if (
                        cleaned_c_tool_shed == cleaned_a_tool_shed
                        and c_repo_name == a_repo_name
                        and c_repo_owner == a_repo_owner
                        and c_changeset_revision == a_changeset_revision
                        and util.string_as_bool(c_prior_installation_required)
                        == util.string_as_bool(a_prior_installation_required)
                        and util.string_as_bool(c_only_if_compiling_contained_td)
                        == util.string_as_bool(a_only_if_compiling_contained_td)
                    ):
                        found_in_current = True
                        break
                if not found_in_current:
                    # In some cases, the only difference between a dependency definition in the lists
                    # is the changeset_revision value.  We'll check to see if this is the case, and if
                    # the defined dependency is a repository that has metadata set only on its tip.
                    if not self.different_revision_defines_tip_only_repository_dependency(
                        ancestor_tup, current_repository_dependencies
                    ):
                        return self.NOT_EQUAL_AND_NOT_SUBSET
                    return self.SUBSET
            if len(ancestor_repository_dependencies) == len(current_repository_dependencies):
                return self.EQUAL
            else:
                return self.SUBSET
        return self.NOT_EQUAL_AND_NOT_SUBSET

    def compare_tool_dependencies(self, ancestor_tool_dependencies, current_tool_dependencies):
        """
        Determine if ancestor_tool_dependencies is the same as or a subset of current_tool_dependencies.
        """
        # The tool_dependencies dictionary looks something like:
        # {'bwa/0.5.9': {'readme': 'some string', 'version': '0.5.9', 'type': 'package', 'name': 'bwa'}}
        if len(ancestor_tool_dependencies) <= len(current_tool_dependencies):
            for ancestor_td_key in ancestor_tool_dependencies.keys():
                if ancestor_td_key in current_tool_dependencies:
                    # The only values that could have changed between the 2 dictionaries are the
                    # "readme" or "type" values.  Changing the readme value makes no difference.
                    # Changing the type will change the installation process, but for now we'll
                    # assume it was a typo, so new metadata shouldn't be generated.
                    continue
                else:
                    return self.NOT_EQUAL_AND_NOT_SUBSET
            # At this point we know that ancestor_tool_dependencies is at least a subset of current_tool_dependencies.
            if len(ancestor_tool_dependencies) == len(current_tool_dependencies):
                return self.EQUAL
            else:
                return self.SUBSET
        return self.NOT_EQUAL_AND_NOT_SUBSET

    def create_or_update_repository_metadata(self, changeset_revision, metadata_dict):
        """Create or update a repository_metadata record in the tool shed."""
        has_repository_dependencies = False
        has_repository_dependencies_only_if_compiling_contained_td = False
        includes_tools = False
        includes_tool_dependencies = False
        if metadata_dict:
            repository_dependencies_dict = metadata_dict.get("repository_dependencies", {})
            repository_dependencies = repository_dependencies_dict.get("repository_dependencies", [])
            (
                has_repository_dependencies,
                has_repository_dependencies_only_if_compiling_contained_td,
            ) = repository_util.get_repository_dependency_types(repository_dependencies)
            if "tools" in metadata_dict:
                includes_tools = True
            if "tool_dependencies" in metadata_dict:
                includes_tool_dependencies = True
        if (
            has_repository_dependencies
            or has_repository_dependencies_only_if_compiling_contained_td
            or includes_tools
            or includes_tool_dependencies
        ):
            downloadable = True
        else:
            downloadable = False
        assert self.repository
        repository_metadata = repository_metadata_by_changeset_revision(
            self.app.model, self.repository.id, changeset_revision
        )
        if repository_metadata:
            repository_metadata.metadata = metadata_dict
            repository_metadata.downloadable = downloadable
            repository_metadata.has_repository_dependencies = has_repository_dependencies
            repository_metadata.includes_datatypes = False
            repository_metadata.includes_tools = includes_tools
            repository_metadata.includes_tool_dependencies = includes_tool_dependencies
            repository_metadata.includes_workflows = False
        else:
            repository_metadata = self.app.model.RepositoryMetadata(
                repository_id=self.repository.id,
                changeset_revision=changeset_revision,
                metadata=metadata_dict,
                downloadable=downloadable,
                has_repository_dependencies=has_repository_dependencies,
                includes_datatypes=False,
                includes_tools=includes_tools,
                includes_tool_dependencies=includes_tool_dependencies,
                includes_workflows=False,
            )
        assert repository_metadata
        # Always set the default values for the following columns.  When resetting all metadata
        # on a repository this will reset the values.
        assert repository_metadata
        repository_metadata.missing_test_components = False
        self.sa_session.add(repository_metadata)
        session = self.sa_session()
        session.commit()

        return repository_metadata

    def different_revision_defines_tip_only_repository_dependency(self, rd_tup, repository_dependencies):
        """
        Determine if the only difference between rd_tup and a dependency definition in the list of
        repository_dependencies is the changeset_revision value.
        """
        (
            rd_tool_shed,
            rd_name,
            rd_owner,
            rd_changeset_revision,
            rd_prior_installation_required,
            rd_only_if_compiling_contained_td,
        ) = common_util.parse_repository_dependency_tuple(rd_tup)
        cleaned_rd_tool_shed = common_util.remove_protocol_from_tool_shed_url(rd_tool_shed)
        for repository_dependency in repository_dependencies:
            (
                tool_shed,
                name,
                owner,
                changeset_revision,
                prior_installation_required,
                only_if_compiling_contained_td,
            ) = common_util.parse_repository_dependency_tuple(repository_dependency)
            cleaned_tool_shed = common_util.remove_protocol_from_tool_shed_url(tool_shed)
            if cleaned_rd_tool_shed == cleaned_tool_shed and rd_name == name and rd_owner == owner:
                # Determine if the repository represented by the dependency tuple is an instance of the repository type TipOnly.
                required_repository = get_repository_by_name_and_owner(self.app.model.context, name, owner)
                repository_type_class = self.app.repository_types_registry.get_class_by_label(required_repository.type)
                return isinstance(repository_type_class, TipOnly)
        return False

    def _get_parent_id(self, id: int, old_id, version, guid, changeset_revisions):
        parent_id = None
        # Compare from most recent to oldest.
        changeset_revisions.reverse()
        for changeset_revision in changeset_revisions:
            repository_metadata = repository_metadata_by_changeset_revision(self.app.model, id, changeset_revision)
            assert repository_metadata
            metadata = repository_metadata.metadata
            tools_dicts = metadata.get("tools", [])
            for tool_dict in tools_dicts:
                if tool_dict["guid"] == guid:
                    # The tool has not changed between the compared changeset revisions.
                    continue
                if tool_dict["id"] == old_id and tool_dict["version"] != version:
                    # The tool version is different, so we've found the parent.
                    return tool_dict["guid"]
        if parent_id is None:
            # The tool did not change through all of the changeset revisions.
            return old_id

    def get_repositories_for_setting_metadata(self, my_writable=False, order=True):
        """
        Return a list of repositories for resetting metadata.  The order parameter
        is used for displaying the list of repositories ordered alphabetically for display on
        a page.  When called from the Tool Shed API, order is False.
        """
        # When called from the Tool Shed API, the metadata is reset on all repositories of types
        # repository_suite_definition and tool_dependency_definition in addition to other selected
        # repositories.
        if my_writable:
            username = self.user.username
            repo_ids = []
            for repository in get_current_repositories(self.sa_session):
                # Always reset metadata on all repositories of types repository_suite_definition and
                # tool_dependency_definition.
                if repository.type in [rt_util.REPOSITORY_SUITE_DEFINITION, rt_util.TOOL_DEPENDENCY_DEFINITION]:
                    repo_ids.append(repository.id)
                else:
                    allow_push = repository.allow_push()
                    if allow_push:
                        # Include all repositories that are writable by the current user.
                        allow_push_usernames = allow_push.split(",")
                        if username in allow_push_usernames:
                            repo_ids.append(repository.id)
            if repo_ids:
                return get_filtered_repositories(self.sa_session, repo_ids, order)
            else:
                return []
        else:
            return get_current_repositories(self.sa_session, order)

    def new_metadata_required_for_utilities(self):
        """
        This method compares the last stored repository_metadata record associated with self.repository
        against the contents of self.metadata_dict and returns True or False for the union set of Galaxy
        utilities contained in both metadata dictionaries.  The metadata contained in self.metadata_dict
        may not be a subset of that contained in the last stored repository_metadata record associated with
        self.repository because one or more Galaxy utilities may have been deleted from self.repository in
        the new tip.
        """
        assert self.repository
        repository_metadata = metadata_util.get_latest_repository_metadata(
            self.app, self.repository.id, downloadable=False
        )
        repository_dependencies_required = self.new_repository_dependency_metadata_required(repository_metadata)
        tools_required = self.new_tool_metadata_required(repository_metadata)
        tool_dependencies_required = self.new_tool_dependency_metadata_required(repository_metadata)
        data_managers_required = self.new_data_manager_required(repository_metadata)
        if repository_dependencies_required or tools_required or tool_dependencies_required or data_managers_required:
            return True
        return False

    def new_repository_dependency_metadata_required(self, repository_metadata):
        """
        Compare the last saved metadata for each repository dependency in the repository
        with the new metadata in self.metadata_dict to determine if a new repository_metadata
        table record is required or if the last saved metadata record can be updated for
        repository_dependencies instead.
        """
        if repository_metadata:
            metadata = repository_metadata.metadata
            if "repository_dependencies" in metadata:
                saved_repository_dependencies = metadata["repository_dependencies"]["repository_dependencies"]
                new_repository_dependencies_metadata = self.metadata_dict.get("repository_dependencies", None)
                if new_repository_dependencies_metadata:
                    new_repository_dependencies = self.metadata_dict["repository_dependencies"][
                        "repository_dependencies"
                    ]
                    # TODO: We used to include the following here to handle the case where repository
                    # dependency definitions were deleted.  However this erroneously returned True in
                    # cases where is should not have done so.  This usually occurred where multiple single
                    # files were uploaded when a single tarball should have been.  We need to implement
                    # support for handling deleted repository dependency definitions so that we can guarantee
                    # reproducibility, but we need to do it in a way that is better than the following.
                    # for new_repository_dependency in new_repository_dependencies:
                    #     if new_repository_dependency not in saved_repository_dependencies:
                    #         return True
                    # The saved metadata must be a subset of the new metadata.
                    for saved_repository_dependency in saved_repository_dependencies:
                        if saved_repository_dependency not in new_repository_dependencies:
                            # In some cases, the only difference between a dependency definition in the lists
                            # is the changeset_revision value.  We'll check to see if this is the case, and if
                            # the defined dependency is a repository that has metadata set only on its tip.
                            if not self.different_revision_defines_tip_only_repository_dependency(
                                saved_repository_dependency, new_repository_dependencies
                            ):
                                return True
                    return False
                else:
                    # The repository_dependencies.xml file must have been deleted, so create a new
                    # repository_metadata record so we always have access to the deleted file.
                    return True
            else:
                return False
        else:
            if "repository_dependencies" in self.metadata_dict:
                # There is no saved repository metadata, so we need to create a new repository_metadata record.
                return True
            else:
                # self.metadata_dict includes no metadata for repository dependencies, so a new repository_metadata
                # record is not needed.
                return False

    def new_data_manager_required(self, repository_metadata):
        if self.metadata_dict and repository_metadata and repository_metadata.metadata:
            return self.compare_data_manager(self.metadata_dict, repository_metadata.metadata) != self.EQUAL
        else:
            return bool(
                repository_metadata
                and repository_metadata.metadata
                and repository_metadata.metadata.get("data_managers")
            )

    def new_tool_metadata_required(self, repository_metadata):
        """
        Compare the last saved metadata for each tool in the repository with the new metadata in
        self.metadata_dict to determine if a new repository_metadata table record is required, or if
        the last saved metadata record can be updated instead.
        """
        if "tools" in self.metadata_dict:
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if "tools" in metadata:
                        saved_tool_ids = []
                        # The metadata for one or more tools was successfully generated in the past
                        # for this repository, so we first compare the version string for each tool id
                        # in self.metadata_dict with what was previously saved to see if we need to create
                        # a new table record or if we can simply update the existing record.
                        for new_tool_metadata_dict in self.metadata_dict["tools"]:
                            for saved_tool_metadata_dict in metadata["tools"]:
                                if saved_tool_metadata_dict["id"] not in saved_tool_ids:
                                    saved_tool_ids.append(saved_tool_metadata_dict["id"])
                                if new_tool_metadata_dict["id"] == saved_tool_metadata_dict["id"]:
                                    if new_tool_metadata_dict["version"] != saved_tool_metadata_dict["version"]:
                                        return True
                        # So far, a new metadata record is not required, but we still have to check to see if
                        # any new tool ids exist in self.metadata_dict that are not in the saved metadata.  We do
                        # this because if a new tarball was uploaded to a repository that included tools, it
                        # may have removed existing tool files if they were not included in the uploaded tarball.
                        for new_tool_metadata_dict in self.metadata_dict["tools"]:
                            if new_tool_metadata_dict["id"] not in saved_tool_ids:
                                return True
                        return False
                    else:
                        # The new metadata includes tools, but the stored metadata does not, so we can
                        # update the stored metadata.
                        return False
                else:
                    # There is no stored metadata, so we can update the metadata column in the
                    # repository_metadata table.
                    return False
            else:
                # There is no stored repository metadata, so we need to create a new repository_metadata
                # table record.
                return True
        # self.metadata_dict includes no metadata for tools, so a new repository_metadata table
        # record is not needed.
        return False

    def new_tool_dependency_metadata_required(self, repository_metadata):
        """
        Compare the last saved metadata for each tool dependency in the repository with the new
        metadata in self.metadata_dict to determine if a new repository_metadata table record is
        required or if the last saved metadata record can be updated for tool_dependencies instead.
        """
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                if "tool_dependencies" in metadata:
                    saved_tool_dependencies = metadata["tool_dependencies"]
                    new_tool_dependencies = self.metadata_dict.get("tool_dependencies", None)
                    if new_tool_dependencies:
                        # TODO: We used to include the following here to handle the case where
                        # tool dependency definitions were deleted.  However, this erroneously
                        # returned True in cases where is should not have done so.  This usually
                        # occurred where multiple single files were uploaded when a single tarball
                        # should have been.  We need to implement support for handling deleted
                        # tool dependency definitions so that we can guarantee reproducibility,
                        # but we need to do it in a way that is better than the following.
                        # for new_tool_dependency in new_tool_dependencies:
                        #     if new_tool_dependency not in saved_tool_dependencies:
                        #         return True
                        # The saved metadata must be a subset of the new metadata.
                        for saved_tool_dependency in saved_tool_dependencies:
                            if saved_tool_dependency not in new_tool_dependencies:
                                return True
                        return False
                    else:
                        # The tool_dependencies.xml file must have been deleted, so create a new
                        # repository_metadata record so we always have
                        # access to the deleted file.
                        return True
                else:
                    return False
            else:
                # We have repository metadata that does not include metadata for any tool dependencies
                # in the repository, so we can update the existing repository metadata.
                return False
        else:
            if "tool_dependencies" in self.metadata_dict:
                # There is no saved repository metadata, so we need to create a new repository_metadata
                # record.
                return True
            else:
                # self.metadata_dict includes no metadata for tool dependencies, so a new repository_metadata
                # record is not needed.
                return False

    def reset_all_metadata_on_repository_in_tool_shed(self, repository_clone_url=None):
        """Reset all metadata on a single repository in a tool shed."""
        assert self.repository
        log.debug(f"Resetting all metadata on repository: {self.repository.name}")
        repo = self.repository.hg_repo
        # The list of changeset_revisions refers to repository_metadata records that have been created
        # or updated.  When the following loop completes, we'll delete all repository_metadata records
        # for this repository that do not have a changeset_revision value in this list.
        changeset_revisions: List[Optional[str]] = []
        # When a new repository_metadata record is created, it always uses the values of
        # metadata_changeset_revision and metadata_dict.
        metadata_changeset_revision = None
        metadata_dict = None
        ancestor_changeset_revision = None
        ancestor_metadata_dict = None
        for changeset in self.repository.get_changesets_for_setting_metadata(self.app):
            work_dir = tempfile.mkdtemp(prefix="tmp-toolshed-ramorits")
            ctx = repo[changeset]
            log.debug("Cloning repository changeset revision: %s", str(ctx.rev()))
            assert self.repository_clone_url
            repository_clone_url = repository_clone_url or self.repository_clone_url
            cloned_ok, error_message = hg_util.clone_repository(repository_clone_url, work_dir, str(ctx.rev()))
            if cloned_ok:
                log.debug("Generating metadata for changeset revision: %s", str(ctx.rev()))
                self.set_changeset_revision(str(ctx))
                self.set_repository_files_dir(work_dir)
                self.generate_metadata_for_changeset_revision()
                if self.metadata_dict:
                    if metadata_changeset_revision is None and metadata_dict is None:
                        # We're at the first change set in the change log.
                        metadata_changeset_revision = self.changeset_revision
                        metadata_dict = self.metadata_dict
                    if ancestor_changeset_revision:
                        # Compare metadata from ancestor and current.  The value of comparison will be one of:
                        # self.NO_METADATA - no metadata for either ancestor or current, so continue from current
                        # self.EQUAL - ancestor metadata is equivalent to current metadata, so continue from current
                        # self.SUBSET - ancestor metadata is a subset of current metadata, so continue from current
                        # self.NOT_EQUAL_AND_NOT_SUBSET - ancestor metadata is neither equal to nor a subset of current
                        # metadata, so persist ancestor metadata.
                        log.info(f"amd {ancestor_metadata_dict}")
                        comparison = self.compare_changeset_revisions(
                            ancestor_changeset_revision, ancestor_metadata_dict
                        )
                        log.info(f"comparison {comparison}")
                        if comparison in [self.NO_METADATA, self.EQUAL, self.SUBSET]:
                            ancestor_changeset_revision = self.changeset_revision
                            ancestor_metadata_dict = self.metadata_dict
                        elif comparison == self.NOT_EQUAL_AND_NOT_SUBSET:
                            metadata_changeset_revision = ancestor_changeset_revision
                            metadata_dict = ancestor_metadata_dict
                            self.create_or_update_repository_metadata(metadata_changeset_revision, metadata_dict)
                            changeset_revisions.append(metadata_changeset_revision)
                            ancestor_changeset_revision = self.changeset_revision
                            ancestor_metadata_dict = self.metadata_dict
                    else:
                        # We're at the beginning of the change log.
                        ancestor_changeset_revision = self.changeset_revision
                        ancestor_metadata_dict = self.metadata_dict
                    if not ctx.children():
                        metadata_changeset_revision = self.changeset_revision
                        metadata_dict = self.metadata_dict
                        # We're at the end of the change log.
                        self.create_or_update_repository_metadata(metadata_changeset_revision, metadata_dict)
                        changeset_revisions.append(metadata_changeset_revision)
                        ancestor_changeset_revision = None
                        ancestor_metadata_dict = None
                elif ancestor_metadata_dict:
                    # We reach here only if self.metadata_dict is empty and ancestor_metadata_dict is not.
                    if not ctx.children():
                        # We're at the end of the change log.
                        self.create_or_update_repository_metadata(metadata_changeset_revision, metadata_dict)
                        changeset_revisions.append(metadata_changeset_revision)
                        ancestor_changeset_revision = None
                        ancestor_metadata_dict = None
            basic_util.remove_dir(work_dir)
        # Delete all repository_metadata records for this repository that do not have a changeset_revision
        # value in changeset_revisions.
        self._clean_repository_metadata(changeset_revisions)
        # Set tool version information for all downloadable changeset revisions.  Get the list of changeset
        # revisions from the changelog.
        self._reset_all_tool_versions(repo)

    def _reset_all_tool_versions(self, repo):
        """Reset tool version lineage for those changeset revisions that include valid tools."""
        assert self.repository
        changeset_revisions_that_contain_tools = _get_changeset_revisions_that_contain_tools(
            self.app, repo, self.repository
        )
        # The list of changeset_revisions_that_contain_tools is now filtered to contain only those that
        # are downloadable and contain tools.  If a repository includes tools, build a dictionary of
        # { 'tool id' : 'parent tool id' } pairs for each tool in each changeset revision.
        for index, changeset_revision in enumerate(changeset_revisions_that_contain_tools):
            tool_versions_dict = {}
            repository_metadata = repository_metadata_by_changeset_revision(
                self.app.model, self.repository.id, changeset_revision
            )
            assert repository_metadata
            metadata = repository_metadata.metadata
            tool_dicts = metadata["tools"]
            if index == 0:
                # The first changeset_revision is a special case because it will have no ancestor
                # changeset_revisions in which to match tools.  The parent tool id for tools in the
                # first changeset_revision will be the "old_id" in the tool config.
                for tool_dict in tool_dicts:
                    tool_versions_dict[tool_dict["guid"]] = tool_dict["id"]
            else:
                for tool_dict in tool_dicts:
                    parent_id = self._get_parent_id(
                        self.repository.id,
                        tool_dict["id"],
                        tool_dict["version"],
                        tool_dict["guid"],
                        changeset_revisions_that_contain_tools[0:index],
                    )
                    tool_versions_dict[tool_dict["guid"]] = parent_id
            if tool_versions_dict:
                repository_metadata.tool_versions = tool_versions_dict
                self.sa_session.add(repository_metadata)
                session = self.sa_session()
                session.commit()

    def reset_metadata_on_selected_repositories(self, **kwd):
        """
        Inspect the repository changelog to reset metadata for all appropriate changeset revisions.
        This method is called from both Galaxy and the Tool Shed.
        """
        message = ""
        status = "done"
        if repository_ids := util.listify(kwd.get("repository_ids", None)):
            successful_count = 0
            unsuccessful_count = 0
            for repository_id in repository_ids:
                try:
                    repository = repository_util.get_repository_in_tool_shed(self.app, repository_id)
                    self.set_repository(repository)
                    self.resetting_all_metadata_on_repository = True
                    self.reset_all_metadata_on_repository_in_tool_shed()
                    if self.invalid_file_tups:
                        message = tool_util.generate_message_for_invalid_tools(
                            self.app, self.invalid_file_tups, repository, None, as_html=False
                        )
                        log.debug(message)
                        unsuccessful_count += 1
                    else:
                        log.debug(
                            "Successfully reset metadata on repository %s owned by %s",
                            repository.name,
                            repository.user.username,
                        )
                        successful_count += 1
                except Exception:
                    log.exception("Error attempting to reset metadata on repository %s", str(repository.name))
                    unsuccessful_count += 1
            message = "Successfully reset metadata on {} {}.  ".format(
                successful_count,
                inflector.cond_plural(successful_count, "repository"),
            )
            if unsuccessful_count:
                message += "Error setting metadata on {} {} - see the paster log for details.  ".format(
                    unsuccessful_count,
                    inflector.cond_plural(unsuccessful_count, "repository"),
                )
        else:
            message = "Select at least one repository to on which to reset all metadata."
            status = "error"
        return message, status

    def set_repository(
        self, repository, relative_install_dir: Optional[str] = None, changeset_revision: Optional[str] = None
    ):
        super().set_repository(repository)
        self.repository_clone_url = relative_install_dir or common_util.generate_clone_url_for(self.trans, repository)

    def set_repository_metadata(self, host, content_alert_str="", **kwd):
        """
        Set metadata using the self.repository's current disk files, returning specific error
        messages (if any) to alert the repository owner that the changeset has problems.
        """
        assert self.repository
        message = ""
        status = "done"
        repository_id = self.repository.id
        repo = self.repository.hg_repo
        self.generate_metadata_for_changeset_revision()
        if self.metadata_dict:
            repository_metadata = None
            repository_type_class = self.app.repository_types_registry.get_class_by_label(self.repository.type)
            tip_only = isinstance(repository_type_class, TipOnly)
            if not tip_only and self.new_metadata_required_for_utilities():
                # Create a new repository_metadata table row.
                repository_metadata = self.create_or_update_repository_metadata(
                    self.repository.tip(), self.metadata_dict
                )
                # If this is the first record stored for this repository, see if we need to send any email alerts.
                if len(self.repository.downloadable_revisions) == 1:
                    suc.handle_email_alerts(
                        self.app, host, self.repository, content_alert_str="", new_repo_alert=True, admin_only=False
                    )
            else:
                # Update the latest stored repository metadata with the contents and attributes of self.metadata_dict.
                repository_metadata = metadata_util.get_latest_repository_metadata(
                    self.app, repository_id, downloadable=False
                )
                if repository_metadata:
                    downloadable = metadata_util.is_downloadable(self.metadata_dict)
                    # Update the last saved repository_metadata table row.
                    repository_metadata.changeset_revision = self.repository.tip()
                    repository_metadata.metadata = self.metadata_dict
                    repository_metadata.downloadable = downloadable
                    repository_metadata.includes_datatypes = False
                    # We don't store information about the special type of repository dependency that is needed only for
                    # compiling a tool dependency defined for the dependent repository.
                    repository_dependencies_dict = self.metadata_dict.get("repository_dependencies", {})
                    repository_dependencies = repository_dependencies_dict.get("repository_dependencies", [])
                    (
                        has_repository_dependencies,
                        has_repository_dependencies_only_if_compiling_contained_td,
                    ) = repository_util.get_repository_dependency_types(repository_dependencies)
                    repository_metadata.has_repository_dependencies = has_repository_dependencies
                    if "tool_dependencies" in self.metadata_dict:
                        repository_metadata.includes_tool_dependencies = True
                    else:
                        repository_metadata.includes_tool_dependencies = False
                    if "tools" in self.metadata_dict:
                        repository_metadata.includes_tools = True
                    else:
                        repository_metadata.includes_tools = False
                    repository_metadata.includes_workflows = False
                    repository_metadata.missing_test_components = False
                    self.sa_session.add(repository_metadata)
                    session = self.sa_session()
                    session.commit()
                else:
                    # There are no metadata records associated with the repository.
                    repository_metadata = self.create_or_update_repository_metadata(
                        self.repository.tip(), self.metadata_dict
                    )
            if "tools" in self.metadata_dict and repository_metadata and status != "error":
                # Set tool versions on the new downloadable change set.  The order of the list of changesets is
                # critical, so we use the repo's changelog.
                changeset_revisions = []
                for changeset in repo.changelog:
                    changeset_revision = str(repo[changeset])
                    if repository_metadata_by_changeset_revision(self.app.model, repository_id, changeset_revision):
                        changeset_revisions.append(changeset_revision)
                self._add_tool_versions(repository_id, repository_metadata, changeset_revisions)
        elif len(repo) == 1 and not self.invalid_file_tups:
            message = (
                f"Revision <b>{self.repository.tip()}</b> includes no Galaxy utilities for which metadata can "
                "be defined so this revision cannot be automatically installed into a local Galaxy instance."
            )
            status = "error"
        if self.invalid_file_tups:
            message = tool_util.generate_message_for_invalid_tools(
                self.app, self.invalid_file_tups, self.repository, self.metadata_dict
            )
            status = "error"
        return message, status

    def set_repository_metadata_due_to_new_tip(self, host, content_alert_str=None, **kwd):
        """Set metadata on the tip of self.repository in the tool shed."""
        error_message, status = self.set_repository_metadata(host, content_alert_str=content_alert_str, **kwd)
        return status, error_message


def _get_changeset_revisions_that_contain_tools(app: "ToolShedApp", repo, repository) -> List[str]:
    changeset_revisions_that_contain_tools = []
    for changeset in repo.changelog:
        changeset_revision = str(repo[changeset])
        repository_metadata = repository_metadata_by_changeset_revision(app.model, repository.id, changeset_revision)
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                if metadata.get("tools", None):
                    changeset_revisions_that_contain_tools.append(changeset_revision)
    return changeset_revisions_that_contain_tools


def get_user_by_username(session, username):
    stmt = select(User).where(User.username == username)
    return session.execute(stmt).scalar_one()


def get_repository(session, name, user_id):
    stmt = select(Repository).where(Repository.name == name).where(Repository.user_id == user_id)
    return session.execute(stmt).scalar_one()


def get_repository_metadata(session, repository_id):
    stmt = (
        select(RepositoryMetadata)
        .where(RepositoryMetadata.repository_id == repository_id)
        .order_by(RepositoryMetadata.changeset_revision, RepositoryMetadata.update_time.desc())  # type: ignore[attr-defined]  # mapped attribute
    )
    return session.scalars(stmt)


def get_current_repositories(session, order=False):
    stmt = select(Repository).where(Repository.deleted == false())
    if order:
        stmt = stmt.order_by(Repository.name, Repository.user_id)
    return session.scalars(stmt)


def get_filtered_repositories(session, repo_ids, order):
    stmt = select(Repository).where(Repository.id.in_(repo_ids))
    if order:
        stmt = stmt.order_by(Repository.name, Repository.user_id)
    return session.scalars(stmt)
