import os, shutil, tempfile, logging
from galaxy import util
from galaxy.tools import parameters
from galaxy.util import inflector
from galaxy.web import url_for
from galaxy.web.form_builder import SelectField
from galaxy.datatypes.checkers import *
from galaxy.model.orm import *

from galaxy import eggs
import pkg_resources

pkg_resources.require( 'mercurial' )
from mercurial import hg, ui, commands

log = logging.getLogger( __name__ )

INITIAL_CHANGELOG_HASH = '000000000000'
# Characters that must be html escaped
MAPPED_CHARS = { '>' :'&gt;', 
                 '<' :'&lt;',
                 '"' : '&quot;',
                 '&' : '&amp;',
                 '\'' : '&apos;' }
MAX_CONTENT_SIZE = 32768
NOT_TOOL_CONFIGS = [ 'datatypes_conf.xml', 'tool_dependencies.xml' ]
GALAXY_ADMIN_TOOL_SHED_CONTROLLER = 'GALAXY_ADMIN_TOOL_SHED_CONTROLLER'
TOOL_SHED_ADMIN_CONTROLLER = 'TOOL_SHED_ADMIN_CONTROLLER'
VALID_CHARS = set( string.letters + string.digits + "'\"-=_.()/+*^,:?!#[]%\\$@;{}" )

def build_repository_ids_select_field( trans, cntrller, name='repository_ids', multiple=True, display='checkboxes' ):
    """Method called from both Galaxy and the Tool Shed to generate the current list of repositories for resetting metadata."""
    repositories_select_field = SelectField( name=name, multiple=multiple, display=display )
    if cntrller == TOOL_SHED_ADMIN_CONTROLLER:
        for repository in trans.sa_session.query( trans.model.Repository ) \
                                          .filter( trans.model.Repository.table.c.deleted == False ) \
                                          .order_by( trans.model.Repository.table.c.name,
                                                     trans.model.Repository.table.c.user_id ):
            owner = repository.user.username
            option_label = '%s (%s)' % ( repository.name, owner )
            option_value = '%s' % trans.security.encode_id( repository.id )
            repositories_select_field.add_option( option_label, option_value )
    elif cntrller == GALAXY_ADMIN_TOOL_SHED_CONTROLLER:
        for repository in trans.sa_session.query( trans.model.ToolShedRepository ) \
                                          .filter( trans.model.ToolShedRepository.table.c.uninstalled == False ) \
                                          .order_by( trans.model.ToolShedRepository.table.c.name,
                                                     trans.model.ToolShedRepository.table.c.owner ):
            option_label = '%s (%s)' % ( repository.name, repository.owner )
            option_value = trans.security.encode_id( repository.id )
            repositories_select_field.add_option( option_label, option_value )
    return repositories_select_field
def check_tool_input_params( app, repo_dir, tool_config_name, tool, sample_files ):
    """
    Check all of the tool's input parameters, looking for any that are dynamically generated using external data files to make 
    sure the files exist.
    """
    invalid_files_and_errors_tups = []
    correction_msg = ''
    for input_param in tool.input_params:
        if isinstance( input_param, parameters.basic.SelectToolParameter ) and input_param.is_dynamic:
            # If the tool refers to .loc files or requires an entry in the tool_data_table_conf.xml, make sure all requirements exist.
            options = input_param.dynamic_options or input_param.options
            if options:
                if options.tool_data_table or options.missing_tool_data_table_name:
                    # Make sure the repository contains a tool_data_table_conf.xml.sample file.
                    sample_tool_data_table_conf = get_config_from_disk( 'tool_data_table_conf.xml.sample', repo_dir )
                    if sample_tool_data_table_conf:
                        error, correction_msg = handle_sample_tool_data_table_conf_file( app, sample_tool_data_table_conf )
                        if error:
                            invalid_files_and_errors_tups.append( ( 'tool_data_table_conf.xml.sample', correction_msg ) )
                        else:
                            options.missing_tool_data_table_name = None
                    else:
                        correction_msg = "This file requires an entry in the tool_data_table_conf.xml file.  Upload a file named tool_data_table_conf.xml.sample "
                        correction_msg += "to the repository that includes the required entry to correct this error.<br/>"
                        invalid_files_and_errors_tups.append( ( tool_config_name, correction_msg ) )
                if options.index_file or options.missing_index_file:
                    # Make sure the repository contains the required xxx.loc.sample file.
                    index_file = options.index_file or options.missing_index_file
                    index_file_name = strip_path( index_file )
                    sample_found = False
                    for sample_file in sample_files:
                        sample_file_name = strip_path( sample_file )
                        if sample_file_name == '%s.sample' % index_file_name:
                            options.index_file = index_file_name
                            options.missing_index_file = None
                            if options.tool_data_table:
                                options.tool_data_table.missing_index_file = None
                            sample_found = True
                            break
                    if not sample_found:
                        correction_msg = "This file refers to a file named <b>%s</b>.  " % str( index_file )
                        correction_msg += "Upload a file named <b>%s.sample</b> to the repository to correct this error." % str( index_file_name )
                        invalid_files_and_errors_tups.append( ( tool_config_name, correction_msg ) )
    return invalid_files_and_errors_tups
def clone_repository( repository_clone_url, repository_file_dir, ctx_rev ):   
    """Clone the repository up to the specified changeset_revision.  No subsequent revisions will be present in the cloned repository."""
    try:
        commands.clone( get_configured_ui(),
                        str( repository_clone_url ),
                        dest=str( repository_file_dir ),
                        pull=True,
                        noupdate=False,
                        rev=util.listify( str( ctx_rev ) ) )
        return True, None
    except Exception, e:
        error_message = 'Error cloning repository: %s' % str( e )
        log.debug( error_message )
        return False, error_message
def concat_messages( msg1, msg2 ):
    if msg1:
        if msg2:
            message = '%s  %s' % ( msg1, msg2 )
        else:
            message = msg1
    elif msg2:
        message = msg2
    else:
        message = ''
    return message
def copy_sample_file( app, filename, dest_path=None ):
    """Copy xxx.sample to dest_path/xxx.sample and dest_path/xxx.  The default value for dest_path is ~/tool-data."""
    if dest_path is None:
        dest_path = os.path.abspath( app.config.tool_data_path )
    sample_file_name = strip_path( filename )
    copied_file = sample_file_name.replace( '.sample', '' )
    full_source_path = os.path.abspath( filename )
    full_destination_path = os.path.join( dest_path, sample_file_name )
    # Don't copy a file to itself - not sure how this happens, but sometimes it does...
    if full_source_path != full_destination_path:
        # It's ok to overwrite the .sample version of the file.
        shutil.copy( full_source_path, full_destination_path )
    # Only create the .loc file if it does not yet exist.  We don't overwrite it in case it contains stuff proprietary to the local instance.
    if not os.path.exists( os.path.join( dest_path, copied_file ) ):
        shutil.copy( full_source_path, os.path.join( dest_path, copied_file ) )
def create_or_update_repository_metadata( trans, id, repository, changeset_revision, metadata_dict ):
    downloadable = is_downloadable( metadata_dict )
    repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
    if repository_metadata:
        repository_metadata.metadata = metadata_dict
        repository_metadata.downloadable = downloadable
    else:
        repository_metadata = trans.model.RepositoryMetadata( repository_id=repository.id,
                                                              changeset_revision=changeset_revision,
                                                              metadata=metadata_dict,
                                                              downloadable=downloadable )
    trans.sa_session.add( repository_metadata )
    trans.sa_session.flush()
    return repository_metadata
def create_repo_info_dict( repository, owner, repository_clone_url, changeset_revision, ctx_rev, metadata ):
    repo_info_dict = {}
    repo_info_dict[ repository.name ] = ( repository.description,
                                          repository_clone_url,
                                          changeset_revision,
                                          ctx_rev,
                                          owner,
                                          metadata.get( 'tool_dependencies', None ) )
    return repo_info_dict
def generate_clone_url_for_repository_in_tool_shed( trans, repository ):
    """Generate the URL for cloning a repository that is in the tool shed."""
    base_url = url_for( '/', qualified=True ).rstrip( '/' )
    if trans.user:
        protocol, base = base_url.split( '://' )
        username = '%s@' % trans.user.username
        return '%s://%s%s/repos/%s/%s' % ( protocol, username, base, repository.user.username, repository.name )
    else:
        return '%s/repos/%s/%s' % ( base_url, repository.user.username, repository.name )
def generate_message_for_invalid_tools( trans, invalid_file_tups, repository, metadata_dict, as_html=True, displaying_invalid_tool=False ):
    if as_html:
        new_line = '<br/>'
        bold_start = '<b>'
        bold_end = '</b>'
    else:
        new_line = '\n'
        bold_start = ''
        bold_end = ''
    message = ''
    if not displaying_invalid_tool:
        if metadata_dict:
            message += "Metadata was defined for some items in revision '%s'.  " % str( repository.tip( trans.app ) )
            message += "Correct the following problems if necessary and reset metadata.%s" % new_line
        else:
            message += "Metadata cannot be defined for revision '%s' so this revision cannot be automatically " % str( repository.tip( trans.app ) )
            message += "installed into a local Galaxy instance.  Correct the following problems and reset metadata.%s" % new_line
    for itc_tup in invalid_file_tups:
        tool_file, exception_msg = itc_tup
        if exception_msg.find( 'No such file or directory' ) >= 0:
            exception_items = exception_msg.split()
            missing_file_items = exception_items[ 7 ].split( '/' )
            missing_file = missing_file_items[ -1 ].rstrip( '\'' )
            if missing_file.endswith( '.loc' ):
                sample_ext = '%s.sample' % missing_file
            else:
                sample_ext = missing_file
            correction_msg = "This file refers to a missing file %s%s%s.  " % ( bold_start, str( missing_file ), bold_end )
            correction_msg += "Upload a file named %s%s%s to the repository to correct this error." % ( bold_start, sample_ext, bold_end )
        else:
            if as_html:
                correction_msg = exception_msg
            else:
                correction_msg = exception_msg.replace( '<br/>', new_line ).replace( '<b>', bold_start ).replace( '</b>', bold_end )
        message += "%s%s%s - %s%s" % ( bold_start, tool_file, bold_end, correction_msg, new_line )
    return message
def generate_metadata_for_changeset_revision( app, repository, repository_clone_url, shed_config_dict={}, relative_install_dir=None, repository_files_dir=None,
                                              resetting_all_metadata_on_repository=False, updating_installed_repository=False, persist=False ):
    """
    Generate metadata for a repository using it's files on disk.  To generate metadata for changeset revisions older than the repository tip,
    the repository will have been cloned to a temporary location and updated to a specified changeset revision to access that changeset revision's
    disk files, so the value of repository_files_dir will not always be repository.repo_path( app ) (it could be an absolute path to a temporary
    directory containing a clone).  If it is an absolute path, the value of relative_install_dir must contain repository.repo_path( app ).
    
    The value of persist will be True when the installed repository contains a valid tool_data_table_conf.xml.sample file, in which case the entries
    should ultimately be persisted to the file referred to by app.config.shed_tool_data_table_config.
    """
    if updating_installed_repository:
        # Keep the original tool shed repository metadata if setting metadata on a repository installed into a local Galaxy instance for which 
        # we have pulled updates.
        original_repository_metadata = repository.metadata
    else:
        original_repository_metadata = None
    readme_file_names = get_readme_file_names( repository.name )
    metadata_dict = { 'shed_config_filename': shed_config_dict.get( 'config_filename' ) }
    invalid_file_tups = []
    invalid_tool_configs = []
    tool_dependencies_config = None
    original_tool_data_path = app.config.tool_data_path
    original_tool_data_table_config_path = app.config.tool_data_table_config_path
    if resetting_all_metadata_on_repository:
        if not relative_install_dir:
            raise Exception( "The value of repository.repo_path( app ) must be sent when resetting all metadata on a repository." )
        # Keep track of the location where the repository is temporarily cloned so that we can strip the path when setting metadata.  The value of
        # repository_files_dir is the full path to the temporary directory to which the repository was cloned.
        work_dir = repository_files_dir
        files_dir = repository_files_dir
        # Since we're working from a temporary directory, we can safely copy sample files included in the repository to the repository root.
        app.config.tool_data_path = repository_files_dir
        app.config.tool_data_table_config_path = repository_files_dir
    else:
        # Use a temporary working directory to copy all sample files.
        work_dir = tempfile.mkdtemp()
        # All other files are on disk in the repository's repo_path, which is the value of relative_install_dir.
        files_dir = relative_install_dir
        if shed_config_dict.get( 'tool_path' ):
            files_dir = os.path.join( shed_config_dict['tool_path'], files_dir )
        app.config.tool_data_path = work_dir
        app.config.tool_data_table_config_path = work_dir
    # Handle proprietary datatypes, if any.
    datatypes_config = get_config_from_disk( 'datatypes_conf.xml', files_dir )
    if datatypes_config:
        metadata_dict = generate_datatypes_metadata( datatypes_config, metadata_dict )
    # Get the relative path to all sample files included in the repository for storage in the repository's metadata.
    sample_file_metadata_paths, sample_file_copy_paths = get_sample_files_from_disk( repository_files_dir=files_dir,
                                                                                     tool_path=shed_config_dict.get( 'tool_path' ),
                                                                                     relative_install_dir=relative_install_dir,
                                                                                     resetting_all_metadata_on_repository=resetting_all_metadata_on_repository )
    if sample_file_metadata_paths:
        metadata_dict[ 'sample_files' ] = sample_file_metadata_paths
    # Copy all sample files included in the repository to a single directory location so we can load tools that depend on them.
    for sample_file in sample_file_copy_paths:
        copy_sample_file( app, sample_file, dest_path=work_dir )
        # If the list of sample files includes a tool_data_table_conf.xml.sample file, laad it's table elements into memory.
        relative_path, filename = os.path.split( sample_file )
        if filename == 'tool_data_table_conf.xml.sample':
            new_table_elems = app.tool_data_tables.add_new_entries_from_config_file( config_filename=sample_file,
                                                                                     tool_data_path=original_tool_data_path,
                                                                                     shed_tool_data_table_config=app.config.shed_tool_data_table_config,
                                                                                     persist=persist )
    for root, dirs, files in os.walk( files_dir ):
        if root.find( '.hg' ) < 0 and root.find( 'hgrc' ) < 0:
            if '.hg' in dirs:
                dirs.remove( '.hg' )
            for name in files:
                # See if we have a READ_ME file.
                if name.lower() in readme_file_names:
                    if resetting_all_metadata_on_repository:
                        full_path_to_readme = os.path.join( root, name )
                        stripped_path_to_readme = full_path_to_readme.replace( work_dir, '' )
                        if stripped_path_to_readme.startswith( '/' ):
                            stripped_path_to_readme = stripped_path_to_readme[ 1: ]
                        relative_path_to_readme = os.path.join( relative_install_dir, stripped_path_to_readme )
                    else:
                        relative_path_to_readme = os.path.join( root, name )
                        if relative_install_dir and shed_config_dict.get( 'tool_path' ) and relative_path_to_readme.startswith( os.path.join( shed_config_dict.get( 'tool_path' ), relative_install_dir ) ):
                            relative_path_to_readme = relative_path_to_readme[ len( shed_config_dict.get( 'tool_path' ) ) + 1: ]
                    metadata_dict[ 'readme' ] = relative_path_to_readme
                # See if we have a tool config.
                elif name not in NOT_TOOL_CONFIGS and name.endswith( '.xml' ):
                    full_path = str( os.path.abspath( os.path.join( root, name ) ) )
                    if os.path.getsize( full_path ) > 0:
                        if not ( check_binary( full_path ) or check_image( full_path ) or check_gzip( full_path )[ 0 ]
                                 or check_bz2( full_path )[ 0 ] or check_zip( full_path ) ):
                            try:
                                # Make sure we're looking at a tool config and not a display application config or something else.
                                element_tree = util.parse_xml( full_path )
                                element_tree_root = element_tree.getroot()
                                is_tool = element_tree_root.tag == 'tool'
                            except Exception, e:
                                log.debug( "Error parsing %s, exception: %s" % ( full_path, str( e ) ) )
                                is_tool = False
                            if is_tool:
                                tool, valid, error_message = load_tool_from_config( app, full_path )
                                if tool is None:
                                    if not valid:
                                        invalid_file_tups.append( ( name, error_message ) )
                                else:
                                    invalid_files_and_errors_tups = check_tool_input_params( app, files_dir, name, tool, sample_file_metadata_paths )
                                    can_set_metadata = True
                                    for tup in invalid_files_and_errors_tups:
                                        if name in tup:
                                            can_set_metadata = False
                                            invalid_tool_configs.append( name )
                                            break
                                    if can_set_metadata:
                                        if resetting_all_metadata_on_repository:
                                            full_path_to_tool_config = os.path.join( root, name )
                                            stripped_path_to_tool_config = full_path_to_tool_config.replace( work_dir, '' )
                                            if stripped_path_to_tool_config.startswith( '/' ):
                                                stripped_path_to_tool_config = stripped_path_to_tool_config[ 1: ]
                                            relative_path_to_tool_config = os.path.join( relative_install_dir, stripped_path_to_tool_config )
                                        else:
                                            relative_path_to_tool_config = os.path.join( root, name )
                                            if relative_install_dir and shed_config_dict.get( 'tool_path' ) and relative_path_to_tool_config.startswith( os.path.join( shed_config_dict.get( 'tool_path' ), relative_install_dir ) ):
                                                relative_path_to_tool_config = relative_path_to_tool_config[ len( shed_config_dict.get( 'tool_path' ) ) + 1: ]
                                        metadata_dict = generate_tool_metadata( relative_path_to_tool_config, tool, repository_clone_url, metadata_dict )
                                    else:
                                        for tup in invalid_files_and_errors_tups:
                                            invalid_file_tups.append( tup )
                # Find all exported workflows.
                elif name.endswith( '.ga' ):
                    relative_path = os.path.join( root, name )
                    if os.path.getsize( os.path.abspath( relative_path ) ) > 0:
                        fp = open( relative_path, 'rb' )
                        workflow_text = fp.read()
                        fp.close()
                        exported_workflow_dict = from_json_string( workflow_text )
                        if 'a_galaxy_workflow' in exported_workflow_dict and exported_workflow_dict[ 'a_galaxy_workflow' ] == 'true':
                            metadata_dict = generate_workflow_metadata( relative_path, exported_workflow_dict, metadata_dict )
    if 'tools' in metadata_dict:
        # This step must be done after metadata for tools has been defined.
        tool_dependencies_config = get_config_from_disk( 'tool_dependencies.xml', files_dir )
        if tool_dependencies_config:
            metadata_dict = generate_tool_dependency_metadata( app,
                                                               repository,
                                                               tool_dependencies_config,
                                                               metadata_dict,
                                                               original_repository_metadata=original_repository_metadata )
    if invalid_tool_configs:
        metadata_dict [ 'invalid_tools' ] = invalid_tool_configs
    # Reset the value of the app's tool_data_path  and tool_data_table_config_path to their respective original values.
    app.config.tool_data_path = original_tool_data_path
    app.config.tool_data_table_config_path = original_tool_data_table_config_path
    return metadata_dict, invalid_file_tups
def get_changectx_for_changeset( repo, changeset_revision, **kwd ):
    """Retrieve a specified changectx from a repository"""
    for changeset in repo.changelog:
        ctx = repo.changectx( changeset )
        if str( ctx ) == changeset_revision:
            return ctx
    return None
def get_config_from_disk( config_file, relative_install_dir ):
    for root, dirs, files in os.walk( relative_install_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name == config_file:
                    return os.path.abspath( os.path.join( root, name ) )
    return None
def get_configured_ui():
    # Configure any desired ui settings.
    _ui = ui.ui()
    # The following will suppress all messages.  This is
    # the same as adding the following setting to the repo
    # hgrc file' [ui] section:
    # quiet = True
    _ui.setconfig( 'ui', 'quiet', True )
    return _ui
def get_file_context_from_ctx( ctx, filename ):
    # We have to be careful in determining if we found the correct file because multiple files with the same name may be in different directories
    # within ctx if the files were moved within the change set.  For example, in the following ctx.files() list, the former may have been moved to
    # the latter: ['tmap_wrapper_0.0.19/tool_data_table_conf.xml.sample', 'tmap_wrapper_0.3.3/tool_data_table_conf.xml.sample'].  Another scenario
    # is that the file has been deleted.
    deleted = False
    filename = strip_path( filename )
    for ctx_file in ctx.files():
        ctx_file_name = strip_path( ctx_file )
        if filename == ctx_file_name:
            try:
                # If the file was moved, its destination will be returned here.
                fctx = ctx[ ctx_file ]
                return fctx
            except LookupError, e:
                # Set deleted for now, and continue looking in case the file was moved instead of deleted.
                deleted = True
    if deleted:
        return 'DELETED'
    return None
def get_repository_file_contents( file_path ):
    if is_gzip( file_path ):
        to_html = to_html_str( '\ngzip compressed file\n' )
    elif is_bz2( file_path ):
        to_html = to_html_str( '\nbz2 compressed file\n' )
    elif check_zip( file_path ):
        to_html = to_html_str( '\nzip compressed file\n' )
    elif check_binary( file_path ):
        to_html = to_html_str( '\nBinary file\n' )
    else:
        to_html = ''
        for i, line in enumerate( open( file_path ) ):
            to_html = '%s%s' % ( to_html, to_html_str( line ) )
            if len( to_html ) > MAX_CONTENT_SIZE:
                large_str = '\nFile contents truncated because file size is larger than maximum viewing size of %s\n' % util.nice_size( MAX_CONTENT_SIZE )
                to_html = '%s%s' % ( to_html, to_html_str( large_str ) )
                break
    return to_html
def get_repository_in_tool_shed( trans, id ):
    """Get a repository on the tool shed side from the database via id"""
    return trans.sa_session.query( trans.model.Repository ).get( trans.security.decode_id( id ) )
def get_repository_metadata_by_changeset_revision( trans, id, changeset_revision ):
    """Get metadata for a specified repository change set from the database"""
    # Make sure there are no duplicate records, and return the single unique record for the changeset_revision.  Duplicate records were somehow
    # created in the past.  The cause of this issue has been resolved, but we'll leave this method as is for a while longer to ensure all duplicate
    # records are removed.
    all_metadata_records = trans.sa_session.query( trans.model.RepositoryMetadata ) \
                                           .filter( and_( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ),
                                                          trans.model.RepositoryMetadata.table.c.changeset_revision == changeset_revision ) ) \
                                           .order_by( trans.model.RepositoryMetadata.table.c.update_time.desc() ) \
                                           .all()
    if len( all_metadata_records ) > 1:
        # Delete all recrds older than the last one updated.
        for repository_metadata in all_metadata_records[ 1: ]:
            trans.sa_session.delete( repository_metadata )
            trans.sa_session.flush()
        return all_metadata_records[ 0 ]
    elif all_metadata_records:
        return all_metadata_records[ 0 ]
    return None
def get_named_tmpfile_from_ctx( ctx, filename, dir ):
    filename = strip_path( filename )
    for ctx_file in ctx.files():
        ctx_file_name = strip_path( ctx_file )
        if filename == ctx_file_name:
            try:
                # If the file was moved, its destination file contents will be returned here.
                fctx = ctx[ ctx_file ]
            except LookupError, e:
                # Continue looking in case the file was moved.
                fctx = None
                continue
            if fctx:
                fh = tempfile.NamedTemporaryFile( 'wb', dir=dir )
                tmp_filename = fh.name
                fh.close()
                fh = open( tmp_filename, 'wb' )
                fh.write( fctx.data() )
                fh.close()
                return tmp_filename
    return None
def get_parent_id( trans, id, old_id, version, guid, changeset_revisions ):
    parent_id = None
    # Compare from most recent to oldest.
    changeset_revisions.reverse()
    for changeset_revision in changeset_revisions:
        repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
        metadata = repository_metadata.metadata
        tools_dicts = metadata.get( 'tools', [] )
        for tool_dict in tools_dicts:
            if tool_dict[ 'guid' ] == guid:
                # The tool has not changed between the compared changeset revisions.
                continue
            if tool_dict[ 'id' ] == old_id and tool_dict[ 'version' ] != version:
                # The tool version is different, so we've found the parent.
                return tool_dict[ 'guid' ]
    if parent_id is None:
        # The tool did not change through all of the changeset revisions.
        return old_id
def handle_sample_files_and_load_tool_from_disk( trans, repo_files_dir, tool_config_filepath, work_dir ):
    # Copy all sample files from disk to a temporary directory since the sample files may be in multiple directories.
    message = ''
    sample_files = copy_disk_sample_files_to_dir( trans, repo_files_dir, work_dir )
    if sample_files:
        if 'tool_data_table_conf.xml.sample' in sample_files:
            # Load entries into the tool_data_tables if the tool requires them.
            tool_data_table_config = os.path.join( work_dir, 'tool_data_table_conf.xml' )
            error, message = handle_sample_tool_data_table_conf_file( trans.app, tool_data_table_config )
    tool, valid, message2 = load_tool_from_config( trans.app, tool_config_filepath )
    message = concat_messages( message, message2 )
    return tool, valid, message, sample_files
def handle_sample_files_and_load_tool_from_tmp_config( trans, repo, changeset_revision, tool_config_filename, work_dir ):
    tool = None
    message = ''
    ctx = get_changectx_for_changeset( repo, changeset_revision )
    # We're not currently doing anything with the returned list of deleted_sample_files here.  It is intended to help handle sample files that are in 
    # the manifest, but have been deleted from disk.
    sample_files, deleted_sample_files = get_list_of_copied_sample_files( repo, ctx, dir=work_dir )
    if sample_files:
        trans.app.config.tool_data_path = work_dir
        if 'tool_data_table_conf.xml.sample' in sample_files:
            # Load entries into the tool_data_tables if the tool requires them.
            tool_data_table_config = os.path.join( work_dir, 'tool_data_table_conf.xml' )
            if tool_data_table_config:
                error, message = handle_sample_tool_data_table_conf_file( trans.app, tool_data_table_config )
                if error:
                    log.debug( message )
    manifest_ctx, ctx_file = get_ctx_file_path_from_manifest( tool_config_filename, repo, changeset_revision )
    if manifest_ctx and ctx_file:
        tool, message2 = load_tool_from_tmp_config( trans, repo, manifest_ctx, ctx_file, work_dir )
        message = concat_messages( message, message2 )
    return tool, message, sample_files
def handle_sample_tool_data_table_conf_file( app, filename, persist=False ):
    """
    Parse the incoming filename and add new entries to the in-memory app.tool_data_tables dictionary.  If persist is True (should only occur
    if call is from the Galaxy side, not the tool shed), the new entries will be appended to Galaxy's shed_tool_data_table_conf.xml file on disk.
    """
    error = False
    message = ''
    try:
        new_table_elems = app.tool_data_tables.add_new_entries_from_config_file( config_filename=filename,
                                                                                 tool_data_path=app.config.tool_data_path,
                                                                                 shed_tool_data_table_config=app.config.shed_tool_data_table_config,
                                                                                 persist=persist )
    except Exception, e:
        message = str( e )
        error = True
    return error, message
def is_downloadable( metadata_dict ):
    return 'datatypes' in metadata_dict or 'tools' in metadata_dict or 'workflows' in metadata_dict
def load_tool_from_config( app, full_path ):
    try:
        tool = app.toolbox.load_tool( full_path )
        valid = True
        error_message = None
    except KeyError, e:
        tool = None
        valid = False
        error_message = 'This file requires an entry for "%s" in the tool_data_table_conf.xml file.  Upload a file ' % str( e )
        error_message += 'named tool_data_table_conf.xml.sample to the repository that includes the required entry to correct '
        error_message += 'this error.  '
    except Exception, e:
        tool = None
        valid = False
        error_message = str( e )
    return tool, valid, error_message
def open_repository_files_folder( trans, folder_path ):
    try:
        files_list = get_repository_files( trans, folder_path )
    except OSError, e:
        if str( e ).find( 'No such file or directory' ) >= 0:
            # We have a repository with no contents.
            return []
    folder_contents = []
    for filename in files_list:
        is_folder = False
        if filename and filename[-1] == os.sep:
            is_folder = True
        if filename:
            full_path = os.path.join( folder_path, filename )
            node = { "title": filename,
                     "isFolder": is_folder,
                     "isLazy": is_folder,
                     "tooltip": full_path,
                     "key": full_path }
            folder_contents.append( node )
    return folder_contents
def remove_dir( dir ):
    if os.path.exists( dir ):
        try:
            shutil.rmtree( dir )
        except:
            pass
def reset_all_metadata_on_repository_in_tool_shed( trans, id ):
    """Reset all metadata on a single repository in a tool shed."""
    def reset_all_tool_versions( trans, id, repo ):
        changeset_revisions = []
        for changeset in repo.changelog:
            changeset_revision = str( repo.changectx( changeset ) )
            repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if metadata.get( 'tools', None ):
                        changeset_revisions.append( changeset_revision )
        # The list of changeset_revisions is now filtered to contain only those that are downloadable and contain tools.
        # If a repository includes tools, build a dictionary of { 'tool id' : 'parent tool id' } pairs for each tool in each changeset revision.
        for index, changeset_revision in enumerate( changeset_revisions ):
            tool_versions_dict = {}
            repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
            metadata = repository_metadata.metadata
            tool_dicts = metadata[ 'tools' ]
            if index == 0:
                # The first changset_revision is a special case because it will have no ancestor changeset_revisions in which to match tools.
                # The parent tool id for tools in the first changeset_revision will be the "old_id" in the tool config.
                for tool_dict in tool_dicts:
                    tool_versions_dict[ tool_dict[ 'guid' ] ] = tool_dict[ 'id' ]
            else:
                for tool_dict in tool_dicts:
                    parent_id = get_parent_id( trans,
                                               id,
                                               tool_dict[ 'id' ],
                                               tool_dict[ 'version' ],
                                               tool_dict[ 'guid' ],
                                               changeset_revisions[ 0:index ] )
                    tool_versions_dict[ tool_dict[ 'guid' ] ] = parent_id
            if tool_versions_dict:
                repository_metadata.tool_versions = tool_versions_dict
                trans.sa_session.add( repository_metadata )
                trans.sa_session.flush()
    repository = get_repository_in_tool_shed( trans, id )
    log.debug( "Resetting all metadata on repository: %s" % repository.name )
    repo_dir = repository.repo_path( trans.app )
    repo = hg.repository( get_configured_ui(), repo_dir )
    repository_clone_url = generate_clone_url_for_repository_in_tool_shed( trans, repository )
    # The list of changeset_revisions refers to repository_metadata records that have been created or updated.  When the following loop
    # completes, we'll delete all repository_metadata records for this repository that do not have a changeset_revision value in this list.
    changeset_revisions = []
    # When a new repository_metadata record is created, it always uses the values of metadata_changeset_revision and metadata_dict.
    metadata_changeset_revision = None
    metadata_dict = None
    ancestor_changeset_revision = None
    ancestor_metadata_dict = None
    invalid_file_tups = []
    home_dir = os.getcwd()
    for changeset in repo.changelog:
        work_dir = tempfile.mkdtemp()
        current_changeset_revision = str( repo.changectx( changeset ) )
        ctx = repo.changectx( changeset )
        log.debug( "Cloning repository revision: %s", str( ctx.rev() ) )
        cloned_ok, error_message = clone_repository( repository_clone_url, work_dir, str( ctx.rev() ) )
        if cloned_ok:
            log.debug( "Generating metadata for changset revision: %s", str( ctx.rev() ) )
            current_metadata_dict, invalid_file_tups = generate_metadata_for_changeset_revision( app=trans.app,
                                                                                                 repository=repository,
                                                                                                 repository_clone_url=repository_clone_url,
                                                                                                 relative_install_dir=repo_dir,
                                                                                                 repository_files_dir=work_dir,
                                                                                                 resetting_all_metadata_on_repository=True,
                                                                                                 updating_installed_repository=False,
                                                                                                 persist=False )
            if current_metadata_dict:
                if not metadata_changeset_revision and not metadata_dict:
                    # We're at the first change set in the change log.
                    metadata_changeset_revision = current_changeset_revision
                    metadata_dict = current_metadata_dict
                if ancestor_changeset_revision:
                    # Compare metadata from ancestor and current.  The value of comparison will be one of:
                    # 'no metadata' - no metadata for either ancestor or current, so continue from current
                    # 'equal' - ancestor metadata is equivalent to current metadata, so continue from current
                    # 'subset' - ancestor metadata is a subset of current metadata, so continue from current
                    # 'not equal and not subset' - ancestor metadata is neither equal to nor a subset of current metadata, so persist ancestor metadata.
                    comparison = compare_changeset_revisions( ancestor_changeset_revision,
                                                              ancestor_metadata_dict,
                                                              current_changeset_revision,
                                                              current_metadata_dict )
                    if comparison in [ 'no metadata', 'equal', 'subset' ]:
                        ancestor_changeset_revision = current_changeset_revision
                        ancestor_metadata_dict = current_metadata_dict
                    elif comparison == 'not equal and not subset':
                        metadata_changeset_revision = ancestor_changeset_revision
                        metadata_dict = ancestor_metadata_dict
                        repository_metadata = create_or_update_repository_metadata( trans, id, repository, metadata_changeset_revision, metadata_dict )
                        changeset_revisions.append( metadata_changeset_revision )
                        ancestor_changeset_revision = current_changeset_revision
                        ancestor_metadata_dict = current_metadata_dict
                else:
                    # We're at the beginning of the change log.
                    ancestor_changeset_revision = current_changeset_revision
                    ancestor_metadata_dict = current_metadata_dict
                if not ctx.children():
                    metadata_changeset_revision = current_changeset_revision
                    metadata_dict = current_metadata_dict
                    # We're at the end of the change log.
                    repository_metadata = create_or_update_repository_metadata( trans, id, repository, metadata_changeset_revision, metadata_dict )
                    changeset_revisions.append( metadata_changeset_revision )
                    ancestor_changeset_revision = None
                    ancestor_metadata_dict = None
            elif ancestor_metadata_dict:
                # We reach here only if current_metadata_dict is empty and ancestor_metadata_dict is not.
                if not ctx.children():
                    # We're at the end of the change log.
                    repository_metadata = create_or_update_repository_metadata( trans, id, repository, metadata_changeset_revision, metadata_dict )
                    changeset_revisions.append( metadata_changeset_revision )
                    ancestor_changeset_revision = None
                    ancestor_metadata_dict = None
        remove_dir( work_dir )
    # Delete all repository_metadata records for this repository that do not have a changeset_revision value in changeset_revisions.
    clean_repository_metadata( trans, id, changeset_revisions )
    # Set tool version information for all downloadable changeset revisions.  Get the list of changeset revisions from the changelog.
    reset_all_tool_versions( trans, id, repo )
    # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
    reset_tool_data_tables( trans.app )
    return invalid_file_tups, metadata_dict
def reset_metadata_on_selected_repositories( trans, **kwd ):
    # This method is called from both Galaxy and the Tool Shed, so the cntrller param is required.
    repository_ids = util.listify( kwd.get( 'repository_ids', None ) )
    CONTROLLER = kwd[ 'CONTROLLER' ]
    message = ''
    status = 'done'
    if repository_ids:
        successful_count = 0
        unsuccessful_count = 0
        for repository_id in repository_ids:
            try:
                if CONTROLLER == 'TOOL_SHED_ADMIN_CONTROLLER':
                    repository = get_repository_in_tool_shed( trans, repository_id )
                    invalid_file_tups, metadata_dict = reset_all_metadata_on_repository_in_tool_shed( trans, repository_id )
                elif CONTROLLER == 'GALAXY_ADMIN_TOOL_SHED_CONTROLLER':
                    repository = get_installed_tool_shed_repository( trans, repository_id )
                    invalid_file_tups, metadata_dict = reset_all_metadata_on_installed_repository( trans, repository_id )
                if invalid_file_tups:
                    message = generate_message_for_invalid_tools( trans, invalid_file_tups, repository, None, as_html=False )
                    log.debug( message )
                    unsuccessful_count += 1
                else:
                    log.debug( "Successfully reset metadata on repository %s" % repository.name )
                    successful_count += 1
            except Exception, e:
                log.debug( "Error attempting to reset metadata on repository '%s': %s" % ( repository.name, str( e ) ) )
                unsuccessful_count += 1
        message = "Successfully reset metadata on %d %s.  " % ( successful_count, inflector.cond_plural( successful_count, "repository" ) )
        if unsuccessful_count:
            message += "Error setting metadata on %d %s - see the paster log for details.  " % ( unsuccessful_count,
                                                                                                 inflector.cond_plural( unsuccessful_count, "repository" ) )
    else:
        message = 'Select at least one repository to on which to reset all metadata.'
        status = 'error'
    return message, status
def reset_tool_data_tables( app ):
    # Reset the tool_data_tables to an empty dictionary.
    app.tool_data_tables.data_tables = {}
def reversed_lower_upper_bounded_changelog( repo, excluded_lower_bounds_changeset_revision, included_upper_bounds_changeset_revision ):
    """
    Return a reversed list of changesets in the repository changelog after the excluded_lower_bounds_changeset_revision, but up to and
    including the included_upper_bounds_changeset_revision.  The value of excluded_lower_bounds_changeset_revision will be the value of
    INITIAL_CHANGELOG_HASH if no valid changesets exist before included_upper_bounds_changeset_revision.
    """
    # To set excluded_lower_bounds_changeset_revision, calling methods should do the following, where the value of changeset_revision
    # is a downloadable changeset_revision.
    # excluded_lower_bounds_changeset_revision = get_previous_downloadable_changset_revision( repository, repo, changeset_revision )
    if excluded_lower_bounds_changeset_revision == INITIAL_CHANGELOG_HASH:
        appending_started = True
    else:
        appending_started = False
    reversed_changelog = []
    for changeset in repo.changelog:
        changeset_hash = str( repo.changectx( changeset ) )
        if appending_started:
            reversed_changelog.insert( 0, changeset )
        if changeset_hash == excluded_lower_bounds_changeset_revision and not appending_started:
            appending_started = True
        if changeset_hash == included_upper_bounds_changeset_revision:
            break
    return reversed_changelog
def reversed_upper_bounded_changelog( repo, included_upper_bounds_changeset_revision ):
    return reversed_lower_upper_bounded_changelog( repo, INITIAL_CHANGELOG_HASH, included_upper_bounds_changeset_revision )
def strip_path( fpath ):
    if not fpath:
        return fpath
    try:
        file_path, file_name = os.path.split( fpath )
    except:
        file_name = fpath
    return file_name
def update_repository( repo, ctx_rev=None ):
    """
    Update the cloned repository to changeset_revision.  It is critical that the installed repository is updated to the desired
    changeset_revision before metadata is set because the process for setting metadata uses the repository files on disk.
    """
    # TODO: We may have files on disk in the repo directory that aren't being tracked, so they must be removed.
    # The codes used to show the status of files are as follows.
    # M = modified
    # A = added
    # R = removed
    # C = clean
    # ! = deleted, but still tracked
    # ? = not tracked
    # I = ignored
    # It would be nice if we could use mercurial's purge extension to remove untracked files.  The problem is that
    # purging is not supported by the mercurial API.  See the deprecated update_for_browsing() method in common.py.
    commands.update( get_configured_ui(),
                     repo,
                     rev=ctx_rev )
def url_join( *args ):
    parts = []
    for arg in args:
        parts.append( arg.strip( '/' ) )
    return '/'.join( parts )
