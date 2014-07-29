import gzip
import json
import logging
import os
import shutil
import tempfile

from galaxy.datatypes import checkers

from tool_shed.tools import data_table_manager

from tool_shed.util import basic_util
from tool_shed.util import hg_util
from tool_shed.util import shed_util_common as suc

import tool_shed.repository_types.util as rt_util

log = logging.getLogger( __name__ )

UNDESIRABLE_DIRS = [ '.hg', '.svn', '.git', '.cvs' ]
UNDESIRABLE_FILES = [ '.hg_archival.txt', 'hgrc', '.DS_Store' ]

def check_archive( repository, archive ):
    for member in archive.getmembers():
        # Allow regular files and directories only
        if not ( member.isdir() or member.isfile() or member.islnk() ):
            message = "Uploaded archives can only include regular directories and files (no symbolic links, devices, etc).  "
            message += "The problematic member in this archive is %s," % str( member.name )
            return False, message
        for item in [ '.hg', '..', '/' ]:
            if member.name.startswith( item ):
                message = "Uploaded archives cannot contain .hg directories, absolute filenames starting with '/', or filenames with two dots '..'.  "
                message += "The problematic member in this archive is %s." % str( member.name )
                return False, message
        if member.name in [ 'hgrc' ]:
            message = "Uploaded archives cannot contain hgrc files.  "
            message += "The problematic member in this archive is %s." % str( member.name )
            return False, message
        if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION and member.name != rt_util.REPOSITORY_DEPENDENCY_DEFINITION_FILENAME:
            message = 'Repositories of type <b>Repository suite definition</b> can contain only a single file named <b>repository_dependencies.xml</b>.'
            message += 'This archive contains a member named %s.' % str( member.name )
            return False, message
        if repository.type == rt_util.TOOL_DEPENDENCY_DEFINITION and member.name != rt_util.TOOL_DEPENDENCY_DEFINITION_FILENAME:
            message = 'Repositories of type <b>Tool dependency definition</b> can contain only a single file named <b>tool_dependencies.xml</b>.'
            message += 'This archive contains a member named %s.' % str( member.name )
            return False, message
    return True, ''

def check_file_contents_for_email_alerts( app ):
    """
    See if any admin users have chosen to receive email alerts when a repository is updated.
    If so, the file contents of the update must be checked for inappropriate content.
    """
    sa_session = app.model.context.current
    admin_users = app.config.get( "admin_users", "" ).split( "," )
    for repository in sa_session.query( app.model.Repository ) \
                                .filter( app.model.Repository.table.c.email_alerts != None ):
        email_alerts = json.loads( repository.email_alerts )
        for user_email in email_alerts:
            if user_email in admin_users:
                return True
    return False

def check_file_content_for_html_and_images( file_path ):
    message = ''
    if checkers.check_html( file_path ):
        message = 'The file "%s" contains HTML content.\n' % str( file_path )
    elif checkers.check_image( file_path ):
        message = 'The file "%s" contains image content.\n' % str( file_path )
    return message

def get_change_lines_in_file_for_tag( tag, change_dict ):
    """
    The received change_dict is the jsonified version of the changes to a file in a
    changeset being pushed to the Tool Shed from the command line. This method cleans
    and returns appropriate lines for inspection.
    """
    cleaned_lines = []
    data_list = change_dict.get( 'data', [] )
    for data_dict in data_list:
        block = data_dict.get( 'block', '' )
        lines = block.split( '\\n' )
        for line in lines:
            index = line.find( tag )
            if index > -1:
                line = line[ index: ]
                cleaned_lines.append( line )
    return cleaned_lines

def get_upload_point( repository, **kwd ):
    upload_point = kwd.get( 'upload_point', None )
    if upload_point is not None:
        # The value of upload_point will be something like: database/community_files/000/repo_12/1.bed
        if os.path.exists( upload_point ):
            if os.path.isfile( upload_point ):
                # Get the parent directory
                upload_point, not_needed = os.path.split( upload_point )
                # Now the value of uplaod_point will be something like: database/community_files/000/repo_12/
            upload_point = upload_point.split( 'repo_%d' % repository.id )[ 1 ]
            if upload_point:
                upload_point = upload_point.lstrip( '/' )
                upload_point = upload_point.rstrip( '/' )
            # Now the value of uplaod_point will be something like: /
            if upload_point == '/':
                upload_point = None
        else:
            # Must have been an error selecting something that didn't exist, so default to repository root
            upload_point = None
    return upload_point

def handle_bz2( repository, uploaded_file_name ):
    fd, uncompressed = tempfile.mkstemp( prefix='repo_%d_upload_bunzip2_' % repository.id,
                                         dir=os.path.dirname( uploaded_file_name ),
                                         text=False )
    bzipped_file = bz2.BZ2File( uploaded_file_name, 'rb' )
    while 1:
        try:
            chunk = bzipped_file.read( basic_util.CHUNK_SIZE )
        except IOError:
            os.close( fd )
            os.remove( uncompressed )
            log.exception( 'Problem uncompressing bz2 data "%s": %s' % ( uploaded_file_name, str( e ) ) )
            return
        if not chunk:
            break
        os.write( fd, chunk )
    os.close( fd )
    bzipped_file.close()
    shutil.move( uncompressed, uploaded_file_name )

def handle_directory_changes( app, host, username, repository, full_path, filenames_in_archive, remove_repo_files_not_in_tar,
                              new_repo_alert, commit_message, undesirable_dirs_removed, undesirable_files_removed ):
    repo = hg_util.get_repo_for_repository( app, repository=repository, repo_path=None, create=False )
    content_alert_str = ''
    files_to_remove = []
    filenames_in_archive = [ os.path.join( full_path, name ) for name in filenames_in_archive ]
    if remove_repo_files_not_in_tar and not repository.is_new( app ):
        # We have a repository that is not new (it contains files), so discover those files that are in the
        # repository, but not in the uploaded archive.
        for root, dirs, files in os.walk( full_path ):
            if root.find( '.hg' ) < 0 and root.find( 'hgrc' ) < 0:
                for undesirable_dir in UNDESIRABLE_DIRS:
                    if undesirable_dir in dirs:
                        dirs.remove( undesirable_dir )
                        undesirable_dirs_removed += 1
                for undesirable_file in UNDESIRABLE_FILES:
                    if undesirable_file in files:
                        files.remove( undesirable_file )
                        undesirable_files_removed += 1
                for name in files:
                    full_name = os.path.join( root, name )
                    if full_name not in filenames_in_archive:
                        files_to_remove.append( full_name )
        for repo_file in files_to_remove:
            # Remove files in the repository (relative to the upload point) that are not in
            # the uploaded archive.
            try:
                hg_util.remove_file( repo.ui, repo, repo_file, force=True )
            except Exception, e:
                log.debug( "Error removing files using the mercurial API, so trying a different approach, the error was: %s" % str( e ))
                relative_selected_file = repo_file.split( 'repo_%d' % repository.id )[1].lstrip( '/' )
                repo.dirstate.remove( relative_selected_file )
                repo.dirstate.write()
                absolute_selected_file = os.path.abspath( repo_file )
                if os.path.isdir( absolute_selected_file ):
                    try:
                        os.rmdir( absolute_selected_file )
                    except OSError, e:
                        # The directory is not empty.
                        pass
                elif os.path.isfile( absolute_selected_file ):
                    os.remove( absolute_selected_file )
                    dir = os.path.split( absolute_selected_file )[0]
                    try:
                        os.rmdir( dir )
                    except OSError, e:
                        # The directory is not empty.
                        pass
    # See if any admin users have chosen to receive email alerts when a repository is updated.
    # If so, check every uploaded file to ensure content is appropriate.
    check_contents = check_file_contents_for_email_alerts( app )
    for filename_in_archive in filenames_in_archive:
        # Check file content to ensure it is appropriate.
        if check_contents and os.path.isfile( filename_in_archive ):
            content_alert_str += check_file_content_for_html_and_images( filename_in_archive )
        hg_util.add_changeset( repo.ui, repo, filename_in_archive )
        if filename_in_archive.endswith( 'tool_data_table_conf.xml.sample' ):
            # Handle the special case where a tool_data_table_conf.xml.sample file is being uploaded
            # by parsing the file and adding new entries to the in-memory app.tool_data_tables
            # dictionary.
            tdtm = data_table_manager.ToolDataTableManager( app )
            error, message = tdtm.handle_sample_tool_data_table_conf_file( filename_in_archive, persist=False )
            if error:
                return False, message, files_to_remove, content_alert_str, undesirable_dirs_removed, undesirable_files_removed
    hg_util.commit_changeset( repo.ui,
                              repo,
                              full_path_to_changeset=full_path,
                              username=username,
                              message=commit_message )
    admin_only = len( repository.downloadable_revisions ) != 1
    suc.handle_email_alerts( app,
                             host,
                             repository,
                             content_alert_str=content_alert_str,
                             new_repo_alert=new_repo_alert,
                             admin_only=admin_only )
    return True, '', files_to_remove, content_alert_str, undesirable_dirs_removed, undesirable_files_removed

def handle_gzip( repository, uploaded_file_name ):
    fd, uncompressed = tempfile.mkstemp( prefix='repo_%d_upload_gunzip_' % repository.id,
                                         dir=os.path.dirname( uploaded_file_name ),
                                         text=False )
    gzipped_file = gzip.GzipFile( uploaded_file_name, 'rb' )
    while 1:
        try:
            chunk = gzipped_file.read( basic_util.CHUNK_SIZE )
        except IOError, e:
            os.close( fd )
            os.remove( uncompressed )
            log.exception( 'Problem uncompressing gz data "%s": %s' % ( uploaded_file_name, str( e ) ) )
            return
        if not chunk:
            break
        os.write( fd, chunk )
    os.close( fd )
    gzipped_file.close()
    shutil.move( uncompressed, uploaded_file_name )

def uncompress( repository, uploaded_file_name, uploaded_file_filename, isgzip=False, isbz2=False ):
    if isgzip:
        handle_gzip( repository, uploaded_file_name )
        return uploaded_file_filename.rstrip( '.gz' )
    if isbz2:
        handle_bz2( repository, uploaded_file_name )
        return uploaded_file_filename.rstrip( '.bz2' )
