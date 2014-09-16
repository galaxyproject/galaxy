import logging
import os
import threading

from mako.template import Template

from galaxy import web
from galaxy.util import json
from galaxy.util import rst_to_html
from galaxy.util import unicodify

import tool_shed.util.shed_util_common as suc
from tool_shed.util import basic_util
from tool_shed.util import common_util
from tool_shed.util import hg_util

log = logging.getLogger( __name__ )

def build_readme_files_dict( app, repository, changeset_revision, metadata, tool_path=None ):
    """
    Return a dictionary of valid readme file name <-> readme file content pairs for all readme files defined in the received metadata.  Since the
    received changeset_revision (which is associated with the received metadata) may not be the latest installable changeset revision, the README
    file contents may not be available on disk.  This method is used by both Galaxy and the Tool Shed.
    """
    if app.name == 'galaxy':
        can_use_disk_files = True
    else:
        repo = hg_util.get_repo_for_repository( app, repository=repository, repo_path=None, create=False )
        latest_downloadable_changeset_revision = suc.get_latest_downloadable_changeset_revision( app, repository, repo )
        can_use_disk_files = changeset_revision == latest_downloadable_changeset_revision
    readme_files_dict = {}
    if metadata:
        if 'readme_files' in metadata:
            for relative_path_to_readme_file in metadata[ 'readme_files' ]:
                readme_file_name = os.path.split( relative_path_to_readme_file )[ 1 ]
                if can_use_disk_files:
                    if tool_path:
                        full_path_to_readme_file = os.path.abspath( os.path.join( tool_path, relative_path_to_readme_file ) )
                    else:
                        full_path_to_readme_file = os.path.abspath( relative_path_to_readme_file )
                    text = None
                    try:
                        f = open( full_path_to_readme_file, 'r' )
                        text = unicodify( f.read() )
                        f.close()
                    except Exception, e:
                        log.exception( "Error reading README file '%s' from disk: %s" % ( str( relative_path_to_readme_file ), str( e ) ) )
                        text = None
                    if text:
                        text_of_reasonable_length = basic_util.size_string( text )
                        if text_of_reasonable_length.find( '.. image:: ' ) >= 0:
                            # Handle image display for README files that are contained in repositories in the tool shed or installed into Galaxy.
                            lock = threading.Lock()
                            lock.acquire( True )
                            try:
                                text_of_reasonable_length = suc.set_image_paths( app,
                                                                                 app.security.encode_id( repository.id ),
                                                                                 text_of_reasonable_length )
                            except Exception, e:
                                log.exception( "Exception in build_readme_files_dict, so images may not be properly displayed:\n%s" % str( e ) )
                            finally:
                                lock.release()
                        if readme_file_name.endswith( '.rst' ):
                            text_of_reasonable_length = Template( rst_to_html( text_of_reasonable_length ),
                                                                  input_encoding='utf-8',
                                                                  output_encoding='utf-8',
                                                                  default_filters=[ 'decode.utf8' ],
                                                                  encoding_errors='replace' )
                            text_of_reasonable_length = text_of_reasonable_length.render( static_path=web.url_for( '/static' ),
                                                                                          host_url=web.url_for( '/', qualified=True ) )
                            text_of_reasonable_length = unicodify( text_of_reasonable_length )
                        else:
                            text_of_reasonable_length = basic_util.to_html_string( text_of_reasonable_length )
                        readme_files_dict[ readme_file_name ] = text_of_reasonable_length
                else:
                    # We must be in the tool shed and have an old changeset_revision, so we need to retrieve the file contents from the repository manifest.
                    ctx = hg_util.get_changectx_for_changeset( repo, changeset_revision )
                    if ctx:
                        fctx = hg_util.get_file_context_from_ctx( ctx, readme_file_name )
                        if fctx and fctx not in [ 'DELETED' ]:
                            try:
                                text = unicodify( fctx.data() )
                                readme_files_dict[ readme_file_name ] = basic_util.size_string( text )
                            except Exception, e:
                                log.exception( "Error reading README file '%s' from repository manifest: %s" % \
                                               ( str( relative_path_to_readme_file ), str( e ) ) )
    return readme_files_dict

def get_readme_files_dict_for_display( app, tool_shed_url, repo_info_dict ):
    """
    Return a dictionary of README files contained in the single repository being installed so they can be displayed on the tool panel section
    selection page.
    """
    name = repo_info_dict.keys()[ 0 ]
    repo_info_tuple = repo_info_dict[ name ]
    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, installed_td = \
        suc.get_repo_info_tuple_contents( repo_info_tuple )
    # Handle changing HTTP protocols over time.
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( app, tool_shed_url )
    params = '?name=%s&owner=%s&changeset_revision=%s' % ( name, repository_owner, changeset_revision )
    url = common_util.url_join( tool_shed_url,
                                'repository/get_readme_files%s' % params )
    raw_text = common_util.tool_shed_get( app, tool_shed_url, url )
    readme_files_dict = json.loads( raw_text )
    return readme_files_dict

def get_readme_file_names( repository_name ):
    """Return a list of file names that will be categorized as README files for the received repository_name."""
    readme_files = [ 'readme', 'read_me', 'install' ]
    valid_filenames = map( lambda f: '%s.txt' % f, readme_files )
    valid_filenames.extend( map( lambda f: '%s.rst' % f, readme_files ) )
    valid_filenames.extend( readme_files )
    valid_filenames.append( '%s.txt' % repository_name )
    valid_filenames.append( '%s.rst' % repository_name )
    return valid_filenames
