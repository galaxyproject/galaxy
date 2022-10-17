import logging
import os

from galaxy import util
from galaxy.tool_shed.util import utility_container_manager
from galaxy.util.tool_shed.common_util import parse_repository_dependency_tuple

log = logging.getLogger(__name__)


class DependencyDisplayer:
    def __init__(self, app):
        self.app = app

    def _add_installation_directories_to_tool_dependencies(self, tool_dependencies):
        """
        Determine the path to the installation directory for each of the received
        tool dependencies.  This path will be displayed within the tool dependencies
        container on the select_tool_panel_section or reselect_tool_panel_section
        pages when installing or reinstalling repositories that contain tools with
        the defined tool dependencies.  The list of tool dependencies may be associated
        with more than a single repository.
        """
        for dependency_key, requirements_dict in tool_dependencies.items():
            if dependency_key in ["set_environment"]:
                continue
            repository_name = requirements_dict.get("repository_name", "unknown")
            repository_owner = requirements_dict.get("repository_owner", "unknown")
            changeset_revision = requirements_dict.get("changeset_revision", "unknown")
            dependency_name = requirements_dict["name"]
            version = requirements_dict["version"]
            if self.app.tool_dependency_dir:
                root_dir = self.app.tool_dependency_dir
            else:
                root_dir = "<set your tool_dependency_dir in your Galaxy configuration file>"
            install_dir = os.path.join(
                root_dir, dependency_name, version, repository_owner, repository_name, changeset_revision
            )
            requirements_dict["install_dir"] = install_dir
            tool_dependencies[dependency_key] = requirements_dict
        return tool_dependencies

    def generate_message_for_invalid_repository_dependencies(self, metadata_dict, error_from_tuple=False):
        """
        Get or generate and return an error message associated with an invalid repository dependency.
        """
        message = ""
        if metadata_dict:
            if error_from_tuple:
                # Return the error messages associated with a set of one or more invalid repository
                # dependency tuples.
                invalid_repository_dependencies_dict = metadata_dict.get("invalid_repository_dependencies", None)
                if invalid_repository_dependencies_dict is not None:
                    invalid_repository_dependencies = invalid_repository_dependencies_dict.get(
                        "invalid_repository_dependencies", []
                    )
                    for repository_dependency_tup in invalid_repository_dependencies:
                        (
                            toolshed,
                            name,
                            owner,
                            changeset_revision,
                            prior_installation_required,
                            only_if_compiling_contained_td,
                            error,
                        ) = parse_repository_dependency_tuple(repository_dependency_tup, contains_error=True)
                        if error:
                            message += f"{error}  "
            else:
                # The complete dependency hierarchy could not be determined for a repository being installed into
                # Galaxy.  This is likely due to invalid repository dependency definitions, so we'll get them from
                # the metadata and parse them for display in an error message.  This will hopefully communicate the
                # problem to the user in such a way that a resolution can be determined.
                message += (
                    "The complete dependency hierarchy could not be determined for this repository, so no required "
                )
                message += "repositories will not be installed.  This is likely due to invalid repository dependency definitions.  "
                repository_dependencies_dict = metadata_dict.get("repository_dependencies", None)
                if repository_dependencies_dict is not None:
                    rd_tups = repository_dependencies_dict.get("repository_dependencies", None)
                    if rd_tups is not None:
                        message += "Here are the attributes of the dependencies defined for this repository to help determine the "
                        message += "cause of this problem.<br/>"
                        message += '<table cellpadding="2" cellspacing="2">'
                        message += (
                            "<tr><th>Tool shed</th><th>Repository name</th><th>Owner</th><th>Changeset revision</th>"
                        )
                        message += "<th>Prior install required</th></tr>"
                        for rd_tup in rd_tups:
                            (
                                tool_shed,
                                name,
                                owner,
                                changeset_revision,
                                pir,
                                oicct,
                            ) = parse_repository_dependency_tuple(rd_tup)
                            if util.asbool(pir):
                                pir_str = "True"
                            else:
                                pir_str = ""
                            message += f"<tr><td>{tool_shed}</td><td>{name}</td><td>{owner}</td><td>{changeset_revision}</td><td>{pir_str}</td></tr>"
                        message += "</table>"
        return message

    def generate_message_for_invalid_tool_dependencies(self, metadata_dict):
        """
        Tool dependency definitions can only be invalid if they include a definition for a complex
        repository dependency and the repository dependency definition is invalid.  This method
        retrieves the error message associated with the invalid tool dependency for display in the
        caller.
        """
        message = ""
        if metadata_dict:
            invalid_tool_dependencies = metadata_dict.get("invalid_tool_dependencies", None)
            if invalid_tool_dependencies:
                for requirement_dict in invalid_tool_dependencies.values():
                    error = requirement_dict.get("error", None)
                    if error:
                        message = f"{error}  "
        return message

    def generate_message_for_orphan_tool_dependencies(self, repository, metadata_dict):
        """
        The designation of a ToolDependency into the "orphan" category has evolved over time,
        and is significantly restricted since the introduction of the TOOL_DEPENDENCY_DEFINITION
        repository type.  This designation is still critical, however, in that it handles the
        case where a repository contains both tools and a tool_dependencies.xml file, but the
        definition in the tool_dependencies.xml file is in no way related to anything defined
        by any of the contained tool's requirements tag sets.  This is important in that it is
        often a result of a typo (e.g., dependency name or version) that differs between the tool
        dependency definition within the tool_dependencies.xml file and what is defined in the
        tool config's <requirements> tag sets.  In these cases, the user should be presented with
        a warning message, and this warning message is is in fact displayed if the following
        is_orphan attribute is True.  This is tricky because in some cases it may be intentional,
        and tool dependencies that are categorized as "orphan" are in fact valid.
        """
        has_orphan_package_dependencies = False
        has_orphan_set_environment_dependencies = False
        message = ""
        package_orphans_str = ""
        set_environment_orphans_str = ""
        # Tool dependencies are categorized as orphan only if the repository contains tools.
        if metadata_dict:
            tools = metadata_dict.get("tools", [])
            tool_dependencies = metadata_dict.get("tool_dependencies", {})
            # The use of the orphan_tool_dependencies category in metadata has been deprecated,
            # but we still need to check in case the metadata is out of date.
            orphan_tool_dependencies = metadata_dict.get("orphan_tool_dependencies", {})
            # Updating should cause no problems here since a tool dependency cannot be included
            # in both dictionaries.
            tool_dependencies.update(orphan_tool_dependencies)
            if tool_dependencies and tools:
                for td_key, requirements_dict in tool_dependencies.items():
                    if td_key == "set_environment":
                        # "set_environment": [{"name": "R_SCRIPT_PATH", "type": "set_environment"}]
                        for env_requirements_dict in requirements_dict:
                            name = env_requirements_dict["name"]
                            type = env_requirements_dict["type"]
                            if self._tool_dependency_is_orphan(type, name, None, tools):
                                if not has_orphan_set_environment_dependencies:
                                    has_orphan_set_environment_dependencies = True
                                set_environment_orphans_str += f"<b>* name:</b> {name}, <b>type:</b> {type}<br/>"
                    else:
                        # "R/2.15.1": {"name": "R", "readme": "some string", "type": "package", "version": "2.15.1"}
                        name = requirements_dict["name"]
                        type = requirements_dict["type"]
                        version = requirements_dict["version"]
                        if self._tool_dependency_is_orphan(type, name, version, tools):
                            if not has_orphan_package_dependencies:
                                has_orphan_package_dependencies = True
                            package_orphans_str += (
                                f"<b>* name:</b> {name}, <b>type:</b> {type}, <b>version:</b> {version}<br/>"
                            )
        if has_orphan_package_dependencies:
            message += "The settings for <b>name</b>, <b>version</b> and <b>type</b> from a "
            message += "contained tool configuration file's <b>requirement</b> tag does not match "
            message += "the information for the following tool dependency definitions in the "
            message += "<b>tool_dependencies.xml</b> file, so these tool dependencies have no "
            message += "relationship with any tools within this repository.<br/>"
            message += package_orphans_str
        if has_orphan_set_environment_dependencies:
            message += "The settings for <b>name</b> and <b>type</b> from a contained tool "
            message += "configuration file's <b>requirement</b> tag does not match the information "
            message += "for the following tool dependency definitions in the <b>tool_dependencies.xml</b> "
            message += "file, so these tool dependencies have no relationship with any tools within "
            message += "this repository.<br/>"
            message += set_environment_orphans_str
        return message

    def populate_containers_dict_from_repository_metadata(self, repository):
        """
        Retrieve necessary information from the received repository's metadata to populate the
        containers_dict for display.  This method is called only from Galaxy (not the tool shed)
        when displaying repository dependencies for installed repositories and when displaying
        them for uninstalled repositories that are being reinstalled.
        """
        metadata = repository.metadata_
        if metadata:
            # Handle repository dependencies.
            (
                installed_repository_dependencies,
                missing_repository_dependencies,
            ) = self.app.installed_repository_manager.get_installed_and_missing_repository_dependencies(repository)
            # Handle the current repository's tool dependencies.
            repository_tool_dependencies = metadata.get("tool_dependencies", None)
            # Make sure to display missing tool dependencies as well.
            repository_invalid_tool_dependencies = metadata.get("invalid_tool_dependencies", None)
            if repository_invalid_tool_dependencies is not None:
                if repository_tool_dependencies is None:
                    repository_tool_dependencies = {}
                repository_tool_dependencies.update(repository_invalid_tool_dependencies)
            gucm = GalaxyUtilityContainerManager(self.app)
            containers_dict = gucm.build_repository_containers(
                missing_repository_dependencies=missing_repository_dependencies,
                repository_dependencies=installed_repository_dependencies,
            )
        else:
            containers_dict = dict(
                repository_dependencies=None,
            )
        return containers_dict

    def _tool_dependency_is_orphan(self, type, name, version, tools):
        """
        Determine if the combination of the received type, name and version is defined in the <requirement>
        tag for at least one tool in the received list of tools.  If not, the tool dependency defined by the
        combination is considered an orphan in its repository in the tool shed.
        """
        if type == "package":
            if name and version:
                for tool_dict in tools:
                    requirements = tool_dict.get("requirements", [])
                    for requirement_dict in requirements:
                        req_name = requirement_dict.get("name", None)
                        req_version = requirement_dict.get("version", None)
                        req_type = requirement_dict.get("type", None)
                        if req_name == name and req_version == version and req_type == type:
                            return False
        elif type == "set_environment":
            if name:
                for tool_dict in tools:
                    requirements = tool_dict.get("requirements", [])
                    for requirement_dict in requirements:
                        req_name = requirement_dict.get("name", None)
                        req_type = requirement_dict.get("type", None)
                        if req_name == name and req_type == type:
                            return False
        return True


class GalaxyUtilityContainerManager(utility_container_manager.UtilityContainerManager):
    def __init__(self, app):
        self.app = app

    def build_repository_containers(
        self,
        missing_repository_dependencies,
        repository_dependencies,
    ):
        """
        Return a dictionary of containers for the received repository's dependencies and readme files for
        display during installation to Galaxy.
        """
        containers_dict = dict(
            repository_dependencies=None,
            missing_repository_dependencies=None,
        )
        # Some of the tool dependency folders will include links to display tool dependency information, and
        # some of these links require the repository id.  However we need to be careful because sometimes the
        # repository object is None.
        try:
            folder_id = 0
            # Installed repository dependencies container.
            if repository_dependencies:
                label = "Installed repository dependencies"
                folder_id, repository_dependencies_root_folder = self.build_repository_dependencies_folder(
                    folder_id=folder_id, repository_dependencies=repository_dependencies, label=label, installed=True
                )
                containers_dict["repository_dependencies"] = repository_dependencies_root_folder
            # Missing repository dependencies container.
            if missing_repository_dependencies:
                folder_id, missing_repository_dependencies_root_folder = self.build_repository_dependencies_folder(
                    folder_id=folder_id,
                    repository_dependencies=missing_repository_dependencies,
                    label="Missing repository dependencies",
                    installed=False,
                )
                containers_dict["missing_repository_dependencies"] = missing_repository_dependencies_root_folder
        except Exception as e:
            log.debug(f"Exception in build_repository_containers: {str(e)}")
        return containers_dict
