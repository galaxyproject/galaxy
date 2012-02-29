import os, tempfile, shutil, subprocess, logging
from datetime import date, datetime, timedelta
from time import strftime
from galaxy import util
from galaxy.util.json import *
from galaxy.tools.search import ToolBoxSearch
from galaxy.model.orm import *

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree, ElementInclude
from elementtree.ElementTree import Element, SubElement

log = logging.getLogger( __name__ )

def add_to_tool_panel( app, repository_name, repository_clone_url, changeset_revision, repository_tools_tups, owner, shed_tool_conf, tool_panel_dict, new_install=True ):
    """A tool shed repository is being installed or updated so handle tool panel alterations accordingly."""
    # We need to change the in-memory version and the file system version of the shed_tool_conf file.
    index, shed_tool_conf_dict = get_shed_tool_conf_dict( app, shed_tool_conf )
    tool_path = shed_tool_conf_dict[ 'tool_path' ]
    config_elems = shed_tool_conf_dict[ 'config_elems' ]
    # Generate the list of ElementTree Element objects for each section or tool.
    elem_list = generate_tool_panel_elem_list( repository_name,
                                               repository_clone_url,
                                               changeset_revision,
                                               tool_panel_dict,
                                               repository_tools_tups,
                                               owner=owner )
    # Load the tools into the tool panel.
    for config_elem in elem_list:
        if config_elem.tag == 'section':
            app.toolbox.load_section_tag_set( config_elem, app.toolbox.tool_panel, tool_path )
        elif config_elem.tag == 'tool':
            guid = config_elem.get( 'guid' )
            app.toolbox.load_tool_tag_set( config_elem, app.toolbox.tool_panel, tool_path=tool_path, guid=guid )
    if new_install:
        # Add the elements to the in-memory list of config_elems.
        for elem_entry in elem_list:
            config_elems.append( elem_entry )
    # Replace the old list of config_elems with the new list.
    shed_tool_conf_dict[ 'config_elems' ] = config_elems
    app.toolbox.shed_tool_confs[ index ] = shed_tool_conf_dict
    # Append the new entry (either section or list of tools) to the shed_tool_config file.
    config_elems_to_xml_file( app, shed_tool_conf_dict )
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
        fd, proprietary_datatypes_config = tempfile.mkstemp()
        os.write( fd, '<?xml version="1.0"?>\n' )
        os.write( fd, '<datatypes>\n' )
        os.write( fd, '%s' % util.xml_to_string( registration ) )
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
def config_elems_to_xml_file( app, shed_tool_conf_dict ):
    # Persist the current in-memory list of config_elems in the received shed_tool_conf_dict
    # to a file named by the value of config_filename in the received shed_tool_conf_dict.  
    config_filename = shed_tool_conf_dict[ 'config_filename' ]
    tool_path = shed_tool_conf_dict[ 'tool_path' ]
    config_elems = shed_tool_conf_dict[ 'config_elems' ]
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
def clone_repository( name, clone_dir, current_working_dir, repository_clone_url ):
    log.debug( "Installing repository '%s'" % name )
    if not os.path.exists( clone_dir ):
        os.makedirs( clone_dir )
    log.debug( 'Cloning %s' % repository_clone_url )
    cmd = 'hg clone %s' % repository_clone_url
    tmp_name = tempfile.NamedTemporaryFile().name
    tmp_stderr = open( tmp_name, 'wb' )
    os.chdir( clone_dir )
    proc = subprocess.Popen( args=cmd, shell=True, stderr=tmp_stderr.fileno() )
    returncode = proc.wait()
    os.chdir( current_working_dir )
    tmp_stderr.close()
    return returncode, tmp_name
def copy_sample_loc_file( app, filename ):
    """Copy xxx.loc.sample to ~/tool-data/xxx.loc.sample and ~/tool-data/xxx.loc"""
    head, sample_loc_file = os.path.split( filename )
    loc_file = sample_loc_file.replace( '.sample', '' )
    tool_data_path = os.path.abspath( app.config.tool_data_path )
    # It's ok to overwrite the .sample version of the file.
    shutil.copy( os.path.abspath( filename ), os.path.join( tool_data_path, sample_loc_file ) )
    # Only create the .loc file if it does not yet exist.  We don't  
    # overwrite it in case it contains stuff proprietary to the local instance.
    if not os.path.exists( os.path.join( tool_data_path, loc_file ) ):
        shutil.copy( os.path.abspath( filename ), os.path.join( tool_data_path, loc_file ) )
def create_repository_dict_for_proprietary_datatypes( tool_shed, name, owner, installed_changeset_revision, tool_dicts, converter_path=None, display_path=None ):
    return dict( tool_shed=tool_shed,
                 repository_name=name,
                 repository_owner=owner,
                 installed_changeset_revision=installed_changeset_revision,
                 tool_dicts=tool_dicts,
                 converter_path=converter_path,
                 display_path=display_path )
def create_or_update_tool_shed_repository( app, name, description, changeset_revision, repository_clone_url, metadata_dict, owner='', dist_to_shed=False ):
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
    """Update the received metadata_dict with changes that have been applied to the received datatypes_config."""
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
def generate_metadata( toolbox, relative_install_dir, repository_clone_url, tool_section_dict=None, tool_panel_dict=None ):
    """
    Browse the repository files on disk to generate metadata.  Since we are using disk files, it is imperative that the
    repository is updated to the desired change set revision before metadata is generated.
    """
    metadata_dict = {}
    sample_files = []
    datatypes_config = None
    new_tool_panel_dict = {}
    # Keep track of the section in the tool panel in which this repository's tools will be contained by using the information in either the
    # tool_section_dict or the tool_panel_dict (at least 1 of these 2 dictionaries should be None).  The tool_section_dict is passed when the
    # Admin is manually installing a repository into a single selected section.  It looks something like this.
    # { id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}
    # The tool_panel_dict is fully populated with all tools in the repository that should be loaded into the tool panel.  It is received when
    # this method is called by the InstallManager or when metadata is being reset on an existing repository.  This dictionary looks something
    #  like this.
    # {<Tool guid> : { tool_config : <tool_config_file>, id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}}
    # The tool_panel_dict enables each tool in the repository to be contained inside or outside a specified ToolSection in the tool panel.  The 
    # new_tool_panel_dict with be populated with a subset of the items in the received tool_panel_dict.  This will allow for the case where
    # repository metadata is being updated where the previous change set revision included more tools than the current change set revision.
    if tool_section_dict:
        # The received tool_panel_dict must be None, so we'll populate it here.  Currently tools must all be installed in a single
        # section or outside any sections.
        for k, v in tool_section_dict.items():
            if v is None:
                # Coerce None values into empty strings because ElementTree.tostring() throws exceptions on None values.
                tool_section_dict[ k ] = ''
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
                    try:
                        tool = toolbox.load_tool( full_path )
                    except Exception, e:
                        tool = None
                    if tool is not None:
                        tool_config = os.path.join( root, name )
                        guid = generate_tool_guid( repository_clone_url, tool )
                        metadata_dict = generate_tool_metadata( tool_config, tool, repository_clone_url, metadata_dict )
                        # Populate the tool_section_dict if necessary.
                        if tool_panel_dict and guid in tool_panel_dict:
                            # We're updating metadata on a previously installed repository.
                            old_tool_panel_dict = tool_panel_dict[ guid ]
                            if 'tool_config' not in old_tool_panel_dict or old_tool_panel_dict[ 'tool_config' ] in [ None, '' ]:
                                old_tool_panel_dict[ 'tool_config' ] = name
                            new_tool_panel_dict[ guid ] = old_tool_panel_dict
                        else:
                            # The admin is manually installing a new repository.
                            new_tool_section_dict = {}
                            if tool_section_dict:
                                for k, v in tool_section_dict.items():
                                    new_tool_section_dict[ k ] = v
                            else:
                                new_tool_section_dict[ 'id' ] = ''
                                new_tool_section_dict[ 'name' ] = ''
                                new_tool_section_dict[ 'version' ] = ''
                            if 'tool_config' not in new_tool_section_dict or new_tool_section_dict[ 'tool_config' ] in [ None, '' ]:
                                new_tool_section_dict[ 'tool_config' ] = name
                            new_tool_panel_dict[ guid ] = new_tool_section_dict
                # Find all exported workflows
                elif name.endswith( '.ga' ):
                    relative_path = os.path.join( root, name )
                    fp = open( relative_path, 'rb' )
                    workflow_text = fp.read()
                    fp.close()
                    exported_workflow_dict = from_json_string( workflow_text )
                    if 'a_galaxy_workflow' in exported_workflow_dict and exported_workflow_dict[ 'a_galaxy_workflow' ] == 'true':
                        metadata_dict = generate_workflow_metadata( relative_path, exported_workflow_dict, metadata_dict )
    metadata_dict[ 'tool_panel_section' ] = new_tool_panel_dict
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
        name=tr.name
        type=tr.type
        if type == 'fabfile':
            version = None
            fabfile = tr.fabfile
            method = tr.method
        else:
            version = tr.version
            fabfile = None
            method = None
        requirement_dict = dict( name=name,
                                 type=type,
                                 version=version,
                                 fabfile=fabfile,
                                 method=method )
        tool_requirements.append( requirement_dict )
    # Handle tool.tests.
    tool_tests = []
    if tool.tests:
        for ttb in tool.tests:
            test_dict = dict( name=ttb.name,
                              required_files=ttb.required_files,
                              inputs=ttb.inputs,
                              outputs=ttb.outputs )
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
    # Each entry in the  tool_panel_dict looks like this.
    # {<Tool guid> : { tool_config : <tool_config_file>, id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}}
    elem_list = []
    tool_elem = None
    tmp_url = clean_repository_clone_url( repository_clone_url )
    if not owner:
        owner = get_repository_owner( tmp_url )
    for guid, tool_section_dict in tool_panel_dict.items():
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
def generate_tool_panel_dict_for_repository_tools( repository_metadata, tool_section=None, tool_section_dict=None ):
    """
    Create a dictionary of the following type for every tool in the repository where the tools are all
    contained in the same tool section or no tool section.  If tool_section is None, tools will be displayed
    outside of any sections in the tool panel.
    {<Tool guid> : { tool_config : <tool_config_file>, id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}}
    """
    tool_panel_dict = {}
    tool_dicts = repository_metadata[ 'tools' ]
    for tool_dict in tool_dicts:
        guid = tool_dict[ 'guid' ]
        tool_config = tool_dict[ 'tool_config' ]
        new_tool_section_dict = {}
        if tool_section_dict:
            for k, v in tool_section_dict.items():
                new_tool_section_dict[ k ] = v
            file_path, file_name = os.path.split( tool_config )
            new_tool_section_dict[ 'tool_config' ] = file_name
        else:
            new_tool_section_dict = generate_tool_section_dict( tool_config=tool_config, tool_section=tool_section )
        tool_panel_dict[ guid ] = tool_section_dict
    return tool_panel_dict
def generate_tool_panel_dict_for_tool_config( guid, tool_config, tool_section=None ):
    """
    Create a dictionary of the following type for a single tool config file name.  The intent is to call this method for every tool config
    in a repository and append each of these as entries to a tool panel dictionary for the repository.  This allows for each tool to be
    loaded into a different section in the tool panel.
    {<Tool guid> : { tool_config : <tool_config_file>, id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}}
    """
    tool_panel_dict = {}
    file_path, file_name = os.path.split( tool_config )
    tool_section_dict = generate_tool_section_dict( tool_config=file_name, tool_section=tool_section )
    tool_panel_dict[ guid ] = tool_section_dict
    return tool_panel_dict
def generate_tool_section_dict( tool_config=None, tool_section=None ):
    if tool_config is None:
        tool_config = ''
    if tool_section:
        section_id = tool_section.id or ''
        section_version = tool_section.version or ''
        section_name = tool_section.name or ''
        tool_section_dict = dict( tool_config=tool_config, id=section_id, version=section_version, name=section_name )
    else:
        tool_section_dict = dict( tool_config=tool_config, id='', version='', name='' )
    return tool_section_dict
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
            relative_path = tool_dict[ 'tool_config' ]
            guid = tool_dict[ 'guid' ]
            tool = app.toolbox.load_tool( os.path.abspath( relative_path ), guid=guid )
            repository_tools_tups.append( ( relative_path, guid, tool ) )
    return repository_tools_tups
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
        # The repository must contain a tool_data_table_conf.xml.sample file that includes all required entries for all tools in the repository.
        for sample_file in sample_files:
            head, tail = os.path.split( sample_file )
            if tail == 'tool_data_table_conf.xml.sample':
                break
        error, correction_msg = handle_sample_tool_data_table_conf_file( app, sample_file )
        if error:
            # TODO: Do more here than logging an exception.
            log.debug( exception_msg )
        # Reload the tool into the local list of repository_tools_tups.
        repository_tool = app.toolbox.load_tool( os.path.join( tool_path, tup_path ), guid=guid )
        repository_tools_tups[ index ] = ( tup_path, repository_tool )
    return repository_tools_tups
def handle_missing_index_file( app, tool_path, sample_files, repository_tools_tups ):
    """Inspect each tool to see if it has any input parameters that are dynamically generated select lists that depend on a .loc file."""
    missing_files_handled = []
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        params_with_missing_index_file = repository_tool.params_with_missing_index_file
        for param in params_with_missing_index_file:
            options = param.options
            missing_head, missing_tail = os.path.split( options.missing_index_file )
            if missing_tail not in missing_files_handled:
                # The repository must contain the required xxx.loc.sample file.
                for sample_file in sample_files:
                    sample_head, sample_tail = os.path.split( sample_file )
                    if sample_tail == '%s.sample' % missing_tail:
                        copy_sample_loc_file( app, sample_file )
                        if options.tool_data_table and options.tool_data_table.missing_index_file:
                            options.tool_data_table.handle_found_index_file( options.missing_index_file )
                        missing_files_handled.append( missing_tail )
                        break
        # Reload the tool into the local list of repository_tools_tups.
        repository_tool = app.toolbox.load_tool( os.path.join( tool_path, tup_path ), guid=guid )
        repository_tools_tups[ index ] = ( tup_path, guid, repository_tool )
    return repository_tools_tups
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
def load_repository_contents( trans, repository_name, description, owner, changeset_revision, tool_path, repository_clone_url, relative_install_dir,
                              current_working_dir, tmp_name, tool_panel_dict=None, tool_shed=None, tool_section=None, shed_tool_conf=None,
                              new_install=True ):
    """
    Generate the metadata for the installed tool shed repository, among other things.  It is critical that the installed repository
    is updated to the desired changeset_revision before metadata is set because the process for setting metadata uses the repository
    files on disk.  If this method is called when a new repository is being installed, the value of tool_panel_dict will be None and
    the value of tool_section (a ToolSection or None) will be used.  This method is also called when updates have been pulled to a
    previously installed repository, in which case the value of tool_panel_dict will be used and the value of new_install will be False.
    """
    if tool_panel_dict:
        # We're resetting metadata on a previously installed repository.  For backward compatibility we have to handle 2 types of dictionaries.
        # In the past, all repository tools had to be installed into a single ToolSection (or outside of any sections) in the tool panel.
        if panel_entry_per_tool( tool_panel_dict ):
            # {<Tool guid> : { tool_config : <tool_config_file>, id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}}
            metadata_dict = generate_metadata( trans.app.toolbox, relative_install_dir, repository_clone_url, tool_panel_dict=tool_panel_dict )
        else:
            # { id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}
            metadata_dict = generate_metadata( trans.app.toolbox, relative_install_dir, repository_clone_url, tool_section_dict=tool_panel_dict )
    else:
        # We're installing a new repository or reinstalling an uninstalled repository where all tools are contained in the same tool panel section
        # or outside of any sections in the tool panel.  We cannot pass a specific tool_config since we do not yet have one.
        tool_section_dict = generate_tool_section_dict( tool_config=None, tool_section=tool_section )
        metadata_dict = generate_metadata( trans.app.toolbox, relative_install_dir, repository_clone_url, tool_section_dict=tool_section_dict )
    tool_panel_dict = metadata_dict[ 'tool_panel_section' ]
    # Add a new record to the tool_shed_repository table if one doesn't already exist.  If one exists but is marked deleted, undelete it.  This
    # must happen before the call to add_to_tool_panel() below because tools will not be properly loaded if the repository is marked deleted.
    log.debug( "Adding new row (or updating an existing row) for repository '%s' in the tool_shed_repository table." % repository_name )
    tool_shed_repository = create_or_update_tool_shed_repository( trans.app,
                                                                  repository_name,
                                                                  description,
                                                                  changeset_revision,
                                                                  repository_clone_url,
                                                                  metadata_dict,
                                                                  dist_to_shed=False )
    if 'tools' in metadata_dict:
        repository_tools_tups = get_repository_tools_tups( trans.app, metadata_dict )
        if repository_tools_tups:
            sample_files = metadata_dict.get( 'sample_files', [] )
            # Handle missing data table entries for tool parameters that are dynamically generated select lists.
            repository_tools_tups = handle_missing_data_table_entry( trans.app, tool_path, sample_files, repository_tools_tups )
            # Handle missing index files for tool parameters that are dynamically generated select lists.
            repository_tools_tups = handle_missing_index_file( trans.app, tool_path, sample_files, repository_tools_tups )
            # Handle tools that use fabric scripts to install dependencies.
            handle_tool_dependencies( current_working_dir, relative_install_dir, repository_tools_tups )
            if new_install:
                add_to_tool_panel( app=trans.app,
                                   repository_name=repository_name,
                                   repository_clone_url=repository_clone_url,
                                   changeset_revision=changeset_revision,
                                   repository_tools_tups=repository_tools_tups,
                                   owner=owner,
                                   shed_tool_conf=shed_tool_conf,
                                   tool_panel_dict=tool_panel_dict,
                                   new_install=new_install )
            elif trans.app.toolbox_search.enabled:
                # If search support for tools is enabled, index the new installed tools.  In the condition above, this happens in the
                # add_to_tool_panel() method.
                trans.app.toolbox_search = ToolBoxSearch( trans.app.toolbox )
            # Remove the temporary file
            try:
                os.unlink( tmp_name )
            except:
                pass
    if 'datatypes_config' in metadata_dict:
        datatypes_config = os.path.abspath( metadata_dict[ 'datatypes_config' ] )
        # Load data types required by tools.
        override = not new_install
        converter_path, display_path = alter_config_and_load_prorietary_datatypes( trans.app, datatypes_config, relative_install_dir, override=override )
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
    # {<Tool guid> : { tool_config : <tool_config_file>, id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}}
    # But not like this.
    # { id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}
    if len( tool_section_dict ) != 3:
        return True
    for k, v in tool_section_dict:
        if k not in [ 'id', 'version', 'name' ]:
            return True
    return False
def pull_repository( current_working_dir, repo_files_dir, name ):
    # Pull the latest possible contents to the repository.
    log.debug( "Pulling latest updates to the repository named '%s'" % name )
    cmd = 'hg pull'
    tmp_name = tempfile.NamedTemporaryFile().name
    tmp_stderr = open( tmp_name, 'wb' )
    os.chdir( repo_files_dir )
    proc = subprocess.Popen( cmd, shell=True, stderr=tmp_stderr.fileno() )
    returncode = proc.wait()
    os.chdir( current_working_dir )
    tmp_stderr.close()
    return returncode, tmp_name
def remove_from_tool_panel( app, shed_tool_conf, tool_panel_dict, uninstall=False ):
    # A tool shed repository is being deactivated or uninstalled so handle tool panel alterations accordingly.  We need to change the
    # in-memory version and the file system version of the shed_tool_conf file.  The value of tool_panel_dict is a dictionary of entries
    # that look like this.
    # {<Tool guid> : { tool_config : <tool_config_file>, id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}}
    index, shed_tool_conf_dict = get_shed_tool_conf_dict( app, shed_tool_conf )
    config_elems = shed_tool_conf_dict[ 'config_elems' ]
    tool_elements_removed = 0
    config_elems_to_remove = []
    # Create a list of guids for all tools that will be removed from the tool panel config.
    guids_to_remove = [ k for k in tool_panel_dict.keys() ]
    for config_elem in config_elems:
        config_elems_to_remove = []
        if config_elem.tag == 'section':
            tool_elems_to_remove = []
            for tool_elem in config_elem:
                if tool_elem.get( 'guid' ) in guids_to_remove:
                    tool_elems_to_remove.append( tool_elem )
            for tool_elem in tool_elems_to_remove:
                # Remove all of the appropriate tool sub-elements from the section element.
                config_elem.remove( tool_elem )
                log.debug( "Removed tool with guid '%s'." % str( tool_elem.get( 'guid' ) ) )
                tool_elements_removed += 1
            if len( config_elem ) < 1:
                # Keep a list of all empty section elements so they can be removed.
                config_elems_to_remove.append( config_elem )
            if tool_elements_removed == len( guids_to_remove ):
                break
        elif config_elem.tag == 'tool':
            if config_elem.get( 'guid' ) in guids_to_remove:
                config_elems_to_remove.append( config_elem )
                log.debug( "Removed tool with guid '%s'." % str( config_elem.get( 'guid' ) ) )
                tool_elements_removed += 1
            if tool_elements_removed == len( guids_to_remove ):
                break
    for config_elem in config_elems_to_remove:
        # Remove the element from the in-menory tool panel.
        if config_elem.tag == 'section':
            key = 'section_%s' % str( config_elem.get( "id" ) )
            del app.toolbox.tool_panel[ key ]
        elif config_elem.tag == 'tool':
            key = 'tool_%s' % str( config_elem.get( 'guid' ) )
            del app.toolbox.tool_panel[ key ]
        # Remove the element from the in-memory list of elements.
        config_elems.remove( config_elem )
    # Update the config_elems of the in-memory shed_tool_conf_dict.
    shed_tool_conf_dict[ 'config_elems' ] = config_elems
    app.toolbox.shed_tool_confs[ index ] = shed_tool_conf_dict
    if uninstall:
        # Persist the altered in-memory version of the tool config.
        config_elems_to_xml_file( app, shed_tool_conf_dict )
    if app.toolbox_search.enabled:
        # If search support for tools is enabled, index the new installed tools.
        app.toolbox_search = ToolBoxSearch( app.toolbox )
def update_repository( current_working_dir, repo_files_dir, changeset_revision ):
    # Update the cloned repository to changeset_revision.  It is imperative that the 
    # installed repository is updated to the desired changeset_revision before metadata
    # is set because the process for setting metadata uses the repository files on disk.
    log.debug( 'Updating cloned repository to revision "%s"' % changeset_revision )
    cmd = 'hg update -r %s' % changeset_revision
    tmp_name = tempfile.NamedTemporaryFile().name
    tmp_stderr = open( tmp_name, 'wb' )
    os.chdir( repo_files_dir )
    proc = subprocess.Popen( cmd, shell=True, stderr=tmp_stderr.fileno() )
    returncode = proc.wait()
    os.chdir( current_working_dir )
    tmp_stderr.close()
    return returncode, tmp_name
