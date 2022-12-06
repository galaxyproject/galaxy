import logging
import os
import tempfile

from sqlalchemy import and_

from galaxy import util
from galaxy.tool_shed.repository_type import (
    REPOSITORY_DEPENDENCY_DEFINITION_FILENAME,
    TOOL_DEPENDENCY_DEFINITION_FILENAME,
)
from galaxy.tool_shed.tools.tool_validator import ToolValidator
from galaxy.tool_shed.util import (
    shed_util_common as suc,
    tool_dependency_util,
    tool_util,
)
from galaxy.tool_shed.util.basic_util import (
    remove_dir,
    strip_path,
)
from galaxy.tool_shed.util.hg_util import get_config_from_disk
from galaxy.tool_shed.util.metadata_util import get_updated_changeset_revisions_from_tool_shed
from galaxy.tool_shed.util.repository_util import get_repository_for_dependency_relationship
from galaxy.tool_util.loader_directory import looks_like_a_tool
from galaxy.tool_util.parser.interface import TestCollectionDef
from galaxy.tools.data_manager.manager import DataManager
from galaxy.tools.repositories import ValidationContext
from galaxy.util.tool_shed.common_util import (
    generate_clone_url_for_installed_repository,
    generate_clone_url_for_repository_in_tool_shed,
    remove_protocol_and_user_from_clone_url,
    remove_protocol_from_tool_shed_url,
)
from galaxy.util.tool_shed.xml_util import parse_xml
from galaxy.web import url_for

log = logging.getLogger(__name__)


class MetadataGenerator:
    def __init__(
        self,
        app,
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
        user=None,
    ):
        self.app = app
        self.user = user
        self.repository = repository
        if self.app.name == "galaxy":
            if changeset_revision is None and self.repository is not None:
                self.changeset_revision = self.repository.changeset_revision
            else:
                self.changeset_revision = changeset_revision

            if repository_clone_url is None and self.repository is not None:
                self.repository_clone_url = generate_clone_url_for_installed_repository(self.app, self.repository)
            else:
                self.repository_clone_url = repository_clone_url
            if shed_config_dict is None:
                if self.repository is not None:
                    self.shed_config_dict = self.repository.get_shed_config_dict(self.app)
                else:
                    self.shed_config_dict = {}
            else:
                self.shed_config_dict = shed_config_dict
            if relative_install_dir is None and self.repository is not None:
                tool_path, relative_install_dir = self.repository.get_tool_relative_path(self.app)
            if repository_files_dir is None and self.repository is not None:
                repository_files_dir = self.repository.repo_files_directory(self.app)
            if metadata_dict is None:
                # Shed related tool panel configs are only relevant to Galaxy.
                self.metadata_dict = {"shed_config_filename": self.shed_config_dict.get("config_filename", None)}
            else:
                self.metadata_dict = metadata_dict
        else:
            # We're in the Tool Shed.
            if changeset_revision is None and self.repository is not None:
                self.changeset_revision = self.repository.tip()
            else:
                self.changeset_revision = changeset_revision
            if repository_clone_url is None and self.repository is not None:
                self.repository_clone_url = generate_clone_url_for_repository_in_tool_shed(self.user, self.repository)
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
        self.sa_session = app.model.session
        self.NOT_TOOL_CONFIGS = [
            suc.DATATYPES_CONFIG_FILENAME,
            REPOSITORY_DEPENDENCY_DEFINITION_FILENAME,
            TOOL_DEPENDENCY_DEFINITION_FILENAME,
            suc.REPOSITORY_DATA_MANAGER_CONFIG_FILENAME,
        ]

    def _generate_data_manager_metadata(
        self, repo_dir, data_manager_config_filename, metadata_dict, shed_config_dict=None
    ):
        """
        Update the received metadata_dict with information from the parsed data_manager_config_filename.
        """
        if data_manager_config_filename is None:
            return metadata_dict
        repo_path = self.repository.repo_path(self.app)
        try:
            # Galaxy Side.
            repo_files_directory = self.repository.repo_files_directory(self.app)
            repo_dir = repo_files_directory
        except AttributeError:
            # Tool Shed side.
            repo_files_directory = repo_path
        relative_data_manager_dir = util.relpath(os.path.split(data_manager_config_filename)[0], repo_dir)
        rel_data_manager_config_filename = os.path.join(
            relative_data_manager_dir, os.path.split(data_manager_config_filename)[1]
        )
        data_managers = {}
        invalid_data_managers = []
        data_manager_metadata = {
            "config_filename": rel_data_manager_config_filename,
            "data_managers": data_managers,
            "invalid_data_managers": invalid_data_managers,
            "error_messages": [],
        }
        metadata_dict["data_manager"] = data_manager_metadata
        tree, error_message = parse_xml(data_manager_config_filename)
        if tree is None:
            # We are not able to load any data managers.
            data_manager_metadata["error_messages"].append(error_message)
            return metadata_dict
        tool_path = None
        if shed_config_dict:
            tool_path = shed_config_dict.get("tool_path", None)
        tools = {}
        for tool in metadata_dict.get("tools", []):
            tool_conf_name = tool["tool_config"]
            if tool_path:
                tool_conf_name = os.path.join(tool_path, tool_conf_name)
            tools[tool_conf_name] = tool
        root = tree.getroot()
        data_manager_tool_path = root.get("tool_path", None)
        if data_manager_tool_path:
            relative_data_manager_dir = os.path.join(relative_data_manager_dir, data_manager_tool_path)
        for i, data_manager_elem in enumerate(root.findall("data_manager")):
            tool_file = data_manager_elem.get("tool_file", None)
            data_manager_id = data_manager_elem.get("id", None)
            if data_manager_id is None:
                log.error(f'Data Manager entry is missing id attribute in "{data_manager_config_filename}".')
                invalid_data_managers.append(
                    {"index": i, "error_message": "Data Manager entry is missing id attribute"}
                )
                continue
            # FIXME: default behavior is to fall back to tool.name.
            data_manager_name = data_manager_elem.get("name", data_manager_id)
            version = data_manager_elem.get("version", DataManager.DEFAULT_VERSION)
            guid = self.generate_guid_for_object(DataManager.GUID_TYPE, data_manager_id, version)
            data_tables = []
            if tool_file is None:
                log.error(f'Data Manager entry is missing tool_file attribute in "{data_manager_config_filename}".')
                invalid_data_managers.append(
                    {"index": i, "error_message": "Data Manager entry is missing tool_file attribute"}
                )
                continue
            else:
                bad_data_table = False
                for data_table_elem in data_manager_elem.findall("data_table"):
                    data_table_name = data_table_elem.get("name", None)
                    if data_table_name is None:
                        log.error(
                            f'Data Manager data_table entry is missing name attribute in "{data_manager_config_filename}".'
                        )
                        invalid_data_managers.append(
                            {"index": i, "error_message": "Data Manager entry is missing name attribute"}
                        )
                        bad_data_table = True
                        break
                    else:
                        data_tables.append(data_table_name)
                if bad_data_table:
                    continue
            data_manager_metadata_tool_file = os.path.normpath(os.path.join(relative_data_manager_dir, tool_file))
            tool_metadata_tool_file = os.path.join(repo_files_directory, data_manager_metadata_tool_file)
            tool = tools.get(tool_metadata_tool_file, None)
            if tool is None:
                log.error(f"Unable to determine tools metadata for '{data_manager_metadata_tool_file}'.")
                invalid_data_managers.append({"index": i, "error_message": "Unable to determine tools metadata"})
                continue
            data_managers[data_manager_id] = {
                "id": data_manager_id,
                "name": data_manager_name,
                "guid": guid,
                "version": version,
                "tool_config_file": data_manager_metadata_tool_file,
                "data_tables": data_tables,
                "tool_guid": tool["guid"],
            }
            log.debug(f"Loaded Data Manager tool_files: {tool_file}")
        return metadata_dict

    def generate_environment_dependency_metadata(self, elem, valid_tool_dependencies_dict):
        """
        The value of env_var_name must match the value of the "set_environment" type
        in the tool config's <requirements> tag set, or the tool dependency will be
        considered an orphan.
        """
        # The value of the received elem looks something like this:
        # <set_environment version="1.0">
        #    <environment_variable name="JAVA_JAR_PATH" action="set_to">$INSTALL_DIR</environment_variable>
        # </set_environment>
        for env_elem in elem:
            # <environment_variable name="JAVA_JAR_PATH" action="set_to">$INSTALL_DIR</environment_variable>
            env_name = env_elem.get("name", None)
            if env_name:
                requirements_dict = dict(name=env_name, type="set_environment")
                if "set_environment" in valid_tool_dependencies_dict:
                    valid_tool_dependencies_dict["set_environment"].append(requirements_dict)
                else:
                    valid_tool_dependencies_dict["set_environment"] = [requirements_dict]
        return valid_tool_dependencies_dict

    def generate_guid_for_object(self, guid_type, obj_id, version):
        tmp_url = remove_protocol_and_user_from_clone_url(self.repository_clone_url)
        return f"{tmp_url}/{guid_type}/{obj_id}/{version}"

    def generate_metadata_for_changeset_revision(self):
        """
        Generate metadata for a repository using its files on disk.  To generate metadata
        for changeset revisions older than the repository tip, the repository will have been
        cloned to a temporary location and updated to a specified changeset revision to access
        that changeset revision's disk files, so the value of self.repository_files_dir will not
        always be self.repository.repo_path( self.app ) (it could be an absolute path to a temporary
        directory containing a clone).  If it is an absolute path, the value of self.relative_install_dir
        must contain repository.repo_path( self.app ).

        The value of self.persist will be True when the installed repository contains a valid
        tool_data_table_conf.xml.sample file, in which case the entries should ultimately be
        persisted to the file referred to by self.app.config.shed_tool_data_table_config.
        """
        if self.shed_config_dict is None:
            self.shed_config_dict = {}
        if self.updating_installed_repository:
            # Keep the original tool shed repository metadata if setting metadata on a repository
            # installed into a local Galaxy instance for which we have pulled updates.
            original_repository_metadata = self.repository.metadata_
        else:
            original_repository_metadata = None
        readme_file_names = _get_readme_file_names(str(self.repository.name))
        if self.app.name == "galaxy":
            # Shed related tool panel configs are only relevant to Galaxy.
            metadata_dict = {"shed_config_filename": self.shed_config_dict.get("config_filename")}
        else:
            metadata_dict = {}
        readme_files = []
        invalid_tool_configs = []
        if self.resetting_all_metadata_on_repository:
            if not self.relative_install_dir:
                raise Exception(
                    "The value of self.repository.repo_path must be set when resetting all metadata on a repository."
                )
            # Keep track of the location where the repository is temporarily cloned so that we can
            # strip the path when setting metadata.  The value of self.repository_files_dir is the
            # full path to the temporary directory to which self.repository was cloned.
            work_dir = self.repository_files_dir
            files_dir = self.repository_files_dir
            # Since we're working from a temporary directory, we can safely copy sample files included
            # in the repository to the repository root.
        else:
            # Use a temporary working directory to copy all sample files.
            work_dir = tempfile.mkdtemp(prefix="tmp-toolshed-gmfcr")
            # All other files are on disk in the repository's repo_path, which is the value of
            # self.relative_install_dir.
            files_dir = self.relative_install_dir
            if self.shed_config_dict.get("tool_path"):
                files_dir = os.path.join(self.shed_config_dict["tool_path"], files_dir)
        # Create ValidationContext to load and validate tools, data tables and datatypes
        with ValidationContext.from_app(app=self.app, work_dir=work_dir) as validation_context:
            tv = ToolValidator(validation_context)
            # Get the relative path to all sample files included in the repository for storage in
            # the repository's metadata.
            sample_file_metadata_paths, sample_file_copy_paths = self.get_sample_files_from_disk(
                repository_files_dir=files_dir,
                tool_path=self.shed_config_dict.get("tool_path"),
                relative_install_dir=self.relative_install_dir,
            )
            if sample_file_metadata_paths:
                metadata_dict["sample_files"] = sample_file_metadata_paths
            # Copy all sample files included in the repository to a single directory location so we
            # can load tools that depend on them.
            data_table_conf_xml_sample_files = []
            for sample_file in sample_file_copy_paths:
                tool_util.copy_sample_file(self.app.config.tool_data_path, sample_file, dest_path=work_dir)
                # If the list of sample files includes a tool_data_table_conf.xml.sample file, load
                # its table elements into memory.
                relative_path, filename = os.path.split(sample_file)
                if filename == "tool_data_table_conf.xml.sample":
                    data_table_conf_xml_sample_files.append(sample_file)

            for data_table_conf_xml_sample_file in data_table_conf_xml_sample_files:
                # We create a new ToolDataTableManager to avoid adding entries to the app-wide
                # tool data tables. This is only used for checking that the data table is valid.
                new_table_elems, error_message = validation_context.tool_data_tables.add_new_entries_from_config_file(
                    config_filename=data_table_conf_xml_sample_file,
                    tool_data_path=work_dir,
                    shed_tool_data_table_config=work_dir,
                    persist=False,
                )
                if error_message:
                    self.invalid_file_tups.append((filename, error_message))
            for root, dirs, files in os.walk(files_dir):
                if root.find(".hg") < 0 and root.find("hgrc") < 0:
                    if ".hg" in dirs:
                        dirs.remove(".hg")
                    for name in files:
                        # See if we have a repository dependencies defined.
                        if name == REPOSITORY_DEPENDENCY_DEFINITION_FILENAME:
                            path_to_repository_dependencies_config = os.path.join(root, name)
                            metadata_dict, error_message = self.generate_repository_dependency_metadata(
                                path_to_repository_dependencies_config, metadata_dict
                            )
                            if error_message:
                                self.invalid_file_tups.append((name, error_message))
                        # See if we have one or more READ_ME files.
                        elif name.lower() in readme_file_names:
                            relative_path_to_readme = self.get_relative_path_to_repository_file(
                                root, name, self.relative_install_dir, work_dir, self.shed_config_dict
                            )
                            readme_files.append(relative_path_to_readme)
                        # See if we have a tool config.
                        elif looks_like_a_tool(os.path.join(root, name), invalid_names=self.NOT_TOOL_CONFIGS):
                            full_path = str(os.path.abspath(os.path.join(root, name)))  # why the str, seems very odd
                            element_tree, error_message = parse_xml(full_path)
                            if element_tree is None:
                                is_tool = False
                            else:
                                element_tree_root = element_tree.getroot()
                                is_tool = element_tree_root.tag == "tool"
                            if is_tool:
                                tool, valid, error_message = tv.load_tool_from_config(
                                    self.app.security.encode_id(self.repository.id), full_path
                                )
                                if tool is None:
                                    if not valid:
                                        invalid_tool_configs.append(name)
                                        self.invalid_file_tups.append((name, error_message))
                                else:
                                    invalid_files_and_errors_tups = tv.check_tool_input_params(
                                        files_dir, name, tool, sample_file_copy_paths
                                    )
                                    can_set_metadata = True
                                    for tup in invalid_files_and_errors_tups:
                                        if name in tup:
                                            can_set_metadata = False
                                            invalid_tool_configs.append(name)
                                            break
                                    if can_set_metadata:
                                        relative_path_to_tool_config = self.get_relative_path_to_repository_file(
                                            root, name, self.relative_install_dir, work_dir, self.shed_config_dict
                                        )
                                        metadata_dict = self.generate_tool_metadata(
                                            relative_path_to_tool_config, tool, metadata_dict
                                        )
                                    else:
                                        for tup in invalid_files_and_errors_tups:
                                            self.invalid_file_tups.append(tup)
        # Handle any data manager entries
        data_manager_config = get_config_from_disk(suc.REPOSITORY_DATA_MANAGER_CONFIG_FILENAME, files_dir)
        metadata_dict = self._generate_data_manager_metadata(
            files_dir, data_manager_config, metadata_dict, shed_config_dict=self.shed_config_dict
        )

        if readme_files:
            metadata_dict["readme_files"] = readme_files
        # This step must be done after metadata for tools has been defined.
        tool_dependencies_config = get_config_from_disk(TOOL_DEPENDENCY_DEFINITION_FILENAME, files_dir)
        if tool_dependencies_config:
            metadata_dict, error_message = self.generate_tool_dependency_metadata(
                tool_dependencies_config, metadata_dict, original_repository_metadata=original_repository_metadata
            )
            if error_message:
                self.invalid_file_tups.append((TOOL_DEPENDENCY_DEFINITION_FILENAME, error_message))
        if invalid_tool_configs:
            metadata_dict["invalid_tools"] = invalid_tool_configs
        self.metadata_dict = metadata_dict
        remove_dir(work_dir)

    def generate_package_dependency_metadata(self, elem, valid_tool_dependencies_dict, invalid_tool_dependencies_dict):
        """
        Generate the metadata for a tool dependencies package defined for a repository.  The
        value of package_name must match the value of the "package" type in the tool config's
        <requirements> tag set.
        """
        # TODO: make this function a class.
        repository_dependency_is_valid = True
        repository_dependency_tup = []
        requirements_dict = {}
        error_message = ""
        package_name = elem.get("name", None)
        package_version = elem.get("version", None)
        if package_name and package_version:
            requirements_dict["name"] = package_name
            requirements_dict["version"] = package_version
            requirements_dict["type"] = "package"
            for sub_elem in elem:
                if sub_elem.tag == "readme":
                    requirements_dict["readme"] = sub_elem.text
                elif sub_elem.tag == "repository":
                    # We have a complex repository dependency.  If the returned value of repository_dependency_is_valid
                    # is True, the tool dependency definition will be set as invalid.  This is currently the only case
                    # where a tool dependency definition is considered invalid.
                    (
                        repository_dependency_tup,
                        repository_dependency_is_valid,
                        error_message,
                    ) = self.handle_repository_elem(repository_elem=sub_elem, only_if_compiling_contained_td=False)
                elif sub_elem.tag == "install":
                    package_install_version = sub_elem.get("version", "1.0")
                    if package_install_version == "1.0":
                        # Complex repository dependencies can be defined within the last <actions> tag set contained in an
                        # <actions_group> tag set.  Comments, <repository> tag sets and <readme> tag sets will be skipped
                        # in tool_dependency_util.parse_package_elem().
                        actions_elem_tuples = tool_dependency_util.parse_package_elem(
                            sub_elem, platform_info_dict=None, include_after_install_actions=False
                        )
                        if actions_elem_tuples:
                            # We now have a list of a single tuple that looks something like:
                            # [(True, <Element 'actions' at 0x104017850>)]
                            actions_elem_tuple = actions_elem_tuples[0]
                            in_actions_group, actions_elem = actions_elem_tuple
                            if in_actions_group:
                                # Since we're inside an <actions_group> tag set, inspect the actions_elem to see if a complex
                                # repository dependency is defined.  By definition, complex repository dependency definitions
                                # contained within the last <actions> tag set within an <actions_group> tag set will have the
                                # value of "only_if_compiling_contained_td" set to True in
                                for action_elem in actions_elem:
                                    if action_elem.tag == "package":
                                        # <package name="libgtextutils" version="0.6">
                                        #    <repository name="package_libgtextutils_0_6" owner="test" prior_installation_required="True" />
                                        # </package>
                                        ae_package_name = action_elem.get("name", None)
                                        ae_package_version = action_elem.get("version", None)
                                        if ae_package_name and ae_package_version:
                                            for sub_action_elem in action_elem:
                                                if sub_action_elem.tag == "repository":
                                                    # We have a complex repository dependency.
                                                    (
                                                        repository_dependency_tup,
                                                        repository_dependency_is_valid,
                                                        error_message,
                                                    ) = self.handle_repository_elem(
                                                        repository_elem=sub_action_elem,
                                                        only_if_compiling_contained_td=True,
                                                    )
                                    elif action_elem.tag == "action":
                                        # <action type="set_environment_for_install">
                                        #    <repository changeset_revision="b107b91b3574" name="package_readline_6_2" owner="devteam" prior_installation_required="True" toolshed="http://localhost:9009">
                                        #        <package name="readline" version="6.2" />
                                        #    </repository>
                                        # </action>
                                        for sub_action_elem in action_elem:
                                            if sub_action_elem.tag == "repository":
                                                # We have a complex repository dependency.
                                                (
                                                    repository_dependency_tup,
                                                    repository_dependency_is_valid,
                                                    error_message,
                                                ) = self.handle_repository_elem(
                                                    repository_elem=sub_action_elem, only_if_compiling_contained_td=True
                                                )
        if requirements_dict:
            dependency_key = f"{package_name}/{package_version}"
            if repository_dependency_is_valid:
                valid_tool_dependencies_dict[dependency_key] = requirements_dict
            else:
                # Append the error message to the requirements_dict.
                requirements_dict["error"] = error_message
                invalid_tool_dependencies_dict[dependency_key] = requirements_dict
        return (
            valid_tool_dependencies_dict,
            invalid_tool_dependencies_dict,
            repository_dependency_tup,
            repository_dependency_is_valid,
            error_message,
        )

    def generate_repository_dependency_metadata(self, repository_dependencies_config, metadata_dict):
        """
        Generate a repository dependencies dictionary based on valid information defined in the received
        repository_dependencies_config.  This method is called from the tool shed as well as from Galaxy.
        """
        # Make sure we're looking at a valid repository_dependencies.xml file.
        tree, error_message = parse_xml(repository_dependencies_config)
        if tree is None:
            xml_is_valid = False
        else:
            root = tree.getroot()
            xml_is_valid = root.tag == "repositories"
        if xml_is_valid:
            invalid_repository_dependencies_dict = dict(description=root.get("description"))
            invalid_repository_dependency_tups = []
            valid_repository_dependencies_dict = dict(description=root.get("description"))
            valid_repository_dependency_tups = []
            for repository_elem in root.findall("repository"):
                repository_dependency_tup, repository_dependency_is_valid, err_msg = self.handle_repository_elem(
                    repository_elem, only_if_compiling_contained_td=False
                )
                if repository_dependency_is_valid:
                    valid_repository_dependency_tups.append(repository_dependency_tup)
                else:
                    # Append the error_message to the repository dependencies tuple.
                    (
                        toolshed,
                        name,
                        owner,
                        changeset_revision,
                        prior_installation_required,
                        only_if_compiling_contained_td,
                    ) = repository_dependency_tup
                    repository_dependency_tup = (
                        toolshed,
                        name,
                        owner,
                        changeset_revision,
                        prior_installation_required,
                        only_if_compiling_contained_td,
                        err_msg,
                    )
                    invalid_repository_dependency_tups.append(repository_dependency_tup)
                    error_message += err_msg
            if invalid_repository_dependency_tups:
                invalid_repository_dependencies_dict["repository_dependencies"] = invalid_repository_dependency_tups
                metadata_dict["invalid_repository_dependencies"] = invalid_repository_dependencies_dict
            if valid_repository_dependency_tups:
                valid_repository_dependencies_dict["repository_dependencies"] = valid_repository_dependency_tups
                metadata_dict["repository_dependencies"] = valid_repository_dependencies_dict
        return metadata_dict, error_message

    def generate_tool_metadata(self, tool_config, tool, metadata_dict):
        """Update the received metadata_dict with changes that have been applied to the received tool."""
        # Generate the guid.
        guid = suc.generate_tool_guid(self.repository_clone_url, tool)
        # Handle tool.requirements.
        tool_requirements = []
        for tool_requirement in tool.requirements:
            name = str(tool_requirement.name)
            tool_type = str(tool_requirement.type)
            version = str(tool_requirement.version) if tool_requirement.version else None
            requirement_dict = dict(name=name, type=tool_type, version=version)
            tool_requirements.append(requirement_dict)
        # Handle tool.tests.
        tool_tests = []
        if tool.tests:
            for ttb in tool.tests:
                required_files = []
                for required_file in ttb.required_files:
                    value, extra = required_file
                    required_files.append(value)
                inputs = []
                for param_name, values in ttb.inputs.items():
                    # Handle improperly defined or strange test parameters and values.
                    if param_name is not None:
                        if values in [None, False]:
                            # An example is the third test in http://testtoolshed.g2.bx.psu.edu/view/devteam/samtools_rmdup
                            # which is defined as:
                            # <test>
                            #    <param name="input1" value="1.bam" ftype="bam" />
                            #    <param name="bam_paired_end_type_selector" value="PE" />
                            #    <param name="force_se" />
                            #    <output name="output1" file="1.bam" ftype="bam" sort="True" />
                            # </test>
                            inputs.append((param_name, values))
                        else:
                            if isinstance(values, TestCollectionDef):
                                # Nested required files are being populated correctly,
                                # not sure we need the value here to be anything else?
                                collection_type = values.collection_type
                                metadata_display_value = f"{collection_type} collection"
                                inputs.append((param_name, metadata_display_value))
                            else:
                                try:
                                    if len(values) == 1:
                                        inputs.append((param_name, values[0]))
                                        continue
                                except TypeError:
                                    log.exception(
                                        'Expected a list of values for tool "%s" parameter "%s", got %s: %s',
                                        tool.id,
                                        param_name,
                                        type(values),
                                        values,
                                    )
                                inputs.append((param_name, values))
                outputs = []
                for output in ttb.outputs:
                    name, file_name, extra = output
                    outputs.append((name, strip_path(file_name) if file_name else None))
                    if file_name not in required_files and file_name is not None:
                        required_files.append(file_name)
                test_dict = dict(name=str(ttb.name), required_files=required_files, inputs=inputs, outputs=outputs)
                tool_tests.append(test_dict)
        # Determine if the tool should be loaded into the tool panel.  Examples of valid tools that
        # should not be displayed in the tool panel are datatypes converters and DataManager tools
        # (which are of type 'manage_data').
        add_to_tool_panel_attribute = self._set_add_to_tool_panel_attribute_for_tool(tool)
        tool_dict = dict(
            id=tool.id,
            guid=guid,
            name=tool.name,
            version=tool.version,
            profile=tool.profile,
            description=tool.description,
            version_string_cmd=tool.version_string_cmd,
            tool_config=tool_config,
            tool_type=tool.tool_type,
            requirements=tool_requirements,
            tests=tool_tests,
            add_to_tool_panel=add_to_tool_panel_attribute,
        )
        if "tools" in metadata_dict:
            metadata_dict["tools"].append(tool_dict)
        else:
            metadata_dict["tools"] = [tool_dict]
        return metadata_dict

    def generate_tool_dependency_metadata(
        self, tool_dependencies_config, metadata_dict, original_repository_metadata=None
    ):
        """
        If the combination of name, version and type of each element is defined in the <requirement> tag for
        at least one tool in self.repository, then update the received metadata_dict with information from the
        parsed tool_dependencies_config.
        """
        error_message = ""
        if original_repository_metadata:
            # Keep a copy of the original tool dependencies dictionary and the list of tool
            # dictionaries in the metadata.
            original_valid_tool_dependencies_dict = original_repository_metadata.get("tool_dependencies", None)
        else:
            original_valid_tool_dependencies_dict = None
        tree, error_message = parse_xml(tool_dependencies_config)
        if tree is None:
            return metadata_dict, error_message
        root = tree.getroot()

        class RecurserValueStore:
            pass

        rvs = RecurserValueStore()
        rvs.valid_tool_dependencies_dict = {}
        rvs.invalid_tool_dependencies_dict = {}
        valid_repository_dependency_tups = []
        invalid_repository_dependency_tups = []
        description = root.get("description")

        def _check_elem_for_dep(elems):
            error_messages = []
            for elem in elems:
                if elem.tag == "package":
                    (
                        rvs.valid_tool_dependencies_dict,
                        rvs.invalid_tool_dependencies_dict,
                        repository_dependency_tup,
                        repository_dependency_is_valid,
                        message,
                    ) = self.generate_package_dependency_metadata(
                        elem, rvs.valid_tool_dependencies_dict, rvs.invalid_tool_dependencies_dict
                    )
                    if repository_dependency_is_valid:
                        if (
                            repository_dependency_tup
                            and repository_dependency_tup not in valid_repository_dependency_tups
                        ):
                            # We have a valid complex repository dependency.
                            valid_repository_dependency_tups.append(repository_dependency_tup)
                    else:
                        if (
                            repository_dependency_tup
                            and repository_dependency_tup not in invalid_repository_dependency_tups
                        ):
                            # We have an invalid complex repository dependency, so mark the tool dependency as invalid.
                            # Append the error message to the invalid repository dependency tuple.
                            (
                                toolshed,
                                name,
                                owner,
                                changeset_revision,
                                prior_installation_required,
                                only_if_compiling_contained_td,
                            ) = repository_dependency_tup
                            repository_dependency_tup = (
                                toolshed,
                                name,
                                owner,
                                changeset_revision,
                                prior_installation_required,
                                only_if_compiling_contained_td,
                                message,
                            )
                            invalid_repository_dependency_tups.append(repository_dependency_tup)
                            error_messages.append(f"{error_message}  {message}")
                elif elem.tag == "set_environment":
                    rvs.valid_tool_dependencies_dict = self.generate_environment_dependency_metadata(
                        elem, rvs.valid_tool_dependencies_dict
                    )
                error_messages += _check_elem_for_dep(elem)
            return error_messages

        error_message = "\n".join([error_message] + _check_elem_for_dep(root))
        if rvs.valid_tool_dependencies_dict:
            if original_valid_tool_dependencies_dict:
                # We're generating metadata on an update pulled to a tool shed repository installed
                # into a Galaxy instance, so handle changes to tool dependencies appropriately.
                irm = self.app.installed_repository_manager
                (
                    updated_tool_dependency_names,
                    deleted_tool_dependency_names,
                ) = irm.handle_existing_tool_dependencies_that_changed_in_update(
                    self.repository, original_valid_tool_dependencies_dict, rvs.valid_tool_dependencies_dict
                )
            metadata_dict["tool_dependencies"] = rvs.valid_tool_dependencies_dict
        if rvs.invalid_tool_dependencies_dict:
            metadata_dict["invalid_tool_dependencies"] = rvs.invalid_tool_dependencies_dict
        if valid_repository_dependency_tups:
            metadata_dict = self.update_repository_dependencies_metadata(
                metadata=metadata_dict,
                repository_dependency_tups=valid_repository_dependency_tups,
                is_valid=True,
                description=description,
            )
        if invalid_repository_dependency_tups:
            metadata_dict = self.update_repository_dependencies_metadata(
                metadata=metadata_dict,
                repository_dependency_tups=invalid_repository_dependency_tups,
                is_valid=False,
                description=description,
            )
        return metadata_dict, error_message

    def get_invalid_file_tups(self):
        return self.invalid_file_tups

    def get_metadata_dict(self):
        return self.metadata_dict

    def get_relative_path_to_repository_file(self, root, name, relative_install_dir, work_dir, shed_config_dict):
        if self.resetting_all_metadata_on_repository:
            full_path_to_file = os.path.join(root, name)
            stripped_path_to_file = full_path_to_file.replace(work_dir, "")
            if stripped_path_to_file.startswith("/"):
                stripped_path_to_file = stripped_path_to_file[1:]
            relative_path_to_file = os.path.join(relative_install_dir, stripped_path_to_file)
        else:
            relative_path_to_file = os.path.join(root, name)
            if (
                relative_install_dir
                and shed_config_dict.get("tool_path")
                and relative_path_to_file.startswith(
                    os.path.join(shed_config_dict.get("tool_path"), relative_install_dir)
                )
            ):
                relative_path_to_file = relative_path_to_file[len(shed_config_dict.get("tool_path")) + 1 :]
        return relative_path_to_file

    def get_sample_files_from_disk(self, repository_files_dir, tool_path=None, relative_install_dir=None):
        work_dir = ""
        if self.resetting_all_metadata_on_repository:
            # Keep track of the location where the repository is temporarily cloned so that we can strip
            # it when setting metadata.
            work_dir = repository_files_dir
        sample_file_metadata_paths = []
        sample_file_copy_paths = []
        for root, _dirs, files in os.walk(repository_files_dir):
            if root.find(".hg") < 0:
                for name in files:
                    if name.endswith(".sample"):
                        if self.resetting_all_metadata_on_repository:
                            full_path_to_sample_file = os.path.join(root, name)
                            stripped_path_to_sample_file = full_path_to_sample_file.replace(work_dir, "")
                            if stripped_path_to_sample_file.startswith("/"):
                                stripped_path_to_sample_file = stripped_path_to_sample_file[1:]
                            relative_path_to_sample_file = os.path.join(
                                relative_install_dir, stripped_path_to_sample_file
                            )
                            if os.path.exists(relative_path_to_sample_file):
                                sample_file_copy_paths.append(relative_path_to_sample_file)
                            else:
                                sample_file_copy_paths.append(full_path_to_sample_file)
                        else:
                            relative_path_to_sample_file = os.path.join(root, name)
                            sample_file_copy_paths.append(relative_path_to_sample_file)
                            if tool_path and relative_install_dir:
                                if relative_path_to_sample_file.startswith(
                                    os.path.join(tool_path, relative_install_dir)
                                ):
                                    relative_path_to_sample_file = relative_path_to_sample_file[len(tool_path) + 1 :]
                        sample_file_metadata_paths.append(relative_path_to_sample_file)
        return sample_file_metadata_paths, sample_file_copy_paths

    def handle_repository_elem(self, repository_elem, only_if_compiling_contained_td=False):
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
        if self.app.name == "galaxy":
            if self.updating_installed_repository:
                pass
            else:
                # We're installing a repository into Galaxy, so make sure its contained repository
                # dependency definition is valid.
                if toolshed is None or name is None or owner is None or changeset_revision is None:
                    # Several packages exist in the Tool Shed that contain invalid repository
                    # definitions, but will still install. We will report these errors to the
                    # installing user. Previously, we would:
                    # Raise an exception here instead of returning an error_message to keep the
                    # installation from proceeding.  Reaching here implies a bug in the Tool Shed
                    # framework.
                    error_message = "Installation encountered an invalid repository dependency definition:\n"
                    error_message += util.xml_to_string(repository_elem, pretty=True)
                    log.error(error_message)
                    return repository_dependency_tup, False, error_message
        if not toolshed:
            # Default to the current tool shed.
            toolshed = str(url_for("/", qualified=True)).rstrip("/")
            repository_dependency_tup[0] = toolshed
        toolshed = remove_protocol_from_tool_shed_url(toolshed)
        if self.app.name == "galaxy":
            # We're in Galaxy.  We reach here when we're generating the metadata for a tool
            # dependencies package defined for a repository or when we're generating metadata
            # for an installed repository.  See if we can locate the installed repository via
            # the changeset_revision defined in the repository_elem (it may be outdated).  If
            # we're successful in locating an installed repository with the attributes defined
            # in the repository_elem, we know it is valid.
            repository = get_repository_for_dependency_relationship(self.app, toolshed, name, owner, changeset_revision)
            if repository:
                return repository_dependency_tup, is_valid, error_message
            else:
                # Send a request to the tool shed to retrieve appropriate additional changeset
                # revisions with which the repository
                # may have been installed.
                text = get_updated_changeset_revisions_from_tool_shed(
                    self.app, toolshed, name, owner, changeset_revision
                )
                if text:
                    updated_changeset_revisions = util.listify(text)
                    for updated_changeset_revision in updated_changeset_revisions:
                        repository = get_repository_for_dependency_relationship(
                            self.app, toolshed, name, owner, updated_changeset_revision
                        )
                        if repository:
                            return repository_dependency_tup, is_valid, error_message
                        if self.updating_installed_repository:
                            # The repository dependency was included in an update to the installed
                            # repository, so it will not yet be installed.  Return the tuple for later
                            # installation.
                            return repository_dependency_tup, is_valid, error_message
                if self.updating_installed_repository:
                    # The repository dependency was included in an update to the installed repository,
                    # so it will not yet be installed.  Return the tuple for later installation.
                    return repository_dependency_tup, is_valid, error_message
                # Don't generate an error message for missing repository dependencies that are required
                # only if compiling the dependent repository's tool dependency.
                if not only_if_compiling_contained_td:
                    # We'll currently default to setting the repository dependency definition as invalid
                    # if an installed repository cannot be found.  This may not be ideal because the tool
                    # shed may have simply been inaccessible when metadata was being generated for the
                    # installed tool shed repository.
                    error_message = (
                        "Ignoring invalid repository dependency definition for tool shed %s, name %s, owner %s, "
                        % (toolshed, name, owner)
                    )
                    error_message += f"changeset revision {changeset_revision}."
                    log.debug(error_message)
                    is_valid = False
                    return repository_dependency_tup, is_valid, error_message
        else:
            # We're in the tool shed.
            if suc.tool_shed_is_this_tool_shed(toolshed):
                try:
                    user = (
                        self.sa_session.query(self.app.model.User)
                        .filter(self.app.model.User.table.c.username == owner)
                        .one()
                    )
                except Exception:
                    error_message = (
                        "Ignoring repository dependency definition for tool shed %s, name %s, owner %s, "
                        % (toolshed, name, owner)
                    )
                    error_message += f"changeset revision {changeset_revision} because the owner is invalid."
                    log.debug(error_message)
                    is_valid = False
                    return repository_dependency_tup, is_valid, error_message
                try:
                    repository = (
                        self.sa_session.query(self.app.model.Repository)
                        .filter(
                            and_(
                                self.app.model.Repository.table.c.name == name,
                                self.app.model.Repository.table.c.user_id == user.id,
                            )
                        )
                        .one()
                    )
                except Exception:
                    error_message = (
                        "Ignoring repository dependency definition for tool shed %s, name %s, owner %s, "
                        % (toolshed, name, owner)
                    )
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
                        error_message = (
                            "Ignoring repository dependency definition for tool shed %s, name %s, owner %s, "
                            % (toolshed, name, owner)
                        )
                        error_message += (
                            f"changeset revision {changeset_revision} because the changeset revision is invalid.  "
                        )
                        log.debug(error_message)
                        is_valid = False
                        return repository_dependency_tup, is_valid, error_message
            else:
                # Repository dependencies are currently supported within a single tool shed.
                error_message = (
                    "Repository dependencies are currently supported only within the same tool shed.  Ignoring "
                )
                error_message += (
                    "repository dependency definition  for tool shed %s, name %s, owner %s, changeset revision %s.  "
                    % (toolshed, name, owner, changeset_revision)
                )
                log.debug(error_message)
                is_valid = False
                return repository_dependency_tup, is_valid, error_message
        return repository_dependency_tup, is_valid, error_message

    def _set_add_to_tool_panel_attribute_for_tool(self, tool):
        """
        Determine if a tool should be loaded into the Galaxy tool panel.  Examples of valid tools that
        should not be displayed in the tool panel are DataManager tools.
        """
        if hasattr(tool, "tool_type"):
            if tool.tool_type in ["manage_data"]:
                # We have a DataManager tool.
                return False
        return True

    def set_changeset_revision(self, changeset_revision):
        self.changeset_revision = changeset_revision

    def set_relative_install_dir(self, relative_install_dir):
        self.relative_install_dir = relative_install_dir

    def set_repository(self, repository, relative_install_dir=None, changeset_revision=None):
        self.repository = repository
        # Shed related tool panel configs are only relevant to Galaxy.
        if self.app.name == "galaxy":
            if relative_install_dir is None and self.repository is not None:
                tool_path, relative_install_dir = self.repository.get_tool_relative_path(self.app)
            if changeset_revision is None and self.repository is not None:
                self.set_changeset_revision(self.repository.changeset_revision)
            else:
                self.set_changeset_revision(changeset_revision)
            self.shed_config_dict = repository.get_shed_config_dict(self.app)
            self.metadata_dict = {"shed_config_filename": self.shed_config_dict.get("config_filename", None)}
        else:
            if relative_install_dir is None and self.repository is not None:
                relative_install_dir = repository.repo_path(self.app)
            if changeset_revision is None and self.repository is not None:
                self.set_changeset_revision(self.repository.tip())
            else:
                self.set_changeset_revision(changeset_revision)
            self.shed_config_dict = {}
            self.metadata_dict = {}
        self.set_relative_install_dir(relative_install_dir)
        self.set_repository_files_dir()
        self.resetting_all_metadata_on_repository = False
        self.updating_installed_repository = False
        self.persist = False
        self.invalid_file_tups = []

    def set_repository_clone_url(self, repository_clone_url):
        self.repository_clone_url = repository_clone_url

    def set_repository_files_dir(self, repository_files_dir=None):
        self.repository_files_dir = repository_files_dir

    def update_repository_dependencies_metadata(self, metadata, repository_dependency_tups, is_valid, description):
        if is_valid:
            repository_dependencies_dict = metadata.get("repository_dependencies", None)
        else:
            repository_dependencies_dict = metadata.get("invalid_repository_dependencies", None)
        for repository_dependency_tup in repository_dependency_tups:
            if repository_dependencies_dict:
                repository_dependencies = repository_dependencies_dict.get("repository_dependencies", [])
                for repository_dependency_tup in repository_dependency_tups:
                    if repository_dependency_tup not in repository_dependencies:
                        repository_dependencies.append(repository_dependency_tup)
                repository_dependencies_dict["repository_dependencies"] = repository_dependencies
            else:
                repository_dependencies_dict = dict(
                    description=description, repository_dependencies=repository_dependency_tups
                )
        if repository_dependencies_dict:
            if is_valid:
                metadata["repository_dependencies"] = repository_dependencies_dict
            else:
                metadata["invalid_repository_dependencies"] = repository_dependencies_dict
        return metadata


def _get_readme_file_names(repository_name):
    """Return a list of file names that will be categorized as README files for the received repository_name."""
    readme_files = ["readme", "read_me", "install"]
    valid_filenames = [f"{f}.txt" for f in readme_files]
    valid_filenames.extend([f"{f}.rst" for f in readme_files])
    valid_filenames.extend(readme_files)
    valid_filenames.append(f"{repository_name}.txt")
    valid_filenames.append(f"{repository_name}.rst")
    return valid_filenames
