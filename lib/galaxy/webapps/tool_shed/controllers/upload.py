import logging
import os
import shutil
import tarfile
import tempfile
import urllib
from galaxy.web.base.controller import BaseUIController
from galaxy import util
from galaxy import web
from galaxy.datatypes import checkers
import tool_shed.util.shed_util_common as suc
from tool_shed.util import commit_util
from tool_shed.util import metadata_util
from tool_shed.util import repository_dependency_util
from tool_shed.util import tool_dependency_util
from tool_shed.util import tool_util

from galaxy import eggs
eggs.require( 'mercurial' )
from mercurial import commands
from mercurial import hg
from mercurial import ui

log = logging.getLogger( __name__ )


class UploadController( BaseUIController ):

    @web.expose
    @web.require_login( 'upload', use_panels=True )
    def upload( self, trans, **kwd ):
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        commit_message = kwd.get( 'commit_message', 'Uploaded'  )
        category_ids = util.listify( kwd.get( 'category_id', '' ) )
        categories = suc.get_categories( trans )
        repository_id = kwd.get( 'repository_id', '' )
        repository = suc.get_repository_in_tool_shed( trans, repository_id )
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        uncompress_file = util.string_as_bool( kwd.get( 'uncompress_file', 'true' ) )
        remove_repo_files_not_in_tar = util.string_as_bool( kwd.get( 'remove_repo_files_not_in_tar', 'true' ) )
        uploaded_file = None
        upload_point = commit_util.get_upload_point( repository, **kwd )
        tip = repository.tip( trans.app )
        file_data = kwd.get( 'file_data', '' )
        url = kwd.get( 'url', '' )
        # Part of the upload process is sending email notification to those that have registered to
        # receive them.  One scenario occurs when the first change set is produced for the repository.
        # See the suc.handle_email_alerts() method for the definition of the scenarios.
        new_repo_alert = repository.is_new( trans.app )
        uploaded_directory = None
        if kwd.get( 'upload_button', False ):
            if file_data == '' and url == '':
                message = 'No files were entered on the upload form.'
                status = 'error'
                uploaded_file = None
            elif url and url.startswith( 'hg' ):
                # Use mercurial clone to fetch repository, contents will then be copied over.
                uploaded_directory = tempfile.mkdtemp()
                repo_url = 'http%s' % url[ len( 'hg' ): ]
                repo_url = repo_url.encode( 'ascii', 'replace' )
                commands.clone( suc.get_configured_ui(), repo_url, uploaded_directory )
            elif url:
                valid_url = True
                try:
                    stream = urllib.urlopen( url )
                except Exception, e:
                    valid_url = False
                    message = 'Error uploading file via http: %s' % str( e )
                    status = 'error'
                    uploaded_file = None
                if valid_url:
                    fd, uploaded_file_name = tempfile.mkstemp()
                    uploaded_file = open( uploaded_file_name, 'wb' )
                    while 1:
                        chunk = stream.read( util.CHUNK_SIZE )
                        if not chunk:
                            break
                        uploaded_file.write( chunk )
                    uploaded_file.flush()
                    uploaded_file_filename = url.split( '/' )[ -1 ]
                    isempty = os.path.getsize( os.path.abspath( uploaded_file_name ) ) == 0
            elif file_data not in ( '', None ):
                uploaded_file = file_data.file
                uploaded_file_name = uploaded_file.name
                uploaded_file_filename = os.path.split( file_data.filename )[ -1 ]
                isempty = os.path.getsize( os.path.abspath( uploaded_file_name ) ) == 0
            if uploaded_file or uploaded_directory:
                ok = True
                isgzip = False
                isbz2 = False
                if uploaded_file:
                    if uncompress_file:
                        isgzip = checkers.is_gzip( uploaded_file_name )
                        if not isgzip:
                            isbz2 = checkers.is_bz2( uploaded_file_name )
                    if isempty:
                        tar = None
                        istar = False
                    else:                
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
                else:
                    # Uploaded directory
                    istar = False
                if istar:
                    ok, message, files_to_remove, content_alert_str, undesirable_dirs_removed, undesirable_files_removed = \
                        self.upload_tar( trans, repository, tar, uploaded_file, upload_point, remove_repo_files_not_in_tar, commit_message, new_repo_alert )
                elif uploaded_directory:
                    ok, message, files_to_remove, content_alert_str, undesirable_dirs_removed, undesirable_files_removed = \
                        self.upload_directory( trans, repository, uploaded_directory, upload_point, remove_repo_files_not_in_tar, commit_message, new_repo_alert )
                else:
                    if ( isgzip or isbz2 ) and uncompress_file:
                        uploaded_file_filename = commit_util.uncompress( repository, uploaded_file_name, uploaded_file_filename, isgzip, isbz2 )
                    if upload_point is not None:
                        full_path = os.path.abspath( os.path.join( repo_dir, upload_point, uploaded_file_filename ) )
                    else:
                        full_path = os.path.abspath( os.path.join( repo_dir, uploaded_file_filename ) )
                    # Move some version of the uploaded file to the load_point within the repository hierarchy.
                    if uploaded_file_filename in [ 'repository_dependencies.xml' ]:
                        # Inspect the contents of the file to see if changeset_revision values are missing and if so, set them appropriately.
                        altered, root_elem = commit_util.handle_repository_dependencies_definition( trans, uploaded_file_name )
                        if altered:
                            tmp_filename = commit_util.create_and_write_tmp_file( root_elem )
                            shutil.move( tmp_filename, full_path )
                        else:
                            shutil.move( uploaded_file_name, full_path )
                    elif uploaded_file_filename in [ 'tool_dependencies.xml' ]:
                        # Inspect the contents of the file to see if it defines a complex repository dependency definition whose changeset_revision values
                        # are missing and if so, set them appropriately.
                        altered, root_elem = commit_util.handle_tool_dependencies_definition( trans, uploaded_file_name )
                        if altered:
                            tmp_filename = commit_util.create_and_write_tmp_file( root_elem )
                            shutil.move( tmp_filename, full_path )
                        else:
                            shutil.move( uploaded_file_name, full_path )
                    else:
                        shutil.move( uploaded_file_name, full_path )
                    # See if any admin users have chosen to receive email alerts when a repository is updated.  If so, check every uploaded file to ensure
                    # content is appropriate.
                    check_contents = commit_util.check_file_contents_for_email_alerts( trans )
                    if check_contents and os.path.isfile( full_path ):
                        content_alert_str = commit_util.check_file_content_for_html_and_images( full_path )
                    else:
                        content_alert_str = ''
                    commands.add( repo.ui, repo, full_path )
                    # Convert from unicode to prevent "TypeError: array item must be char"
                    full_path = full_path.encode( 'ascii', 'replace' )
                    commands.commit( repo.ui, repo, full_path, user=trans.user.username, message=commit_message )
                    if full_path.endswith( 'tool_data_table_conf.xml.sample' ):
                        # Handle the special case where a tool_data_table_conf.xml.sample file is being uploaded by parsing the file and adding new entries
                        # to the in-memory trans.app.tool_data_tables dictionary.
                        error, error_message = tool_util.handle_sample_tool_data_table_conf_file( trans.app, full_path )
                        if error:
                            message = '%s<br/>%s' % ( message, error_message )
                    # See if the content of the change set was valid.
                    admin_only = len( repository.downloadable_revisions ) != 1
                    suc.handle_email_alerts( trans, repository, content_alert_str=content_alert_str, new_repo_alert=new_repo_alert, admin_only=admin_only )
                if ok:
                    # Update the repository files for browsing.
                    suc.update_repository( repo )
                    # Get the new repository tip.
                    if tip == repository.tip( trans.app ):
                        message = 'No changes to repository.  '
                        status = 'warning'
                    else:
                        if ( isgzip or isbz2 ) and uncompress_file:
                            uncompress_str = ' uncompressed and '
                        else:
                            uncompress_str = ' '
                        if uploaded_directory:
                            source_type = "repository"
                            source = url
                        else:
                            source_type = "file"
                            source = uploaded_file_filename
                        message = "The %s <b>%s</b> has been successfully%suploaded to the repository.  " % ( source_type, source, uncompress_str )
                        if istar and ( undesirable_dirs_removed or undesirable_files_removed ):
                            items_removed = undesirable_dirs_removed + undesirable_files_removed
                            message += "  %d undesirable items (.hg .svn .git directories, .DS_Store, hgrc files, etc) were removed from the archive.  " % items_removed
                        if istar and remove_repo_files_not_in_tar and files_to_remove:
                            if upload_point is not None:
                                message += "  %d files were removed from the repository relative to the selected upload point '%s'.  " % ( len( files_to_remove ), upload_point )
                            else:
                                message += "  %d files were removed from the repository root.  " % len( files_to_remove )
                        kwd[ 'message' ] = message
                        metadata_util.set_repository_metadata_due_to_new_tip( trans, repository, content_alert_str=content_alert_str, **kwd )
                    if repository.metadata_revisions:
                        # A repository's metadata revisions are order descending by update_time, so the zeroth revision will be the tip just after an upload.
                        metadata_dict = repository.metadata_revisions[0].metadata
                    else:
                        metadata_dict = {}
                    # Provide a warning message if a tool_dependencies.xml file is provided, but tool dependencies weren't loaded due to a requirement tag mismatch
                    # or some other problem.  Tool dependency definitions can define orphan tool dependencies (no relationship to any tools contained in the repository),
                    # so warning messages are important because orphans are always valid.  The repository owner must be warned in case they did not intend to define an
                    # orphan dependency, but simply provided incorrect information (tool shed, name owner, changeset_revision) for the definition.
                    # Handle messaging for orphan tool dependencies.
                    orphan_message = tool_dependency_util.generate_message_for_orphan_tool_dependencies( metadata_dict )
                    if orphan_message:
                        message += orphan_message
                        status = 'warning'
                    # Handle messaging for invalid tool dependencies.
                    invalid_tool_dependencies_message = tool_dependency_util.generate_message_for_invalid_tool_dependencies( metadata_dict )
                    if invalid_tool_dependencies_message:
                        message += invalid_tool_dependencies_message
                        status = 'error'
                    # Handle messaging for invalid repository dependencies.
                    invalid_repository_dependencies_message = repository_dependency_util.generate_message_for_invalid_repository_dependencies( metadata_dict )
                    if invalid_repository_dependencies_message:
                        message += invalid_repository_dependencies_message
                        status = 'error'
                    # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
                    tool_util.reset_tool_data_tables( trans.app )
                    trans.response.send_redirect( web.url_for( controller='repository',
                                                               action='browse_repository',
                                                               id=repository_id,
                                                               commit_message='Deleted selected files',
                                                               message=message,
                                                               status=status ) )
                else:
                    status = 'error'
                # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
                tool_util.reset_tool_data_tables( trans.app )
        selected_categories = [ trans.security.decode_id( id ) for id in category_ids ]
        return trans.fill_template( '/webapps/tool_shed/repository/upload.mako',
                                    repository=repository,
                                    url=url,
                                    commit_message=commit_message,
                                    uncompress_file=uncompress_file,
                                    remove_repo_files_not_in_tar=remove_repo_files_not_in_tar,
                                    message=message,
                                    status=status )

    def upload_directory( self, trans, repository, uploaded_directory, upload_point, remove_repo_files_not_in_tar, commit_message, new_repo_alert ):
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        undesirable_dirs_removed = 0
        undesirable_files_removed = 0
        if upload_point is not None:
            full_path = os.path.abspath( os.path.join( repo_dir, upload_point ) )
        else:
            full_path = os.path.abspath( repo_dir )
        filenames_in_archive = []
        for root, dirs, files in os.walk( uploaded_directory ):
            for uploaded_file in files:
                relative_path = os.path.normpath( os.path.join( os.path.relpath( root, uploaded_directory ), uploaded_file ) )
                ok = os.path.basename( uploaded_file ) not in commit_util.UNDESIRABLE_FILES
                if ok:
                    for file_path_item in relative_path.split( '/' ):
                        if file_path_item in commit_util.UNDESIRABLE_DIRS:
                            undesirable_dirs_removed += 1
                            ok = False
                            break
                else:
                    undesirable_files_removed += 1
                uploaded_file_name = os.path.abspath( os.path.join( root, uploaded_file ) )
                if os.path.split( uploaded_file_name )[ -1 ] == 'repository_dependencies.xml':
                    # Inspect the contents of the file to see if changeset_revision values are missing and if so, set them appropriately.
                    altered, root_elem = commit_util.handle_repository_dependencies_definition( trans, uploaded_file_name )
                    if altered:
                        tmp_filename = commit_util.create_and_write_tmp_file( root_elem )
                        shutil.move( tmp_filename, uploaded_file_name )
                elif os.path.split( uploaded_file_name )[ -1 ] == 'tool_dependencies.xml':
                    # Inspect the contents of the file to see if changeset_revision values are missing and if so, set them appropriately.
                    altered, root_elem = commit_util.handle_tool_dependencies_definition( trans, uploaded_file_name )
                    if altered:
                        tmp_filename = commit_util.create_and_write_tmp_file( root_elem )
                        shutil.move( tmp_filename, uploaded_file_name )
                if ok:
                    repo_path = os.path.join( full_path, relative_path )
                    repo_basedir = os.path.normpath( os.path.join( repo_path, os.path.pardir ) )
                    if not os.path.exists( repo_basedir ):
                        os.makedirs( repo_basedir )
                    if os.path.exists( repo_path ):
                        if os.path.isdir( repo_path ):
                            shutil.rmtree( repo_path )
                        else:
                            os.remove( repo_path )
                    shutil.move( os.path.join( uploaded_directory, relative_path ), repo_path )
                    filenames_in_archive.append( relative_path )
        return commit_util.handle_directory_changes( trans, repository, full_path, filenames_in_archive, remove_repo_files_not_in_tar,
                                                     new_repo_alert, commit_message, undesirable_dirs_removed, undesirable_files_removed )

    def upload_tar( self, trans, repository, tar, uploaded_file, upload_point, remove_repo_files_not_in_tar, commit_message, new_repo_alert ):
        # Upload a tar archive of files.
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        undesirable_dirs_removed = 0
        undesirable_files_removed = 0
        ok, message = commit_util.check_archive( tar )
        if not ok:
            tar.close()
            uploaded_file.close()
            return ok, message, [], '', undesirable_dirs_removed, undesirable_files_removed
        else:
            if upload_point is not None:
                full_path = os.path.abspath( os.path.join( repo_dir, upload_point ) )
            else:
                full_path = os.path.abspath( repo_dir )
            filenames_in_archive = []
            for tarinfo_obj in tar.getmembers():
                ok = os.path.basename( tarinfo_obj.name ) not in commit_util.UNDESIRABLE_FILES
                if ok:
                    for file_path_item in tarinfo_obj.name.split( '/' ):
                        if file_path_item in commit_util.UNDESIRABLE_DIRS:
                            undesirable_dirs_removed += 1
                            ok = False
                            break
                else:
                    undesirable_files_removed += 1
                if ok:
                    filenames_in_archive.append( tarinfo_obj.name )
            # Extract the uploaded tar to the load_point within the repository hierarchy.
            tar.extractall( path=full_path )
            tar.close()
            uploaded_file.close()
            for filename in filenames_in_archive:
                uploaded_file_name = os.path.join( full_path, filename )
                if os.path.split( uploaded_file_name )[ -1 ] == 'repository_dependencies.xml':
                    # Inspect the contents of the file to see if changeset_revision values are missing and if so, set them appropriately.
                    altered, root_elem = commit_util.handle_repository_dependencies_definition( trans, uploaded_file_name )
                    if altered:
                        tmp_filename = commit_util.create_and_write_tmp_file( root_elem )
                        shutil.move( tmp_filename, uploaded_file_name )
                elif os.path.split( uploaded_file_name )[ -1 ] == 'tool_dependencies.xml':
                    # Inspect the contents of the file to see if changeset_revision values are missing and if so, set them appropriately.
                    altered, root_elem = commit_util.handle_tool_dependencies_definition( trans, uploaded_file_name )
                    if altered:
                        tmp_filename = commit_util.create_and_write_tmp_file( root_elem )
                        shutil.move( tmp_filename, uploaded_file_name )
            return commit_util.handle_directory_changes( trans,
                                                         repository,
                                                         full_path,
                                                         filenames_in_archive,
                                                         remove_repo_files_not_in_tar,
                                                         new_repo_alert,
                                                         commit_message,
                                                         undesirable_dirs_removed,
                                                         undesirable_files_removed )
