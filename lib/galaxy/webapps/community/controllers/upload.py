import sys, os, shutil, logging, tarfile, tempfile
from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy.datatypes.checkers import *
from common import get_categories, get_repository, hg_add, hg_clone, hg_commit, hg_push, update_for_browsing
from mercurial import hg, ui

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
        uploaded_file = None
        upload_point = params.get( 'upload_point', None )
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
                # TODO: throw an exception????
                upload_point = None
        else:
            # Default to repository root
            upload_point = None
        if params.get( 'upload_button', False ):
            ctx = repo.changectx( "tip" )
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
                # Our current support for browsing repo contents requires a copy of the
                # repository files in the repo root directory.  To eliminate these copies,
                # we update the repo, passing the "-r null" flag.
                os.chdir( repo_dir )
                os.system( 'hg update -r null > /dev/null 2>&1' )
                os.chdir( current_working_dir )
                isgzip = False
                isbz2 = False
                if uncompress_file:
                    isgzip = is_gzip( uploaded_file_name )
                    if not isgzip:
                        isbz2 = is_bz2( uploaded_file_name )
                ok = True
                files_to_commit = []
                # Determine what we have - a single file or an archive
                try:
                    if uncompress_file:
                        # Open for reading with transparent compression.
                        tar = tarfile.open( uploaded_file_name, 'r:*' )
                    else:
                        tar = tarfile.open( uploaded_file_name )
                    istar = True
                except tarfile.ReadError, e:
                    tar = None
                    istar = False
                if repository.is_new:
                    if istar:
                        # We have an archive ( a tarball ) in a new repository.
                        ok, message = self.__check_archive( tar )
                        if ok:
                            tar.extractall( path=repo_dir )
                            tar.close()
                            uploaded_file.close()
                            for root, dirs, files in os.walk( repo_dir, topdown=False ):
                                # Don't visit .hg directories and don't include hgrc files in commit.
                                if not root.find( '.hg' ) >= 0 and not root.find( 'hgrc' ) >= 0:
                                    if '.hg' in dirs:
                                        # Don't visit .hg directories
                                        dirs.remove( '.hg' )
                                    if 'hgrc' in files:
                                         # Don't include hgrc files in commit - should be impossible
                                         # since we don't visit .hg dirs, but just in case...
                                        files.remove( 'hgrc' )
                                    for name in files:
                                        relative_root = root.split( 'repo_%d' % repository.id )[ 1 ].lstrip ( '/' )
                                        if upload_point is not None:
                                            file_path = os.path.join( relative_root, upload_point, name )
                                        else:
                                            file_path = os.path.join( relative_root, name )
                                        # Check if the file is tracked and make it tracked if not.
                                        repo_contains = file_path in [ i for i in ctx.manifest() ]
                                        if not repo_contains:
                                            # Add the file to the dirstate
                                            repo.dirstate.add( file_path )
                                            files_to_commit.append( file_path )
                        else:
                            tar.close()
                    else:
                        # We have a single file in a new repository.
                        if uncompress_file and ( isgzip or isbz2 ):
                            uploaded_file_filename = self.uncompress( repository, uploaded_file_name, uploaded_file_filename, isgzip, isbz2 )
                        if upload_point is not None:
                            full_path = os.path.abspath( os.path.join( upload_point, uploaded_file_filename ) )
                            file_path = os.path.join( upload_point, uploaded_file_filename )
                        else:
                            full_path = os.path.abspath( os.path.join( repo_dir, uploaded_file_filename ) )
                            file_path = os.path.join( uploaded_file_filename )
                        shutil.move( uploaded_file_name, full_path )
                        repo.dirstate.add( file_path )
                        files_to_commit.append( file_path )
                else:
                    # We have a repository that is not new (it contains files).
                    if uncompress_file and ( isgzip or isbz2 ):
                        uploaded_file_filename = self.uncompress( repository, uploaded_file_name, uploaded_file_filename, isgzip, isbz2 )
                    # Get the current repository tip.
                    tip = repo[ 'tip' ]
                    # Clone the repository to a temporary location.
                    tmp_dir, cloned_repo_dir = hg_clone( trans, repository, current_working_dir )
                    # Move the uploaded files to the upload_point within the cloned repository.
                    self.__move_to_upload_point( upload_point, uploaded_file, uploaded_file_name, uploaded_file_filename, cloned_repo_dir, istar, tar )
                    # Add the files to the cloned repository.
                    hg_add( trans, current_working_dir, cloned_repo_dir )
                    # Commit the files to the cloned repository.
                    if not commit_message:
                        commit_message = 'Uploaded'
                    hg_commit( commit_message, current_working_dir, cloned_repo_dir )
                    # Push the changes from the cloned repository to the master repository.
                    hg_push( trans, repository, current_working_dir, cloned_repo_dir )
                    # Remove the temporary directory containing the cloned repository.
                    shutil.rmtree( tmp_dir )
                    # Update the repository files for browsing.
                    update_for_browsing( repository, current_working_dir )
                    # Get the new repository tip.
                    repo = hg.repository( ui.ui(), repo_dir )
                    if tip != repo[ 'tip' ]:
                        if uncompress_file:
                            uncompress_str = ' uncompressed and '
                        else:
                            uncompress_str = ' '
                        message = "The file '%s' has been successfully%suploaded to the repository." % ( uploaded_file_filename, uncompress_str )
                    else:
                        message = 'No changes to repository.'
                    trans.response.send_redirect( web.url_for( controller='repository',
                                                               action='browse_repository',
                                                               commit_message='Deleted selected files',
                                                               message=message,
                                                               id=trans.security.encode_id( repository.id ) ) )
                if ok:
                    if files_to_commit:
                        repo.dirstate.write()
                        repo.commit( text=commit_message )
                        os.chdir( repo_dir )
                        os.system( 'hg update > /dev/null 2>&1' )
                        os.chdir( current_working_dir )
                        if uncompress_file:
                            uncompress_str = ' uncompressed and '
                        else:
                            uncompress_str = ' '
                        message = "The file '%s' has been successfully%suploaded to the repository." % ( uploaded_file_filename, uncompress_str )
                        trans.response.send_redirect( web.url_for( controller='repository',
                                                                   action='browse_repository',
                                                                   commit_message='Deleted selected files',
                                                                   message=message,
                                                                   id=trans.security.encode_id( repository.id ) ) )
                else:
                    status = 'error'
                os.chdir( repo_dir )
                os.system( 'hg update > /dev/null 2>&1' )
                os.chdir( current_working_dir )
        selected_categories = [ trans.security.decode_id( id ) for id in category_ids ]
        return trans.fill_template( '/webapps/community/repository/upload.mako',
                                    repository=repository,
                                    commit_message=commit_message,
                                    uncompress_file=uncompress_file,
                                    message=message,
                                    status=status )
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
    def __move_to_upload_point( self, upload_point, uploaded_file, uploaded_file_name, uploaded_file_filename, cloned_repo_dir, istar, tar ):
        if upload_point is not None:
            if istar:
                full_path = os.path.abspath( os.path.join( cloned_repo_dir, upload_point ) )
            else:
                full_path = os.path.abspath( os.path.join( cloned_repo_dir, upload_point, uploaded_file_filename ) )
        else:
            if istar:
                full_path = os.path.abspath( os.path.join( cloned_repo_dir ) )
            else:
                full_path = os.path.abspath( os.path.join( cloned_repo_dir, uploaded_file_filename ) )
        if istar:
            # Extract the uploaded tarball to the load_point within the cloned repository hierarchy
            tar.extractall( path=full_path )
            tar.close()
            uploaded_file.close()
        else:
            # Move the uploaded file to the load_point within the cloned repository hierarchy
            shutil.move( uploaded_file_name, full_path )
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
                            