import logging
import os
import shutil
import tempfile
from galaxy import util
from galaxy.datatypes import checkers
from galaxy.util import json
import tool_shed.util.shed_util_common as suc
from tool_shed.util import tool_util

from galaxy import eggs
eggs.require( 'mercurial' )
from mercurial import commands
from mercurial import hg
from mercurial import ui

log = logging.getLogger( __name__ )

UNDESIRABLE_DIRS = [ '.hg', '.svn', '.git', '.cvs' ]
UNDESIRABLE_FILES = [ '.hg_archival.txt', 'hgrc', '.DS_Store' ]
CHUNK_SIZE = 2**20 # 1Mb

def check_archive( archive ):
    for member in archive.getmembers():
        # Allow regular files and directories only
        if not ( member.isdir() or member.isfile() or member.islnk() ):
            message = "Uploaded archives can only include regular directories and files (no symbolic links, devices, etc). Offender: %s" % str( member )
            return False, message
        for item in [ '.hg', '..', '/' ]:
            if member.name.startswith( item ):
                message = "Uploaded archives cannot contain .hg directories, absolute filenames starting with '/', or filenames with two dots '..'."
                return False, message
        if member.name in [ 'hgrc' ]:
            message = "Uploaded archives cannot contain hgrc files."
            return False, message
    return True, ''

def check_file_contents_for_email_alerts( trans ):
    """
    See if any admin users have chosen to receive email alerts when a repository is updated.  If so, the file contents of the update must be
    checked for inappropriate content.
    """
    admin_users = trans.app.config.get( "admin_users", "" ).split( "," )
    for repository in trans.sa_session.query( trans.model.Repository ) \
                                      .filter( trans.model.Repository.table.c.email_alerts != None ):
        email_alerts = json.from_json_string( repository.email_alerts )
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

def create_and_write_tmp_file( text ):
    fh = tempfile.NamedTemporaryFile( 'wb' )
    tmp_filename = fh.name
    fh.close()
    fh = open( tmp_filename, 'wb' )
    fh.write( '<?xml version="1.0"?>\n' )
    fh.write( text )
    fh.close()
    return tmp_filename

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
    fd, uncompressed = tempfile.mkstemp( prefix='repo_%d_upload_bunzip2_' % repository.id, dir=os.path.dirname( uploaded_file_name ), text=False )
    bzipped_file = bz2.BZ2File( uploaded_file_name, 'rb' )
    while 1:
        try:
            chunk = bzipped_file.read( CHUNK_SIZE )
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

def handle_directory_changes( trans, repository, full_path, filenames_in_archive, remove_repo_files_not_in_tar, new_repo_alert, commit_message,
                              undesirable_dirs_removed, undesirable_files_removed ):    
    repo_dir = repository.repo_path( trans.app )
    repo = hg.repository( suc.get_configured_ui(), repo_dir )
    content_alert_str = ''
    files_to_remove = []
    filenames_in_archive = [ os.path.join( full_path, name ) for name in filenames_in_archive ]
    if remove_repo_files_not_in_tar and not repository.is_new( trans.app ):
        # We have a repository that is not new (it contains files), so discover those files that are in the repository, but not in the uploaded archive.
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
            # Remove files in the repository (relative to the upload point) that are not in the uploaded archive.
            try:
                commands.remove( repo.ui, repo, repo_file, force=True )
            except Exception, e:
                log.debug( "Error removing files using the mercurial API, so trying a different approach, the error was: %s" % str( e ))
                relative_selected_file = selected_file.split( 'repo_%d' % repository.id )[1].lstrip( '/' )
                repo.dirstate.remove( relative_selected_file )
                repo.dirstate.write()
                absolute_selected_file = os.path.abspath( selected_file )
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
    # See if any admin users have chosen to receive email alerts when a repository is
    # updated.  If so, check every uploaded file to ensure content is appropriate.
    check_contents = check_file_contents_for_email_alerts( trans )
    for filename_in_archive in filenames_in_archive:
        # Check file content to ensure it is appropriate.
        if check_contents and os.path.isfile( filename_in_archive ):
            content_alert_str += check_file_content_for_html_and_images( filename_in_archive )
        commands.add( repo.ui, repo, filename_in_archive )
        if filename_in_archive.endswith( 'tool_data_table_conf.xml.sample' ):
            # Handle the special case where a tool_data_table_conf.xml.sample file is being uploaded by parsing the file and adding new entries
            # to the in-memory trans.app.tool_data_tables dictionary.
            error, message = tool_util.handle_sample_tool_data_table_conf_file( trans.app, filename_in_archive )
            if error:
                return False, message, files_to_remove, content_alert_str, undesirable_dirs_removed, undesirable_files_removed
    commands.commit( repo.ui, repo, full_path, user=trans.user.username, message=commit_message )
    admin_only = len( repository.downloadable_revisions ) != 1
    suc.handle_email_alerts( trans, repository, content_alert_str=content_alert_str, new_repo_alert=new_repo_alert, admin_only=admin_only )
    return True, '', files_to_remove, content_alert_str, undesirable_dirs_removed, undesirable_files_removed

def handle_gzip( repository, uploaded_file_name ):
    fd, uncompressed = tempfile.mkstemp( prefix='repo_%d_upload_gunzip_' % repository.id, dir=os.path.dirname( uploaded_file_name ), text=False )
    gzipped_file = gzip.GzipFile( uploaded_file_name, 'rb' )
    while 1:
        try:
            chunk = gzipped_file.read( CHUNK_SIZE )
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

def handle_repository_dependencies_definition( trans, repository_dependencies_config ):
    altered = False
    try:
        # Make sure we're looking at a valid repository_dependencies.xml file.
        tree = util.parse_xml( repository_dependencies_config )
        root = tree.getroot()
    except Exception, e:
        error_message = "Error parsing %s in handle_repository_dependencies_definition: " % str( repository_dependencies_config )
        log.exception( error_message )
        return False, None
    if root.tag == 'repositories':
        for index, elem in enumerate( root ):
            # <repository name="molecule_datatypes" owner="test" changeset_revision="1a070566e9c6" />
            populated, elem = handle_repository_dependency_elem( trans, elem )
            if populated:
                root[ index ] = elem
                if not altered:
                    altered = True
        return altered, root
    return False, None

def handle_repository_dependency_elem( trans, elem ):
    # <repository name="molecule_datatypes" owner="test" changeset_revision="1a070566e9c6" />
    populated = False
    name = elem.get( 'name' )
    owner = elem.get( 'owner' )
    changeset_revision = elem.get( 'changeset_revision' )
    if not changeset_revision:
        # Populate the changeset_revision attribute with the latest installable metadata revision for the defined repository.
        # We use the latest installable revision instead of the latest metadata revision to ensure that the contents of the
        # revision are valid.
        repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
        if repository:
            repo_dir = repository.repo_path( trans.app )
            repo = hg.repository( suc.get_configured_ui(), repo_dir )
            lastest_installable_changeset_revision = suc.get_latest_downloadable_changeset_revision( trans, repository, repo )
            if lastest_installable_changeset_revision != suc.INITIAL_CHANGELOG_HASH:
                elem.attrib[ 'changeset_revision' ] = lastest_installable_changeset_revision
                populated = True
    return populated, elem

def handle_tool_dependencies_definition( trans, tool_dependencies_config ):
    altered = False
    try:
        # Make sure we're looking at a valid tool_dependencies.xml file.
        tree = util.parse_xml( tool_dependencies_config )
        root = tree.getroot()
    except Exception, e:
        error_message = "Error parsing %s in handle_tool_dependencies_definition: " % str( tool_dependencies_config )
        log.exception( error_message )
        return False, None
    if root.tag == 'tool_dependency':
        for root_index, root_elem in enumerate( root ):
            # <package name="eigen" version="2.0.17">
            if root_elem.tag == 'package':
                package_altered = False
                for package_index, package_elem in enumerate( root_elem ):
                    if package_elem.tag == 'repository':
                        # <repository name="package_eigen_2_0" owner="test" changeset_revision="09eb05087cd0" prior_installation_required="True" />
                        populated, repository_elem = handle_repository_dependency_elem( trans, package_elem )
                        if populated:
                            root_elem[ package_index ] = repository_elem
                            package_altered = True
                            if not altered:
                                altered = True

                    elif package_elem.tag == 'install':
                        # <install version="1.0">
                        for actions_index, actions_elem in enumerate( package_elem ):
                            for action_index, action_elem in enumerate( actions_elem ):
                                action_type = action_elem.get( 'type' )
                                if action_type == 'set_environment_for_install':
                                    # <action type="set_environment_for_install">
                                    #     <repository name="package_eigen_2_0" owner="test" changeset_revision="09eb05087cd0">
                                    #        <package name="eigen" version="2.0.17" />
                                    #     </repository>
                                    # </action>
                                    for repo_index, repo_elem in enumerate( action_elem ):
                                        populated, repository_elem = handle_repository_dependency_elem( trans, repo_elem )
                                        if populated:
                                            action_elem[ repo_index ] = repository_elem
                                            package_altered = True
                                            if not altered:
                                                altered = True
                                    if package_altered:
                                        actions_elem[ action_index ] = action_elem
                            if package_altered:
                                root_elem[ actions_index ] = actions_elem

                if package_altered:
                    root[ root_index ] = root_elem
        return altered, root
    return False, None

def uncompress( repository, uploaded_file_name, uploaded_file_filename, isgzip, isbz2 ):
    if isgzip:
        handle_gzip( repository, uploaded_file_name )
        return uploaded_file_filename.rstrip( '.gz' )
    if isbz2:
        handle_bz2( repository, uploaded_file_name )
        return uploaded_file_filename.rstrip( '.bz2' )
