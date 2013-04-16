import logging
import os
from galaxy.util import json
import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_util

log = logging.getLogger( __name__ )

def build_readme_files_dict( metadata, tool_path=None ):
    """Return a dictionary of valid readme file name <-> readme file content pairs for all readme files contained in the received metadata."""
    readme_files_dict = {}
    if metadata:
        if 'readme_files' in metadata:
            for relative_path_to_readme_file in metadata[ 'readme_files' ]:
                readme_file_name = os.path.split( relative_path_to_readme_file )[ 1 ]
                if tool_path:
                    full_path_to_readme_file = os.path.abspath( os.path.join( tool_path, relative_path_to_readme_file ) )
                else:
                    full_path_to_readme_file = os.path.abspath( relative_path_to_readme_file )
                try:
                    f = open( full_path_to_readme_file, 'r' )
                    text = f.read()
                    f.close()
                    readme_files_dict[ readme_file_name ] = suc.translate_string( text, to_html=False )
                except Exception, e:
                    log.debug( "Error reading README file '%s' defined in metadata: %s" % ( str( relative_path_to_readme_file ), str( e ) ) )
    return readme_files_dict

def get_readme_files_dict_for_display( trans, tool_shed_url, repo_info_dict ):
    """
    Return a dictionary of README files contained in the single repository being installed so they can be displayed on the tool panel section 
    selection page.
    """
    name = repo_info_dict.keys()[ 0 ]
    repo_info_tuple = repo_info_dict[ name ]
    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, installed_td = \
        suc.get_repo_info_tuple_contents( repo_info_tuple )
    # Handle README files.
    url = suc.url_join( tool_shed_url,
                       'repository/get_readme_files?name=%s&owner=%s&changeset_revision=%s' % ( name, repository_owner, changeset_revision ) )
    raw_text = common_util.tool_shed_get( trans.app, tool_shed_url, url )
    readme_files_dict = json.from_json_string( raw_text )
    return readme_files_dict
