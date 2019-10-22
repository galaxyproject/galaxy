import logging
import os

from galaxy.util import asbool
from galaxy.util.bunch import Bunch
from galaxy.util.dictifiable import Dictifiable
from galaxy.util.tool_shed import common_util

log = logging.getLogger(__name__)


class ToolShedRepository(object):
    dict_collection_visible_keys = ['id', 'tool_shed', 'name', 'owner', 'installed_changeset_revision', 'changeset_revision', 'ctx_rev', 'includes_datatypes',
                                    'tool_shed_status', 'deleted', 'uninstalled', 'dist_to_shed', 'status', 'error_message']
    dict_element_visible_keys = ['id', 'tool_shed', 'name', 'owner', 'installed_changeset_revision', 'changeset_revision', 'ctx_rev', 'includes_datatypes',
                                 'tool_shed_status', 'deleted', 'uninstalled', 'dist_to_shed', 'status', 'error_message']
    installation_status = Bunch(NEW='New',
                                CLONING='Cloning',
                                SETTING_TOOL_VERSIONS='Setting tool versions',
                                INSTALLING_REPOSITORY_DEPENDENCIES='Installing repository dependencies',
                                INSTALLING_TOOL_DEPENDENCIES='Installing tool dependencies',
                                LOADING_PROPRIETARY_DATATYPES='Loading proprietary datatypes',
                                INSTALLED='Installed',
                                DEACTIVATED='Deactivated',
                                ERROR='Error',
                                UNINSTALLED='Uninstalled')
    states = Bunch(INSTALLING='running',
                   OK='ok',
                   WARNING='queued',
                   ERROR='error',
                   UNINSTALLED='deleted_new')

    def __init__(self, id=None, create_time=None, tool_shed=None, name=None, description=None, owner=None, installed_changeset_revision=None,
                 changeset_revision=None, ctx_rev=None, metadata=None, includes_datatypes=False, tool_shed_status=None, deleted=False,
                 uninstalled=False, dist_to_shed=False, status=None, error_message=None):
        self.id = id
        self.create_time = create_time
        self.tool_shed = tool_shed
        self.name = name
        self.description = description
        self.owner = owner
        self.installed_changeset_revision = installed_changeset_revision
        self.changeset_revision = changeset_revision
        self.ctx_rev = ctx_rev
        self.metadata = metadata or {}
        self.includes_datatypes = includes_datatypes
        self.tool_shed_status = tool_shed_status
        self.deleted = deleted
        self.uninstalled = uninstalled
        self.dist_to_shed = dist_to_shed
        self.status = status
        self.error_message = error_message

    def as_dict(self, value_mapper=None):
        return self.to_dict(view='element', value_mapper=value_mapper)

    @property
    def can_install(self):
        return self.status == self.installation_status.NEW

    @property
    def can_reset_metadata(self):
        return self.status == self.installation_status.INSTALLED

    @property
    def can_uninstall(self):
        return self.status != self.installation_status.UNINSTALLED

    @property
    def can_deactivate(self):
        return self.status not in [self.installation_status.DEACTIVATED,
                                   self.installation_status.ERROR,
                                   self.installation_status.UNINSTALLED]

    @property
    def can_reinstall_or_activate(self):
        return self.deleted

    def get_sharable_url(self, app):
        return common_util.get_tool_shed_repository_url(app, self.tool_shed, self.owner, self.name)

    @property
    def shed_config_filename(self):
        return self.metadata.get('shed_config_filename', None)

    @shed_config_filename.setter
    def shed_config_filename(self, value):
        self.metadata['shed_config_filename'] = value

    def get_shed_config_dict(self, app, default=None):
        """
        Return the in-memory version of the shed_tool_conf file, which is stored in the config_elems entry
        in the shed_tool_conf_dict.
        """

        def _is_valid_shed_config_filename(filename):
            for shed_tool_conf_dict in app.toolbox.dynamic_confs(include_migrated_tool_conf=True):
                if filename == shed_tool_conf_dict['config_filename']:
                    return True
            return False

        if not self.shed_config_filename or not _is_valid_shed_config_filename(self.shed_config_filename):
            self.guess_shed_config(app, default=default)
        if self.shed_config_filename:
            for shed_tool_conf_dict in app.toolbox.dynamic_confs(include_migrated_tool_conf=True):
                if self.shed_config_filename == shed_tool_conf_dict['config_filename']:
                    return shed_tool_conf_dict
        return default

    def get_tool_relative_path(self, app):
        # This is a somewhat public function, used by data_manager_manual for instance
        shed_conf_dict = self.get_shed_config_dict(app)
        tool_path = None
        relative_path = None
        if shed_conf_dict:
            tool_path = shed_conf_dict['tool_path']
            relative_path = os.path.join(self.tool_shed_path_name, 'repos', self.owner, self.name, self.installed_changeset_revision)
        return tool_path, relative_path

    def guess_shed_config(self, app, default=None):
        tool_ids = []
        metadata = self.metadata
        for tool in metadata.get('tools', []):
            tool_ids.append(tool.get('guid'))
        for shed_tool_conf_dict in app.toolbox.dynamic_confs(include_migrated_tool_conf=True):
            name = shed_tool_conf_dict['config_filename']
            for elem in shed_tool_conf_dict['config_elems']:
                if elem.tag == 'tool':
                    for sub_elem in elem.findall('id'):
                        tool_id = sub_elem.text.strip()
                        if tool_id in tool_ids:
                            self.shed_config_filename = name
                            return shed_tool_conf_dict
                elif elem.tag == "section":
                    for tool_elem in elem.findall('tool'):
                        for sub_elem in tool_elem.findall('id'):
                            tool_id = sub_elem.text.strip()
                            if tool_id in tool_ids:
                                self.shed_config_filename = name
                                return shed_tool_conf_dict
        if self.includes_datatypes or self.includes_data_managers:
            # We need to search by file paths here, which is less desirable.
            tool_shed = common_util.remove_protocol_and_port_from_tool_shed_url(self.tool_shed)
            for shed_tool_conf_dict in app.toolbox.dynamic_confs(include_migrated_tool_conf=True):
                tool_path = shed_tool_conf_dict['tool_path']
                relative_path = os.path.join(tool_path, tool_shed, 'repos', self.owner, self.name, self.installed_changeset_revision)
                if os.path.exists(relative_path):
                    self.shed_config_filename = shed_tool_conf_dict['config_filename']
                    return shed_tool_conf_dict
        return default

    @property
    def has_readme_files(self):
        return 'readme_files' in self.metadata

    @property
    def has_repository_dependencies(self):
        repository_dependencies_dict = self.metadata.get('repository_dependencies', {})
        repository_dependencies = repository_dependencies_dict.get('repository_dependencies', [])
        # [["http://localhost:9009", "package_libgtextutils_0_6", "test", "e2003cbf18cd", "True", "True"]]
        for rd_tup in repository_dependencies:
            tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
                common_util.parse_repository_dependency_tuple(rd_tup)
            if not asbool(only_if_compiling_contained_td):
                return True
        return False

    @property
    def has_repository_dependencies_only_if_compiling_contained_td(self):
        repository_dependencies_dict = self.metadata.get('repository_dependencies', {})
        repository_dependencies = repository_dependencies_dict.get('repository_dependencies', [])
        # [["http://localhost:9009", "package_libgtextutils_0_6", "test", "e2003cbf18cd", "True", "True"]]
        for rd_tup in repository_dependencies:
            tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
                common_util.parse_repository_dependency_tuple(rd_tup)
            if not asbool(only_if_compiling_contained_td):
                return False
        return True

    @property
    def in_error_state(self):
        return self.status == self.installation_status.ERROR

    @property
    def includes_data_managers(self):
        return bool(len(self.metadata.get('data_manager', {}).get('data_managers', {})))

    @property
    def includes_tools(self):
        return 'tools' in self.metadata

    @property
    def includes_tools_for_display_in_tool_panel(self):
        if self.includes_tools:
            tool_dicts = self.metadata['tools']
            for tool_dict in tool_dicts:
                if tool_dict.get('add_to_tool_panel', True):
                    return True
        return False

    @property
    def includes_tool_dependencies(self):
        return 'tool_dependencies' in self.metadata

    @property
    def includes_workflows(self):
        return 'workflows' in self.metadata

    @property
    def installed_repository_dependencies(self):
        """Return the repository's repository dependencies that are currently installed."""
        installed_required_repositories = []
        for required_repository in self.repository_dependencies:
            if required_repository.status == self.installation_status.INSTALLED:
                installed_required_repositories.append(required_repository)
        return installed_required_repositories

    @property
    def installed_tool_dependencies(self):
        """Return the repository's tool dependencies that are currently installed, but possibly in an error state."""
        installed_dependencies = []
        for tool_dependency in self.tool_dependencies:
            if tool_dependency.status in [ToolDependency.installation_status.INSTALLED]:
                installed_dependencies.append(tool_dependency)
        return installed_dependencies

    @property
    def is_deprecated_in_tool_shed(self):
        if self.tool_shed_status:
            return asbool(self.tool_shed_status.get('repository_deprecated', False))
        return False

    @property
    def is_deactivated_or_installed(self):
        return self.status in [self.installation_status.DEACTIVATED,
                               self.installation_status.INSTALLED]

    @property
    def is_installed(self):
        return self.status == self.installation_status.INSTALLED

    @property
    def is_latest_installable_revision(self):
        if self.tool_shed_status:
            return asbool(self.tool_shed_status.get('latest_installable_revision', False))
        return False

    @property
    def is_new(self):
        return self.status == self.installation_status.NEW

    @property
    def missing_repository_dependencies(self):
        """Return the repository's repository dependencies that are not currently installed, and may not ever have been installed."""
        missing_required_repositories = []
        for required_repository in self.repository_dependencies:
            if required_repository.status not in [self.installation_status.INSTALLED]:
                missing_required_repositories.append(required_repository)
        return missing_required_repositories

    @property
    def missing_tool_dependencies(self):
        """Return the repository's tool dependencies that are not currently installed, and may not ever have been installed."""
        missing_dependencies = []
        for tool_dependency in self.tool_dependencies:
            if tool_dependency.status not in [ToolDependency.installation_status.INSTALLED]:
                missing_dependencies.append(tool_dependency)
        return missing_dependencies

    def repo_files_directory(self, app):
        repo_path = self.repo_path(app)
        if repo_path:
            return os.path.join(repo_path, self.name)
        return None

    def repo_path(self, app):
        tool_shed = common_util.remove_protocol_and_port_from_tool_shed_url(self.tool_shed)
        for shed_tool_conf_dict in app.toolbox.dynamic_confs(include_migrated_tool_conf=True):
            tool_path = shed_tool_conf_dict['tool_path']
            relative_path = os.path.join(tool_path, tool_shed, 'repos', self.owner, self.name, self.installed_changeset_revision)
            if os.path.exists(relative_path):
                return relative_path
        return None

    @property
    def repository_dependencies(self):
        """
        Return all of this repository's repository dependencies, ignoring their attributes like prior_installation_required and
        only_if_compiling_contained_td.
        """
        required_repositories = []
        for rrda in self.required_repositories:
            repository_dependency = rrda.repository_dependency
            required_repository = repository_dependency.repository
            if required_repository:
                required_repositories.append(required_repository)
        return required_repositories

    @property
    def repository_dependencies_being_installed(self):
        """Return the repository's repository dependencies that are currently being installed."""
        required_repositories_being_installed = []
        for required_repository in self.repository_dependencies:
            if required_repository.status in [self.installation_status.CLONING,
                                              self.installation_status.INSTALLING_REPOSITORY_DEPENDENCIES,
                                              self.installation_status.INSTALLING_TOOL_DEPENDENCIES,
                                              self.installation_status.LOADING_PROPRIETARY_DATATYPES,
                                              self.installation_status.SETTING_TOOL_VERSIONS]:
                required_repositories_being_installed.append(required_repository)
        return required_repositories_being_installed

    @property
    def repository_dependencies_missing_or_being_installed(self):
        """Return the repository's repository dependencies that are either missing or currently being installed."""
        required_repositories_missing_or_being_installed = []
        for required_repository in self.repository_dependencies:
            if required_repository.status in [self.installation_status.ERROR,
                                              self.installation_status.INSTALLING,
                                              self.installation_status.NEVER_INSTALLED,
                                              self.installation_status.UNINSTALLED]:
                required_repositories_missing_or_being_installed.append(required_repository)
        return required_repositories_missing_or_being_installed

    @property
    def repository_dependencies_with_installation_errors(self):
        """Return the repository's repository dependencies that have installation errors."""
        required_repositories_with_installation_errors = []
        for required_repository in self.repository_dependencies:
            if required_repository.status == self.installation_status.ERROR:
                required_repositories_with_installation_errors.append(required_repository)
        return required_repositories_with_installation_errors

    @property
    def requires_prior_installation_of(self):
        """
        Return a list of repository dependency tuples like (tool_shed, name, owner, changeset_revision, prior_installation_required) for this
        repository's repository dependencies where prior_installation_required is True.  By definition, repository dependencies are required to
        be installed in order for this repository to function correctly.  However, those repository dependencies that are defined for this
        repository with prior_installation_required set to True place them in a special category in that the required repositories must be
        installed before this repository is installed.  Among other things, this enables these "special" repository dependencies to include
        information that enables the successful installation of this repository.  This method is not used during the initial installation of
        this repository, but only after it has been installed (metadata must be set for this repository in order for this method to be useful).
        """
        required_rd_tups_that_must_be_installed = []
        if self.has_repository_dependencies:
            rd_tups = self.metadata['repository_dependencies']['repository_dependencies']
            for rd_tup in rd_tups:
                if len(rd_tup) == 5:
                    tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
                        common_util.parse_repository_dependency_tuple(rd_tup, contains_error=False)
                    if asbool(prior_installation_required):
                        required_rd_tups_that_must_be_installed.append((tool_shed, name, owner, changeset_revision, 'True', 'False'))
                elif len(rd_tup) == 6:
                    tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
                        common_util.parse_repository_dependency_tuple(rd_tup, contains_error=False)
                    # The repository dependency will only be required to be previously installed if it does not fall into the category of
                    # a repository that must be installed only so that its contained tool dependency can be used for compiling the tool
                    # dependency of the dependent repository.
                    if not asbool(only_if_compiling_contained_td):
                        if asbool(prior_installation_required):
                            required_rd_tups_that_must_be_installed.append((tool_shed, name, owner, changeset_revision, 'True', 'False'))
        return required_rd_tups_that_must_be_installed

    @property
    def revision_update_available(self):
        # This method should be named update_available, but since it is no longer possible to drop a table column using migration scripts
        # with the sqlite database (see ~/galaxy/model/migrate/versions/0016_drop_update_available_col_add_tool_shed_status_col.py), we
        # have to name it in such a way that it will not conflict with the eliminated tool_shed_repository.update_available column (which
        # cannot be eliminated if using the sqlite database).
        if self.tool_shed_status:
            return asbool(self.tool_shed_status.get('revision_update', False))
        return False

    def to_dict(self, view='collection', value_mapper=None):
        if value_mapper is None:
            value_mapper = {}
        rval = {}
        try:
            visible_keys = self.__getattribute__('dict_' + view + '_visible_keys')
        except AttributeError:
            raise Exception('Unknown API view: %s' % view)
        for key in visible_keys:
            try:
                rval[key] = self.__getattribute__(key)
                if key in value_mapper:
                    rval[key] = value_mapper.get(key, rval[key])
            except AttributeError:
                rval[key] = None
        return rval

    @property
    def tool_dependencies_being_installed(self):
        dependencies_being_installed = []
        for tool_dependency in self.tool_dependencies:
            if tool_dependency.status == ToolDependency.installation_status.INSTALLING:
                dependencies_being_installed.append(tool_dependency)
        return dependencies_being_installed

    @property
    def tool_dependencies_installed_or_in_error(self):
        """Return the repository's tool dependencies that are currently installed, but possibly in an error state."""
        installed_dependencies = []
        for tool_dependency in self.tool_dependencies:
            if tool_dependency.status in [ToolDependency.installation_status.INSTALLED,
                                          ToolDependency.installation_status.ERROR]:
                installed_dependencies.append(tool_dependency)
        return installed_dependencies

    @property
    def tool_dependencies_missing_or_being_installed(self):
        dependencies_missing_or_being_installed = []
        for tool_dependency in self.tool_dependencies:
            if tool_dependency.status in [ToolDependency.installation_status.ERROR,
                                          ToolDependency.installation_status.INSTALLING,
                                          ToolDependency.installation_status.NEVER_INSTALLED,
                                          ToolDependency.installation_status.UNINSTALLED]:
                dependencies_missing_or_being_installed.append(tool_dependency)
        return dependencies_missing_or_being_installed

    @property
    def tool_dependencies_with_installation_errors(self):
        dependencies_with_installation_errors = []
        for tool_dependency in self.tool_dependencies:
            if tool_dependency.status == ToolDependency.installation_status.ERROR:
                dependencies_with_installation_errors.append(tool_dependency)
        return dependencies_with_installation_errors

    @property
    def tool_shed_path_name(self):
        tool_shed_url = self.tool_shed
        if tool_shed_url.find(':') > 0:
            # Eliminate the port, if any, since it will result in an invalid directory name.
            tool_shed_url = tool_shed_url.split(':')[0]
        return tool_shed_url.rstrip('/')

    @property
    def tuples_of_repository_dependencies_needed_for_compiling_td(self):
        """
        Return tuples defining this repository's repository dependencies that are necessary only for compiling this repository's tool
        dependencies.
        """
        rd_tups_of_repositories_needed_for_compiling_td = []
        repository_dependencies = self.metadata.get('repository_dependencies', None)
        rd_tups = repository_dependencies['repository_dependencies']
        for rd_tup in rd_tups:
            if len(rd_tup) == 6:
                tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = rd_tup
                if asbool(only_if_compiling_contained_td):
                    rd_tups_of_repositories_needed_for_compiling_td.append((tool_shed, name, owner, changeset_revision, 'False', 'True'))
        return rd_tups_of_repositories_needed_for_compiling_td

    @property
    def uninstalled_repository_dependencies(self):
        """Return the repository's repository dependencies that have been uninstalled."""
        uninstalled_required_repositories = []
        for required_repository in self.repository_dependencies:
            if required_repository.status == self.installation_status.UNINSTALLED:
                uninstalled_required_repositories.append(required_repository)
        return uninstalled_required_repositories

    @property
    def uninstalled_tool_dependencies(self):
        """Return the repository's tool dependencies that have been uninstalled."""
        uninstalled_tool_dependencies = []
        for tool_dependency in self.tool_dependencies:
            if tool_dependency.status == ToolDependency.installation_status.UNINSTALLED:
                uninstalled_tool_dependencies.append(tool_dependency)
        return uninstalled_tool_dependencies

    @property
    def upgrade_available(self):
        if self.tool_shed_status:
            if self.is_deprecated_in_tool_shed:
                # Only allow revision upgrades if the repository is not deprecated in the tool shed.
                return False
            return asbool(self.tool_shed_status.get('revision_upgrade', False))
        return False


class RepositoryRepositoryDependencyAssociation(object):

    def __init__(self, tool_shed_repository_id=None, repository_dependency_id=None):
        self.tool_shed_repository_id = tool_shed_repository_id
        self.repository_dependency_id = repository_dependency_id


class RepositoryDependency(object):

    def __init__(self, tool_shed_repository_id=None):
        self.tool_shed_repository_id = tool_shed_repository_id


class ToolDependency(object):
    installation_status = Bunch(NEVER_INSTALLED='Never installed',
                                INSTALLING='Installing',
                                INSTALLED='Installed',
                                ERROR='Error',
                                UNINSTALLED='Uninstalled')

    states = Bunch(INSTALLING='running',
                   OK='ok',
                   WARNING='queued',
                   ERROR='error',
                   UNINSTALLED='deleted_new')

    def __init__(self, tool_shed_repository_id=None, name=None, version=None, type=None, status=None, error_message=None):
        self.tool_shed_repository_id = tool_shed_repository_id
        self.name = name
        self.version = version
        self.type = type
        self.status = status
        self.error_message = error_message

    @property
    def can_install(self):
        return self.status in [self.installation_status.NEVER_INSTALLED, self.installation_status.UNINSTALLED]

    @property
    def can_uninstall(self):
        return self.status in [self.installation_status.ERROR, self.installation_status.INSTALLED]

    @property
    def can_update(self):
        return self.status in [self.installation_status.NEVER_INSTALLED,
                               self.installation_status.INSTALLED,
                               self.installation_status.ERROR,
                               self.installation_status.UNINSTALLED]

    def get_env_shell_file_path(self, app):
        installation_directory = self.installation_directory(app)
        file_path = os.path.join(installation_directory, 'env.sh')
        if os.path.exists(file_path):
            return file_path
        return None

    @property
    def in_error_state(self):
        return self.status == self.installation_status.ERROR

    def installation_directory(self, app):
        if self.type == 'package':
            return os.path.join(app.tool_dependency_dir,
                                self.name,
                                self.version,
                                self.tool_shed_repository.owner,
                                self.tool_shed_repository.name,
                                self.tool_shed_repository.installed_changeset_revision)
        if self.type == 'set_environment':
            return os.path.join(app.tool_dependency_dir,
                                'environment_settings',
                                self.name,
                                self.tool_shed_repository.owner,
                                self.tool_shed_repository.name,
                                self.tool_shed_repository.installed_changeset_revision)

    @property
    def is_installed(self):
        return self.status == self.installation_status.INSTALLED


class ToolVersion(Dictifiable):
    dict_element_visible_keys = ['id', 'tool_shed_repository']

    def __init__(self, id=None, create_time=None, tool_id=None, tool_shed_repository=None):
        self.id = id
        self.create_time = create_time
        self.tool_id = tool_id
        self.tool_shed_repository = tool_shed_repository

    def to_dict(self, view='element'):
        rval = super(ToolVersion, self).to_dict(view=view)
        rval['tool_name'] = self.tool_id
        for a in self.parent_tool_association:
            rval['parent_tool_id'] = a.parent_id
        for a in self.child_tool_association:
            rval['child_tool_id'] = a.tool_id
        return rval


class ToolVersionAssociation(object):

    def __init__(self, id=None, tool_id=None, parent_id=None):
        self.id = id
        self.tool_id = tool_id
        self.parent_id = parent_id


class MigrateTools(object):

    def __init__(self, repository_id=None, repository_path=None, version=None):
        self.repository_id = repository_id
        self.repository_path = repository_path
        self.version = version
