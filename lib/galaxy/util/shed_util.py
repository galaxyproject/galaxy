import sys, os, tempfile, shutil, subprocess, logging, string, urllib2
from datetime import date, datetime, timedelta
from time import strftime, gmtime
from galaxy import util
from galaxy.datatypes.checkers import *
from galaxy.util.json import *
from galaxy.tools.search import ToolBoxSearch
from galaxy.model.orm import *

from galaxy import eggs
import pkg_resources

pkg_resources.require( 'mercurial' )
from mercurial import ui, commands

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree, ElementInclude
from elementtree.ElementTree import Element, SubElement

log = logging.getLogger( __name__ )

# Characters that must be html escaped
MAPPED_CHARS = { '>' :'&gt;', 
                 '<' :'&lt;',
                 '"' : '&quot;',
                 '&' : '&amp;',
                 '\'' : '&apos;' }
VALID_CHARS = set( string.letters + string.digits + "'\"-=_.()/+*^,:?!#[]%\\$@;{}" )

class ShedCounter( object ):
    def __init__( self, model ):
        self.model = model
        self.generation_time = strftime( "%b %d, %Y", gmtime() )
        self.repositories = 0
        self.new_repositories = 0
        self.deleted_repositories = 0
        self.invalid_tools = 0
        self.valid_tools = 0
        self.workflows = 0
        self.proprietary_datatypes = 0
        self.total_clones = 0
        self.generate_statistics()
    @property
    def sa_session( self ):
        """Returns a SQLAlchemy session"""
        return self.model.context
    def generate_statistics( self ):
        self.repositories = 0
        self.new_repositories = 0
        self.deleted_repositories = 0
        self.invalid_tools = 0
        self.valid_tools = 0
        self.workflows = 0
        self.proprietary_datatypes = 0
        self.total_clones = 0
        for repository in self.sa_session.query( self.model.Repository ):
            self.repositories += 1
            self.total_clones += repository.times_downloaded
            is_deleted = repository.deleted
            is_new = repository.is_new
            if is_deleted and is_new:
                self.deleted_repositories += 1
                self.new_repositories += 1
            elif is_deleted:
                self.deleted_repositories += 1
            elif is_new:
                self.new_repositories += 1
            else:
                processed_guids = []
                processed_invalid_tool_configs = []
                processed_relative_workflow_paths = []
                processed_datatypes = []
                for downloadable_revision in repository.downloadable_revisions:
                    metadata = downloadable_revision.metadata
                    if 'tools' in metadata:
                        tool_dicts = metadata[ 'tools' ]
                        for tool_dict in tool_dicts:
                            if 'guid' in tool_dict:
                                guid = tool_dict[ 'guid' ]
                                if guid not in processed_guids:
                                    self.valid_tools += 1
                                    processed_guids.append( guid )
                    if 'invalid_tools' in metadata:
                        invalid_tool_configs = metadata[ 'invalid_tools' ]
                        for invalid_tool_config in invalid_tool_configs:
                            if invalid_tool_config not in processed_invalid_tool_configs:
                                self.invalid_tools += 1
                                processed_invalid_tool_configs.append( invalid_tool_config )
                    if 'datatypes' in metadata:
                        datatypes = metadata[ 'datatypes' ]
                        for datatypes_dict in datatypes:
                            if 'extension' in datatypes_dict:
                                extension = datatypes_dict[ 'extension' ]
                                if extension not in processed_datatypes:
                                    self.proprietary_datatypes += 1
                                    processed_datatypes.append( extension )
                    if 'workflows' in metadata:
                        workflows = metadata[ 'workflows' ]
                        for workflow_tup in workflows:
                            relative_path, exported_workflow_dict = workflow_tup
                            if relative_path not in processed_relative_workflow_paths:
                                self.workflows += 1
                                processed_relative_workflow_paths.append( relative_path )
        self.generation_time = strftime( "%b %d, %Y", gmtime() )
def add_to_shed_tool_config( app, shed_tool_conf_dict, elem_list ):
    # A tool shed repository is being installed so change the shed_tool_conf file.  Parse the config file to generate the entire list
    # of config_elems instead of using the in-memory list since it will be a subset of the entire list if one or more repositories have
    # been deactivated.
    shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
    tool_path = shed_tool_conf_dict[ 'tool_path' ]
    config_elems = []
    tree = util.parse_xml( shed_tool_conf )
    root = tree.getroot()
    for elem in root:
        config_elems.append( elem )
    # Add the elements to the in-memory list of config_elems.
    for elem_entry in elem_list:
        config_elems.append( elem_entry )
    # Persist the altered shed_tool_config file.
    config_elems_to_xml_file( app, config_elems, shed_tool_conf, tool_path )
def add_to_tool_panel( app, repository_name, repository_clone_url, changeset_revision, repository_tools_tups, owner, shed_tool_conf, tool_panel_dict,
                       new_install=True ):
    """A tool shed repository is being installed or updated so handle tool panel alterations accordingly."""
    # We need to change the in-memory version and the file system version of the shed_tool_conf file.
    index, shed_tool_conf_dict = get_shed_tool_conf_dict( app, shed_tool_conf )
    tool_path = shed_tool_conf_dict[ 'tool_path' ]
    # Generate the list of ElementTree Element objects for each section or tool.
    elem_list = generate_tool_panel_elem_list( repository_name,
                                               repository_clone_url,
                                               changeset_revision,
                                               tool_panel_dict,
                                               repository_tools_tups,
                                               owner=owner )
    if new_install:
        # Add the new elements to the shed_tool_conf file on disk.
        add_to_shed_tool_config( app, shed_tool_conf_dict, elem_list )
        # Use the new elements to add entries to the 
    config_elems = shed_tool_conf_dict[ 'config_elems' ]
    for config_elem in elem_list:
        # Add the new elements to the in-memory list of config_elems.
        config_elems.append( config_elem )
        # Load the tools into the in-memory tool panel.
        if config_elem.tag == 'section':
            app.toolbox.load_section_tag_set( config_elem, tool_path, load_panel_dict=True )
        elif config_elem.tag == 'workflow':
            app.toolbox.load_workflow_tag_set( config_elem, app.toolbox.tool_panel, app.toolbox.integrated_tool_panel, load_panel_dict=True )
        elif config_elem.tag == 'tool':
            guid = config_elem.get( 'guid' )
            app.toolbox.load_tool_tag_set( config_elem,
                                           app.toolbox.tool_panel,
                                           app.toolbox.integrated_tool_panel,
                                           tool_path,
                                           load_panel_dict=True,
                                           guid=guid )
    # Replace the old list of in-memory config_elems with the new list for this shed_tool_conf_dict.
    shed_tool_conf_dict[ 'config_elems' ] = config_elems
    app.toolbox.shed_tool_confs[ index ] = shed_tool_conf_dict
    # Write the current in-memory version of the integrated_tool_panel.xml file to disk.
    app.toolbox.write_integrated_tool_panel_config_file()
    if app.toolbox_search.enabled:
        # If search support for tools is enabled, index the new installed tools.
        app.toolbox_search = ToolBoxSearch( app.toolbox )
def alter_config_and_load_prorietary_datatypes( app, datatypes_config, relative_install_dir, deactivate=False, override=True ):
    """
    Parse a proprietary datatypes config (a datatypes_conf.xml file included in an installed tool shed repository) and
    add information to appropriate element attributes that will enable proprietary datatype class modules, datatypes converters
    and display applications to be discovered and properly imported by the datatypes registry.  The value of override will
    be False when a tool shed repository is being installed.  Since installation is occurring after the datatypes registry
    has been initialized, the registry's contents cannot be overridden by conflicting data types.
    """
    tree = util.parse_xml( datatypes_config )
    datatypes_config_root = tree.getroot()
    # Path to datatype converters
    converter_path = None
    # Path to datatype display applications
    display_path = None
    relative_path_to_datatype_file_name = None
    datatype_files = datatypes_config_root.find( 'datatype_files' )
    datatype_class_modules = []
    if datatype_files:
        # The <datatype_files> tag set contains any number of <datatype_file> tags.
        # <datatype_files>
        #    <datatype_file name="gmap.py"/>
        #    <datatype_file name="metagenomics.py"/>
        # </datatype_files>
        # We'll add attributes to the datatype tag sets so that the modules can be properly imported by the datatypes registry.
        for elem in datatype_files.findall( 'datatype_file' ):
            datatype_file_name = elem.get( 'name', None )
            if datatype_file_name:
                # Find the file in the installed repository.
                for root, dirs, files in os.walk( relative_install_dir ):
                    if root.find( '.hg' ) < 0:
                        for name in files:
                            if name == datatype_file_name:
                                datatype_class_modules.append( os.path.join( root, name ) )
                                break
                break
        if datatype_class_modules:
            registration = datatypes_config_root.find( 'registration' )
            converter_path, display_path = get_converter_and_display_paths( registration, relative_install_dir )
            if converter_path:
                registration.attrib[ 'proprietary_converter_path' ] = converter_path
            if display_path:
                registration.attrib[ 'proprietary_display_path' ] = display_path
            for relative_path_to_datatype_file_name in datatype_class_modules:
                relative_head, relative_tail = os.path.split( relative_path_to_datatype_file_name )
                for elem in registration.findall( 'datatype' ):
                    # Handle 'type' attribute which should be something like one of the following: 
                    # type="gmap:GmapDB"
                    # type="galaxy.datatypes.gmap:GmapDB"
                    dtype = elem.get( 'type', None )
                    if dtype:
                        fields = dtype.split( ':' )
                        proprietary_datatype_module = fields[ 0 ]
                        if proprietary_datatype_module.find( '.' ) >= 0:
                            # Handle the case where datatype_module is "galaxy.datatypes.gmap".
                            proprietary_datatype_module = proprietary_datatype_module.split( '.' )[ -1 ]
                        # The value of proprietary_path must be an absolute path due to job_working_directory.
                        elem.attrib[ 'proprietary_path' ] = os.path.abspath( relative_head )
                        elem.attrib[ 'proprietary_datatype_module' ] = proprietary_datatype_module
            sniffers = datatypes_config_root.find( 'sniffers' )
        else:
            sniffers = None
        fd, proprietary_datatypes_config = tempfile.mkstemp()
        os.write( fd, '<?xml version="1.0"?>\n' )
        os.write( fd, '<datatypes>\n' )
        os.write( fd, '%s' % util.xml_to_string( registration ) )
        if sniffers:
            os.write( fd, '%s' % util.xml_to_string( sniffers ) )
        os.write( fd, '</datatypes>\n' )
        os.close( fd )
        os.chmod( proprietary_datatypes_config, 0644 )
    else:
        proprietary_datatypes_config = datatypes_config
    # Load proprietary datatypes
    app.datatypes_registry.load_datatypes( root_dir=app.config.root, config=proprietary_datatypes_config, deactivate=deactivate, override=override )
    if datatype_files:
        try:
            os.unlink( proprietary_datatypes_config )
        except:
            pass
    return converter_path, display_path
def config_elems_to_xml_file( app, config_elems, config_filename, tool_path ):
    # Persist the current in-memory list of config_elems to a file named by the value of config_filename.  
    fd, filename = tempfile.mkstemp()
    os.write( fd, '<?xml version="1.0"?>\n' )
    os.write( fd, '<toolbox tool_path="%s">\n' % str( tool_path ) )
    for elem in config_elems:
        os.write( fd, '%s' % util.xml_to_string( elem, pretty=True ) )
    os.write( fd, '</toolbox>\n' )
    os.close( fd )
    shutil.move( filename, os.path.abspath( config_filename ) )
    os.chmod( config_filename, 0644 )
def clean_repository_clone_url( repository_clone_url ):
    if repository_clone_url.find( '@' ) > 0:
        # We have an url that includes an authenticated user, something like:
        # http://test@bx.psu.edu:9009/repos/some_username/column
        items = repository_clone_url.split( '@' )
        tmp_url = items[ 1 ]
    elif repository_clone_url.find( '//' ) > 0:
        # We have an url that includes only a protocol, something like:
        # http://bx.psu.edu:9009/repos/some_username/column
        items = repository_clone_url.split( '//' )
        tmp_url = items[ 1 ]
    else:
        tmp_url = repository_clone_url
    return tmp_url
def clean_tool_shed_url( tool_shed_url ):
    if tool_shed_url.find( ':' ) > 0:
        # Eliminate the port, if any, since it will result in an invalid directory name.
        return tool_shed_url.split( ':' )[ 0 ]
    return tool_shed_url.rstrip( '/' )
def clone_repository( repository_clone_url, repository_file_dir, ctx_rev ):
    """
    Clone the repository up to the specified changeset_revision.  No subsequent revisions will be present in the cloned repository.
    """
    commands.clone( get_configured_ui(),
                    repository_clone_url,
                    dest=repository_file_dir,
                    pull=True,
                    noupdate=False,
                    rev=[ ctx_rev ] )
def copy_sample_file( app, filename, dest_path=None ):
    """
    Copy xxx.loc.sample to dest_path/xxx.loc.sample and dest_path/xxx.loc.  The default value for dest_path is ~/tool-data.
    """
    if dest_path is None:
        dest_path = os.path.abspath( app.config.tool_data_path )
    sample_file_path, sample_file_name = os.path.split( filename )
    copied_file = sample_file_name.replace( '.sample', '' )
    # It's ok to overwrite the .sample version of the file.
    shutil.copy( os.path.abspath( filename ), os.path.join( dest_path, sample_file_name ) )
    # Only create the .loc file if it does not yet exist.  We don't overwrite it in case it contains stuff proprietary to the local instance.
    if not os.path.exists( os.path.join( dest_path, copied_file ) ):
        shutil.copy( os.path.abspath( filename ), os.path.join( dest_path, copied_file ) )
def copy_sample_files( app, sample_files, sample_files_copied=None, dest_path=None ):
    """
    Copy all files to dest_path in the local Galaxy environment that have not already been copied.  Those that have been copied
    are contained in sample_files_copied.  The default value for dest_path is ~/tool-data.
    """
    sample_files_copied = util.listify( sample_files_copied )
    for filename in sample_files:
        if filename not in sample_files_copied:
            copy_sample_file( app, filename, dest_path=dest_path )
def create_repository_dict_for_proprietary_datatypes( tool_shed, name, owner, installed_changeset_revision, tool_dicts, converter_path=None, display_path=None ):
    return dict( tool_shed=tool_shed,
                 repository_name=name,
                 repository_owner=owner,
                 installed_changeset_revision=installed_changeset_revision,
                 tool_dicts=tool_dicts,
                 converter_path=converter_path,
                 display_path=display_path )
def create_or_update_tool_shed_repository( app, name, description, changeset_revision, ctx_rev, repository_clone_url, metadata_dict,
                                           owner='', dist_to_shed=False ):
    # The received value for dist_to_shed will be True if the InstallManager is installing a repository that contains tools or datatypes that used
    # to be in the Galaxy distribution, but have been moved to the main Galaxy tool shed.
    sa_session = app.model.context.current
    tmp_url = clean_repository_clone_url( repository_clone_url )
    tool_shed = tmp_url.split( 'repos' )[ 0 ].rstrip( '/' )
    if not owner:
        owner = get_repository_owner( tmp_url )
    includes_datatypes = 'datatypes_config' in metadata_dict
    tool_shed_repository = get_repository_by_shed_name_owner_changeset_revision( app, tool_shed, name, owner, changeset_revision )
    if tool_shed_repository:
        tool_shed_repository.description = description
        tool_shed_repository.changeset_revision = changeset_revision
        tool_shed_repository.ctx_rev = ctx_rev
        tool_shed_repository.metadata = metadata_dict
        tool_shed_repository.includes_datatypes = includes_datatypes
        tool_shed_repository.deleted = False
        tool_shed_repository.uninstalled = False
    else:
        tool_shed_repository = app.model.ToolShedRepository( tool_shed=tool_shed,
                                                             name=name,
                                                             description=description,
                                                             owner=owner,
                                                             installed_changeset_revision=changeset_revision,
                                                             changeset_revision=changeset_revision,
                                                             ctx_rev=ctx_rev,
                                                             metadata=metadata_dict,
                                                             includes_datatypes=includes_datatypes,
                                                             dist_to_shed=dist_to_shed )
    sa_session.add( tool_shed_repository )
    sa_session.flush()
    return tool_shed_repository
def generate_clone_url( trans, repository ):
    """Generate the URL for cloning a repository."""
    tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
    return '%s/repos/%s/%s' % ( tool_shed_url, repository.owner, repository.name )
def generate_datatypes_metadata( datatypes_config, metadata_dict ):
    """Update the received metadata_dict with information from the parsed datatypes_config."""
    tree = ElementTree.parse( datatypes_config )
    root = tree.getroot()
    ElementInclude.include( root )
    repository_datatype_code_files = []
    datatype_files = root.find( 'datatype_files' )
    if datatype_files:
        for elem in datatype_files.findall( 'datatype_file' ):
            name = elem.get( 'name', None )
            repository_datatype_code_files.append( name )
        metadata_dict[ 'datatype_files' ] = repository_datatype_code_files
    datatypes = []
    registration = root.find( 'registration' )
    if registration:
        for elem in registration.findall( 'datatype' ):
            datatypes_dict = {}
            display_in_upload = elem.get( 'display_in_upload', None )
            if display_in_upload:
                datatypes_dict[ 'display_in_upload' ] = display_in_upload
            dtype = elem.get( 'type', None )
            if dtype:
                datatypes_dict[ 'dtype' ] = dtype
            extension = elem.get( 'extension', None )
            if extension:
                datatypes_dict[ 'extension' ] = extension
            max_optional_metadata_filesize = elem.get( 'max_optional_metadata_filesize', None )
            if max_optional_metadata_filesize:
                datatypes_dict[ 'max_optional_metadata_filesize' ] = max_optional_metadata_filesize
            mimetype = elem.get( 'mimetype', None )
            if mimetype:
                datatypes_dict[ 'mimetype' ] = mimetype
            subclass = elem.get( 'subclass', None )
            if subclass:
                datatypes_dict[ 'subclass' ] = subclass
            if datatypes_dict:
                datatypes.append( datatypes_dict )
        if datatypes:
            metadata_dict[ 'datatypes' ] = datatypes
    return metadata_dict
def generate_metadata( toolbox, relative_install_dir, repository_clone_url ):
    """
    Browse the repository files on disk to generate metadata.  Since we are using disk files, it is imperative that the
    repository is updated to the desired change set revision before metadata is generated.
    """
    metadata_dict = {}
    sample_files = []
    datatypes_config = None
    # Find datatypes_conf.xml if it exists.
    for root, dirs, files in os.walk( relative_install_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name == 'datatypes_conf.xml':
                    relative_path = os.path.join( root, name )
                    datatypes_config = os.path.abspath( relative_path )
                    break
    if datatypes_config:
        metadata_dict[ 'datatypes_config' ] = relative_path
        metadata_dict = generate_datatypes_metadata( datatypes_config, metadata_dict )
    # Find all special .sample files.
    for root, dirs, files in os.walk( relative_install_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name.endswith( '.sample' ):
                    sample_files.append( os.path.join( root, name ) )
    if sample_files:
        metadata_dict[ 'sample_files' ] = sample_files
    # Find all tool configs and exported workflows.
    for root, dirs, files in os.walk( relative_install_dir ):
        if root.find( '.hg' ) < 0 and root.find( 'hgrc' ) < 0:
            if '.hg' in dirs:
                dirs.remove( '.hg' )
            for name in files:
                # Find all tool configs.
                if name != 'datatypes_conf.xml' and name.endswith( '.xml' ):
                    full_path = os.path.abspath( os.path.join( root, name ) )
                    if not ( check_binary( full_path ) or check_image( full_path ) or check_gzip( full_path )[ 0 ]
                             or check_bz2( full_path )[ 0 ] or check_zip( full_path ) ):
                        try:
                            # Make sure we're looking at a tool config and not a display application config or something else.
                            element_tree = util.parse_xml( full_path )
                            element_tree_root = element_tree.getroot()
                            is_tool = element_tree_root.tag == 'tool'
                        except Exception, e:
                            log.debug( "Error parsing %s, exception: %s" % ( full_path, str( e ) ) )
                            is_tool = False
                        if is_tool:
                            try:
                                tool = toolbox.load_tool( full_path )
                            except Exception, e:
                                tool = None
                            if tool is not None:
                                tool_config = os.path.join( root, name )
                                metadata_dict = generate_tool_metadata( tool_config, tool, repository_clone_url, metadata_dict )
                # Find all exported workflows
                elif name.endswith( '.ga' ):
                    relative_path = os.path.join( root, name )
                    fp = open( relative_path, 'rb' )
                    workflow_text = fp.read()
                    fp.close()
                    exported_workflow_dict = from_json_string( workflow_text )
                    if 'a_galaxy_workflow' in exported_workflow_dict and exported_workflow_dict[ 'a_galaxy_workflow' ] == 'true':
                        metadata_dict = generate_workflow_metadata( relative_path, exported_workflow_dict, metadata_dict )
    return metadata_dict
def generate_tool_guid( repository_clone_url, tool ):
    """
    Generate a guid for the installed tool.  It is critical that this guid matches the guid for
    the tool in the Galaxy tool shed from which it is being installed.  The form of the guid is    
    <tool shed host>/repos/<repository owner>/<repository name>/<tool id>/<tool version>
    """
    tmp_url = clean_repository_clone_url( repository_clone_url )
    return '%s/%s/%s' % ( tmp_url, tool.id, tool.version )
def generate_tool_metadata( tool_config, tool, repository_clone_url, metadata_dict ):
    """Update the received metadata_dict with changes that have been applied to the received tool."""
    # Generate the guid
    guid = generate_tool_guid( repository_clone_url, tool )
    # Handle tool.requirements.
    tool_requirements = []
    for tr in tool.requirements:
        requirement_dict = dict( name=tr.name,
                                 type=tr.type,
                                 version=tr.version )
        tool_requirements.append( requirement_dict )
    # Handle tool.tests.
    tool_tests = []
    if tool.tests:
        for ttb in tool.tests:
            required_files = []
            for required_file in ttb.required_files:
                value, extra = required_file
                required_files.append( ( value ) )
            inputs = []
            for input in ttb.inputs:
                name, value, extra = input
                inputs.append( ( name, value ) )
            outputs = []
            for output in ttb.outputs:
                name, file_name, extra = output
                outputs.append( ( name, os.path.split( file_name )[ 1 ] ) )
            test_dict = dict( name=ttb.name,
                              required_files=required_files,
                              inputs=inputs,
                              outputs=outputs )
            tool_tests.append( test_dict )
    tool_dict = dict( id=tool.id,
                      guid=guid,
                      name=tool.name,
                      version=tool.version,
                      description=tool.description,
                      version_string_cmd = tool.version_string_cmd,
                      tool_config=tool_config,
                      requirements=tool_requirements,
                      tests=tool_tests )
    if 'tools' in metadata_dict:
        metadata_dict[ 'tools' ].append( tool_dict )
    else:
        metadata_dict[ 'tools' ] = [ tool_dict ]
    return metadata_dict
def generate_tool_panel_elem_list( repository_name, repository_clone_url, changeset_revision, tool_panel_dict, repository_tools_tups, owner='' ):
    """Generate a list of ElementTree Element objects for each section or tool."""
    elem_list = []
    tool_elem = None
    tmp_url = clean_repository_clone_url( repository_clone_url )
    if not owner:
        owner = get_repository_owner( tmp_url )
    for guid, tool_section_dicts in tool_panel_dict.items():
        for tool_section_dict in tool_section_dicts:
            tool_section = None
            inside_section = False
            section_in_elem_list = False
            if tool_section_dict[ 'id' ]:
                inside_section = True
                # Create a new section element only if we haven't already created it.
                for index, elem in enumerate( elem_list ):
                    if elem.tag == 'section':
                        section_id = elem.get( 'id', None )
                        if section_id == tool_section_dict[ 'id' ]:
                            section_in_elem_list = True
                            tool_section = elem
                            break
                if tool_section is None:
                    tool_section = generate_tool_section_element_from_dict( tool_section_dict )
            # Find the tuple containing the current guid from the list of repository_tools_tups.
            for repository_tool_tup in repository_tools_tups:
                tool_file_path, tup_guid, tool = repository_tool_tup
                if tup_guid == guid:
                    break
            if inside_section:
                tool_elem = SubElement( tool_section, 'tool' )
            else:
                tool_elem = Element( 'tool' )
            tool_elem.attrib[ 'file' ] = tool_file_path
            tool_elem.attrib[ 'guid' ] = guid
            tool_shed_elem = SubElement( tool_elem, 'tool_shed' )
            tool_shed_elem.text = tmp_url.split( 'repos' )[ 0 ].rstrip( '/' )
            repository_name_elem = SubElement( tool_elem, 'repository_name' )
            repository_name_elem.text = repository_name
            repository_owner_elem = SubElement( tool_elem, 'repository_owner' )
            repository_owner_elem.text = owner
            changeset_revision_elem = SubElement( tool_elem, 'installed_changeset_revision' )
            changeset_revision_elem.text = changeset_revision
            id_elem = SubElement( tool_elem, 'id' )
            id_elem.text = tool.id
            version_elem = SubElement( tool_elem, 'version' )
            version_elem.text = tool.version
            if inside_section:
                if section_in_elem_list:
                    elem_list[ index ] = tool_section
                else:
                    elem_list.append( tool_section )
            else:
                elem_list.append( tool_elem )
    return elem_list
def generate_tool_panel_dict_for_new_install( tool_dicts, tool_section=None ):
    """
    When installing a repository that contains tools, all tools must curently be defined within the same tool section in the tool
    panel or outside of any sections.
    """
    tool_panel_dict = {}
    if tool_section:
        section_id = tool_section.id
        section_name = tool_section.name
        section_version = tool_section.version or ''
    else:
        section_id = ''
        section_name = ''
        section_version = ''
    for tool_dict in tool_dicts:
        guid = tool_dict[ 'guid' ]
        tool_config = tool_dict[ 'tool_config' ]
        tool_section_dict = dict( tool_config=tool_config, id=section_id, name=section_name, version=section_version )
        if guid in tool_panel_dict:
            tool_panel_dict[ guid ].append( tool_section_dict )
        else:
            tool_panel_dict[ guid ] = [ tool_section_dict ]
    return tool_panel_dict
def generate_tool_panel_dict_from_shed_tool_conf_entries( trans, repository ):
    """
    Keep track of the section in the tool panel in which this repository's tools will be contained by parsing the shed-tool_conf in
    which the repository's tools are defined and storing the tool panel definition of each tool in the repository.  This method is called
    only when the repository is being deactivated or uninstalled and allows for activation or reinstallation using the original layout.
    """
    tool_panel_dict = {}
    shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, repository )
    metadata = repository.metadata
    # Create a dictionary of tool guid and tool config file name for each tool in the repository.
    guids_and_configs = {}
    for tool_dict in metadata[ 'tools' ]:
        guid = tool_dict[ 'guid' ]
        tool_config = tool_dict[ 'tool_config' ]
        file_path, file_name = os.path.split( tool_config )
        guids_and_configs[ guid ] = file_name
    # Parse the shed_tool_conf file in which all of this repository's tools are defined and generate the tool_panel_dict. 
    tree = util.parse_xml( shed_tool_conf )
    root = tree.getroot()
    for elem in root:
        if elem.tag == 'tool':
            guid = elem.get( 'guid' )
            if guid in guids_and_configs:
                # The tool is displayed in the tool panel outside of any tool sections.
                tool_section_dict = dict( tool_config=guids_and_configs[ guid ], id='', name='', version='' )
                if guid in tool_panel_dict:
                    tool_panel_dict[ guid ].append( tool_section_dict )
                else:
                    tool_panel_dict[ guid ] = [ tool_section_dict ]
        elif elem.tag == 'section':
            section_id = elem.get( 'id' ) or ''
            section_name = elem.get( 'name' ) or ''
            section_version = elem.get( 'version' ) or ''
            for section_elem in elem:
                if section_elem.tag == 'tool':
                    guid = section_elem.get( 'guid' )
                    if guid in guids_and_configs:
                        # The tool is displayed in the tool panel inside the current tool section.
                        tool_section_dict = dict( tool_config=guids_and_configs[ guid ],
                                                  id=section_id,
                                                  name=section_name,
                                                  version=section_version )
                        if guid in tool_panel_dict:
                            tool_panel_dict[ guid ].append( tool_section_dict )
                        else:
                            tool_panel_dict[ guid ] = [ tool_section_dict ]
    return tool_panel_dict
def generate_tool_panel_dict_for_tool_config( guid, tool_config, tool_sections=None ):
    """
    Create a dictionary of the following type for a single tool config file name.  The intent is to call this method for every tool config
    in a repository and append each of these as entries to a tool panel dictionary for the repository.  This allows for each tool to be
    loaded into a different section in the tool panel.
    {<Tool guid> : [{ tool_config : <tool_config_file>, id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}]}
    """
    tool_panel_dict = {}
    file_path, file_name = os.path.split( tool_config )
    tool_section_dicts = generate_tool_section_dicts( tool_config=file_name, tool_sections=tool_sections )
    tool_panel_dict[ guid ] = tool_section_dicts
    return tool_panel_dict
def generate_tool_section_dicts( tool_config=None, tool_sections=None ):
    tool_section_dicts = []
    if tool_config is None:
        tool_config = ''
    if tool_sections:
        for tool_section in tool_sections:
            # The value of tool_section will be None if the tool is displayed outside of any sections in the tool panel.
            if tool_section:
                section_id = tool_section.id or ''
                section_version = tool_section.version or ''
                section_name = tool_section.name or ''
            else:
                section_id = ''
                section_version = ''
                section_name = ''
            tool_section_dicts.append( dict( tool_config=tool_config, id=section_id, version=section_version, name=section_name ) )
    else:
        tool_section_dicts.append( dict( tool_config=tool_config, id='', version='', name='' ) )
    return tool_section_dicts
def generate_tool_section_element_from_dict( tool_section_dict ):
    # The value of tool_section_dict looks like the following.
    # { id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}
    if tool_section_dict[ 'id' ]:
        # Create a new tool section.
        tool_section = Element( 'section' )
        tool_section.attrib[ 'id' ] = tool_section_dict[ 'id' ]
        tool_section.attrib[ 'name' ] = tool_section_dict[ 'name' ]
        tool_section.attrib[ 'version' ] = tool_section_dict[ 'version' ]
    else:
        tool_section = None
    return tool_section
def generate_workflow_metadata( relative_path, exported_workflow_dict, metadata_dict ):
    """Update the received metadata_dict with changes that have been applied to the received exported_workflow_dict."""
    if 'workflows' in metadata_dict:
        metadata_dict[ 'workflows' ].append( ( relative_path, exported_workflow_dict ) )
    else:
        metadata_dict[ 'workflows' ] = [ ( relative_path, exported_workflow_dict ) ]
    return metadata_dict
def get_configured_ui():
    # Configure any desired ui settings.
    _ui = ui.ui()
    # The following will suppress all messages.  This is
    # the same as adding the following setting to the repo
    # hgrc file' [ui] section:
    # quiet = True
    _ui.setconfig( 'ui', 'quiet', True )
    return _ui
def get_converter_and_display_paths( registration_elem, relative_install_dir ):
    """Find the relative path to data type converters and display applications included in installed tool shed repositories."""
    converter_path = None
    display_path = None
    for elem in registration_elem.findall( 'datatype' ):
        if not converter_path:
            # If any of the <datatype> tag sets contain <converter> tags, set the converter_path
            # if it is not already set.  This requires developers to place all converters in the
            # same subdirectory within the repository hierarchy.
            for converter in elem.findall( 'converter' ):
                converter_config = converter.get( 'file', None )
                if converter_config:
                    relative_head, relative_tail = os.path.split( converter_config )
                    for root, dirs, files in os.walk( relative_install_dir ):
                        if root.find( '.hg' ) < 0:
                            for name in files:
                                if name == relative_tail:
                                    # The value of converter_path must be absolute due to job_working_directory.
                                    converter_path = os.path.abspath( root )
                                    break
                if converter_path:
                    break
        if not display_path:
            # If any of the <datatype> tag sets contain <display> tags, set the display_path
            # if it is not already set.  This requires developers to place all display acpplications
            # in the same subdirectory within the repository hierarchy.
            for display_app in elem.findall( 'display' ):
                display_config = display_app.get( 'file', None )
                if display_config:
                    relative_head, relative_tail = os.path.split( display_config )
                    for root, dirs, files in os.walk( relative_install_dir ):
                        if root.find( '.hg' ) < 0:
                            for name in files:
                                if name == relative_tail:
                                    # The value of display_path must be absolute due to job_working_directory.
                                    display_path = os.path.abspath( root )
                                    break
                if display_path:
                    break
        if converter_path and display_path:
            break
    return converter_path, display_path
def get_ctx_rev( tool_shed_url, name, owner, changeset_revision ):
    url = '%s/repository/get_ctx_rev?name=%s&owner=%s&changeset_revision=%s&webapp=galaxy&no_reset=true' % ( tool_shed_url, name, owner, changeset_revision )
    response = urllib2.urlopen( url )
    ctx_rev = response.read()
    response.close()
    return ctx_rev
def get_shed_tool_conf_dict( app, shed_tool_conf ):
    """
    Return the in-memory version of the shed_tool_conf file, which is stored in the config_elems entry
    in the shed_tool_conf_dict associated with the file.
    """
    for index, shed_tool_conf_dict in enumerate( app.toolbox.shed_tool_confs ):
        if shed_tool_conf == shed_tool_conf_dict[ 'config_filename' ]:
            return index, shed_tool_conf_dict
        else:
            file_path, file_name = os.path.split( shed_tool_conf_dict[ 'config_filename' ] )
            if shed_tool_conf == file_name:
                return index, shed_tool_conf_dict
def get_repository_by_shed_name_owner_changeset_revision( app, tool_shed, name, owner, changeset_revision ):
    sa_session = app.model.context.current
    if tool_shed.find( '//' ) > 0:
        tool_shed = tool_shed.split( '//' )[1]
    tool_shed = tool_shed.rstrip( '/' )
    return sa_session.query( app.model.ToolShedRepository ) \
                     .filter( and_( app.model.ToolShedRepository.table.c.tool_shed == tool_shed,
                                    app.model.ToolShedRepository.table.c.name == name,
                                    app.model.ToolShedRepository.table.c.owner == owner,
                                    app.model.ToolShedRepository.table.c.changeset_revision == changeset_revision ) ) \
                     .first()
def get_repository_owner( cleaned_repository_url ):
    items = cleaned_repository_url.split( 'repos' )
    repo_path = items[ 1 ]
    if repo_path.startswith( '/' ):
        repo_path = repo_path.replace( '/', '', 1 )
    return repo_path.lstrip( '/' ).split( '/' )[ 0 ]
def get_repository_tools_tups( app, metadata_dict ):
    repository_tools_tups = []
    if 'tools' in metadata_dict:
        for tool_dict in metadata_dict[ 'tools' ]:
            relative_path = tool_dict.get( 'tool_config', None )
            guid = tool_dict.get( 'guid', None )
            if relative_path and guid:
                tool = app.toolbox.load_tool( os.path.abspath( relative_path ), guid=guid )
            else:
                tool = None
            if tool:
                repository_tools_tups.append( ( relative_path, guid, tool ) )
    return repository_tools_tups
def get_tool_panel_config_tool_path_install_dir( app, repository ):
    # Return shed-related tool panel config, the tool_path configured in it, and the relative path to the directory where the
    # repository is installed.  This method assumes all repository tools are defined in a single shed-related tool panel config.
    tool_shed = clean_tool_shed_url( repository.tool_shed )
    partial_install_dir = '%s/repos/%s/%s/%s' % ( tool_shed, repository.owner, repository.name, repository.installed_changeset_revision )
    # Get the relative tool installation paths from each of the shed tool configs.
    relative_install_dir = None
    for shed_tool_conf_dict in app.toolbox.shed_tool_confs:
        shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
        if repository.dist_to_shed:
            # The repository is owned by devteam and contains tools migrated from the Galaxy distribution to the tool shed, so
            # the reserved tool panel config is migrated_tools_conf.xml, to which app.config.migrated_tools_config refers.
            if shed_tool_conf == app.config.migrated_tools_config:
                tool_path = shed_tool_conf_dict[ 'tool_path' ]
                relative_install_dir = os.path.join( tool_path, partial_install_dir )
                if tool_path and relative_install_dir:
                    return shed_tool_conf, tool_path, relative_install_dir
        elif repository.uninstalled:
            # Since the repository is uninstalled we don't know what tool panel config was originally used to
            # define the tools in the repository, so we'll just make sure not to use the reserved migrated_tools_conf.xml.
            if shed_tool_conf != app.config.migrated_tools_config:
                tool_path = shed_tool_conf_dict[ 'tool_path' ]
                relative_install_dir = os.path.join( tool_path, partial_install_dir )
                if tool_path and relative_install_dir:
                    return shed_tool_conf, tool_path, relative_install_dir
        else:
            if repository.includes_tools:
                metadata = repository.metadata
                for tool_dict in metadata[ 'tools' ]:
                    # Parse the tool panel config to get the entire set of config_elems.  # We'll check config_elems until we
                    # find an element that matches one of the tools in the repository's metadata.
                    tool_panel_config = shed_tool_conf_dict[ 'config_filename' ]
                    tree = util.parse_xml( tool_panel_config )
                    root = tree.getroot()
                    tool_path, relative_install_dir = get_tool_path_install_dir( partial_install_dir,
                                                                                 shed_tool_conf_dict,
                                                                                 tool_dict,
                                                                                 root )
                    if tool_path and relative_install_dir:
                        return shed_tool_conf, tool_path, relative_install_dir
            else:
                # Nothing will be loaded into the tool panel, so look for the installed repository on disk.
                tool_path = shed_tool_conf_dict[ 'tool_path' ]
                relative_install_dir = os.path.join( tool_path, partial_install_dir )
                if tool_path and relative_install_dir and os.path.isdir( relative_install_dir ):
                    return shed_tool_conf, tool_path, relative_install_dir
    return None, None, None
def get_tool_path_install_dir( partial_install_dir, shed_tool_conf_dict, tool_dict, config_elems ):
    for elem in config_elems:
        if elem.tag == 'tool':
            if elem.get( 'guid' ) == tool_dict[ 'guid' ]:
                tool_path = shed_tool_conf_dict[ 'tool_path' ]
                relative_install_dir = os.path.join( tool_path, partial_install_dir )
                return tool_path, relative_install_dir
        elif elem.tag == 'section':
            for section_elem in elem:
                if section_elem.tag == 'tool':
                    if section_elem.get( 'guid' ) == tool_dict[ 'guid' ]:
                        tool_path = shed_tool_conf_dict[ 'tool_path' ]
                        relative_install_dir = os.path.join( tool_path, partial_install_dir )
                        return tool_path, relative_install_dir
    return None, None
def get_tool_version( app, tool_id ):
    sa_session = app.model.context.current
    return sa_session.query( app.model.ToolVersion ) \
                     .filter( app.model.ToolVersion.table.c.tool_id == tool_id ) \
                     .first()
def get_tool_version_association( app, parent_tool_version, tool_version ):
    """Return a ToolVersionAssociation if one exists that associates the two received tool_versions"""
    sa_session = app.model.context.current
    return sa_session.query( app.model.ToolVersionAssociation ) \
                     .filter( and_( app.model.ToolVersionAssociation.table.c.parent_id == parent_tool_version.id,
                                    app.model.ToolVersionAssociation.table.c.tool_id == tool_version.id ) ) \
                     .first()
def get_url_from_repository_tool_shed( app, repository ):
    """
    The stored value of repository.tool_shed is something like: toolshed.g2.bx.psu.edu
    We need the URL to this tool shed, which is something like: http://toolshed.g2.bx.psu.edu/
    """
    for shed_name, shed_url in app.tool_shed_registry.tool_sheds.items():
        if shed_url.find( repository.tool_shed ) >= 0:
            if shed_url.endswith( '/' ):
                shed_url = shed_url.rstrip( '/' )
            return shed_url
    # The tool shed from which the repository was originally installed must no longer be configured in tool_sheds_conf.xml.
    return None
def handle_missing_data_table_entry( app, tool_path, sample_files, repository_tools_tups ):
    """
    Inspect each tool to see if any have input parameters that are dynamically generated select lists that require entries in the
    tool_data_table_conf.xml file.
    """
    missing_data_table_entry = False
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        if repository_tool.params_with_missing_data_table_entry:
            missing_data_table_entry = True
            break
    if missing_data_table_entry:
        sample_file = None
        # The repository must contain a tool_data_table_conf.xml.sample file that includes all required entries for all tools in the repository.
        for sample_file in sample_files:
            head, tail = os.path.split( sample_file )
            if tail == 'tool_data_table_conf.xml.sample':
                break
        error, correction_msg = handle_sample_tool_data_table_conf_file( app, sample_file )
        if error:
            # TODO: Do more here than logging an exception.
            log.debug( correction_msg )
        # Reload the tool into the local list of repository_tools_tups.
        repository_tool = app.toolbox.load_tool( os.path.join( tool_path, tup_path ), guid=guid )
        repository_tools_tups[ index ] = ( tup_path, guid, repository_tool )
    return repository_tools_tups
def handle_missing_index_file( app, tool_path, sample_files, repository_tools_tups ):
    """Inspect each tool to see if it has any input parameters that are dynamically generated select lists that depend on a .loc file."""
    sample_files_copied = []
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        params_with_missing_index_file = repository_tool.params_with_missing_index_file
        for param in params_with_missing_index_file:
            options = param.options
            missing_file_path, missing_file_name = os.path.split( options.missing_index_file )
            if missing_file_name not in sample_files_copied:
                # The repository must contain the required xxx.loc.sample file.
                for sample_file in sample_files:
                    sample_file_path, sample_file_name = os.path.split( sample_file )
                    if sample_file_name == '%s.sample' % missing_file_name:
                        copy_sample_file( app, sample_file )
                        if options.tool_data_table and options.tool_data_table.missing_index_file:
                            options.tool_data_table.handle_found_index_file( options.missing_index_file )
                        sample_files_copied.append( options.missing_index_file )
                        break
        # Reload the tool into the local list of repository_tools_tups.
        repository_tool = app.toolbox.load_tool( os.path.join( tool_path, tup_path ), guid=guid )
        repository_tools_tups[ index ] = ( tup_path, guid, repository_tool )
    return repository_tools_tups, sample_files_copied
def handle_sample_tool_data_table_conf_file( app, filename ):
    """
    Parse the incoming filename and add new entries to the in-memory
    app.tool_data_tables dictionary as well as appending them to the
    shed's tool_data_table_conf.xml file on disk.
    """
    error = False
    message = ''
    try:
        new_table_elems = app.tool_data_tables.add_new_entries_from_config_file( filename )
    except Exception, e:
        message = str( e )
        error = True
    if not error:
        # Add an entry to the end of the tool_data_table_conf.xml file.
        tdt_config = "%s/tool_data_table_conf.xml" % app.config.root
        if os.path.exists( tdt_config ):
            # Make a backup of the file since we're going to be changing it.
            today = date.today()
            backup_date = today.strftime( "%Y_%m_%d" )
            tdt_config_copy = '%s/tool_data_table_conf.xml_%s_backup' % ( app.config.root, backup_date )
            shutil.copy( os.path.abspath( tdt_config ), os.path.abspath( tdt_config_copy ) )
            # Write each line of the tool_data_table_conf.xml file, except the last line to a temp file.
            fh = tempfile.NamedTemporaryFile( 'wb' )
            tmp_filename = fh.name
            fh.close()
            new_tdt_config = open( tmp_filename, 'wb' )
            for i, line in enumerate( open( tdt_config, 'rb' ) ):
                if line.find( '</tables>' ) >= 0:
                    for new_table_elem in new_table_elems:
                        new_tdt_config.write( '    %s\n' % util.xml_to_string( new_table_elem ).rstrip( '\n' ) )
                    new_tdt_config.write( '</tables>\n' )
                else:
                    new_tdt_config.write( line )
            new_tdt_config.close()
            shutil.move( tmp_filename, os.path.abspath( tdt_config ) )
        else:
            message = "The required file named tool_data_table_conf.xml does not exist in the Galaxy install directory."
            error = True
    return error, message
def handle_tool_dependencies( current_working_dir, repo_files_dir, repository_tools_tups ):
    """
    Inspect each tool to see if it includes a "requirement" that refers to a fabric
    script.  For those that do, execute the fabric script to install tool dependencies.
    """
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        for requirement in repository_tool.requirements:
            if requirement.type == 'fabfile':
                log.debug( 'Executing fabric script to install dependencies for tool "%s"...' % repository_tool.name )
                fabfile = requirement.fabfile
                method = requirement.method
                # Find the relative path to the fabfile.
                relative_fabfile_path = None
                for root, dirs, files in os.walk( repo_files_dir ):
                    for name in files:
                        if name == fabfile:
                            relative_fabfile_path = os.path.join( root, name )
                            break
                if relative_fabfile_path:
                    # cmd will look something like: fab -f fabfile.py install_bowtie
                    cmd = 'fab -f %s %s' % ( relative_fabfile_path, method )
                    tmp_name = tempfile.NamedTemporaryFile().name
                    tmp_stderr = open( tmp_name, 'wb' )
                    os.chdir( repo_files_dir )
                    proc = subprocess.Popen( cmd, shell=True, stderr=tmp_stderr.fileno() )
                    returncode = proc.wait()
                    os.chdir( current_working_dir )
                    tmp_stderr.close()
                    if returncode != 0:
                        # TODO: do something more here than logging the problem.
                        tmp_stderr = open( tmp_name, 'rb' )
                        error = tmp_stderr.read()
                        tmp_stderr.close()
                        log.debug( 'Problem installing dependencies for tool "%s"\n%s' % ( repository_tool.name, error ) )
def handle_tool_versions( app, tool_version_dicts, tool_shed_repository ):
    """
    Using the list of tool_version_dicts retrieved from the tool shed (one per changeset revison up to the currently installed changeset revision),
    create the parent / child pairs of tool versions.  Each dictionary contains { tool id : parent tool id } pairs.
    """
    sa_session = app.model.context.current
    for tool_version_dict in tool_version_dicts:
        for tool_guid, parent_id in tool_version_dict.items():
            tool_version_using_tool_guid = get_tool_version( app, tool_guid )
            tool_version_using_parent_id = get_tool_version( app, parent_id )
            if not tool_version_using_tool_guid:
                tool_version_using_tool_guid = app.model.ToolVersion( tool_id=tool_guid, tool_shed_repository=tool_shed_repository )
                sa_session.add( tool_version_using_tool_guid )
                sa_session.flush()
            if not tool_version_using_parent_id:
                tool_version_using_parent_id = app.model.ToolVersion( tool_id=parent_id, tool_shed_repository=tool_shed_repository )
                sa_session.add( tool_version_using_parent_id )
                sa_session.flush()
            tool_version_association = get_tool_version_association( app,
                                                                     tool_version_using_parent_id,
                                                                     tool_version_using_tool_guid )
            if not tool_version_association:
                # Associate the two versions as parent / child.
                tool_version_association = app.model.ToolVersionAssociation( tool_id=tool_version_using_tool_guid.id,
                                                                             parent_id=tool_version_using_parent_id.id )
                sa_session.add( tool_version_association )
                sa_session.flush()
def load_datatype_items( app, repository, relative_install_dir, deactivate=False ):
    # Load proprietary datatypes.
    metadata = repository.metadata
    datatypes_config = metadata.get( 'datatypes_config', None )
    if datatypes_config:
        converter_path, display_path = alter_config_and_load_prorietary_datatypes( app, datatypes_config, relative_install_dir, deactivate=deactivate )
        if converter_path or display_path:
            # Create a dictionary of tool shed repository related information.
            repository_dict = create_repository_dict_for_proprietary_datatypes( tool_shed=repository.tool_shed,
                                                                                name=repository.name,
                                                                                owner=repository.owner,
                                                                                installed_changeset_revision=repository.installed_changeset_revision,
                                                                                tool_dicts=metadata.get( 'tools', [] ),
                                                                                converter_path=converter_path,
                                                                                display_path=display_path )
        if converter_path:
            # Load or deactivate proprietary datatype converters
            app.datatypes_registry.load_datatype_converters( app.toolbox, installed_repository_dict=repository_dict, deactivate=deactivate )
        if display_path:
            # Load or deactivate proprietary datatype display applications
            app.datatypes_registry.load_display_applications( installed_repository_dict=repository_dict, deactivate=deactivate )
def load_repository_contents( trans, repository_name, description, owner, changeset_revision, ctx_rev, tool_path, repository_clone_url,
                              relative_install_dir, current_working_dir, tool_shed=None, tool_section=None, shed_tool_conf=None,
                              install_tool_dependencies=False ):
    """Generate the metadata for the installed tool shed repository, among other things."""
    # It is critical that the installed repository is updated to the desired changeset_revision before metadata is set because the
    # process for setting metadata uses the repository files on disk.  This method is called when an admin is installing a new repository
    # or reinstalling an uninstalled repository. 
    metadata_dict = generate_metadata( trans.app.toolbox, relative_install_dir, repository_clone_url )
    # Add a new record to the tool_shed_repository table if one doesn't already exist.  If one exists but is marked deleted, undelete it.  This
    # must happen before the call to add_to_tool_panel() below because tools will not be properly loaded if the repository is marked deleted.
    log.debug( "Adding new row (or updating an existing row) for repository '%s' in the tool_shed_repository table." % repository_name )
    tool_shed_repository = create_or_update_tool_shed_repository( trans.app,
                                                                  repository_name,
                                                                  description,
                                                                  changeset_revision,
                                                                  ctx_rev,
                                                                  repository_clone_url,
                                                                  metadata_dict,
                                                                  dist_to_shed=False )
    if 'tools' in metadata_dict:
        tool_panel_dict = generate_tool_panel_dict_for_new_install( metadata_dict[ 'tools' ], tool_section )
        repository_tools_tups = get_repository_tools_tups( trans.app, metadata_dict )
        if repository_tools_tups:
            sample_files = metadata_dict.get( 'sample_files', [] )
            # Handle missing data table entries for tool parameters that are dynamically generated select lists.
            repository_tools_tups = handle_missing_data_table_entry( trans.app, tool_path, sample_files, repository_tools_tups )
            # Handle missing index files for tool parameters that are dynamically generated select lists.
            repository_tools_tups, sample_files_copied = handle_missing_index_file( trans.app, tool_path, sample_files, repository_tools_tups )
            # Copy remaining sample files included in the repository to the ~/tool-data directory of the local Galaxy instance.
            copy_sample_files( trans.app, sample_files, sample_files_copied=sample_files_copied )
            handle_tool_dependencies( current_working_dir, relative_install_dir, repository_tools_tups )
            add_to_tool_panel( app=trans.app,
                               repository_name=repository_name,
                               repository_clone_url=repository_clone_url,
                               changeset_revision=changeset_revision,
                               repository_tools_tups=repository_tools_tups,
                               owner=owner,
                               shed_tool_conf=shed_tool_conf,
                               tool_panel_dict=tool_panel_dict,
                               new_install=True )
    if 'datatypes_config' in metadata_dict:
        datatypes_config = os.path.abspath( metadata_dict[ 'datatypes_config' ] )
        # Load data types required by tools.
        converter_path, display_path = alter_config_and_load_prorietary_datatypes( trans.app, datatypes_config, relative_install_dir, override=False )
        if converter_path or display_path:
            # Create a dictionary of tool shed repository related information.
            repository_dict = create_repository_dict_for_proprietary_datatypes( tool_shed=tool_shed,
                                                                                name=repository_name,
                                                                                owner=owner,
                                                                                installed_changeset_revision=changeset_revision,
                                                                                tool_dicts=metadata_dict.get( 'tools', [] ),
                                                                                converter_path=converter_path,
                                                                                display_path=display_path )
        if converter_path:
            # Load proprietary datatype converters
            trans.app.datatypes_registry.load_datatype_converters( trans.app.toolbox, installed_repository_dict=repository_dict )
        if display_path:
            # Load proprietary datatype display applications
            trans.app.datatypes_registry.load_display_applications( installed_repository_dict=repository_dict )
    return tool_shed_repository, metadata_dict
def panel_entry_per_tool( tool_section_dict ):
    # Return True if tool_section_dict looks like this.
    # {<Tool guid> : [{ tool_config : <tool_config_file>, id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}]}
    # But not like this.
    # { id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}
    if not tool_section_dict:
        return False
    if len( tool_section_dict ) != 3:
        return True
    for k, v in tool_section_dict:
        if k not in [ 'id', 'version', 'name' ]:
            return True
    return False
def pull_repository( repo, repository_clone_url, ctx_rev ):
    """Pull changes from a remote repository to a local one."""
    commands.pull( get_configured_ui(),
                   repo,
                   source=repository_clone_url,
                   rev=ctx_rev )
def remove_from_shed_tool_config( trans, shed_tool_conf_dict, guids_to_remove ):
    # A tool shed repository is being uninstalled so change the shed_tool_conf file.  Parse the config file to generate the entire list
    # of config_elems instead of using the in-memory list since it will be a subset of the entire list if one or more repositories have
    # been deactivated.
    shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
    tool_path = shed_tool_conf_dict[ 'tool_path' ]
    config_elems = []
    tree = util.parse_xml( shed_tool_conf )
    root = tree.getroot()
    for elem in root:
        config_elems.append( elem )
    config_elems_to_remove = []
    for config_elem in config_elems:
        if config_elem.tag == 'section':
            tool_elems_to_remove = []
            for tool_elem in config_elem:
                if tool_elem.get( 'guid' ) in guids_to_remove:
                    tool_elems_to_remove.append( tool_elem )
            for tool_elem in tool_elems_to_remove:
                # Remove all of the appropriate tool sub-elements from the section element.
                config_elem.remove( tool_elem )
            if len( config_elem ) < 1:
                # Keep a list of all empty section elements so they can be removed.
                config_elems_to_remove.append( config_elem )
        elif config_elem.tag == 'tool':
            if config_elem.get( 'guid' ) in guids_to_remove:
                config_elems_to_remove.append( config_elem )
    for config_elem in config_elems_to_remove:
        config_elems.remove( config_elem )
    # Persist the altered in-memory version of the tool config.
    config_elems_to_xml_file( trans.app, config_elems, shed_tool_conf, tool_path )
def remove_from_tool_panel( trans, repository, shed_tool_conf, uninstall ):
    """A tool shed repository is being deactivated or uninstalled so handle tool panel alterations accordingly."""
    # Determine where the tools are currently defined in the tool panel and store this information so the tools can be displayed
    # in the same way when the repository is activated or reinstalled.
    tool_panel_dict = generate_tool_panel_dict_from_shed_tool_conf_entries( trans, repository )
    repository.metadata[ 'tool_panel_section' ] = tool_panel_dict
    trans.sa_session.add( repository )
    trans.sa_session.flush()
    # Create a list of guids for all tools that will be removed from the in-memory tool panel and config file on disk.
    guids_to_remove = [ k for k in tool_panel_dict.keys() ]
    index, shed_tool_conf_dict = get_shed_tool_conf_dict( trans.app, shed_tool_conf )
    if uninstall:
        # Remove from the shed_tool_conf file on disk.
        remove_from_shed_tool_config( trans, shed_tool_conf_dict, guids_to_remove )
    config_elems = shed_tool_conf_dict[ 'config_elems' ]
    config_elems_to_remove = []
    for config_elem in config_elems:
        if config_elem.tag == 'section':
            # Get the section key for the in-memory tool panel.
            section_key = 'section_%s' % str( config_elem.get( "id" ) )
            # Generate the list of tool elements to remove.
            tool_elems_to_remove = []
            for tool_elem in config_elem:
                if tool_elem.get( 'guid' ) in guids_to_remove:
                    tool_elems_to_remove.append( tool_elem )
            for tool_elem in tool_elems_to_remove:
                # Remove the tool sub-element from the section element.
                config_elem.remove( tool_elem )
                # Remove the tool from the section in the in-memory tool panel.
                if section_key in trans.app.toolbox.tool_panel:
                    tool_section = trans.app.toolbox.tool_panel[ section_key ]
                    tool_key = 'tool_%s' % str( tool_elem.get( 'guid' ) )
                    # Remove empty sections only from the in-memory config_elems, but leave the in-memory tool panel alone.
                    if tool_key in tool_section.elems:
                        del tool_section.elems[ tool_key ]
                if uninstall:
                    # Remove the tool from the section in the in-memory integrated tool panel.
                    if section_key in trans.app.toolbox.integrated_tool_panel:
                        tool_section = trans.app.toolbox.integrated_tool_panel[ section_key ]
                        tool_key = 'tool_%s' % str( tool_elem.get( 'guid' ) )
                        if tool_key in tool_section.elems:
                            del tool_section.elems[ tool_key ]
            if len( config_elem ) < 1:
                # Keep a list of all empty section elements so they can be removed.
                config_elems_to_remove.append( config_elem )
        elif config_elem.tag == 'tool':
            if config_elem.get( 'guid' ) in guids_to_remove:
                tool_key = key = 'tool_%s' % str( config_elem.get( 'guid' ) )
                if tool_key in trans.app.toolbox.tool_panel:
                    del trans.app.toolbox.tool_panel[ tool_key ]
                if uninstall:
                    if tool_key in trans.app.toolbox.integrated_tool_panel:
                        del trans.app.toolbox.integrated_tool_panel[ tool_key ]
                config_elems_to_remove.append( config_elem )
    for config_elem in config_elems_to_remove:
        # Remove the element from the in-memory list of elements.
        config_elems.remove( config_elem )
    # Update the config_elems of the in-memory shed_tool_conf_dict.
    shed_tool_conf_dict[ 'config_elems' ] = config_elems
    trans.app.toolbox.shed_tool_confs[ index ] = shed_tool_conf_dict
    if trans.app.toolbox_search.enabled:
        # If search support for tools is enabled, index tools.
        trans.app.toolbox_search = ToolBoxSearch( trans.app.toolbox )
    if uninstall:
        # Write the current in-memory version of the integrated_tool_panel.xml file to disk.
        trans.app.toolbox.write_integrated_tool_panel_config_file()
def to_html_escaped( text ):
    """Translates the characters in text to html values"""
    translated = []
    for c in text:
        if c in [ '\r\n', '\n', ' ', '\t' ] or c in VALID_CHARS:
            translated.append( c )
        elif c in MAPPED_CHARS:
            translated.append( MAPPED_CHARS[ c ] )
        else:
            translated.append( 'X' )
    return ''.join( translated )
def to_html_str( text ):
    """Translates the characters in text to sn html string"""
    translated = []
    for c in text:
        if c in VALID_CHARS:
            translated.append( c )
        elif c in MAPPED_CHARS:
            translated.append( MAPPED_CHARS[ c ] )
        elif c == ' ':
            translated.append( '&nbsp;' )
        elif c == '\t':
            translated.append( '&nbsp;&nbsp;&nbsp;&nbsp;' )
        elif c == '\n':
            translated.append( '<br/>' )
        elif c not in [ '\r' ]:
            translated.append( 'X' )
    return ''.join( translated )
def update_repository( repo, ctx_rev=None ):
    """
    Update the cloned repository to changeset_revision.  It is critical that the installed repository is updated to the desired
    changeset_revision before metadata is set because the process for setting metadata uses the repository files on disk.
    """
    # TODO: We may have files on disk in the repo directory that aren't being tracked, so they must be removed.
    # The codes used to show the status of files are as follows.
    # M = modified
    # A = added
    # R = removed
    # C = clean
    # ! = deleted, but still tracked
    # ? = not tracked
    # I = ignored
    # It would be nice if we could use mercurial's purge extension to remove untracked files.  The problem is that
    # purging is not supported by the mercurial API.  See the deprecated update_for_browsing() method in common.py.
    commands.update( get_configured_ui(),
                     repo,
                     rev=ctx_rev )
