import os, tempfile, shutil, logging, urllib2
from galaxy.datatypes import checkers
from galaxy.web import url_for
from galaxy import util
from galaxy.util.json import from_json_string, to_json_string
from galaxy.webapps.community.util import container_util
import shed_util_common as suc
from galaxy.tools.search import ToolBoxSearch
from galaxy.tool_shed.tool_dependencies.install_util import create_or_update_tool_dependency, install_package, set_environment
from galaxy.tool_shed import encoding_util
from galaxy.model.orm import and_

from galaxy import eggs
import pkg_resources

pkg_resources.require( 'mercurial' )
from mercurial import hg, ui, commands

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree, ElementInclude
from elementtree.ElementTree import Element, SubElement

log = logging.getLogger( __name__ )

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
    suc.config_elems_to_xml_file( app, config_elems, shed_tool_conf, tool_path )
def add_to_tool_panel( app, repository_name, repository_clone_url, changeset_revision, repository_tools_tups, owner, shed_tool_conf, tool_panel_dict,
                       new_install=True ):
    """A tool shed repository is being installed or updated so handle tool panel alterations accordingly."""
    # We need to change the in-memory version and the file system version of the shed_tool_conf file.
    index, shed_tool_conf_dict = suc.get_shed_tool_conf_dict( app, shed_tool_conf )
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
    if app.config.update_integrated_tool_panel:
        # Write the current in-memory version of the integrated_tool_panel.xml file to disk.
        app.toolbox.write_integrated_tool_panel_config_file()
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
                datatype_file_name_path, datatype_file_name = os.path.split( relative_path_to_datatype_file_name )
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
                        elem.attrib[ 'proprietary_path' ] = os.path.abspath( datatype_file_name_path )
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
def copy_sample_files( app, sample_files, tool_path=None, sample_files_copied=None, dest_path=None ):
    """
    Copy all appropriate files to dest_path in the local Galaxy environment that have not already been copied.  Those that have been copied
    are contained in sample_files_copied.  The default value for dest_path is ~/tool-data.  We need to be careful to copy only appropriate
    files here because tool shed repositories can contain files ending in .sample that should not be copied to the ~/tool-data directory.
    """
    filenames_not_to_copy = [ 'tool_data_table_conf.xml.sample' ]
    sample_files_copied = util.listify( sample_files_copied )
    for filename in sample_files:
        filename_sans_path = os.path.split( filename )[ 1 ]
        if filename_sans_path not in filenames_not_to_copy and filename not in sample_files_copied:
            if tool_path:
                filename=os.path.join( tool_path, filename )
            # Attempt to ensure we're copying an appropriate file.
            if is_data_index_sample_file( filename ):
                suc.copy_sample_file( app, filename, dest_path=dest_path )
def create_repository_dependency_objects( trans, tool_path, tool_shed_url, repo_info_dicts, reinstalling=False ):
    """
    Discover all repository dependencies and make sure all tool_shed_repository and associated repository_dependency records exist as well as
    the dependency relationships between installed repositories.  This method is called when new repositories are being installed into a Galaxy
    instance and when uninstalled repositories are being reinstalled.
    """
    message = ''
    created_or_updated_tool_shed_repositories = []
    # Repositories will be filtered (e.g., if already installed, etc), so filter the associated repo_info_dicts accordingly.
    filtered_repo_info_dicts = []
    # Discover all repository dependencies and retrieve information for installing them.
    all_repo_info_dicts = get_required_repo_info_dicts( tool_shed_url, repo_info_dicts )
    for repo_info_dict in all_repo_info_dicts:
        for name, repo_info_tuple in repo_info_dict.items():
            description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
                suc.get_repo_info_tuple_contents( repo_info_tuple )
            clone_dir = os.path.join( tool_path, generate_tool_path( repository_clone_url, changeset_revision ) )
            relative_install_dir = os.path.join( clone_dir, name )
            # Make sure the repository was not already installed.
            installed_tool_shed_repository, installed_changeset_revision = \
                repository_was_previously_installed( trans, tool_shed_url, name, repo_info_tuple, clone_dir )
            if installed_tool_shed_repository:
                if reinstalling:
                    if installed_tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.ERROR,
                                                                  trans.model.ToolShedRepository.installation_status.UNINSTALLED ]:
                        can_update = True
                        name = installed_tool_shed_repository.name
                        description = installed_tool_shed_repository.description
                        installed_changeset_revision = installed_tool_shed_repository.installed_changeset_revision
                        metadata_dict = installed_tool_shed_repository.metadata
                        dist_to_shed = installed_tool_shed_repository.dist_to_shed
                    else:
                        # There is a repository already installed which is a dependency of the repository being reinstalled.
                        can_update = False
                else:
                    # An attempt is being made to install a tool shed repository into a Galaxy instance when the same repository was previously installed.
                    message += "Revision <b>%s</b> of tool shed repository <b>%s</b> owned by <b>%s</b> " % ( changeset_revision, name, repository_owner )
                    if installed_changeset_revision != changeset_revision:
                        message += "was previously installed using changeset revision <b>%s</b>.  " % installed_changeset_revision
                    else:
                        message += "was previously installed.  "
                    if installed_tool_shed_repository.uninstalled:
                        message += "The repository has been uninstalled, however, so reinstall the original repository instead of installing it again.  "
                    elif installed_tool_shed_repository.deleted:
                        message += "The repository has been deactivated, however, so activate the original repository instead of installing it again.  "
                    if installed_changeset_revision != changeset_revision:
                        message += "You can get the latest updates for the repository using the <b>Get updates</b> option from the repository's "
                        message += "<b>Repository Actions</b> pop-up menu.  "
                    if len( repo_info_dicts ) == 1:
                        created_or_updated_tool_shed_repositories.append( installed_tool_shed_repository )
                        return created_or_updated_tool_shed_repositories, all_repo_info_dicts, filtered_repo_info_dicts, message
            else:
                # A tool shed repository is being installed into a Galaxy instance for the first time.  We may have the case where a repository
                # is being reinstalled where because the repository being newly installed here may be a dependency of the repository being reinstalled.
                can_update = True
                installed_changeset_revision = changeset_revision
                metadata_dict={}
                dist_to_shed = False
            if can_update:
                log.debug( "Adding new row (or updating an existing row) for repository '%s' in the tool_shed_repository table." % name )
                tool_shed_repository = suc.create_or_update_tool_shed_repository( app=trans.app,
                                                                                  name=name,
                                                                                  description=description,
                                                                                  installed_changeset_revision=changeset_revision,
                                                                                  ctx_rev=ctx_rev,
                                                                                  repository_clone_url=repository_clone_url,
                                                                                  metadata_dict={},
                                                                                  status=trans.model.ToolShedRepository.installation_status.NEW,
                                                                                  current_changeset_revision=changeset_revision,
                                                                                  owner=repository_owner,
                                                                                  dist_to_shed=False )
                created_or_updated_tool_shed_repositories.append( tool_shed_repository )
                filtered_repo_info_dicts.append( encoding_util.tool_shed_encode( repo_info_dict ) )
    return created_or_updated_tool_shed_repositories, all_repo_info_dicts, filtered_repo_info_dicts, message
def create_repository_dict_for_proprietary_datatypes( tool_shed, name, owner, installed_changeset_revision, tool_dicts, converter_path=None, display_path=None ):
    return dict( tool_shed=tool_shed,
                 repository_name=name,
                 repository_owner=owner,
                 installed_changeset_revision=installed_changeset_revision,
                 tool_dicts=tool_dicts,
                 converter_path=converter_path,
                 display_path=display_path )
def create_tool_dependency_objects( app, tool_shed_repository, relative_install_dir, set_status=True ):
    """Create or update a ToolDependency for each entry in tool_dependencies_config.  This method is called when installing a new tool_shed_repository."""
    tool_dependency_objects = []
    shed_config_dict = tool_shed_repository.get_shed_config_dict( app )
    if shed_config_dict.get( 'tool_path' ):
        relative_install_dir = os.path.join( shed_config_dict.get( 'tool_path' ), relative_install_dir )
    # Get the tool_dependencies.xml file from the repository.
    tool_dependencies_config = suc.get_config_from_disk( 'tool_dependencies.xml', relative_install_dir )
    try:
        tree = ElementTree.parse( tool_dependencies_config )
    except Exception, e:
        log.debug( "Exception attempting to parse tool_dependencies.xml: %s" %str( e ) )
        return tool_dependency_objects
    root = tree.getroot()
    ElementInclude.include( root )
    fabric_version_checked = False
    for elem in root:
        tool_dependency_type = elem.tag
        if tool_dependency_type == 'package':
            name = elem.get( 'name', None )
            version = elem.get( 'version', None )
            if name and version:
                tool_dependency = create_or_update_tool_dependency( app,
                                                                    tool_shed_repository,
                                                                    name=name,
                                                                    version=version,
                                                                    type=tool_dependency_type,
                                                                    status=app.model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                                    set_status=set_status )
                tool_dependency_objects.append( tool_dependency )
        elif tool_dependency_type == 'set_environment':
            for env_elem in elem:
                # <environment_variable name="R_SCRIPT_PATH" action="set_to">$REPOSITORY_INSTALL_DIR</environment_variable>
                name = env_elem.get( 'name', None )
                action = env_elem.get( 'action', None )
                if name and action:
                    tool_dependency = create_or_update_tool_dependency( app,
                                                                        tool_shed_repository,
                                                                        name=name,
                                                                        version=None,
                                                                        type=tool_dependency_type,
                                                                        status=app.model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                                        set_status=set_status )
                    tool_dependency_objects.append( tool_dependency )
    return tool_dependency_objects
def generate_tool_panel_elem_list( repository_name, repository_clone_url, changeset_revision, tool_panel_dict, repository_tools_tups, owner='' ):
    """Generate a list of ElementTree Element objects for each section or tool."""
    elem_list = []
    tool_elem = None
    cleaned_repository_clone_url = suc.clean_repository_clone_url( repository_clone_url )
    if not owner:
        owner = get_repository_owner( cleaned_repository_clone_url )
    tool_shed = cleaned_repository_clone_url.split( 'repos' )[ 0 ].rstrip( '/' )
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
                tool_elem = suc.generate_tool_elem( tool_shed, repository_name, changeset_revision, owner, tool_file_path, tool, tool_section )
            else:
                tool_elem = suc.generate_tool_elem( tool_shed, repository_name, changeset_revision, owner, tool_file_path, tool, None )
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
def generate_tool_panel_dict_for_tool_config( guid, tool_config, tool_sections=None ):
    """
    Create a dictionary of the following type for a single tool config file name.  The intent is to call this method for every tool config
    in a repository and append each of these as entries to a tool panel dictionary for the repository.  This allows for each tool to be
    loaded into a different section in the tool panel.
    {<Tool guid> : [{ tool_config : <tool_config_file>, id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}]}
    """
    tool_panel_dict = {}
    file_name = suc.strip_path( tool_config )
    tool_section_dicts = generate_tool_section_dicts( tool_config=file_name, tool_sections=tool_sections )
    tool_panel_dict[ guid ] = tool_section_dicts
    return tool_panel_dict
def generate_tool_path( repository_clone_url, changeset_revision ):
    """
    Generate a tool path that guarantees repositories with the same name will always be installed
    in different directories.  The tool path will be of the form:
    <tool shed url>/repos/<repository owner>/<repository name>/<installed changeset revision>
    http://test@bx.psu.edu:9009/repos/test/filter
    """
    tmp_url = suc.clean_repository_clone_url( repository_clone_url )
    # Now tmp_url is something like: bx.psu.edu:9009/repos/some_username/column
    items = tmp_url.split( 'repos' )
    tool_shed_url = items[ 0 ]
    repo_path = items[ 1 ]
    tool_shed_url = suc.clean_tool_shed_url( tool_shed_url )
    return suc.url_join( tool_shed_url, 'repos', repo_path, changeset_revision )
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
def get_config( config_file, repo, ctx, dir ):
    """Return the latest version of config_filename from the repository manifest."""
    config_file = suc.strip_path( config_file )
    for changeset in suc.reversed_upper_bounded_changelog( repo, ctx ):
        changeset_ctx = repo.changectx( changeset )
        for ctx_file in changeset_ctx.files():
            ctx_file_name = suc.strip_path( ctx_file )
            if ctx_file_name == config_file:
                return suc.get_named_tmpfile_from_ctx( changeset_ctx, ctx_file, dir )
    return None
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
                    converter_config_file_name = suc.strip_path( converter_config )
                    for root, dirs, files in os.walk( relative_install_dir ):
                        if root.find( '.hg' ) < 0:
                            for name in files:
                                if name == converter_config_file_name:
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
                    display_config_file_name = suc.strip_path( display_config )
                    for root, dirs, files in os.walk( relative_install_dir ):
                        if root.find( '.hg' ) < 0:
                            for name in files:
                                if name == display_config_file_name:
                                    # The value of display_path must be absolute due to job_working_directory.
                                    display_path = os.path.abspath( root )
                                    break
                if display_path:
                    break
        if converter_path and display_path:
            break
    return converter_path, display_path
def get_headers( fname, sep, count=60, is_multi_byte=False ):
    """Returns a list with the first 'count' lines split by 'sep'."""
    headers = []
    for idx, line in enumerate( file( fname ) ):
        line = line.rstrip( '\n\r' )
        if is_multi_byte:
            line = unicode( line, 'utf-8' )
            sep = sep.encode( 'utf-8' )
        headers.append( line.split( sep ) )
        if idx == count:
            break
    return headers
def get_installed_and_missing_tool_dependencies( trans, repository, all_tool_dependencies ):
    if all_tool_dependencies:
        tool_dependencies = {}
        missing_tool_dependencies = {}
        for td_key, val in all_tool_dependencies.items():
            if td_key in [ 'set_environment' ]:
                for index, td_info_dict in enumerate( val ):
                    name = td_info_dict[ 'name' ]
                    version = None
                    type = td_info_dict[ 'type' ]
                    tool_dependency = get_tool_dependency_by_name_type_repository( trans, repository, name, type )
                    if tool_dependency:
                        td_info_dict[ 'repository_id' ] = repository.id
                        td_info_dict[ 'tool_dependency_id' ] = tool_dependency.id
                        td_info_dict[ 'status' ] = str( tool_dependency.status )
                        val[ index ] = td_info_dict
                        if tool_dependency.status == trans.model.ToolDependency.installation_status.INSTALLED:
                            tool_dependencies[ td_key ] = val
                        else:
                            missing_tool_dependencies[ td_key ] = val
            else:
                name = val[ 'name' ]
                version = val[ 'version' ]
                type = val[ 'type' ]
                tool_dependency = get_tool_dependency_by_name_version_type_repository( trans, repository, name, version, type )
                if tool_dependency:
                    val[ 'repository_id' ] = repository.id
                    val[ 'tool_dependency_id' ] = tool_dependency.id
                    val[ 'status' ] = str( tool_dependency.status )
                    if tool_dependency.status == trans.model.ToolDependency.installation_status.INSTALLED:
                        tool_dependencies[ td_key ] = val
                    else:
                        missing_tool_dependencies[ td_key ] = val
    else:
        tool_dependencies = None
        missing_tool_dependencies = None
    return tool_dependencies, missing_tool_dependencies
def get_repository_owner( cleaned_repository_url ):
    items = cleaned_repository_url.split( 'repos' )
    repo_path = items[ 1 ]
    if repo_path.startswith( '/' ):
        repo_path = repo_path.replace( '/', '', 1 )
    return repo_path.lstrip( '/' ).split( '/' )[ 0 ]
def get_repository_owner_from_clone_url( repository_clone_url ):
    tmp_url = suc.clean_repository_clone_url( repository_clone_url )
    tool_shed = tmp_url.split( 'repos' )[ 0 ].rstrip( '/' )
    return get_repository_owner( tmp_url )
def get_required_repo_info_dicts( tool_shed_url, repo_info_dicts ):
    """
    Inspect the list of repo_info_dicts for repository dependencies and append a repo_info_dict for each of them to the list.  All
    repository_dependencies entries in each of the received repo_info_dicts includes all required repositories, so only one pass through
    this methid is required to retrieve all repository dependencies.
    """
    if repo_info_dicts:
        all_repo_info_dicts = [ rid for rid in repo_info_dicts ]
        # We'll send tuples of ( tool_shed, repository_name, repository_owner, changeset_revision ) to the tool shed to discover repository ids.
        required_repository_tups = []
        for repo_info_dict in repo_info_dicts:
            for repository_name, repo_info_tup in repo_info_dict.items():
                description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
                    suc.get_repo_info_tuple_contents( repo_info_tup )
                if repository_dependencies:
                    for key, val in repository_dependencies.items():
                        if key in [ 'root_key', 'description' ]:
                            continue
                        toolshed, name, owner, changeset_revision = container_util.get_components_from_key( key )
                        components_list = [ toolshed, name, owner, changeset_revision ]
                        if components_list not in required_repository_tups:
                            required_repository_tups.append( components_list )
                        for components_list in val:
                            if components_list not in required_repository_tups:
                                required_repository_tups.append( components_list )
            if required_repository_tups:
                # The value of required_repository_tups is a list of tuples, so we need to encode it.
                encoded_required_repository_tups = []
                for required_repository_tup in required_repository_tups:
                    encoded_required_repository_tups.append( encoding_util.encoding_sep.join( required_repository_tup ) )
                encoded_required_repository_str = encoding_util.encoding_sep2.join( encoded_required_repository_tups )
                encoded_required_repository_str = encoding_util.tool_shed_encode( encoded_required_repository_str )
                url = suc.url_join( tool_shed_url, '/repository/get_required_repo_info_dict?encoded_str=%s' % encoded_required_repository_str )
                response = urllib2.urlopen( url )
                text = response.read()
                response.close()
                if text:
                    required_repo_info_dict = from_json_string( text )                        
                    required_repo_info_dicts = []
                    encoded_dict_strings = required_repo_info_dict[ 'repo_info_dicts' ]
                    for encoded_dict_str in encoded_dict_strings:
                        decoded_dict = encoding_util.tool_shed_decode( encoded_dict_str )
                        required_repo_info_dicts.append( decoded_dict )                        
                    if required_repo_info_dicts:                            
                        for required_repo_info_dict in required_repo_info_dicts:
                            if required_repo_info_dict not in all_repo_info_dicts:
                                all_repo_info_dicts.append( required_repo_info_dict )
    return all_repo_info_dicts
def get_tool_index_sample_files( sample_files ):
    """Try to return the list of all appropriate tool data sample files included in the repository."""
    tool_index_sample_files = []
    for s in sample_files:
        # The problem with this is that Galaxy does not follow a standard naming convention for file names.
        if s.endswith( '.loc.sample' ) or s.endswith( '.xml.sample' ) or s.endswith( '.txt.sample' ):
            tool_index_sample_files.append( str( s ) )
    return tool_index_sample_files
def get_tool_dependency( trans, id ):
    """Get a tool_dependency from the database via id"""
    return trans.sa_session.query( trans.model.ToolDependency ).get( trans.security.decode_id( id ) )
def get_tool_dependency_by_name_type_repository( trans, repository, name, type ):
    return trans.sa_session.query( trans.model.ToolDependency ) \
                           .filter( and_( trans.model.ToolDependency.table.c.tool_shed_repository_id == repository.id,
                                          trans.model.ToolDependency.table.c.name == name,
                                          trans.model.ToolDependency.table.c.type == type ) ) \
                           .first()
def get_tool_dependency_by_name_version_type_repository( trans, repository, name, version, type ):
    return trans.sa_session.query( trans.model.ToolDependency ) \
                           .filter( and_( trans.model.ToolDependency.table.c.tool_shed_repository_id == repository.id,
                                          trans.model.ToolDependency.table.c.name == name,
                                          trans.model.ToolDependency.table.c.version == version,
                                          trans.model.ToolDependency.table.c.type == type ) ) \
                           .first()
def get_tool_dependency_ids( as_string=False, **kwd ):
    tool_dependency_id = kwd.get( 'tool_dependency_id', None )
    tool_dependency_ids = util.listify( kwd.get( 'tool_dependency_ids', None ) )
    if not tool_dependency_ids:
        tool_dependency_ids = util.listify( kwd.get( 'id', None ) )
    if tool_dependency_id and tool_dependency_id not in tool_dependency_ids:
        tool_dependency_ids.append( tool_dependency_id )
    if as_string:
        return ','.join( tool_dependency_ids )
    return tool_dependency_ids
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
def get_update_to_changeset_revision_and_ctx_rev( trans, repository ):
    """Return the changeset revision hash to which the repository can be updated."""
    tool_shed_url = suc.get_url_from_repository_tool_shed( trans.app, repository )
    url = suc.url_join( tool_shed_url, 'repository/get_changeset_revision_and_ctx_rev?name=%s&owner=%s&changeset_revision=%s' % \
        ( repository.name, repository.owner, repository.installed_changeset_revision ) )
    try:
        response = urllib2.urlopen( url )
        encoded_update_dict = response.read()
        if encoded_update_dict:
            update_dict = encoding_util.tool_shed_decode( encoded_update_dict )
            changeset_revision = update_dict[ 'changeset_revision' ]
            ctx_rev = update_dict[ 'ctx_rev' ]
        response.close()
    except Exception, e:
        log.debug( "Error getting change set revision for update from the tool shed for repository '%s': %s" % ( repository.name, str( e ) ) )
        changeset_revision = None
        ctx_rev = None
    return changeset_revision, ctx_rev
def handle_missing_data_table_entry( app, relative_install_dir, tool_path, repository_tools_tups ):
    """
    Inspect each tool to see if any have input parameters that are dynamically generated select lists that require entries in the
    tool_data_table_conf.xml file.  This method is called only from Galaxy (not the tool shed) when a repository is being installed
    or reinstalled.
    """
    missing_data_table_entry = False
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        if repository_tool.params_with_missing_data_table_entry:
            missing_data_table_entry = True
            break
    if missing_data_table_entry:
        # The repository must contain a tool_data_table_conf.xml.sample file that includes all required entries for all tools in the repository.
        sample_tool_data_table_conf = suc.get_config_from_disk( 'tool_data_table_conf.xml.sample', relative_install_dir )
        if sample_tool_data_table_conf:
            # Add entries to the ToolDataTableManager's in-memory data_tables dictionary as well as the list of data_table_elems and the list of
            # data_table_elem_names.
            error, message = suc.handle_sample_tool_data_table_conf_file( app, sample_tool_data_table_conf, persist=True )
            if error:
                # TODO: Do more here than logging an exception.
                log.debug( message )
        # Reload the tool into the local list of repository_tools_tups.
        repository_tool = app.toolbox.load_tool( os.path.join( tool_path, tup_path ), guid=guid )
        repository_tools_tups[ index ] = ( tup_path, guid, repository_tool )
        # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
        suc.reset_tool_data_tables( app )
    return repository_tools_tups
def handle_missing_index_file( app, tool_path, sample_files, repository_tools_tups, sample_files_copied ):
    """
    Inspect each tool to see if it has any input parameters that are dynamically generated select lists that depend on a .loc file.
    This method is not called from the tool shed, but from Galaxy when a repository is being installed.
    """
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        params_with_missing_index_file = repository_tool.params_with_missing_index_file
        for param in params_with_missing_index_file:
            options = param.options
            missing_file_name = suc.strip_path( options.missing_index_file )
            if missing_file_name not in sample_files_copied:
                # The repository must contain the required xxx.loc.sample file.
                for sample_file in sample_files:
                    sample_file_name = suc.strip_path( sample_file )
                    if sample_file_name == '%s.sample' % missing_file_name:
                        suc.copy_sample_file( app, sample_file )
                        if options.tool_data_table and options.tool_data_table.missing_index_file:
                            options.tool_data_table.handle_found_index_file( options.missing_index_file )
                        sample_files_copied.append( options.missing_index_file )
                        break
        # Reload the tool into the local list of repository_tools_tups.
        repository_tool = app.toolbox.load_tool( os.path.join( tool_path, tup_path ), guid=guid )
        repository_tools_tups[ index ] = ( tup_path, guid, repository_tool )
    return repository_tools_tups, sample_files_copied
def handle_tool_dependencies( app, tool_shed_repository, tool_dependencies_config, tool_dependencies ):
    """
    Install and build tool dependencies defined in the tool_dependencies_config.  This config's tag sets can currently refer to installation
    methods in Galaxy's tool_dependencies module.  In the future, proprietary fabric scripts contained in the repository will be supported.
    Future enhancements to handling tool dependencies may provide installation processes in addition to fabric based processes.  The dependencies
    will be installed in:
    ~/<app.config.tool_dependency_dir>/<package_name>/<package_version>/<repo_owner>/<repo_name>/<repo_installed_changeset_revision>
    """
    installed_tool_dependencies = []
    # Parse the tool_dependencies.xml config.
    tree = ElementTree.parse( tool_dependencies_config )
    root = tree.getroot()
    ElementInclude.include( root )
    fabric_version_checked = False
    for elem in root:
        if elem.tag == 'package':
            # Only install the tool_dependency if it is not already installed.
            package_name = elem.get( 'name', None )
            package_version = elem.get( 'version', None )
            if package_name and package_version:
                for tool_dependency in tool_dependencies:
                    if tool_dependency.name==package_name and tool_dependency.version==package_version:
                        break
                if tool_dependency.can_install:
                    tool_dependency = install_package( app, elem, tool_shed_repository, tool_dependencies=tool_dependencies )
                    if tool_dependency and tool_dependency.status in [ app.model.ToolDependency.installation_status.INSTALLED,
                                                                       app.model.ToolDependency.installation_status.ERROR ]:
                        installed_tool_dependencies.append( tool_dependency )
        elif elem.tag == 'set_environment':
            tool_dependency = set_environment( app, elem, tool_shed_repository )
            if tool_dependency and tool_dependency.status in [ app.model.ToolDependency.installation_status.INSTALLED,
                                                               app.model.ToolDependency.installation_status.ERROR ]:
                installed_tool_dependencies.append( tool_dependency )
    return installed_tool_dependencies
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
def is_column_based( fname, sep='\t', skip=0, is_multi_byte=False ):
    """See if the file is column based with respect to a separator."""
    headers = get_headers( fname, sep, is_multi_byte=is_multi_byte )
    count = 0
    if not headers:
        return False
    for hdr in headers[ skip: ]:
        if hdr and hdr[ 0 ] and not hdr[ 0 ].startswith( '#' ):
            if len( hdr ) > 1:
                count = len( hdr )
            break
    if count < 2:
        return False
    for hdr in headers[ skip: ]:
        if hdr and hdr[ 0 ] and not hdr[ 0 ].startswith( '#' ):
            if len( hdr ) != count:
                return False
    return True
def is_data_index_sample_file( file_path ):
    """
    Attempt to determine if a .sample file is appropriate for copying to ~/tool-data when a tool shed repository is being installed
    into a Galaxy instance.
    """
    # Currently most data index files are tabular, so check that first.  We'll assume that if the file is tabular, it's ok to copy.
    if is_column_based( file_path ):
        return True
    # If the file is any of the following, don't copy it.
    if checkers.check_html( file_path ):
        return False
    if checkers.check_image( file_path ):
        return False
    if checkers.check_binary( name=file_path ):
        return False
    if checkers.is_bz2( file_path ):
        return False
    if checkers.is_gzip( file_path ):
        return False
    if checkers.check_zip( file_path ):
        return False
    # Default to copying the file if none of the above are true.
    return True
def load_installed_datatype_converters( app, installed_repository_dict, deactivate=False ):
    # Load or deactivate proprietary datatype converters
    app.datatypes_registry.load_datatype_converters( app.toolbox, installed_repository_dict=installed_repository_dict, deactivate=deactivate )
def load_installed_datatypes( app, repository, relative_install_dir, deactivate=False ):
    # Load proprietary datatypes and return information needed for loading proprietary datatypes converters and display applications later.
    metadata = repository.metadata
    repository_dict = None
    datatypes_config = suc.get_config_from_disk( 'datatypes_conf.xml', relative_install_dir )
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
    return repository_dict
def load_installed_display_applications( app, installed_repository_dict, deactivate=False ):
    # Load or deactivate proprietary datatype display applications
    app.datatypes_registry.load_display_applications( installed_repository_dict=installed_repository_dict, deactivate=deactivate )
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
def populate_containers_dict_from_repository_metadata( trans, tool_shed_url, tool_path, repository, reinstalling=False ):
    """
    Retrieve necessary information from the received repository's metadata to populate the containers_dict for display.  This methos is called only
    from Galaxy (not the tool shed) when displaying repository dependencies for installed repositories and when displaying them for uninstalled
    repositories that are being reinstalled.
    """
    metadata = repository.metadata
    if metadata:
        datatypes = metadata.get( 'datatypes', None )
        invalid_tools = metadata.get( 'invalid_tools', None )
        if repository.has_readme_files:
            if reinstalling:
                # Since we're reinstalling, we need to sned a request to the tool shed to get the README files.
                url = suc.url_join( tool_shed_url,
                                    'repository/get_readme_files?name=%s&owner=%s&changeset_revision=%s' % \
                                    ( repository.name, repository.owner, repository.installed_changeset_revision ) )
                response = urllib2.urlopen( url )
                raw_text = response.read()
                response.close()
                readme_files_dict = from_json_string( raw_text )
            else:
                readme_files_dict = suc.build_readme_files_dict( repository.metadata, tool_path )
        else:
            readme_files_dict = None
        repository_dependencies_dict_for_display = {}
        if repository.has_repository_dependencies:
            rd_tups = []
            # We need to add a root_key entry to the repository_dependencies dictionary for proper display parsing.
            root_key = container_util.generate_repository_dependencies_key_for_repository( repository.tool_shed,
                                                                                           repository.name,
                                                                                           repository.owner,
                                                                                           repository.installed_changeset_revision )            
            # The repository dependencies container will include only the immediate repository dependencies of this repository, so
            # the container will be only a single level in depth.
            for rr in repository.required_repositories:
                rd_tup = [ rr.tool_shed, rr.name, rr.owner, rr.changeset_revision, rr.id, rr.status ]
                rd_tups.append( rd_tup )
            repository_dependencies_dict_for_display[ 'root_key' ] = root_key
            repository_dependencies_dict_for_display[ root_key ] = rd_tups
            # Get the description from the metadata in case it has a value.
            repository_dependencies = metadata.get( 'repository_dependencies', {} )
            repository_dependencies_dict_for_display[ 'description' ] = repository_dependencies.get( 'description', None )
        all_tool_dependencies = metadata.get( 'tool_dependencies', None )
        tool_dependencies, missing_tool_dependencies = get_installed_and_missing_tool_dependencies( trans, repository, all_tool_dependencies )
        if reinstalling:
            # All tool dependencies will be considered missing since we are reinstalling the repository.
            if tool_dependencies:
                for td in tool_dependencies:
                    missing_tool_dependencies.append( td )
                tool_dependencies = None
        valid_tools = metadata.get( 'tools', None )
        workflows = metadata.get( 'workflows', None )
        containers_dict = suc.build_repository_containers_for_galaxy( trans=trans,
                                                                      toolshed_base_url=tool_shed_url,
                                                                      repository_name=repository.name,
                                                                      repository_owner=repository.owner,
                                                                      changeset_revision=repository.installed_changeset_revision,
                                                                      repository=repository,
                                                                      datatypes=datatypes,
                                                                      invalid_tools=invalid_tools,
                                                                      missing_tool_dependencies=missing_tool_dependencies,
                                                                      readme_files_dict=readme_files_dict,
                                                                      repository_dependencies=repository_dependencies_dict_for_display,
                                                                      tool_dependencies=tool_dependencies,
                                                                      valid_tools=valid_tools,
                                                                      workflows=workflows )
    else:
        containers_dict = dict( datatypes=None,
                                invalid_tools=None,
                                readme_files_dict=None,
                                repository_dependencies=None,
                                tool_dependencies=None,
                                valid_tools=None,
                                workflows=None )
    return containers_dict
def pull_repository( repo, repository_clone_url, ctx_rev ):
    """Pull changes from a remote repository to a local one."""
    commands.pull( suc.get_configured_ui(), repo, source=repository_clone_url, rev=[ ctx_rev ] )
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
    suc.config_elems_to_xml_file( trans.app, config_elems, shed_tool_conf, tool_path )
def remove_from_tool_panel( trans, repository, shed_tool_conf, uninstall ):
    """A tool shed repository is being deactivated or uninstalled so handle tool panel alterations accordingly."""
    # Determine where the tools are currently defined in the tool panel and store this information so the tools can be displayed
    # in the same way when the repository is activated or reinstalled.
    tool_panel_dict = suc.generate_tool_panel_dict_from_shed_tool_conf_entries( trans.app, repository )
    repository.metadata[ 'tool_panel_section' ] = tool_panel_dict
    trans.sa_session.add( repository )
    trans.sa_session.flush()
    # Create a list of guids for all tools that will be removed from the in-memory tool panel and config file on disk.
    guids_to_remove = [ k for k in tool_panel_dict.keys() ]
    # Remove the tools from the toolbox's tools_by_id dictionary.
    for guid_to_remove in guids_to_remove:
        if guid_to_remove in trans.app.toolbox.tools_by_id:
            del trans.app.toolbox.tools_by_id[ guid_to_remove ]
    index, shed_tool_conf_dict = suc.get_shed_tool_conf_dict( trans.app, shed_tool_conf )
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
                if tool_elem in config_elem:
                    # Remove the tool sub-element from the section element.
                    config_elem.remove( tool_elem )
                # Remove the tool from the section in the in-memory tool panel.
                if section_key in trans.app.toolbox.tool_panel:
                    tool_section = trans.app.toolbox.tool_panel[ section_key ]
                    guid = tool_elem.get( 'guid' )
                    tool_key = 'tool_%s' % str( guid )
                    # Get the list of versions of this tool that are currently available in the toolbox.
                    available_tool_versions = trans.app.toolbox.get_loaded_tools_by_lineage( guid )
                    if tool_key in tool_section.elems:
                        if available_tool_versions:
                            available_tool_versions.reverse()
                            replacement_tool_key = None
                            replacement_tool_version = None
                            # Since we are going to remove the tool from the section, replace it with the newest loaded version of the tool.
                            for available_tool_version in available_tool_versions:
                                if available_tool_version.id in tool_section.elems.keys():
                                    replacement_tool_key = 'tool_%s' % str( available_tool_version.id )
                                    replacement_tool_version = available_tool_version
                                    break
                            if replacement_tool_key and replacement_tool_version:
                                # Get the index of the tool_key in the tool_section.
                                for tool_section_elems_index, key in enumerate( tool_section.elems.keys() ):
                                    if key == tool_key:
                                        break
                                # Remove the tool from the tool section.
                                del tool_section.elems[ tool_key ]
                                # Add the replacement tool at the same location in the tool section.
                                tool_section.elems.insert( tool_section_elems_index, replacement_tool_key, replacement_tool_version )
                            else:
                                del tool_section.elems[ tool_key ]
                        else:
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
            guid = config_elem.get( 'guid' )
            if guid in guids_to_remove:
                tool_key = 'tool_%s' % str( config_elem.get( 'guid' ) )
                # Get the list of versions of this tool that are currently available in the toolbox.
                available_tool_versions = trans.app.toolbox.get_loaded_tools_by_lineage( guid )
                if tool_key in trans.app.toolbox.tool_panel:
                    if available_tool_versions:
                        available_tool_versions.reverse()
                        replacement_tool_key = None
                        replacement_tool_version = None
                        # Since we are going to remove the tool from the section, replace it with the newest loaded version of the tool.
                        for available_tool_version in available_tool_versions:
                            if available_tool_version.id in trans.app.toolbox.tool_panel.keys():
                                replacement_tool_key = 'tool_%s' % str( available_tool_version.id )
                                replacement_tool_version = available_tool_version
                                break
                        if replacement_tool_key and replacement_tool_version:
                            # Get the index of the tool_key in the tool_section.
                            for tool_panel_index, key in enumerate( trans.app.toolbox.tool_panel.keys() ):
                                if key == tool_key:
                                    break
                            # Remove the tool from the tool panel.
                            del trans.app.toolbox.tool_panel[ tool_key ]
                            # Add the replacement tool at the same location in the tool panel.
                            trans.app.toolbox.tool_panel.insert( tool_panel_index, replacement_tool_key, replacement_tool_version )
                        else:
                            del trans.app.toolbox.tool_panel[ tool_key ]
                    else:
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
    trans.app.toolbox_search = ToolBoxSearch( trans.app.toolbox )
    if uninstall and trans.app.config.update_integrated_tool_panel:
        # Write the current in-memory version of the integrated_tool_panel.xml file to disk.
        trans.app.toolbox.write_integrated_tool_panel_config_file()
def remove_tool_dependency( trans, tool_dependency ):
    dependency_install_dir = tool_dependency.installation_directory( trans.app )
    removed, error_message = suc.remove_tool_dependency_installation_directory( dependency_install_dir )
    if removed:
        tool_dependency.status = trans.model.ToolDependency.installation_status.UNINSTALLED
        tool_dependency.error_message = None
        trans.sa_session.add( tool_dependency )
        trans.sa_session.flush()
    return removed, error_message
def repository_was_previously_installed( trans, tool_shed_url, repository_name, repo_info_tuple, clone_dir ):
    """
    Handle the case where the repository was previously installed using an older changeset_revsion, but later the repository was updated
    in the tool shed and now we're trying to install the latest changeset revision of the same repository instead of updating the one
    that was previously installed.  We'll look in the database instead of on disk since the repository may be uninstalled.
    """
    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
        suc.get_repo_info_tuple_contents( repo_info_tuple )
    tool_shed = suc.get_tool_shed_from_clone_url( repository_clone_url )
    # Get all previous change set revisions from the tool shed for the repository back to, but excluding, the previous valid changeset
    # revision to see if it was previously installed using one of them.
    url = suc.url_join( tool_shed_url,
                        'repository/previous_changeset_revisions?galaxy_url=%s&name=%s&owner=%s&changeset_revision=%s' % \
                        ( url_for( '/', qualified=True ), repository_name, repository_owner, changeset_revision ) )
    response = urllib2.urlopen( url )
    text = response.read()
    response.close()
    if text:
        #clone_path, clone_directory = os.path.split( clone_dir )
        changeset_revisions = util.listify( text )
        for previous_changeset_revision in changeset_revisions:
            tool_shed_repository = suc.get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( trans.app,
                                                                                                                 tool_shed,
                                                                                                                 repository_name,
                                                                                                                 repository_owner,
                                                                                                                 previous_changeset_revision )
            if tool_shed_repository and tool_shed_repository.status not in [ trans.model.ToolShedRepository.installation_status.NEW ]:
                return tool_shed_repository, previous_changeset_revision
    return None, None
def update_tool_shed_repository_status( app, tool_shed_repository, status ):
    sa_session = app.model.context.current
    tool_shed_repository.status = status
    sa_session.add( tool_shed_repository )
    sa_session.flush()
