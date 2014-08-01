import logging
import os
import threading

from galaxy import util

from tool_shed.util import common_util
from tool_shed.util import container_util
from tool_shed.util import readme_util

from tool_shed.utility_containers import utility_container_manager

log = logging.getLogger( __name__ )


class FailedTest( object ):
    """Failed tool tests object"""

    def __init__( self, id=None, stderr=None, test_id=None, tool_id=None, tool_version=None, traceback=None ):
        self.id = id
        self.stderr = stderr
        self.test_id = test_id
        self.tool_id = tool_id
        self.tool_version = tool_version
        self.traceback = traceback


class InvalidRepositoryDependency( object ):
    """Invalid repository dependency definition object"""

    def __init__( self, id=None, toolshed=None, repository_name=None, repository_owner=None, changeset_revision=None,
                  prior_installation_required=False, only_if_compiling_contained_td=False, error=None ):
        self.id = id
        self.toolshed = toolshed
        self.repository_name = repository_name
        self.repository_owner = repository_owner
        self.changeset_revision = changeset_revision
        self.prior_installation_required = prior_installation_required
        self.only_if_compiling_contained_td = only_if_compiling_contained_td
        self.error = error


class InvalidToolDependency( object ):
    """Invalid tool dependency definition object"""

    def __init__( self, id=None, name=None, version=None, type=None, error=None ):
        self.id = id
        self.name = name
        self.version = version
        self.type = type
        self.error = error


class MissingTestComponent( object ):
    """Missing tool test components object"""

    def __init__( self, id=None, missing_components=None, tool_guid=None, tool_id=None, tool_version=None ):
        self.id = id
        self.missing_components = missing_components
        self.tool_guid = tool_guid
        self.tool_id = tool_id
        self.tool_version = tool_version


class NotTested( object ):
    """NotTested object"""

    def __init__( self, id=None, reason=None ):
        self.id = id
        self.reason = reason


class PassedTest( object ):
    """Passed tool tests object"""

    def __init__( self, id=None, test_id=None, tool_id=None, tool_version=None ):
        self.id = id
        self.test_id = test_id
        self.tool_id = tool_id
        self.tool_version = tool_version


class RepositoryInstallationError( object ):
    """Repository installation error object"""

    def __init__( self, id=None, tool_shed=None, name=None, owner=None, changeset_revision=None, error_message=None ):
        self.id = id
        self.tool_shed = tool_shed
        self.name = name
        self.owner = owner
        self.changeset_revision = changeset_revision
        self.error_message = error_message


class RepositorySuccessfulInstallation( object ):
    """Repository installation object"""

    def __init__( self, id=None, tool_shed=None, name=None, owner=None, changeset_revision=None ):
        self.id = id
        self.tool_shed = tool_shed
        self.name = name
        self.owner = owner
        self.changeset_revision = changeset_revision


class TestEnvironment( object ):
    """Tool test environment object"""

    def __init__( self, id=None, architecture=None, galaxy_database_version=None, galaxy_revision=None, python_version=None, system=None, time_tested=None,
                  tool_shed_database_version=None, tool_shed_mercurial_version=None, tool_shed_revision=None ):
        self.id = id
        self.architecture = architecture
        self.galaxy_database_version = galaxy_database_version
        self.galaxy_revision = galaxy_revision
        self.python_version = python_version
        self.system = system
        self.time_tested = time_tested
        self.tool_shed_database_version = tool_shed_database_version
        self.tool_shed_mercurial_version = tool_shed_mercurial_version
        self.tool_shed_revision = tool_shed_revision


class ToolDependencyInstallationError( object ):
    """Tool dependency installation error object"""

    def __init__( self, id=None, type=None, name=None, version=None, error_message=None ):
        self.id = id
        self.type = type
        self.name = name
        self.version = version
        self.error_message = error_message


class ToolDependencySuccessfulInstallation( object ):
    """Tool dependency installation object"""

    def __init__( self, id=None, type=None, name=None, version=None, installation_directory=None ):
        self.id = id
        self.type = type
        self.name = name
        self.version = version
        self.installation_directory = installation_directory


class ToolShedUtilityContainerManager( utility_container_manager.UtilityContainerManager ):

    def __init__( self, app ):
        self.app = app

    def build_invalid_repository_dependencies_root_folder( self, folder_id, invalid_repository_dependencies_dict ):
        """Return a folder hierarchy containing invalid repository dependencies."""
        label = 'Invalid repository dependencies'
        if invalid_repository_dependencies_dict:
            invalid_repository_dependency_id = 0
            folder_id += 1
            invalid_repository_dependencies_root_folder = \
                utility_container_manager.Folder( id=folder_id,
                                                  key='root',
                                                  label='root',
                                                  parent=None )
            folder_id += 1
            invalid_repository_dependencies_folder = \
                utility_container_manager.Folder( id=folder_id,
                                                  key='invalid_repository_dependencies',
                                                  label=label,
                                                  parent=invalid_repository_dependencies_root_folder )
            invalid_repository_dependencies_root_folder.folders.append( invalid_repository_dependencies_folder )
            invalid_repository_dependencies = invalid_repository_dependencies_dict[ 'repository_dependencies' ]
            for invalid_repository_dependency in invalid_repository_dependencies:
                folder_id += 1
                invalid_repository_dependency_id += 1
                toolshed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td, error = \
                    common_util.parse_repository_dependency_tuple( invalid_repository_dependency, contains_error=True )
                key = container_util.generate_repository_dependencies_key_for_repository( toolshed,
                                                                                          name,
                                                                                          owner,
                                                                                          changeset_revision,
                                                                                          prior_installation_required,
                                                                                          only_if_compiling_contained_td )
                label = "Repository <b>%s</b> revision <b>%s</b> owned by <b>%s</b>" % ( name, changeset_revision, owner )
                folder = utility_container_manager.Folder( id=folder_id,
                                                           key=key,
                                                           label=label,
                                                           parent=invalid_repository_dependencies_folder )
                ird = InvalidRepositoryDependency( id=invalid_repository_dependency_id,
                                                   toolshed=toolshed,
                                                   repository_name=name,
                                                   repository_owner=owner,
                                                   changeset_revision=changeset_revision,
                                                   prior_installation_required=util.asbool( prior_installation_required ),
                                                   only_if_compiling_contained_td=util.asbool( only_if_compiling_contained_td ),
                                                   error=error )
                folder.invalid_repository_dependencies.append( ird )
                invalid_repository_dependencies_folder.folders.append( folder )
        else:
            invalid_repository_dependencies_root_folder = None
        return folder_id, invalid_repository_dependencies_root_folder

    def build_invalid_tool_dependencies_root_folder( self, folder_id, invalid_tool_dependencies_dict ):
        """Return a folder hierarchy containing invalid tool dependencies."""
        # # INvalid tool dependencies are always packages like:
        # {"R/2.15.1": {"name": "R", "readme": "some string", "type": "package", "version": "2.15.1" "error" : "some sting" }
        label = 'Invalid tool dependencies'
        if invalid_tool_dependencies_dict:
            invalid_tool_dependency_id = 0
            folder_id += 1
            invalid_tool_dependencies_root_folder = \
                utility_container_manager.Folder( id=folder_id, key='root', label='root', parent=None )
            folder_id += 1
            invalid_tool_dependencies_folder = \
                utility_container_manager.Folder( id=folder_id,
                                                  key='invalid_tool_dependencies',
                                                  label=label,
                                                  parent=invalid_tool_dependencies_root_folder )
            invalid_tool_dependencies_root_folder.folders.append( invalid_tool_dependencies_folder )
            for td_key, requirements_dict in invalid_tool_dependencies_dict.items():
                folder_id += 1
                invalid_tool_dependency_id += 1
                try:
                    name = requirements_dict[ 'name' ]
                    type = requirements_dict[ 'type' ]
                    version = requirements_dict[ 'version' ]
                    error = requirements_dict[ 'error' ]
                except Exception, e:
                    name = 'unknown'
                    type = 'unknown'
                    version = 'unknown'
                    error = str( e )
                key = self.generate_tool_dependencies_key( name, version, type )
                label = "Version <b>%s</b> of the <b>%s</b> <b>%s</b>" % ( version, name, type )
                folder = utility_container_manager.Folder( id=folder_id,
                                                           key=key,
                                                           label=label,
                                                           parent=invalid_tool_dependencies_folder )
                itd = InvalidToolDependency( id=invalid_tool_dependency_id,
                                             name=name,
                                             version=version,
                                             type=type,
                                             error=error )
                folder.invalid_tool_dependencies.append( itd )
                invalid_tool_dependencies_folder.folders.append( folder )
        else:
            invalid_tool_dependencies_root_folder = None
        return folder_id, invalid_tool_dependencies_root_folder

    def build_repository_containers( self, repository, changeset_revision, repository_dependencies, repository_metadata,
                                     exclude=None ):
        """
        Return a dictionary of containers for the received repository's dependencies and
        contents for display in the Tool Shed.
        """
        if exclude is None:
            exclude = []
        containers_dict = dict( datatypes=None,
                                invalid_tools=None,
                                readme_files=None,
                                repository_dependencies=None,
                                tool_dependencies=None,
                                valid_tools=None,
                                workflows=None,
                                valid_data_managers=None
                                 )
        if repository_metadata:
            metadata = repository_metadata.metadata
            lock = threading.Lock()
            lock.acquire( True )
            try:
                folder_id = 0
                # Datatypes container.
                if metadata:
                    if 'datatypes' not in exclude and 'datatypes' in metadata:
                        datatypes = metadata[ 'datatypes' ]
                        folder_id, datatypes_root_folder = self.build_datatypes_folder( folder_id, datatypes )
                        containers_dict[ 'datatypes' ] = datatypes_root_folder
                # Invalid repository dependencies container.
                if metadata:
                    if 'invalid_repository_dependencies' not in exclude and 'invalid_repository_dependencies' in metadata:
                        invalid_repository_dependencies = metadata[ 'invalid_repository_dependencies' ]
                        folder_id, invalid_repository_dependencies_root_folder = \
                            self.build_invalid_repository_dependencies_root_folder( folder_id,
                                                                                    invalid_repository_dependencies )
                        containers_dict[ 'invalid_repository_dependencies' ] = invalid_repository_dependencies_root_folder
                # Invalid tool dependencies container.
                if metadata:
                    if 'invalid_tool_dependencies' not in exclude and 'invalid_tool_dependencies' in metadata:
                        invalid_tool_dependencies = metadata[ 'invalid_tool_dependencies' ]
                        folder_id, invalid_tool_dependencies_root_folder = \
                            self.build_invalid_tool_dependencies_root_folder( folder_id,
                                                                              invalid_tool_dependencies )
                        containers_dict[ 'invalid_tool_dependencies' ] = invalid_tool_dependencies_root_folder
                # Invalid tools container.
                if metadata:
                    if 'invalid_tools' not in exclude and 'invalid_tools' in metadata:
                        invalid_tool_configs = metadata[ 'invalid_tools' ]
                        folder_id, invalid_tools_root_folder = \
                            self.build_invalid_tools_folder( folder_id,
                                                             invalid_tool_configs,
                                                             changeset_revision,
                                                             repository=repository,
                                                             label='Invalid tools' )
                        containers_dict[ 'invalid_tools' ] = invalid_tools_root_folder
                # Readme files container.
                if metadata:
                    if 'readme_files' not in exclude and 'readme_files' in metadata:
                        readme_files_dict = readme_util.build_readme_files_dict( self.app, repository, changeset_revision, metadata )
                        folder_id, readme_files_root_folder = self.build_readme_files_folder( folder_id, readme_files_dict )
                        containers_dict[ 'readme_files' ] = readme_files_root_folder
                if 'repository_dependencies' not in exclude:
                    # Repository dependencies container.
                    folder_id, repository_dependencies_root_folder = \
                        self.build_repository_dependencies_folder( folder_id=folder_id,
                                                                   repository_dependencies=repository_dependencies,
                                                                   label='Repository dependencies',
                                                                   installed=False )
                    if repository_dependencies_root_folder:
                        containers_dict[ 'repository_dependencies' ] = repository_dependencies_root_folder
                # Tool dependencies container.
                if metadata:
                    if 'tool_dependencies' not in exclude and 'tool_dependencies' in metadata:
                        tool_dependencies = metadata[ 'tool_dependencies' ]
                        if 'orphan_tool_dependencies' in metadata:
                            # The use of the orphan_tool_dependencies category in metadata has been deprecated,
                            # but we still need to check in case the metadata is out of date.
                            orphan_tool_dependencies = metadata[ 'orphan_tool_dependencies' ]
                            tool_dependencies.update( orphan_tool_dependencies )
                        # Tool dependencies can be categorized as orphans only if the repository contains tools.
                        if 'tools' not in exclude:
                            tools = metadata.get( 'tools', [] )
                            tools.extend( metadata.get( 'invalid_tools', [] ) )
                        folder_id, tool_dependencies_root_folder = \
                            self.build_tool_dependencies_folder( folder_id,
                                                                 tool_dependencies,
                                                                 missing=False,
                                                                 new_install=False )
                        containers_dict[ 'tool_dependencies' ] = tool_dependencies_root_folder
                # Valid tools container.
                if metadata:
                    if 'tools' not in exclude and 'tools' in metadata:
                        valid_tools = metadata[ 'tools' ]
                        folder_id, valid_tools_root_folder = self.build_tools_folder( folder_id,
                                                                                      valid_tools,
                                                                                      repository,
                                                                                      changeset_revision,
                                                                                      label='Valid tools' )
                        containers_dict[ 'valid_tools' ] = valid_tools_root_folder
                # Tool test results container.
                tool_test_results = util.listify( repository_metadata.tool_test_results )
                # Only create and populate this folder if there are actual tool test results to display.
                if self.can_display_tool_test_results( tool_test_results, exclude=exclude ):
                    folder_id, tool_test_results_root_folder = \
                        self.build_tool_test_results_folder( folder_id,
                                                             tool_test_results,
                                                             label='Tool test results' )
                    containers_dict[ 'tool_test_results' ] = tool_test_results_root_folder
                # Workflows container.
                if metadata:
                    if 'workflows' not in exclude and 'workflows' in metadata:
                        workflows = metadata[ 'workflows' ]
                        folder_id, workflows_root_folder = \
                            self.build_workflows_folder( folder_id=folder_id,
                                                         workflows=workflows,
                                                         repository_metadata_id=repository_metadata.id,
                                                         repository_id=None,
                                                         label='Workflows' )
                        containers_dict[ 'workflows' ] = workflows_root_folder
                # Valid Data Managers container
                if metadata:
                    if 'data_manager' not in exclude and 'data_manager' in metadata:
                        data_managers = metadata['data_manager'].get( 'data_managers', None )
                        folder_id, data_managers_root_folder = \
                            self.build_data_managers_folder( folder_id, data_managers, label="Data Managers" )
                        containers_dict[ 'valid_data_managers' ] = data_managers_root_folder
                        error_messages = metadata['data_manager'].get( 'error_messages', None )
                        data_managers = metadata['data_manager'].get( 'invalid_data_managers', None )
                        folder_id, data_managers_root_folder = \
                            self.build_invalid_data_managers_folder( folder_id,
                                                                     data_managers,
                                                                     error_messages,
                                                                     label="Invalid Data Managers" )
                        containers_dict[ 'invalid_data_managers' ] = data_managers_root_folder
            except Exception, e:
                log.exception( "Exception in build_repository_containers: %s" % str( e ) )
            finally:
                lock.release()
        return containers_dict

    def build_tool_test_results_folder( self, folder_id, tool_test_results_dicts, label='Tool test results' ):
        """Return a folder hierarchy containing tool dependencies."""
        # This container is displayed only in the tool shed.
        if tool_test_results_dicts:
            folder_id += 1
            tool_test_results_root_folder = utility_container_manager.Folder( id=folder_id, key='root', label='root', parent=None )
            multiple_tool_test_results_dicts = len( tool_test_results_dicts ) > 1
            if multiple_tool_test_results_dicts:
                folder_id += 1
                test_runs_folder = utility_container_manager.Folder( id=folder_id,
                                                                     key='test_runs',
                                                                     label='Test runs',
                                                                     parent=tool_test_results_root_folder )
                tool_test_results_root_folder.folders.append( test_runs_folder )
            for index, tool_test_results_dict in enumerate( tool_test_results_dicts ):
                if len( tool_test_results_dict ) < 2:
                    # Skip tool test results that have only a 'test_environment' entry since this implies that only the preparation
                    # script check_repositories_for_functional_tests.py has run for that entry.
                    continue
                # We have a dictionary that looks something like this:
                # {
                #  'missing_test_components': [], 
                #  'failed_tests': [], 
                #  'passed_tests': 
                #        [{'tool_id': 'effectiveT3', 
                #          'test_id': 'test_tool_000000 (functional.test_toolbox.TestForTool_testtoolshed.g2.bx.psu.edu/repos/...)', 
                #          'tool_version': '0.0.12'}, 
                #         {'tool_id': 'effectiveT3', 
                #          'test_id': 'test_tool_000001 (functional.test_toolbox.TestForTool_testtoolshed.g2.bx.psu.edu/repos/...)', 
                #          'tool_version': '0.0.12'}], 
                # 'test_environment': 
                #    {'python_version': '2.7.4', 'tool_shed_mercurial_version': '2.2.3', 'system': 'Linux 3.8.0-30-generic', 
                #     'tool_shed_database_version': 21, 'architecture': 'x86_64', 'galaxy_revision': '11573:a62c54ddbe2a', 
                #     'galaxy_database_version': 117, 'time_tested': '2013-12-03 09:11:48', 'tool_shed_revision': '11556:228156daa575'}, 
                # 'installation_errors': {'current_repository': [], 'repository_dependencies': [], 'tool_dependencies': []},
                # 'successful_installations': {'current_repository': [], 'repository_dependencies': [], 'tool_dependencies': []}
                # }
                test_environment_dict = tool_test_results_dict.get( 'test_environment', None )
                if test_environment_dict is None:
                    # The test environment entry will exist only if the preparation script check_repositories_for_functional_tests.py
                    # was executed prior to the ~/install_and_test_repositories/functional_tests.py script.  If that did not occur,
                    # we'll display test result, but the test_environment entries will not be complete.
                    test_environment_dict = {}
                time_tested = test_environment_dict.get( 'time_tested', 'unknown_%d' % index )
                if multiple_tool_test_results_dicts:
                    folder_id += 1
                    containing_folder = utility_container_manager.Folder( id=folder_id,
                                                                          key='test_results',
                                                                          label=time_tested,
                                                                          parent=test_runs_folder )
                    test_runs_folder.folders.append( containing_folder )
                else:
                    containing_folder = tool_test_results_root_folder
                folder_id += 1
                test_environment_folder = utility_container_manager.Folder( id=folder_id,
                                                                            key='test_environment',
                                                                            label='Automated test environment',
                                                                            parent=containing_folder )
                containing_folder.folders.append( test_environment_folder )
                try:
                    architecture = test_environment_dict.get( 'architecture', '' )
                    galaxy_database_version = test_environment_dict.get( 'galaxy_database_version', '' )
                    galaxy_revision = test_environment_dict.get( 'galaxy_revision', '' )
                    python_version = test_environment_dict.get( 'python_version', '' )
                    system = test_environment_dict.get( 'system', '' )
                    tool_shed_database_version = test_environment_dict.get( 'tool_shed_database_version', '' )
                    tool_shed_mercurial_version = test_environment_dict.get( 'tool_shed_mercurial_version', '' )
                    tool_shed_revision = test_environment_dict.get( 'tool_shed_revision', '' )
                except Exception, e:
                    architecture = str( e )
                    galaxy_database_version = ''
                    galaxy_revision = ''
                    python_version = ''
                    system = ''
                    tool_shed_database_version = ''
                    tool_shed_mercurial_version = ''
                    tool_shed_revision = ''
                test_environment = TestEnvironment( id=1,
                                                    architecture=architecture,
                                                    galaxy_database_version=galaxy_database_version,
                                                    galaxy_revision=galaxy_revision,
                                                    python_version=python_version,
                                                    system=system,
                                                    time_tested=time_tested,
                                                    tool_shed_database_version=tool_shed_database_version,
                                                    tool_shed_mercurial_version=tool_shed_mercurial_version,
                                                    tool_shed_revision=tool_shed_revision )
                test_environment_folder.test_environments.append( test_environment )
                not_tested_dict = tool_test_results_dict.get( 'not_tested', {} )
                if len( not_tested_dict ) > 0:
                    folder_id += 1
                    not_tested_folder = utility_container_manager.Folder( id=folder_id,
                                                                          key='not_tested',
                                                                          label='Not tested',
                                                                          parent=containing_folder )
                    containing_folder.folders.append( not_tested_folder )
                    not_tested_id = 0
                    try:
                        reason = not_tested_dict.get( 'reason', '' )
                    except Exception, e:
                        reason = str( e )
                    not_tested = NotTested( id=not_tested_id, reason=reason )
                    not_tested_folder.not_tested.append( not_tested )
                passed_tests_dicts = tool_test_results_dict.get( 'passed_tests', [] )
                if len( passed_tests_dicts ) > 0:
                    folder_id += 1
                    passed_tests_folder = utility_container_manager.Folder( id=folder_id,
                                                                            key='passed_tests',
                                                                            label='Tests that passed successfully',
                                                                            parent=containing_folder )
                    containing_folder.folders.append( passed_tests_folder )
                    passed_test_id = 0
                    for passed_tests_dict in passed_tests_dicts:
                        passed_test_id += 1
                        try:
                            test_id = passed_tests_dict.get( 'test_id' '' )
                            tool_id = passed_tests_dict.get( 'tool_id', '' )
                            tool_version = passed_tests_dict.get( 'tool_version', '' )
                        except Exception, e:
                            test_id = str( e )
                            tool_id = 'unknown'
                            tool_version = 'unknown'
                        passed_test = PassedTest( id=passed_test_id,
                                                  test_id=test_id,
                                                  tool_id=tool_id,
                                                  tool_version=tool_version )
                        passed_tests_folder.passed_tests.append( passed_test )
                failed_tests_dicts = tool_test_results_dict.get( 'failed_tests', [] )
                if len( failed_tests_dicts ) > 0:
                    folder_id += 1
                    failed_tests_folder = utility_container_manager.Folder( id=folder_id,
                                                                            key='failed_tests',
                                                                            label='Tests that failed',
                                                                            parent=containing_folder )
                    containing_folder.folders.append( failed_tests_folder )
                    failed_test_id = 0
                    for failed_tests_dict in failed_tests_dicts:
                        failed_test_id += 1
                        try:
                            stderr = failed_tests_dict.get( 'stderr', '' )
                            test_id = failed_tests_dict.get( 'test_id', '' )
                            tool_id = failed_tests_dict.get( 'tool_id', '' )
                            tool_version = failed_tests_dict.get( 'tool_version', '' )
                            traceback = failed_tests_dict.get( 'traceback', '' )
                        except Exception, e:
                            stderr = 'unknown'
                            test_id = 'unknown'
                            tool_id = 'unknown'
                            tool_version = 'unknown'
                            traceback = str( e )
                        failed_test = FailedTest( id=failed_test_id,
                                                  stderr=stderr,
                                                  test_id=test_id,
                                                  tool_id=tool_id,
                                                  tool_version=tool_version,
                                                  traceback=traceback )
                        failed_tests_folder.failed_tests.append( failed_test )
                missing_test_components_dicts = tool_test_results_dict.get( 'missing_test_components', [] )
                if len( missing_test_components_dicts ) > 0:
                    folder_id += 1
                    missing_test_components_folder = \
                        utility_container_manager.Folder( id=folder_id,
                                                          key='missing_test_components',
                                                          label='Tools missing tests or test data',
                                                          parent=containing_folder )
                    containing_folder.folders.append( missing_test_components_folder )
                    missing_test_component_id = 0
                    for missing_test_components_dict in missing_test_components_dicts:
                        missing_test_component_id += 1
                        try:
                           missing_components = missing_test_components_dict.get( 'missing_components', '' )
                           tool_guid = missing_test_components_dict.get( 'tool_guid', '' )
                           tool_id = missing_test_components_dict.get( 'tool_id', '' )
                           tool_version = missing_test_components_dict.get( 'tool_version', '' )
                        except Exception, e:
                            missing_components = str( e )
                            tool_guid = 'unknown'
                            tool_id = 'unknown'
                            tool_version = 'unknown'
                        missing_test_component = MissingTestComponent( id=missing_test_component_id,
                                                                       missing_components=missing_components,
                                                                       tool_guid=tool_guid,
                                                                       tool_id=tool_id,
                                                                       tool_version=tool_version )
                        missing_test_components_folder.missing_test_components.append( missing_test_component )
                installation_error_dict = tool_test_results_dict.get( 'installation_errors', {} )
                if len( installation_error_dict ) > 0:
                    # 'installation_errors':
                    #    {'current_repository': [], 
                    #     'repository_dependencies': [], 
                    #     'tool_dependencies': 
                    #        [{'error_message': 'some traceback string' 'type': 'package', 'name': 'MIRA', 'version': '4.0'}]
                    #    }
                    current_repository_installation_error_dicts = installation_error_dict.get( 'current_repository', [] )
                    repository_dependency_installation_error_dicts = installation_error_dict.get( 'repository_dependencies', [] )
                    tool_dependency_installation_error_dicts = installation_error_dict.get( 'tool_dependencies', [] )
                    if len( current_repository_installation_error_dicts ) > 0 or \
                        len( repository_dependency_installation_error_dicts ) > 0 or \
                        len( tool_dependency_installation_error_dicts ) > 0:
                        repository_installation_error_id = 0
                        folder_id += 1
                        installation_error_base_folder = utility_container_manager.Folder( id=folder_id,
                                                                                           key='installation_errors',
                                                                                           label='Installation errors',
                                                                                           parent=containing_folder )
                        containing_folder.folders.append( installation_error_base_folder )
                        if len( current_repository_installation_error_dicts ) > 0:
                            folder_id += 1
                            current_repository_folder = \
                                utility_container_manager.Folder( id=folder_id,
                                                                  key='current_repository_installation_errors',
                                                                  label='This repository',
                                                                  parent=installation_error_base_folder )
                            installation_error_base_folder.folders.append( current_repository_folder )
                            for current_repository_error_dict in current_repository_installation_error_dicts:
                                repository_installation_error_id += 1
                                try:
                                    r_tool_shed = str( current_repository_error_dict.get( 'tool_shed', '' ) )
                                    r_name = str( current_repository_error_dict.get( 'name', '' ) )
                                    r_owner = str( current_repository_error_dict.get( 'owner', '' ) )
                                    r_changeset_revision = str( current_repository_error_dict.get( 'changeset_revision', '' ) )
                                    r_error_message = current_repository_error_dict.get( 'error_message', '' )
                                except Exception, e:
                                    r_tool_shed = 'unknown'
                                    r_name = 'unknown'
                                    r_owner = 'unknown'
                                    r_changeset_revision = 'unknown'
                                    r_error_message = str( e )
                                repository_installation_error = RepositoryInstallationError( id=repository_installation_error_id,
                                                                                             tool_shed=r_tool_shed,
                                                                                             name=r_name,
                                                                                             owner=r_owner,
                                                                                             changeset_revision=r_changeset_revision,
                                                                                             error_message=r_error_message )
                                current_repository_folder.current_repository_installation_errors.append( repository_installation_error )
                        if len( repository_dependency_installation_error_dicts ) > 0:
                            folder_id += 1
                            repository_dependencies_folder = \
                                utility_container_manager.Folder( id=folder_id,
                                                                  key='repository_dependency_installation_errors',
                                                                  label='Repository dependencies',
                                                                  parent=installation_error_base_folder )
                            installation_error_base_folder.folders.append( repository_dependencies_folder )
                            for repository_dependency_error_dict in repository_dependency_installation_error_dicts:
                                repository_installation_error_id += 1
                                try:
                                    rd_tool_shed = str( repository_dependency_error_dict.get( 'tool_shed', '' ) )
                                    rd_name = str( repository_dependency_error_dict.get( 'name', '' ) )
                                    rd_owner = str( repository_dependency_error_dict.get( 'owner', '' ) )
                                    rd_changeset_revision = str( repository_dependency_error_dict.get( 'changeset_revision', '' ) )
                                    rd_error_message = repository_dependency_error_dict.get( 'error_message', '' )
                                except Exception, e:
                                    rd_tool_shed = 'unknown'
                                    rd_name = 'unknown'
                                    rd_owner = 'unknown'
                                    rd_changeset_revision = 'unknown'
                                    rd_error_message = str( e )
                                repository_installation_error = RepositoryInstallationError( id=repository_installation_error_id,
                                                                                             tool_shed=rd_tool_shed,
                                                                                             name=rd_name,
                                                                                             owner=rd_owner,
                                                                                             changeset_revision=rd_changeset_revision,
                                                                                             error_message=rd_error_message )
                                repository_dependencies_folder.repository_installation_errors.append( repository_installation_error )
                        if len( tool_dependency_installation_error_dicts ) > 0:
                            # [{'error_message': 'some traceback string' 'type': 'package', 'name': 'MIRA', 'version': '4.0'}]
                            folder_id += 1
                            tool_dependencies_folder = \
                                utility_container_manager.Folder( id=folder_id,
                                                                  key='tool_dependency_installation_errors',
                                                                  label='Tool dependencies',
                                                                  parent=installation_error_base_folder )
                            installation_error_base_folder.folders.append( tool_dependencies_folder )
                            tool_dependency_error_id = 0
                            for tool_dependency_error_dict in tool_dependency_installation_error_dicts:
                                tool_dependency_error_id += 1
                                try:
                                    td_type = str( tool_dependency_error_dict.get( 'type', '' ) )
                                    td_name = str( tool_dependency_error_dict.get( 'name', '' ) )
                                    td_version = str( tool_dependency_error_dict.get( 'version', '' ) )
                                    td_error_message = tool_dependency_error_dict.get( 'error_message', '' )
                                except Exception, e:
                                    td_type = 'unknown'
                                    td_name = 'unknown'
                                    td_version = 'unknown'
                                    td_error_message = str( e )
                                tool_dependency_installation_error = ToolDependencyInstallationError( id=tool_dependency_error_id,
                                                                                                      type=td_type,
                                                                                                      name=td_name,
                                                                                                      version=td_version,
                                                                                                      error_message=td_error_message )
                                tool_dependencies_folder.tool_dependency_installation_errors.append( tool_dependency_installation_error )
                successful_installation_dict = tool_test_results_dict.get( 'successful_installations', {} )
                if len( successful_installation_dict ) > 0:
                    # 'successful_installation':
                    #    {'current_repository': [], 
                    #     'repository_dependencies': [], 
                    #     'tool_dependencies': 
                    #        [{'installation_directory': 'some path' 'type': 'package', 'name': 'MIRA', 'version': '4.0'}]
                    #    }
                    # We won't display the current repository in this container.  I fit is not displaying installation errors,
                    # then it must be a successful installation.
                    repository_dependency_successful_installation_dicts = successful_installation_dict.get( 'repository_dependencies', [] )
                    tool_dependency_successful_installation_dicts = successful_installation_dict.get( 'tool_dependencies', [] )
                    if len( repository_dependency_successful_installation_dicts ) > 0 or \
                        len( tool_dependency_successful_installation_dicts ) > 0:
                        repository_installation_success_id = 0
                        folder_id += 1
                        successful_installation_base_folder = \
                            utility_container_manager.Folder( id=folder_id,
                                                              key='successful_installations',
                                                              label='Successful installations',
                                                              parent=containing_folder )
                        containing_folder.folders.append( successful_installation_base_folder )
                        # Displaying the successful installation of the current repository is not really necessary, so we'll skip it.
                        if len( repository_dependency_successful_installation_dicts ) > 0:
                            folder_id += 1
                            repository_dependencies_folder = \
                                utility_container_manager.Folder( id=folder_id,
                                                                  key='repository_dependency_successful_installations',
                                                                  label='Repository dependencies',
                                                                  parent=successful_installation_base_folder )
                            successful_installation_base_folder.folders.append( repository_dependencies_folder )
                            for repository_dependency_successful_installation_dict in repository_dependency_successful_installation_dicts:
                                repository_installation_success_id += 1
                                try:
                                    rd_tool_shed = str( repository_dependency_successful_installation_dict.get( 'tool_shed', '' ) )
                                    rd_name = str( repository_dependency_successful_installation_dict.get( 'name', '' ) )
                                    rd_owner = str( repository_dependency_successful_installation_dict.get( 'owner', '' ) )
                                    rd_changeset_revision = \
                                        str( repository_dependency_successful_installation_dict.get( 'changeset_revision', '' ) )
                                except Exception, e:
                                    rd_tool_shed = 'unknown'
                                    rd_name = 'unknown'
                                    rd_owner = 'unknown'
                                    rd_changeset_revision = 'unknown'
                                repository_installation_success = \
                                    RepositorySuccessfulInstallation( id=repository_installation_success_id,
                                                                      tool_shed=rd_tool_shed,
                                                                      name=rd_name,
                                                                      owner=rd_owner,
                                                                      changeset_revision=rd_changeset_revision )
                                repository_dependencies_folder.repository_successful_installations.append( repository_installation_success )
                        if len( tool_dependency_successful_installation_dicts ) > 0:
                            # [{'installation_directory': 'some path' 'type': 'package', 'name': 'MIRA', 'version': '4.0'}]
                            folder_id += 1
                            tool_dependencies_folder = \
                                utility_container_manager.Folder( id=folder_id,
                                                                  key='tool_dependency_successful_installations',
                                                                  label='Tool dependencies',
                                                                  parent=successful_installation_base_folder )
                            successful_installation_base_folder.folders.append( tool_dependencies_folder )
                            tool_dependency_error_id = 0
                            for tool_dependency_successful_installation_dict in tool_dependency_successful_installation_dicts:
                                tool_dependency_error_id += 1
                                try:
                                    td_type = str( tool_dependency_successful_installation_dict.get( 'type', '' ) )
                                    td_name = str( tool_dependency_successful_installation_dict.get( 'name', '' ) )
                                    td_version = str( tool_dependency_successful_installation_dict.get( 'version', '' ) )
                                    td_installation_directory = tool_dependency_successful_installation_dict.get( 'installation_directory', '' )
                                except Exception, e:
                                    td_type = 'unknown'
                                    td_name = 'unknown'
                                    td_version = 'unknown'
                                    td_installation_directory = str( e )
                                tool_dependency_successful_installation = \
                                    ToolDependencySuccessfulInstallation( id=tool_dependency_error_id,
                                                                          type=td_type,
                                                                          name=td_name,
                                                                          version=td_version,
                                                                          installation_directory=td_installation_directory )
                                tool_dependencies_folder.tool_dependency_successful_installations.append( tool_dependency_successful_installation )
        else:
            tool_test_results_root_folder = None
        return folder_id, tool_test_results_root_folder

    def can_display_tool_test_results( self, tool_test_results_dicts, exclude=None ):
        # Only create and populate the tool_test_results container if there are actual tool test results to display.
        if exclude is None:
            exclude = []
        if 'tool_test_results' in exclude:
            return False
        for tool_test_results_dict in tool_test_results_dicts:
            # We check for more than a single entry in the tool_test_results dictionary because it may have
            # only the "test_environment" entry, but we want at least 1 of "passed_tests", "failed_tests",
            # "installation_errors", "missing_test_components" "skipped_tests", "not_tested" or any other
            # entry that may be added in the future.
            display_entries = [ 'failed_tests', 'installation_errors', 'missing_test_components',
                                'not_tested', 'passed_tests', 'skipped_tests' ]
            for k, v in tool_test_results_dict.items():
                if k in display_entries:
                    # We've discovered an entry that can be displayed, so see if it has a value since displaying
                    # empty lists is not desired.
                    if v:
                        return True
        return False

    def generate_tool_dependencies_key( self, name, version, type ):
        return '%s%s%s%s%s' % ( str( name ), container_util.STRSEP, str( version ), container_util.STRSEP, str( type ) )
