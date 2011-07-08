import sys, os, shutil, logging, tarfile, tempfile
from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy.datatypes.checkers import *
from common import *
from mercurial import hg, ui, commands

log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"
CHUNK_SIZE = 2**20 # 1Mb

class UploadError( Exception ):
    pass

class UploadController( BaseController ):
    @web.expose
    @web.require_login( 'upload', use_panels=True, webapp='community' )
    def upload( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        commit_message = util.restore_text( params.get( 'commit_message', 'Uploaded'  ) )
        category_ids = util.listify( params.get( 'category_id', '' ) )
        categories = get_categories( trans )
        repository_id = params.get( 'repository_id', '' )
        repository = get_repository( trans, repository_id )
        repo_dir = repository.repo_path
        repo = hg.repository( ui.ui(), repo_dir )
        uncompress_file = util.string_as_bool( params.get( 'uncompress_file', 'true' ) )
        remove_repo_files_not_in_tar = util.string_as_bool( params.get( 'remove_repo_files_not_in_tar', 'true' ) )
        uploaded_file = None
        upload_point = self.__get_upload_point( repository, **kwd )
        # Get the current repository tip.
        tip = repository.tip
        if params.get( 'upload_button', False ):
            current_working_dir = os.getcwd()
            file_data = params.get( 'file_data', '' )
            if file_data == '':
                message = 'No files were entered on the upload form.'
                status = 'error'
                uploaded_file = None
            elif file_data not in ( '', None ):
                uploaded_file = file_data.file
                uploaded_file_name = uploaded_file.name
                uploaded_file_filename = file_data.filename
            if uploaded_file:
                isgzip = False
                isbz2 = False
                if uncompress_file:
                    isgzip = is_gzip( uploaded_file_name )
                    if not isgzip:
                        isbz2 = is_bz2( uploaded_file_name )
                ok = True
                # Determine what we have - a single file or an archive
                try:
                    if ( isgzip or isbz2 ) and uncompress_file:
                        # Open for reading with transparent compression.
                        tar = tarfile.open( uploaded_file_name, 'r:*' )
                    else:
                        tar = tarfile.open( uploaded_file_name )
                    istar = True
                except tarfile.ReadError, e:
                    tar = None
                    istar = False
                if istar:
                    ok, message, files_to_remove = self.upload_tar( trans,
                                                                    repository,
                                                                    tar,
                                                                    uploaded_file,
                                                                    upload_point,
                                                                    remove_repo_files_not_in_tar,
                                                                    commit_message )
                else:
                    if ( isgzip or isbz2 ) and uncompress_file:
                        uploaded_file_filename = self.uncompress( repository, uploaded_file_name, uploaded_file_filename, isgzip, isbz2 )
                    if upload_point is not None:
                        full_path = os.path.abspath( os.path.join( repo_dir, upload_point, uploaded_file_filename ) )
                    else:
                        full_path = os.path.abspath( os.path.join( repo_dir, uploaded_file_filename ) )
                    # Move the uploaded file to the load_point within the repository hierarchy.
                    shutil.move( uploaded_file_name, full_path )
                    commands.add( repo.ui, repo, full_path )
                    commands.commit( repo.ui, repo, full_path, user=trans.user.username, message=commit_message )
                    handle_email_alerts( trans, repository )
                if ok:
                    # Update the repository files for browsing, a by-product of doing this
                    # is eliminating unwanted files from the repository directory.
                    update_for_browsing( repository, current_working_dir )
                    # Get the new repository tip.
                    if tip != repository.tip:
                        if ( isgzip or isbz2 ) and uncompress_file:
                            uncompress_str = ' uncompressed and '
                        else:
                            uncompress_str = ' '
                        message = "The file '%s' has been successfully%suploaded to the repository." % ( uploaded_file_filename, uncompress_str )
                        if istar and remove_repo_files_not_in_tar and files_to_remove:
                            if upload_point is not None:
                                message += "  %d files were removed from the repository relative to the selected upload point '%s'." % ( len( files_to_remove ), upload_point )
                            else:
                                message += "  %d files were removed from the repository root." % len( files_to_remove )
                    else:
                        message = 'No changes to repository.'      
                    # Set metadata on the repository tip
                    error_message, status = set_repository_metadata( trans, repository_id, repository.tip, **kwd )
                    if error_message:
                        message = '%s<br/>%s' % ( message, error_message )
                        return trans.response.send_redirect( web.url_for( controller='repository',
                                                                          action='manage_repository',
                                                                          id=repository_id,
                                                                          message=message,
                                                                          status=status ) )
                    trans.response.send_redirect( web.url_for( controller='repository',
                                                               action='browse_repository',
                                                               id=repository_id,
                                                               commit_message='Deleted selected files',
                                                               message=message,
                                                               status=status ) )
                else:
                    status = 'error'
        selected_categories = [ trans.security.decode_id( id ) for id in category_ids ]
        return trans.fill_template( '/webapps/community/repository/upload.mako',
                                    repository=repository,
                                    commit_message=commit_message,
                                    uncompress_file=uncompress_file,
                                    remove_repo_files_not_in_tar=remove_repo_files_not_in_tar,
                                    message=message,
                                    status=status )
    def upload_tar( self, trans, repository, tar, uploaded_file, upload_point, remove_repo_files_not_in_tar, commit_message ):
        # Upload a tar archive of files.
        repo_dir = repository.repo_path
        repo = hg.repository( ui.ui(), repo_dir )
        files_to_remove = []
        ok, message = self.__check_archive( tar )
        if not ok:
            tar.close()
            uploaded_file.close()
            return ok, message, files_to_remove
        else:
            if upload_point is not None:
                full_path = os.path.abspath( os.path.join( repo_dir, upload_point ) )
            else:
                full_path = os.path.abspath( repo_dir )
            filenames_in_archive = [ tarinfo_obj.name for tarinfo_obj in tar.getmembers() ]
            filenames_in_archive = [ os.path.join( full_path, name ) for name in filenames_in_archive ]
            # Extract the uploaded tar to the load_point within the repository hierarchy.
            tar.extractall( path=full_path )
            tar.close()
            uploaded_file.close()
            if remove_repo_files_not_in_tar and not repository.is_new:
                # We have a repository that is not new (it contains files), so discover
                # those files that are in the repository, but not in the uploaded archive.
                for root, dirs, files in os.walk( full_path ):
                    if not root.find( '.hg' ) >= 0 and not root.find( 'hgrc' ) >= 0:
                        if '.hg' in dirs:
                            # Don't visit .hg directories - should be impossible since we don't
                            # allow uploaded archives that contain .hg dirs, but just in case...
                            dirs.remove( '.hg' )
                        if 'hgrc' in files:
                             # Don't include hgrc files in commit.
                            files.remove( 'hgrc' )
                        for name in files:
                            full_name = os.path.join( root, name )
                            if full_name not in filenames_in_archive:
                                files_to_remove.append( full_name )
                for repo_file in files_to_remove:
                    # Remove files in the repository (relative to the upload point)
                    # that are not in the uploaded archive.
                    commands.remove( repo.ui, repo, repo_file )
            for filename_in_archive in filenames_in_archive:
                commands.add( repo.ui, repo, filename_in_archive )
            # Commit the changes.
            commands.commit( repo.ui, repo, full_path, user=trans.user.username, message=commit_message )
            handle_email_alerts( trans, repository )
            return True, '', files_to_remove
    def uncompress( self, repository, uploaded_file_name, uploaded_file_filename, isgzip, isbz2 ):
        if isgzip:
            self.__handle_gzip( repository, uploaded_file_name )
            return uploaded_file_filename.rstrip( '.gz' )
        if isbz2:
            self.__handle_bz2( repository, uploaded_file_name )
            return uploaded_file_filename.rstrip( '.bz2' )
    def __handle_gzip( self, repository, uploaded_file_name ):
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
    def __handle_bz2( self, repository, uploaded_file_name ):
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
    def __get_upload_point( self, repository, **kwd ):
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
    def __check_archive( self, archive ):
        for member in archive.getmembers():
            # Allow regular files and directories only
            if not ( member.isdir() or member.isfile() ):
                message = "Uploaded archives can only include regular directories and files (no symbolic links, devices, etc)."
                return False, message
            for item in [ '.hg', '..', '/' ]:
                if member.name.startswith( item ):
                    message = "Uploaded archives cannot contain .hg directories, absolute filenames starting with '/', or filenames with two dots '..'."
                    return False, message
            if member.name in [ 'hgrc' ]:
                message = "Uploaded archives cannot contain hgrc files."
                return False, message
        return True, ''
                            