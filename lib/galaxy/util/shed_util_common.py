import os, shutil, tempfile, logging, string, threading, urllib2
from galaxy import util
from galaxy.tools import parameters
from galaxy.util import inflector
from galaxy.util import json
from galaxy.web import url_for
from galaxy.web.form_builder import SelectField
from galaxy.webapps.community.util import container_util
from galaxy.datatypes import checkers
from galaxy.model.orm import and_
from galaxy.tools.parameters import dynamic_options

from galaxy import eggs
import pkg_resources

pkg_resources.require( 'mercurial' )
from mercurial import hg, ui, commands

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree, ElementInclude
from elementtree.ElementTree import Element, SubElement

eggs.require( 'markupsafe' )
import markupsafe
        
log = logging.getLogger( __name__ )

INITIAL_CHANGELOG_HASH = '000000000000'
# Characters that must be html escaped
MAPPED_CHARS = { '>' :'&gt;', 
                 '<' :'&lt;',
                 '"' : '&quot;',
                 '&' : '&amp;',
                 '\'' : '&apos;' }
MAX_CONTENT_SIZE = 32768
NOT_TOOL_CONFIGS = [ 'datatypes_conf.xml', 'repository_dependencies.xml', 'tool_dependencies.xml' ]
GALAXY_ADMIN_TOOL_SHED_CONTROLLER = 'GALAXY_ADMIN_TOOL_SHED_CONTROLLER'
TOOL_SHED_ADMIN_CONTROLLER = 'TOOL_SHED_ADMIN_CONTROLLER'
VALID_CHARS = set( string.letters + string.digits + "'\"-=_.()/+*^,:?!#[]%\\$@;{}" )

def add_installation_directories_to_tool_dependencies( trans, repository_name, repository_owner, changeset_revision, tool_dependencies ):
    for dependency_key, requirements_dict in tool_dependencies.items():
        if dependency_key not in [ 'set_environment' ]:
            dependency_name = requirements_dict[ 'name' ]
            version = requirements_dict[ 'version' ]
            type = requirements_dict[ 'type' ]
            install_dir = os.path.join( trans.app.config.tool_dependency_dir,
                                        dependency_name,
                                        version,
                                        repository_owner,
                                        repository_name,
                                        changeset_revision )
            requirements_dict[ 'install_dir' ] = install_dir
            tool_dependencies[ dependency_key ] = requirements_dict
    return tool_dependencies
def build_readme_files_dict( repository_metadata ):
    """Return a dictionary of valid readme file name <-> readme file content pairs for all readme files contained in the received repository_metadata."""
    readme_files_dict = {}
    if repository_metadata:
        metadata = repository_metadata.metadata
        if metadata and 'readme_files' in metadata:
            for relative_path_to_readme_file in metadata[ 'readme_files' ]:
                readme_file_name = os.path.split( relative_path_to_readme_file )[ 1 ]
                full_path_to_readme_file = os.path.abspath( relative_path_to_readme_file )
                try:
                    f = open( full_path_to_readme_file, 'r' )
                    text = f.read()
                    f.close()
                    readme_files_dict[ readme_file_name ] = translate_string( text, to_html=False )
                except Exception, e:
                    log.debug( "Error reading README file '%s' defined in metadata for repository '%s', revision '%s': %s" % \
                               ( str( relative_path_to_readme_file ), str( repository_name ), str( changeset_revision ), str( e ) ) )
    return readme_files_dict
def build_repository_containers_for_galaxy( trans, toolshed_base_url, repository_name, repository_owner, changeset_revision, 
                                            readme_files_dict, repository_dependencies, tool_dependencies ):
    """Return a dictionary of containers for the received repository's dependencies and readme files for display during installation to Galaxy."""
    containers_dict = dict( readme_files=None, repository_dependencies=None, tool_dependencies=None )
    if readme_files_dict or repository_dependencies or tool_dependencies:
        lock = threading.Lock()
        lock.acquire( True )
        if tool_dependencies:
            # Add the install_dir attribute to the tool_dependencies.
            tool_dependencies = add_installation_directories_to_tool_dependencies( trans,
                                                                                   repository_name,
                                                                                   repository_owner,
                                                                                   changeset_revision,
                                                                                   tool_dependencies )
        try:
            folder_id = 0
            if readme_files_dict:
                folder_id, readme_files_root_folder = build_readme_files_folder( folder_id, readme_files_dict )
                containers_dict[ 'readme_files' ] = readme_files_root_folder
            if repository_dependencies:
                folder_id, repository_dependencies_root_folder = container_util.build_repository_dependencies_folder( toolshed_base_url=toolshed_base_url,
                                                                                                                      repository_name=repository_name,
                                                                                                                      repository_owner=repository_owner,
                                                                                                                      changeset_revision=changeset_revision,
                                                                                                                      folder_id=folder_id,
                                                                                                                      repository_dependencies=repository_dependencies )
                containers_dict[ 'repository_dependencies' ] = repository_dependencies_root_folder
            if tool_dependencies:
                folder_id, tool_dependencies_root_folder = container_util.build_tool_dependencies_folder( folder_id, tool_dependencies, for_galaxy=True )
                containers_dict[ 'tool_dependencies' ] = tool_dependencies_root_folder
        except Exception, e:
            log.debug( "Exception in build_repository_containers_for_galaxy: %s" % str( e ) )
        finally:
            lock.release()
    return containers_dict
def build_repository_containers_for_tool_shed( repository, changeset_revision, repository_dependencies, repository_metadata ):
    """Return a dictionary of containers for the received repository's dependencies and contents for display in the tool shed."""
    containers_dict = dict( datatypes=None,
                            invalid_tools=None,
                            readme_files=None,
                            repository_dependencies=None,
                            tool_dependencies=None,
                            valid_tools=None,
                            workflows=None )
    if repository_metadata:
        metadata = repository_metadata.metadata
        lock = threading.Lock()
        lock.acquire( True )
        try:
            folder_id = 0
            # Datatypes container.
            if metadata and 'datatypes' in metadata:
                datatypes = metadata[ 'datatypes' ]
                folder_id, datatypes_root_folder = container_util.build_datatypes_folder( folder_id, datatypes )
                containers_dict[ 'datatypes' ] = datatypes_root_folder
            # Invalid tools container.
            if metadata and 'invalid_tools' in metadata:
                invalid_tool_configs = metadata[ 'invalid_tools' ]
                folder_id, invalid_tools_root_folder = container_util.build_invalid_tools_folder( folder_id,
                                                                                                  invalid_tool_configs,
                                                                                                  changeset_revision,
                                                                                                  repository=repository,
                                                                                                  label='Invalid tools' )
                containers_dict[ 'invalid_tools' ] = invalid_tools_root_folder
            # Readme files container.
            readme_files_dict = build_readme_files_dict( repository_metadata )
            folder_id, readme_files_root_folder = container_util.build_readme_files_folder( folder_id, readme_files_dict )
            containers_dict[ 'readme_files' ] = readme_files_root_folder
            # Repository dependencies container.
            toolshed_base_url = str( url_for( '/', qualified=True ) ).rstrip( '/' )
            folder_id, repository_dependencies_root_folder = container_util.build_repository_dependencies_folder( toolshed_base_url=toolshed_base_url,
                                                                                                                  repository_name=repository.name,
                                                                                                                  repository_owner=repository.user.username,
                                                                                                                  changeset_revision=changeset_revision,
                                                                                                                  folder_id=folder_id,
                                                                                                                  repository_dependencies=repository_dependencies )
            if repository_dependencies_root_folder:
                containers_dict[ 'repository_dependencies' ] = repository_dependencies_root_folder
            # Tool dependencies container.
            if metadata and 'tool_dependencies' in metadata:
                tool_dependencies = metadata[ 'tool_dependencies' ]
                folder_id, tool_dependencies_root_folder = container_util.build_tool_dependencies_folder( folder_id, tool_dependencies, for_galaxy=False )
                containers_dict[ 'tool_dependencies' ] = tool_dependencies_root_folder
            # Valid tools container.
            if metadata and 'tools' in metadata:
                valid_tools = metadata[ 'tools' ]
                folder_id, valid_tools_root_folder = container_util.build_tools_folder( folder_id,
                                                                                        valid_tools,
                                                                                        repository,
                                                                                        changeset_revision,
                                                                                        label='Valid tools' )
                containers_dict[ 'valid_tools' ] = valid_tools_root_folder
            # Workflows container.
            if metadata and 'workflows' in metadata:
                workflows = metadata[ 'workflows' ]
                folder_id, workflows_root_folder = container_util.build_workflows_folder( folder_id, workflows, repository_metadata, label='Workflows' )
                containers_dict[ 'workflows' ] = workflows_root_folder
        except Exception, e:
            log.debug( "Exception in build_repository_containers_for_tool_shed: %s" % str( e ) )
        finally:
            lock.release()
    return containers_dict
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
def can_add_to_key_rd_dicts( key_rd_dict, key_rd_dicts ):
    """Handle the case where an update to the changeset revision was done."""
    k = key_rd_dict.keys()[ 0 ]
    rd = key_rd_dict[ k ]
    partial_rd = rd[ 0:3 ]
    for kr_dict in key_rd_dicts:
        key = kr_dict.keys()[ 0 ]
        if key == k:
            val = kr_dict[ key ]
            for repository_dependency in val:
                if repository_dependency[ 0:3 ] == partial_rd:
                    return False
    return True
def can_generate_tool_dependency_metadata( root, metadata_dict ):
    """
    Make sure the combination of name, version and type (the type will be the value of elem.tag) of each root element tag in the tool_dependencies.xml
    file is defined in the <requirement> tag for at least one tool in the repository.
    """
    can_generate_dependency_metadata = False
    for elem in root:
        tool_dependency_type = elem.tag
        tool_dependency_version = elem.get( 'version', None )
        if tool_dependency_type == 'package':
            can_generate_dependency_metadata = False
            tool_dependency_name = elem.get( 'name', None )
            if tool_dependency_name and tool_dependency_version:
                for tool_dict in metadata_dict.get( 'tools', [] ):
                    requirements = tool_dict.get( 'requirements', [] )
                    for requirement_dict in requirements:
                        req_name = requirement_dict.get( 'name', None )
                        req_version = requirement_dict.get( 'version', None )
                        req_type = requirement_dict.get( 'type', None )
                        if req_name==tool_dependency_name and req_version==tool_dependency_version and req_type==tool_dependency_type:
                            can_generate_dependency_metadata = True
                            break
                    if requirements and not can_generate_dependency_metadata:
                        # We've discovered at least 1 combination of name, version and type that is not defined in the <requirement>
                        # tag for any tool in the repository.
                        break
                if not can_generate_dependency_metadata:
                    break
        elif tool_dependency_type == 'set_environment':
            # Here elem is something like: <set_environment version="1.0">
            for env_var_elem in elem:
                can_generate_dependency_metadata = False
                # <environment_variable name="R_SCRIPT_PATH" action="set_to">$REPOSITORY_INSTALL_DIR</environment_variable>
                env_var_name = env_var_elem.get( 'name', None )
                if env_var_name:
                    for tool_dict in metadata_dict.get( 'tools', [] ):
                        requirements = tool_dict.get( 'requirements', [] )
                        for requirement_dict in requirements:
                            # {"name": "R_SCRIPT_PATH", "type": "set_environment", "version": null}
                            req_name = requirement_dict.get( 'name', None )
                            req_type = requirement_dict.get( 'type', None )
                            if req_name==env_var_name and req_type==tool_dependency_type:
                                can_generate_dependency_metadata = True
                                break
                        if requirements and not can_generate_dependency_metadata:
                            # We've discovered at least 1 combination of name, version and type that is not defined in the <requirement>
                            # tag for any tool in the repository.
                            break
    return can_generate_dependency_metadata
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
            if options and isinstance( options, dynamic_options.DynamicOptions ):
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
def clean_repository_clone_url( repository_clone_url ):
    if repository_clone_url.find( '@' ) > 0:
        # We have an url that includes an authenticated user, something like:
        # http://test@bx.psu.edu:9009/repos/some_username/column
        items = repository_clone_url.split( '@' )
        tmp_url = items[ 1 ]
    elif repository_clone_url.find( '//' ) > 0:
        # We have an url that includes only a protocol, something like:
        # http://bx.psu.edu:9009/repos/some_username/column
        items = repository_clone_url.split( '//' )
        tmp_url = items[ 1 ]
    else:
        tmp_url = repository_clone_url
    return tmp_url
def clean_repository_metadata( trans, id, changeset_revisions ):
    # Delete all repository_metadata records associated with the repository that have a changeset_revision that is not in changeset_revisions.
    # We sometimes see multiple records with the same changeset revision value - no idea how this happens. We'll assume we can delete the older
    # records, so we'll order by update_time descending and delete records that have the same changeset_revision we come across later..
    changeset_revisions_checked = []
    for repository_metadata in trans.sa_session.query( trans.model.RepositoryMetadata ) \
                                               .filter( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ) ) \
                                               .order_by( trans.model.RepositoryMetadata.table.c.changeset_revision,
                                                          trans.model.RepositoryMetadata.table.c.update_time.desc() ):
        changeset_revision = repository_metadata.changeset_revision
        can_delete = changeset_revision in changeset_revisions_checked or changeset_revision not in changeset_revisions
        if can_delete:
            trans.sa_session.delete( repository_metadata )
            trans.sa_session.flush()
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
def compare_changeset_revisions( ancestor_changeset_revision, ancestor_metadata_dict, current_changeset_revision, current_metadata_dict ):
    """Compare the contents of two changeset revisions to determine if a new repository metadata revision should be created."""
    # The metadata associated with ancestor_changeset_revision is ancestor_metadata_dict.  This changeset_revision is an ancestor of
    # current_changeset_revision which is associated with current_metadata_dict.  A new repository_metadata record will be created only
    # when this method returns the string 'not equal and not subset'.
    ancestor_datatypes = ancestor_metadata_dict.get( 'datatypes', [] )
    ancestor_tools = ancestor_metadata_dict.get( 'tools', [] )
    ancestor_guids = [ tool_dict[ 'guid' ] for tool_dict in ancestor_tools ]
    ancestor_guids.sort()
    ancestor_repository_dependencies_dict = ancestor_metadata_dict.get( 'repository_dependencies', {} )
    ancestor_repository_dependencies = ancestor_repository_dependencies_dict.get( 'repository_dependencies', [] )
    ancestor_tool_dependencies = ancestor_metadata_dict.get( 'tool_dependencies', [] )
    ancestor_workflows = ancestor_metadata_dict.get( 'workflows', [] )
    current_datatypes = current_metadata_dict.get( 'datatypes', [] )
    current_tools = current_metadata_dict.get( 'tools', [] )
    current_guids = [ tool_dict[ 'guid' ] for tool_dict in current_tools ]
    current_guids.sort()
    current_repository_dependencies_dict = current_metadata_dict.get( 'repository_dependencies', {} )
    current_repository_dependencies = current_repository_dependencies_dict.get( 'repository_dependencies', [] )
    current_tool_dependencies = current_metadata_dict.get( 'tool_dependencies', [] ) 
    current_workflows = current_metadata_dict.get( 'workflows', [] )
    # Handle case where no metadata exists for either changeset.
    no_datatypes = not ancestor_datatypes and not current_datatypes
    no_repository_dependencies = not ancestor_repository_dependencies and not current_repository_dependencies
    # Note: we currently don't need to check tool_dependencies since we're checking for guids - tool_dependencies always require tools (currently).
    no_tool_dependencies = not ancestor_tool_dependencies and not current_tool_dependencies
    no_tools = not ancestor_guids and not current_guids
    no_workflows = not ancestor_workflows and not current_workflows
    if no_datatypes and no_repository_dependencies and no_tool_dependencies and no_tools and no_workflows:
        return 'no metadata'
    repository_dependency_comparison = compare_repository_dependencies( ancestor_repository_dependencies, current_repository_dependencies )
    workflow_comparison = compare_workflows( ancestor_workflows, current_workflows )
    datatype_comparison = compare_datatypes( ancestor_datatypes, current_datatypes )
    # Handle case where all metadata is the same.
    if ancestor_guids == current_guids and repository_dependency_comparison == 'equal' and workflow_comparison == 'equal' and datatype_comparison == 'equal':
        return 'equal'
    # Handle case where ancestor metadata is a subset of current metadata.
    repository_dependency_is_subset = repository_dependency_comparison in [ 'equal', 'subset' ]
    workflow_dependency_is_subset = workflow_comparison in [ 'equal', 'subset' ]
    datatype_is_subset = datatype_comparison in [ 'equal', 'subset' ]
    if repository_dependency_is_subset and workflow_dependency_is_subset and datatype_is_subset:
        is_subset = True
        for guid in ancestor_guids:
            if guid not in current_guids:
                is_subset = False
                break
        if is_subset:
            return 'subset'
    return 'not equal and not subset'
def compare_datatypes( ancestor_datatypes, current_datatypes ):
    """Determine if ancestor_datatypes is the same as or a subset of current_datatypes."""
    # Each datatype dict looks something like: {"dtype": "galaxy.datatypes.images:Image", "extension": "pdf", "mimetype": "application/pdf"}
    if len( ancestor_datatypes ) <= len( current_datatypes ):
        for ancestor_datatype in ancestor_datatypes:
            # Currently the only way to differentiate datatypes is by name.
            ancestor_datatype_dtype = ancestor_datatype[ 'dtype' ]
            ancestor_datatype_extension = ancestor_datatype[ 'extension' ]
            ancestor_datatype_mimetype = ancestor_datatype.get( 'mimetype', None )
            found_in_current = False
            for current_datatype in current_datatypes:
                if current_datatype[ 'dtype' ] == ancestor_datatype_dtype and \
                    current_datatype[ 'extension' ] == ancestor_datatype_extension and \
                    current_datatype.get( 'mimetype', None ) == ancestor_datatype_mimetype:
                    found_in_current = True
                    break
            if not found_in_current:
                return 'not equal and not subset'
        if len( ancestor_datatypes ) == len( current_datatypes ):
            return 'equal'
        else:
            return 'subset'
    return 'not equal and not subset'
def compare_repository_dependencies( ancestor_repository_dependencies, current_repository_dependencies ):
    """Determine if ancestor_repository_dependencies is the same as or a subset of current_repository_dependencies."""
    # The list of repository_dependencies looks something like: [["http://localhost:9009", "emboss_datatypes", "test", "ab03a2a5f407"]].
    # Create a string from each tuple in the list for easier comparison.
    if len( ancestor_repository_dependencies ) <= len( current_repository_dependencies ):
        for ancestor_tup in ancestor_repository_dependencies:
            ancestor_tool_shed, ancestor_repository_name, ancestor_repository_owner, ancestor_changeset_revision = ancestor_tup
            found_in_current = False
            for current_tup in current_repository_dependencies:
                current_tool_shed, current_repository_name, current_repository_owner, current_changeset_revision = current_tup
                if current_tool_shed == ancestor_tool_shed and \
                    current_repository_name == ancestor_repository_name and \
                    current_repository_owner == ancestor_repository_owner and \
                    current_changeset_revision == ancestor_changeset_revision:
                    found_in_current = True
                    break
            if not found_in_current:
                return 'not equal and not subset'
        if len( ancestor_repository_dependencies ) == len( current_repository_dependencies ):
            return 'equal'
        else:
            return 'subset'
    return 'not equal and not subset'
def compare_workflows( ancestor_workflows, current_workflows ):
    """Determine if ancestor_workflows is the same as current_workflows or if ancestor_workflows is a subset of current_workflows."""
    if len( ancestor_workflows ) <= len( current_workflows ):
        for ancestor_workflow_tup in ancestor_workflows:
            # ancestor_workflows is a list of tuples where each contained tuple is
            # [ <relative path to the .ga file in the repository>, <exported workflow dict> ]
            ancestor_workflow_dict = ancestor_workflow_tup[1]
            # Currently the only way to differentiate workflows is by name.
            ancestor_workflow_name = ancestor_workflow_dict[ 'name' ]
            num_ancestor_workflow_steps = len( ancestor_workflow_dict[ 'steps' ] )
            found_in_current = False
            for current_workflow_tup in current_workflows:
                current_workflow_dict = current_workflow_tup[1]
                # Assume that if the name and number of steps are euqal,
                # then the workflows are the same.  Of course, this may
                # not be true...
                if current_workflow_dict[ 'name' ] == ancestor_workflow_name and len( current_workflow_dict[ 'steps' ] ) == num_ancestor_workflow_steps:
                    found_in_current = True
                    break
            if not found_in_current:
                return 'not equal and not subset'
        if len( ancestor_workflows ) == len( current_workflows ):
            return 'equal'
        else:
            return 'subset'
    return 'not equal and not subset'
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
def copy_disk_sample_files_to_dir( trans, repo_files_dir, dest_path ):
    """Copy all files currently on disk that end with the .sample extension to the directory to which dest_path refers."""
    sample_files = []
    for root, dirs, files in os.walk( repo_files_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name.endswith( '.sample' ):
                    relative_path = os.path.join( root, name )
                    copy_sample_file( trans.app, relative_path, dest_path=dest_path )
                    sample_files.append( name )
    return sample_files
def copy_file_from_manifest( repo, ctx, filename, dir ):
    """Copy the latest version of the file named filename from the repository manifest to the directory to which dir refers."""
    for changeset in reversed_upper_bounded_changelog( repo, ctx ):
        changeset_ctx = repo.changectx( changeset )
        fctx = get_file_context_from_ctx( changeset_ctx, filename )
        if fctx and fctx not in [ 'DELETED' ]:
            file_path = os.path.join( dir, filename )
            fh = open( file_path, 'wb' )
            fh.write( fctx.data() )
            fh.close()
            return file_path
    return None
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
def create_repo_info_dict( trans, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_name=None, repository=None,
                           repository_metadata=None, metadata=None, repository_dependencies=None ):
    """
    Return a dictionary that includes all of the information needed to install a repository into a local Galaxy instance.  The dictionary will also
    contain the recursive list of repository dependencies defined for the repository, as well as the defined tool dependencies.  
    
    This method is called from Galaxy from two places:
    1. During the tool shed repository installation process (via the tool shed's get_repository_information() method)- in this case both the received
    repository and repository_metadata will be objects.
    2. When a tool shed repository that was uninstalled from a Galaxy instance is being re-installed - in this case, both repository and
    repository_metadata will be None, but metadata will be the tool_shed_repository metadata on the Galaxy side, and the repository_dependencies will
    be an object previously retrieved from the tool shed.
    """
    repo_info_dict = {}
    repository = get_repository_by_name_and_owner( trans, repository_name, repository_owner )
    if trans.webapp.name == 'community':
        # We're in the tool shed.
        repository_metadata = get_repository_metadata_by_changeset_revision( trans, trans.security.encode_id( repository.id ), changeset_revision )
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                # Get a dictionary of all repositories upon which the contents of the received repository depends.
                repository_dependencies = get_repository_dependencies_for_changeset_revision( trans=trans,
                                                                                              repository=repository,
                                                                                              repository_metadata=repository_metadata,
                                                                                              toolshed_base_url=str( url_for( '/', qualified=True ) ).rstrip( '/' ),
                                                                                              key_rd_dicts_to_be_processed=None,
                                                                                              all_repository_dependencies=None,
                                                                                              handled_key_rd_dicts=None,
                                                                                              circular_repository_dependencies=None )
    # Cast unicode to string.
    repo_info_dict[ str( repository.name ) ] = ( str( repository.description ),
                                                 str( repository_clone_url ),
                                                 str( changeset_revision ),
                                                 str( ctx_rev ),
                                                 str( repository_owner ),
                                                 repository_dependencies,
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
def generate_datatypes_metadata( datatypes_config, metadata_dict ):
    """Update the received metadata_dict with information from the parsed datatypes_config."""
    tree = ElementTree.parse( datatypes_config )
    root = tree.getroot()
    ElementInclude.include( root )
    repository_datatype_code_files = []
    datatype_files = root.find( 'datatype_files' )
    if datatype_files:
        for elem in datatype_files.findall( 'datatype_file' ):
            name = elem.get( 'name', None )
            repository_datatype_code_files.append( name )
        metadata_dict[ 'datatype_files' ] = repository_datatype_code_files
    datatypes = []
    registration = root.find( 'registration' )
    if registration:
        for elem in registration.findall( 'datatype' ):
            datatypes_dict = {}
            display_in_upload = elem.get( 'display_in_upload', None )
            if display_in_upload:
                datatypes_dict[ 'display_in_upload' ] = display_in_upload
            dtype = elem.get( 'type', None )
            if dtype:
                datatypes_dict[ 'dtype' ] = dtype
            extension = elem.get( 'extension', None )
            if extension:
                datatypes_dict[ 'extension' ] = extension
            max_optional_metadata_filesize = elem.get( 'max_optional_metadata_filesize', None )
            if max_optional_metadata_filesize:
                datatypes_dict[ 'max_optional_metadata_filesize' ] = max_optional_metadata_filesize
            mimetype = elem.get( 'mimetype', None )
            if mimetype:
                datatypes_dict[ 'mimetype' ] = mimetype
            subclass = elem.get( 'subclass', None )
            if subclass:
                datatypes_dict[ 'subclass' ] = subclass
            if datatypes_dict:
                datatypes.append( datatypes_dict )
        if datatypes:
            metadata_dict[ 'datatypes' ] = datatypes
    return metadata_dict
def generate_environment_dependency_metadata( elem, tool_dependencies_dict ):
    """The value of env_var_name must match the value of the "set_environment" type in the tool config's <requirements> tag set."""
    requirements_dict = {}
    for env_elem in elem:
        env_name = env_elem.get( 'name', None )
        if env_name:
            requirements_dict [ 'name' ] = env_name
            requirements_dict [ 'type' ] = 'environment variable'
        if requirements_dict:
            if 'set_environment' in tool_dependencies_dict:
                tool_dependencies_dict[ 'set_environment' ].append( requirements_dict )
            else:
                tool_dependencies_dict[ 'set_environment' ] = [ requirements_dict ]
    return tool_dependencies_dict
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
            message += "Metadata may have been defined for some items in revision '%s'.  " % str( repository.tip( trans.app ) )
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
def generate_metadata_for_changeset_revision( app, repository, repository_clone_url, shed_config_dict=None, relative_install_dir=None, repository_files_dir=None,
                                              resetting_all_metadata_on_repository=False, updating_installed_repository=False, persist=False ):
    """
    Generate metadata for a repository using it's files on disk.  To generate metadata for changeset revisions older than the repository tip,
    the repository will have been cloned to a temporary location and updated to a specified changeset revision to access that changeset revision's
    disk files, so the value of repository_files_dir will not always be repository.repo_path( app ) (it could be an absolute path to a temporary
    directory containing a clone).  If it is an absolute path, the value of relative_install_dir must contain repository.repo_path( app ).
    
    The value of persist will be True when the installed repository contains a valid tool_data_table_conf.xml.sample file, in which case the entries
    should ultimately be persisted to the file referred to by app.config.shed_tool_data_table_config.
    """
    if shed_config_dict is None:
        shed_config_dict = {}
    if updating_installed_repository:
        # Keep the original tool shed repository metadata if setting metadata on a repository installed into a local Galaxy instance for which 
        # we have pulled updates.
        original_repository_metadata = repository.metadata
    else:
        original_repository_metadata = None
    readme_file_names = get_readme_file_names( repository.name )
    metadata_dict = { 'shed_config_filename' : shed_config_dict.get( 'config_filename' ) }
    readme_files = []
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
            new_table_elems, error_message = app.tool_data_tables.add_new_entries_from_config_file( config_filename=sample_file,
                                                                                                    tool_data_path=app.config.tool_data_path,
                                                                                                    shed_tool_data_table_config=app.config.shed_tool_data_table_config,
                                                                                                    persist=persist )
            if error_message:
                invalid_file_tups.append( ( filename, error_message ) )
    for root, dirs, files in os.walk( files_dir ):
        if root.find( '.hg' ) < 0 and root.find( 'hgrc' ) < 0:
            if '.hg' in dirs:
                dirs.remove( '.hg' )
            for name in files:
                # See if we have a repository dependencies defined.
                if name == 'repository_dependencies.xml':
                    path_to_repository_dependencies_config = os.path.join( root, name )
                    metadata_dict, error_message = generate_repository_dependency_metadata( app, path_to_repository_dependencies_config, metadata_dict )
                    if error_message:
                        invalid_file_tups.append( ( name, error_message ) )
                # See if we have one or more READ_ME files.
                elif name.lower() in readme_file_names:
                    relative_path_to_readme = get_relative_path_to_repository_file( root,
                                                                                    name,
                                                                                    relative_install_dir,
                                                                                    work_dir,
                                                                                    shed_config_dict,
                                                                                    resetting_all_metadata_on_repository )
                    readme_files.append( relative_path_to_readme )
                # See if we have a tool config.
                elif name not in NOT_TOOL_CONFIGS and name.endswith( '.xml' ):
                    full_path = str( os.path.abspath( os.path.join( root, name ) ) )
                    if os.path.getsize( full_path ) > 0:
                        if not ( checkers.check_binary( full_path ) or checkers.check_image( full_path ) or checkers.check_gzip( full_path )[ 0 ]
                                 or checkers.check_bz2( full_path )[ 0 ] or checkers.check_zip( full_path ) ):
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
                                    invalid_files_and_errors_tups = check_tool_input_params( app, files_dir, name, tool, sample_file_copy_paths )
                                    can_set_metadata = True
                                    for tup in invalid_files_and_errors_tups:
                                        if name in tup:
                                            can_set_metadata = False
                                            invalid_tool_configs.append( name )
                                            break
                                    if can_set_metadata:
                                        relative_path_to_tool_config = get_relative_path_to_repository_file( root,
                                                                                                             name,
                                                                                                             relative_install_dir,
                                                                                                             work_dir,
                                                                                                             shed_config_dict,
                                                                                                             resetting_all_metadata_on_repository )
                                        
                                        
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
                        exported_workflow_dict = json.from_json_string( workflow_text )
                        if 'a_galaxy_workflow' in exported_workflow_dict and exported_workflow_dict[ 'a_galaxy_workflow' ] == 'true':
                            metadata_dict = generate_workflow_metadata( relative_path, exported_workflow_dict, metadata_dict )
    if readme_files:
        metadata_dict[ 'readme_files' ] = readme_files
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
def generate_package_dependency_metadata( elem, tool_dependencies_dict ):
    """The value of package_name must match the value of the "package" type in the tool config's <requirements> tag set."""
    requirements_dict = {}
    package_name = elem.get( 'name', None )
    package_version = elem.get( 'version', None )
    if package_name and package_version:
        dependency_key = '%s/%s' % ( package_name, package_version )
        requirements_dict [ 'name' ] = package_name
        requirements_dict [ 'version' ] = package_version
        requirements_dict [ 'type' ] = 'package'
        for sub_elem in elem:
            if sub_elem.tag == 'readme':
                requirements_dict[ 'readme' ] = sub_elem.text
    if requirements_dict:
        tool_dependencies_dict[ dependency_key ] = requirements_dict
    return tool_dependencies_dict
def generate_repository_dependency_metadata( app, repository_dependencies_config, metadata_dict ):
    """Generate a repository dependencies dictionary based on valid information defined in the received repository_dependencies_config."""
    repository_dependencies_tups = []
    error_message = ''
    try:
        # Make sure we're looking at a valid repository_dependencies.xml file.
        tree = util.parse_xml( repository_dependencies_config )
        root = tree.getroot()
        is_valid = root.tag == 'repositories'
    except Exception, e:
        error_message = "Error parsing %s, exception: %s" % ( repository_dependencies_config, str( e ) )
        log.debug( error_message )
        is_valid = False
    if is_valid:
        sa_session = app.model.context.current
        for repository_elem in root.findall( 'repository' ):
            toolshed = repository_elem.attrib[ 'toolshed' ]
            name = repository_elem.attrib[ 'name' ]
            owner = repository_elem.attrib[ 'owner']
            changeset_revision = repository_elem.attrib[ 'changeset_revision' ]
            user = None
            repository = None
            if tool_shed_is_this_tool_shed( toolshed ):
                try:
                    user = sa_session.query( app.model.User ) \
                                     .filter( app.model.User.table.c.username == owner ) \
                                     .one()
                except Exception, e:
                    error_message = "Invalid owner %s defined for repository %s.  Repository dependencies will be ignored." % ( owner, name )
                    log.debug( error_message )
                    return metadata_dict, error_message
                if user:
                    try:
                        repository = sa_session.query( app.model.Repository ) \
                                               .filter( and_( app.model.Repository.table.c.name == name,
                                                              app.model.Repository.table.c.user_id == user.id ) ) \
                                               .first()
                    except:
                        error_message = "Invalid name %s or owner %s defined for repository.  Repository dependencies will be ignored." % ( name, owner )
                        log.debug( error_message )
                        return metadata_dict, error_message
                    if repository:
                        repository_dependencies_tup = ( toolshed, name, owner, changeset_revision )
                        if repository_dependencies_tup not in repository_dependencies_tups:
                            repository_dependencies_tups.append( repository_dependencies_tup )
                    else:
                        error_message = "Invalid name %s or owner %s defined for repository.  Repository dependencies will be ignored." % ( name, owner )
                        log.debug( error_message )
                        return metadata_dict, error_message
                else:
                    error_message = "Invalid owner %s defined for owner of repository %s.  Repository dependencies will be ignored." % ( owner, name )
                    log.debug( error_message )
                    return metadata_dict, error_message
            else:
                # Repository dependencies are currentlhy supported within a single tool shed.
                error_message = "Invalid tool shed %s defined for repository %s.  " % ( toolshed, name )
                error_message += "Repository dependencies are currently supported within a single tool shed, so your definition will be ignored."
                log.debug( error_message )
                return metadata_dict, error_message
        if repository_dependencies_tups:
            repository_dependencies_dict = dict( description=root.get( 'description' ),
                                                 repository_dependencies=repository_dependencies_tups )
            metadata_dict[ 'repository_dependencies' ] = repository_dependencies_dict
    return metadata_dict, error_message
def generate_tool_dependency_metadata( app, repository, tool_dependencies_config, metadata_dict, original_repository_metadata=None ):
    """
    If the combination of name, version and type of each element is defined in the <requirement> tag for at least one tool in the repository,
    then update the received metadata_dict with information from the parsed tool_dependencies_config.
    """
    if original_repository_metadata:
        # Keep a copy of the original tool dependencies dictionary in the metadata.
        original_tool_dependencies_dict = original_repository_metadata.get( 'tool_dependencies', None )
    else:
        original_tool_dependencies_dict = None
    try:
        tree = ElementTree.parse( tool_dependencies_config )
    except Exception, e:
        log.debug( "Exception attempting to parse tool_dependencies.xml: %s" %str( e ) )
        return metadata_dict
    root = tree.getroot()
    ElementInclude.include( root )
    tool_dependencies_dict = {}
    if can_generate_tool_dependency_metadata( root, metadata_dict ):
        for elem in root:
            if elem.tag == 'package':
                tool_dependencies_dict = generate_package_dependency_metadata( elem, tool_dependencies_dict )
            elif elem.tag == 'set_environment':
                tool_dependencies_dict = generate_environment_dependency_metadata( elem, tool_dependencies_dict )
            # Handle tool dependency installation via other means here (future).
        if tool_dependencies_dict:
            metadata_dict[ 'tool_dependencies' ] = tool_dependencies_dict
    else:
        log.debug( "Name, version and type from the <requirement> tag does not match the information in the tool_dependencies.xml file. Tool dependencies will be ignored." )
    if tool_dependencies_dict:
        if original_tool_dependencies_dict:
            # We're generating metadata on an update pulled to a tool shed repository installed into a Galaxy instance, so handle changes to
            # tool dependencies appropriately.
            handle_existing_tool_dependencies_that_changed_in_update( app, repository, original_tool_dependencies_dict, tool_dependencies_dict )
        metadata_dict[ 'tool_dependencies' ] = tool_dependencies_dict
    return metadata_dict
def generate_tool_guid( repository_clone_url, tool ):
    """
    Generate a guid for the installed tool.  It is critical that this guid matches the guid for
    the tool in the Galaxy tool shed from which it is being installed.  The form of the guid is    
    <tool shed host>/repos/<repository owner>/<repository name>/<tool id>/<tool version>
    """
    tmp_url = clean_repository_clone_url( repository_clone_url )
    return '%s/%s/%s' % ( tmp_url, tool.id, tool.version )
def generate_tool_metadata( tool_config, tool, repository_clone_url, metadata_dict ):
    """Update the received metadata_dict with changes that have been applied to the received tool."""
    # Generate the guid
    guid = generate_tool_guid( repository_clone_url, tool )
    # Handle tool.requirements.
    tool_requirements = []
    for tr in tool.requirements:
        requirement_dict = dict( name=tr.name,
                                 type=tr.type,
                                 version=tr.version )
        tool_requirements.append( requirement_dict )
    # Handle tool.tests.
    tool_tests = []
    if tool.tests:
        for ttb in tool.tests:
            required_files = []
            for required_file in ttb.required_files:
                value, extra = required_file
                required_files.append( ( value ) )
            inputs = []
            for input in ttb.inputs:
                name, value, extra = input
                inputs.append( ( name, value ) )
            outputs = []
            for output in ttb.outputs:
                name, file_name, extra = output
                outputs.append( ( name, strip_path( file_name ) if file_name else None ) )
            test_dict = dict( name=ttb.name,
                              required_files=required_files,
                              inputs=inputs,
                              outputs=outputs )
            tool_tests.append( test_dict )
    tool_dict = dict( id=tool.id,
                      guid=guid,
                      name=tool.name,
                      version=tool.version,
                      description=tool.description,
                      version_string_cmd = tool.version_string_cmd,
                      tool_config=tool_config,
                      requirements=tool_requirements,
                      tests=tool_tests )
    if 'tools' in metadata_dict:
        metadata_dict[ 'tools' ].append( tool_dict )
    else:
        metadata_dict[ 'tools' ] = [ tool_dict ]
    return metadata_dict
def generate_workflow_metadata( relative_path, exported_workflow_dict, metadata_dict ):
    """Update the received metadata_dict with changes that have been applied to the received exported_workflow_dict."""
    if 'workflows' in metadata_dict:
        metadata_dict[ 'workflows' ].append( ( relative_path, exported_workflow_dict ) )
    else:
        metadata_dict[ 'workflows' ] = [ ( relative_path, exported_workflow_dict ) ]
    return metadata_dict
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
def get_ctx_file_path_from_manifest( filename, repo, changeset_revision ):
    """Get the ctx file path for the latest revision of filename from the repository manifest up to the value of changeset_revision."""
    stripped_filename = strip_path( filename )
    for changeset in reversed_upper_bounded_changelog( repo, changeset_revision ):
        manifest_changeset_revision = str( repo.changectx( changeset ) )
        manifest_ctx = repo.changectx( changeset )
        for ctx_file in manifest_ctx.files():
            ctx_file_name = strip_path( ctx_file )
            if ctx_file_name == stripped_filename:
                return manifest_ctx, ctx_file
    return None, None
def get_key_for_repository_changeset_revision( toolshed_base_url, repository, repository_metadata ):
    return container_util.generate_repository_dependencies_key_for_repository( toolshed_base_url=toolshed_base_url,
                                                                               repository_name=repository.name,
                                                                               repository_owner=repository.user.username,
                                                                               changeset_revision=repository_metadata.changeset_revision )
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
def get_list_of_copied_sample_files( repo, ctx, dir ):
    """
    Find all sample files (files in the repository with the special .sample extension) in the reversed repository manifest up to ctx.  Copy
    each discovered file to dir and return the list of filenames.  If a .sample file was added in a changeset and then deleted in a later
    changeset, it will be returned in the deleted_sample_files list.  The caller will set the value of app.config.tool_data_path to dir in
    order to load the tools and generate metadata for them.
    """
    deleted_sample_files = []
    sample_files = []
    for changeset in reversed_upper_bounded_changelog( repo, ctx ):
        changeset_ctx = repo.changectx( changeset )
        for ctx_file in changeset_ctx.files():
            ctx_file_name = strip_path( ctx_file )
            # If we decide in the future that files deleted later in the changelog should not be used, we can use the following if statement.
            # if ctx_file_name.endswith( '.sample' ) and ctx_file_name not in sample_files and ctx_file_name not in deleted_sample_files:
            if ctx_file_name.endswith( '.sample' ) and ctx_file_name not in sample_files:
                fctx = get_file_context_from_ctx( changeset_ctx, ctx_file )
                if fctx in [ 'DELETED' ]:
                    # Since the possibly future used if statement above is commented out, the same file that was initially added will be
                    # discovered in an earlier changeset in the change log and fall through to the else block below.  In other words, if
                    # a file named blast2go.loc.sample was added in change set 0 and then deleted in changeset 3, the deleted file in changeset
                    # 3 will be handled here, but the later discovered file in changeset 0 will be handled in the else block below.  In this
                    # way, the file contents will always be found for future tools even though the file was deleted.
                    if ctx_file_name not in deleted_sample_files:
                        deleted_sample_files.append( ctx_file_name )
                else:
                    sample_files.append( ctx_file_name )
                    tmp_ctx_file_name = os.path.join( dir, ctx_file_name.replace( '.sample', '' ) )
                    fh = open( tmp_ctx_file_name, 'wb' )
                    fh.write( fctx.data() )
                    fh.close()
    return sample_files, deleted_sample_files
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
def get_next_downloadable_changeset_revision( repository, repo, after_changeset_revision ):
    """
    Return the installable changeset_revision in the repository changelog after to the changeset to which after_changeset_revision
    refers.  If there isn't one, return None.
    """
    changeset_revisions = get_ordered_downloadable_changeset_revisions( repository, repo )
    if len( changeset_revisions ) == 1:
        changeset_revision = changeset_revisions[ 0 ]
        if changeset_revision == after_changeset_revision:
            return None
    found_after_changeset_revision = False
    for changeset in repo.changelog:
        changeset_revision = str( repo.changectx( changeset ) )
        if found_after_changeset_revision:
            if changeset_revision in changeset_revisions:
                return changeset_revision
        elif not found_after_changeset_revision and changeset_revision == after_changeset_revision:
            # We've found the changeset in the changelog for which we need to get the next downloadable changset.
            found_after_changeset_revision = True
    return None
def get_ordered_downloadable_changeset_revisions( repository, repo ):
    """Return an ordered list of changeset_revisions defined by a repository changelog."""
    changeset_tups = []
    for repository_metadata in repository.downloadable_revisions:
        changeset_revision = repository_metadata.changeset_revision
        ctx = get_changectx_for_changeset( repo, changeset_revision )
        if ctx:
            rev = '%04d' % ctx.rev()
        else:
            rev = '-1'
        changeset_tups.append( ( rev, changeset_revision ) )
    sorted_changeset_tups = sorted( changeset_tups )
    sorted_changeset_revisions = [ changeset_tup[ 1 ] for changeset_tup in sorted_changeset_tups ]
    return sorted_changeset_revisions
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
def get_previous_downloadable_changset_revision( repository, repo, before_changeset_revision ):
    """
    Return the installable changeset_revision in the repository changelog prior to the changeset to which before_changeset_revision
    refers.  If there isn't one, return the hash value of an empty repository changelog, INITIAL_CHANGELOG_HASH.
    """
    changeset_revisions = get_ordered_downloadable_changeset_revisions( repository, repo )
    if len( changeset_revisions ) == 1:
        changeset_revision = changeset_revisions[ 0 ]
        if changeset_revision == before_changeset_revision:
            return INITIAL_CHANGELOG_HASH
        return changeset_revision
    previous_changeset_revision = None
    for changeset_revision in changeset_revisions:
        if changeset_revision == before_changeset_revision:
            if previous_changeset_revision:
                return previous_changeset_revision
            else:
                # Return the hash value of an empty repository changelog - note that this will not be a valid changeset revision.
                return INITIAL_CHANGELOG_HASH
        else:
            previous_changeset_revision = changeset_revision
def get_readme_file_names( repository_name ):
    readme_files = [ 'readme', 'read_me', 'install' ]
    valid_filenames = [ r for r in readme_files ]
    for r in readme_files:
        valid_filenames.append( '%s.txt' % r )
    valid_filenames.append( '%s.txt' % repository_name )
    return valid_filenames
def get_repository_by_name_and_owner( trans, name, owner ):
    """Get a repository from the database via name and owner"""
    if trans.webapp.name == 'galaxy':
        return trans.sa_session.query( trans.model.ToolShedRepository ) \
                                 .filter( and_( trans.model.ToolShedRepository.table.c.name == name,
                                                trans.model.ToolShedRepository.table.c.owner == owner ) ) \
                                 .first()
    # We're in the tool shed.
    user = get_user_by_username( trans, owner )
    return trans.sa_session.query( trans.model.Repository ) \
                             .filter( and_( trans.model.Repository.table.c.name == name,
                                            trans.model.Repository.table.c.user_id == user.id ) ) \
                             .first()
def get_repository_dependencies_for_changeset_revision( trans, repository, repository_metadata, toolshed_base_url,
                                                        key_rd_dicts_to_be_processed=None, all_repository_dependencies=None,
                                                        handled_key_rd_dicts=None, circular_repository_dependencies=None ):
    """
    Return a dictionary of all repositories upon which the contents of the received repository_metadata record depend.  The dictionary keys
    are name-spaced values consisting of toolshed_base_url/repository_name/repository_owner/changeset_revision and the values are lists of
    repository_dependency tuples consisting of ( toolshed_base_url, repository_name, repository_owner, changeset_revision ).  This method
    ensures that all required repositories to the nth degree are returned.
    """
    if handled_key_rd_dicts is None:
        handled_key_rd_dicts = []
    if all_repository_dependencies is None:
        all_repository_dependencies = {}
    if key_rd_dicts_to_be_processed is None:
        key_rd_dicts_to_be_processed = []
    if circular_repository_dependencies is None:
        circular_repository_dependencies = []
    # Assume the current repository does not have repository dependencies defined for it.
    current_repository_key = None
    metadata = repository_metadata.metadata
    if metadata and 'repository_dependencies' in metadata:
        current_repository_key = get_key_for_repository_changeset_revision( toolshed_base_url, repository, repository_metadata )
        repository_dependencies_dict = metadata[ 'repository_dependencies' ]
        if not all_repository_dependencies:
            all_repository_dependencies = initialize_all_repository_dependencies( current_repository_key,
                                                                                  repository_dependencies_dict,
                                                                                  all_repository_dependencies )
        # Handle the repository dependencies defined in the current repository, if any, and populate the various repository dependency objects for
        # this round of processing.
        current_repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts, all_repository_dependencies = \
            populate_repository_dependency_objects_for_processing( trans,
                                                                   current_repository_key,
                                                                   repository_dependencies_dict,
                                                                   key_rd_dicts_to_be_processed,
                                                                   handled_key_rd_dicts,
                                                                   circular_repository_dependencies,
                                                                   all_repository_dependencies )
    if current_repository_key:
        if current_repository_key_rd_dicts:
            # There should be only a single current_repository_key_rd_dict in this list.
            current_repository_key_rd_dict = current_repository_key_rd_dicts[ 0 ]
            # Handle circular repository dependencies.
            if not in_circular_repository_dependencies( current_repository_key_rd_dict, circular_repository_dependencies ):
                if current_repository_key in all_repository_dependencies:
                    handle_current_repository_dependency( trans,
                                                          current_repository_key,
                                                          key_rd_dicts_to_be_processed,
                                                          all_repository_dependencies,
                                                          handled_key_rd_dicts,
                                                          circular_repository_dependencies )
            elif key_rd_dicts_to_be_processed:
                handle_next_repository_dependency( trans, key_rd_dicts_to_be_processed, all_repository_dependencies, handled_key_rd_dicts, circular_repository_dependencies )
        elif key_rd_dicts_to_be_processed:
            handle_next_repository_dependency( trans, key_rd_dicts_to_be_processed, all_repository_dependencies, handled_key_rd_dicts, circular_repository_dependencies )
    elif key_rd_dicts_to_be_processed:
        handle_next_repository_dependency( trans, key_rd_dicts_to_be_processed, all_repository_dependencies, handled_key_rd_dicts, circular_repository_dependencies )
    return all_repository_dependencies
def get_repository_dependency_as_key( repository_dependency ):
    return container_util.generate_repository_dependencies_key_for_repository( repository_dependency[ 0 ],
                                                                               repository_dependency[ 1 ],
                                                                               repository_dependency[ 2 ],
                                                                               repository_dependency[ 3] )
def get_repository_file_contents( file_path ):
    if checkers.is_gzip( file_path ):
        safe_str = to_safe_string( '\ngzip compressed file\n' )
    elif checkers.is_bz2( file_path ):
        safe_str = to_safe_string( '\nbz2 compressed file\n' )
    elif checkers.check_zip( file_path ):
        safe_str = to_safe_string( '\nzip compressed file\n' )
    elif checkers.check_binary( file_path ):
        safe_str = to_safe_string( '\nBinary file\n' )
    else:
        safe_str = ''
        for i, line in enumerate( open( file_path ) ):
            safe_str = '%s%s' % ( safe_str, to_safe_string( line ) )
            if len( safe_str ) > MAX_CONTENT_SIZE:
                large_str = '\nFile contents truncated because file size is larger than maximum viewing size of %s\n' % util.nice_size( MAX_CONTENT_SIZE )
                safe_str = '%s%s' % ( safe_str, to_safe_string( large_str ) )
                break
    return safe_str
def get_repository_files( trans, folder_path ):
    contents = []
    for item in os.listdir( folder_path ):
        # Skip .hg directories
        if str( item ).startswith( '.hg' ):
            continue
        if os.path.isdir( os.path.join( folder_path, item ) ):
            # Append a '/' character so that our jquery dynatree will function properly.
            item = '%s/' % item
        contents.append( item )
    if contents:
        contents.sort()
    return contents
def get_repository_in_tool_shed( trans, id ):
    """Get a repository on the tool shed side from the database via id"""
    return trans.sa_session.query( trans.model.Repository ).get( trans.security.decode_id( id ) )
def get_repository_metadata_by_changeset_revision( trans, id, changeset_revision ):
    """Get metadata for a specified repository change set from the database."""
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
def get_repository_metadata_by_repository_id_changset_revision( trans, id, changeset_revision ):
    """Get a specified metadata record for a specified repository."""
    return trans.sa_session.query( trans.model.RepositoryMetadata ) \
                           .filter( and_( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ),
                                          trans.model.RepositoryMetadata.table.c.changeset_revision == changeset_revision ) ) \
                           .first()
def get_relative_path_to_repository_file( root, name, relative_install_dir, work_dir, shed_config_dict, resetting_all_metadata_on_repository ):
    if resetting_all_metadata_on_repository:
        full_path_to_file = os.path.join( root, name )
        stripped_path_to_file = full_path_to_file.replace( work_dir, '' )
        if stripped_path_to_file.startswith( '/' ):
            stripped_path_to_file = stripped_path_to_file[ 1: ]
        relative_path_to_file = os.path.join( relative_install_dir, stripped_path_to_file )
    else:
        relative_path_to_file = os.path.join( root, name )
        if relative_install_dir and \
            shed_config_dict.get( 'tool_path' ) and \
            relative_path_to_file.startswith( os.path.join( shed_config_dict.get( 'tool_path' ), relative_install_dir ) ):
            relative_path_to_file = relative_path_to_file[ len( shed_config_dict.get( 'tool_path' ) ) + 1: ]
    return relative_path_to_file
def get_sample_files_from_disk( repository_files_dir, tool_path=None, relative_install_dir=None, resetting_all_metadata_on_repository=False ):
    if resetting_all_metadata_on_repository:
        # Keep track of the location where the repository is temporarily cloned so that we can strip it when setting metadata.
        work_dir = repository_files_dir
    sample_file_metadata_paths = []
    sample_file_copy_paths = []
    for root, dirs, files in os.walk( repository_files_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name.endswith( '.sample' ):
                    if resetting_all_metadata_on_repository:
                        full_path_to_sample_file = os.path.join( root, name )
                        stripped_path_to_sample_file = full_path_to_sample_file.replace( work_dir, '' )
                        if stripped_path_to_sample_file.startswith( '/' ):
                            stripped_path_to_sample_file = stripped_path_to_sample_file[ 1: ]
                        relative_path_to_sample_file = os.path.join( relative_install_dir, stripped_path_to_sample_file )
                        if os.path.exists( relative_path_to_sample_file ):
                            sample_file_copy_paths.append( relative_path_to_sample_file )
                        else:
                            sample_file_copy_paths.append( full_path_to_sample_file )
                    else:
                        relative_path_to_sample_file = os.path.join( root, name )
                        sample_file_copy_paths.append( relative_path_to_sample_file )
                        if tool_path and relative_install_dir:
                            if relative_path_to_sample_file.startswith( os.path.join( tool_path, relative_install_dir ) ):
                                relative_path_to_sample_file = relative_path_to_sample_file[ len( tool_path ) + 1 :]
                        sample_file_metadata_paths.append( relative_path_to_sample_file )
    return sample_file_metadata_paths, sample_file_copy_paths
def get_tool_shed_from_clone_url( repository_clone_url ):
    tmp_url = clean_repository_clone_url( repository_clone_url )
    return tmp_url.split( 'repos' )[ 0 ].rstrip( '/' )
def get_updated_changeset_revisions_for_repository_dependencies( trans, key_rd_dicts ):
    updated_key_rd_dicts = []
    for key_rd_dict in key_rd_dicts:
        key = key_rd_dict.keys()[ 0 ]
        repository_dependency = key_rd_dict[ key ]
        toolshed, name, owner, changeset_revision = repository_dependency
        if tool_shed_is_this_tool_shed( toolshed ):
            repository = get_repository_by_name_and_owner( trans, name, owner )
            repository_metadata = get_repository_metadata_by_repository_id_changset_revision( trans,
                                                                                              trans.security.encode_id( repository.id ),
                                                                                              changeset_revision )
            if repository_metadata:
                # The repository changeset_revision is installable, so no updates are available.
                new_key_rd_dict = {}
                new_key_rd_dict[ key ] = repository_dependency
                updated_key_rd_dicts.append( key_rd_dict )
            else:
                # The repository changeset_revision is no longer installable, so see if there's been an update.
                repo_dir = repository.repo_path( trans.app )
                repo = hg.repository( get_configured_ui(), repo_dir )
                changeset_revision = get_next_downloadable_changeset_revision( repository, repo, changeset_revision )
                repository_metadata = get_repository_metadata_by_repository_id_changset_revision( trans,
                                                                                                  trans.security.encode_id( repository.id ),
                                                                                                  changeset_revision )
                if repository_metadata:
                    new_key_rd_dict = {}
                    new_key_rd_dict[ key ] = [ toolshed, name, owner, repository_metadata.changeset_revision ]
                    # We have the updated changset revision.
                    updated_key_rd_dicts.append( new_key_rd_dict )
    return updated_key_rd_dicts
def get_url_from_repository_tool_shed( app, repository ):
    """
    The stored value of repository.tool_shed is something like: toolshed.g2.bx.psu.edu.  We need the URL to this tool shed, which is
    something like: http://toolshed.g2.bx.psu.edu/.
    """
    for shed_name, shed_url in app.tool_shed_registry.tool_sheds.items():
        if shed_url.find( repository.tool_shed ) >= 0:
            if shed_url.endswith( '/' ):
                shed_url = shed_url.rstrip( '/' )
            return shed_url
    # The tool shed from which the repository was originally installed must no longer be configured in tool_sheds_conf.xml.
    return None
def get_user_by_username( trans, username ):
    """Get a user from the database by username"""
    return trans.sa_session.query( trans.model.User ) \
                           .filter( trans.model.User.table.c.username == username ) \
                           .one()
def handle_circular_repository_dependency( repository_key, repository_dependency, circular_repository_dependencies, handled_key_rd_dicts, all_repository_dependencies ):
    all_repository_dependencies_root_key = all_repository_dependencies[ 'root_key' ]
    repository_dependency_as_key = get_repository_dependency_as_key( repository_dependency )
    repository_key_as_repository_dependency = repository_key.split( container_util.STRSEP )
    update_circular_repository_dependencies( repository_key,
                                             repository_dependency,
                                             all_repository_dependencies[ repository_dependency_as_key ],
                                             circular_repository_dependencies )
    if all_repository_dependencies_root_key != repository_dependency_as_key:
        all_repository_dependencies[ repository_key ] = [ repository_dependency ]
    return circular_repository_dependencies, handled_key_rd_dicts, all_repository_dependencies
def handle_current_repository_dependency( trans, current_repository_key, key_rd_dicts_to_be_processed, all_repository_dependencies, handled_key_rd_dicts,
                                          circular_repository_dependencies ):
    current_repository_key_rd_dicts = []
    for rd in all_repository_dependencies[ current_repository_key ]:
        rd_copy = [ str( item ) for item in rd ]
        new_key_rd_dict = {}
        new_key_rd_dict[ current_repository_key ] = rd_copy
        current_repository_key_rd_dicts.append( new_key_rd_dict )
    if current_repository_key_rd_dicts:
        toolshed, required_repository, required_repository_metadata, repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts = \
            handle_key_rd_dicts_for_repository( trans,
                                                current_repository_key,
                                                current_repository_key_rd_dicts,
                                                key_rd_dicts_to_be_processed,
                                                handled_key_rd_dicts,
                                                circular_repository_dependencies )
        return get_repository_dependencies_for_changeset_revision( trans=trans,
                                                                   repository=required_repository,
                                                                   repository_metadata=required_repository_metadata,
                                                                   toolshed_base_url=toolshed,
                                                                   key_rd_dicts_to_be_processed=key_rd_dicts_to_be_processed,
                                                                   all_repository_dependencies=all_repository_dependencies,
                                                                   handled_key_rd_dicts=handled_key_rd_dicts,
                                                                   circular_repository_dependencies=circular_repository_dependencies )
def handle_existing_tool_dependencies_that_changed_in_update( app, repository, original_dependency_dict, new_dependency_dict ):
    """
    This method is called when a Galaxy admin is getting updates for an installed tool shed repository in order to cover the case where an
    existing tool dependency was changed (e.g., the version of the dependency was changed) but the tool version for which it is a dependency
    was not changed.  In this case, we only want to determine if any of the dependency information defined in original_dependency_dict was
    changed in new_dependency_dict.  We don't care if new dependencies were added in new_dependency_dict since they will just be treated as
    missing dependencies for the tool.
    """
    updated_tool_dependency_names = []
    deleted_tool_dependency_names = []
    for original_dependency_key, original_dependency_val_dict in original_dependency_dict.items():
        if original_dependency_key not in new_dependency_dict:
            updated_tool_dependency = update_existing_tool_dependency( app, repository, original_dependency_val_dict, new_dependency_dict )
            if updated_tool_dependency:
                updated_tool_dependency_names.append( updated_tool_dependency.name )
            else:
                deleted_tool_dependency_names.append( original_dependency_val_dict[ 'name' ] )
    return updated_tool_dependency_names, deleted_tool_dependency_names
def handle_key_rd_dicts_for_repository( trans, current_repository_key, repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts, circular_repository_dependencies ):
    key_rd_dict = repository_key_rd_dicts.pop( 0 )
    repository_dependency = key_rd_dict[ current_repository_key ]
    toolshed, name, owner, changeset_revision = repository_dependency
    if tool_shed_is_this_tool_shed( toolshed ):
        required_repository = get_repository_by_name_and_owner( trans, name, owner )
        required_repository_metadata = get_repository_metadata_by_repository_id_changset_revision( trans,
                                                                                                   trans.security.encode_id( required_repository.id ),
                                                                                                   changeset_revision )
        if required_repository_metadata:
            # The required_repository_metadata changeset_revision is installable.
            required_metadata = required_repository_metadata.metadata
            if required_metadata:
                for current_repository_key_rd_dict in repository_key_rd_dicts:
                    if not in_key_rd_dicts( current_repository_key_rd_dict, key_rd_dicts_to_be_processed ):
                        key_rd_dicts_to_be_processed.append( current_repository_key_rd_dict )
        # Mark the current repository_dependency as handled_key_rd_dicts.
        if not in_key_rd_dicts( key_rd_dict, handled_key_rd_dicts ):
            handled_key_rd_dicts.append( key_rd_dict )
        # Remove the current repository from the list of repository_dependencies to be processed.
        if in_key_rd_dicts( key_rd_dict, key_rd_dicts_to_be_processed ):
            key_rd_dicts_to_be_processed = remove_from_key_rd_dicts( key_rd_dict, key_rd_dicts_to_be_processed )
    else:
        # The repository is in a different tool shed, so build an url and send a request.
        error_message = "Repository dependencies are currently supported only within the same tool shed.  Ignoring repository dependency definition "
        error_message += "for tool shed %s, name %s, owner %s, changeset revision %s" % ( toolshed, name, owner, changeset_revision )
        log.debug( error_message )
    return toolshed, required_repository, required_repository_metadata, repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts
def handle_next_repository_dependency( trans, key_rd_dicts_to_be_processed, all_repository_dependencies, handled_key_rd_dicts, circular_repository_dependencies ):
    next_repository_key_rd_dict = key_rd_dicts_to_be_processed.pop( 0 )
    next_repository_key_rd_dicts = [ next_repository_key_rd_dict ]
    next_repository_key = next_repository_key_rd_dict.keys()[ 0 ]
    toolshed, required_repository, required_repository_metadata, repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts = \
        handle_key_rd_dicts_for_repository( trans,
                                            next_repository_key,
                                            next_repository_key_rd_dicts,
                                            key_rd_dicts_to_be_processed,
                                            handled_key_rd_dicts,
                                            circular_repository_dependencies )
    return get_repository_dependencies_for_changeset_revision( trans=trans,
                                                               repository=required_repository,
                                                               repository_metadata=required_repository_metadata,
                                                               toolshed_base_url=toolshed,
                                                               key_rd_dicts_to_be_processed=key_rd_dicts_to_be_processed,
                                                               all_repository_dependencies=all_repository_dependencies,
                                                               handled_key_rd_dicts=handled_key_rd_dicts,
                                                               circular_repository_dependencies=circular_repository_dependencies )
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
        new_table_elems, message = app.tool_data_tables.add_new_entries_from_config_file( config_filename=filename,
                                                                                          tool_data_path=app.config.tool_data_path,
                                                                                          shed_tool_data_table_config=app.config.shed_tool_data_table_config,
                                                                                          persist=persist )
        if message:
            error = True
    except Exception, e:
        message = str( e )
        error = True
    return error, message
def in_all_repository_dependencies( repository_key, repository_dependency, all_repository_dependencies ):
    """Return True if { repository_key :repository_dependency } is in all_repository_dependencies."""
    for key, val in all_repository_dependencies.items():
        if key != repository_key:
            continue
        if repository_dependency in val:
            return True
    return False
def in_circular_repository_dependencies( repository_key_rd_dict, circular_repository_dependencies ):
    """
    Return True if any combination of a circular dependency tuple is the key : value pair defined in the received repository_key_rd_dict.  This
    means that each circular dependency tuple is converted into the key : value pair for vomparision.
    """
    for tup in circular_repository_dependencies:
        rd_0, rd_1 = tup
        rd_0_as_key = get_repository_dependency_as_key( rd_0 )
        rd_1_as_key = get_repository_dependency_as_key( rd_1 )
        if rd_0_as_key in repository_key_rd_dict and repository_key_rd_dict[ rd_0_as_key ] == rd_1:
            return True
        if rd_1_as_key in repository_key_rd_dict and repository_key_rd_dict[ rd_1_as_key ] == rd_0:
            return True
    return False
def in_key_rd_dicts( key_rd_dict, key_rd_dicts ):
    k = key_rd_dict.keys()[ 0 ]
    v = key_rd_dict[ k ]
    for key_rd_dict in key_rd_dicts:
        for key, val in key_rd_dict.items():
            if key == k and val == v:
                return True
    return False
def is_circular_repository_dependency( repository_key, repository_dependency, all_repository_dependencies ):
    """
    Return True if the received repository_dependency is a key in all_repository_dependencies whose list of repository dependencies
    includes the received repository_key.
    """
    repository_dependency_as_key = get_repository_dependency_as_key( repository_dependency )
    repository_key_as_repository_dependency = repository_key.split( container_util.STRSEP )
    for key, val in all_repository_dependencies.items():
        if key != repository_dependency_as_key:
            continue
        if repository_key_as_repository_dependency in val:
            return True
    return False
def is_downloadable( metadata_dict ):
    return 'datatypes' in metadata_dict or 'repository_dependencies' in metadata_dict or 'tools' in metadata_dict or 'workflows' in metadata_dict
def initialize_all_repository_dependencies( current_repository_key, repository_dependencies_dict, all_repository_dependencies ):
    # Initialize the all_repository_dependencies dictionary.  It's safe to assume that current_repository_key in this case will have a value.
    all_repository_dependencies[ 'root_key' ] = current_repository_key
    all_repository_dependencies[ current_repository_key ] = []
    # Store the value of the 'description' key only once, the first time through this recursive method.
    description = repository_dependencies_dict.get( 'description', None )
    all_repository_dependencies[ 'description' ] = description
    return all_repository_dependencies
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
def load_tool_from_tmp_config( trans, repo, ctx, ctx_file, work_dir ):
    tool = None
    message = ''
    tmp_tool_config = get_named_tmpfile_from_ctx( ctx, ctx_file, work_dir )
    if tmp_tool_config:
        element_tree = util.parse_xml( tmp_tool_config )
        element_tree_root = element_tree.getroot()
        # Look for code files required by the tool config.
        tmp_code_files = []
        for code_elem in element_tree_root.findall( 'code' ):
            code_file_name = code_elem.get( 'file' )
            tmp_code_file_name = copy_file_from_manifest( repo, ctx, code_file_name, work_dir )
            if tmp_code_file_name:
                tmp_code_files.append( tmp_code_file_name )
        tool, valid, message = load_tool_from_config( trans.app, tmp_tool_config )
        for tmp_code_file in tmp_code_files:
            try:
                os.unlink( tmp_code_file )
            except:
                pass
        try:
            os.unlink( tmp_tool_config )
        except:
            pass
    return tool, message
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
def populate_repository_dependency_objects_for_processing( trans, current_repository_key, repository_dependencies_dict, key_rd_dicts_to_be_processed,
                                                           handled_key_rd_dicts, circular_repository_dependencies, all_repository_dependencies ):
    current_repository_key_rd_dicts = []
    for rd in repository_dependencies_dict[ 'repository_dependencies' ]:
        new_key_rd_dict = {}
        new_key_rd_dict[ current_repository_key ] = rd
        current_repository_key_rd_dicts.append( new_key_rd_dict )
    if current_repository_key_rd_dicts and current_repository_key:
        # Remove all repository dependencies that point to a revision within its own repository.
        current_repository_key_rd_dicts = remove_ropository_dependency_reference_to_self( current_repository_key_rd_dicts )
    current_repository_key_rd_dicts = get_updated_changeset_revisions_for_repository_dependencies( trans, current_repository_key_rd_dicts )
    for key_rd_dict in current_repository_key_rd_dicts:
        is_circular = False
        if not in_key_rd_dicts( key_rd_dict, handled_key_rd_dicts ) and not in_key_rd_dicts( key_rd_dict, key_rd_dicts_to_be_processed ):
            repository_dependency = key_rd_dict[ current_repository_key ]
            if current_repository_key in all_repository_dependencies:
                # Add all repository dependencies for the current repository into it's entry in all_repository_dependencies.
                all_repository_dependencies_val = all_repository_dependencies[ current_repository_key ]
                if repository_dependency not in all_repository_dependencies_val:
                    all_repository_dependencies_val.append( repository_dependency )
                    all_repository_dependencies[ current_repository_key ] = all_repository_dependencies_val
            elif not in_all_repository_dependencies( current_repository_key, repository_dependency, all_repository_dependencies ):
                # Handle circular repository dependencies.
                if is_circular_repository_dependency( current_repository_key, repository_dependency, all_repository_dependencies ):
                    is_circular = True
                    circular_repository_dependencies, handled_key_rd_dicts, all_repository_dependencies = \
                        handle_circular_repository_dependency( current_repository_key,
                                                               repository_dependency,
                                                               circular_repository_dependencies,
                                                               handled_key_rd_dicts,
                                                               all_repository_dependencies )
                else:
                    all_repository_dependencies[ current_repository_key ] = [ repository_dependency ]
            if not is_circular and can_add_to_key_rd_dicts( key_rd_dict, key_rd_dicts_to_be_processed ):
                new_key_rd_dict = {}
                new_key_rd_dict[ current_repository_key ] = repository_dependency
                key_rd_dicts_to_be_processed.append( new_key_rd_dict )
    return current_repository_key_rd_dicts, key_rd_dicts_to_be_processed, handled_key_rd_dicts, all_repository_dependencies
def remove_dir( dir ):
    if os.path.exists( dir ):
        try:
            shutil.rmtree( dir )
        except:
            pass
def remove_from_key_rd_dicts( key_rd_dict, key_rd_dicts ):
    k = key_rd_dict.keys()[ 0 ]
    v = key_rd_dict[ k ]
    clean_key_rd_dicts = []
    for krd_dict in key_rd_dicts:
        key = krd_dict.keys()[ 0 ]
        val = krd_dict[ key ]
        if key == k and val == v:
            continue
        clean_key_rd_dicts.append( krd_dict )
    return clean_key_rd_dicts
def remove_ropository_dependency_reference_to_self( key_rd_dicts ):
    """Remove all repository dependencies that point to a revision within its own repository."""
    clean_key_rd_dicts = []
    key = key_rd_dicts[ 0 ].keys()[ 0 ]
    repository_tup = key.split( container_util.STRSEP )
    rd_toolshed, rd_name, rd_owner, rd_changeset_revision = repository_tup
    for key_rd_dict in key_rd_dicts:
        k = key_rd_dict.keys()[ 0 ]
        repository_dependency = key_rd_dict[ k ]
        toolshed, name, owner, changeset_revision = repository_dependency
        if rd_toolshed == toolshed and rd_name == name and rd_owner == owner:
            log.debug( "Removing repository dependency for repository %s owned by %s since it refers to a revision within itself." % ( name, owner ) )
        else:
            new_key_rd_dict = {}
            new_key_rd_dict[ key ] = repository_dependency
            clean_key_rd_dicts.append( new_key_rd_dict )
    return clean_key_rd_dicts
def remove_tool_dependency_installation_directory( dependency_install_dir ):
    if os.path.exists( dependency_install_dir ):
        try:
            shutil.rmtree( dependency_install_dir )
            removed = True
            error_message = ''
            log.debug( "Removed tool dependency installation directory: %s" % str( dependency_install_dir ) )
        except Exception, e:
            removed = False
            error_message = "Error removing tool dependency installation directory %s: %s" % ( str( dependency_install_dir ), str( e ) )
            log.debug( error_message )
    else:
        removed = True
        error_message = ''
    return removed, error_message
def reset_all_metadata_on_installed_repository( trans, id ):
    """Reset all metadata on a single tool shed repository installed into a Galaxy instance."""
    repository = get_installed_tool_shed_repository( trans, id )
    tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
    repository_clone_url = generate_clone_url_for_installed_repository( trans, repository )
    tool_path, relative_install_dir = repository.get_tool_relative_path( trans.app )
    if relative_install_dir:
        original_metadata_dict = repository.metadata
        metadata_dict, invalid_file_tups = generate_metadata_for_changeset_revision( app=trans.app,
                                                                                     repository=repository,
                                                                                     repository_clone_url=repository_clone_url,
                                                                                     shed_config_dict = repository.get_shed_config_dict( trans.app ),
                                                                                     relative_install_dir=relative_install_dir,
                                                                                     repository_files_dir=None,
                                                                                     resetting_all_metadata_on_repository=False,
                                                                                     updating_installed_repository=False,
                                                                                     persist=False )
        repository.metadata = metadata_dict
        if metadata_dict != original_metadata_dict:
            update_in_shed_tool_config( trans.app, repository )
            trans.sa_session.add( repository )
            trans.sa_session.flush()
            log.debug( 'Metadata has been reset on repository %s.' % repository.name )
        else:
            log.debug( 'Metadata did not need to be reset on repository %s.' % repository.name )
    else:
        log.debug( 'Error locating installation directory for repository %s.' % repository.name )
    return invalid_file_tups, metadata_dict
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
            current_metadata_dict, invalid_tups = generate_metadata_for_changeset_revision( app=trans.app,
                                                                                            repository=repository,
                                                                                            repository_clone_url=repository_clone_url,
                                                                                            relative_install_dir=repo_dir,
                                                                                            repository_files_dir=work_dir,
                                                                                            resetting_all_metadata_on_repository=True,
                                                                                            updating_installed_repository=False,
                                                                                            persist=False )
            invalid_file_tups.extend( invalid_tups )            
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
def to_safe_string( text, to_html=True ):
    """Translates the characters in text to an html string"""
    translated = []
    for c in text:
        if c in VALID_CHARS:
            translated.append( c )
        elif c in MAPPED_CHARS:
            translated.append( MAPPED_CHARS[ c ] )
        elif c in [ '\n' ]:
            if to_html:
                translated.append( '<br/>' )
            else:
                translated.append( c )
        elif c in [ '\r' ]:
            continue
        elif c in [ ' ', '    ' ]:
            translated.append( c )
        else:
            translated.append( '' )
    if to_html:
        str( markupsafe.escape( ''.join( translated ) ) )
    return ''.join( translated )
def tool_shed_is_this_tool_shed( toolshed_base_url ):
    return toolshed_base_url.rstrip( '/' ) == str( url_for( '/', qualified=True ) ).rstrip( '/' )
def translate_string( raw_text, to_html=True ):
    if raw_text:
        if len( raw_text ) <= MAX_CONTENT_SIZE:
            translated_string = to_safe_string( raw_text, to_html=to_html )
        else:
            large_str = '\nFile contents truncated because file size is larger than maximum viewing size of %s\n' % util.nice_size( MAX_CONTENT_SIZE )
            translated_string = to_safe_string( '%s%s' % ( raw_text[ 0:MAX_CONTENT_SIZE ], large_str ), to_html=to_html )
    else:
        translated_string = ''
    return translated_string
def update_circular_repository_dependencies( repository_key, repository_dependency, repository_dependencies, circular_repository_dependencies ):
    repository_dependency_as_key = get_repository_dependency_as_key( repository_dependency )
    repository_key_as_repository_dependency = repository_key.split( container_util.STRSEP )
    if repository_key_as_repository_dependency in repository_dependencies:
        found = False
        for tup in circular_repository_dependencies:
            if repository_dependency in tup and repository_key_as_repository_dependency in tup:
                # The circular dependency has already been included.
                found = True
        if not found:
            new_circular_tup = [ repository_dependency, repository_key_as_repository_dependency ]
            circular_repository_dependencies.append( new_circular_tup )
        return circular_repository_dependencies
def update_existing_tool_dependency( app, repository, original_dependency_dict, new_dependencies_dict ):
    """
    Update an exsiting tool dependency whose definition was updated in a change set pulled by a Galaxy administrator when getting updates 
    to an installed tool shed repository.  The original_dependency_dict is a single tool dependency definition, an example of which is::

        {"name": "bwa", 
         "readme": "\\nCompiling BWA requires zlib and libpthread to be present on your system.\\n        ", 
         "type": "package", 
         "version": "0.6.2"}

    The new_dependencies_dict is the dictionary generated by the generate_tool_dependency_metadata method.
    """
    new_tool_dependency = None
    original_name = original_dependency_dict[ 'name' ]
    original_type = original_dependency_dict[ 'type' ]
    original_version = original_dependency_dict[ 'version' ]
    # Locate the appropriate tool_dependency associated with the repository.
    tool_dependency = None
    for tool_dependency in repository.tool_dependencies:
        if tool_dependency.name == original_name and tool_dependency.type == original_type and tool_dependency.version == original_version:
            break
    if tool_dependency and tool_dependency.can_update:
        dependency_install_dir = tool_dependency.installation_directory( app )
        removed_from_disk, error_message = remove_tool_dependency_installation_directory( dependency_install_dir )
        if removed_from_disk:
            sa_session = app.model.context.current
            new_dependency_name = None
            new_dependency_type = None
            new_dependency_version = None
            for new_dependency_key, new_dependency_val_dict in new_dependencies_dict.items():
                # Match on name only, hopefully this will be enough!
                if original_name == new_dependency_val_dict[ 'name' ]:
                    new_dependency_name = new_dependency_val_dict[ 'name' ]
                    new_dependency_type = new_dependency_val_dict[ 'type' ]
                    new_dependency_version = new_dependency_val_dict[ 'version' ]
                    break
            if new_dependency_name and new_dependency_type and new_dependency_version:
                # Update all attributes of the tool_dependency record in the database.
                log.debug( "Updating tool dependency '%s' with type '%s' and version '%s' to have new type '%s' and version '%s'." % \
                           ( str( tool_dependency.name ), str( tool_dependency.type ), str( tool_dependency.version ), str( new_dependency_type ), str( new_dependency_version ) ) )
                tool_dependency.type = new_dependency_type
                tool_dependency.version = new_dependency_version
                tool_dependency.status = app.model.ToolDependency.installation_status.UNINSTALLED
                tool_dependency.error_message = None
                sa_session.add( tool_dependency )
                sa_session.flush()
                new_tool_dependency = tool_dependency
            else:
                # We have no new tool dependency definition based on a matching dependency name, so remove the existing tool dependency record from the database.
                log.debug( "Deleting tool dependency with name '%s', type '%s' and version '%s' from the database since it is no longer defined." % \
                           ( str( tool_dependency.name ), str( tool_dependency.type ), str( tool_dependency.version ) ) )
                sa_session.delete( tool_dependency )
                sa_session.flush()
    return new_tool_dependency
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
