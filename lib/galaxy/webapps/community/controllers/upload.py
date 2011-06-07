import sys, os, shutil, logging, tarfile, tempfile
from galaxy.web.base.controller import *
from galaxy.model.orm import *
from common import get_categories, get_repository
from mercurial import hg, ui

log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

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
            if uploaded_file:
                # Our current support for browsing repo contents requires a copy of the
                # repository files in the repo root directory.  To produce these copies,
                # we update without passing the "-r null" flag.
                os.chdir( repo_dir )
                os.system( 'hg update -r null > /dev/null 2>&1' )
                os.chdir( current_working_dir )
                ok = True
                files_to_commit = []
                # Determine what we have - a single file or an archive
                try:
                    tar = tarfile.open( uploaded_file.name )
                    istar = True
                except tarfile.ReadError, e:
                    tar = None
                    istar = False
                if repository.is_new:
                    if istar:
                        # We have an archive ( a tarball )
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
                        # We have a single file
                        if upload_point is not None:
                            full_path = os.path.abspath( os.path.join( upload_point, file_data.filename ) )
                            file_path = os.path.join( upload_point, file_data.filename )
                        else:
                            full_path = os.path.abspath( os.path.join( repo_dir, file_data.filename ) )
                            file_path = os.path.join( file_data.filename )
                        shutil.move( uploaded_file.name, full_path )
                        repo.dirstate.add( file_path )
                        files_to_commit.append( file_path )
                else:
                    # Clone the repository to a temporary location.
                    tmp_dir, cloned_repo_dir = self.__hg_clone( trans, repository, repo_dir, current_working_dir )
                    # Move the uploaded files to the upload_point within the cloned repository.
                    self.__move_to_upload_point( upload_point, uploaded_file, file_data, cloned_repo_dir, istar, tar )
                    # Commit and push the changes from the cloned repo to the master repo.
                    self.__hg_push( trans, repository, file_data, commit_message, current_working_dir, cloned_repo_dir, repo_dir, tmp_dir )
                if ok:
                    if files_to_commit:
                        repo.dirstate.write()
                        repo.commit( text=commit_message )
                        os.chdir( repo_dir )
                        os.system( 'hg update > /dev/null 2>&1' )
                        os.chdir( current_working_dir )
                        message = "The file '%s' has been successfully uploaded to the repository." % file_data.filename
                        trans.response.send_redirect( web.url_for( controller='repository',
                                                                   action='browse_repository',
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
                                    message=message,
                                    status=status )
    def __hg_clone( self, trans, repository, repo_dir, current_working_dir ):
        tmp_dir = tempfile.mkdtemp()
        tmp_archive_dir = os.path.join( tmp_dir, 'tmp_archive_dir' )
        if not os.path.exists( tmp_archive_dir ):
            os.makedirs( tmp_archive_dir )
        # Make a clone of the repository in a temporary location
        cmd = "hg clone %s > /dev/null 2>&1" % os.path.abspath( repo_dir )
        os.chdir( tmp_archive_dir )
        os.system( cmd )
        os.chdir( current_working_dir )
        cloned_repo_dir = os.path.join( tmp_archive_dir, 'repo_%d' % repository.id )
        return tmp_dir, cloned_repo_dir
    def __hg_push( self, trans, repository, file_data, commit_message, current_working_dir, cloned_repo_dir, repo_dir, tmp_dir ):
        # We want these change sets to be associated with the owner of the repository, so we'll
        # set the HGUSER environment variable accordingly.
        os.environ[ 'HGUSER' ] = trans.user.username
        # Add the file to the cloned repository.  If it's already tracked, this should do nothing.
        os.chdir( cloned_repo_dir )
        os.system( 'hg add > /dev/null 2>&1' )
        os.chdir( current_working_dir )
        os.chdir( cloned_repo_dir )
        # Commit the change set to the cloned repository
        os.system( "hg commit -m '%s' > /dev/null 2>&1" % commit_message )
        os.chdir( current_working_dir )
        # Push the change set to the master repository
        cmd = "hg push %s > /dev/null 2>&1" % os.path.abspath( repo_dir )
        os.chdir( cloned_repo_dir )
        os.system( cmd )
        os.chdir( current_working_dir )
        # Make a copy of the updated repository files for browsing.
        os.chdir( repo_dir )
        os.system( 'hg update > /dev/null 2>&1' )
        os.chdir( current_working_dir )
        shutil.rmtree( tmp_dir )
        message = "The file '%s' has been successfully uploaded to the repository." % file_data.filename
        trans.response.send_redirect( web.url_for( controller='repository',
                                                   action='browse_repository',
                                                   message=message,
                                                   id=trans.security.encode_id( repository.id ) ) )
    def __move_to_upload_point( self, upload_point, uploaded_file, file_data, cloned_repo_dir, istar, tar ):
        if upload_point is not None:
            full_path = os.path.abspath( os.path.join( cloned_repo_dir, upload_point, file_data.filename ) )
        else:
            full_path = os.path.abspath( os.path.join( cloned_repo_dir, file_data.filename ) )
        if istar:
            # Extract the uploaded tarball to the load_point within the cloned repository hierarchy
            tar.extractall( path=full_path )
            tar.close()
            uploaded_file.close()
        else:
            # Move the uploaded file to the load_point within the cloned repository hierarchy
            shutil.move( uploaded_file.name, full_path )
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
                            