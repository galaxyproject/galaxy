import logging

from galaxy import util
from galaxy.tool_shed.util.container_util import (
    generate_repository_dependencies_key_for_repository,
    get_components_from_key,
)
from galaxy.tool_shed.util.repository_util import (
    extract_components_from_tuple,
    get_tool_shed_repository_by_id,
)
from galaxy.util import UNKNOWN
from galaxy.util.tool_shed.common_util import parse_repository_dependency_tuple

log = logging.getLogger(__name__)


class Folder:
    """Container object."""

    def __init__(self, id=None, key=None, label=None, parent=None):
        self.id = id
        self.key = key
        self.label = label
        self.parent = parent
        self.current_repository_installation_errors = []
        self.current_repository_successful_installations = []
        self.description = None
        self.datatypes = []
        self.folders = []
        self.invalid_data_managers = []
        self.invalid_repository_dependencies = []
        self.invalid_tool_dependencies = []
        self.invalid_tools = []
        self.missing_test_components = []
        self.readme_files = []
        self.repository_dependencies = []
        self.repository_installation_errors = []
        self.repository_successful_installations = []
        self.test_environments = []
        self.tool_dependencies = []
        self.valid_tools = []
        self.valid_data_managers = []
        self.workflows = []

    def to_dict(self):
        folders = []
        if self.folders:
            for folder in self.folders:
                folders.append(folder.to_dict())
        repository_dependencies = []
        for rd in self.repository_dependencies or []:
            repository_dependencies.append(rd.to_dict())
        return {
            "description": self.description,
            "folders": folders,
            "repository_dependencies": repository_dependencies,
        }


class DataManager:
    """Data Manager object"""

    def __init__(self, id=None, name=None, version=None, data_tables=None):
        self.id = id
        self.name = name
        self.version = version
        self.data_tables = data_tables


class InvalidTool:
    """Invalid tool object"""

    def __init__(
        self,
        id=None,
        tool_config=None,
        repository_id=None,
        changeset_revision=None,
        repository_installation_status=None,
    ):
        self.id = id
        self.tool_config = tool_config
        self.repository_id = repository_id
        self.changeset_revision = changeset_revision
        self.repository_installation_status = repository_installation_status


class RepositoryDependency:
    """Repository dependency object"""

    def __init__(
        self,
        id=None,
        toolshed=None,
        repository_name=None,
        repository_owner=None,
        changeset_revision=None,
        prior_installation_required=False,
        only_if_compiling_contained_td=False,
        installation_status=None,
        tool_shed_repository_id=None,
    ):
        self.id = id
        self.toolshed = toolshed
        self.repository_name = repository_name
        self.repository_owner = repository_owner
        self.changeset_revision = changeset_revision
        self.prior_installation_required = prior_installation_required
        self.only_if_compiling_contained_td = only_if_compiling_contained_td
        self.installation_status = installation_status
        self.tool_shed_repository_id = tool_shed_repository_id

    @property
    def listify(self):
        return [
            self.toolshed,
            self.repository_name,
            self.repository_owner,
            self.changeset_revision,
            self.prior_installation_required,
            self.only_if_compiling_contained_td,
        ]

    def to_dict(self):
        return {
            "toolshed": self.toolshed,
            "repository_name": self.repository_name,
            "repository_owner": self.repository_owner,
            "changeset_revision": self.changeset_revision,
        }


class Tool:
    """Tool object"""

    def __init__(
        self,
        id=None,
        tool_config=None,
        tool_id=None,
        name=None,
        description=None,
        version=None,
        profile=None,
        requirements=None,
        repository_id=None,
        changeset_revision=None,
        repository_installation_status=None,
    ):
        self.id = id
        self.tool_config = tool_config
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.version = version
        self.profile = profile
        self.requirements = requirements
        self.repository_id = repository_id
        self.changeset_revision = changeset_revision
        self.repository_installation_status = repository_installation_status


class ToolDependency:
    """Tool dependency object"""

    def __init__(
        self,
        id=None,
        name=None,
        version=None,
        type=None,
        readme=None,
        installation_status=None,
        repository_id=None,
        tool_dependency_id=None,
    ):
        self.id = id
        self.name = name
        self.version = version
        self.type = type
        self.readme = readme
        self.installation_status = installation_status
        self.repository_id = repository_id
        self.tool_dependency_id = tool_dependency_id

    @property
    def listify(self):
        return [self.name, self.version, self.type]


class UtilityContainerManager:
    def __init__(self, app):
        self.app = app

    def build_repository_dependencies_folder(
        self, folder_id, repository_dependencies, label="Repository dependencies", installed=False
    ):
        """Return a folder hierarchy containing repository dependencies."""
        if repository_dependencies:
            repository_dependency_id = 0
            folder_id += 1
            # Create the root folder.
            repository_dependencies_root_folder = Folder(id=folder_id, key="root", label="root", parent=None)
            folder_id += 1
            # Create the Repository dependencies folder and add it to the root folder.
            repository_dependencies_folder_key = repository_dependencies["root_key"]
            repository_dependencies_folder = Folder(
                id=folder_id,
                key=repository_dependencies_folder_key,
                label=label,
                parent=repository_dependencies_root_folder,
            )
            del repository_dependencies["root_key"]
            # The received repository_dependencies is a dictionary with keys: 'root_key', 'description', and one or more
            # repository_dependency keys.  We want the description value associated with the repository_dependencies_folder.
            repository_dependencies_folder.description = repository_dependencies.get("description", None)
            repository_dependencies_root_folder.folders.append(repository_dependencies_folder)
            del repository_dependencies["description"]
            (
                repository_dependencies_folder,
                folder_id,
                repository_dependency_id,
            ) = self.populate_repository_dependencies_container(
                repository_dependencies_folder, repository_dependencies, folder_id, repository_dependency_id
            )
            repository_dependencies_folder = self.prune_repository_dependencies(repository_dependencies_folder)
        else:
            repository_dependencies_root_folder = None
        return folder_id, repository_dependencies_root_folder

    def generate_repository_dependencies_folder_label_from_key(
        self,
        repository_name,
        repository_owner,
        changeset_revision,
        prior_installation_required,
        only_if_compiling_contained_td,
        key,
    ):
        """Return a repository dependency label based on the repository dependency key."""
        if self.key_is_current_repositorys_key(
            repository_name,
            repository_owner,
            changeset_revision,
            prior_installation_required,
            only_if_compiling_contained_td,
            key,
        ):
            label = "Repository dependencies"
        else:
            if util.asbool(prior_installation_required):
                prior_installation_required_str = " <i>(prior install required)</i>"
            else:
                prior_installation_required_str = ""
            label = f"Repository <b>{repository_name}</b> revision <b>{changeset_revision}</b> owned by <b>{repository_owner}</b>{prior_installation_required_str}"
        return label

    def get_components_from_repository_dependency_for_installed_repository(self, repository_dependency):
        """
        Parse a repository dependency and return components necessary for proper display
        in Galaxy on the Manage repository page.
        """
        # Default prior_installation_required and only_if_compiling_contained_td to False.
        prior_installation_required = "False"
        only_if_compiling_contained_td = "False"
        if len(repository_dependency) == 6:
            # Metadata should have been reset on this installed repository, but it wasn't.
            tool_shed_repository_id = repository_dependency[4]
            installation_status = repository_dependency[5]
            tool_shed, name, owner, changeset_revision = repository_dependency[0:4]
            repository_dependency = [
                tool_shed,
                name,
                owner,
                changeset_revision,
                prior_installation_required,
                only_if_compiling_contained_td,
            ]
        elif len(repository_dependency) == 7:
            # We have a repository dependency tuple that includes a prior_installation_required value but not a only_if_compiling_contained_td value.
            tool_shed_repository_id = repository_dependency[5]
            installation_status = repository_dependency[6]
            tool_shed, name, owner, changeset_revision, prior_installation_required = repository_dependency[0:5]
            repository_dependency = [
                tool_shed,
                name,
                owner,
                changeset_revision,
                prior_installation_required,
                only_if_compiling_contained_td,
            ]
        elif len(repository_dependency) == 8:
            # We have a repository dependency tuple that includes both a prior_installation_required value
            # and a only_if_compiling_contained_td value.
            tool_shed_repository_id = repository_dependency[6]
            installation_status = repository_dependency[7]
            repository_dependency = repository_dependency[0:6]
        else:
            tool_shed_repository_id = None
            installation_status = UNKNOWN
        if tool_shed_repository_id:
            tool_shed_repository = get_tool_shed_repository_by_id(
                self.app, self.app.security.encode_id(tool_shed_repository_id)
            )
            if tool_shed_repository:
                if tool_shed_repository.missing_repository_dependencies:
                    installation_status = f"{installation_status}, missing repository dependencies"
                elif tool_shed_repository.missing_tool_dependencies:
                    installation_status = f"{installation_status}, missing tool dependencies"
        return tool_shed_repository_id, installation_status, repository_dependency

    def get_folder(self, folder, key):
        if folder.key == key:
            return folder
        for sub_folder in folder.folders:
            return self.get_folder(sub_folder, key)
        return None

    def handle_repository_dependencies_container_entry(
        self, repository_dependencies_folder, rd_key, rd_value, folder_id, repository_dependency_id, folder_keys
    ):
        repository_components_tuple = get_components_from_key(rd_key)
        components_list = extract_components_from_tuple(repository_components_tuple)
        toolshed, repository_name, repository_owner, changeset_revision = components_list[0:4]
        # For backward compatibility to the 12/20/12 Galaxy release.
        if len(components_list) == 4:
            prior_installation_required = "False"
            only_if_compiling_contained_td = "False"
        elif len(components_list) == 5:
            prior_installation_required = components_list[4]
            only_if_compiling_contained_td = "False"
        elif len(components_list) == 6:
            prior_installation_required = components_list[4]
            only_if_compiling_contained_td = components_list[5]
        folder = self.get_folder(repository_dependencies_folder, rd_key)
        label = self.generate_repository_dependencies_folder_label_from_key(
            repository_name,
            repository_owner,
            changeset_revision,
            prior_installation_required,
            only_if_compiling_contained_td,
            repository_dependencies_folder.key,
        )
        if folder:
            if rd_key not in folder_keys:
                folder_id += 1
                sub_folder = Folder(id=folder_id, key=rd_key, label=label, parent=folder)
                folder.folders.append(sub_folder)
            else:
                sub_folder = folder
        else:
            folder_id += 1
            sub_folder = Folder(id=folder_id, key=rd_key, label=label, parent=repository_dependencies_folder)
            repository_dependencies_folder.folders.append(sub_folder)
        if self.app.name == "galaxy":
            # Insert a header row.
            repository_dependency_id += 1
            repository_dependency = RepositoryDependency(
                id=repository_dependency_id,
                repository_name="Name",
                changeset_revision="Revision",
                repository_owner="Owner",
                installation_status="Installation status",
            )
            # Insert the header row into the folder.
            sub_folder.repository_dependencies.append(repository_dependency)
        for repository_dependency in rd_value:
            if self.app.name == "galaxy":
                (
                    tool_shed_repository_id,
                    installation_status,
                    repository_dependency,
                ) = self.get_components_from_repository_dependency_for_installed_repository(repository_dependency)
            else:
                tool_shed_repository_id = None
                installation_status = None
            can_create_dependency = not self.is_subfolder_of(sub_folder, repository_dependency)
            if can_create_dependency:
                (
                    toolshed,
                    repository_name,
                    repository_owner,
                    changeset_revision,
                    prior_installation_required,
                    only_if_compiling_contained_td,
                ) = parse_repository_dependency_tuple(repository_dependency)
                repository_dependency_id += 1
                repository_dependency = RepositoryDependency(
                    id=repository_dependency_id,
                    toolshed=toolshed,
                    repository_name=repository_name,
                    repository_owner=repository_owner,
                    changeset_revision=changeset_revision,
                    prior_installation_required=util.asbool(prior_installation_required),
                    only_if_compiling_contained_td=util.asbool(only_if_compiling_contained_td),
                    installation_status=installation_status,
                    tool_shed_repository_id=tool_shed_repository_id,
                )
                # Insert the repository_dependency into the folder.
                sub_folder.repository_dependencies.append(repository_dependency)
        return repository_dependencies_folder, folder_id, repository_dependency_id

    def is_subfolder_of(self, folder, repository_dependency):
        (
            toolshed,
            repository_name,
            repository_owner,
            changeset_revision,
            prior_installation_required,
            only_if_compiling_contained_td,
        ) = parse_repository_dependency_tuple(repository_dependency)
        key = generate_repository_dependencies_key_for_repository(
            toolshed,
            repository_name,
            repository_owner,
            changeset_revision,
            prior_installation_required,
            only_if_compiling_contained_td,
        )
        for sub_folder in folder.folders:
            if key == sub_folder.key:
                return True
        return False

    def key_is_current_repositorys_key(
        self,
        repository_name,
        repository_owner,
        changeset_revision,
        prior_installation_required,
        only_if_compiling_contained_td,
        key,
    ):
        repository_components_tuple = get_components_from_key(key)
        components_list = extract_components_from_tuple(repository_components_tuple)
        toolshed, key_name, key_owner, key_changeset_revision = components_list[0:4]
        # For backward compatibility to the 12/20/12 Galaxy release.
        if len(components_list) == 4:
            key_prior_installation_required = "False"
            key_only_if_compiling_contained_td = "False"
        elif len(components_list) == 5:
            key_prior_installation_required = components_list[4]
            key_only_if_compiling_contained_td = "False"
        elif len(components_list) == 6:
            key_prior_installation_required = components_list[4]
            key_only_if_compiling_contained_td = components_list[5]
        if (
            repository_name == key_name
            and repository_owner == key_owner
            and changeset_revision == key_changeset_revision
            and prior_installation_required == key_prior_installation_required
            and only_if_compiling_contained_td == key_only_if_compiling_contained_td
        ):
            return True
        return False

    def populate_repository_dependencies_container(
        self, repository_dependencies_folder, repository_dependencies, folder_id, repository_dependency_id
    ):
        folder_keys = []
        for key in repository_dependencies.keys():
            if key not in folder_keys:
                folder_keys.append(key)
        for key, value in repository_dependencies.items():
            (
                repository_dependencies_folder,
                folder_id,
                repository_dependency_id,
            ) = self.handle_repository_dependencies_container_entry(
                repository_dependencies_folder, key, value, folder_id, repository_dependency_id, folder_keys
            )
        return repository_dependencies_folder, folder_id, repository_dependency_id

    def prune_folder(self, folder, repository_dependency):
        listified_repository_dependency = repository_dependency.listify
        if self.is_subfolder_of(folder, listified_repository_dependency):
            folder.repository_dependencies.remove(repository_dependency)

    def prune_repository_dependencies(self, folder):
        """
        Since the object used to generate a repository dependencies container is a dictionary
        and not an OrderedDict() (it must be json-serialize-able), the order in which the dictionary
        is processed to create the container sometimes results in repository dependency entries
        in a folder that also includes the repository dependency as a sub-folder (if the repository
        dependency has its own repository dependency).  This method will remove all repository
        dependencies from folder that are also sub-folders of folder.
        """
        repository_dependencies = list(folder.repository_dependencies)
        for repository_dependency in repository_dependencies:
            self.prune_folder(folder, repository_dependency)
        for sub_folder in folder.folders:
            return self.prune_repository_dependencies(sub_folder)
        return folder
