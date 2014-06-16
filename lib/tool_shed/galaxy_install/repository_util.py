import logging
import os
from galaxy import util
from galaxy import web
import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_util
from tool_shed.util import data_manager_util
from tool_shed.util import datatype_util
from tool_shed.util import encoding_util
from tool_shed.util import hg_util
from tool_shed.util import repository_dependency_util
from tool_shed.util import metadata_util
from tool_shed.util import tool_dependency_util
from tool_shed.util import tool_util

log = logging.getLogger( __name__ )

def create_repo_info_dict( app, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_name=None,
                           repository=None, repository_metadata=None, tool_dependencies=None, repository_dependencies=None ):
    """
    Return a dictionary that includes all of the information needed to install a repository into a local
    Galaxy instance.  The dictionary will also contain the recursive list of repository dependencies defined
    for the repository, as well as the defined tool dependencies.

    This method is called from Galaxy under four scenarios:
    1. During the tool shed repository installation process via the tool shed's get_repository_information()
    method.  In this case both the received repository and repository_metadata will be objects, but
    tool_dependencies and repository_dependencies will be None.
    2. When getting updates for an install repository where the updates include newly defined repository
    dependency definitions.  This scenario is similar to 1. above. The tool shed's get_repository_information()
    method is the caller, and both the received repository and repository_metadata will be objects, but
    tool_dependencies and repository_dependencies will be None.
    3. When a tool shed repository that was uninstalled from a Galaxy instance is being reinstalled with no
    updates available.  In this case, both repository and repository_metadata will be None, but tool_dependencies
    and repository_dependencies will be objects previously retrieved from the tool shed if the repository includes
    definitions for them.
    4. When a tool shed repository that was uninstalled from a Galaxy instance is being reinstalled with updates
    available.  In this case, this method is reached via the tool shed's get_updated_repository_information()
    method, and both repository and repository_metadata will be objects but tool_dependencies and
    repository_dependencies will be None.
    """
    repo_info_dict = {}
    repository = suc.get_repository_by_name_and_owner( app, repository_name, repository_owner )
    if app.name == 'tool_shed':
        # We're in the tool shed.
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( app,
                                                                                 app.security.encode_id( repository.id ),
                                                                                 changeset_revision )
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                tool_shed_url = str( web.url_for( '/', qualified=True ) ).rstrip( '/' )
                # Get a dictionary of all repositories upon which the contents of the received repository depends.
                repository_dependencies = \
                    repository_dependency_util.get_repository_dependencies_for_changeset_revision( app=app,
                                                                                                   repository=repository,
                                                                                                   repository_metadata=repository_metadata,
                                                                                                   toolshed_base_url=tool_shed_url,
                                                                                                   key_rd_dicts_to_be_processed=None,
                                                                                                   all_repository_dependencies=None,
                                                                                                   handled_key_rd_dicts=None,
                                                                                                   circular_repository_dependencies=None )
                tool_dependencies = metadata.get( 'tool_dependencies', {} )
    if tool_dependencies:
        new_tool_dependencies = {}
        for dependency_key, requirements_dict in tool_dependencies.items():
            if dependency_key in [ 'set_environment' ]:
                new_set_environment_dict_list = []
                for set_environment_dict in requirements_dict:
                    set_environment_dict[ 'repository_name' ] = repository_name
                    set_environment_dict[ 'repository_owner' ] = repository_owner
                    set_environment_dict[ 'changeset_revision' ] = changeset_revision
                    new_set_environment_dict_list.append( set_environment_dict )
                new_tool_dependencies[ dependency_key ] = new_set_environment_dict_list
            else:
                requirements_dict[ 'repository_name' ] = repository_name
                requirements_dict[ 'repository_owner' ] = repository_owner
                requirements_dict[ 'changeset_revision' ] = changeset_revision
                new_tool_dependencies[ dependency_key ] = requirements_dict
        tool_dependencies = new_tool_dependencies
    # Cast unicode to string, with the exception of description, since it is free text and can contain special characters.
    repo_info_dict[ str( repository.name ) ] = ( repository.description,
                                                 str( repository_clone_url ),
                                                 str( changeset_revision ),
                                                 str( ctx_rev ),
                                                 str( repository_owner ),
                                                 repository_dependencies,
                                                 tool_dependencies )
    return repo_info_dict

def get_prior_install_required_dict( trans, tsr_ids, repo_info_dicts ):
    """
    Return a dictionary whose keys are the received tsr_ids and whose values are a list of tsr_ids, each of which is contained in the received list of tsr_ids
    and whose associated repository must be installed prior to the repository associated with the tsr_id key.
    """
    # Initialize the dictionary.
    prior_install_required_dict = {}
    for tsr_id in tsr_ids:
        prior_install_required_dict[ tsr_id ] = []
    # Inspect the repository dependencies for each repository about to be installed and populate the dictionary.
    for repo_info_dict in repo_info_dicts:
        repository, repository_dependencies = suc.get_repository_and_repository_dependencies_from_repo_info_dict( trans.app, repo_info_dict )
        if repository:
            encoded_repository_id = trans.security.encode_id( repository.id )
            if encoded_repository_id in tsr_ids:
                # We've located the database table record for one of the repositories we're about to install, so find out if it has any repository
                # dependencies that require prior installation.
                prior_install_ids = suc.get_repository_ids_requiring_prior_import_or_install( trans.app, tsr_ids, repository_dependencies )
                prior_install_required_dict[ encoded_repository_id ] = prior_install_ids
    return prior_install_required_dict

def get_repo_info_dict( trans, repository_id, changeset_revision ):
    repository = suc.get_repository_in_tool_shed( trans.app, repository_id )
    repo = hg_util.get_repo_for_repository( trans.app, repository=repository, repo_path=None, create=False )
    repository_clone_url = common_util.generate_clone_url_for_repository_in_tool_shed( trans, repository )
    repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans.app,
                                                                             repository_id,
                                                                             changeset_revision )
    if not repository_metadata:
        # The received changeset_revision is no longer installable, so get the next changeset_revision
        # in the repository's changelog.  This generally occurs only with repositories of type
        # repository_suite_definition or tool_dependency_definition.
        next_downloadable_changeset_revision = \
            suc.get_next_downloadable_changeset_revision( repository,repo, changeset_revision )
        if next_downloadable_changeset_revision:
            repository_metadata = \
                suc.get_repository_metadata_by_changeset_revision( trans.app, repository_id, next_downloadable_changeset_revision )
    if repository_metadata:
        # For now, we'll always assume that we'll get repository_metadata, but if we discover our assumption
        # is not valid we'll have to enhance the callers to handle repository_metadata values of None in the
        # returned repo_info_dict.
        metadata = repository_metadata.metadata
        if 'tools' in metadata:
            includes_tools = True
        else:
            includes_tools = False
        includes_tools_for_display_in_tool_panel = repository_metadata.includes_tools_for_display_in_tool_panel
        repository_dependencies_dict = metadata.get( 'repository_dependencies', {} )
        repository_dependencies = repository_dependencies_dict.get( 'repository_dependencies', [] )
        has_repository_dependencies, has_repository_dependencies_only_if_compiling_contained_td = \
            suc.get_repository_dependency_types( repository_dependencies )
        if 'tool_dependencies' in metadata:
            includes_tool_dependencies = True
        else:
            includes_tool_dependencies = False
    else:
        # Here's where we may have to handle enhancements to the callers. See above comment.
        includes_tools = False
        has_repository_dependencies = False
        has_repository_dependencies_only_if_compiling_contained_td = False
        includes_tool_dependencies = False
        includes_tools_for_display_in_tool_panel = False
    ctx = hg_util.get_changectx_for_changeset( repo, changeset_revision )
    repo_info_dict = create_repo_info_dict( app=trans.app,
                                            repository_clone_url=repository_clone_url,
                                            changeset_revision=changeset_revision,
                                            ctx_rev=str( ctx.rev() ),
                                            repository_owner=repository.user.username,
                                            repository_name=repository.name,
                                            repository=repository,
                                            repository_metadata=repository_metadata,
                                            tool_dependencies=None,
                                            repository_dependencies=None )
    return repo_info_dict, includes_tools, includes_tool_dependencies, includes_tools_for_display_in_tool_panel, \
        has_repository_dependencies, has_repository_dependencies_only_if_compiling_contained_td

def get_tool_shed_repository_ids( as_string=False, **kwd ):
    tsrid = kwd.get( 'tool_shed_repository_id', None )
    tsridslist = util.listify( kwd.get( 'tool_shed_repository_ids', None ) )
    if not tsridslist:
        tsridslist = util.listify( kwd.get( 'id', None ) )
    if tsridslist:
        if tsrid and tsrid not in tsridslist:
            tsridslist.append( tsrid )
        if as_string:
            return ','.join( tsridslist )
        return tsridslist
    else:
        tsridslist = util.listify( kwd.get( 'ordered_tsr_ids', None ) )
        if as_string:
            return ','.join( tsridslist )
        return tsridslist
    if as_string:
        ''
    return []

def get_update_to_changeset_revision_and_ctx_rev( app, repository ):
    """Return the changeset revision hash to which the repository can be updated."""
    changeset_revision_dict = {}
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( app, str( repository.tool_shed ) )
    params = '?name=%s&owner=%s&changeset_revision=%s' % ( str( repository.name ),
                                                           str( repository.owner ),
                                                           str( repository.installed_changeset_revision ) )
    url = common_util.url_join( tool_shed_url, 'repository/get_changeset_revision_and_ctx_rev%s' % params )
    try:
        encoded_update_dict = common_util.tool_shed_get( app, tool_shed_url, url )
        if encoded_update_dict:
            update_dict = encoding_util.tool_shed_decode( encoded_update_dict )
            includes_data_managers = update_dict.get( 'includes_data_managers', False )
            includes_datatypes = update_dict.get( 'includes_datatypes', False )
            includes_tools = update_dict.get( 'includes_tools', False )
            includes_tools_for_display_in_tool_panel = update_dict.get( 'includes_tools_for_display_in_tool_panel', False )
            includes_tool_dependencies = update_dict.get( 'includes_tool_dependencies', False )
            includes_workflows = update_dict.get( 'includes_workflows', False )
            has_repository_dependencies = update_dict.get( 'has_repository_dependencies', False )
            has_repository_dependencies_only_if_compiling_contained_td = update_dict.get( 'has_repository_dependencies_only_if_compiling_contained_td', False )
            changeset_revision = update_dict.get( 'changeset_revision', None )
            ctx_rev = update_dict.get( 'ctx_rev', None )
        changeset_revision_dict[ 'includes_data_managers' ] = includes_data_managers
        changeset_revision_dict[ 'includes_datatypes' ] = includes_datatypes
        changeset_revision_dict[ 'includes_tools' ] = includes_tools
        changeset_revision_dict[ 'includes_tools_for_display_in_tool_panel' ] = includes_tools_for_display_in_tool_panel
        changeset_revision_dict[ 'includes_tool_dependencies' ] = includes_tool_dependencies
        changeset_revision_dict[ 'includes_workflows' ] = includes_workflows
        changeset_revision_dict[ 'has_repository_dependencies' ] = has_repository_dependencies
        changeset_revision_dict[ 'has_repository_dependencies_only_if_compiling_contained_td' ] = has_repository_dependencies_only_if_compiling_contained_td
        changeset_revision_dict[ 'changeset_revision' ] = changeset_revision
        changeset_revision_dict[ 'ctx_rev' ] = ctx_rev
    except Exception, e:
        log.debug( "Error getting change set revision for update from the tool shed for repository '%s': %s" % ( repository.name, str( e ) ) )
        changeset_revision_dict[ 'includes_data_managers' ] = False
        changeset_revision_dict[ 'includes_datatypes' ] = False
        changeset_revision_dict[ 'includes_tools' ] = False
        changeset_revision_dict[ 'includes_tools_for_display_in_tool_panel' ] = False
        changeset_revision_dict[ 'includes_tool_dependencies' ] = False
        changeset_revision_dict[ 'includes_workflows' ] = False
        changeset_revision_dict[ 'has_repository_dependencies' ] = False
        changeset_revision_dict[ 'has_repository_dependencies_only_if_compiling_contained_td' ] = False
        changeset_revision_dict[ 'changeset_revision' ] = None
        changeset_revision_dict[ 'ctx_rev' ] = None
    return changeset_revision_dict

def handle_repository_contents( app, tool_shed_repository, tool_path, repository_clone_url, relative_install_dir,
                                tool_shed=None, tool_section=None, shed_tool_conf=None, reinstalling=False ):
    """
    Generate the metadata for the installed tool shed repository, among other things.  This method is called from Galaxy
    (never the tool shed) when an administrator is installing a new repository or reinstalling an uninstalled repository.
    """
    install_model = app.install_model
    shed_config_dict = app.toolbox.get_shed_config_dict_by_filename( shed_tool_conf )
    metadata_dict, invalid_file_tups = \
        metadata_util.generate_metadata_for_changeset_revision( app=app,
                                                                repository=tool_shed_repository,
                                                                changeset_revision=tool_shed_repository.changeset_revision,
                                                                repository_clone_url=repository_clone_url,
                                                                shed_config_dict=shed_config_dict,
                                                                relative_install_dir=relative_install_dir,
                                                                repository_files_dir=None,
                                                                resetting_all_metadata_on_repository=False,
                                                                updating_installed_repository=False,
                                                                persist=True )
    tool_shed_repository.metadata = metadata_dict
    # Update the tool_shed_repository.tool_shed_status column in the database.
    tool_shed_status_dict = suc.get_tool_shed_status_for_installed_repository( app, tool_shed_repository )
    if tool_shed_status_dict:
        tool_shed_repository.tool_shed_status = tool_shed_status_dict
    install_model.context.add( tool_shed_repository )
    install_model.context.flush()
    if 'tool_dependencies' in metadata_dict and not reinstalling:
        tool_dependencies = tool_dependency_util.create_tool_dependency_objects( app,
                                                                                 tool_shed_repository,
                                                                                 relative_install_dir,
                                                                                 set_status=True )
    if 'sample_files' in metadata_dict:
        sample_files = metadata_dict.get( 'sample_files', [] )
        tool_index_sample_files = tool_util.get_tool_index_sample_files( sample_files )
        tool_data_table_conf_filename, tool_data_table_elems = \
            tool_util.install_tool_data_tables( app, tool_shed_repository, tool_index_sample_files )
        if tool_data_table_elems:
            app.tool_data_tables.add_new_entries_from_config_file( tool_data_table_conf_filename,
                                                                         None,
                                                                         app.config.shed_tool_data_table_config,
                                                                         persist=True )
    if 'tools' in metadata_dict:
        tool_panel_dict = tool_util.generate_tool_panel_dict_for_new_install( metadata_dict[ 'tools' ], tool_section )
        sample_files = metadata_dict.get( 'sample_files', [] )
        tool_index_sample_files = tool_util.get_tool_index_sample_files( sample_files )
        tool_util.copy_sample_files( app, tool_index_sample_files, tool_path=tool_path )
        sample_files_copied = [ str( s ) for s in tool_index_sample_files ]
        repository_tools_tups = suc.get_repository_tools_tups( app, metadata_dict )
        if repository_tools_tups:
            # Handle missing data table entries for tool parameters that are dynamically generated select lists.
            repository_tools_tups = tool_util.handle_missing_data_table_entry( app,
                                                                               relative_install_dir,
                                                                               tool_path,
                                                                               repository_tools_tups )
            # Handle missing index files for tool parameters that are dynamically generated select lists.
            repository_tools_tups, sample_files_copied = \
                tool_util.handle_missing_index_file( app,
                                                     tool_path,
                                                     sample_files,
                                                     repository_tools_tups,
                                                     sample_files_copied )
            # Copy remaining sample files included in the repository to the ~/tool-data directory of the
            # local Galaxy instance.
            tool_util.copy_sample_files( app, sample_files, tool_path=tool_path, sample_files_copied=sample_files_copied )
            tool_util.add_to_tool_panel( app=app,
                                         repository_name=tool_shed_repository.name,
                                         repository_clone_url=repository_clone_url,
                                         changeset_revision=tool_shed_repository.installed_changeset_revision,
                                         repository_tools_tups=repository_tools_tups,
                                         owner=tool_shed_repository.owner,
                                         shed_tool_conf=shed_tool_conf,
                                         tool_panel_dict=tool_panel_dict,
                                         new_install=True )
    if 'data_manager' in metadata_dict:
        new_data_managers = data_manager_util.install_data_managers( app,
                                                                     app.config.shed_data_manager_config_file,
                                                                     metadata_dict,
                                                                     shed_config_dict,
                                                                     relative_install_dir,
                                                                     tool_shed_repository,
                                                                     repository_tools_tups )
    if 'datatypes' in metadata_dict:
        tool_shed_repository.status = install_model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES
        if not tool_shed_repository.includes_datatypes:
            tool_shed_repository.includes_datatypes = True
        install_model.context.add( tool_shed_repository )
        install_model.context.flush()
        files_dir = relative_install_dir
        if shed_config_dict.get( 'tool_path' ):
            files_dir = os.path.join( shed_config_dict[ 'tool_path' ], files_dir )
        datatypes_config = hg_util.get_config_from_disk( suc.DATATYPES_CONFIG_FILENAME, files_dir )
        # Load data types required by tools.
        converter_path, display_path = \
            datatype_util.alter_config_and_load_prorietary_datatypes( app, datatypes_config, files_dir, override=False )
        if converter_path or display_path:
            # Create a dictionary of tool shed repository related information.
            repository_dict = \
                datatype_util.create_repository_dict_for_proprietary_datatypes( tool_shed=tool_shed,
                                                                                name=tool_shed_repository.name,
                                                                                owner=tool_shed_repository.owner,
                                                                                installed_changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                                                tool_dicts=metadata_dict.get( 'tools', [] ),
                                                                                converter_path=converter_path,
                                                                                display_path=display_path )
        if converter_path:
            # Load proprietary datatype converters
            app.datatypes_registry.load_datatype_converters( app.toolbox, installed_repository_dict=repository_dict )
        if display_path:
            # Load proprietary datatype display applications
            app.datatypes_registry.load_display_applications( installed_repository_dict=repository_dict )

def handle_tool_shed_repositories( app, installation_dict, using_api=False ):
    # The following installation_dict entries are all required.
    install_repository_dependencies = installation_dict[ 'install_repository_dependencies' ]
    new_tool_panel_section_label = installation_dict[ 'new_tool_panel_section_label' ]
    no_changes_checked = installation_dict[ 'no_changes_checked' ]
    repo_info_dicts = installation_dict[ 'repo_info_dicts' ]
    tool_panel_section_id = installation_dict[ 'tool_panel_section_id' ]
    tool_path = installation_dict[ 'tool_path' ]
    tool_shed_url = installation_dict[ 'tool_shed_url' ]
    created_or_updated_tool_shed_repositories, tool_panel_section_keys, repo_info_dicts, filtered_repo_info_dicts = \
        repository_dependency_util.create_repository_dependency_objects( app=app,
                                                                         tool_path=tool_path,
                                                                         tool_shed_url=tool_shed_url,
                                                                         repo_info_dicts=repo_info_dicts,
                                                                         install_repository_dependencies=install_repository_dependencies,
                                                                         no_changes_checked=no_changes_checked,
                                                                         tool_panel_section_id=tool_panel_section_id,
                                                                         new_tool_panel_section_label=new_tool_panel_section_label )
    return created_or_updated_tool_shed_repositories, tool_panel_section_keys, repo_info_dicts, filtered_repo_info_dicts

def update_repository_record( app, repository, updated_metadata_dict, updated_changeset_revision, updated_ctx_rev ):
    """
    Update a tool_shed_repository database record with new information retrieved from the
    Tool Shed.  This happens when updating an installed repository to a new changeset revision.
    """
    repository.metadata = updated_metadata_dict
    # Update the repository.changeset_revision column in the database.
    repository.changeset_revision = updated_changeset_revision
    repository.ctx_rev = updated_ctx_rev
    # Update the repository.tool_shed_status column in the database.
    tool_shed_status_dict = suc.get_tool_shed_status_for_installed_repository( app, repository )
    if tool_shed_status_dict:
        repository.tool_shed_status = tool_shed_status_dict
    else:
        repository.tool_shed_status = None
    app.install_model.context.add( repository )
    app.install_model.context.flush()
    app.install_model.context.refresh( repository )
    return repository
