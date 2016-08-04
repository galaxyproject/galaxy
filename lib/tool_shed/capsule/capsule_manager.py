import contextlib
import logging
import os
import shutil
import tarfile
import tempfile
import threading
from time import gmtime, strftime

from six.moves.urllib.request import urlopen
from sqlalchemy import and_, false

import tool_shed.repository_types.util as rt_util
from galaxy import web
from galaxy.util import asbool, build_url, CHUNK_SIZE, safe_relpath
from galaxy.util.odict import odict
from tool_shed.dependencies import attribute_handlers
from tool_shed.dependencies.repository.relation_builder import RelationBuilder
from tool_shed.galaxy_install.repository_dependencies.repository_dependency_manager import RepositoryDependencyInstallManager
from tool_shed.metadata import repository_metadata_manager
from tool_shed.util import (basic_util, commit_util, common_util, encoding_util,
    hg_util, metadata_util, repository_util, shed_util_common as suc, xml_util)

log = logging.getLogger( __name__ )


class ExportedRepositoryRegistry( object ):

    def __init__( self ):
        self.exported_repository_elems = []


class ExportRepositoryManager( object ):

    def __init__( self, app, user, tool_shed_url, repository, changeset_revision, export_repository_dependencies, using_api ):
        self.app = app
        self.capsule_filename = 'capsule'
        self.capsule_with_dependencies_filename = 'capsule_with_dependencies'
        self.changeset_revision = changeset_revision
        self.export_repository_dependencies = asbool( export_repository_dependencies )
        self.file_type = 'gz'
        self.repository = repository
        self.repository_id = self.app.security.encode_id( repository.id )
        self.tool_shed_url = tool_shed_url
        self.user = user
        self.using_api = using_api

    def export_repository( self ):
        repositories_archive_filename = self.generate_repository_archive_filename( use_tmp_archive_dir=True )
        if self.export_repository_dependencies:
            repo_info_dicts = self.get_repo_info_dicts()
            repository_ids = self.get_repository_ids( repo_info_dicts )
            ordered_repository_ids, ordered_repositories, ordered_changeset_revisions = \
                self.order_components_for_import( repository_ids, repo_info_dicts )
        else:
            ordered_repository_ids = []
            ordered_repositories = []
            ordered_changeset_revisions = []
            if self.repository:
                repository_metadata = \
                    metadata_util.get_current_repository_metadata_for_changeset_revision( self.app,
                                                                                          self.repository,
                                                                                          self.changeset_revision )
                if repository_metadata:
                    ordered_repository_ids = [ self.repository_id ]
                    ordered_repositories = [ self.repository ]
                    ordered_changeset_revisions = [ repository_metadata.changeset_revision ]
        repositories_archive = None
        error_messages = ''
        lock = threading.Lock()
        lock.acquire( True )
        try:
            repositories_archive = tarfile.open( repositories_archive_filename, "w:%s" % self.file_type )
            exported_repository_registry = ExportedRepositoryRegistry()
            for repository_id, ordered_repository, ordered_changeset_revision in zip( ordered_repository_ids,
                                                                                      ordered_repositories,
                                                                                      ordered_changeset_revisions ):
                with self.__tempdir( prefix='tmp-toolshed-export-er' ) as work_dir:
                    repository_archive, error_message = self.generate_repository_archive( ordered_repository,
                                                                                          ordered_changeset_revision,
                                                                                          work_dir )
                    if error_message:
                        error_messages = '%s  %s' % ( error_messages, error_message )
                    else:
                        archive_name = str( os.path.basename( repository_archive.name ) )
                        repositories_archive.add( repository_archive.name, arcname=archive_name )
                        attributes, sub_elements = self.get_repository_attributes_and_sub_elements( ordered_repository,
                                                                                                    archive_name )
                        elem = xml_util.create_element( 'repository', attributes=attributes, sub_elements=sub_elements )
                        exported_repository_registry.exported_repository_elems.append( elem )
            # Keep information about the export in a file named export_info.xml in the archive.
            sub_elements = self.generate_export_elem()
            export_elem = xml_util.create_element( 'export_info', attributes=None, sub_elements=sub_elements )
            tmp_export_info = xml_util.create_and_write_tmp_file( export_elem, use_indent=True )
            repositories_archive.add( tmp_export_info, arcname='export_info.xml' )
            # Write the manifest, which must preserve the order in which the repositories should be imported.
            exported_repository_root = xml_util.create_element( 'repositories' )
            for exported_repository_elem in exported_repository_registry.exported_repository_elems:
                exported_repository_root.append( exported_repository_elem )
            tmp_manifest = xml_util.create_and_write_tmp_file( exported_repository_root, use_indent=True )
            repositories_archive.add( tmp_manifest, arcname='manifest.xml' )
        except Exception as e:
            log.exception( str( e ) )
        finally:
            if os.path.exists( tmp_export_info ):
                os.remove( tmp_export_info )
            if os.path.exists( tmp_manifest ):
                os.remove( tmp_manifest )
            lock.release()
        if repositories_archive is not None:
            repositories_archive.close()
        if self.using_api:
            encoded_repositories_archive_name = encoding_util.tool_shed_encode( repositories_archive_filename )
            params = dict( encoded_repositories_archive_name=encoded_repositories_archive_name )
            pathspec = [ 'repository', 'export_via_api' ]
            tool_shed_url = web.url_for( '/', qualified=True )
            download_url = build_url( tool_shed_url, pathspec=pathspec, params=params )
            return dict( download_url=download_url, error_messages=error_messages )
        return repositories_archive, error_messages

    def generate_export_elem( self ):
        sub_elements = odict()
        sub_elements[ 'export_time' ] = strftime( '%a, %d %b %Y %H:%M:%S +0000', gmtime() )
        sub_elements[ 'tool_shed' ] = str( self.tool_shed_url.rstrip( '/' ) )
        sub_elements[ 'repository_name' ] = str( self.repository.name )
        sub_elements[ 'repository_owner' ] = str( self.repository.user.username )
        sub_elements[ 'changeset_revision' ] = str( self.changeset_revision )
        sub_elements[ 'export_repository_dependencies' ] = str( self.export_repository_dependencies )
        sub_elements[ 'exported_via_api' ] = str( self.using_api )
        return sub_elements

    def generate_repository_archive( self, repository, changeset_revision, work_dir ):
        rdah = attribute_handlers.RepositoryDependencyAttributeHandler( self.app, unpopulate=True )
        tdah = attribute_handlers.ToolDependencyAttributeHandler( self.app, unpopulate=True )
        file_type_str = basic_util.get_file_type_str( changeset_revision, self.file_type )
        file_name = '%s-%s' % ( repository.name, file_type_str )
        return_code, error_message = hg_util.archive_repository_revision( self.app,
                                                                          repository,
                                                                          work_dir,
                                                                          changeset_revision )
        if return_code:
            return None, error_message
        repository_archive_name = os.path.join( work_dir, file_name )
        # Create a compressed tar archive that will contain only valid files and possibly altered dependency definition files.
        repository_archive = tarfile.open( repository_archive_name, "w:%s" % self.file_type )
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
                    if name == rt_util.REPOSITORY_DEPENDENCY_DEFINITION_FILENAME:
                        # Eliminate the toolshed, and changeset_revision attributes from all <repository> tags.
                        altered, root_elem, error_message = rdah.handle_tag_attributes( full_path )
                        if error_message:
                            return None, error_message
                        if altered:
                            tmp_filename = xml_util.create_and_write_tmp_file( root_elem, use_indent=True )
                            shutil.move( tmp_filename, full_path )
                    elif name == rt_util.TOOL_DEPENDENCY_DEFINITION_FILENAME:
                        # Eliminate the toolshed, and changeset_revision attributes from all <repository> tags.
                        altered, root_elem, error_message = tdah.handle_tag_attributes( full_path )
                        if error_message:
                            return None, error_message
                        if altered:
                            tmp_filename = xml_util.create_and_write_tmp_file( root_elem, use_indent=True )
                            shutil.move( tmp_filename, full_path )
                    repository_archive.add( full_path, arcname=relative_path )
        repository_archive.close()
        return repository_archive, error_message

    def generate_repository_archive_filename( self, use_tmp_archive_dir=False ):
        tool_shed = self.remove_protocol_from_tool_shed_url()
        file_type_str = basic_util.get_file_type_str( self.changeset_revision, self.file_type )
        if self.export_repository_dependencies:
            repositories_archive_filename = '%s_%s_%s_%s_%s' % ( self.capsule_with_dependencies_filename,
                                                                 tool_shed,
                                                                 str( self.repository.name ),
                                                                 str( self.repository.user.username ),
                                                                 file_type_str )
        else:
            repositories_archive_filename = '%s_%s_%s_%s_%s' % ( self.capsule_filename,
                                                                 tool_shed,
                                                                 str( self.repository.name ),
                                                                 str( self.repository.user.username ),
                                                                 file_type_str )
        if use_tmp_archive_dir:
            tmp_archive_dir = tempfile.mkdtemp( prefix="tmp-toolshed-arcdir" )
            repositories_archive_filename = os.path.join( tmp_archive_dir, repositories_archive_filename )
        return repositories_archive_filename

    def get_components_from_repo_info_dict( self, repo_info_dict ):
        """
        Return the repository and the associated latest installable changeset_revision (including
        # updates) for the repository defined by the received repo_info_dict.
        """
        for repository_name, repo_info_tup in repo_info_dict.items():
            # There should only be one entry in the received repo_info_dict.
            description, repository_clone_url, changeset_revision, ctx_rev, \
                repository_owner, repository_dependencies, tool_dependencies = \
                repository_util.get_repo_info_tuple_contents( repo_info_tup )
            repository = repository_util.get_repository_by_name_and_owner( self.app, repository_name, repository_owner )
            repository_metadata = metadata_util.get_current_repository_metadata_for_changeset_revision( self.app,
                                                                                                        repository,
                                                                                                        changeset_revision )
            if repository_metadata:
                return repository, repository_metadata.changeset_revision
        return None, None

    def get_repo_info_dict_for_import( self, encoded_repository_id, encoded_repository_ids, repo_info_dicts ):
        """
        The received encoded_repository_ids and repo_info_dicts are lists that contain associated
        elements at each location in the list.  This method will return the element from repo_info_dicts
        associated with the received encoded_repository_id by determining its location in the received
        encoded_repository_ids list.
        """
        for index, repository_id in enumerate( encoded_repository_ids ):
            if repository_id == encoded_repository_id:
                repo_info_dict = repo_info_dicts[ index ]
                return repo_info_dict
        return None

    def get_repo_info_dicts( self ):
        """
        Return a list of dictionaries defining repositories that are required by the repository
        associated with self.repository_id.
        """
        rdim = RepositoryDependencyInstallManager( self.app )
        repository = repository_util.get_repository_in_tool_shed( self.app, self.repository_id )
        repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision( self.app,
                                                                                           self.repository_id,
                                                                                           self.changeset_revision )
        # Get a dictionary of all repositories upon which the contents of the current
        # repository_metadata record depend.
        toolshed_base_url = str( web.url_for( '/', qualified=True ) ).rstrip( '/' )
        rb = RelationBuilder( self.app, repository, repository_metadata, toolshed_base_url )
        # Work-around to ensure repositories that contain packages needed only for compiling
        # a dependent package are included in the capsule.
        rb.set_filter_dependencies_needed_for_compiling( False )
        repository_dependencies = rb.get_repository_dependencies_for_changeset_revision()
        repo = hg_util.get_repo_for_repository( self.app,
                                                repository=self.repository,
                                                repo_path=None,
                                                create=False )
        ctx = hg_util.get_changectx_for_changeset( repo, self.changeset_revision )
        repo_info_dict = {}
        # Cast unicode to string.
        repo_info_dict[ str( repository.name ) ] = ( str( self.repository.description ),
                                                     common_util.generate_clone_url_for_repository_in_tool_shed( self.user,
                                                                                                                 self.repository ),
                                                     str( self.changeset_revision ),
                                                     str( ctx.rev() ),
                                                     str( self.repository.user.username ),
                                                     repository_dependencies,
                                                     None )
        all_required_repo_info_dict = rdim.get_required_repo_info_dicts( self.tool_shed_url, [ repo_info_dict ] )
        all_repo_info_dicts = all_required_repo_info_dict.get( 'all_repo_info_dicts', [] )
        return all_repo_info_dicts

    def get_repository_attributes_and_sub_elements( self, repository, archive_name ):
        """
        Get the information about a repository to create and populate an XML tag set.  The
        generated attributes will be contained within the <repository> tag, while the sub_elements
        will be tag sets contained within the <repository> tag set.
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

    def get_repository_ids( self, repo_info_dicts ):
        """Return a list of repository ids associated with each dictionary in the received repo_info_dicts."""
        repository_ids = []
        for repo_info_dict in repo_info_dicts:
            for repository_name, repo_info_tup in repo_info_dict.items():
                description, repository_clone_url, changeset_revision, \
                    ctx_rev, repository_owner, repository_dependencies, \
                    tool_dependencies = \
                    repository_util.get_repo_info_tuple_contents( repo_info_tup )
                repository = repository_util.get_repository_by_name_and_owner( self.app, repository_name, repository_owner )
                repository_ids.append( self.app.security.encode_id( repository.id ) )
        return repository_ids

    def order_components_for_import( self, repository_ids, repo_info_dicts ):
        """
        Some repositories may have repository dependencies that must be imported and have metadata set on
        them before the dependent repository is imported.  This method will inspect the list of repositories
        about to be exported and make sure to order them appropriately for proper import.  For each repository
        about to be exported, if required repositories are not contained in the list of repositories about to
        be exported, then they are not considered.  Repository dependency definitions that contain circular
        dependencies should not result in an infinite loop, but obviously ordering the list will not be handled
        for one or more of the repositories that require prior import.
        """
        # The received list of repository_ids are the ids of all of the primary exported repository's
        # repository dependencies.  The primary repository will always be last in the returned lists.
        ordered_repository_ids = []
        ordered_repositories = []
        ordered_changeset_revisions = []
        # Create a dictionary whose keys are the received repository_ids and whose values are a list of
        # repository_ids, each of which is contained in the received list of repository_ids and whose associated
        # repository must be imported prior to the repository associated with the repository_id key.
        prior_import_required_dict = repository_util.get_prior_import_or_install_required_dict( self.app,
                                                                                                repository_ids,
                                                                                                repo_info_dicts )
        processed_repository_ids = []
        # Process the list of repository dependencies defined for the primary exported repository.
        while len( processed_repository_ids ) != len( prior_import_required_dict.keys() ):
            repository_id = suc.get_next_prior_import_or_install_required_dict_entry( prior_import_required_dict,
                                                                                      processed_repository_ids )
            if repository_id == self.repository_id:
                # Append self.repository_id without processing it since it must be returned last in the order.
                # It will be processed below after all dependencies are processed.
                processed_repository_ids.append( self.repository_id )
                continue
            processed_repository_ids.append( repository_id )
            if repository_id not in ordered_repository_ids:
                prior_import_required_ids = prior_import_required_dict[ repository_id ]
                for prior_import_required_id in prior_import_required_ids:
                    if prior_import_required_id not in ordered_repository_ids:
                        # Import the associated repository dependency first.
                        prior_repo_info_dict = \
                            self.get_repo_info_dict_for_import( prior_import_required_id,
                                                                repository_ids,
                                                                repo_info_dicts )
                        prior_repository, prior_import_changeset_revision = \
                            self.get_components_from_repo_info_dict( prior_repo_info_dict )
                        if prior_repository and prior_import_changeset_revision:
                            ordered_repository_ids.append( prior_import_required_id )
                            ordered_repositories.append( prior_repository )
                            ordered_changeset_revisions.append( prior_import_changeset_revision )
                repo_info_dict = self.get_repo_info_dict_for_import( repository_id, repository_ids, repo_info_dicts )
                repository, changeset_revision = self.get_components_from_repo_info_dict( repo_info_dict )
                if repository and changeset_revision:
                    ordered_repository_ids.append( repository_id )
                    ordered_repositories.append( repository )
                    ordered_changeset_revisions.append( changeset_revision )
        # Process the repository associated with self.repository_id last.
        repo_info_dict = self.get_repo_info_dict_for_import( self.repository_id, repository_ids, repo_info_dicts )
        repository, changeset_revision = self.get_components_from_repo_info_dict( repo_info_dict )
        if repository and changeset_revision:
            ordered_repository_ids.append( repository_id )
            ordered_repositories.append( repository )
            ordered_changeset_revisions.append( changeset_revision )
        return ordered_repository_ids, ordered_repositories, ordered_changeset_revisions

    def remove_protocol_from_tool_shed_url( self ):
        protocol, base = self.tool_shed_url.split( '://' )
        base = base.replace( ':', '_colon_' )
        base = base.rstrip( '/' )
        return base

    @contextlib.contextmanager
    def __tempdir( self, prefix=None ):
        td = tempfile.mkdtemp( prefix=prefix )
        try:
            yield td
        finally:
            shutil.rmtree( td )


class ImportRepositoryManager( object ):

    def __init__( self, app, host, user, user_is_admin ):
        self.app = app
        self.host = host
        self.user = user
        self.user_is_admin = user_is_admin

    def check_status_and_reset_downloadable( self, import_results_tups ):
        """Check the status of each imported repository and set downloadable to False if errors."""
        sa_session = self.app.model.context.current
        flush = False
        for import_results_tup in import_results_tups:
            ok, name_owner, message = import_results_tup
            name, owner = name_owner
            if not ok:
                repository = repository_util.get_repository_by_name_and_owner( self.app, name, owner )
                if repository is not None:
                    # Do not allow the repository to be automatically installed if population resulted in errors.
                    tip_changeset_revision = repository.tip( self.app )
                    repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision( self.app,
                                                                                                       self.app.security.encode_id( repository.id ),
                                                                                                       tip_changeset_revision )
                    if repository_metadata:
                        if repository_metadata.downloadable:
                            repository_metadata.downloadable = False
                            sa_session.add( repository_metadata )
                            if not flush:
                                flush = True
                        # Do not allow dependent repository revisions to be automatically installed if population
                        # resulted in errors.
                        dependent_downloadable_revisions = self.get_dependent_downloadable_revisions( repository_metadata )
                        for dependent_downloadable_revision in dependent_downloadable_revisions:
                            if dependent_downloadable_revision.downloadable:
                                dependent_downloadable_revision.downloadable = False
                                sa_session.add( dependent_downloadable_revision )
                                if not flush:
                                    flush = True
        if flush:
            sa_session.flush()

    def create_repository_and_import_archive( self, repository_archive_dict, import_results_tups ):
        """
        Create a new repository in the tool shed and populate it with the contents of a gzip compressed
        tar archive that was exported as part or all of the contents of a capsule.
        """
        results_message = ''
        name = repository_archive_dict.get( 'name', None )
        username = repository_archive_dict.get( 'owner', None )
        if name is None or username is None:
            ok = False
            results_message += 'Import failed: required repository name <b>%s</b> or owner <b>%s</b> is missing.' % \
                ( str( name ), str( username ))
            import_results_tups.append( ( ok, ( str( name ), str( username ) ), results_message ) )
        else:
            status = repository_archive_dict.get( 'status', None )
            if status is None:
                # The repository does not yet exist in this Tool Shed and the current user is authorized to import
                # the current archive file.
                type = repository_archive_dict.get( 'type', 'unrestricted' )
                description = repository_archive_dict.get( 'description', '' )
                long_description = repository_archive_dict.get( 'long_description', '' )
                # The owner entry in the repository_archive_dict is the public username of the user associated with
                # the exported repository archive.
                user = common_util.get_user_by_username( self.app, username )
                if user is None:
                    ok = False
                    results_message += 'Import failed: repository owner <b>%s</b> does not have an account in this Tool Shed.' % \
                        str( username )
                    import_results_tups.append( ( ok, ( str( name ), str( username ) ), results_message ) )
                else:
                    user_id = user.id
                    # The categories entry in the repository_archive_dict is a list of category names.  If a name does not
                    # exist in the current Tool Shed, the category will not be created, so it will not be associated with
                    # the repository.
                    category_ids = []
                    category_names = repository_archive_dict.get( 'category_names', [] )
                    for category_name in category_names:
                        category = suc.get_category_by_name( self.app, category_name )
                        if category is None:
                            results_message += 'This Tool Shed does not have the category <b>%s</b> so it ' % str( category_name )
                            results_message += 'will not be associated with this repository.'
                        else:
                            category_ids.append( self.app.security.encode_id( category.id ) )
                    # Create the repository record in the database.
                    repository, create_message = repository_util.create_repository( self.app,
                                                                                    name,
                                                                                    type,
                                                                                    description,
                                                                                    long_description,
                                                                                    user_id=user_id,
                                                                                    category_ids=category_ids )
                    if create_message:
                        results_message += create_message
                    # Populate the new repository with the contents of exported repository archive.
                    results_dict = self.import_repository_archive( repository, repository_archive_dict )
                    ok = results_dict.get( 'ok', False )
                    error_message = results_dict.get( 'error_message', '' )
                    if error_message:
                        results_message += error_message
                    import_results_tups.append( ( ok, ( str( name ), str( username ) ), results_message ) )
            else:
                # The repository either already exists in this Tool Shed or the current user is not authorized to create it.
                ok = True
                results_message += 'Import not necessary: repository status for this Tool Shed is: %s.' % str( status )
                import_results_tups.append( ( ok, ( str( name ), str( username ) ), results_message ) )
        return import_results_tups

    def extract_capsule_files( self, **kwd ):
        """
        Extract the uploaded capsule archive into a temporary location for inspection, validation
        and potential import.
        """
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
            except Exception as e:
                log.exception( "Cannot close tar_archive: %s" % str( e ) )
            del return_dict[ 'tar_archive' ]
        return return_dict

    def get_archives_from_manifest( self, manifest_file_path ):
        """
        Return the list of archive names defined in the capsule manifest.  This method will validate
        the manifest by ensuring all <repository> tag sets contain a valid <archive> sub-element.
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

    def get_dependent_downloadable_revisions( self, repository_metadata ):
        """
        Return all repository_metadata records that are downloadable and that depend upon the received
        repository_metadata record.
        """
        # This method is called only from the tool shed.
        sa_session = self.app.model.context.current
        rm_changeset_revision = repository_metadata.changeset_revision
        rm_repository = repository_metadata.repository
        rm_repository_name = str( rm_repository.name )
        rm_repository_owner = str( rm_repository.user.username )
        dependent_downloadable_revisions = []
        for repository in sa_session.query( self.app.model.Repository ) \
                                    .filter( and_( self.app.model.Repository.table.c.id != rm_repository.id,
                                                   self.app.model.Repository.table.c.deleted == false(),
                                                   self.app.model.Repository.table.c.deprecated == false() ) ):
            downloadable_revisions = repository.downloadable_revisions
            if downloadable_revisions:
                for downloadable_revision in downloadable_revisions:
                    if downloadable_revision.has_repository_dependencies:
                        metadata = downloadable_revision.metadata
                        if metadata:
                            repository_dependencies_dict = metadata.get( 'repository_dependencies', {} )
                            repository_dependencies_tups = repository_dependencies_dict.get( 'repository_dependencies', [] )
                            for repository_dependencies_tup in repository_dependencies_tups:
                                tool_shed, name, owner, changeset_revision, \
                                    prior_installation_required, \
                                    only_if_compiling_contained_td = \
                                    common_util.parse_repository_dependency_tuple( repository_dependencies_tup )
                                if name == rm_repository_name and owner == rm_repository_owner:
                                    # We've discovered a repository revision that depends upon the repository associated
                                    # with the received repository_metadata record, but we need to make sure it depends
                                    # upon the revision.
                                    if changeset_revision == rm_changeset_revision:
                                        dependent_downloadable_revisions.append( downloadable_revision )
                                    else:
                                        # Make sure the defined changeset_revision is current.
                                        defined_repository_metadata = \
                                            sa_session.query( self.app.model.RepositoryMetadata ) \
                                                      .filter( self.app.model.RepositoryMetadata.table.c.changeset_revision == changeset_revision ) \
                                                      .first()
                                        if defined_repository_metadata is None:
                                            # The defined changeset_revision is not associated with a repository_metadata
                                            # record, so updates must be necessary.
                                            defined_repository = repository_util.get_repository_by_name_and_owner( self.app, name, owner )
                                            defined_repo = hg_util.get_repo_for_repository( self.app,
                                                                                            repository=defined_repository,
                                                                                            repo_path=None,
                                                                                            create=False )
                                            updated_changeset_revision = \
                                                metadata_util.get_next_downloadable_changeset_revision( defined_repository,
                                                                                                        defined_repo,
                                                                                                        changeset_revision )
                                            if updated_changeset_revision == rm_changeset_revision and updated_changeset_revision != changeset_revision:
                                                dependent_downloadable_revisions.append( downloadable_revision )
        return dependent_downloadable_revisions

    def get_export_info_dict( self, export_info_file_path ):
        """
        Parse the export_info.xml file contained within the capsule and return a dictionary
        containing its entries.
        """
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
                if asbool( elem.text ):
                    export_info_dict[ 'export_repository_dependencies' ] = 'Yes'
                else:
                    export_info_dict[ 'export_repository_dependencies' ] = 'No'
        return export_info_dict

    def get_repository_info_from_manifest( self, manifest_file_path ):
        """
        Parse the capsule manifest and return a list of dictionaries containing information about
        each exported repository archive contained within the capsule.
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
                    repository_info_dict[ 'changeset_revision' ] = changeset_revision
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

    def get_repository_status_from_tool_shed( self, repository_info_dicts ):
        """
        For each exported repository archive contained in the capsule, inspect the Tool Shed to
        see if that repository already exists or if the current user is authorized to create the
        repository and set a status appropriately.  If repository dependencies are included in the
        capsule, repositories may have various owners.  We will keep repositories associated with
        owners, so we need to restrict created repositories to those the current user can create.
        If the current user is an admin or a member of the IUC, all repositories will be created
        no matter the owner.  Otherwise only repositories whose associated owner is the current
        user will be created.
        """
        repository_status_info_dicts = []
        for repository_info_dict in repository_info_dicts:
            repository = repository_util.get_repository_by_name_and_owner( self.app,
                                                                           repository_info_dict[ 'name' ],
                                                                           repository_info_dict[ 'owner' ] )
            if repository:
                if repository.deleted:
                    repository_info_dict[ 'status' ] = 'Exists, deleted'
                elif repository.deprecated:
                    repository_info_dict[ 'status' ] = 'Exists, deprecated'
                else:
                    repository_info_dict[ 'status' ] = 'Exists'
            else:
                # No repository with the specified name and owner currently exists, so make sure
                # the current user can create one.
                if self.user_is_admin:
                    repository_info_dict[ 'status' ] = None
                elif self.app.security_agent.user_can_import_repository_archive( self.user,
                                                                                 repository_info_dict[ 'owner' ] ):
                    repository_info_dict[ 'status' ] = None
                else:
                    repository_info_dict[ 'status' ] = 'Not authorized to import'
            repository_status_info_dicts.append( repository_info_dict )
        return repository_status_info_dicts

    def import_repository_archive( self, repository, repository_archive_dict ):
        """Import a repository archive contained within a repository capsule."""
        rdah = attribute_handlers.RepositoryDependencyAttributeHandler( self.app, unpopulate=False )
        tdah = attribute_handlers.ToolDependencyAttributeHandler( self.app, unpopulate=False )
        archive_file_name = repository_archive_dict.get( 'archive_file_name', None )
        capsule_file_name = repository_archive_dict[ 'capsule_file_name' ]
        encoded_file_path = repository_archive_dict[ 'encoded_file_path' ]
        file_path = encoding_util.tool_shed_decode( encoded_file_path )
        results_dict = dict( ok=True, error_message='' )
        archive_file_path = os.path.join( file_path, archive_file_name )
        archive = tarfile.open( archive_file_path, 'r:*' )
        repo_dir = repository.repo_path( self.app )
        hg_util.get_repo_for_repository( self.app, repository=None, repo_path=repo_dir, create=False )
        undesirable_dirs_removed = 0
        undesirable_files_removed = 0
        check_results = commit_util.check_archive( repository, archive )
        # We filter out undesirable files but fail on undesriable dirs. Not
        # sure why, just trying to maintain the same behavior as before. -nate
        if not check_results.invalid and not check_results.undesirable_dirs:
            full_path = os.path.abspath( repo_dir )
            # Extract the uploaded archive to the repository root.
            archive.extractall( path=full_path, members=check_results.valid )
            archive.close()
            for tar_member in check_results.valid:
                filename = tar_member.name
                uploaded_file_name = os.path.join( full_path, filename )
                if os.path.split( uploaded_file_name )[ -1 ] == rt_util.REPOSITORY_DEPENDENCY_DEFINITION_FILENAME:
                    # Inspect the contents of the file to see if toolshed or changeset_revision attributes
                    # are missing and if so, set them appropriately.
                    altered, root_elem, error_message = rdah.handle_tag_attributes( uploaded_file_name )
                    if error_message:
                        results_dict[ 'ok' ] = False
                        results_dict[ 'error_message' ] += error_message
                    if altered:
                        tmp_filename = xml_util.create_and_write_tmp_file( root_elem )
                        shutil.move( tmp_filename, uploaded_file_name )
                elif os.path.split( uploaded_file_name )[ -1 ] == rt_util.TOOL_DEPENDENCY_DEFINITION_FILENAME:
                    # Inspect the contents of the file to see if toolshed or changeset_revision
                    # attributes are missing and if so, set them appropriately.
                    altered, root_elem, error_message = tdah.handle_tag_attributes( uploaded_file_name )
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
            filenames_in_archive = [ member.name for member in check_results.valid ]
            undesirable_files_removed = len( check_results.undesirable_files )
            undesirable_dirs_removed = 0
            ok, error_message, files_to_remove, content_alert_str, undesirable_dirs_removed, undesirable_files_removed = \
                commit_util.handle_directory_changes( self.app,
                                                      self.host,
                                                      self.user.username,
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
                rmm = repository_metadata_manager.RepositoryMetadataManager( app=self.app,
                                                                             user=self.user,
                                                                             repository=repository )
                status, error_message = rmm.set_repository_metadata_due_to_new_tip( self.host,
                                                                                    content_alert_str=content_alert_str )
                if error_message:
                    results_dict[ 'ok' ] = False
                    results_dict[ 'error_message' ] += error_message
            except Exception as e:
                log.debug( "Error setting metadata on repository %s created from imported archive %s: %s" %
                    ( str( repository.name ), str( archive_file_name ), str( e ) ) )
        else:
            archive.close()
            results_dict[ 'ok' ] = False
            results_dict[ 'error_message' ] += 'Capsule errors were found: '
            if check_results.invalid:
                results_dict[ 'error_message' ] += '%s Invalid files were: %s.' % (
                    ' '.join( check_results.errors ), ', '.join( check_results.invalid ) )
            if check_results.undesirable_dirs:
                results_dict[ 'error_message' ] += ' Undesirable directories were: %s.' % (
                    ', '.join( check_results.undesirable_dirs ) )
        return results_dict

    def upload_capsule( self, **kwd ):
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
        if url:
            valid_url = True
            try:
                stream = urlopen( url )
            except Exception as e:
                valid_url = False
                return_dict['error_message'] = 'Error importing file via http: %s' % str( e )
                return_dict['status'] = 'error'
                return return_dict
            if valid_url:
                fd, uploaded_file_name = tempfile.mkstemp()
                uploaded_file = open( uploaded_file_name, 'wb' )
                while 1:
                    chunk = stream.read( CHUNK_SIZE )
                    if not chunk:
                        break
                    uploaded_file.write( chunk )
                uploaded_file.flush()
                uploaded_file_filename = url.split( '/' )[ -1 ]
        elif file_data not in ( '', None ):
            uploaded_file = file_data.file
            uploaded_file_name = uploaded_file.name
            uploaded_file_filename = os.path.split( file_data.filename )[ -1 ]
        if uploaded_file is not None:
            if os.path.getsize( os.path.abspath( uploaded_file_name ) ) == 0:
                uploaded_file.close()
                return_dict[ 'error_message' ] = 'Your uploaded capsule file is empty.'
                return_dict[ 'status' ] = 'error'
                return return_dict
            try:
                # Open for reading with transparent compression.
                tar_archive = tarfile.open( uploaded_file_name, 'r:*' )
            except tarfile.ReadError as e:
                error_message = 'Error opening file %s: %s' % ( str( uploaded_file_name ), str( e ) )
                log.exception( error_message )
                return_dict[ 'error_message' ] = error_message
                return_dict[ 'status' ] = 'error'
                uploaded_file.close()
                return return_dict
            if not self.validate_archive_paths( tar_archive ):
                return_dict[ 'status' ] = 'error'
                return_dict[ 'message' ] = ( 'This capsule contains an invalid member type '
                    'or a file outside the archive path.' )
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

    def validate_archive_paths( self, tar_archive ):
        '''
        Inspect the archive contents to ensure that there are no risky symlinks.
        Returns True if a suspicious path is found.
        '''
        for member in tar_archive.getmembers():
            if not ( member.isdir() or member.isfile() or member.islnk() ):
                return False
            elif not safe_relpath( member.name ):
                return False
        return True

    def validate_capsule( self, **kwd ):
        """
        Inspect the uploaded capsule's manifest and its contained files to ensure it is a valid
        repository capsule.
        """
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
        # Validate the capsule manifest by inspecting name, owner, changeset_revision and type
        # information contained within each <repository> tag set.
        repository_info_dicts, error_message = self.get_repository_info_from_manifest( manifest_file_path )
        if error_message:
            capsule_dict[ 'error_message' ] = error_message
            capsule_dict[ 'status' ] = 'error'
            return capsule_dict
        # Validate the capsule manifest by ensuring all <repository> tag sets contain a valid
        # <archive> sub-element.
        archives, error_message = self.get_archives_from_manifest( manifest_file_path )
        if error_message:
            capsule_dict[ 'error_message' ] = error_message
            capsule_dict[ 'status' ] = 'error'
            return capsule_dict
        # Validate the capsule manifest by ensuring each defined archive file name exists within
        # the capsule.
        error_message = self.verify_archives_in_capsule( file_path, archives )
        if error_message:
            capsule_dict[ 'error_message' ] = error_message
            capsule_dict[ 'status' ] = 'error'
            return capsule_dict
        capsule_dict[ 'status' ] = 'ok'
        return capsule_dict

    def verify_archives_in_capsule( self, file_path, archives ):
        """
        Inspect the files contained within the capsule and make sure each is defined correctly
        in the capsule manifest.
        """
        error_message = ''
        for archive_file_name in archives:
            full_path = os.path.join( file_path, archive_file_name )
            if not os.path.exists( full_path ):
                error_message = 'The uploaded capsule is invalid because the contained manifest.xml '
                error_message += 'file defines an archive file named <b>%s</b> which ' % str( archive_file_name )
                error_message += 'is not contained within the capsule.'
                break
        return error_message
