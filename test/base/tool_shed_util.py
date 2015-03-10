import logging
import os
import sys

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.append( cwd )

new_path = [ os.path.join( cwd, "lib" ) ]
if new_path not in sys.path:
    new_path.extend( sys.path )
    sys.path = new_path

from galaxy.util import parse_xml

log = logging.getLogger(__name__)

# Set a 10 minute timeout for repository installation.
repository_installation_timeout = 600


def get_installed_repository_info( elem, last_galaxy_test_file_dir, last_tested_repository_name, last_tested_changeset_revision, tool_path ):
    """
    Return the GALAXY_TEST_FILE_DIR, the containing repository name and the
    change set revision for the tool elem. This only happens when testing
    tools installed from the tool shed.
    """
    tool_config_path = elem.get( 'file' )
    installed_tool_path_items = tool_config_path.split( '/repos/' )
    sans_shed = installed_tool_path_items[ 1 ]
    path_items = sans_shed.split( '/' )
    repository_owner = path_items[ 0 ]
    repository_name = path_items[ 1 ]
    changeset_revision = path_items[ 2 ]
    if repository_name != last_tested_repository_name or changeset_revision != last_tested_changeset_revision:
        # Locate the test-data directory.
        installed_tool_path = os.path.join( installed_tool_path_items[ 0 ], 'repos', repository_owner, repository_name, changeset_revision )
        for root, dirs, files in os.walk( os.path.join(tool_path, installed_tool_path )):
            if '.' in dirs:
                dirs.remove( '.hg' )
            if 'test-data' in dirs:
                return os.path.join( root, 'test-data' ), repository_name, changeset_revision
        return None, repository_name, changeset_revision
    return last_galaxy_test_file_dir, last_tested_repository_name, last_tested_changeset_revision


def parse_tool_panel_config( config, shed_tools_dict ):
    """
    Parse a shed-related tool panel config to generate the shed_tools_dict. This only happens when testing tools installed from the tool shed.
    """
    last_galaxy_test_file_dir = None
    last_tested_repository_name = None
    last_tested_changeset_revision = None
    tool_path = None
    has_test_data = False
    tree = parse_xml( config )
    root = tree.getroot()
    tool_path = root.get('tool_path')
    for elem in root:
        if elem.tag == 'tool':
            galaxy_test_file_dir, \
                last_tested_repository_name, \
                last_tested_changeset_revision = get_installed_repository_info( elem,
                                                                                last_galaxy_test_file_dir,
                                                                                last_tested_repository_name,
                                                                                last_tested_changeset_revision,
                                                                                tool_path )
            if galaxy_test_file_dir:
                if not has_test_data:
                    has_test_data = True
                if galaxy_test_file_dir != last_galaxy_test_file_dir:
                    if not os.path.isabs( galaxy_test_file_dir ):
                        galaxy_test_file_dir = os.path.join( os.getcwd(), galaxy_test_file_dir )
                guid = elem.get( 'guid' )
                shed_tools_dict[ guid ] = galaxy_test_file_dir
                last_galaxy_test_file_dir = galaxy_test_file_dir
        elif elem.tag == 'section':
            for section_elem in elem:
                if section_elem.tag == 'tool':
                    galaxy_test_file_dir, \
                        last_tested_repository_name, \
                        last_tested_changeset_revision = get_installed_repository_info( section_elem,
                                                                                        last_galaxy_test_file_dir,
                                                                                        last_tested_repository_name,
                                                                                        last_tested_changeset_revision,
                                                                                        tool_path )
                    if galaxy_test_file_dir:
                        if not has_test_data:
                            has_test_data = True
                        if galaxy_test_file_dir != last_galaxy_test_file_dir:
                            if not os.path.isabs( galaxy_test_file_dir ):
                                galaxy_test_file_dir = os.path.join( os.getcwd(), galaxy_test_file_dir )
                        guid = section_elem.get( 'guid' )
                        shed_tools_dict[ guid ] = galaxy_test_file_dir
                        last_galaxy_test_file_dir = galaxy_test_file_dir
    return has_test_data, shed_tools_dict
