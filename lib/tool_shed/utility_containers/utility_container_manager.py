import logging

from galaxy import util
from tool_shed.util import common_util
from tool_shed.util import container_util
from tool_shed.util import repository_util

log = logging.getLogger( __name__ )


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


class InvalidDataManager( object ):
    """Invalid data Manager object"""

    def __init__( self, id=None, index=None, error=None ):
        self.id = id
        self.index = index
        self.error = error


class InvalidTool( object ):
    """Invalid tool object"""

    def __init__( self, id=None, tool_config=None, repository_id=None, changeset_revision=None, repository_installation_status=None ):
        self.id = id
        self.tool_config = tool_config
        self.repository_id = repository_id
        self.changeset_revision = changeset_revision
        self.repository_installation_status = repository_installation_status


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


class Workflow( object ):
    """Workflow object."""

    def __init__( self, id=None, workflow_name=None, steps=None, format_version=None, annotation=None,
                  repository_metadata_id=None, repository_id=None ):
        """
        When rendered in the tool shed, repository_metadata_id will have a value and repository_id will
        be None.  When rendered in Galaxy, repository_id will have a value and repository_metadata_id will
        be None.
        """
        self.id = id
        self.workflow_name = workflow_name
        self.steps = steps
        self.format_version = format_version
        self.annotation = annotation
        self.repository_metadata_id = repository_metadata_id
        self.repository_id = repository_id


class UtilityContainerManager( object ):

    def __init__( self, app ):
        self.app = app

    def build_data_managers_folder( self, folder_id, data_managers, label=None ):
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
            for data_manager_dict in data_managers.values():
                data_manager_id += 1
                try:
                    name = data_manager_dict.get( 'name', '' )
                    version = data_manager_dict.get( 'version', '' )
                    data_tables = ", ".join( data_manager_dict.get( 'data_tables', '' ) )
                except Exception as e:
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

    def build_datatypes_folder( self, folder_id, datatypes, label='Datatypes' ):
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
                except Exception as e:
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

    def build_invalid_data_managers_folder( self, folder_id, data_managers, error_messages=None, label=None ):
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
            for data_manager_dict in data_managers:
                data_manager_id += 1
                data_manager = InvalidDataManager( id=data_manager_id,
                                                   index=data_manager_dict.get( 'index', 0 ) + 1,
                                                   error=data_manager_dict.get( 'error_message', '' ) )
                folder.invalid_data_managers.append( data_manager )
        else:
            data_managers_root_folder = None
        return folder_id, data_managers_root_folder

    def build_invalid_tools_folder( self, folder_id, invalid_tool_configs, changeset_revision, repository=None,
                                    label='Invalid tools' ):
        """Return a folder hierarchy containing invalid tools."""
        # TODO: Should we display invalid tools on the tool panel selection page when installing the
        # repository into Galaxy?
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
                    if self.app.name == 'galaxy':
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

    def build_readme_files_folder( self, folder_id, readme_files_dict, label='Readme files' ):
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

    def build_repository_dependencies_folder( self, folder_id, repository_dependencies, label='Repository dependencies',
                                              installed=False ):
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
                self.populate_repository_dependencies_container( repository_dependencies_folder,
                                                                 repository_dependencies,
                                                                 folder_id,
                                                                 repository_dependency_id )
            repository_dependencies_folder = self.prune_repository_dependencies( repository_dependencies_folder )
        else:
            repository_dependencies_root_folder = None
        return folder_id, repository_dependencies_root_folder

    def build_tools_folder( self, folder_id, tool_dicts, repository, changeset_revision, valid=True, label='Valid tools' ):
        """Return a folder hierarchy containing valid tools."""
        if tool_dicts:
            container_object_tool_id = 0
            folder_id += 1
            tools_root_folder = Folder( id=folder_id, key='root', label='root', parent=None )
            folder_id += 1
            folder = Folder( id=folder_id, key='tools', label=label, parent=tools_root_folder )
            if self.app.name == 'galaxy':
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
                if self.app.name == 'galaxy':
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
                        except Exception as e:
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
                except Exception as e:
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

    def build_tool_dependencies_folder( self, folder_id, tool_dependencies, label='Tool dependencies', missing=False,
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
            if self.app.name == 'galaxy':
                if new_install or reinstalling:
                    folder.description = "repository tools require handling of these dependencies"
                elif missing and not new_install and not reinstalling:
                    folder.description = 'click the name to install the missing dependency'
                else:
                    folder.description = 'click the name to browse the dependency installation directory'
            tool_dependencies_root_folder.folders.append( folder )
            # Insert a header row.
            tool_dependency_id += 1
            if self.app.name == 'galaxy':
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
            for dependency_key, requirements_dict in tool_dependencies.items():
                tool_dependency_id += 1
                if dependency_key in [ 'set_environment' ]:
                    for set_environment_dict in requirements_dict:
                        try:
                            name = set_environment_dict.get( 'name', None )
                            type = set_environment_dict[ 'type' ]
                            repository_id = set_environment_dict.get( 'repository_id', None )
                            td_id = set_environment_dict.get( 'tool_dependency_id', None )
                        except Exception as e:
                            name = str( e )
                            type = 'unknown'
                            repository_id = 'unknown'
                            td_id = 'unknown'
                        if self.app.name == 'galaxy':
                            try:
                                installation_status = set_environment_dict.get( 'status', 'Never installed' )
                            except Exception as e:
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
                    except Exception as e:
                        name = str( e )
                        version = 'unknown'
                        type = 'unknown'
                        repository_id = 'unknown'
                        td_id = 'unknown'
                    if self.app.name == 'galaxy':
                        try:
                            installation_status = requirements_dict.get( 'status', 'Never installed' )
                        except Exception as e:
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

    def build_workflows_folder( self, folder_id, workflows, repository_metadata_id=None, repository_id=None,
                                label='Workflows' ):
        """
        Return a folder hierarchy containing workflow objects for each workflow dictionary in the
        received workflows list.  When this method is called from the tool shed, repository_metadata_id
        will have a value and repository_id will be None.  When this method is called from Galaxy,
        repository_id will have a value only if the repository is not currenlty being installed and
        repository_metadata_id will be None.
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
                workflow_dict = workflow_tup[ 1 ]
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

    def generate_repository_dependencies_folder_label_from_key( self, repository_name, repository_owner, changeset_revision,
                                                                prior_installation_required, only_if_compiling_contained_td, key ):
        """Return a repository dependency label based on the repository dependency key."""
        if self.key_is_current_repositorys_key( repository_name,
                                                repository_owner,
                                                changeset_revision,
                                                prior_installation_required,
                                                only_if_compiling_contained_td, key ):
            label = 'Repository dependencies'
        else:
            if util.asbool( prior_installation_required ):
                prior_installation_required_str = " <i>(prior install required)</i>"
            else:
                prior_installation_required_str = ""
            label = "Repository <b>%s</b> revision <b>%s</b> owned by <b>%s</b>%s" % \
                ( repository_name, changeset_revision, repository_owner, prior_installation_required_str )
        return label

    def get_components_from_repository_dependency_for_installed_repository( self, repository_dependency ):
        """
        Parse a repository dependency and return components necessary for proper display
        in Galaxy on the Manage repository page.
        """
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
            repository_dependency = \
                [ tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td ]
        elif len( repository_dependency ) == 8:
            # We have a repository dependency tuple that includes both a prior_installation_required value
            # and a only_if_compiling_contained_td value.
            tool_shed_repository_id = repository_dependency[ 6 ]
            installation_status = repository_dependency[ 7 ]
            repository_dependency = repository_dependency[ 0:6 ]
        else:
            tool_shed_repository_id = None
            installation_status = 'unknown'
        if tool_shed_repository_id:
            tool_shed_repository = repository_util.get_tool_shed_repository_by_id( self.app,
                                                                                   self.app.security.encode_id( tool_shed_repository_id ) )
            if tool_shed_repository:
                if tool_shed_repository.missing_repository_dependencies:
                    installation_status = '%s, missing repository dependencies' % installation_status
                elif tool_shed_repository.missing_tool_dependencies:
                    installation_status = '%s, missing tool dependencies' % installation_status
        return tool_shed_repository_id, installation_status, repository_dependency

    def get_folder( self, folder, key ):
        if folder.key == key:
            return folder
        for sub_folder in folder.folders:
            return self.get_folder( sub_folder, key )
        return None

    def handle_repository_dependencies_container_entry( self, repository_dependencies_folder, rd_key, rd_value, folder_id,
                                                        repository_dependency_id, folder_keys ):
        repository_components_tuple = container_util.get_components_from_key( rd_key )
        components_list = repository_util.extract_components_from_tuple( repository_components_tuple )
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
        folder = self.get_folder( repository_dependencies_folder, rd_key )
        label = self.generate_repository_dependencies_folder_label_from_key( repository_name,
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
        if self.app.name == 'galaxy':
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
            if self.app.name == 'galaxy':
                tool_shed_repository_id, installation_status, repository_dependency = \
                    self.get_components_from_repository_dependency_for_installed_repository( repository_dependency )
            else:
                tool_shed_repository_id = None
                installation_status = None
            can_create_dependency = not self.is_subfolder_of( sub_folder, repository_dependency )
            if can_create_dependency:
                toolshed, repository_name, repository_owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
                    common_util.parse_repository_dependency_tuple( repository_dependency )
                repository_dependency_id += 1
                repository_dependency = RepositoryDependency( id=repository_dependency_id,
                                                              toolshed=toolshed,
                                                              repository_name=repository_name,
                                                              repository_owner=repository_owner,
                                                              changeset_revision=changeset_revision,
                                                              prior_installation_required=util.asbool( prior_installation_required ),
                                                              only_if_compiling_contained_td=util.asbool( only_if_compiling_contained_td ),
                                                              installation_status=installation_status,
                                                              tool_shed_repository_id=tool_shed_repository_id )
                # Insert the repository_dependency into the folder.
                sub_folder.repository_dependencies.append( repository_dependency )
        return repository_dependencies_folder, folder_id, repository_dependency_id

    def is_subfolder_of( self, folder, repository_dependency ):
        toolshed, repository_name, repository_owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
            common_util.parse_repository_dependency_tuple( repository_dependency )
        key = container_util.generate_repository_dependencies_key_for_repository( toolshed,
                                                                                  repository_name,
                                                                                  repository_owner,
                                                                                  changeset_revision,
                                                                                  prior_installation_required,
                                                                                  only_if_compiling_contained_td )
        for sub_folder in folder.folders:
            if key == sub_folder.key:
                return True
        return False

    def key_is_current_repositorys_key( self, repository_name, repository_owner, changeset_revision,
                                        prior_installation_required, only_if_compiling_contained_td, key ):
        repository_components_tuple = container_util.get_components_from_key( key )
        components_list = repository_util.extract_components_from_tuple( repository_components_tuple )
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
        if ( repository_name == key_name and
             repository_owner == key_owner and
             changeset_revision == key_changeset_revision and
             prior_installation_required == key_prior_installation_required and
             only_if_compiling_contained_td == key_only_if_compiling_contained_td ):
            return True
        return False

    def populate_repository_dependencies_container( self, repository_dependencies_folder, repository_dependencies, folder_id,
                                                    repository_dependency_id ):
        folder_keys = []
        for key in repository_dependencies.keys():
            if key not in folder_keys:
                folder_keys.append( key )
        for key, value in repository_dependencies.items():
            repository_dependencies_folder, folder_id, repository_dependency_id = \
                self.handle_repository_dependencies_container_entry( repository_dependencies_folder,
                                                                     key,
                                                                     value,
                                                                     folder_id,
                                                                     repository_dependency_id,
                                                                     folder_keys )
        return repository_dependencies_folder, folder_id, repository_dependency_id

    def prune_folder( self, folder, repository_dependency ):
        listified_repository_dependency = repository_dependency.listify
        if self.is_subfolder_of( folder, listified_repository_dependency ):
            folder.repository_dependencies.remove( repository_dependency )

    def prune_repository_dependencies( self, folder ):
        """
        Since the object used to generate a repository dependencies container is a dictionary
        and not an odict() (it must be json-serialize-able), the order in which the dictionary
        is processed to create the container sometimes results in repository dependency entries
        in a folder that also includes the repository dependency as a sub-folder (if the repository
        dependency has its own repository dependency).  This method will remove all repository
        dependencies from folder that are also sub-folders of folder.
        """
        repository_dependencies = [ rd for rd in folder.repository_dependencies ]
        for repository_dependency in repository_dependencies:
            self.prune_folder( folder, repository_dependency )
        for sub_folder in folder.folders:
            return self.prune_repository_dependencies( sub_folder )
        return folder
