import logging
import os
import shutil
import tarfile
import tempfile
import urllib
from galaxy import util
from galaxy.datatypes import checkers
from tool_shed.util import commit_util
from tool_shed.util import encoding_util
from tool_shed.util import hg_util
from tool_shed.util import metadata_util
from tool_shed.util import xml_util
import tool_shed.util.shed_util_common as suc

from galaxy import eggs
eggs.require( 'mercurial' )

from mercurial import commands
from mercurial import hg
from mercurial import ui

log = logging.getLogger( __name__ )

def check_status_and_reset_downloadable( trans, import_results_tups ):
    """Check the status of each imported repository and set downloadable to False if errors."""
    flush = False
    for import_results_tup in import_results_tups:
        ok, name_owner, message = import_results_tup
        name, owner = name_owner
        if not ok:
            repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
            if repository is not None:
                # Do not allow the repository to be automatically installed if population resulted in errors.
                tip_changeset_revision = repository.tip( trans.app )
                repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans,
                                                                                         trans.security.encode_id( repository.id ),
                                                                                         tip_changeset_revision )
                if repository_metadata:
                    if repository_metadata.downloadable:
                        repository_metadata.downloadable = False
                        trans.sa_session.add( repository_metadata )
                        if not flush:
                            flush = True
                    # Do not allow dependent repository revisions to be automatically installed if population
                    # resulted in errors.
                    dependent_downloadable_revisions = suc.get_dependent_downloadable_revisions( trans, repository_metadata )
                    for dependent_downloadable_revision in dependent_downloadable_revisions:
                        if dependent_downloadable_revision.downloadable:
                            dependent_downloadable_revision.downloadable = False
                            trans.sa_session.add( dependent_downloadable_revision )
                            if not flush:
                                flush = True
    if flush:
        trans.sa_session.flush()

def extract_capsule_files( trans, **kwd ):
    """Extract the uploaded capsule archive into a temporary location for inspection, validation and potential import."""
    return_dict = {}
    tar_archive = kwd.get( 'tar_archive', None )
    capsule_file_name = kwd.get( 'capsule_file_name', None )
    if tar_archive is not None and capsule_file_name is not None:
        return_dict.update( kwd )
        extract_directory_path = tempfile.mkdtemp( prefix="tmp-capsule-ecf" )
        if capsule_file_name.endswith( '.tar.gz' ):
            extract_directory_name = capsule_file_name.replace( '.tar.gz', '' )
        elif capsule_file_name.endswith( '.tar' ):
            extract_directory_name = capsule_file_name.replace( '.tar', '' )
        else:
            extract_directory_name = capsule_file_name
        file_path = os.path.join( extract_directory_path, extract_directory_name )
        return_dict[ 'encoded_file_path' ] = encoding_util.tool_shed_encode( file_path )
        tar_archive.extractall( path=file_path )
        try:
            tar_archive.close()
        except Exception, e:
            log.exception( "Cannot close tar_archive: %s" % str( e ) )
        del return_dict[ 'tar_archive' ]
    return return_dict

def get_archives_from_manifest( manifest_file_path ):
    """
    Return the list of archive names defined in the capsule manifest.  This method sill validate the manifest by ensuring all
    <repository> tag sets contain a valid <archive> sub-element.
    """
    archives = []
    error_message = ''
    manifest_tree, error_message = xml_util.parse_xml( manifest_file_path )
    if error_message:
        return archives, error_message
    manifest_root = manifest_tree.getroot()
    for elem in manifest_root:
        # <repository name="package_lapack_3_4" type="tool_dependency_definition" username="test">
        if elem.tag != 'repository':
            error_message = 'All level one sub-elements in the manifest.xml file must be <repository> tag sets.  '
            error_message += 'The tag <b><%s></b> is invalid.' % str( elem.tag )
            return [], error_message
        archive_file_name = None
        for repository_elem in elem:
            if repository_elem.tag == 'archive':
                # <archive>package_lapack_3_4-9e7a45ad3522.tar.gz</archive>
                archive_file_name = repository_elem.text
                break
        if archive_file_name is None:
            error_message = 'The %s tag set is missing a required <archive> sub-element.' % str( elem.tag )
            return [], error_message
        archives.append( archive_file_name )
    return archives, error_message

def get_export_info_dict( export_info_file_path ):
    """Parse the export_info.xml file contained within the capsule and return a dictionary containing its entries."""
    export_info_tree, error_message = xml_util.parse_xml( export_info_file_path )
    export_info_root = export_info_tree.getroot()
    export_info_dict = {}
    for elem in export_info_root:
        if elem.tag == 'export_time':
            export_info_dict[ 'export_time' ] = elem.text
        elif elem.tag == 'tool_shed':
            export_info_dict[ 'tool_shed' ] = elem.text
        elif elem.tag == 'repository_name':
            export_info_dict[ 'repository_name' ] = elem.text
        elif elem.tag == 'repository_owner':
            export_info_dict[ 'repository_owner' ] = elem.text
        elif elem.tag == 'changeset_revision':
            export_info_dict[ 'changeset_revision' ] = elem.text
        elif elem.tag == 'export_repository_dependencies':
            if util.asbool( elem.text ):
                export_info_dict[ 'export_repository_dependencies' ] = 'Yes'
            else:
                export_info_dict[ 'export_repository_dependencies' ] = 'No'
    return export_info_dict

def get_repository_info_from_manifest( manifest_file_path ):
    """
    Parse the capsule manifest and return a list of dictionaries containing information about each exported repository
    archive contained within the capsule.
    """
    repository_info_dicts = []
    manifest_tree, error_message = xml_util.parse_xml( manifest_file_path )
    if error_message:
        return repository_info_dicts, error_message
    manifest_root = manifest_tree.getroot()
    for elem in manifest_root:
        # <repository name="package_lapack_3_4" type="tool_dependency_definition" username="test">
        if elem.tag != 'repository':
            error_message = 'All level one sub-elements in the manifest.xml file must be <repository> tag sets.  '
            error_message += 'The tag <b><%s></b> is invalid.' % str( elem.tag )
            return [], error_message
        name = elem.get( 'name', None )
        owner = elem.get( 'username', None )
        type = elem.get( 'type', None )
        if name is None or owner is None or type is None:
            error_message = 'Missing required name, type, owner attributes from the tag %s' % str( elem.tag )
            return [], error_message
        repository_info_dict = dict( name=name, owner=owner, type=type )
        for repository_elem in elem:
            if repository_elem.tag == 'archive':
                # <archive>package_lapack_3_4-9e7a45ad3522.tar.gz</archive>
                archive_file_name = repository_elem.text
                repository_info_dict[ 'archive_file_name' ] = archive_file_name
                items = archive_file_name.split( '-' )
                changeset_revision = items[ 1 ].rstrip( '.tar.gz' )
                repository_info_dict [ 'changeset_revision' ] = changeset_revision
            elif repository_elem.tag == 'categories':
                category_names = []
                for category_elem in repository_elem:
                    if category_elem.tag == 'category':
                        category_names.append( category_elem.text )
                repository_info_dict[ 'category_names' ] = category_names
            elif repository_elem.tag == 'description':
                repository_info_dict[ 'description' ] = repository_elem.text
            elif repository_elem.tag == 'long_description':
                repository_info_dict[ 'long_description' ] = repository_elem.text
        repository_info_dicts.append( repository_info_dict )
    return repository_info_dicts, error_message

def get_repository_status_from_tool_shed( trans, repository_info_dicts ):
    """
    For each exported repository archive contained in the capsule, inspect the Tool Shed to see if that repository already
    exists or if the current user is authorized to create the repository, and set a status appropriately.  If repository
    dependencies are included in the capsule, repositories may have various owners.  We will keep repositories associated
    with owners, so we need to restrict created repositories to those the current user can create.  If the current user is
    an admin or a member of the IUC, all repositories will be created no matter the owner.  Otherwise, only repositories
    whose associated owner is the current user will be created.
    """
    repository_status_info_dicts = []
    for repository_info_dict in repository_info_dicts:
        repository = suc.get_repository_by_name_and_owner( trans.app, repository_info_dict[ 'name' ], repository_info_dict[ 'owner' ] )
        if repository:
            if repository.deleted:
                repository_info_dict[ 'status' ] = 'Exists, deleted'
            elif repository.deprecated:
                repository_info_dict[ 'status' ] = 'Exists, deprecated'
            else:
                repository_info_dict[ 'status' ] = 'Exists'
        else:
            # No repository with the specified name and owner currently exists, so make sure the current user can create one.
            if trans.user_is_admin():
                repository_info_dict[ 'status' ] = None
            elif trans.app.security_agent.user_can_import_repository_archive( trans.user, repository_info_dict[ 'owner' ] ):
                repository_info_dict[ 'status' ] = None
            else:
                repository_info_dict[ 'status' ] = 'Not authorized to import'
        repository_status_info_dicts.append( repository_info_dict )
    return repository_status_info_dicts

def import_repository_archive( trans, repository, repository_archive_dict ):
    """Import a repository archive contained within a repository capsule."""
    archive_file_name = repository_archive_dict.get( 'archive_file_name', None )
    capsule_file_name = repository_archive_dict[ 'capsule_file_name' ]
    encoded_file_path = repository_archive_dict[ 'encoded_file_path' ]
    file_path = encoding_util.tool_shed_decode( encoded_file_path )
    results_dict = dict( ok=True, error_message='' )
    archive_file_path = os.path.join( file_path, archive_file_name )
    archive = tarfile.open( archive_file_path, 'r:*' )
    repo_dir = repository.repo_path( trans.app )
    repo = hg.repository( hg_util.get_configured_ui(), repo_dir )
    undesirable_dirs_removed = 0
    undesirable_files_removed = 0
    ok, error_message = commit_util.check_archive( repository, archive )
    if ok:
        full_path = os.path.abspath( repo_dir )
        filenames_in_archive = []
        for tarinfo_obj in archive.getmembers():
            # Check files and directories in the archive.
            ok = os.path.basename( tarinfo_obj.name ) not in commit_util.UNDESIRABLE_FILES
            if ok:
                for file_path_item in tarinfo_obj.name.split( '/' ):
                    if file_path_item in commit_util.UNDESIRABLE_DIRS:
                        undesirable_dirs_removed += 1
                        error_message = 'Import failed: invalid file path <b>%s</b> in archive <b>%s</b>' % \
                            ( str( file_path_item ), str( archive_file_name ) )
                        results_dict[ 'ok' ] = False
                        results_dict[ 'error_message' ] += error_message
                        return results_dict
                filenames_in_archive.append( tarinfo_obj.name )
            else:
                undesirable_files_removed += 1
        # Extract the uploaded archive to the repository root.
        archive.extractall( path=full_path )
        archive.close()
        for filename in filenames_in_archive:
            uploaded_file_name = os.path.join( full_path, filename )
            if os.path.split( uploaded_file_name )[ -1 ] == suc.REPOSITORY_DEPENDENCY_DEFINITION_FILENAME:
                # Inspect the contents of the file to see if changeset_revision values are missing and if so, set them appropriately.
                altered, root_elem, error_message = commit_util.handle_repository_dependencies_definition( trans,
                                                                                                           uploaded_file_name,
                                                                                                           unpopulate=False )
                if error_message:
                    results_dict[ 'ok' ] = False
                    results_dict[ 'error_message' ] += error_message
                if altered:
                    tmp_filename = xml_util.create_and_write_tmp_file( root_elem )
                    shutil.move( tmp_filename, uploaded_file_name )
            elif os.path.split( uploaded_file_name )[ -1 ] == suc.TOOL_DEPENDENCY_DEFINITION_FILENAME:
                # Inspect the contents of the file to see if changeset_revision values are missing and if so, set them appropriately.
                altered, root_elem, error_message = commit_util.handle_tool_dependencies_definition( trans, uploaded_file_name )
                if error_message:
                    results_dict[ 'ok' ] = False
                    results_dict[ 'error_message' ] += error_message
                if altered:
                    tmp_filename = xml_util.create_and_write_tmp_file( root_elem )
                    shutil.move( tmp_filename, uploaded_file_name )
        commit_message = 'Imported from capsule %s' % str( capsule_file_name )
        # Send email notification to those that have registered to receive alerts for new repositories in this Tool Shed.
        new_repo_alert = True
        # Since the repository is new, the following must be False.
        remove_repo_files_not_in_tar = False
        ok, error_message, files_to_remove, content_alert_str, undesirable_dirs_removed, undesirable_files_removed = \
            commit_util.handle_directory_changes( trans,
                                                  repository,
                                                  full_path,
                                                  filenames_in_archive,
                                                  remove_repo_files_not_in_tar,
                                                  new_repo_alert,
                                                  commit_message,
                                                  undesirable_dirs_removed,
                                                  undesirable_files_removed )
        if error_message:
            results_dict[ 'ok' ] = False
            results_dict[ 'error_message' ] += error_message
        try:
            metadata_util.set_repository_metadata_due_to_new_tip( trans,
                                                                  repository,
                                                                  content_alert_str=content_alert_str )
        except Exception, e:
            log.debug( "Error setting metadata on repository %s created from imported archive %s: %s" % \
                ( str( repository.name ), str( archive_file_name ), str( e ) ) )
    else:
        archive.close()
        results_dict[ 'ok' ] = False
        results_dict[ 'error_message' ] += error_message
    return results_dict

def upload_capsule( trans, **kwd ):
    """Upload and prepare an exported repository capsule for validation."""
    file_data = kwd.get( 'file_data', '' )
    url = kwd.get( 'url', '' )
    uploaded_file = None
    return_dict = dict( error_message='',
                        encoded_file_path=None,
                        status='ok',
                        tar_archive=None,
                        uploaded_file=None,
                        capsule_file_name=None )
    if file_data == '' and url == '':
        message = 'No files were entered on the import form.'
        status = 'error'
    elif url:
        valid_url = True
        try:
            stream = urllib.urlopen( url )
        except Exception, e:
            valid_url = False
            message = 'Error importing file via http: %s' % str( e )
            status = 'error'
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
    if uploaded_file is not None:
        if isempty:
            uploaded_file.close()
            return_dict[ 'error_message' ] = 'Your uploaded capsule file is empty.'
            return_dict[ 'status' ] = 'error'
            return return_dict
        try:
            # Open for reading with transparent compression.
            tar_archive = tarfile.open( uploaded_file_name, 'r:*' )
        except tarfile.ReadError, e:
            error_message = 'Error opening file %s: %s' % ( str( uploaded_file_name ), str( e ) )
            log.exception( error_message )
            return_dict[ 'error_message' ] = error_message
            return_dict[ 'status' ] = 'error'
            uploaded_file.close()
            return return_dict
        return_dict[ 'tar_archive' ] = tar_archive
        return_dict[ 'capsule_file_name' ] = uploaded_file_filename
        uploaded_file.close()
    else:
        return_dict[ 'error_message' ] = 'No files were entered on the import form.'
        return_dict[ 'status' ] = 'error'
        return return_dict
    return return_dict

def validate_capsule( trans, **kwd ):
    """Inspect the uploaded capsule's manifest and its contained files to ensure it is a valid repository capsule."""
    capsule_dict = {}
    capsule_dict.update( kwd )
    encoded_file_path = capsule_dict.get( 'encoded_file_path', '' )
    file_path = encoding_util.tool_shed_decode( encoded_file_path )
    # The capsule must contain a valid XML file named export_info.xml.
    export_info_file_path = os.path.join( file_path, 'export_info.xml' )
    export_info_tree, error_message = xml_util.parse_xml( export_info_file_path )
    if error_message:
        capsule_dict[ 'error_message' ] = error_message
        capsule_dict[ 'status' ] = 'error'
        return capsule_dict
    # The capsule must contain a valid XML file named manifest.xml.
    manifest_file_path = os.path.join( file_path, 'manifest.xml' )
    # Validate the capsule manifest by inspecting name, owner, changeset_revision and type information contained within
    # each <repository> tag set.
    repository_info_dicts, error_message = get_repository_info_from_manifest( manifest_file_path )
    if error_message:
        capsule_dict[ 'error_message' ] = error_message
        capsule_dict[ 'status' ] = 'error'
        return capsule_dict
    # Validate the capsule manifest by ensuring all <repository> tag sets contain a valid <archive> sub-element.
    archives, error_message = get_archives_from_manifest( manifest_file_path )
    if error_message:
        capsule_dict[ 'error_message' ] = error_message
        capsule_dict[ 'status' ] = 'error'
        return capsule_dict
    # Validate the capsule manifest by ensuring each defined archive file name exists within the capsule.
    error_message = verify_archives_in_capsule( file_path, archives )
    if error_message:
        capsule_dict[ 'error_message' ] = error_message
        capsule_dict[ 'status' ] = 'error'
        return capsule_dict
    capsule_dict[ 'status' ] = 'ok'
    return capsule_dict

def verify_archives_in_capsule( file_path, archives ):
    """Inspect the files contained within the capsule and make sure each is defined correctly in the capsule manifest."""
    error_message = ''
    for archive_file_name in archives:
        full_path = os.path.join( file_path, archive_file_name )
        if not os.path.exists( full_path ):
            error_message = 'The uploaded capsule is invalid because the contained manifest.xml file defines an archive file '
            error_message += 'named <b>%s</b> which is not contained within the capsule.' % str( archive_file_name )
            break
    return error_message
