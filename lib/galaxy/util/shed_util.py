import os, sys, tempfile, shutil, subprocess, threading, logging
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

def add_shed_tool_conf_entry( app, shed_tool_conf, tool_panel_entry ):
    """
    Add an entry in the shed_tool_conf file. An entry looks something like:
    <section name="Filter and Sort" id="filter">
        <tool file="filter/filtering.xml" guid="toolshed.g2.bx.psu.edu/repos/test/filter/1.0.2"/>
    </section>
    This method is used by the InstallManager, which does not have access to trans.
    """
    # Make a backup of the hgweb.config file since we're going to be changing it.
    if not os.path.exists( shed_tool_conf ):
        output = open( shed_tool_conf, 'w' )
        output.write( '<?xml version="1.0"?>\n' )
        output.write( '<toolbox tool_path="%s">\n' % tool_path )
        output.write( '</toolbox>\n' )
        output.close()
    # Make a backup of the shed_tool_conf file.
    today = date.today()
    backup_date = today.strftime( "%Y_%m_%d" )
    shed_tool_conf_copy = '%s/%s_%s_backup' % ( app.config.root, shed_tool_conf, backup_date )
    shutil.copy( os.path.abspath( shed_tool_conf ), os.path.abspath( shed_tool_conf_copy ) )
    tmp_fd, tmp_fname = tempfile.mkstemp()
    new_shed_tool_conf = open( tmp_fname, 'wb' )
    for i, line in enumerate( open( shed_tool_conf ) ):
        if line.startswith( '</toolbox>' ):
            # We're at the end of the original config file, so add our entry.
            new_shed_tool_conf.write( '    ' )
            new_shed_tool_conf.write( util.xml_to_string( tool_panel_entry, pretty=True ) )
            new_shed_tool_conf.write( line )
        else:
            new_shed_tool_conf.write( line )
    new_shed_tool_conf.close()
    shutil.move( tmp_fname, os.path.abspath( shed_tool_conf ) )
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
def create_or_update_tool_shed_repository( app, name, description, changeset_revision, repository_clone_url, metadata_dict, owner='' ):
    # This method is used by the InstallManager, which does not have access to trans.
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
    else:
        tool_shed_repository = app.model.ToolShedRepository( tool_shed=tool_shed,
                                                             name=name,
                                                             description=description,
                                                             owner=owner,
                                                             installed_changeset_revision=changeset_revision,
                                                             changeset_revision=changeset_revision,
                                                             metadata=metadata_dict,
                                                             includes_datatypes=includes_datatypes )
    sa_session.add( tool_shed_repository )
    sa_session.flush()
def generate_datatypes_metadata( datatypes_config, metadata_dict ):
    """
    Update the received metadata_dict with changes that have been applied
    to the received datatypes_config.  This method is used by the InstallManager,
    which does not have access to trans.
    """
    # Parse datatypes_config.
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
def generate_metadata( toolbox, relative_install_dir, repository_clone_url, tool_section_dict=None ):
    """
    Browse the repository files on disk to generate metadata.  Since we are using disk files, it
    is imperative that the repository is updated to the desired change set revision before metadata
    is generated.  This method is used by the InstallManager, which does not have access to trans.
    """
    metadata_dict = {}
    sample_files = []
    datatypes_config = None
    # Keep track of the section in the tool panel in which this repository's tools will be contained.
    if tool_section_dict:
        metadata_dict[ 'tool_panel_section' ] = tool_section_dict
    else:
        metadata_dict[ 'tool_panel_section' ] = dict( id='', version='', name='' )
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
    """
    Update the received metadata_dict with changes that have been
    applied to the received tool.  This method is used by the InstallManager,
    which does not have access to trans.
    """
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
def generate_tool_panel_elem_list( repository_name, repository_clone_url, changeset_revision, repository_tools_tups, tool_section=None, owner='' ):
    """Generate a list of ElementTree Element objects for each section or list of tools."""
    elem_list = []
    tool_elem = None
    tmp_url = clean_repository_clone_url( repository_clone_url )
    if not owner:
        owner = get_repository_owner( tmp_url )
    if tool_section:
        root_elem = Element( 'section' )
        root_elem.attrib[ 'name' ] = tool_section.name
        root_elem.attrib[ 'id' ] = tool_section.id
        root_elem.attrib[ 'version' ] = tool_section.version
    for repository_tool_tup in repository_tools_tups:
        tool_file_path, guid, tool = repository_tool_tup
        if tool_section:
            tool_elem = SubElement( root_elem, 'tool' )
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
    if tool_section:
        elem_list.append( root_elem )
    elif tool_elem:
        elem_list.append( tool_elem )
    return elem_list
def generate_workflow_metadata( relative_path, exported_workflow_dict, metadata_dict ):
    """
    Update the received metadata_dict with changes that have been applied
    to the received exported_workflow_dict.  Store everything in the database.
    This method is used by the InstallManager, which does not have access to trans.
    """
    if 'workflows' in metadata_dict:
        metadata_dict[ 'workflows' ].append( ( relative_path, exported_workflow_dict ) )
    else:
        metadata_dict[ 'workflows' ] = [ ( relative_path, exported_workflow_dict ) ]
    return metadata_dict
def get_repository_by_shed_name_owner_changeset_revision( app, tool_shed, name, owner, changeset_revision ):
    # This method is used by the InstallManager, which does not have access to trans.
    sa_session = app.model.context.current
    if tool_shed.find( '//' ) > 0:
        tool_shed = tool_shed.split( '//' )[1]
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
def get_tool_id_guid_map( app, tool_id, version, tool_shed, repository_owner, repository_name ):
    # This method is used by the InstallManager, which does not have access to trans.
    sa_session = app.model.context.current
    return sa_session.query( app.model.ToolIdGuidMap ) \
                     .filter( and_( app.model.ToolIdGuidMap.table.c.tool_id == tool_id,
                                    app.model.ToolIdGuidMap.table.c.tool_version == version,
                                    app.model.ToolIdGuidMap.table.c.tool_shed == tool_shed,
                                    app.model.ToolIdGuidMap.table.c.repository_owner == repository_owner,
                                    app.model.ToolIdGuidMap.table.c.repository_name == repository_name ) ) \
                     .first()
def get_url_from_repository_tool_shed( app, repository ):
    """
    This method is used by the UpdateManager, which does not have access to trans.
    The stored value of repository.tool_shed is something like: toolshed.g2.bx.psu.edu
    We need the URL to this tool shed, which is something like: http://toolshed.g2.bx.psu.edu/
    """
    for shed_name, shed_url in app.tool_shed_registry.tool_sheds.items():
        if shed_url.find( repository.tool_shed ) >= 0:
            if shed_url.endswith( '/' ):
                shed_url = shed_url.rstrip( '/' )
            return shed_url
    # The tool shed from which the repository was originally
    # installed must no longer be configured in tool_sheds_conf.xml.
    return None
def handle_missing_data_table_entry( app, tool_path, sample_files, repository_tools_tups ):
    """
    Inspect each tool to see if any have input parameters that are dynamically
    generated select lists that require entries in the tool_data_table_conf.xml file.
    This method is used by the InstallManager, which does not have access to trans.
    """
    missing_data_table_entry = False
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        if repository_tool.params_with_missing_data_table_entry:
            missing_data_table_entry = True
            break
    if missing_data_table_entry:
        # The repository must contain a tool_data_table_conf.xml.sample file that includes
        # all required entries for all tools in the repository.
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
    """
    Inspect each tool to see if it has any input parameters that
    are dynamically generated select lists that depend on a .loc file.
    This method is used by the InstallManager, which does not have access to trans.
    """
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
    This method is used by the InstallManager, which does not have access to trans.
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
def load_datatype_items( app, repository, relative_install_dir, deactivate=False ):
    # Load proprietary datatypes.
    metadata = repository.metadata
    datatypes_config = metadata.get( 'datatypes_config', None )
    if datatypes_config:
        converter_path, display_path = load_datatypes( app, datatypes_config, relative_install_dir, deactivate=deactivate )
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
def load_datatypes( app, datatypes_config, relative_install_dir, deactivate=False ):
    # This method is used by the InstallManager, which does not have access to trans.
    def __import_module( relative_path, datatype_module ):
        sys.path.insert( 0, relative_path )
        imported_module = __import__( datatype_module )
        sys.path.pop( 0 )
        return imported_module
    imported_modules = []
    # Parse datatypes_config.
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
            # Import each of the datatype class modules.
            for relative_path_to_datatype_file_name in datatype_class_modules:
                relative_head, relative_tail = os.path.split( relative_path_to_datatype_file_name )
                registration = datatypes_config_root.find( 'registration' )
                # Get the module by parsing the <datatype> tag.
                for elem in registration.findall( 'datatype' ):
                    # A 'type' attribute is currently required.  The attribute
                    # should be something like one of the following: 
                    # type="gmap:GmapDB"
                    # type="galaxy.datatypes.gmap:GmapDB"
                    dtype = elem.get( 'type', None )
                    if dtype:
                        fields = dtype.split( ':' )
                        datatype_module = fields[ 0 ]
                        if datatype_module.find( '.' ) >= 0:
                            # Handle the case where datatype_module is "galaxy.datatypes.gmap"
                            datatype_module = datatype_module.split( '.' )[ -1 ]
                        datatype_class_name = fields[ 1 ]
                    # We need to change the value of sys.path, so do it in a way that is thread-safe.
                    lock = threading.Lock()
                    lock.acquire( True )
                    try:
                        imported_module = __import_module( relative_head, datatype_module )
                        if imported_module not in imported_modules:
                            imported_modules.append( imported_module )
                    except Exception, e:
                        log.debug( "Exception importing datatypes code file %s: %s" % ( str( relative_path_to_datatype_file_name ), str( e ) ) )
                    finally:
                        lock.release()
        # Handle data type converters and display applications.
        for elem in registration.findall( 'datatype' ):
            if not converter_path:
                # If any of the <datatype> tag sets contain <converter> tags, set the converter_path
                # if it is not already set.  This requires developers to place all converters in the
                # same subdirectory within the repository hierarchy.
                for converter in elem.findall( 'converter' ):
                    converter_config = converter.get( 'file', None )
                    if converter_config:
                        for root, dirs, files in os.walk( relative_install_dir ):
                            if root.find( '.hg' ) < 0:
                                for name in files:
                                    if name == converter_config:
                                        converter_path = root
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
                        for root, dirs, files in os.walk( relative_install_dir ):
                            if root.find( '.hg' ) < 0:
                                for name in files:
                                    if name == display_config:
                                        display_path = root
                                        break
                    if display_path:
                        break
            if converter_path and display_path:
                break
    else:
        # The repository includes a dataypes_conf.xml file, but no code file that
        # contains data type classes.  This implies that the data types in datayptes_conf.xml
        # are all subclasses of data types that are in the distribution.
        imported_modules = []
    # Load proprietary datatypes
    app.datatypes_registry.load_datatypes( root_dir=app.config.root, config=datatypes_config, imported_modules=imported_modules, deactivate=deactivate )
    return converter_path, display_path
def load_repository_contents( app, repository_name, description, owner, changeset_revision, tool_path, repository_clone_url, relative_install_dir,
                              current_working_dir, tmp_name, tool_shed=None, tool_section=None, shed_tool_conf=None, new_install=True ):
    # This method is used by the InstallManager, which does not have access to trans.
    # Generate the metadata for the installed tool shed repository.  It is imperative that
    # the installed repository is updated to the desired changeset_revision before metadata
    # is set because the process for setting metadata uses the repository files on disk.  This
    # method is called when new tools have been installed (in which case values should be received
    # for tool_section and shed_tool_conf, and new_install should be left at it's default value)
    # and when updates have been pulled to previously installed repositories (in which case the
    # default value None is set for tool_section and shed_tool_conf, and the value of new_install
    # is passed as False).
    if tool_section:
        section_id = tool_section.id
        section_version = tool_section.version
        section_name = tool_section.name
    else:
        section_id = ''
        section_version = ''
        section_name = ''
    tool_section_dict = dict( id=section_id, version=section_version, name=section_name )
    metadata_dict = generate_metadata( app.toolbox, relative_install_dir, repository_clone_url, tool_section_dict=tool_section_dict )
    if 'tools' in metadata_dict:
        repository_tools_tups = get_repository_tools_tups( app, metadata_dict )
        if repository_tools_tups:
            sample_files = metadata_dict.get( 'sample_files', [] )
            # Handle missing data table entries for tool parameters that are dynamically generated select lists.
            repository_tools_tups = handle_missing_data_table_entry( app, tool_path, sample_files, repository_tools_tups )
            # Handle missing index files for tool parameters that are dynamically generated select lists.
            repository_tools_tups = handle_missing_index_file( app, tool_path, sample_files, repository_tools_tups )
            # Handle tools that use fabric scripts to install dependencies.
            handle_tool_dependencies( current_working_dir, relative_install_dir, repository_tools_tups )
            if new_install:
                load_altered_part_of_tool_panel( app=app,
                                                 repository_name=repository_name,
                                                 repository_clone_url=repository_clone_url,
                                                 changeset_revision=changeset_revision,
                                                 repository_tools_tups=repository_tools_tups,
                                                 tool_section=tool_section,
                                                 shed_tool_conf=shed_tool_conf,
                                                 tool_path=tool_path,
                                                 owner=owner,
                                                 add_to_config=True )
            else:
                if app.toolbox_search.enabled:
                    # If search support for tools is enabled, index the new installed tools.
                    app.toolbox_search = ToolBoxSearch( app.toolbox )
            # Remove the temporary file
            try:
                os.unlink( tmp_name )
            except:
                pass
    if 'datatypes_config' in metadata_dict:
        datatypes_config = os.path.abspath( metadata_dict[ 'datatypes_config' ] )
        # Load data types required by tools.
        converter_path, display_path = load_datatypes( app, datatypes_config, relative_install_dir )
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
            app.datatypes_registry.load_datatype_converters( app.toolbox, installed_repository_dict=repository_dict )
        if display_path:
            # Load proprietary datatype display applications
            app.datatypes_registry.load_display_applications( installed_repository_dict=repository_dict )
    # Add a new record to the tool_shed_repository table if one doesn't
    # already exist.  If one exists but is marked deleted, undelete it.
    log.debug( "Adding new row (or updating an existing row) for repository '%s' in the tool_shed_repository table." % repository_name )
    create_or_update_tool_shed_repository( app, repository_name, description, changeset_revision, repository_clone_url, metadata_dict )
    return metadata_dict
def load_altered_part_of_tool_panel( app, repository_name, repository_clone_url, changeset_revision, repository_tools_tups,
                                     tool_section, shed_tool_conf, tool_path, owner, add_to_config=True ):
    # Generate a new entry for the tool config.
    elem_list = generate_tool_panel_elem_list( repository_name,
                                               repository_clone_url,
                                               changeset_revision,
                                               repository_tools_tups,
                                               tool_section=tool_section,
                                               owner=owner )
    if tool_section:
        for section_elem in elem_list:
            # Load the section into the tool panel.
            app.toolbox.load_section_tag_set( section_elem, app.toolbox.tool_panel, tool_path )
    else:
        # Load the tools into the tool panel outside of any sections.
        for tool_elem in elem_list:
            guid = tool_elem.get( 'guid' )
            app.toolbox.load_tool_tag_set( tool_elem, app.toolbox.tool_panel, tool_path=tool_path, guid=guid )
    if add_to_config:
        # Append the new entry (either section or list of tools) to the shed_tool_config file.
        for elem_entry in elem_list:
            add_shed_tool_conf_entry( app, shed_tool_conf, elem_entry )
    if app.toolbox_search.enabled:
        # If search support for tools is enabled, index the new installed tools.
        app.toolbox_search = ToolBoxSearch( app.toolbox )
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
