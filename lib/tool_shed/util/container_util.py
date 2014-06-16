import logging
import os
import threading
import galaxy.util
from galaxy.web.framework.helpers import time_ago
from tool_shed.util import common_util
from tool_shed.util import readme_util
import tool_shed.util.shed_util_common as suc

log = logging.getLogger( __name__ )

# String separator
STRSEP = '__ESEP__'


class Folder( object ):
    """Container object."""

    def __init__( self, id=None, key=None, label=None, parent=None ):
        self.id = id
        self.key = key
        self.label = label
        self.parent = parent
        self.current_repository_installation_errors = []
        self.current_repository_successful_installations = []
        self.description = None
        self.datatypes = []
        self.failed_tests = []
        self.folders = []
        self.invalid_data_managers = []
        self.invalid_repository_dependencies = []
        self.invalid_tool_dependencies = []
        self.invalid_tools = []
        self.missing_test_components = []
        self.not_tested = []
        self.passed_tests = []
        self.readme_files = []
        self.repository_dependencies = []
        self.repository_installation_errors = []
        self.repository_successful_installations = []
        self.test_environments = []
        self.tool_dependencies = []
        self.tool_dependency_installation_errors = []
        self.tool_dependency_successful_installations = []
        self.valid_tools = []
        self.valid_data_managers = []
        self.workflows = []

    def contains_folder( self, folder ):
        for index, contained_folder in enumerate( self.folders ):
            if folder == contained_folder:
                return index, contained_folder
        return 0, None

    def contains_repository_dependency( self, repository_dependency ):
        listified_repository_dependency = repository_dependency.listify
        for contained_repository_dependency in self.repository_dependencies:
            if contained_repository_dependency.listify == listified_repository_dependency:
                return True
        return False

    def remove_repository_dependency( self, repository_dependency ):
        listified_repository_dependency = repository_dependency.listify
        for contained_repository_dependency in self.repository_dependencies:
            if contained_repository_dependency.listify == listified_repository_dependency:
                self.repository_dependencies.remove( contained_repository_dependency )


class DataManager( object ):
    """Data Manager object"""

    def __init__( self, id=None, name=None, version=None, data_tables=None ):
        self.id = id
        self.name = name
        self.version = version
        self.data_tables = data_tables


class Datatype( object ):
    """Datatype object"""

    def __init__( self, id=None, extension=None, type=None, mimetype=None, subclass=None, converters=None, display_app_containers=None ):
        self.id = id
        self.extension = extension
        self.type = type
        self.mimetype = mimetype
        self.subclass = subclass
        self.converters = converters
        self.display_app_containers = display_app_containers


class FailedTest( object ):
    """Failed tool tests object"""

    def __init__( self, id=None, stderr=None, test_id=None, tool_id=None, tool_version=None, traceback=None ):
        self.id = id
        self.stderr = stderr
        self.test_id = test_id
        self.tool_id = tool_id
        self.tool_version = tool_version
        self.traceback = traceback


class InvalidDataManager( object ):
    """Invalid data Manager object"""

    def __init__( self, id=None, index=None, error=None ):
        self.id = id
        self.index = index
        self.error = error


class InvalidRepositoryDependency( object ):
    """Invalid repository dependency definition object"""

    def __init__( self, id=None, toolshed=None, repository_name=None, repository_owner=None, changeset_revision=None, prior_installation_required=False,
                  only_if_compiling_contained_td=False, error=None ):
        self.id = id
        self.toolshed = toolshed
        self.repository_name = repository_name
        self.repository_owner = repository_owner
        self.changeset_revision = changeset_revision
        self.prior_installation_required = prior_installation_required
        self.only_if_compiling_contained_td = only_if_compiling_contained_td
        self.error = error


class InvalidTool( object ):
    """Invalid tool object"""

    def __init__( self, id=None, tool_config=None, repository_id=None, changeset_revision=None, repository_installation_status=None ):
        self.id = id
        self.tool_config = tool_config
        self.repository_id = repository_id
        self.changeset_revision = changeset_revision
        self.repository_installation_status = repository_installation_status


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


class ReadMe( object ):
    """Readme text object"""

    def __init__( self, id=None, name=None, text=None ):
        self.id = id
        self.name = name
        self.text = text


class RepositoryDependency( object ):
    """Repository dependency object"""

    def __init__( self, id=None, toolshed=None, repository_name=None, repository_owner=None, changeset_revision=None, prior_installation_required=False,
                  only_if_compiling_contained_td=False, installation_status=None, tool_shed_repository_id=None ):
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
    def listify( self ):
        return [ self.toolshed,
                self.repository_name,
                self.repository_owner,
                self.changeset_revision,
                self.prior_installation_required,
                self.only_if_compiling_contained_td ]


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


class Tool( object ):
    """Tool object"""

    def __init__( self, id=None, tool_config=None, tool_id=None, name=None, description=None, version=None, requirements=None,
                  repository_id=None, changeset_revision=None, repository_installation_status=None ):
        self.id = id
        self.tool_config = tool_config
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.version = version
        self.requirements = requirements
        self.repository_id = repository_id
        self.changeset_revision = changeset_revision
        self.repository_installation_status = repository_installation_status


class ToolDependency( object ):
    """Tool dependency object"""

    def __init__( self, id=None, name=None, version=None, type=None, readme=None, installation_status=None, repository_id=None,
                  tool_dependency_id=None ):
        self.id = id
        self.name = name
        self.version = version
        self.type = type
        self.readme = readme
        self.installation_status = installation_status
        self.repository_id = repository_id
        self.tool_dependency_id = tool_dependency_id

    @property
    def listify( self ):
        return [ self.name, self.version, self.type ]


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

class Workflow( object ):
    """Workflow object."""

    def __init__( self, id=None, workflow_name=None, steps=None, format_version=None, annotation=None, repository_metadata_id=None, repository_id=None ):
        # When rendered in the tool shed, repository_metadata_id will have a value and repository_id will be None.  When rendered in Galaxy, repository_id
        # will have a value and repository_metadata_id will be None.
        self.id = id
        self.workflow_name = workflow_name
        self.steps = steps
        self.format_version = format_version
        self.annotation = annotation
        self.repository_metadata_id = repository_metadata_id
        self.repository_id = repository_id

def build_data_managers_folder( app, folder_id, data_managers, label=None ):
    """Return a folder hierarchy containing Data Managers."""
    if data_managers:
        if label is None:
            label = "Data Managers"
        data_manager_id = 0
        folder_id += 1
        data_managers_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        key = "valid_data_managers"
        folder = Folder( id=folder_id, key=key, label=label, parent=data_managers_root_folder )
        data_managers_root_folder.folders.append( folder )
        # Insert a header row.
        data_manager_id += 1
        data_manager = DataManager( id=data_manager_id,
                                    name='Name',
                                    version='Version',
                                    data_tables='Data Tables' )
        folder.valid_data_managers.append( data_manager )
        for data_manager_dict in data_managers.itervalues():
            data_manager_id += 1
            try:
                name = data_manager_dict.get( 'name', '' )
                version = data_manager_dict.get( 'version', '' )
                data_tables = ", ".join( data_manager_dict.get( 'data_tables', '' ) )
            except Exception, e:
                name = str( e )
                version = 'unknown'
                data_tables = 'unknown'
            data_manager = DataManager( id=data_manager_id,
                                        name=name,
                                        version=version,
                                        data_tables=data_tables )
            folder.valid_data_managers.append( data_manager )
    else:
        data_managers_root_folder = None
    return folder_id, data_managers_root_folder

def build_datatypes_folder( app, folder_id, datatypes, label='Datatypes' ):
    """Return a folder hierarchy containing datatypes."""
    if datatypes:
        datatype_id = 0
        folder_id += 1
        datatypes_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        folder = Folder( id=folder_id, key='datatypes', label=label, parent=datatypes_root_folder )
        datatypes_root_folder.folders.append( folder )
        # Insert a header row.
        datatype_id += 1
        datatype = Datatype( id=datatype_id,
                             extension='extension',
                             type='type',
                             mimetype='mimetype',
                             subclass='subclass' )
        folder.datatypes.append( datatype )
        for datatypes_dict in datatypes:
            # {"converters":
            #    [{"target_datatype": "gff",
            #      "tool_config": "bed_to_gff_converter.xml",
            #      "guid": "localhost:9009/repos/test/bed_to_gff_converter/CONVERTER_bed_to_gff_0/2.0.0"}],
            # "display_in_upload": "true",
            # "dtype": "galaxy.datatypes.interval:Bed",
            # "extension": "bed"}
            # TODO: converters and display_app information is not currently rendered.  Should it be?
            # Handle defined converters, if any.
            converters = datatypes_dict.get( 'converters', None )
            if converters:
                num_converters = len( converters )
            else:
                num_converters = 0
            # Handle defined display applications, if any.
            display_app_containers = datatypes_dict.get( 'display_app_containers', None )
            if display_app_containers:
                num_display_app_containers = len( display_app_containers )
            else:
                num_display_app_containers = 0
            datatype_id += 1
            try:
                extension = datatypes_dict.get( 'extension', '' )
                type = datatypes_dict.get( 'dtype', '' )
                mimetype = datatypes_dict.get( 'mimetype', '' )
                subclass = datatypes_dict.get( 'subclass', '' )
                converters = num_converters
                display_app_containers = num_display_app_containers
            except Exception, e:
                extension = str( e )
                type = 'unknown'
                mimetype = 'unknown'
                subclass = 'unknown'
                converters = 'unknown'
                display_app_containers = 'unknown'
            datatype = Datatype( id=datatype_id,
                                 extension=extension,
                                 type=type,
                                 mimetype=mimetype,
                                 subclass=subclass,
                                 converters=converters,
                                 display_app_containers=display_app_containers )
            folder.datatypes.append( datatype )
    else:
        datatypes_root_folder = None
    return folder_id, datatypes_root_folder

def build_invalid_data_managers_folder( app, folder_id, data_managers, error_messages=None, label=None ):
    """Return a folder hierarchy containing invalid Data Managers."""
    if data_managers or error_messages:
        if label is None:
            label = "Invalid Data Managers"
        data_manager_id = 0
        folder_id += 1
        data_managers_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        key = "invalid_data_managers"
        folder = Folder( id=folder_id, key=key, label=label, parent=data_managers_root_folder )
        data_managers_root_folder.folders.append( folder )
        # Insert a header row.
        data_manager_id += 1
        data_manager = InvalidDataManager( id=data_manager_id,
                                           index='Element Index',
                                           error='Error' )
        folder.invalid_data_managers.append( data_manager )
        if error_messages:
            for error_message in error_messages:
                data_manager_id += 1
                data_manager = InvalidDataManager( id=data_manager_id,
                                                   index=0,
                                                   error=error_message )
                folder.invalid_data_managers.append( data_manager )
                has_errors = True
        for data_manager_dict in data_managers:
            data_manager_id += 1
            data_manager = InvalidDataManager( id=data_manager_id,
                                               index=data_manager_dict.get( 'index', 0 ) + 1,
                                               error=data_manager_dict.get( 'error_message', '' ) )
            folder.invalid_data_managers.append( data_manager )
            has_errors = True
    else:
        data_managers_root_folder = None
    return folder_id, data_managers_root_folder

def build_invalid_repository_dependencies_root_folder( app, folder_id, invalid_repository_dependencies_dict ):
    """Return a folder hierarchy containing invalid repository dependencies."""
    label = 'Invalid repository dependencies'
    if invalid_repository_dependencies_dict:
        invalid_repository_dependency_id = 0
        folder_id += 1
        invalid_repository_dependencies_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        invalid_repository_dependencies_folder = Folder( id=folder_id,
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
            key = generate_repository_dependencies_key_for_repository( toolshed,
                                                                       name,
                                                                       owner,
                                                                       changeset_revision,
                                                                       prior_installation_required,
                                                                       only_if_compiling_contained_td )
            label = "Repository <b>%s</b> revision <b>%s</b> owned by <b>%s</b>" % ( name, changeset_revision, owner )
            folder = Folder( id=folder_id,
                             key=key,
                             label=label,
                             parent=invalid_repository_dependencies_folder )
            ird = InvalidRepositoryDependency( id=invalid_repository_dependency_id,
                                               toolshed=toolshed,
                                               repository_name=name,
                                               repository_owner=owner,
                                               changeset_revision=changeset_revision,
                                               prior_installation_required=galaxy.util.asbool( prior_installation_required ),
                                               only_if_compiling_contained_td=galaxy.util.asbool( only_if_compiling_contained_td ),
                                               error=error )
            folder.invalid_repository_dependencies.append( ird )
            invalid_repository_dependencies_folder.folders.append( folder )
    else:
        invalid_repository_dependencies_root_folder = None
    return folder_id, invalid_repository_dependencies_root_folder

def build_invalid_tool_dependencies_root_folder( app, folder_id, invalid_tool_dependencies_dict ):
    """Return a folder hierarchy containing invalid tool dependencies."""
    # # INvalid tool dependencies are always packages like:
    # {"R/2.15.1": {"name": "R", "readme": "some string", "type": "package", "version": "2.15.1" "error" : "some sting" }
    label = 'Invalid tool dependencies'
    if invalid_tool_dependencies_dict:
        invalid_tool_dependency_id = 0
        folder_id += 1
        invalid_tool_dependencies_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        invalid_tool_dependencies_folder = Folder( id=folder_id,
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
            key = generate_tool_dependencies_key( name, version, type )
            label = "Version <b>%s</b> of the <b>%s</b> <b>%s</b>" % ( version, name, type )
            folder = Folder( id=folder_id,
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

def build_invalid_tools_folder( app, folder_id, invalid_tool_configs, changeset_revision, repository=None, label='Invalid tools' ):
    """Return a folder hierarchy containing invalid tools."""
    # TODO: Should we display invalid tools on the tool panel selection page when installing the repository into Galaxy?
    if invalid_tool_configs:
        invalid_tool_id = 0
        folder_id += 1
        invalid_tools_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        folder = Folder( id=folder_id, key='invalid_tools', label=label, parent=invalid_tools_root_folder )
        invalid_tools_root_folder.folders.append( folder )
        for invalid_tool_config in invalid_tool_configs:
            invalid_tool_id += 1
            if repository:
                repository_id = repository.id
                if app.name == 'galaxy':
                    repository_installation_status = repository.status
                else:
                    repository_installation_status = None
            else:
                repository_id = None
                repository_installation_status = None
            invalid_tool = InvalidTool( id=invalid_tool_id,
                                        tool_config=invalid_tool_config,
                                        repository_id=repository_id,
                                        changeset_revision=changeset_revision,
                                        repository_installation_status=repository_installation_status )
            folder.invalid_tools.append( invalid_tool )
    else:
        invalid_tools_root_folder = None
    return folder_id, invalid_tools_root_folder

def build_readme_files_folder( app, folder_id, readme_files_dict, label='Readme files' ):
    """Return a folder hierarchy containing readme text files."""
    if readme_files_dict:
        readme_id = 0
        folder_id += 1
        readme_files_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        readme_files_folder = Folder( id=folder_id, key='readme_files', label=label, parent=readme_files_root_folder )
        multiple_readme_files = len( readme_files_dict ) > 1
        readme_files_root_folder.folders.append( readme_files_folder )
        for readme_file_name, readme_file_text in readme_files_dict.items():
            readme_id += 1
            readme = ReadMe( id=readme_id, name=readme_file_name, text=readme_file_text )
            if multiple_readme_files:
                folder_id += 1
                folder = Folder( id=folder_id, key=readme_file_name, label=readme_file_name, parent=readme_files_folder )
                folder.readme_files.append( readme )
                readme_files_folder.folders.append( folder )
            else:
                readme_files_folder.readme_files.append( readme )
    else:
        readme_files_root_folder = None
    return folder_id, readme_files_root_folder

def build_repository_containers_for_galaxy( app, repository, datatypes, invalid_tools, missing_repository_dependencies, missing_tool_dependencies,
                                            readme_files_dict, repository_dependencies, tool_dependencies, valid_tools, workflows, valid_data_managers,
                                            invalid_data_managers, data_managers_errors, new_install=False, reinstalling=False ):
    """Return a dictionary of containers for the received repository's dependencies and readme files for display during installation to Galaxy."""
    containers_dict = dict( datatypes=None,
                            invalid_tools=None,
                            missing_tool_dependencies=None,
                            readme_files=None,
                            repository_dependencies=None,
                            missing_repository_dependencies=None,
                            tool_dependencies=None,
                            valid_tools=None,
                            workflows=None,
                            valid_data_managers=None,
                            invalid_data_managers=None )
    # Some of the tool dependency folders will include links to display tool dependency information, and some of these links require the repository
    # id.  However we need to be careful because sometimes the repository object is None.
    if repository:
        repository_id = repository.id
        changeset_revision = repository.changeset_revision
    else:
        repository_id = None
        changeset_revision = None
    lock = threading.Lock()
    lock.acquire( True )
    try:
        folder_id = 0
        # Datatypes container.
        if datatypes:
            folder_id, datatypes_root_folder = build_datatypes_folder( app, folder_id, datatypes )
            containers_dict[ 'datatypes' ] = datatypes_root_folder
        # Invalid tools container.
        if invalid_tools:
            folder_id, invalid_tools_root_folder = build_invalid_tools_folder( app,
                                                                               folder_id,
                                                                               invalid_tools,
                                                                               changeset_revision,
                                                                               repository=repository,
                                                                               label='Invalid tools' )
            containers_dict[ 'invalid_tools' ] = invalid_tools_root_folder
        # Readme files container.
        if readme_files_dict:
            folder_id, readme_files_root_folder = build_readme_files_folder( app, folder_id, readme_files_dict )
            containers_dict[ 'readme_files' ] = readme_files_root_folder
        # Installed repository dependencies container.
        if repository_dependencies:
            if new_install:
                label = 'Repository dependencies'
            else:
                label = 'Installed repository dependencies'
            folder_id, repository_dependencies_root_folder = build_repository_dependencies_folder( app=app,
                                                                                                   folder_id=folder_id,
                                                                                                   repository_dependencies=repository_dependencies,
                                                                                                   label=label,
                                                                                                   installed=True )
            containers_dict[ 'repository_dependencies' ] = repository_dependencies_root_folder
        # Missing repository dependencies container.
        if missing_repository_dependencies:
            folder_id, missing_repository_dependencies_root_folder = \
                build_repository_dependencies_folder( app=app,
                                                      folder_id=folder_id,
                                                      repository_dependencies=missing_repository_dependencies,
                                                      label='Missing repository dependencies',
                                                      installed=False )
            containers_dict[ 'missing_repository_dependencies' ] = missing_repository_dependencies_root_folder
        # Installed tool dependencies container.
        if tool_dependencies:
            if new_install:
                label = 'Tool dependencies'
            else:
                label = 'Installed tool dependencies'
            # We only want to display the Status column if the tool_dependency is missing.
            folder_id, tool_dependencies_root_folder = build_tool_dependencies_folder( app,
                                                                                       folder_id,
                                                                                       tool_dependencies,
                                                                                       label=label,
                                                                                       missing=False,
                                                                                       new_install=new_install,
                                                                                       reinstalling=reinstalling )
            containers_dict[ 'tool_dependencies' ] = tool_dependencies_root_folder
        # Missing tool dependencies container.
        if missing_tool_dependencies:
            # We only want to display the Status column if the tool_dependency is missing.
            folder_id, missing_tool_dependencies_root_folder = build_tool_dependencies_folder( app,
                                                                                               folder_id,
                                                                                               missing_tool_dependencies,
                                                                                               label='Missing tool dependencies',
                                                                                               missing=True,
                                                                                               new_install=new_install,
                                                                                               reinstalling=reinstalling )
            containers_dict[ 'missing_tool_dependencies' ] = missing_tool_dependencies_root_folder
        # Valid tools container.
        if valid_tools:
            folder_id, valid_tools_root_folder = build_tools_folder( app,
                                                                     folder_id,
                                                                     valid_tools,
                                                                     repository,
                                                                     changeset_revision,
                                                                     label='Valid tools' )
            containers_dict[ 'valid_tools' ] = valid_tools_root_folder
        # Workflows container.
        if workflows:
            folder_id, workflows_root_folder = build_workflows_folder( app=app,
                                                                       folder_id=folder_id,
                                                                       workflows=workflows,
                                                                       repository_metadata_id=None,
                                                                       repository_id=repository_id,
                                                                       label='Workflows' )
            containers_dict[ 'workflows' ] = workflows_root_folder
        if valid_data_managers:
            folder_id, valid_data_managers_root_folder = build_data_managers_folder( app=app,
                                                                                     folder_id=folder_id,
                                                                                     data_managers=valid_data_managers,
                                                                                     label='Valid Data Managers' )
            containers_dict[ 'valid_data_managers' ] = valid_data_managers_root_folder
        if invalid_data_managers or data_managers_errors:
            folder_id, invalid_data_managers_root_folder = build_invalid_data_managers_folder( app=app,
                                                                                               folder_id=folder_id,
                                                                                               data_managers=invalid_data_managers,
                                                                                               error_messages=data_managers_errors,
                                                                                               label='Invalid Data Managers' )
            containers_dict[ 'invalid_data_managers' ] = invalid_data_managers_root_folder
    except Exception, e:
        log.debug( "Exception in build_repository_containers_for_galaxy: %s" % str( e ) )
    finally:
        lock.release()
    return containers_dict

def build_repository_containers_for_tool_shed( app, repository, changeset_revision, repository_dependencies, repository_metadata,
                                               exclude=None ):
    """Return a dictionary of containers for the received repository's dependencies and contents for display in the tool shed."""
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
                    folder_id, datatypes_root_folder = build_datatypes_folder( app, folder_id, datatypes )
                    containers_dict[ 'datatypes' ] = datatypes_root_folder
            # Invalid repository dependencies container.
            if metadata:
                if 'invalid_repository_dependencies' not in exclude and 'invalid_repository_dependencies' in metadata:
                    invalid_repository_dependencies = metadata[ 'invalid_repository_dependencies' ]
                    folder_id, invalid_repository_dependencies_root_folder = \
                        build_invalid_repository_dependencies_root_folder( app,
                                                                           folder_id,
                                                                           invalid_repository_dependencies )
                    containers_dict[ 'invalid_repository_dependencies' ] = invalid_repository_dependencies_root_folder
            # Invalid tool dependencies container.
            if metadata:
                if 'invalid_tool_dependencies' not in exclude and 'invalid_tool_dependencies' in metadata:
                    invalid_tool_dependencies = metadata[ 'invalid_tool_dependencies' ]
                    folder_id, invalid_tool_dependencies_root_folder = \
                        build_invalid_tool_dependencies_root_folder( app,
                                                                     folder_id,
                                                                     invalid_tool_dependencies )
                    containers_dict[ 'invalid_tool_dependencies' ] = invalid_tool_dependencies_root_folder
            # Invalid tools container.
            if metadata:
                if 'invalid_tools' not in exclude and 'invalid_tools' in metadata:
                    invalid_tool_configs = metadata[ 'invalid_tools' ]
                    folder_id, invalid_tools_root_folder = build_invalid_tools_folder( app,
                                                                                       folder_id,
                                                                                       invalid_tool_configs,
                                                                                       changeset_revision,
                                                                                       repository=repository,
                                                                                       label='Invalid tools' )
                    containers_dict[ 'invalid_tools' ] = invalid_tools_root_folder
            # Readme files container.
            if metadata:
                if 'readme_files' not in exclude and 'readme_files' in metadata:
                    readme_files_dict = readme_util.build_readme_files_dict( app, repository, changeset_revision, metadata )
                    folder_id, readme_files_root_folder = build_readme_files_folder( app, folder_id, readme_files_dict )
                    containers_dict[ 'readme_files' ] = readme_files_root_folder
            if 'repository_dependencies' not in exclude:
                # Repository dependencies container.
                folder_id, repository_dependencies_root_folder = \
                    build_repository_dependencies_folder( app=app,
                                                          folder_id=folder_id,
                                                          repository_dependencies=repository_dependencies,
                                                          label='Repository dependencies',
                                                          installed=False )
                if repository_dependencies_root_folder:
                    containers_dict[ 'repository_dependencies' ] = repository_dependencies_root_folder
            # Tool dependencies container.
            if metadata:
                if 'tool_dependencies' not in exclude and 'tool_dependencies' in metadata:
                    tool_dependencies = metadata[ 'tool_dependencies' ]
                    if app.name == 'tool_shed':
                        if 'orphan_tool_dependencies' in metadata:
                            # The use of the orphan_tool_dependencies category in metadata has been deprecated,
                            # but we still need to check in case the metadata is out of date.
                            orphan_tool_dependencies = metadata[ 'orphan_tool_dependencies' ]
                            tool_dependencies.update( orphan_tool_dependencies )
                        # Tool dependencies can be categorized as orphans only if the repository contains tools.
                        if 'tools' not in exclude:
                            tools = metadata.get( 'tools', [] )
                            tools.extend( metadata.get( 'invalid_tools', [] ) )
                    folder_id, tool_dependencies_root_folder = build_tool_dependencies_folder( app,
                                                                                               folder_id,
                                                                                               tool_dependencies,
                                                                                               missing=False,
                                                                                               new_install=False )
                    containers_dict[ 'tool_dependencies' ] = tool_dependencies_root_folder
            # Valid tools container.
            if metadata:
                if 'tools' not in exclude and 'tools' in metadata:
                    valid_tools = metadata[ 'tools' ]
                    folder_id, valid_tools_root_folder = build_tools_folder( app,
                                                                             folder_id,
                                                                             valid_tools,
                                                                             repository,
                                                                             changeset_revision,
                                                                             label='Valid tools' )
                    containers_dict[ 'valid_tools' ] = valid_tools_root_folder
            # Tool test results container.
            tool_test_results = galaxy.util.listify( repository_metadata.tool_test_results )
            # Only create and populate this folder if there are actual tool test results to display.
            if can_display_tool_test_results( tool_test_results, exclude=exclude ):
                folder_id, tool_test_results_root_folder = build_tool_test_results_folder( app,
                                                                                           folder_id,
                                                                                           tool_test_results,
                                                                                           label='Tool test results' )
                containers_dict[ 'tool_test_results' ] = tool_test_results_root_folder
            # Workflows container.
            if metadata:
                if 'workflows' not in exclude and 'workflows' in metadata:
                    workflows = metadata[ 'workflows' ]
                    folder_id, workflows_root_folder = build_workflows_folder( app=app,
                                                                               folder_id=folder_id,
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
                        build_data_managers_folder( app, folder_id, data_managers, label="Data Managers" )
                    containers_dict[ 'valid_data_managers' ] = data_managers_root_folder
                    error_messages = metadata['data_manager'].get( 'error_messages', None )
                    data_managers = metadata['data_manager'].get( 'invalid_data_managers', None )
                    folder_id, data_managers_root_folder = \
                        build_invalid_data_managers_folder( app, folder_id, data_managers, error_messages, label="Invalid Data Managers" )
                    containers_dict[ 'invalid_data_managers' ] = data_managers_root_folder
        except Exception, e:
            log.exception( "Exception in build_repository_containers_for_tool_shed: %s" % str( e ) )
        finally:
            lock.release()
    return containers_dict

def build_repository_dependencies_folder( app, folder_id, repository_dependencies, label='Repository dependencies', installed=False ):
    """Return a folder hierarchy containing repository dependencies."""
    if repository_dependencies:
        repository_dependency_id = 0
        folder_id += 1
        # Create the root folder.
        repository_dependencies_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        # Create the Repository dependencies folder and add it to the root folder.
        repository_dependencies_folder_key = repository_dependencies[ 'root_key' ]
        repository_dependencies_folder = Folder( id=folder_id,
                                                 key=repository_dependencies_folder_key,
                                                 label=label,
                                                 parent=repository_dependencies_root_folder )
        del repository_dependencies[ 'root_key' ]
        # The received repository_dependencies is a dictionary with keys: 'root_key', 'description', and one or more
        # repository_dependency keys.  We want the description value associated with the repository_dependencies_folder.
        repository_dependencies_folder.description = repository_dependencies.get( 'description', None )
        repository_dependencies_root_folder.folders.append( repository_dependencies_folder )
        del repository_dependencies[ 'description' ]
        repository_dependencies_folder, folder_id, repository_dependency_id = \
            populate_repository_dependencies_container( app,
                                                        repository_dependencies_folder,
                                                        repository_dependencies,
                                                        folder_id,
                                                        repository_dependency_id )
        repository_dependencies_folder = prune_repository_dependencies( repository_dependencies_folder )
    else:
        repository_dependencies_root_folder = None
    return folder_id, repository_dependencies_root_folder

def build_tools_folder( app, folder_id, tool_dicts, repository, changeset_revision, valid=True, label='Valid tools' ):
    """Return a folder hierarchy containing valid tools."""
    if tool_dicts:
        container_object_tool_id = 0
        folder_id += 1
        tools_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        folder = Folder( id=folder_id, key='tools', label=label, parent=tools_root_folder )
        if app.name == 'galaxy':
            folder.description = 'click the name to inspect the tool metadata'
        tools_root_folder.folders.append( folder )
        # Insert a header row.
        container_object_tool_id += 1
        tool = Tool( id=container_object_tool_id,
                     tool_config='',
                     tool_id='',
                     name='Name',
                     description='Description',
                     version='Version',
                     requirements='',
                     repository_id='',
                     changeset_revision='' )
        folder.valid_tools.append( tool )
        if repository:
            repository_id = repository.id
            if app.name == 'galaxy':
                repository_installation_status = repository.status
            else:
                repository_installation_status = None
        else:
            repository_id = None
            repository_installation_status = None
        for tool_dict in tool_dicts:
            if not isinstance( tool_dict, dict ):
                # Due to some previous bug (hopefully not current) invalid tool strings may be included in the received
                # list of tool_dicts.  For example, the picard repository metadata has 2 invalid tools in the received
                # list of supposedly valid tools:  'rgPicardASMetrics.xml', 'rgPicardGCBiasMetrics.xml'.
                continue
            container_object_tool_id += 1
            requirements = tool_dict.get( 'requirements', None )
            if requirements is not None:
                # 'requirements': [{'version': '1.56.0', 'type': 'package', 'name': 'picard'}], 
                requirements_str = ''
                for requirement_dict in requirements:
                    try:
                        requirement_name = str( requirement_dict.get( 'name', 'unknown' ) )
                        requirement_type = str( requirement_dict.get( 'type', 'unknown' ) )
                    except Exception, e:
                        requirement_name = str( e )
                        requirement_type = 'unknown'
                    requirements_str += '%s (%s), ' % ( requirement_name, requirement_type )
                requirements_str = requirements_str.rstrip( ', ' )
            else:
                requirements_str = 'none'
            try:
                tool_config = str( tool_dict.get( 'tool_config', 'missing' ) )
                tool_id = str( tool_dict.get( 'id', 'unknown' ) )
                name = str( tool_dict.get( 'name', 'unknown' ) )
                description = str( tool_dict.get( 'description', '' ) )
                version = str( tool_dict.get( 'version', 'unknown' ) )
            except Exception, e:
                tool_config = str( e )
                tool_id = 'unknown'
                name = 'unknown'
                description = ''
                version = 'unknown'
            tool = Tool( id=container_object_tool_id,
                         tool_config=tool_config,
                         tool_id=tool_id,
                         name=name,
                         description=description,
                         version=version,
                         requirements=requirements_str,
                         repository_id=repository_id,
                         changeset_revision=changeset_revision,
                         repository_installation_status=repository_installation_status )
            folder.valid_tools.append( tool )
    else:
        tools_root_folder = None
    return folder_id, tools_root_folder

def build_tool_dependencies_folder( app, folder_id, tool_dependencies, label='Tool dependencies', missing=False,
                                    new_install=False, reinstalling=False ):
    """Return a folder hierarchy containing tool dependencies."""
    # When we're in Galaxy (not the tool shed) and the tool dependencies are not installed or are in an error state,
    # they are considered missing.  The tool dependency status will be displayed only if a record exists for the tool
    # dependency in the Galaxy database, but the tool dependency is not installed.  The value for new_install will be
    # True only if the associated repository in being installed for the first time.  This value is used in setting the
    # container description.
    if tool_dependencies:
        tool_dependency_id = 0
        folder_id += 1
        tool_dependencies_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        folder = Folder( id=folder_id, key='tool_dependencies', label=label, parent=tool_dependencies_root_folder )
        if app.name == 'galaxy':
            if new_install or reinstalling:
                folder.description = "repository tools require handling of these dependencies"
            elif missing and not new_install and not reinstalling:
                folder.description = 'click the name to install the missing dependency'
            else:
                folder.description = 'click the name to browse the dependency installation directory'
        tool_dependencies_root_folder.folders.append( folder )
        # Insert a header row.
        tool_dependency_id += 1
        if app.name == 'galaxy':
            tool_dependency = ToolDependency( id=tool_dependency_id,
                                              name='Name',
                                              version='Version',
                                              type='Type',
                                              readme=None,
                                              installation_status='Installation status',
                                              repository_id=None,
                                              tool_dependency_id=None )
        else:
            tool_dependency = ToolDependency( id=tool_dependency_id,
                                              name='Name',
                                              version='Version',
                                              type='Type',
                                              readme=None,
                                              installation_status=None,
                                              repository_id=None,
                                              tool_dependency_id=None )
        folder.tool_dependencies.append( tool_dependency )
        not_used_by_local_tools_description = "these dependencies may not be required by tools in this repository"
        for dependency_key, requirements_dict in tool_dependencies.items():
            tool_dependency_id += 1
            if dependency_key in [ 'set_environment' ]:
                for set_environment_dict in requirements_dict:
                    try:
                        name = set_environment_dict.get( 'name', None )
                        type = set_environment_dict[ 'type' ]
                        repository_id = set_environment_dict.get( 'repository_id', None )
                        td_id = set_environment_dict.get( 'tool_dependency_id', None )
                    except Exception, e:
                        name = str( e )
                        type = 'unknown'
                        repository_id = 'unknown'
                        td_id = 'unknown'
                    if app.name == 'galaxy':
                        try:
                            installation_status = set_environment_dict.get( 'status', 'Never installed' )
                        except Exception, e:
                            installation_status = str( e )
                    else:
                        installation_status = None
                    tool_dependency = ToolDependency( id=tool_dependency_id,
                                                      name=name,
                                                      version=None,
                                                      type=type,
                                                      readme=None,
                                                      installation_status=installation_status,
                                                      repository_id=repository_id,
                                                      tool_dependency_id=td_id )
                    folder.tool_dependencies.append( tool_dependency )
            else:
                try:
                    name = requirements_dict[ 'name' ]
                    version = requirements_dict[ 'version' ]
                    type = requirements_dict[ 'type' ]
                    repository_id = requirements_dict.get( 'repository_id', None )
                    td_id = requirements_dict.get( 'tool_dependency_id', None )
                except Exception, e:
                    name = str( e )
                    version = 'unknown'
                    type = 'unknown'
                    repository_id = 'unknown'
                    td_id = 'unknown'
                if app.name == 'galaxy':
                    try:
                        installation_status = requirements_dict.get( 'status', 'Never installed' )
                    except Exception, e:
                        installation_status = str( e )
                else:
                    installation_status = None
                tool_dependency = ToolDependency( id=tool_dependency_id,
                                                  name=name,
                                                  version=version,
                                                  type=type,
                                                  readme=None,
                                                  installation_status=installation_status,
                                                  repository_id=repository_id,
                                                  tool_dependency_id=td_id )
                folder.tool_dependencies.append( tool_dependency )
    else:
        tool_dependencies_root_folder = None
    return folder_id, tool_dependencies_root_folder

def build_tool_test_results_folder( app, folder_id, tool_test_results_dicts, label='Tool test results' ):
    """Return a folder hierarchy containing tool dependencies."""
    # This container is displayed only in the tool shed.
    if tool_test_results_dicts:
        folder_id += 1
        tool_test_results_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        multiple_tool_test_results_dicts = len( tool_test_results_dicts ) > 1
        if multiple_tool_test_results_dicts:
            folder_id += 1
            test_runs_folder = Folder( id=folder_id, key='test_runs', label='Test runs', parent=tool_test_results_root_folder )
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
                containing_folder = Folder( id=folder_id, key='test_results', label=time_tested, parent=test_runs_folder )
                test_runs_folder.folders.append( containing_folder )
            else:
                containing_folder = tool_test_results_root_folder
            folder_id += 1
            test_environment_folder = Folder( id=folder_id,
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
                not_tested_folder = Folder( id=folder_id, key='not_tested', label='Not tested', parent=containing_folder )
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
                passed_tests_folder = Folder( id=folder_id,
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
                failed_tests_folder = Folder( id=folder_id, key='failed_tests', label='Tests that failed', parent=containing_folder )
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
                missing_test_components_folder = Folder( id=folder_id,
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
                    installation_error_base_folder = Folder( id=folder_id,
                                                             key='installation_errors',
                                                             label='Installation errors',
                                                             parent=containing_folder )
                    containing_folder.folders.append( installation_error_base_folder )
                    if len( current_repository_installation_error_dicts ) > 0:
                        folder_id += 1
                        current_repository_folder = Folder( id=folder_id,
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
                        repository_dependencies_folder = Folder( id=folder_id,
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
                        tool_dependencies_folder = Folder( id=folder_id,
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
                    successful_installation_base_folder = Folder( id=folder_id,
                                                                  key='successful_installations',
                                                                  label='Successful installations',
                                                                  parent=containing_folder )
                    containing_folder.folders.append( successful_installation_base_folder )
                    # Displaying the successful installation of the current repository is not really necessary, so we'll skip it.
                    if len( repository_dependency_successful_installation_dicts ) > 0:
                        folder_id += 1
                        repository_dependencies_folder = Folder( id=folder_id,
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
                        tool_dependencies_folder = Folder( id=folder_id,
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

def build_workflows_folder( app, folder_id, workflows, repository_metadata_id=None, repository_id=None, label='Workflows' ):
    """
    Return a folder hierarchy containing workflow objects for each workflow dictionary in the received workflows list.  When
    this method is called from the tool shed, repository_metadata_id will have a value and repository_id will be None.  When
    this method is called from Galaxy, repository_id will have a value only if the repository is not currenlty being installed
    and repository_metadata_id will be None.
    """
    if workflows:
        workflow_id = 0
        folder_id += 1
        workflows_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        folder = Folder( id=folder_id, key='workflows', label=label, parent=workflows_root_folder )
        workflows_root_folder.folders.append( folder )
        # Insert a header row.
        workflow_id += 1
        workflow = Workflow( id=workflow_id,
                             workflow_name='Name',
                             steps='steps',
                             format_version='format-version',
                             annotation='annotation',
                             repository_metadata_id=repository_metadata_id,
                             repository_id=repository_id )
        folder.workflows.append( workflow )
        for workflow_tup in workflows:
            workflow_dict=workflow_tup[ 1 ]
            steps = workflow_dict.get( 'steps', [] )
            if steps:
                steps = str( len( steps ) )
            else:
                steps = 'unknown'
            workflow_id += 1
            workflow = Workflow( id=workflow_id,
                                 workflow_name=workflow_dict.get( 'name', '' ),
                                 steps=steps,
                                 format_version=workflow_dict.get( 'format-version', '' ),
                                 annotation=workflow_dict.get( 'annotation', '' ),
                                 repository_metadata_id=repository_metadata_id,
                                 repository_id=repository_id )
            folder.workflows.append( workflow )
    else:
        workflows_root_folder = None
    return folder_id, workflows_root_folder

def can_display_tool_test_results( tool_test_results_dicts, exclude=None ):
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

def generate_repository_dependencies_folder_label_from_key( repository_name, repository_owner, changeset_revision,
                                                            prior_installation_required, only_if_compiling_contained_td, key ):
    """Return a repository dependency label based on the repository dependency key."""
    if key_is_current_repositorys_key( repository_name,
                                       repository_owner,
                                       changeset_revision,
                                       prior_installation_required,
                                       only_if_compiling_contained_td, key ):
        label = 'Repository dependencies'
    else:
        if galaxy.util.asbool( prior_installation_required ):
            prior_installation_required_str = " <i>(prior install required)</i>"
        else:
            prior_installation_required_str = ""
        label = "Repository <b>%s</b> revision <b>%s</b> owned by <b>%s</b>%s" % \
            ( repository_name, changeset_revision, repository_owner, prior_installation_required_str )
    return label

def generate_repository_dependencies_key_for_repository( toolshed_base_url, repository_name, repository_owner, changeset_revision,
                                                         prior_installation_required, only_if_compiling_contained_td ):
    """Assumes tool shed is current tool shed since repository dependencies across tool sheds is not yet supported."""
    # The tool_shed portion of the key must be the value that is stored in the tool_shed_repository.tool_shed column
    # of the Galaxy database for an installed repository.  This value does not include the protocol, but does include
    # the port if there is one.
    tool_shed = common_util.remove_protocol_from_tool_shed_url( toolshed_base_url )
    return '%s%s%s%s%s%s%s%s%s%s%s' % ( tool_shed,
                                        STRSEP,
                                        str( repository_name ),
                                        STRSEP,
                                        str( repository_owner ),
                                        STRSEP,
                                        str( changeset_revision ),
                                        STRSEP,
                                        str( prior_installation_required ),
                                        STRSEP,
                                        str( only_if_compiling_contained_td ) )

def generate_tool_dependencies_key( name, version, type ):
    return '%s%s%s%s%s' % ( str( name ), STRSEP, str( version ), STRSEP, str( type ) )

def get_components_from_repository_dependency_for_installed_repository( app, repository_dependency ):
    """Parse a repository dependency and return components necessary for proper display in Galaxy on the Manage repository page."""
    # Default prior_installation_required and only_if_compiling_contained_td to False.
    prior_installation_required = 'False'
    only_if_compiling_contained_td = 'False'
    if len( repository_dependency ) == 6:
        # Metadata should have been reset on this installed repository, but it wasn't.
        tool_shed_repository_id = repository_dependency[ 4 ]
        installation_status = repository_dependency[ 5 ]
        tool_shed, name, owner, changeset_revision = repository_dependency[ 0:4 ]
        repository_dependency = [ tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td ]
    elif len( repository_dependency ) == 7:
        # We have a repository dependency tuple that includes a prior_installation_required value but not a only_if_compiling_contained_td value.
        tool_shed_repository_id = repository_dependency[ 5 ]
        installation_status = repository_dependency[ 6 ]
        tool_shed, name, owner, changeset_revision, prior_installation_required = repository_dependency[ 0:5 ]
        repository_dependency = [ tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td ]
    elif len( repository_dependency ) == 8:
        # We have a repository dependency tuple that includes both a prior_installation_required value and a only_if_compiling_contained_td value.
        tool_shed_repository_id = repository_dependency[ 6 ]
        installation_status = repository_dependency[ 7 ]
        repository_dependency = repository_dependency[ 0:6 ]
    else:
        tool_shed_repository_id = None
        installation_status = 'unknown'
    if tool_shed_repository_id:
        tool_shed_repository = suc.get_tool_shed_repository_by_id( app,
                                                                   app.security.encode_id( tool_shed_repository_id ) )
        if tool_shed_repository:
            if tool_shed_repository.missing_repository_dependencies:
                installation_status = '%s, missing repository dependencies' % installation_status
            elif tool_shed_repository.missing_tool_dependencies:
                installation_status = '%s, missing tool dependencies' % installation_status
    return tool_shed_repository_id, installation_status, repository_dependency

def get_components_from_key( key ):
    """Assumes tool shed is current tool shed since repository dependencies across tool sheds is not yet supported."""
    items = key.split( STRSEP )
    toolshed_base_url = items[ 0 ]
    repository_name = items[ 1 ]
    repository_owner = items[ 2 ]
    changeset_revision = items[ 3 ]
    if len( items ) == 5:
        prior_installation_required = items[ 4 ]
        return toolshed_base_url, repository_name, repository_owner, changeset_revision, prior_installation_required
    elif len( items ) == 6:
        prior_installation_required = items[ 4 ]
        only_if_compiling_contained_td = items[ 5 ]
        return toolshed_base_url, repository_name, repository_owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td
    else:
        # For backward compatibility to the 12/20/12 Galaxy release we have to return the following, and callers must handle exceptions.
        return toolshed_base_url, repository_name, repository_owner, changeset_revision

def get_folder( folder, key ):
    if folder.key == key:
        return folder
    for sub_folder in folder.folders:
        return get_folder( sub_folder, key )
    return None

def handle_repository_dependencies_container_entry( app, repository_dependencies_folder, rd_key, rd_value, folder_id,
                                                    repository_dependency_id, folder_keys ):
    repository_components_tuple = get_components_from_key( rd_key )
    components_list = suc.extract_components_from_tuple( repository_components_tuple )
    toolshed, repository_name, repository_owner, changeset_revision = components_list[ 0:4 ]
    # For backward compatibility to the 12/20/12 Galaxy release.
    if len( components_list ) == 4:
        prior_installation_required = 'False'
        only_if_compiling_contained_td = 'False'
    elif len( components_list ) == 5:
        prior_installation_required = components_list[ 4 ]
        only_if_compiling_contained_td = 'False'
    elif len( components_list ) == 6:
        prior_installation_required = components_list[ 4 ]
        only_if_compiling_contained_td = components_list[ 5 ]
    folder = get_folder( repository_dependencies_folder, rd_key )
    label = generate_repository_dependencies_folder_label_from_key( repository_name,
                                                                    repository_owner,
                                                                    changeset_revision,
                                                                    prior_installation_required,
                                                                    only_if_compiling_contained_td,
                                                                    repository_dependencies_folder.key )
    if folder:
        if rd_key not in folder_keys:
            folder_id += 1
            sub_folder = Folder( id=folder_id, key=rd_key, label=label, parent=folder )
            folder.folders.append( sub_folder )
        else:
            sub_folder = folder
    else:
        folder_id += 1
        sub_folder = Folder( id=folder_id, key=rd_key, label=label, parent=repository_dependencies_folder )
        repository_dependencies_folder.folders.append( sub_folder )
    if app.name == 'galaxy':
        # Insert a header row.
        repository_dependency_id += 1
        repository_dependency = RepositoryDependency( id=repository_dependency_id,
                                                      repository_name='Name',
                                                      changeset_revision='Revision',
                                                      repository_owner='Owner',
                                                      installation_status='Installation status' )
        # Insert the header row into the folder.
        sub_folder.repository_dependencies.append( repository_dependency )
    for repository_dependency in rd_value:
        if app.name == 'galaxy':
            tool_shed_repository_id, installation_status, repository_dependency = \
                get_components_from_repository_dependency_for_installed_repository( app, repository_dependency )
        else:
            tool_shed_repository_id = None
            installation_status = None
        can_create_dependency = not is_subfolder_of( sub_folder, repository_dependency )
        if can_create_dependency:
            toolshed, repository_name, repository_owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
                common_util.parse_repository_dependency_tuple( repository_dependency )
            repository_dependency_id += 1
            repository_dependency = RepositoryDependency( id=repository_dependency_id,
                                                          toolshed=toolshed,
                                                          repository_name=repository_name,
                                                          repository_owner=repository_owner,
                                                          changeset_revision=changeset_revision,
                                                          prior_installation_required=galaxy.util.asbool( prior_installation_required ),
                                                          only_if_compiling_contained_td=galaxy.util.asbool( only_if_compiling_contained_td ),
                                                          installation_status=installation_status,
                                                          tool_shed_repository_id=tool_shed_repository_id )
            # Insert the repository_dependency into the folder.
            sub_folder.repository_dependencies.append( repository_dependency )
    return repository_dependencies_folder, folder_id, repository_dependency_id

def is_subfolder_of( folder, repository_dependency ):
    toolshed, repository_name, repository_owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
        common_util.parse_repository_dependency_tuple( repository_dependency )
    key = generate_repository_dependencies_key_for_repository( toolshed,
                                                               repository_name,
                                                               repository_owner,
                                                               changeset_revision,
                                                               prior_installation_required,
                                                               only_if_compiling_contained_td )
    for sub_folder in folder.folders:
        if key == sub_folder.key:
            return True
    return False

def key_is_current_repositorys_key( repository_name, repository_owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td, key ):
    repository_components_tuple = get_components_from_key( key )
    components_list = suc.extract_components_from_tuple( repository_components_tuple )
    toolshed, key_name, key_owner, key_changeset_revision = components_list[ 0:4 ]
    # For backward compatibility to the 12/20/12 Galaxy release.
    if len( components_list ) == 4:
        key_prior_installation_required = 'False'
        key_only_if_compiling_contained_td = 'False'
    elif len( components_list ) == 5:
        key_prior_installation_required = components_list[ 4 ]
        key_only_if_compiling_contained_td = 'False'
    elif len( components_list ) == 6:
        key_prior_installation_required = components_list[ 4 ]
        key_only_if_compiling_contained_td = components_list[ 5 ]
    if repository_name == key_name and \
        repository_owner == key_owner and \
        changeset_revision == key_changeset_revision and \
        prior_installation_required == key_prior_installation_required and \
        only_if_compiling_contained_td == key_only_if_compiling_contained_td:
        return True
    return False

def populate_repository_dependencies_container( app, repository_dependencies_folder, repository_dependencies, folder_id,
                                                repository_dependency_id ):
    folder_keys = []
    for key in repository_dependencies.keys():
        if key not in folder_keys:
            folder_keys.append( key )
    for key, value in repository_dependencies.items():
        repository_dependencies_folder, folder_id, repository_dependency_id = \
            handle_repository_dependencies_container_entry( app,
                                                            repository_dependencies_folder,
                                                            key,
                                                            value,
                                                            folder_id,
                                                            repository_dependency_id,
                                                            folder_keys )
    return repository_dependencies_folder, folder_id, repository_dependency_id

def print_folders( pad, folder ):
    # For debugging...
    pad_str = ''
    for i in range( 1, pad ):
        pad_str += ' '
    print '%sid: %s key: %s' % ( pad_str, str( folder.id ), folder.key )
    for repository_dependency in folder.repository_dependencies:
        print '    %s%s' % ( pad_str, repository_dependency.listify )
    for sub_folder in folder.folders:
        print_folders( pad+5, sub_folder )

def prune_folder( folder, repository_dependency ):
    listified_repository_dependency = repository_dependency.listify
    if is_subfolder_of( folder, listified_repository_dependency ):
        folder.repository_dependencies.remove( repository_dependency )

def prune_repository_dependencies( folder ):
    """
    Since the object used to generate a repository dependencies container is a dictionary and not an odict() (it must be
    json-serialize-able), the order in which the dictionary is processed to create the container sometimes results in
    repository dependency entries in a folder that also includes the repository dependency as a sub-folder (if the
    repository dependency has its own repository dependency).  This method will remove all repository dependencies from
    folder that are also sub-folders of folder.
    """
    repository_dependencies = [ rd for rd in folder.repository_dependencies ]
    for repository_dependency in repository_dependencies:
        prune_folder( folder, repository_dependency )
    for sub_folder in folder.folders:
        return prune_repository_dependencies( sub_folder )
    return folder
