import cStringIO
import gzip
import logging
import os
import pkg_resources
import shutil
import struct
import tempfile
from galaxy import util
from galaxy.datatypes import checkers
from galaxy.util import json
from galaxy.web import url_for
import tool_shed.util.shed_util_common as suc
from tool_shed.util import tool_util
from tool_shed.util import xml_util
import tool_shed.repository_types.util as rt_util

from galaxy import eggs
eggs.require( 'mercurial' )
from mercurial import commands
from mercurial import hg
from mercurial import ui
from mercurial.changegroup import readbundle
from mercurial.changegroup import readexactly
from mercurial.changegroup import writebundle

log = logging.getLogger( __name__ )

UNDESIRABLE_DIRS = [ '.hg', '.svn', '.git', '.cvs' ]
UNDESIRABLE_FILES = [ '.hg_archival.txt', 'hgrc', '.DS_Store' ]

def bundle_to_json( fh ):
    """Convert the received HG10xx data stream (a mercurial 1.0 bundle created using hg push from the command line) to a json object."""
    # See http://www.wstein.org/home/wstein/www/home/was/patches/hg_json
    hg_unbundle10_obj = readbundle( fh, None )
    groups = [ group for group in unpack_groups( hg_unbundle10_obj ) ]
    return json.to_json_string( groups, indent=4 )
    
def check_archive( repository, archive ):
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
        if repository.type == rt_util.TOOL_DEPENDENCY_DEFINITION and member.name != suc.TOOL_DEPENDENCY_DEFINITION_FILENAME:
            message = 'Repositories of type <b>Tool dependency definition</b> can contain only a single file named <b>tool_dependencies.xml</b>.'
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

def get_change_lines_in_file_for_tag( tag, change_dict ):
    """
    The received change_dict is the jsonified version of the changes to a file in a changeset being pushed to the tool shed from the command line.
    This method cleans and returns appropriate lines for inspection.
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
    fd, uncompressed = tempfile.mkstemp( prefix='repo_%d_upload_bunzip2_' % repository.id, dir=os.path.dirname( uploaded_file_name ), text=False )
    bzipped_file = bz2.BZ2File( uploaded_file_name, 'rb' )
    while 1:
        try:
            chunk = bzipped_file.read( suc.CHUNK_SIZE )
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
    # See if any admin users have chosen to receive email alerts when a repository is updated.  If so, check every uploaded file to ensure
    # content is appropriate.
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

def handle_missing_repository_attribute( elem ):
    # <repository name="molecule_datatypes" owner="test" />
    error_message = ''
    name = elem.get( 'name' )
    if not name:
        error_message += 'The tag is missing the required name attribute.  '
    owner = elem.get( 'owner' )
    if not owner:
        error_message += 'The tag is missing the required owner attribute.  '
    log.debug( error_message )
    return error_message
    
def handle_gzip( repository, uploaded_file_name ):
    fd, uncompressed = tempfile.mkstemp( prefix='repo_%d_upload_gunzip_' % repository.id, dir=os.path.dirname( uploaded_file_name ), text=False )
    gzipped_file = gzip.GzipFile( uploaded_file_name, 'rb' )
    while 1:
        try:
            chunk = gzipped_file.read( suc.CHUNK_SIZE )
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
    # Make sure we're looking at a valid repository_dependencies.xml file.
    tree, error_message = xml_util.parse_xml( repository_dependencies_config )
    if tree is None:
        return False, None
    root = tree.getroot()
    if root.tag == 'repositories':
        for index, elem in enumerate( root ):
            if elem.tag == 'repository':
                # <repository name="molecule_datatypes" owner="test" changeset_revision="1a070566e9c6" />
                populated, elem, error_message = handle_repository_dependency_elem( trans, elem )
                if error_message:
                    exception_message = 'The repository_dependencies.xml file contains an invalid <repository> tag.  %s' % error_message
                    raise Exception( exception_message )
                if populated:
                    root[ index ] = elem
                    if not altered:
                        altered = True
        return altered, root
    return False, None

def handle_repository_dependency_elem( trans, elem ):
    # <repository name="molecule_datatypes" owner="test" changeset_revision="1a070566e9c6" />
    error_message = ''
    name = elem.get( 'name' )
    owner = elem.get( 'owner' )
    if not name or not owner:
        error_message = handle_missing_repository_attribute( elem )
        return False, elem, error_message
    populated = False
    toolshed = elem.get( 'toolshed' )
    if not toolshed:
        # Default the setting to the current tool shed.
        toolshed = str( url_for( '/', qualified=True ) ).rstrip( '/' )
        elem.attrib[ 'toolshed' ] = toolshed
        populated = True
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
        else:
            error_message = 'Unable to locate repository with name %s and owner %s.  ' % ( str( name ), str( owner ) )
    return populated, elem, error_message

def handle_tool_dependencies_definition( trans, tool_dependencies_config ):
    altered = False
    # Make sure we're looking at a valid tool_dependencies.xml file.
    tree, error_message = xml_util.parse_xml( tool_dependencies_config )
    if tree is None:
        return False, None
    root = tree.getroot()        
    if root.tag == 'tool_dependency':
        for root_index, root_elem in enumerate( root ):
            # <package name="eigen" version="2.0.17">
            if root_elem.tag == 'package':
                package_altered = False
                for package_index, package_elem in enumerate( root_elem ):
                    if package_elem.tag == 'repository':
                        # <repository name="package_eigen_2_0" owner="test" changeset_revision="09eb05087cd0" prior_installation_required="True" />
                        populated, repository_elem, error_message = handle_repository_dependency_elem( trans, package_elem )
                        if error_message:
                            exception_message = 'The tool_dependencies.xml file contains an invalid <repository> tag.  %s' % error_message
                            raise Exception( exception_message )
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
                                        populated, repository_elem, error_message = handle_repository_dependency_elem( trans, repo_elem )
                                        if error_message:
                                            exception_message = 'The tool_dependencies.xml file contains an invalid <repository> tag.  %s' % error_message
                                            raise Exception( exception_message )
                                        if populated:
                                            action_elem[ repo_index ] = repository_elem
                                            package_altered = True
                                            if not altered:
                                                altered = True
                                    if package_altered:
                                        actions_elem[ action_index ] = action_elem
                            if package_altered:
                                package_elem[ actions_index ] = actions_elem
                        if package_altered:
                            root_elem[ package_index ] = package_elem
                if package_altered:
                    root[ root_index ] = root_elem
        return altered, root
    return False, None

def repository_tag_is_valid( filename, line ):
    """
    Checks changes made to <repository> tags in a dependency definition file being pushed to the tool shed from the command line to ensure that
    all required attributes exist.
    """
    required_attributes = [ 'toolshed', 'name', 'owner', 'changeset_revision' ]
    defined_attributes = line.split()
    for required_attribute in required_attributes:
        defined = False
        for defined_attribute in defined_attributes:
            if defined_attribute.startswith( required_attribute ):
                defined = True
                break
        if not defined:
            error_msg = 'The %s file contains a <repository> tag that is missing the required attribute %s.  ' % ( filename, required_attribute )
            error_msg += 'Automatically populating dependency definition attributes occurs only when using the tool shed upload utility.  '
            return False, error_msg
    return True, ''

def repository_tags_are_valid( filename, change_list ):
    """
    Make sure the any complex repository dependency definitions contain valid <repository> tags when pushing changes to the tool shed on the command
    line.
    """
    tag = '<repository'
    for change_dict in change_list:
        lines = get_change_lines_in_file_for_tag( tag, change_dict )
        for line in lines:
            is_valid, error_msg = repository_tag_is_valid( filename, line )
            if not is_valid:
                return False, error_msg
    return True, ''

def uncompress( repository, uploaded_file_name, uploaded_file_filename, isgzip, isbz2 ):
    if isgzip:
        handle_gzip( repository, uploaded_file_name )
        return uploaded_file_filename.rstrip( '.gz' )
    if isbz2:
        handle_bz2( repository, uploaded_file_name )
        return uploaded_file_filename.rstrip( '.bz2' )

def unpack_chunks( hg_unbundle10_obj ):
    """
    This method provides a generator of parsed chunks of a "group" in a mercurial unbundle10 object which is created when a changeset that is pushed
    to a tool shed repository using hg push from the command line is read using readbundle.
    """
    while True:
        length, = struct.unpack( '>l', readexactly( hg_unbundle10_obj, 4 ) )
        if length <= 4:
            # We found a "null chunk", which ends the group.
            break
        if length < 84:
            raise Exception( "negative data length" )
        node, p1, p2, cs = struct.unpack( '20s20s20s20s', readexactly( hg_unbundle10_obj, 80 ) )
        yield { 'node': node.encode( 'hex' ),
                'p1': p1.encode( 'hex' ),
                'p2': p2.encode( 'hex' ),
                'cs': cs.encode( 'hex' ),
                'data': [ patch for patch in unpack_patches( hg_unbundle10_obj, length - 84 ) ] }

def unpack_groups( hg_unbundle10_obj ):
    """
    This method provides a generator of parsed groups from a mercurial unbundle10 object which is created when a changeset that is pushed
    to a tool shed repository using hg push from the command line is read using readbundle.
    """
    # Process the changelog group.
    yield [ chunk for chunk in unpack_chunks( hg_unbundle10_obj ) ]
    # Process the manifest group.
    yield [ chunk for chunk in unpack_chunks( hg_unbundle10_obj ) ]
    while True:
        length, = struct.unpack( '>l', readexactly( hg_unbundle10_obj, 4 ) )
        if length <= 4:
            # We found a "null meta chunk", which ends the changegroup.
            break
        filename = readexactly( hg_unbundle10_obj, length-4 ).encode( 'string_escape' )
        # Process the file group.
        yield ( filename, [ chunk for chunk in unpack_chunks( hg_unbundle10_obj ) ] )

def unpack_patches( hg_unbundle10_obj, remaining ):
    """
    This method provides a generator of patches from the data field in a chunk. As there is no delimiter for this data field, a length argument is
    required.
    """
    while remaining >= 12:
        start, end, blocklen = struct.unpack( '>lll', readexactly( hg_unbundle10_obj, 12 ) )
        remaining -= 12
        if blocklen > remaining:
            raise Exception( "unexpected end of patch stream" )
        block = readexactly( hg_unbundle10_obj, blocklen )
        remaining -= blocklen
        yield { 'start': start,
                'end': end,
                'blocklen': blocklen,
                'block': block.encode( 'string_escape' ) }
    if remaining > 0:
        print remaining
        raise Exception( "unexpected end of patch stream" )
