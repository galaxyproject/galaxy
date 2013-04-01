import os
import urllib2
from galaxy import util
from galaxy.util.odict import odict
from tool_shed.util import encoding_util

REPOSITORY_OWNER = 'devteam'

def check_for_missing_tools( app, tool_panel_configs, latest_tool_migration_script_number ):
    # Get the 000x_tools.xml file associated with the current migrate_tools version number.
    tools_xml_file_path = os.path.abspath( os.path.join( 'scripts', 'migrate_tools', '%04d_tools.xml' % latest_tool_migration_script_number ) )
    # Parse the XML and load the file attributes for later checking against the proprietary tool_panel_config.
    migrated_tool_configs_dict = odict()
    tree = util.parse_xml( tools_xml_file_path )
    root = tree.getroot()
    tool_shed = root.get( 'name' )
    tool_shed_url = get_tool_shed_url_from_tools_xml_file_path( app, tool_shed )
    # The default behavior is that the tool shed is down.
    tool_shed_accessible = False
    if tool_shed_url:
        for elem in root:
            if elem.tag == 'repository':
                tool_dependencies = []
                tool_dependencies_dict = {}
                repository_name = elem.get( 'name' )
                changeset_revision = elem.get( 'changeset_revision' )
                url = '%s/repository/get_tool_dependencies?name=%s&owner=%s&changeset_revision=%s&from_install_manager=True' % \
                ( tool_shed_url, repository_name, REPOSITORY_OWNER, changeset_revision )
                try:
                    response = urllib2.urlopen( url )
                    text = response.read()
                    response.close()
                    tool_shed_accessible = True
                except Exception, e:
                    # Tool shed may be unavailable - we have to set tool_shed_accessible since we're looping.
                    tool_shed_accessible = False
                    print "The URL\n%s\nraised the exception:\n%s\n" % ( url, str( e ) )
                if tool_shed_accessible:
                    if text:
                        tool_dependencies_dict = encoding_util.tool_shed_decode( text )
                        for dependency_key, requirements_dict in tool_dependencies_dict.items():
                            tool_dependency_name = requirements_dict[ 'name' ]
                            tool_dependency_version = requirements_dict[ 'version' ]
                            tool_dependency_type = requirements_dict[ 'type' ]
                            tool_dependency_readme = requirements_dict.get( 'readme', '' )
                            tool_dependencies.append( ( tool_dependency_name, tool_dependency_version, tool_dependency_type, tool_dependency_readme ) )
                    for tool_elem in elem.findall( 'tool' ):
                        migrated_tool_configs_dict[ tool_elem.get( 'file' ) ] = tool_dependencies
        if tool_shed_accessible:
            # Parse the proprietary tool_panel_configs (the default is tool_conf.xml) and generate the list of missing tool config file names.
            missing_tool_configs_dict = odict()
            for tool_panel_config in tool_panel_configs:
                tree = util.parse_xml( tool_panel_config )
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
        if name in migrated_tool_configs_dict:
            tool_dependencies = migrated_tool_configs_dict[ name ]
            missing_tool_configs_dict[ name ] = tool_dependencies
    return missing_tool_configs_dict

def get_non_shed_tool_panel_configs( app ):
    # Get the non-shed related tool panel configs - there can be more than one, and the default is tool_conf.xml.
    config_filenames = []
    for config_filename in app.config.tool_configs:
        # Any config file that includes a tool_path attribute in the root tag set like the following is shed-related.
        # <toolbox tool_path="../shed_tools">
        tree = util.parse_xml( config_filename )
        root = tree.getroot()
        tool_path = root.get( 'tool_path', None )
        if tool_path is None:
            config_filenames.append( config_filename )
    return config_filenames

def get_tool_shed_url_from_tools_xml_file_path( app, tool_shed ):
    search_str = '://%s' % tool_shed
    for shed_name, shed_url in app.tool_shed_registry.tool_sheds.items():
        if shed_url.find( search_str ) >= 0:
            if shed_url.endswith( '/' ):
                shed_url = shed_url.rstrip( '/' )
            return shed_url
    return None
