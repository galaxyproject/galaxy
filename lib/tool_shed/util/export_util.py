import logging
import os
import shutil
import tarfile
import tempfile
import threading
from time import gmtime
from time import strftime
import tool_shed.util.shed_util_common as suc
from galaxy import eggs
from galaxy import web
from galaxy.util.odict import odict
from tool_shed.util import commit_util
from tool_shed.util import common_install_util
from tool_shed.util import common_util
from tool_shed.util import encoding_util
from tool_shed.util import hg_util
from tool_shed.util import repository_dependency_util
from tool_shed.util import xml_util

eggs.require( 'mercurial' )

import mercurial.util
from mercurial import commands
from mercurial import hg
from mercurial import patch
from mercurial import ui

log = logging.getLogger( __name__ )

CAPSULE_FILENAME = 'capsule'
CAPSULE_WITH_DEPENDENCIES_FILENAME = 'capsule_with_dependencies'

class ExportedRepositoryRegistry( object ):

    def __init__( self ):
        self.exported_repository_elems = []

def archive_repository_revision( trans, ui, repository, archive_dir, changeset_revision ):
    '''Create an un-versioned archive of a repository.'''
    repo = hg.repository( hg_util.get_configured_ui(), repository.repo_path( trans.app ) )
    options_dict = hg_util.get_mercurial_default_options_dict( 'archive' )
    options_dict[ 'rev' ] = changeset_revision
    error_message = ''
    return_code = None
    try:
        return_code = commands.archive( ui, repo, archive_dir, **options_dict )
    except Exception, e:
        error_message = "Error attempting to archive revision <b>%s</b> of repository %s: %s\nReturn code: %s\n" % \
            ( str( changeset_revision ), str( repository.name ), str( e ), str( return_code ) )
        log.exception( error_message )
    return return_code, error_message

def export_repository( trans, tool_shed_url, repository_id, repository_name, changeset_revision, file_type,
                       export_repository_dependencies, api=False ):
    repository = suc.get_repository_in_tool_shed( trans, repository_id )
    repositories_archive_filename = generate_repository_archive_filename( tool_shed_url,
                                                                          str( repository.name ),
                                                                          str( repository.user.username ),
                                                                          changeset_revision,
                                                                          file_type,
                                                                          export_repository_dependencies=export_repository_dependencies,
                                                                          use_tmp_archive_dir=True )
    if export_repository_dependencies:
        repo_info_dicts = get_repo_info_dicts( trans, tool_shed_url, repository_id, changeset_revision )
        repository_ids = get_repository_ids( trans, repo_info_dicts )
        ordered_repository_ids, ordered_repositories, ordered_changeset_revisions = \
            order_components_for_import( trans, repository_id, repository_ids, repo_info_dicts )
    else:
        ordered_repository_ids = []
        ordered_repositories = []
        ordered_changeset_revisions = []
        if repository:
            repository_metadata = suc.get_current_repository_metadata_for_changeset_revision( trans, repository, changeset_revision )
            if repository_metadata:
                ordered_repository_ids = [ repository_id ]
                ordered_repositories = [ repository ]
                ordered_changeset_revisions = [ repository_metadata.changeset_revision ]
    repositories_archive = None
    error_messages = ''
    lock = threading.Lock()
    lock.acquire( True )
    try:
        repositories_archive = tarfile.open( repositories_archive_filename, "w:%s" % file_type )
        exported_repository_registry = ExportedRepositoryRegistry()
        for index, repository_id in enumerate( ordered_repository_ids ):
            work_dir = tempfile.mkdtemp( prefix="tmp-toolshed-export-er" )
            ordered_repository = ordered_repositories[ index ]
            ordered_changeset_revision = ordered_changeset_revisions[ index ]
            repository_archive, error_message = generate_repository_archive( trans,
                                                                             work_dir,
                                                                             tool_shed_url,
                                                                             ordered_repository,
                                                                             ordered_changeset_revision,
                                                                             file_type )
            if error_message:
                error_messages = '%s  %s' % ( error_messages, error_message )
            else:
                archive_name = str( os.path.basename( repository_archive.name ) )
                repositories_archive.add( repository_archive.name, arcname=archive_name )
                attributes, sub_elements = get_repository_attributes_and_sub_elements( ordered_repository, archive_name )
                elem = xml_util.create_element( 'repository', attributes=attributes, sub_elements=sub_elements )
                exported_repository_registry.exported_repository_elems.append( elem )
            suc.remove_dir( work_dir )
        # Keep information about the export in a file name export_info.xml in the archive.
        sub_elements = generate_export_elem( tool_shed_url, repository, changeset_revision, export_repository_dependencies, api )
        export_elem = xml_util.create_element( 'export_info', attributes=None, sub_elements=sub_elements )
        tmp_export_info = xml_util.create_and_write_tmp_file( export_elem, use_indent=True )
        repositories_archive.add( tmp_export_info, arcname='export_info.xml' )
        # Write the manifest, which must preserve the order in which the repositories should be imported.
        exported_repository_root = xml_util.create_element( 'repositories' )
        for exported_repository_elem in exported_repository_registry.exported_repository_elems:
            exported_repository_root.append( exported_repository_elem )
        tmp_manifest = xml_util.create_and_write_tmp_file( exported_repository_root, use_indent=True )
        repositories_archive.add( tmp_manifest, arcname='manifest.xml' )
    except Exception, e:
        log.exception( str( e ) )
    finally:
        lock.release()
    repositories_archive.close()
    if api:
        encoded_repositories_archive_name = encoding_util.tool_shed_encode( repositories_archive_filename )
        params = '?encoded_repositories_archive_name=%s' % encoded_repositories_archive_name
        download_url = common_util.url_join( web.url_for( '/', qualified=True ),
                                            'repository/export_via_api%s' % params )
        return dict( download_url=download_url, error_messages=error_messages )
    return repositories_archive, error_messages

def generate_repository_archive( trans, work_dir, tool_shed_url, repository, changeset_revision, file_type ):
    file_type_str = suc.get_file_type_str( changeset_revision, file_type )
    file_name = '%s-%s' % ( repository.name, file_type_str )
    return_code, error_message = archive_repository_revision( trans, ui, repository, work_dir, changeset_revision )
    if return_code:
        return None, error_message
    repository_archive_name = os.path.join( work_dir, file_name )
    # Create a compressed tar archive that will contain only valid files and possibly altered dependency definition files.
    repository_archive = tarfile.open( repository_archive_name, "w:%s" % file_type )
    for root, dirs, files in os.walk( work_dir ):
        if root.find( '.hg' ) < 0 and root.find( 'hgrc' ) < 0:
            for dir in dirs:
                if dir in commit_util.UNDESIRABLE_DIRS:
                    dirs.remove( dir )
            for name in files:
                name = str( name )
                if str( name ) in commit_util.UNDESIRABLE_FILES:
                    continue
                full_path = os.path.join( root, name )
                relative_path = full_path.replace( work_dir, '' ).lstrip( '/' )
                # See if we have a repository dependencies defined.
                if name == suc.REPOSITORY_DEPENDENCY_DEFINITION_FILENAME:
                    # Eliminate the toolshed, and changeset_revision attributes from all <repository> tags.
                    altered, root_elem, error_message = commit_util.handle_repository_dependencies_definition( trans, full_path, unpopulate=True )
                    if error_message:
                        return None, error_message
                    if altered:
                        tmp_filename = xml_util.create_and_write_tmp_file( root_elem, use_indent=True )
                        shutil.move( tmp_filename, full_path )
                elif name == suc.TOOL_DEPENDENCY_DEFINITION_FILENAME:
                    # Eliminate the toolshed, and changeset_revision attributes from all <repository> tags.
                    altered, root_elem, error_message = commit_util.handle_tool_dependencies_definition( trans, full_path, unpopulate=True )
                    if error_message:
                        return None, error_message
                    if altered:
                        tmp_filename = xml_util.create_and_write_tmp_file( root_elem, use_indent=True )
                        shutil.move( tmp_filename, full_path )
                repository_archive.add( full_path, arcname=relative_path )
    repository_archive.close()
    return repository_archive, error_message

def generate_repository_archive_filename( tool_shed_url, name, owner, changeset_revision, file_type, export_repository_dependencies=False, use_tmp_archive_dir=False ):
    tool_shed = remove_protocol_from_tool_shed_url( tool_shed_url )
    file_type_str = suc.get_file_type_str( changeset_revision, file_type )
    if export_repository_dependencies:
        repositories_archive_filename = '%s_%s_%s_%s_%s' % ( CAPSULE_WITH_DEPENDENCIES_FILENAME, tool_shed, name, owner, file_type_str )
    else:
        repositories_archive_filename = '%s_%s_%s_%s_%s' % ( CAPSULE_FILENAME, tool_shed, name, owner, file_type_str )
    if use_tmp_archive_dir:
        tmp_archive_dir = tempfile.mkdtemp( prefix="tmp-toolshed-arcdir" )
        repositories_archive_filename = os.path.join( tmp_archive_dir, repositories_archive_filename )
    return repositories_archive_filename

def generate_export_elem( tool_shed_url, repository, changeset_revision, export_repository_dependencies, api ):
    sub_elements = odict()
    sub_elements[ 'export_time' ] = strftime( '%a, %d %b %Y %H:%M:%S +0000', gmtime() )
    sub_elements[ 'tool_shed' ] = str( tool_shed_url.rstrip( '/' ) )
    sub_elements[ 'repository_name' ] = str( repository.name )
    sub_elements[ 'repository_owner' ] = str( repository.user.username )
    sub_elements[ 'changeset_revision' ] = str( changeset_revision )
    sub_elements[ 'export_repository_dependencies' ] = str( export_repository_dependencies )
    sub_elements[ 'exported_via_api' ] = str( api )
    return sub_elements

def get_components_from_repo_info_dict( trans, repo_info_dict ):
    """
    Return the repository and the associated latest installable changeset_revision (including updates) for the
    repository defined by the received repo_info_dict.
    """
    for repository_name, repo_info_tup in repo_info_dict.items():
        # There should only be one entry in the received repo_info_dict.
        description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
            suc.get_repo_info_tuple_contents( repo_info_tup )
        repository = suc.get_repository_by_name_and_owner( trans.app, repository_name, repository_owner )
        repository_metadata = suc.get_current_repository_metadata_for_changeset_revision( trans, repository, changeset_revision )
        if repository_metadata:
            return repository, repository_metadata.changeset_revision
    return None, None

def get_repo_info_dict_for_import( encoded_repository_id, encoded_repository_ids, repo_info_dicts ):
    """
    The received encoded_repository_ids and repo_info_dicts are lists that contain associated elements at each
    location in the list.  This method will return the element from repo_info_dicts associated with the received
    encoded_repository_id by determining its location in the received encoded_repository_ids list.
    """
    for index, repository_id in enumerate( encoded_repository_ids ):
        if repository_id == encoded_repository_id:
            repo_info_dict = repo_info_dicts[ index ]
            return repo_info_dict
    return None

def get_repo_info_dicts( trans, tool_shed_url, repository_id, changeset_revision ):
    """
    Return a list of dictionaries defining repositories that are required by the repository associated with the
    received repository_id.
    """
    repository = suc.get_repository_in_tool_shed( trans, repository_id )
    repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, repository_id, changeset_revision )
    # Get a dictionary of all repositories upon which the contents of the current repository_metadata record depend.
    toolshed_base_url = str( web.url_for( '/', qualified=True ) ).rstrip( '/' )
    repository_dependencies = \
        repository_dependency_util.get_repository_dependencies_for_changeset_revision( trans=trans,
                                                                                       repository=repository,
                                                                                       repository_metadata=repository_metadata,
                                                                                       toolshed_base_url=toolshed_base_url,
                                                                                       key_rd_dicts_to_be_processed=None,
                                                                                       all_repository_dependencies=None,
                                                                                       handled_key_rd_dicts=None )
    repo = hg.repository( hg_util.get_configured_ui(), repository.repo_path( trans.app ) )
    ctx = hg_util.get_changectx_for_changeset( repo, changeset_revision )
    repo_info_dict = {}
    # Cast unicode to string.
    repo_info_dict[ str( repository.name ) ] = ( str( repository.description ),
                                                 common_util.generate_clone_url_for_repository_in_tool_shed( trans, repository ),
                                                 str( changeset_revision ),
                                                 str( ctx.rev() ),
                                                 str( repository.user.username ),
                                                 repository_dependencies,
                                                 None )
    all_required_repo_info_dict = common_install_util.get_required_repo_info_dicts( trans, tool_shed_url, [ repo_info_dict ] )
    all_repo_info_dicts = all_required_repo_info_dict.get( 'all_repo_info_dicts', [] )
    return all_repo_info_dicts

def get_repository_attributes_and_sub_elements( repository, archive_name ):
    """
    Get the information about a repository to create and populate an XML tag set.  The generated attributes will
    be contained within the <repository> tag, while the sub_elements will be tag sets contained within the <repository>
    tag set.
    """
    attributes = odict()
    sub_elements = odict()
    attributes[ 'name' ] = str( repository.name )
    attributes[ 'type' ] = str( repository.type )
    # We have to associate the public username since the user_id will be different between tool sheds.
    attributes[ 'username' ] = str( repository.user.username )
    # Don't coerce description or long description from unicode to string because the fields are free text.
    sub_elements[ 'description' ] = repository.description
    sub_elements[ 'long_description' ] = repository.long_description
    sub_elements[ 'archive' ] = archive_name
    # Keep track of Category associations.
    categories = []
    for rca in repository.categories:
        category = rca.category
        categories.append( ( 'category', str( category.name ) ) )
    sub_elements[ 'categories' ] = categories
    return attributes, sub_elements

def get_repository_ids( trans, repo_info_dicts ):
    """Return a list of repository ids associated with each dictionary in the received repo_info_dicts."""
    repository_ids = []
    for repo_info_dict in repo_info_dicts:
        for repository_name, repo_info_tup in repo_info_dict.items():
            description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
                suc.get_repo_info_tuple_contents( repo_info_tup )
            repository = suc.get_repository_by_name_and_owner( trans.app, repository_name, repository_owner )
            repository_ids.append( trans.security.encode_id( repository.id ) )
    return repository_ids

def order_components_for_import( trans, primary_repository_id, repository_ids, repo_info_dicts ):
    """
    Some repositories may have repository dependencies that must be imported and have metadata set on
    them before the dependent repository is imported.  This method will inspect the list of repositories
    about to be exported and make sure to order them appropriately for proper import.  For each repository
    about to be exported, if required repositories are not contained in the list of repositories about to
    be exported, then they are not considered.  Repository dependency definitions that contain circular
    dependencies should not result in an infinite loop, but obviously ordering the list will not be handled
    for one or more of the repositories that require prior import.
    """
    # The received primary_repository_id is the id of the repository being exported, with the received list
    # of repository_ids being only the ids of all of its repository dependencies.  The primary repository will
    # always be last in the returned lists.
    ordered_repository_ids = []
    ordered_repositories = []
    ordered_changeset_revisions = []
    # Create a dictionary whose keys are the received repository_ids and whose values are a list of
    # repository_ids, each of which is contained in the received list of repository_ids and whose associated
    # repository must be imported prior to the repository associated with the repository_id key.
    prior_import_required_dict = suc.get_prior_import_or_install_required_dict( trans, repository_ids, repo_info_dicts )
    processed_repository_ids = []
    # Process the list of repository dependencies defined for the repository associated with the received
    # primary_repository_id.
    while len( processed_repository_ids ) != len( prior_import_required_dict.keys() ):
        repository_id = suc.get_next_prior_import_or_install_required_dict_entry( prior_import_required_dict, processed_repository_ids )
        if repository_id == primary_repository_id:
            # Append the primary_repository_id without processing it since it must be returned last in the order.
            # It will be processed below after all dependencies are processed.
            processed_repository_ids.append( primary_repository_id )
            continue
        processed_repository_ids.append( repository_id )
        if repository_id not in ordered_repository_ids:
            prior_import_required_ids = prior_import_required_dict[ repository_id ]
            for prior_import_required_id in prior_import_required_ids:
                if prior_import_required_id not in ordered_repository_ids:
                    # Import the associated repository dependency first.
                    prior_repo_info_dict = get_repo_info_dict_for_import( prior_import_required_id, repository_ids, repo_info_dicts )
                    prior_repository, prior_import_changeset_revision = get_components_from_repo_info_dict( trans, prior_repo_info_dict )
                    if prior_repository and prior_import_changeset_revision:
                        ordered_repository_ids.append( prior_import_required_id )
                        ordered_repositories.append( prior_repository )
                        ordered_changeset_revisions.append( prior_import_changeset_revision )
            repo_info_dict = get_repo_info_dict_for_import( repository_id, repository_ids, repo_info_dicts )
            repository, changeset_revision = get_components_from_repo_info_dict( trans, repo_info_dict )
            if repository and changeset_revision:
                ordered_repository_ids.append( repository_id )
                ordered_repositories.append( repository )
                ordered_changeset_revisions.append( changeset_revision )
    # Process the repository associated with the received primary_repository_id last.
    repo_info_dict = get_repo_info_dict_for_import( primary_repository_id, repository_ids, repo_info_dicts )
    repository, changeset_revision = get_components_from_repo_info_dict( trans, repo_info_dict )
    if repository and changeset_revision:
        ordered_repository_ids.append( repository_id )
        ordered_repositories.append( repository )
        ordered_changeset_revisions.append( changeset_revision )
    return ordered_repository_ids, ordered_repositories, ordered_changeset_revisions

def remove_protocol_from_tool_shed_url( base_url ):
    protocol, base = base_url.split( '://' )
    base = base.replace( ':', '_colon_' )
    base = base.rstrip( '/' )
    return base
