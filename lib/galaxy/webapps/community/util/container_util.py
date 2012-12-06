import os, logging

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
        self.invalid_tools = []
        self.valid_tools = []
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

class Datatype( object ):
    """Datatype object"""
    def __init__( self, id=None, extension=None, type=None, mimetype=None, subclass=None ):
        self.id = id
        self.extension = extension
        self.type = type
        self.mimetype = mimetype
        self.subclass = subclass

class InvalidTool( object ):
    """Invalid tool object"""
    def __init__( self, id=None, tool_config=None, repository_id=None, changeset_revision=None ):
        self.id = id
        self.tool_config = tool_config
        self.repository_id = repository_id
        self.changeset_revision = changeset_revision

class ReadMe( object ):
    """Readme text object"""
    def __init__( self, id=None, name=None, text=None ):
        self.id = id
        self.name = name
        self.text = text

class RepositoryDependency( object ):
    """Repository dependency object"""
    def __init__( self, id=None, toolshed=None, repository_name=None, repository_owner=None, changeset_revision=None ):
        self.id = id
        self.toolshed = toolshed
        self.repository_name = repository_name
        self.repository_owner = repository_owner
        self.changeset_revision = changeset_revision
    @property
    def listify( self ):
        return [ self.toolshed, self.repository_name, self.repository_owner, self.changeset_revision ]

class Tool( object ):
    """Tool object"""
    def __init__( self, id=None, tool_config=None, tool_id=None, name=None, description=None, version=None, requirements=None,
                  repository_id=None, changeset_revision=None ):
        self.id = id
        self.tool_config = tool_config
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.version = version
        self.requirements = requirements
        self.repository_id = repository_id
        self.changeset_revision = changeset_revision

class ToolDependency( object ):
    """Tool dependency object"""
    def __init__( self, id=None, name=None, version=None, type=None, install_dir=None, readme=None ):
        self.id = id
        self.name = name
        self.version = version
        self.type = type
        self.install_dir = install_dir
        self.readme = readme

class Workflow( object ):
    """Workflow object"""
    def __init__( self, id=None, repository_metadata_id=None, workflow_name=None, steps=None, format_version=None, annotation=None ):
        self.id = id
        self.repository_metadata_id = repository_metadata_id
        self.workflow_name = workflow_name
        self.steps = steps
        self.format_version = format_version
        self.annotation = annotation

def build_datatypes_folder( folder_id, datatypes, label='Datatypes' ):
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
            datatype_id += 1
            datatype = Datatype( id=datatype_id,
                                 extension=datatypes_dict.get( 'extension', '' ),
                                 type=datatypes_dict.get( 'dtype', '' ),
                                 mimetype=datatypes_dict.get( 'mimetype', '' ),
                                 subclass=datatypes_dict.get( 'subclass', '' ) )
            folder.datatypes.append( datatype )
    else:
        datatypes_root_folder = None
    return folder_id, datatypes_root_folder
def build_invalid_tools_folder( folder_id, invalid_tool_configs, changeset_revision, repository=None, label='Invalid tools' ):
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
            else:
                repository_id = None
            invalid_tool = InvalidTool( id=invalid_tool_id,
                                        tool_config=invalid_tool_config,
                                        repository_id=repository_id,
                                        changeset_revision=changeset_revision )
            folder.invalid_tools.append( invalid_tool )
    else:
        invalid_tools_root_folder = None
    return folder_id, invalid_tools_root_folder
def build_readme_files_folder( folder_id, readme_files_dict, label='Readme files' ):
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
def build_repository_dependencies_folder( toolshed_base_url, repository_name, repository_owner, changeset_revision, folder_id, repository_dependencies,
                                          label='Repository dependencies' ):
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
        # The remaining keys in repository_dependencies should all be folders.
        folder_keys = repository_dependencies.keys()
        # If repository_dependencies_folder_key is an entry in repository_dependencies, process it first.
        if repository_dependencies_folder_key in repository_dependencies:
            val = repository_dependencies[ repository_dependencies_folder_key ]
            repository_dependencies_folder, folder_id, repository_dependency_id = handle_repository_dependencies_entry( repository_dependencies_root_folder,
                                                                                                                        repository_dependencies_folder,
                                                                                                                        repository_dependencies_folder_key,
                                                                                                                        folder_keys,
                                                                                                                        folder_id,
                                                                                                                        repository_dependency_id,
                                                                                                                        repository_name,
                                                                                                                        repository_owner,
                                                                                                                        changeset_revision,
                                                                                                                        repository_dependencies_folder_key,
                                                                                                                        val )
            del repository_dependencies[ repository_dependencies_folder_key ]
        for key, val in repository_dependencies.items():
            repository_dependencies_folder, folder_id, repository_dependency_id = handle_repository_dependencies_entry( repository_dependencies_root_folder,
                                                                                                                        repository_dependencies_folder,
                                                                                                                        repository_dependencies_folder_key,
                                                                                                                        folder_keys,
                                                                                                                        folder_id,
                                                                                                                        repository_dependency_id,
                                                                                                                        repository_name,
                                                                                                                        repository_owner,
                                                                                                                        changeset_revision,
                                                                                                                        key,
                                                                                                                        val )
        # Cast empty folders to be repository dependencies.
        repository_dependencies_folder, repository_dependency_id = cast_empty_repository_dependency_folders( repository_dependencies_folder,
                                                                                                             repository_dependency_id )
        # Remove repository_dependencies that are also folders, and coerce empty folders into repository dependencies.
    else:
        repository_dependencies_root_folder = None
    return folder_id, repository_dependencies_root_folder
def build_tools_folder( folder_id, tool_dicts, repository, changeset_revision, valid=True, label='Valid tools' ):
    """Return a folder hierarchy containing valid tools."""
    if tool_dicts:
        tool_id = 0
        folder_id += 1
        tools_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        folder = Folder( id=folder_id, key='tools', label=label, parent=tools_root_folder )
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
                         repository_id=repository.id,
                         changeset_revision=changeset_revision )
            folder.valid_tools.append( tool )
    else:
        tools_root_folder = None
    return folder_id, tools_root_folder
def build_tool_dependencies_folder( folder_id, tool_dependencies, label='Tool dependencies', for_galaxy=False ):
    """Return a folder hierarchy containing tool dependencies."""
    if tool_dependencies:
        tool_dependency_id = 0
        folder_id += 1
        tool_dependencies_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
        folder_id += 1
        folder = Folder( id=folder_id, key='tool_dependencies', label=label, parent=tool_dependencies_root_folder )
        tool_dependencies_root_folder.folders.append( folder )
        # Insert a header row.
        tool_dependency_id += 1
        if for_galaxy:
            # Include the installation directory.
            tool_dependency = ToolDependency( id=tool_dependency_id,
                                              name='Name',
                                              version='Version',
                                              type='Type',
                                              install_dir='Install directory' )
        else:
            tool_dependency = ToolDependency( id=tool_dependency_id,
                                              name='Name',
                                              version='Version',
                                              type='Type' )
        folder.tool_dependencies.append( tool_dependency )
        for dependency_key, requirements_dict in tool_dependencies.items():
            tool_dependency_id += 1
            if dependency_key == 'set_environment':
                for set_environment_dict in requirements_dict:
                    name = set_environment_dict[ 'name' ]
                    type = set_environment_dict[ 'type' ]
                    tool_dependency = ToolDependency( id=tool_dependency_id,
                                                      name=name,
                                                      type=type )
                    folder.tool_dependencies.append( tool_dependency )
            else:
                name = requirements_dict[ 'name' ]
                version = requirements_dict[ 'version' ]
                type = requirements_dict[ 'type' ]
                install_dir = requirements_dict.get( 'install_dir', None )
                tool_dependency = ToolDependency( id=tool_dependency_id,
                                                  name=name,
                                                  version=version,
                                                  type=type,
                                                  install_dir=install_dir )
                folder.tool_dependencies.append( tool_dependency )
    else:
        tool_dependencies_root_folder = None
    return folder_id, tool_dependencies_root_folder
def build_workflows_folder( folder_id, workflows, repository_metadata, label='Workflows' ):
    """Return a folder hierarchy containing invalid tools."""
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
                             repository_metadata_id=None,
                             workflow_name='Name',
                             steps='steps',
                             format_version='format-version',
                             annotation='annotation' )
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
                                 repository_metadata_id=repository_metadata.id,
                                 workflow_name=workflow_dict[ 'name' ],
                                 steps=steps,
                                 format_version=workflow_dict[ 'format-version' ],
                                 annotation=workflow_dict[ 'annotation' ] )
            folder.workflows.append( workflow )
    else:
        workflows_root_folder = None
    return folder_id, workflows_root_folder
def cast_empty_repository_dependency_folders( folder, repository_dependency_id ):
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
        #toolshed_base_url, name, owner, revision = get_components_from_key( key )
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
def get_folder( folder, key ):
    if folder and folder.key == key:
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
def handle_repository_dependencies_entry( repository_dependencies_root_folder, repository_dependencies_folder, repository_dependencies_folder_key,
                                          folder_keys, folder_id, repository_dependency_id, repository_name, repository_owner, changeset_revision,
                                          key, val ):
    # Only create a new folder object if necessary.
    folder = get_folder( repository_dependencies_root_folder, key )
    if not folder:
        folder_id += 1
        label = generate_repository_dependencies_folder_label_from_key( repository_name, repository_owner, changeset_revision, key )
        folder = Folder( id=folder_id, key=key, label=label, parent=repository_dependencies_folder )
    for repository_dependency_tup in val:
        toolshed, name, owner, changeset_revision = repository_dependency_tup
        if is_root_repository( repository_dependencies_folder_key, toolshed, name, owner ):
            # Do not include repository dependencies that point to a revision within the same repository.
            continue
        if is_or_should_be_folder( folder_keys, toolshed, name, owner, changeset_revision ):
            check_folder_key = generate_repository_dependencies_key_for_repository( toolshed, name, owner, changeset_revision )
            if get_folder( repository_dependencies_root_folder, check_folder_key ):
                continue
            else:
                # Create a new folder, which may be populated later.
                folder_id += 1
                label = generate_repository_dependencies_folder_label_from_key( name, owner, changeset_revision, key )
                sub_folder = Folder( id=folder_id, key=check_folder_key, label=label, parent=repository_dependencies_folder )
                folder.folders.append( sub_folder )
        else:
            repository_dependency_id += 1
            repository_dependency = RepositoryDependency( id=repository_dependency_id,
                                                          toolshed=toolshed,
                                                          repository_name=name,
                                                          repository_owner=owner,
                                                          changeset_revision=changeset_revision )
            # Insert the repository_dependency into the folder.
            folder.repository_dependencies.append( repository_dependency )
    if not get_folder( repository_dependencies_folder, folder.key ):
        if folder.folders:
            # Insert the folder into the list.
            repository_dependencies_folder.folders.append( folder )
    return repository_dependencies_folder, folder_id, repository_dependency_id
def is_or_should_be_folder( folder_keys, toolshed, repository_name, repository_owner, changeset_revision ):
    key = '%s%s%s%s%s%s%s' % ( toolshed, STRSEP, repository_name, STRSEP, repository_owner, STRSEP, changeset_revision )
    return key in folder_keys
def is_root_repository( repository_dependencies_folder_key, toolshed, repository_name, repository_owner ):
    # Return True if a repository dependency points to a revision within it's own repository.
    repository_dependencies_folder_tup = repository_dependencies_folder_key.split( STRSEP )
    rdf_toolshed, rdf_repository_name, rdf_repository_owner, rdf_changeset_revision = repository_dependencies_folder_tup
    return rdf_toolshed == toolshed and rdf_repository_name == repository_name and rdf_repository_owner == repository_owner
def key_is_current_repositorys_key( repository_name, repository_owner, changeset_revision, key ):
    toolshed_base_url, key_name, key_owner, key_changeset_revision = get_components_from_key( key )
    return repository_name == key_name and repository_owner == key_owner and changeset_revision == key_changeset_revision
def print_folders( pad, folder ):
    # For debugging...
    pad_str = ''
    for i in range( 1, pad ):
        pad_str += ' '
    print '%s%s' % ( pad_str, folder.key )
    for sub_folder in folder.folders:
        print_folders( pad+5, sub_folder )
    