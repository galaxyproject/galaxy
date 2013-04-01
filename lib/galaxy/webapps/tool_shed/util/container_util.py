import os, logging, threading
from tool_shed.util import readme_util

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
        self.description = None
        self.datatypes = []
        self.folders = []
        self.invalid_repository_dependencies = []
        self.invalid_tool_dependencies = []
        self.invalid_tools = []
        self.valid_tools = []
        self.valid_data_managers = []
        self.invalid_data_managers = []
        self.tool_dependencies = []
        self.repository_dependencies = []
        self.readme_files = []
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
    def to_repository_dependency( self, repository_dependency_id ):
        toolshed, name, owner, changeset_revision = self.key.split( STRSEP )
        return RepositoryDependency( id=repository_dependency_id,
                                     toolshed=toolshed,
                                     repository_name=name,
                                     repository_owner=owner,
                                     changeset_revision=changeset_revision )

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

class InvalidDataManager( object ):
    """Data Manager object"""
    def __init__( self, id=None, index=None, error=None ):
        self.id = id
        self.index = index
        self.error = error

class InvalidRepositoryDependency( object ):
    """Invalid repository dependency definition object"""
    def __init__( self, id=None, toolshed=None, repository_name=None, repository_owner=None, changeset_revision=None, error=None ):
        self.id = id
        self.toolshed = toolshed
        self.repository_name = repository_name
        self.repository_owner = repository_owner
        self.changeset_revision = changeset_revision
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

class ReadMe( object ):
    """Readme text object"""
    def __init__( self, id=None, name=None, text=None ):
        self.id = id
        self.name = name
        self.text = text

class RepositoryDependency( object ):
    """Repository dependency object"""
    def __init__( self, id=None, toolshed=None, repository_name=None, repository_owner=None, changeset_revision=None, installation_status=None, tool_shed_repository_id=None ):
        self.id = id
        self.toolshed = toolshed
        self.repository_name = repository_name
        self.repository_owner = repository_owner
        self.changeset_revision = changeset_revision
        self.installation_status = installation_status
        self.tool_shed_repository_id = tool_shed_repository_id
    @property
    def listify( self ):
        return [ self.toolshed, self.repository_name, self.repository_owner, self.changeset_revision ]

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
    def __init__( self, id=None, name=None, version=None, type=None, install_dir=None, readme=None, installation_status=None, repository_id=None,
                  tool_dependency_id=None, is_orphan=None ):
        self.id = id
        self.name = name
        self.version = version
        self.type = type
        self.install_dir = install_dir
        self.readme = readme
        self.installation_status = installation_status
        self.repository_id = repository_id
        self.tool_dependency_id = tool_dependency_id
        self.is_orphan = is_orphan
    @property
    def listify( self ):
        return [ self.name, self.version, self.type ]

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

def add_orphan_settings_to_tool_dependencies( tool_dependencies, orphan_tool_dependencies ):
    """Inspect all received tool dependencies and label those that are orphans within the repository."""
    orphan_env_dependencies = orphan_tool_dependencies.get( 'set_environment', None )
    new_tool_dependencies = {}
    if tool_dependencies:
        for td_key, requirements_dict in tool_dependencies.items():
            if td_key in [ 'set_environment' ]:
                # "set_environment": [{"name": "R_SCRIPT_PATH", "type": "set_environment"}]
                if orphan_env_dependencies:
                    new_set_environment_dict_list = []
                    for set_environment_dict in requirements_dict:
                        if set_environment_dict in orphan_env_dependencies:
                            set_environment_dict[ 'is_orphan' ] = True
                        else:
                            set_environment_dict[ 'is_orphan' ] = False
                        new_set_environment_dict_list.append( set_environment_dict )
                    new_tool_dependencies[ td_key ] = new_set_environment_dict_list
                else:
                    new_tool_dependencies[ td_key ] = requirements_dict
            else:
                # {"R/2.15.1": {"name": "R", "readme": "some string", "type": "package", "version": "2.15.1"}
                if td_key in orphan_tool_dependencies:
                    requirements_dict[ 'is_orphan' ] = True
                else:
                    requirements_dict[ 'is_orphan' ] = False
                new_tool_dependencies[ td_key ] = requirements_dict
    return new_tool_dependencies

def build_data_managers_folder( trans, folder_id, data_managers, label=None ):
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
            data_manager = DataManager( id=data_manager_id,
                                 name=data_manager_dict.get( 'name', '' ),
                                 version=data_manager_dict.get( 'version', '' ),
                                 data_tables=", ".join( data_manager_dict.get( 'data_tables', '' ) ) )
            folder.valid_data_managers.append( data_manager )
    else:
        data_managers_root_folder = None
    return folder_id, data_managers_root_folder

def build_datatypes_folder( trans, folder_id, datatypes, label='Datatypes' ):
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
            datatype = Datatype( id=datatype_id,
                                 extension=datatypes_dict.get( 'extension', '' ),
                                 type=datatypes_dict.get( 'dtype', '' ),
                                 mimetype=datatypes_dict.get( 'mimetype', '' ),
                                 subclass=datatypes_dict.get( 'subclass', '' ),
                                 converters=num_converters,
                                 display_app_containers=num_display_app_containers )
            folder.datatypes.append( datatype )
    else:
        datatypes_root_folder = None
    return folder_id, datatypes_root_folder

def build_invalid_data_managers_folder( trans, folder_id, data_managers, error_messages=None, label=None ):
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

def build_invalid_repository_dependencies_root_folder( trans, folder_id, invalid_repository_dependencies_dict ):
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
            toolshed, name, owner, changeset_revision, error = invalid_repository_dependency
            key = generate_repository_dependencies_key_for_repository( toolshed, name, owner, changeset_revision )
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
                                               error=error )
            folder.invalid_repository_dependencies.append( ird )
            invalid_repository_dependencies_folder.folders.append( folder )
    else:
        invalid_repository_dependencies_root_folder = None
    return folder_id, invalid_repository_dependencies_root_folder

def build_invalid_tool_dependencies_root_folder( trans, folder_id, invalid_tool_dependencies_dict ):
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
            name = requirements_dict[ 'name' ]
            type = requirements_dict[ 'type' ]
            version = requirements_dict[ 'version' ]
            error = requirements_dict[ 'error' ]
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

def build_invalid_tools_folder( trans, folder_id, invalid_tool_configs, changeset_revision, repository=None, label='Invalid tools' ):
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
                if trans.webapp.name == 'galaxy':
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

def build_readme_files_folder( trans, folder_id, readme_files_dict, label='Readme files' ):
    """Return a folder hierarchy containing readme text files."""
    if readme_files_dict:
        multiple_readme_files = len( readme_files_dict ) > 1
        readme_id = 0
        folder_id += 1
        readme_files_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        if multiple_readme_files:
            folder_id += 1
            readme_files_folder = Folder( id=folder_id, key='readme_files', label=label, parent=readme_files_root_folder )
            readme_files_root_folder.folders.append( readme_files_folder )
        for readme_file_name, readme_file_text in readme_files_dict.items():
            readme_id += 1
            readme = ReadMe( id=readme_id, name=readme_file_name, text=readme_file_text )
            if multiple_readme_files:
                folder_id += 1
                folder = Folder( id=folder_id, key=readme.name, label=readme.name, parent=readme_files_folder )
                folder.readme_files.append( readme )
                readme_files_folder.folders.append( folder )
            else:
                folder_id += 1
                readme_files_folder = Folder( id=folder_id, key='readme_files', label=readme.name, parent=readme_files_root_folder )
                readme_files_folder.readme_files.append( readme )
                readme_files_root_folder.folders.append( readme_files_folder )
    else:
        readme_files_root_folder = None
    return folder_id, readme_files_root_folder

def build_repository_containers_for_galaxy( trans, repository, datatypes, invalid_tools, missing_repository_dependencies, missing_tool_dependencies,
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
            folder_id, datatypes_root_folder = build_datatypes_folder( trans, folder_id, datatypes )
            containers_dict[ 'datatypes' ] = datatypes_root_folder
        # Invalid tools container.
        if invalid_tools:
            folder_id, invalid_tools_root_folder = build_invalid_tools_folder( trans,
                                                                               folder_id,
                                                                               invalid_tools,
                                                                               changeset_revision,
                                                                               repository=repository,
                                                                               label='Invalid tools' )
            containers_dict[ 'invalid_tools' ] = invalid_tools_root_folder
        # Readme files container.
        if readme_files_dict:
            folder_id, readme_files_root_folder = build_readme_files_folder( trans, folder_id, readme_files_dict )
            containers_dict[ 'readme_files' ] = readme_files_root_folder
        # Installed repository dependencies container.
        if repository_dependencies:
            if new_install:
                label = 'Repository dependencies'
            else:
                label = 'Installed repository dependencies'
            folder_id, repository_dependencies_root_folder = build_repository_dependencies_folder( trans=trans,
                                                                                                   folder_id=folder_id,
                                                                                                   repository_dependencies=repository_dependencies,
                                                                                                   label=label,
                                                                                                   installed=True )
            containers_dict[ 'repository_dependencies' ] = repository_dependencies_root_folder
        # Missing repository dependencies container.
        if missing_repository_dependencies:
            folder_id, missing_repository_dependencies_root_folder = \
                build_repository_dependencies_folder( trans=trans,
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
            folder_id, tool_dependencies_root_folder = build_tool_dependencies_folder( trans,
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
            folder_id, missing_tool_dependencies_root_folder = build_tool_dependencies_folder( trans,
                                                                                               folder_id,
                                                                                               missing_tool_dependencies,
                                                                                               label='Missing tool dependencies',
                                                                                               missing=True,
                                                                                               new_install=new_install,
                                                                                               reinstalling=reinstalling )
            containers_dict[ 'missing_tool_dependencies' ] = missing_tool_dependencies_root_folder
        # Valid tools container.
        if valid_tools:
            folder_id, valid_tools_root_folder = build_tools_folder( trans,
                                                                     folder_id,
                                                                     valid_tools,
                                                                     repository,
                                                                     changeset_revision,
                                                                     label='Valid tools' )
            containers_dict[ 'valid_tools' ] = valid_tools_root_folder
        # Workflows container.
        if workflows:
            folder_id, workflows_root_folder = build_workflows_folder( trans=trans,
                                                                       folder_id=folder_id,
                                                                       workflows=workflows,
                                                                       repository_metadata_id=None,
                                                                       repository_id=repository_id,
                                                                       label='Workflows' )
            containers_dict[ 'workflows' ] = workflows_root_folder
        if valid_data_managers:
            folder_id, valid_data_managers_root_folder = build_data_managers_folder( trans=trans,
                                                                                     folder_id=folder_id,
                                                                                     data_managers=valid_data_managers,
                                                                                     label='Valid Data Managers' )
            containers_dict[ 'valid_data_managers' ] = valid_data_managers_root_folder
        if invalid_data_managers or data_managers_errors:
            folder_id, invalid_data_managers_root_folder = build_invalid_data_managers_folder( trans=trans,
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

def build_repository_containers_for_tool_shed( trans, repository, changeset_revision, repository_dependencies, repository_metadata ):
    """Return a dictionary of containers for the received repository's dependencies and contents for display in the tool shed."""
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
                if 'datatypes' in metadata:
                    datatypes = metadata[ 'datatypes' ]
                    folder_id, datatypes_root_folder = build_datatypes_folder( trans, folder_id, datatypes )
                    containers_dict[ 'datatypes' ] = datatypes_root_folder
            # Invalid repository dependencies container.
            if metadata:
                if 'invalid_repository_dependencies' in metadata:
                    invalid_repository_dependencies = metadata[ 'invalid_repository_dependencies' ]
                    folder_id, invalid_repository_dependencies_root_folder = \
                        build_invalid_repository_dependencies_root_folder( trans,
                                                                           folder_id,
                                                                           invalid_repository_dependencies )
                    containers_dict[ 'invalid_repository_dependencies' ] = invalid_repository_dependencies_root_folder
            # Invalid tool dependencies container.
            if metadata:
                if 'invalid_tool_dependencies' in metadata:
                    invalid_tool_dependencies = metadata[ 'invalid_tool_dependencies' ]
                    folder_id, invalid_tool_dependencies_root_folder = \
                        build_invalid_tool_dependencies_root_folder( trans,
                                                                     folder_id,
                                                                     invalid_tool_dependencies )
                    containers_dict[ 'invalid_tool_dependencies' ] = invalid_tool_dependencies_root_folder
            # Invalid tools container.
            if metadata:
                if 'invalid_tools' in metadata:
                    invalid_tool_configs = metadata[ 'invalid_tools' ]
                    folder_id, invalid_tools_root_folder = build_invalid_tools_folder( trans,
                                                                                       folder_id,
                                                                                       invalid_tool_configs,
                                                                                       changeset_revision,
                                                                                       repository=repository,
                                                                                       label='Invalid tools' )
                    containers_dict[ 'invalid_tools' ] = invalid_tools_root_folder
            # Readme files container.
            if metadata:
                if 'readme_files' in metadata:
                    readme_files_dict = readme_util.build_readme_files_dict( metadata )
                    folder_id, readme_files_root_folder = build_readme_files_folder( trans, folder_id, readme_files_dict )
                    containers_dict[ 'readme_files' ] = readme_files_root_folder
            # Repository dependencies container.
            folder_id, repository_dependencies_root_folder = build_repository_dependencies_folder( trans=trans,
                                                                                                   folder_id=folder_id,
                                                                                                   repository_dependencies=repository_dependencies,
                                                                                                   label='Repository dependencies',
                                                                                                   installed=False )
            if repository_dependencies_root_folder:
                containers_dict[ 'repository_dependencies' ] = repository_dependencies_root_folder
            # Tool dependencies container.
            if metadata:
                if 'tool_dependencies' in metadata:
                    tool_dependencies = metadata[ 'tool_dependencies' ]
                    if trans.webapp.name == 'tool_shed':
                        if 'orphan_tool_dependencies' in metadata:
                            orphan_tool_dependencies = metadata[ 'orphan_tool_dependencies' ]
                            tool_dependencies = add_orphan_settings_to_tool_dependencies( tool_dependencies, orphan_tool_dependencies )
                    folder_id, tool_dependencies_root_folder = build_tool_dependencies_folder( trans,
                                                                                               folder_id,
                                                                                               tool_dependencies,
                                                                                               missing=False,
                                                                                               new_install=False )
                    containers_dict[ 'tool_dependencies' ] = tool_dependencies_root_folder
            # Valid tools container.
            if metadata:
                if 'tools' in metadata:
                    valid_tools = metadata[ 'tools' ]
                    folder_id, valid_tools_root_folder = build_tools_folder( trans,
                                                                             folder_id,
                                                                             valid_tools,
                                                                             repository,
                                                                             changeset_revision,
                                                                             label='Valid tools' )
                    containers_dict[ 'valid_tools' ] = valid_tools_root_folder
            # Workflows container.
            if metadata:
                if 'workflows' in metadata:
                    workflows = metadata[ 'workflows' ]
                    folder_id, workflows_root_folder = build_workflows_folder( trans=trans,
                                                                               folder_id=folder_id,
                                                                               workflows=workflows,
                                                                               repository_metadata_id=repository_metadata.id,
                                                                               repository_id=None,
                                                                               label='Workflows' )
                    containers_dict[ 'workflows' ] = workflows_root_folder
            # Valid Data Managers container
            if metadata:
                if 'data_manager' in metadata:
                    data_managers = metadata['data_manager'].get( 'data_managers', None )
                    folder_id, data_managers_root_folder = build_data_managers_folder( trans, folder_id, data_managers, label="Data Managers" )
                    containers_dict[ 'valid_data_managers' ] = data_managers_root_folder
                    error_messages = metadata['data_manager'].get( 'error_messages', None )
                    data_managers = metadata['data_manager'].get( 'invalid_data_managers', None )
                    folder_id, data_managers_root_folder = build_invalid_data_managers_folder( trans, folder_id, data_managers, error_messages, label="Invalid Data Managers" )
                    containers_dict[ 'invalid_data_managers' ] = data_managers_root_folder
                    
        except Exception, e:
            log.debug( "Exception in build_repository_containers_for_tool_shed: %s" % str( e ) )
        finally:
            lock.release()
    return containers_dict

def build_repository_dependencies_folder( trans, folder_id, repository_dependencies, label='Repository dependencies', installed=False ):
    """Return a folder hierarchy containing repository dependencies."""
    if repository_dependencies:
        repository_dependency_id = 0
        folder_id += 1
        # Create the root folder.
        repository_dependencies_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        # Create the Repository dependencies folder and add it to the root folder.
        repository_dependencies_folder_key = repository_dependencies[ 'root_key' ]
        repository_dependencies_folder = Folder( id=folder_id, key=repository_dependencies_folder_key, label=label, parent=repository_dependencies_root_folder )
        del repository_dependencies[ 'root_key' ]
        # The received repository_dependencies is a dictionary with keys: 'root_key', 'description', and one or more repository_dependency keys.
        # We want the description value associated with the repository_dependencies_folder.
        repository_dependencies_folder.description = repository_dependencies.get( 'description', None )
        repository_dependencies_root_folder.folders.append( repository_dependencies_folder )
        del repository_dependencies[ 'description' ]
        repository_dependencies_folder, folder_id, repository_dependency_id = \
            populate_repository_dependencies_container( trans, repository_dependencies_folder, repository_dependencies, folder_id, repository_dependency_id )
        repository_dependencies_folder = prune_repository_dependencies( repository_dependencies_folder )
    else:
        repository_dependencies_root_folder = None
    return folder_id, repository_dependencies_root_folder

def build_tools_folder( trans, folder_id, tool_dicts, repository, changeset_revision, valid=True, label='Valid tools' ):
    """Return a folder hierarchy containing valid tools."""
    if tool_dicts:
        tool_id = 0
        folder_id += 1
        tools_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        folder = Folder( id=folder_id, key='tools', label=label, parent=tools_root_folder )
        if trans.webapp.name == 'galaxy':
            folder.description = 'click the name to inspect the tool metadata'
        tools_root_folder.folders.append( folder )
        # Insert a header row.
        tool_id += 1
        tool = Tool( id=tool_id,
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
            if trans.webapp.name == 'galaxy':
                repository_installation_status = repository.status
            else:
                repository_installation_status = None
        else:
            repository_id = None
            repository_installation_status = None
        for tool_dict in tool_dicts:
            tool_id += 1
            if 'requirements' in tool_dict:
                requirements = tool_dict[ 'requirements' ]
                requirements_str = ''
                for requirement_dict in requirements:
                    requirements_str += '%s (%s), ' % ( requirement_dict[ 'name' ], requirement_dict[ 'type' ] )
                requirements_str = requirements_str.rstrip( ', ' )
            else:
                requirements_str = 'none'
            tool = Tool( id=tool_id,
                         tool_config=tool_dict[ 'tool_config' ],
                         tool_id=tool_dict[ 'id' ],
                         name=tool_dict[ 'name' ],
                         description=tool_dict[ 'description' ],
                         version=tool_dict[ 'version' ],
                         requirements=requirements_str,
                         repository_id=repository_id,
                         changeset_revision=changeset_revision,
                         repository_installation_status=repository_installation_status )
            folder.valid_tools.append( tool )
    else:
        tools_root_folder = None
    return folder_id, tools_root_folder

def build_tool_dependencies_folder( trans, folder_id, tool_dependencies, label='Tool dependencies', missing=False, new_install=False, reinstalling=False ):
    """Return a folder hierarchy containing tool dependencies."""
    # When we're in Galaxy (not the tool shed) and the tool dependencies are not installed or are in an error state, they are considered missing.  The tool
    # dependency status will be displayed only if a record exists for the tool dependency in the Galaxy database, but the tool dependency is not installed.
    # The value for new_install will be True only if the associated repository in being installed for the first time.  This value is used in setting the
    # container description.
    if tool_dependencies:
        tool_dependency_id = 0
        folder_id += 1
        tool_dependencies_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        folder = Folder( id=folder_id, key='tool_dependencies', label=label, parent=tool_dependencies_root_folder )
        if trans.webapp.name == 'galaxy':
            if new_install or reinstalling:
                folder.description = "repository tools require handling of these dependencies"
            elif missing and not new_install and not reinstalling:
                folder.description = 'click the name to install the missing dependency'
            else:
                folder.description = 'click the name to browse the dependency installation directory'
        tool_dependencies_root_folder.folders.append( folder )
        # Insert a header row.
        tool_dependency_id += 1
        if trans.webapp.name == 'galaxy':
            # Include the installation directory.
            tool_dependency = ToolDependency( id=tool_dependency_id,
                                              name='Name',
                                              version='Version',
                                              type='Type',
                                              install_dir='Install directory',
                                              readme=None,
                                              installation_status='Installation status',
                                              repository_id=None,
                                              tool_dependency_id=None,
                                              is_orphan=None )
        else:
            tool_dependency = ToolDependency( id=tool_dependency_id,
                                              name='Name',
                                              version='Version',
                                              type='Type',
                                              install_dir=None,
                                              readme=None,
                                              installation_status=None,
                                              repository_id=None,
                                              tool_dependency_id=None,
                                              is_orphan='Orphan' )
        folder.tool_dependencies.append( tool_dependency )
        is_orphan_description = "these dependencies may not be required by tools in this repository"
        for dependency_key, requirements_dict in tool_dependencies.items():
            tool_dependency_id += 1
            if dependency_key in [ 'set_environment' ]:
                for set_environment_dict in requirements_dict:
                    if trans.webapp.name == 'tool_shed':
                        is_orphan = set_environment_dict.get( 'is_orphan', False )
                    else:
                        # TODO: handle this is Galaxy
                        is_orphan = False
                    if is_orphan:
                        folder.description = is_orphan_description
                    name = set_environment_dict.get( 'name', None )
                    type = set_environment_dict[ 'type' ]
                    repository_id = set_environment_dict.get( 'repository_id', None )
                    td_id = set_environment_dict.get( 'tool_dependency_id', None )
                    if trans.webapp.name == 'galaxy':
                        installation_status = set_environment_dict.get( 'status', 'Never installed' )
                    else:
                        installation_status = None
                    tool_dependency = ToolDependency( id=tool_dependency_id,
                                                      name=name,
                                                      version=None,
                                                      type=type,
                                                      install_dir=None,
                                                      readme=None,
                                                      installation_status=installation_status,
                                                      repository_id=repository_id,
                                                      tool_dependency_id=td_id,
                                                      is_orphan=is_orphan )
                    folder.tool_dependencies.append( tool_dependency )
            else:
                if trans.webapp.name == 'tool_shed':
                    is_orphan = requirements_dict.get( 'is_orphan', False )
                else:
                    # TODO: handle this is Galaxy
                    is_orphan = False
                if is_orphan:
                    folder.description = is_orphan_description
                name = requirements_dict[ 'name' ]
                version = requirements_dict[ 'version' ]
                type = requirements_dict[ 'type' ]
                install_dir = requirements_dict.get( 'install_dir', None )
                repository_id = requirements_dict.get( 'repository_id', None )
                td_id = requirements_dict.get( 'tool_dependency_id', None )
                if trans.webapp.name == 'galaxy':
                    installation_status = requirements_dict.get( 'status', 'Never installed' )
                else:
                    installation_status = None
                tool_dependency = ToolDependency( id=tool_dependency_id,
                                                  name=name,
                                                  version=version,
                                                  type=type,
                                                  install_dir=install_dir,
                                                  readme=None,
                                                  installation_status=installation_status,
                                                  repository_id=repository_id,
                                                  tool_dependency_id=td_id,
                                                  is_orphan=is_orphan )
                folder.tool_dependencies.append( tool_dependency )
    else:
        tool_dependencies_root_folder = None
    return folder_id, tool_dependencies_root_folder

def build_workflows_folder( trans, folder_id, workflows, repository_metadata_id=None, repository_id=None, label='Workflows' ):
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
                                 workflow_name=workflow_dict[ 'name' ],
                                 steps=steps,
                                 format_version=workflow_dict[ 'format-version' ],
                                 annotation=workflow_dict[ 'annotation' ],
                                 repository_metadata_id=repository_metadata_id,
                                 repository_id=repository_id )
            folder.workflows.append( workflow )
    else:
        workflows_root_folder = None
    return folder_id, workflows_root_folder

def cast_empty_repository_dependency_folders( folder, repository_dependency_id ):
    """
    Change any empty folders contained within the repository dependencies container into a repository dependency since it has no repository dependencies
    of it's own.  This method is not used (and may not be needed), but here it is just in case.
    """
    if not folder.folders and not folder.repository_dependencies:
        repository_dependency_id += 1
        repository_dependency = folder.to_repository_dependency( repository_dependency_id )
        if not folder.parent.contains_repository_dependency( repository_dependency ):
            folder.parent.repository_dependencies.append( repository_dependency )
            folder.parent.folders.remove( folder )
    for sub_folder in folder.folders:
        return cast_empty_repository_dependency_folders( sub_folder, repository_dependency_id )
    return folder, repository_dependency_id

def generate_repository_dependencies_folder_label_from_key( repository_name, repository_owner, changeset_revision, key ):
    """Return a repository dependency label based on the repository dependency key."""
    if key_is_current_repositorys_key( repository_name, repository_owner, changeset_revision, key ):
        label = 'Repository dependencies'
    else:
        label = "Repository <b>%s</b> revision <b>%s</b> owned by <b>%s</b>" % ( repository_name, changeset_revision, repository_owner )
    return label

def generate_repository_dependencies_key_for_repository( toolshed_base_url, repository_name, repository_owner, changeset_revision ):
    # FIXME: assumes tool shed is current tool shed since repository dependencies across tool sheds is not yet supported.
    return '%s%s%s%s%s%s%s' % ( str( toolshed_base_url ).rstrip( '/' ),
                                STRSEP,
                                str( repository_name ),
                                STRSEP,
                                str( repository_owner ),
                                STRSEP,
                                str( changeset_revision ) )

def generate_tool_dependencies_key( name, version, type ):
    return '%s%s%s%s%s' % ( str( name ), STRSEP, str( version ), STRSEP, str( type ) )

def get_folder( folder, key ):
    if folder.key == key:
        return folder
    for sub_folder in folder.folders:
        return get_folder( sub_folder, key )
    return None

def get_components_from_key( key ):
    # FIXME: assumes tool shed is current tool shed since repository dependencies across tool sheds is not yet supported.
    items = key.split( STRSEP )
    toolshed_base_url = items[ 0 ]
    repository_name = items[ 1 ]
    repository_owner = items[ 2 ]
    changeset_revision = items[ 3 ]
    return toolshed_base_url, repository_name, repository_owner, changeset_revision

def handle_repository_dependencies_container_entry( trans, repository_dependencies_folder, rd_key, rd_value, folder_id, repository_dependency_id, folder_keys ):
    toolshed, repository_name, repository_owner, changeset_revision = get_components_from_key( rd_key )
    folder = get_folder( repository_dependencies_folder, rd_key )
    label = generate_repository_dependencies_folder_label_from_key( repository_name, repository_owner, changeset_revision, repository_dependencies_folder.key )
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
    if trans.webapp.name == 'galaxy':
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
        if trans.webapp.name == 'galaxy':
            if len( repository_dependency ) == 6:
                # We have two extra items in the tuple, repository.id and repository.status.
                tool_shed_repository_id = repository_dependency[ 4 ]
                installation_status = repository_dependency[ 5 ]
                repository_dependency = repository_dependency[ 0:4 ]
            else:
                tool_shed_repository_id = None
                installation_status = 'unknown'
        else:
            tool_shed_repository_id = None
            installation_status = None
        can_create_dependency = not is_subfolder_of( sub_folder, repository_dependency )
        if can_create_dependency:
            toolshed, repository_name, repository_owner, changeset_revision = repository_dependency
            repository_dependency_id += 1
            repository_dependency = RepositoryDependency( id=repository_dependency_id,
                                                          toolshed=toolshed,
                                                          repository_name=repository_name,
                                                          repository_owner=repository_owner,
                                                          changeset_revision=changeset_revision,
                                                          installation_status=installation_status,
                                                          tool_shed_repository_id=tool_shed_repository_id )
            # Insert the repository_dependency into the folder.
            sub_folder.repository_dependencies.append( repository_dependency )
    return repository_dependencies_folder, folder_id, repository_dependency_id

def is_subfolder_of( folder, repository_dependency ):
    toolshed, repository_name, repository_owner, changeset_revision = repository_dependency
    key = generate_repository_dependencies_key_for_repository( toolshed, repository_name, repository_owner, changeset_revision )
    for sub_folder in folder.folders:
        if key == sub_folder.key:
            return True
    return False

def key_is_current_repositorys_key( repository_name, repository_owner, changeset_revision, key ):
    toolshed_base_url, key_name, key_owner, key_changeset_revision = get_components_from_key( key )
    return repository_name == key_name and repository_owner == key_owner and changeset_revision == key_changeset_revision

def populate_repository_dependencies_container( trans, repository_dependencies_folder, repository_dependencies, folder_id, repository_dependency_id ):
    folder_keys = repository_dependencies.keys()
    for key, value in repository_dependencies.items():
        repository_dependencies_folder, folder_id, repository_dependency_id = \
            handle_repository_dependencies_container_entry( trans, repository_dependencies_folder, key, value, folder_id, repository_dependency_id, folder_keys )
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

def prune_repository_dependencies( folder ):
    """
    Since the object used to generate a repository dependencies container is a dictionary and not an odict() (it must be json-serialize-able), the
    order in which the dictionary is processed to create the container sometimes results in repository dependency entries in a folder that also
    includes the repository dependency as a sub-folder (if the repository dependency has it's own repository dependency).  This method will remove
    all repository dependencies from folder that are also sub-folders of folder.
    """
    repository_dependencies = [ rd for rd in folder.repository_dependencies ]
    for repository_dependency in repository_dependencies:
        listified_repository_dependency = repository_dependency.listify
        if is_subfolder_of( folder, listified_repository_dependency ):
            repository_dependencies.remove( repository_dependency )
    folder.repository_dependencies = repository_dependencies
    for sub_folder in folder.folders:
        return prune_repository_dependencies( sub_folder )
    return folder
    