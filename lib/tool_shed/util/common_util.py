import logging
import os
import urllib2
from galaxy.util import json
from galaxy.util.odict import odict
from tool_shed.util import encoding_util
from tool_shed.util import xml_util

log = logging.getLogger( __name__ )

REPOSITORY_OWNER = 'devteam'

def accumulate_tool_dependencies( tool_shed_accessible, tool_dependencies, all_tool_dependencies ):
    if tool_shed_accessible:
        if tool_dependencies:
            for tool_dependency in tool_dependencies:
                if tool_dependency not in all_tool_dependencies:
                    all_tool_dependencies.append( tool_dependency )
    return all_tool_dependencies

def check_for_missing_tools( app, tool_panel_configs, latest_tool_migration_script_number ):
    # Get the 000x_tools.xml file associated with the current migrate_tools version number.
    tools_xml_file_path = os.path.abspath( os.path.join( 'scripts', 'migrate_tools', '%04d_tools.xml' % latest_tool_migration_script_number ) )
    # Parse the XML and load the file attributes for later checking against the proprietary tool_panel_config.
    migrated_tool_configs_dict = odict()
    tree, error_message = xml_util.parse_xml( tools_xml_file_path )
    if tree is None:
        return False, odict()
    root = tree.getroot()
    tool_shed = root.get( 'name' )
    tool_shed_url = get_tool_shed_url_from_tools_xml_file_path( app, tool_shed )
    # The default behavior is that the tool shed is down.
    tool_shed_accessible = False
    missing_tool_configs_dict = odict()
    if tool_shed_url:
        for elem in root:
            if elem.tag == 'repository':
                repository_dependencies = []
                all_tool_dependencies = []
                repository_name = elem.get( 'name' )
                changeset_revision = elem.get( 'changeset_revision' )
                tool_shed_accessible, repository_dependencies_dict = get_repository_dependencies( app,
                                                                                                  tool_shed_url,
                                                                                                  repository_name,
                                                                                                  REPOSITORY_OWNER,
                                                                                                  changeset_revision )
                # Accumulate all tool dependencies defined for repository dependencies for display to the user.
                for rd_key, rd_tups in repository_dependencies_dict.items():
                    if rd_key in [ 'root_key', 'description' ]:
                        continue
                    for rd_tup in rd_tups:
                        tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
                            parse_repository_dependency_tuple( rd_tup )
                    tool_shed_accessible, tool_dependencies = get_tool_dependencies( app,
                                                                                     tool_shed,
                                                                                     name,
                                                                                     owner,
                                                                                     changeset_revision )
                    all_tool_dependencies = accumulate_tool_dependencies( tool_shed_accessible, tool_dependencies, all_tool_dependencies )
                tool_shed_accessible, tool_dependencies = get_tool_dependencies( app, tool_shed_url, repository_name, REPOSITORY_OWNER, changeset_revision )
                all_tool_dependencies = accumulate_tool_dependencies( tool_shed_accessible, tool_dependencies, all_tool_dependencies )
                for tool_elem in elem.findall( 'tool' ):
                    tool_config_file_name = tool_elem.get( 'file' )
                    if tool_config_file_name:
                        # We currently do nothing with repository dependencies except install them (we do not display repositories that will be
                        # installed to the user).  However, we'll store them in the following dictionary in case we choose to display them in the
                        # future.
                        dependencies_dict = dict( tool_dependencies=all_tool_dependencies,
                                                  repository_dependencies=repository_dependencies )
                        migrated_tool_configs_dict[ tool_config_file_name ] = dependencies_dict
        if tool_shed_accessible:
            # Parse the proprietary tool_panel_configs (the default is tool_conf.xml) and generate the list of missing tool config file names.
            for tool_panel_config in tool_panel_configs:
                tree, error_message = xml_util.parse_xml( tool_panel_config )
                if tree:
                    root = tree.getroot()
                    for elem in root:
                        if elem.tag == 'tool':
                            missing_tool_configs_dict = check_tool_tag_set( elem, migrated_tool_configs_dict, missing_tool_configs_dict )
                        elif elem.tag == 'section':
                            for section_elem in elem:
                                if section_elem.tag == 'tool':
                                    missing_tool_configs_dict = check_tool_tag_set( section_elem, migrated_tool_configs_dict, missing_tool_configs_dict )
    else:
        exception_msg = '\n\nThe entry for the main Galaxy tool shed at %s is missing from the %s file.  ' % ( tool_shed, app.config.tool_sheds_config )
        exception_msg += 'The entry for this tool shed must always be available in this file, so re-add it before attempting to start your Galaxy server.\n'
        raise Exception( exception_msg )
    return tool_shed_accessible, missing_tool_configs_dict

def check_tool_tag_set( elem, migrated_tool_configs_dict, missing_tool_configs_dict ):
    file_path = elem.get( 'file', None )
    if file_path:
        path, name = os.path.split( file_path )
        for migrated_tool_config in migrated_tool_configs_dict.keys():
            if migrated_tool_config in [ file_path, name ]:
                missing_tool_configs_dict[ name ] = migrated_tool_configs_dict[ migrated_tool_config ]
    return missing_tool_configs_dict

def get_non_shed_tool_panel_configs( app ):
    """Get the non-shed related tool panel configs - there can be more than one, and the default is tool_conf.xml."""
    config_filenames = []
    for config_filename in app.config.tool_configs:
        # Any config file that includes a tool_path attribute in the root tag set like the following is shed-related.
        # <toolbox tool_path="../shed_tools">
        tree, error_message = xml_util.parse_xml( config_filename )
        if tree is None:
            continue
        root = tree.getroot()
        tool_path = root.get( 'tool_path', None )
        if tool_path is None:
            config_filenames.append( config_filename )
    return config_filenames

def get_repository_dependencies( app, tool_shed_url, repository_name, repository_owner, changeset_revision ):
    repository_dependencies_dict = {}
    tool_shed_accessible = True
    url = '%s/repository/get_repository_dependencies?name=%s&owner=%s&changeset_revision=%s' % \
    ( tool_shed_url, repository_name, repository_owner, changeset_revision )
    try:
        raw_text = tool_shed_get( app, tool_shed_url, url )
        tool_shed_accessible = True
    except Exception, e:
        tool_shed_accessible = False
        print "The URL\n%s\nraised the exception:\n%s\n" % ( url, str( e ) )
    if tool_shed_accessible:
        if len( raw_text ) > 2:
            encoded_text = json.from_json_string( raw_text )
            repository_dependencies_dict = encoding_util.tool_shed_decode( encoded_text )
    return tool_shed_accessible, repository_dependencies_dict

def get_tool_dependencies( app, tool_shed_url, repository_name, repository_owner, changeset_revision ):
    tool_dependencies = []
    tool_shed_accessible = True
    url = '%s/repository/get_tool_dependencies?name=%s&owner=%s&changeset_revision=%s&from_install_manager=True' % \
    ( tool_shed_url, repository_name, repository_owner, changeset_revision )
    try:
        text = tool_shed_get( app, tool_shed_url, url )
        tool_shed_accessible = True
    except Exception, e:
        tool_shed_accessible = False
        print "The URL\n%s\nraised the exception:\n%s\n" % ( url, str( e ) )
    if tool_shed_accessible:
        if text:
            tool_dependencies_dict = encoding_util.tool_shed_decode( text )
            for dependency_key, requirements_dict in tool_dependencies_dict.items():
                tool_dependency_name = requirements_dict[ 'name' ]
                tool_dependency_version = requirements_dict[ 'version' ]
                tool_dependency_type = requirements_dict[ 'type' ]
                tool_dependencies.append( ( tool_dependency_name, tool_dependency_version, tool_dependency_type ) )
    return tool_shed_accessible, tool_dependencies

def get_tool_shed_url_from_tools_xml_file_path( app, tool_shed ):
    search_str = '://%s' % tool_shed
    for shed_name, shed_url in app.tool_shed_registry.tool_sheds.items():
        if shed_url.find( search_str ) >= 0:
            if shed_url.endswith( '/' ):
                shed_url = shed_url.rstrip( '/' )
            return shed_url
    return None

def parse_repository_dependency_tuple( repository_dependency_tuple, contains_error=False ):
    # Default both prior_installation_required and only_if_compiling_contained_td to False in cases where metadata should be reset on the
    # repository containing the repository_dependency definition.
    prior_installation_required = 'False'
    only_if_compiling_contained_td = 'False'
    if contains_error:
        if len( repository_dependency_tuple ) == 5:
            tool_shed, name, owner, changeset_revision, error = repository_dependency_tuple
        elif len( repository_dependency_tuple ) == 6:
            toolshed, name, owner, changeset_revision, prior_installation_required, error = repository_dependency_tuple
        elif len( repository_dependency_tuple ) == 7:
            toolshed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td, error = repository_dependency_tuple
        return toolshed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td, error
    else:
        if len( repository_dependency_tuple ) == 4:
            tool_shed, name, owner, changeset_revision = repository_dependency_tuple
        elif len( repository_dependency_tuple ) == 5:
            tool_shed, name, owner, changeset_revision, prior_installation_required = repository_dependency_tuple
        elif len( repository_dependency_tuple ) == 6:
            tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = repository_dependency_tuple
        return tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td

def tool_shed_get( app, tool_shed_url, uri ):
    """Make contact with the tool shed via the uri provided."""
    registry = app.tool_shed_registry
    # urllib2 auto-detects system proxies, when passed a Proxyhandler.
    # Refer: http://docs.python.org/2/howto/urllib2.html#proxies
    proxy = urllib2.ProxyHandler()
    urlopener = urllib2.build_opener( proxy )
    urllib2.install_opener( urlopener )
    password_mgr = registry.password_manager_for_url( tool_shed_url )
    if password_mgr is not None:
        auth_handler = urllib2.HTTPBasicAuthHandler( password_mgr )
        urlopener.add_handler( auth_handler )
    response = urlopener.open( uri )
    content = response.read()
    response.close()
    return content
