import os, logging
from galaxy.web import url_for

log = logging.getLogger( __name__ )

# String separator
STRSEP = '__ESEP__'

class Folder( object ):
    """Container object."""
    def __init__( self, id=None, key=None, label=None ):
        self.id = id
        self.key = key
        self.label = label
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
        datatypes_root_folder = Folder( id=folder_id, key='root', label='root' )
        folder_id += 1
        folder = Folder( id=folder_id, key='datatypes', label=label )
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
        invalid_tools_root_folder = Folder( id=folder_id, key='root', label='root' )
        folder_id += 1
        folder = Folder( id=folder_id, key='invalid_tools', label=label )
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
        readme_id = 0
        folder_id += 1
        readme_files_root_folder = Folder( id=folder_id, key='root', label='root' )
        folder_id += 1
        readme_files_folder = Folder( id=folder_id, key='readme_files', label=label )
        readme_files_root_folder.folders.append( readme_files_folder )
        for readme_file_name, readme_file_text in readme_files_dict.items():
            readme_id += 1
            readme = ReadMe( id=readme_id,
                             name=readme_file_name,
                             text=readme_file_text )
            folder_id += 1
            folder = Folder( id=folder_id, key=readme.name, label=readme.name )
            folder.readme_files.append( readme )
            readme_files_folder.folders.append( folder )
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
        repository_dependencies_root_folder = Folder( id=folder_id, key='root', label='root' )
        folder_id += 1
        # Create the Repository dependencies folder and add it to the root folder.
        key = generate_repository_dependencies_key_for_repository( toolshed_base_url, repository_name, repository_owner, changeset_revision )
        repository_dependencies_folder = Folder( id=folder_id, key=key, label=label )
        repository_dependencies_root_folder.folders.append( repository_dependencies_folder )
        # Process the repository dependencies.
        for key, val in repository_dependencies.items():
            # Only create a new folder object if necessary.
            folder = get_folder( repository_dependencies_root_folder, key )
            if not folder:
                # Create a new folder.
                folder_id += 1
                label = generate_repository_dependencies_folder_label_from_key( repository_name, repository_owner, changeset_revision, key )
                folder = Folder( id=folder_id, key=key, label=label )
            for repository_dependency_tup in val:
                toolshed, name, owner, changeset_revision = repository_dependency_tup
                if not is_folder( repository_dependencies.keys(), toolshed, name, owner, changeset_revision ):
                    # Create a new repository_dependency.
                    repository_dependency_id += 1
                    repository_dependency = RepositoryDependency( id=repository_dependency_id,
                                                                  toolshed=toolshed,
                                                                  repository_name=name,
                                                                  repository_owner=owner,
                                                                  changeset_revision=changeset_revision )
                    # Insert the repository_dependency into the folder.
                    folder.repository_dependencies.append( repository_dependency )
            if not get_folder( repository_dependencies_folder, key ):
                # Insert the folder into the list.
                repository_dependencies_folder.folders.append( folder )
    else:
        repository_dependencies_root_folder = None
    return folder_id, repository_dependencies_root_folder
def build_tools_folder( folder_id, tool_dicts, repository, changeset_revision, valid=True, label='Valid tools' ):
    """Return a folder hierarchy containing valid tools."""
    if tool_dicts:
        tool_id = 0
        folder_id += 1
        tools_root_folder = Folder( id=folder_id, key='root', label='root' )
        folder_id += 1
        folder = Folder( id=folder_id, key='tools', label=label )
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
        tool_dependencies_root_folder = Folder( id=folder_id, key='root', label='root' )
        folder_id += 1
        folder = Folder( id=folder_id, key='tool_dependencies', label=label )
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
        workflows_root_folder = Folder( id=folder_id, key='root', label='root' )
        folder_id += 1
        folder = Folder( id=folder_id, key='workflows', label=label )
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
def generate_repository_dependencies_folder_label_from_key( repository_name, repository_owner, changeset_revision, key ):
    """Return a repository dependency label based on the repository dependency key."""
    if key_is_current_repositorys_key( repository_name, repository_owner, changeset_revision, key ):
        label = 'Repository dependencies'
    else:
        toolshed_base_url, name, owner, revision = get_components_from_key( key )
        label = "Repository <b>%s</b> revision <b>%s</b> owned by <b>%s</b>" % ( name, revision, owner )
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
def is_folder( folder_keys, toolshed_base_url, repository_name, repository_owner, changeset_revision ):
    key = '%s%s%s%s%s%s%s' % ( toolshed_base_url, STRSEP, repository_name, STRSEP, repository_owner, STRSEP, changeset_revision )
    return key in folder_keys
def key_is_current_repositorys_key( repository_name, repository_owner, changeset_revision, key ):
    toolshed_base_url, key_name, key_owner, key_changeset_revision = get_components_from_key( key )
    return repository_name == key_name and repository_owner == key_owner and changeset_revision == key_changeset_revision
    