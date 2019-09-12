import logging
import threading

from galaxy import util
from tool_shed.util import (
    common_util,
    container_util,
    readme_util
)
from . import utility_container_manager

log = logging.getLogger(__name__)


class FailedTest(object):
    """Failed tool tests object"""

    def __init__(self, id=None, stderr=None, test_id=None, tool_id=None, tool_version=None, traceback=None):
        self.id = id
        self.stderr = stderr
        self.test_id = test_id
        self.tool_id = tool_id
        self.tool_version = tool_version
        self.traceback = traceback


class InvalidRepositoryDependency(object):
    """Invalid repository dependency definition object"""

    def __init__(self, id=None, toolshed=None, repository_name=None, repository_owner=None, changeset_revision=None,
                 prior_installation_required=False, only_if_compiling_contained_td=False, error=None):
        self.id = id
        self.toolshed = toolshed
        self.repository_name = repository_name
        self.repository_owner = repository_owner
        self.changeset_revision = changeset_revision
        self.prior_installation_required = prior_installation_required
        self.only_if_compiling_contained_td = only_if_compiling_contained_td
        self.error = error


class InvalidToolDependency(object):
    """Invalid tool dependency definition object"""

    def __init__(self, id=None, name=None, version=None, type=None, error=None):
        self.id = id
        self.name = name
        self.version = version
        self.type = type
        self.error = error


class MissingTestComponent(object):
    """Missing tool test components object"""

    def __init__(self, id=None, missing_components=None, tool_guid=None, tool_id=None, tool_version=None):
        self.id = id
        self.missing_components = missing_components
        self.tool_guid = tool_guid
        self.tool_id = tool_id
        self.tool_version = tool_version


class NotTested(object):
    """NotTested object"""

    def __init__(self, id=None, reason=None):
        self.id = id
        self.reason = reason


class PassedTest(object):
    """Passed tool tests object"""

    def __init__(self, id=None, test_id=None, tool_id=None, tool_version=None):
        self.id = id
        self.test_id = test_id
        self.tool_id = tool_id
        self.tool_version = tool_version


class RepositoryInstallationError(object):
    """Repository installation error object"""

    def __init__(self, id=None, tool_shed=None, name=None, owner=None, changeset_revision=None, error_message=None):
        self.id = id
        self.tool_shed = tool_shed
        self.name = name
        self.owner = owner
        self.changeset_revision = changeset_revision
        self.error_message = error_message


class RepositorySuccessfulInstallation(object):
    """Repository installation object"""

    def __init__(self, id=None, tool_shed=None, name=None, owner=None, changeset_revision=None):
        self.id = id
        self.tool_shed = tool_shed
        self.name = name
        self.owner = owner
        self.changeset_revision = changeset_revision


class ToolDependencyInstallationError(object):
    """Tool dependency installation error object"""

    def __init__(self, id=None, type=None, name=None, version=None, error_message=None):
        self.id = id
        self.type = type
        self.name = name
        self.version = version
        self.error_message = error_message


class ToolDependencySuccessfulInstallation(object):
    """Tool dependency installation object"""

    def __init__(self, id=None, type=None, name=None, version=None, installation_directory=None):
        self.id = id
        self.type = type
        self.name = name
        self.version = version
        self.installation_directory = installation_directory


class ToolShedUtilityContainerManager(utility_container_manager.UtilityContainerManager):

    def __init__(self, app):
        self.app = app

    def build_invalid_repository_dependencies_root_folder(self, folder_id, invalid_repository_dependencies_dict):
        """Return a folder hierarchy containing invalid repository dependencies."""
        label = 'Invalid repository dependencies'
        if invalid_repository_dependencies_dict:
            invalid_repository_dependency_id = 0
            folder_id += 1
            invalid_repository_dependencies_root_folder = \
                utility_container_manager.Folder(id=folder_id,
                                                 key='root',
                                                 label='root',
                                                 parent=None)
            folder_id += 1
            invalid_repository_dependencies_folder = \
                utility_container_manager.Folder(id=folder_id,
                                                 key='invalid_repository_dependencies',
                                                 label=label,
                                                 parent=invalid_repository_dependencies_root_folder)
            invalid_repository_dependencies_root_folder.folders.append(invalid_repository_dependencies_folder)
            invalid_repository_dependencies = invalid_repository_dependencies_dict['repository_dependencies']
            for invalid_repository_dependency in invalid_repository_dependencies:
                folder_id += 1
                invalid_repository_dependency_id += 1
                toolshed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td, error = \
                    common_util.parse_repository_dependency_tuple(invalid_repository_dependency, contains_error=True)
                key = container_util.generate_repository_dependencies_key_for_repository(toolshed,
                                                                                         name,
                                                                                         owner,
                                                                                         changeset_revision,
                                                                                         prior_installation_required,
                                                                                         only_if_compiling_contained_td)
                label = "Repository <b>%s</b> revision <b>%s</b> owned by <b>%s</b>" % (name, changeset_revision, owner)
                folder = utility_container_manager.Folder(id=folder_id,
                                                          key=key,
                                                          label=label,
                                                          parent=invalid_repository_dependencies_folder)
                ird = InvalidRepositoryDependency(id=invalid_repository_dependency_id,
                                                  toolshed=toolshed,
                                                  repository_name=name,
                                                  repository_owner=owner,
                                                  changeset_revision=changeset_revision,
                                                  prior_installation_required=util.asbool(prior_installation_required),
                                                  only_if_compiling_contained_td=util.asbool(only_if_compiling_contained_td),
                                                  error=error)
                folder.invalid_repository_dependencies.append(ird)
                invalid_repository_dependencies_folder.folders.append(folder)
        else:
            invalid_repository_dependencies_root_folder = None
        return folder_id, invalid_repository_dependencies_root_folder

    def build_invalid_tool_dependencies_root_folder(self, folder_id, invalid_tool_dependencies_dict):
        """Return a folder hierarchy containing invalid tool dependencies."""
        # # INvalid tool dependencies are always packages like:
        # {"R/2.15.1": {"name": "R", "readme": "some string", "type": "package", "version": "2.15.1" "error" : "some sting" }
        label = 'Invalid tool dependencies'
        if invalid_tool_dependencies_dict:
            invalid_tool_dependency_id = 0
            folder_id += 1
            invalid_tool_dependencies_root_folder = \
                utility_container_manager.Folder(id=folder_id, key='root', label='root', parent=None)
            folder_id += 1
            invalid_tool_dependencies_folder = \
                utility_container_manager.Folder(id=folder_id,
                                                 key='invalid_tool_dependencies',
                                                 label=label,
                                                 parent=invalid_tool_dependencies_root_folder)
            invalid_tool_dependencies_root_folder.folders.append(invalid_tool_dependencies_folder)
            for td_key, requirements_dict in invalid_tool_dependencies_dict.items():
                folder_id += 1
                invalid_tool_dependency_id += 1
                try:
                    name = requirements_dict['name']
                    type = requirements_dict['type']
                    version = requirements_dict['version']
                    error = requirements_dict['error']
                except Exception as e:
                    name = 'unknown'
                    type = 'unknown'
                    version = 'unknown'
                    error = str(e)
                key = self.generate_tool_dependencies_key(name, version, type)
                label = "Version <b>%s</b> of the <b>%s</b> <b>%s</b>" % (version, name, type)
                folder = utility_container_manager.Folder(id=folder_id,
                                                          key=key,
                                                          label=label,
                                                          parent=invalid_tool_dependencies_folder)
                itd = InvalidToolDependency(id=invalid_tool_dependency_id,
                                            name=name,
                                            version=version,
                                            type=type,
                                            error=error)
                folder.invalid_tool_dependencies.append(itd)
                invalid_tool_dependencies_folder.folders.append(folder)
        else:
            invalid_tool_dependencies_root_folder = None
        return folder_id, invalid_tool_dependencies_root_folder

    def build_repository_containers(self, repository, changeset_revision, repository_dependencies, repository_metadata,
                                    exclude=None):
        """
        Return a dictionary of containers for the received repository's dependencies and
        contents for display in the Tool Shed.
        """
        if exclude is None:
            exclude = []
        containers_dict = dict(datatypes=None,
                               invalid_tools=None,
                               readme_files=None,
                               repository_dependencies=None,
                               tool_dependencies=None,
                               valid_tools=None,
                               workflows=None,
                               valid_data_managers=None)
        if repository_metadata:
            metadata = repository_metadata.metadata
            lock = threading.Lock()
            lock.acquire(True)
            try:
                folder_id = 0
                # Datatypes container.
                if metadata:
                    if 'datatypes' not in exclude and 'datatypes' in metadata:
                        datatypes = metadata['datatypes']
                        folder_id, datatypes_root_folder = self.build_datatypes_folder(folder_id, datatypes)
                        containers_dict['datatypes'] = datatypes_root_folder
                # Invalid repository dependencies container.
                if metadata:
                    if 'invalid_repository_dependencies' not in exclude and 'invalid_repository_dependencies' in metadata:
                        invalid_repository_dependencies = metadata['invalid_repository_dependencies']
                        folder_id, invalid_repository_dependencies_root_folder = \
                            self.build_invalid_repository_dependencies_root_folder(folder_id,
                                                                                   invalid_repository_dependencies)
                        containers_dict['invalid_repository_dependencies'] = invalid_repository_dependencies_root_folder
                # Invalid tool dependencies container.
                if metadata:
                    if 'invalid_tool_dependencies' not in exclude and 'invalid_tool_dependencies' in metadata:
                        invalid_tool_dependencies = metadata['invalid_tool_dependencies']
                        folder_id, invalid_tool_dependencies_root_folder = \
                            self.build_invalid_tool_dependencies_root_folder(folder_id,
                                                                             invalid_tool_dependencies)
                        containers_dict['invalid_tool_dependencies'] = invalid_tool_dependencies_root_folder
                # Invalid tools container.
                if metadata:
                    if 'invalid_tools' not in exclude and 'invalid_tools' in metadata:
                        invalid_tool_configs = metadata['invalid_tools']
                        folder_id, invalid_tools_root_folder = \
                            self.build_invalid_tools_folder(folder_id,
                                                            invalid_tool_configs,
                                                            changeset_revision,
                                                            repository=repository,
                                                            label='Invalid tools')
                        containers_dict['invalid_tools'] = invalid_tools_root_folder
                # Readme files container.
                if metadata:
                    if 'readme_files' not in exclude and 'readme_files' in metadata:
                        readme_files_dict = readme_util.build_readme_files_dict(self.app, repository, changeset_revision, metadata)
                        folder_id, readme_files_root_folder = self.build_readme_files_folder(folder_id, readme_files_dict)
                        containers_dict['readme_files'] = readme_files_root_folder
                if 'repository_dependencies' not in exclude:
                    # Repository dependencies container.
                    folder_id, repository_dependencies_root_folder = \
                        self.build_repository_dependencies_folder(folder_id=folder_id,
                                                                  repository_dependencies=repository_dependencies,
                                                                  label='Repository dependencies',
                                                                  installed=False)
                    if repository_dependencies_root_folder:
                        containers_dict['repository_dependencies'] = repository_dependencies_root_folder
                # Tool dependencies container.
                if metadata:
                    if 'tool_dependencies' not in exclude and 'tool_dependencies' in metadata:
                        tool_dependencies = metadata['tool_dependencies']
                        if 'orphan_tool_dependencies' in metadata:
                            # The use of the orphan_tool_dependencies category in metadata has been deprecated,
                            # but we still need to check in case the metadata is out of date.
                            orphan_tool_dependencies = metadata['orphan_tool_dependencies']
                            tool_dependencies.update(orphan_tool_dependencies)
                        # Tool dependencies can be categorized as orphans only if the repository contains tools.
                        if 'tools' not in exclude:
                            tools = metadata.get('tools', [])
                            tools.extend(metadata.get('invalid_tools', []))
                        folder_id, tool_dependencies_root_folder = \
                            self.build_tool_dependencies_folder(folder_id,
                                                                tool_dependencies,
                                                                missing=False,
                                                                new_install=False)
                        containers_dict['tool_dependencies'] = tool_dependencies_root_folder
                # Valid tools container.
                if metadata:
                    if 'tools' not in exclude and 'tools' in metadata:
                        valid_tools = metadata['tools']
                        folder_id, valid_tools_root_folder = self.build_tools_folder(folder_id,
                                                                                     valid_tools,
                                                                                     repository,
                                                                                     changeset_revision,
                                                                                     label='Valid tools')
                        containers_dict['valid_tools'] = valid_tools_root_folder
                # Workflows container.
                if metadata:
                    if 'workflows' not in exclude and 'workflows' in metadata:
                        workflows = metadata['workflows']
                        folder_id, workflows_root_folder = \
                            self.build_workflows_folder(folder_id=folder_id,
                                                        workflows=workflows,
                                                        repository_metadata_id=repository_metadata.id,
                                                        repository_id=None,
                                                        label='Workflows')
                        containers_dict['workflows'] = workflows_root_folder
                # Valid Data Managers container
                if metadata:
                    if 'data_manager' not in exclude and 'data_manager' in metadata:
                        data_managers = metadata['data_manager'].get('data_managers', None)
                        folder_id, data_managers_root_folder = \
                            self.build_data_managers_folder(folder_id, data_managers, label="Data Managers")
                        containers_dict['valid_data_managers'] = data_managers_root_folder
                        error_messages = metadata['data_manager'].get('error_messages', None)
                        data_managers = metadata['data_manager'].get('invalid_data_managers', None)
                        folder_id, data_managers_root_folder = \
                            self.build_invalid_data_managers_folder(folder_id,
                                                                    data_managers,
                                                                    error_messages,
                                                                    label="Invalid Data Managers")
                        containers_dict['invalid_data_managers'] = data_managers_root_folder
            except Exception:
                log.exception("Exception in build_repository_containers")
            finally:
                lock.release()
        return containers_dict

    def generate_tool_dependencies_key(self, name, version, type):
        return '%s%s%s%s%s' % (str(name), container_util.STRSEP, str(version), container_util.STRSEP, str(type))
