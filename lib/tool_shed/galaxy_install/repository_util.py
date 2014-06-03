import logging
import os
import shutil
import tempfile
import threading
from galaxy import tools
from galaxy.util import json
from galaxy import util
from galaxy import web
from galaxy.model.orm import or_
import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_util
from tool_shed.util import common_install_util
from tool_shed.util import container_util
from tool_shed.util import data_manager_util
from tool_shed.util import datatype_util
from tool_shed.util import encoding_util
from tool_shed.util import hg_util
from tool_shed.util import repository_dependency_util
from tool_shed.util import metadata_util
from tool_shed.util import tool_dependency_util
from tool_shed.util import tool_util
from tool_shed.util import xml_util

from galaxy import eggs
eggs.require( 'mercurial' )

from mercurial import commands
from mercurial import hg
from mercurial import ui

log = logging.getLogger( __name__ )

def create_repo_info_dict( trans, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_name=None,
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
    repository = suc.get_repository_by_name_and_owner( trans.app, repository_name, repository_owner )
    if trans.webapp.name == 'tool_shed':
        # We're in the tool shed.
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans,
                                                                                 trans.security.encode_id( repository.id ),
                                                                                 changeset_revision )
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                tool_shed_url = str( web.url_for( '/', qualified=True ) ).rstrip( '/' )
                # Get a dictionary of all repositories upon which the contents of the received repository depends.
                repository_dependencies = \
                    repository_dependency_util.get_repository_dependencies_for_changeset_revision( trans=trans,
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

def get_installed_repositories_from_repository_dependencies( trans, repository_dependencies_dict ):
    installed_repositories = []
    if repository_dependencies_dict and isinstance( repository_dependencies_dict, dict ):
        for rd_key, rd_vals in repository_dependencies_dict.items():
            if rd_key in [ 'root_key', 'description' ]:
                continue
            # rd_key is something like: 'http://localhost:9009__ESEP__package_rdkit_2012_12__ESEP__test__ESEP__d635ffb9c665__ESEP__True'
            # rd_val is something like: [['http://localhost:9009', 'package_numpy_1_7', 'test', 'cddd64ecd985', 'True']]
            repository_components_tuple = container_util.get_components_from_key( rd_key )
            components_list = suc.extract_components_from_tuple( repository_components_tuple )
            tool_shed, name, owner, changeset_revision = components_list[ 0:4 ]
            installed_repository = suc.get_tool_shed_repository_by_shed_name_owner_changeset_revision( trans.app, tool_shed, name, owner, changeset_revision )
            if installed_repository not in installed_repositories:
                installed_repositories.append( installed_repository )
            for rd_val in rd_vals:
                tool_shed, name, owner, changeset_revision = rd_val[ 0:4 ]
                installed_repository = suc.get_tool_shed_repository_by_shed_name_owner_changeset_revision( trans.app, tool_shed, name, owner, changeset_revision )
                if installed_repository not in installed_repositories:
                    installed_repositories.append( installed_repository )
    return installed_repositories

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
        repository, repository_dependencies = suc.get_repository_and_repository_dependencies_from_repo_info_dict( trans, repo_info_dict )
        if repository:
            encoded_repository_id = trans.security.encode_id( repository.id )
            if encoded_repository_id in tsr_ids:
                # We've located the database table record for one of the repositories we're about to install, so find out if it has any repository
                # dependencies that require prior installation.
                prior_install_ids = suc.get_repository_ids_requiring_prior_import_or_install( trans, tsr_ids, repository_dependencies )
                prior_install_required_dict[ encoded_repository_id ] = prior_install_ids
    return prior_install_required_dict

def get_repair_dict( trans, repository ):
    """
    Inspect the installed repository dependency hierarchy for a specified repository and attempt to make sure they are all properly installed as well as
    each repository's tool dependencies.  This method is called only from Galaxy when attempting to correct issues with an installed repository that has
    installation problems somewhere in its dependency hierarchy.
    """
    tsr_ids = []
    repo_info_dicts = []
    tool_panel_section_keys = []
    repair_dict = {}
    # Get a dictionary of all repositories upon which the contents of the current repository_metadata record depend.
    repository_dependencies_dict = repository_dependency_util.get_repository_dependencies_for_installed_tool_shed_repository( trans, repository )
    if repository_dependencies_dict:
        # Generate the list of installed repositories from the information contained in the repository_dependencies dictionary.
        installed_repositories = get_installed_repositories_from_repository_dependencies( trans, repository_dependencies_dict )
        # Some repositories may have repository dependencies that are required to be installed before the dependent repository, so we'll order the list of
        # tsr_ids to ensure all repositories are repaired in the required order.
        for installed_repository in installed_repositories:
            tsr_ids.append( trans.security.encode_id( installed_repository.id ) )
            repo_info_dict, tool_panel_section_key = get_repo_info_dict_for_repair( trans, installed_repository )
            tool_panel_section_keys.append( tool_panel_section_key )
            repo_info_dicts.append( repo_info_dict )
    else:
        # The received repository has no repository dependencies.
        tsr_ids.append( trans.security.encode_id( repository.id ) )
        repo_info_dict, tool_panel_section_key = get_repo_info_dict_for_repair( trans, repository )
        tool_panel_section_keys.append( tool_panel_section_key )
        repo_info_dicts.append( repo_info_dict )
    ordered_tsr_ids, ordered_repo_info_dicts, ordered_tool_panel_section_keys = \
        order_components_for_installation( trans,
                                           tsr_ids,
                                           repo_info_dicts,
                                           tool_panel_section_keys=tool_panel_section_keys )
    repair_dict[ 'ordered_tsr_ids' ] = ordered_tsr_ids
    repair_dict[ 'ordered_repo_info_dicts' ] = ordered_repo_info_dicts
    repair_dict[ 'ordered_tool_panel_section_keys' ] = ordered_tool_panel_section_keys
    return repair_dict

def get_repo_info_dict( trans, repository_id, changeset_revision ):
    repository = suc.get_repository_in_tool_shed( trans, repository_id )
    repo_dir = repository.repo_path( trans.app )
    repo = hg.repository( hg_util.get_configured_ui(), repo_dir )
    repository_clone_url = common_util.generate_clone_url_for_repository_in_tool_shed( trans, repository )
    repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans,
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
                suc.get_repository_metadata_by_changeset_revision( trans, repository_id, next_downloadable_changeset_revision )
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
    repo_info_dict = create_repo_info_dict( trans=trans,
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

def get_repo_info_dict_for_repair( trans, repository ):
    tool_panel_section_key = None
    repository_clone_url = common_util.generate_clone_url_for_installed_repository( trans.app, repository )
    repository_dependencies = \
        repository_dependency_util.get_repository_dependencies_for_installed_tool_shed_repository( trans, repository )
    metadata = repository.metadata
    if metadata:
        tool_dependencies = metadata.get( 'tool_dependencies', None )
        tool_panel_section_dict = metadata.get( 'tool_panel_section', None )
        if tool_panel_section_dict:
            # The repository must be in the uninstalled state.  The structure of tool_panel_section_dict is:
            # {<tool guid> : 
            # [{ 'id':<section id>, 'name':<section name>, 'version':<section version>, 'tool_config':<tool config file name> }]}
            # Here is an example:
            # {"localhost:9009/repos/test/filter/Filter1/1.1.0":
            # [{"id": "filter_and_sort", "name": "Filter and Sort", "tool_config": "filtering.xml", "version": ""}]}
            # Currently all tools contained within an installed tool shed repository must be loaded into the same
            # section in the tool panel, so we can get the section id of the first guid in the tool_panel_section_dict.
            # In the future, we'll have to handle different sections per guid.
            guid = tool_panel_section_dict.keys()[ 0 ]
            section_dicts = tool_panel_section_dict[ guid ]
            section_dict = section_dicts[ 0 ]
            tool_panel_section_id = section_dict[ 'id' ]
            tool_panel_section_name = section_dict[ 'name' ]
            if tool_panel_section_id:
                tool_panel_section_key, tool_panel_section = \
                    tool_util.get_or_create_tool_section( trans,
                                                          tool_panel_section_id=tool_panel_section_id,
                                                          new_tool_panel_section_label=tool_panel_section_name )
    else:
        tool_dependencies = None
    repo_info_dict = create_repo_info_dict( trans=trans,
                                            repository_clone_url=repository_clone_url,
                                            changeset_revision=repository.changeset_revision,
                                            ctx_rev=repository.ctx_rev,
                                            repository_owner=repository.owner,
                                            repository_name=repository.name,
                                            repository=None,
                                            repository_metadata=None,
                                            tool_dependencies=tool_dependencies,
                                            repository_dependencies=repository_dependencies )
    return repo_info_dict, tool_panel_section_key

def get_repository_components_for_installation( encoded_tsr_id, encoded_tsr_ids, repo_info_dicts, tool_panel_section_keys ):
    """
    The received encoded_tsr_ids, repo_info_dicts, and tool_panel_section_keys are 3 lists that contain associated elements at each location in
    the list.  This method will return the elements from repo_info_dicts and tool_panel_section_keys associated with the received encoded_tsr_id
    by determining its location in the received encoded_tsr_ids list.
    """
    for index, tsr_id in enumerate( encoded_tsr_ids ):
        if tsr_id == encoded_tsr_id:
            repo_info_dict = repo_info_dicts[ index ]
            tool_panel_section_key = tool_panel_section_keys[ index ]
            return repo_info_dict, tool_panel_section_key
    return None, None

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

def get_update_to_changeset_revision_and_ctx_rev( trans, repository ):
    """Return the changeset revision hash to which the repository can be updated."""
    changeset_revision_dict = {}
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( trans.app, str( repository.tool_shed ) )
    params = '?name=%s&owner=%s&changeset_revision=%s' % ( str( repository.name ),
                                                           str( repository.owner ),
                                                           str( repository.installed_changeset_revision ) )
    url = common_util.url_join( tool_shed_url, 'repository/get_changeset_revision_and_ctx_rev%s' % params )
    try:
        encoded_update_dict = common_util.tool_shed_get( trans.app, tool_shed_url, url )
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

def handle_repository_contents( trans, tool_shed_repository, tool_path, repository_clone_url, relative_install_dir,
                                tool_shed=None, tool_section=None, shed_tool_conf=None, reinstalling=False ):
    """
    Generate the metadata for the installed tool shed repository, among other things.  This method is called from Galaxy
    (never the tool shed) when an administrator is installing a new repository or reinstalling an uninstalled repository.
    """
    shed_config_dict = trans.app.toolbox.get_shed_config_dict_by_filename( shed_tool_conf )
    metadata_dict, invalid_file_tups = \
        metadata_util.generate_metadata_for_changeset_revision( app=trans.app,
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
    tool_shed_status_dict = suc.get_tool_shed_status_for_installed_repository( trans.app, tool_shed_repository )
    if tool_shed_status_dict:
        tool_shed_repository.tool_shed_status = tool_shed_status_dict
    trans.install_model.context.add( tool_shed_repository )
    trans.install_model.context.flush()
    if 'tool_dependencies' in metadata_dict and not reinstalling:
        tool_dependencies = tool_dependency_util.create_tool_dependency_objects( trans.app,
                                                                                 tool_shed_repository,
                                                                                 relative_install_dir,
                                                                                 set_status=True )
    if 'sample_files' in metadata_dict:
        sample_files = metadata_dict.get( 'sample_files', [] )
        tool_index_sample_files = tool_util.get_tool_index_sample_files( sample_files )
        tool_data_table_conf_filename, tool_data_table_elems = \
            tool_util.install_tool_data_tables( trans.app, tool_shed_repository, tool_index_sample_files )
        if tool_data_table_elems:
            trans.app.tool_data_tables.add_new_entries_from_config_file( tool_data_table_conf_filename,
                                                                         None,
                                                                         trans.app.config.shed_tool_data_table_config,
                                                                         persist=True )
    if 'tools' in metadata_dict:
        tool_panel_dict = tool_util.generate_tool_panel_dict_for_new_install( metadata_dict[ 'tools' ], tool_section )
        sample_files = metadata_dict.get( 'sample_files', [] )
        tool_index_sample_files = tool_util.get_tool_index_sample_files( sample_files )
        tool_util.copy_sample_files( trans.app, tool_index_sample_files, tool_path=tool_path )
        sample_files_copied = [ str( s ) for s in tool_index_sample_files ]
        repository_tools_tups = suc.get_repository_tools_tups( trans.app, metadata_dict )
        if repository_tools_tups:
            # Handle missing data table entries for tool parameters that are dynamically generated select lists.
            repository_tools_tups = tool_util.handle_missing_data_table_entry( trans.app,
                                                                               relative_install_dir,
                                                                               tool_path,
                                                                               repository_tools_tups )
            # Handle missing index files for tool parameters that are dynamically generated select lists.
            repository_tools_tups, sample_files_copied = \
                tool_util.handle_missing_index_file( trans.app,
                                                     tool_path,
                                                     sample_files,
                                                     repository_tools_tups,
                                                     sample_files_copied )
            # Copy remaining sample files included in the repository to the ~/tool-data directory of the
            # local Galaxy instance.
            tool_util.copy_sample_files( trans.app, sample_files, tool_path=tool_path, sample_files_copied=sample_files_copied )
            tool_util.add_to_tool_panel( app=trans.app,
                                         repository_name=tool_shed_repository.name,
                                         repository_clone_url=repository_clone_url,
                                         changeset_revision=tool_shed_repository.installed_changeset_revision,
                                         repository_tools_tups=repository_tools_tups,
                                         owner=tool_shed_repository.owner,
                                         shed_tool_conf=shed_tool_conf,
                                         tool_panel_dict=tool_panel_dict,
                                         new_install=True )
    if 'data_manager' in metadata_dict:
        new_data_managers = data_manager_util.install_data_managers( trans.app,
                                                                     trans.app.config.shed_data_manager_config_file,
                                                                     metadata_dict,
                                                                     shed_config_dict,
                                                                     relative_install_dir,
                                                                     tool_shed_repository,
                                                                     repository_tools_tups )
    if 'datatypes' in metadata_dict:
        tool_shed_repository.status = trans.install_model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES
        if not tool_shed_repository.includes_datatypes:
            tool_shed_repository.includes_datatypes = True
        trans.install_model.context.add( tool_shed_repository )
        trans.install_model.context.flush()
        files_dir = relative_install_dir
        if shed_config_dict.get( 'tool_path' ):
            files_dir = os.path.join( shed_config_dict[ 'tool_path' ], files_dir )
        datatypes_config = suc.get_config_from_disk( suc.DATATYPES_CONFIG_FILENAME, files_dir )
        # Load data types required by tools.
        converter_path, display_path = \
            datatype_util.alter_config_and_load_prorietary_datatypes( trans.app, datatypes_config, files_dir, override=False )
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
            trans.app.datatypes_registry.load_datatype_converters( trans.app.toolbox, installed_repository_dict=repository_dict )
        if display_path:
            # Load proprietary datatype display applications
            trans.app.datatypes_registry.load_display_applications( installed_repository_dict=repository_dict )

def handle_tool_shed_repositories( trans, installation_dict, using_api=False ):
    # The following installation_dict entries are all required.
    install_repository_dependencies = installation_dict[ 'install_repository_dependencies' ]
    new_tool_panel_section_label = installation_dict[ 'new_tool_panel_section_label' ]
    no_changes_checked = installation_dict[ 'no_changes_checked' ]
    repo_info_dicts = installation_dict[ 'repo_info_dicts' ]
    tool_panel_section_id = installation_dict[ 'tool_panel_section_id' ]
    tool_path = installation_dict[ 'tool_path' ]
    tool_shed_url = installation_dict[ 'tool_shed_url' ]
    created_or_updated_tool_shed_repositories, tool_panel_section_keys, repo_info_dicts, filtered_repo_info_dicts = \
        repository_dependency_util.create_repository_dependency_objects( trans=trans,
                                                                         tool_path=tool_path,
                                                                         tool_shed_url=tool_shed_url,
                                                                         repo_info_dicts=repo_info_dicts,
                                                                         install_repository_dependencies=install_repository_dependencies,
                                                                         no_changes_checked=no_changes_checked,
                                                                         tool_panel_section_id=tool_panel_section_id,
                                                                         new_tool_panel_section_label=new_tool_panel_section_label )
    return created_or_updated_tool_shed_repositories, tool_panel_section_keys, repo_info_dicts, filtered_repo_info_dicts

def initiate_repository_installation( trans, installation_dict ):
    # The following installation_dict entries are all required.
    created_or_updated_tool_shed_repositories = installation_dict[ 'created_or_updated_tool_shed_repositories' ]
    filtered_repo_info_dicts = installation_dict[ 'filtered_repo_info_dicts' ]
    has_repository_dependencies = installation_dict[ 'has_repository_dependencies' ]
    includes_tool_dependencies = installation_dict[ 'includes_tool_dependencies' ]
    includes_tools = installation_dict[ 'includes_tools' ]
    includes_tools_for_display_in_tool_panel = installation_dict[ 'includes_tools_for_display_in_tool_panel' ]
    install_repository_dependencies = installation_dict[ 'install_repository_dependencies' ]
    install_tool_dependencies = installation_dict[ 'install_tool_dependencies' ]
    message = installation_dict[ 'message' ]
    new_tool_panel_section_label = installation_dict[ 'new_tool_panel_section_label' ]
    shed_tool_conf = installation_dict[ 'shed_tool_conf' ]
    status = installation_dict[ 'status' ]
    tool_panel_section_id = installation_dict[ 'tool_panel_section_id' ]
    tool_panel_section_keys = installation_dict[ 'tool_panel_section_keys' ]
    tool_path = installation_dict[ 'tool_path' ]
    tool_shed_url = installation_dict[ 'tool_shed_url' ]
    # Handle contained tools.
    if includes_tools_for_display_in_tool_panel and ( new_tool_panel_section_label or tool_panel_section_id ):
        tool_panel_section_key, tool_section = \
            tool_util.handle_tool_panel_section( trans,
                                                 tool_panel_section_id=tool_panel_section_id,
                                                 new_tool_panel_section_label=new_tool_panel_section_label )
    else:
        tool_panel_section_key = None
        tool_section = None
    encoded_repository_ids = [ trans.security.encode_id( tsr.id ) for tsr in created_or_updated_tool_shed_repositories ]
    new_kwd = dict( includes_tools=includes_tools,
                    includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
                    has_repository_dependencies=has_repository_dependencies,
                    install_repository_dependencies=install_repository_dependencies,
                    includes_tool_dependencies=includes_tool_dependencies,
                    install_tool_dependencies=install_tool_dependencies,
                    message=message,
                    repo_info_dicts=filtered_repo_info_dicts,
                    shed_tool_conf=shed_tool_conf,
                    status=status,
                    tool_path=tool_path,
                    tool_panel_section_keys=tool_panel_section_keys,
                    tool_shed_repository_ids=encoded_repository_ids,
                    tool_shed_url=tool_shed_url )
    encoded_kwd = encoding_util.tool_shed_encode( new_kwd )
    tsr_ids = [ r.id  for r in created_or_updated_tool_shed_repositories  ]
    tool_shed_repositories = []
    for tsr_id in tsr_ids:
        tsr = trans.install_model.context.query( trans.install_model.ToolShedRepository ).get( tsr_id )
        tool_shed_repositories.append( tsr )
    clause_list = []
    for tsr_id in tsr_ids:
        clause_list.append( trans.install_model.ToolShedRepository.table.c.id == tsr_id )
    query = trans.install_model.context.query( trans.install_model.ToolShedRepository ).filter( or_( *clause_list ) )
    return encoded_kwd, query, tool_shed_repositories, encoded_repository_ids

def install_tool_shed_repository( trans, tool_shed_repository, repo_info_dict, tool_panel_section_key, shed_tool_conf, tool_path,
                                  install_tool_dependencies, reinstalling=False ):
    if tool_panel_section_key:
        try:
            tool_section = trans.app.toolbox.tool_panel[ tool_panel_section_key ]
        except KeyError:
            log.debug( 'Invalid tool_panel_section_key "%s" specified.  Tools will be loaded outside of sections in the tool panel.',
                       str( tool_panel_section_key ) )
            tool_section = None
    else:
        tool_section = None
    if isinstance( repo_info_dict, basestring ):
        repo_info_dict = encoding_util.tool_shed_decode( repo_info_dict )
    # Clone each repository to the configured location.
    suc.update_tool_shed_repository_status( trans.app,
                                            tool_shed_repository,
                                            trans.install_model.ToolShedRepository.installation_status.CLONING )
    repo_info_tuple = repo_info_dict[ tool_shed_repository.name ]
    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = repo_info_tuple
    relative_clone_dir = suc.generate_tool_shed_repository_install_dir( repository_clone_url,
                                                                        tool_shed_repository.installed_changeset_revision )
    clone_dir = os.path.join( tool_path, relative_clone_dir )
    relative_install_dir = os.path.join( relative_clone_dir, tool_shed_repository.name )
    install_dir = os.path.join( tool_path, relative_install_dir )
    cloned_ok, error_message = hg_util.clone_repository( repository_clone_url, os.path.abspath( install_dir ), ctx_rev )
    if cloned_ok:
        if reinstalling:
            # Since we're reinstalling the repository we need to find the latest changeset revision to which it can be updated.
            changeset_revision_dict = get_update_to_changeset_revision_and_ctx_rev( trans, tool_shed_repository )
            current_changeset_revision = changeset_revision_dict.get( 'changeset_revision', None )
            current_ctx_rev = changeset_revision_dict.get( 'ctx_rev', None )
            if current_ctx_rev != ctx_rev:
                repo = hg.repository( hg_util.get_configured_ui(), path=os.path.abspath( install_dir ) )
                pull_repository( repo, repository_clone_url, current_changeset_revision )
                hg_util.update_repository( repo, ctx_rev=current_ctx_rev )
        handle_repository_contents( trans,
                                    tool_shed_repository=tool_shed_repository,
                                    tool_path=tool_path,
                                    repository_clone_url=repository_clone_url,
                                    relative_install_dir=relative_install_dir,
                                    tool_shed=tool_shed_repository.tool_shed,
                                    tool_section=tool_section,
                                    shed_tool_conf=shed_tool_conf,
                                    reinstalling=reinstalling )
        trans.install_model.context.refresh( tool_shed_repository )
        metadata = tool_shed_repository.metadata
        if 'tools' in metadata:
            # Get the tool_versions from the tool shed for each tool in the installed change set.
            suc.update_tool_shed_repository_status( trans.app,
                                                    tool_shed_repository,
                                                    trans.install_model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS )
            tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( trans.app, str( tool_shed_repository.tool_shed ) )
            params = '?name=%s&owner=%s&changeset_revision=%s' % ( str( tool_shed_repository.name ),
                                                                   str( tool_shed_repository.owner ),
                                                                   str( tool_shed_repository.changeset_revision ) )
            url = common_util.url_join( tool_shed_url,
                                        '/repository/get_tool_versions%s' % params )
            text = common_util.tool_shed_get( trans.app, tool_shed_url, url )
            if text:
                tool_version_dicts = json.from_json_string( text )
                tool_util.handle_tool_versions( trans.app, tool_version_dicts, tool_shed_repository )
            else:
                if not error_message:
                    error_message = ""
                error_message += "Version information for the tools included in the <b>%s</b> repository is missing.  " % tool_shed_repository.name
                error_message += "Reset all of this repository's metadata in the tool shed, then set the installed tool versions "
                error_message += "from the installed repository's <b>Repository Actions</b> menu.  "
        if install_tool_dependencies and tool_shed_repository.tool_dependencies and 'tool_dependencies' in metadata:
            work_dir = tempfile.mkdtemp( prefix="tmp-toolshed-itsr" )
            # Install tool dependencies.
            suc.update_tool_shed_repository_status( trans.app,
                                                    tool_shed_repository,
                                                    trans.install_model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES )
            # Get the tool_dependencies.xml file from the repository.
            tool_dependencies_config = suc.get_config_from_disk( 'tool_dependencies.xml', install_dir )
            installed_tool_dependencies = \
                common_install_util.install_specified_tool_dependencies( app=trans.app,
                                                                         tool_shed_repository=tool_shed_repository,
                                                                         tool_dependencies_config=tool_dependencies_config,
                                                                         tool_dependencies=tool_shed_repository.tool_dependencies,
                                                                         from_tool_migration_manager=False )
            suc.remove_dir( work_dir )
        suc.update_tool_shed_repository_status( trans.app,
                                                tool_shed_repository,
                                                trans.install_model.ToolShedRepository.installation_status.INSTALLED )
        if trans.app.config.manage_dependency_relationships:
            # Add the installed repository and any tool dependencies to the in-memory dictionaries in the installed_repository_manager.
            trans.app.installed_repository_manager.handle_repository_install( tool_shed_repository )
    else:
        # An error occurred while cloning the repository, so reset everything necessary to enable another attempt.
        set_repository_attributes( trans,
                                   tool_shed_repository,
                                   status=trans.install_model.ToolShedRepository.installation_status.ERROR,
                                   error_message=error_message,
                                   deleted=False,
                                   uninstalled=False,
                                   remove_from_disk=True )

def merge_containers_dicts_for_new_install( containers_dicts ):
    """
    When installing one or more tool shed repositories for the first time, the received list of containers_dicts contains a containers_dict for
    each repository being installed.  Since the repositories are being installed for the first time, all entries are None except the repository
    dependencies and tool dependencies.  The entries for missing dependencies are all None since they have previously been merged into the installed
    dependencies.  This method will merge the dependencies entries into a single container and return it for display.
    """
    new_containers_dict = dict( readme_files=None,
                                datatypes=None,
                                missing_repository_dependencies=None,
                                repository_dependencies=None,
                                missing_tool_dependencies=None,
                                tool_dependencies=None,
                                invalid_tools=None,
                                valid_tools=None,
                                workflows=None )
    if containers_dicts:
        lock = threading.Lock()
        lock.acquire( True )
        try:
            repository_dependencies_root_folder = None
            tool_dependencies_root_folder = None
            # Use a unique folder id (hopefully the following is).
            folder_id = 867
            for old_container_dict in containers_dicts:
                # Merge repository_dependencies.
                old_container_repository_dependencies_root = old_container_dict[ 'repository_dependencies' ]
                if old_container_repository_dependencies_root:
                    if repository_dependencies_root_folder is None:
                        repository_dependencies_root_folder = container_util.Folder( id=folder_id, key='root', label='root', parent=None )
                        folder_id += 1
                        repository_dependencies_folder = container_util.Folder( id=folder_id,
                                                                                key='merged',
                                                                                label='Repository dependencies',
                                                                                parent=repository_dependencies_root_folder )
                        folder_id += 1
                    # The old_container_repository_dependencies_root will be a root folder containing a single sub_folder.
                    old_container_repository_dependencies_folder = old_container_repository_dependencies_root.folders[ 0 ]
                    # Change the folder id so it won't confict with others being merged.
                    old_container_repository_dependencies_folder.id = folder_id
                    folder_id += 1
                    repository_components_tuple = container_util.get_components_from_key( old_container_repository_dependencies_folder.key )
                    components_list = suc.extract_components_from_tuple( repository_components_tuple )
                    name = components_list[ 1 ]
                    # Generate the label by retrieving the repository name.
                    old_container_repository_dependencies_folder.label = str( name )
                    repository_dependencies_folder.folders.append( old_container_repository_dependencies_folder )
                # Merge tool_dependencies.
                old_container_tool_dependencies_root = old_container_dict[ 'tool_dependencies' ]
                if old_container_tool_dependencies_root:
                    if tool_dependencies_root_folder is None:
                        tool_dependencies_root_folder = container_util.Folder( id=folder_id, key='root', label='root', parent=None )
                        folder_id += 1
                        tool_dependencies_folder = container_util.Folder( id=folder_id,
                                                                          key='merged',
                                                                          label='Tool dependencies',
                                                                          parent=tool_dependencies_root_folder )
                        folder_id += 1
                    else:
                        td_list = [ td.listify for td in tool_dependencies_folder.tool_dependencies ]
                        # The old_container_tool_dependencies_root will be a root folder containing a single sub_folder.
                        old_container_tool_dependencies_folder = old_container_tool_dependencies_root.folders[ 0 ]
                        for td in old_container_tool_dependencies_folder.tool_dependencies:
                            if td.listify not in td_list:
                                tool_dependencies_folder.tool_dependencies.append( td )
            if repository_dependencies_root_folder:
                repository_dependencies_root_folder.folders.append( repository_dependencies_folder )
                new_containers_dict[ 'repository_dependencies' ] = repository_dependencies_root_folder
            if tool_dependencies_root_folder:
                tool_dependencies_root_folder.folders.append( tool_dependencies_folder )
                new_containers_dict[ 'tool_dependencies' ] = tool_dependencies_root_folder
        except Exception, e:
            log.debug( "Exception in merge_containers_dicts_for_new_install: %s" % str( e ) )
        finally:
            lock.release()
    return new_containers_dict

def order_components_for_installation( trans, tsr_ids, repo_info_dicts, tool_panel_section_keys ):
    """
    Some repositories may have repository dependencies that are required to be installed before the dependent repository. 
    This method will inspect the list of repositories about to be installed and make sure to order them appropriately.
    For each repository about to be installed, if required repositories are not contained in the list of repositories about
    to be installed, then they are not considered.  Repository dependency definitions that contain circular dependencies
    should not result in an infinite loop, but obviously prior installation will not be handled for one or more of the
    repositories that require prior installation.
    """
    ordered_tsr_ids = []
    ordered_repo_info_dicts = []
    ordered_tool_panel_section_keys = []
    # Create a dictionary whose keys are the received tsr_ids and whose values are a list of tsr_ids, each of which is
    # contained in the received list of tsr_ids and whose associated repository must be installed prior to the repository
    # associated with the tsr_id key.
    prior_install_required_dict = suc.get_prior_import_or_install_required_dict( trans, tsr_ids, repo_info_dicts )
    processed_tsr_ids = []
    while len( processed_tsr_ids ) != len( prior_install_required_dict.keys() ):
        tsr_id = suc.get_next_prior_import_or_install_required_dict_entry( prior_install_required_dict, processed_tsr_ids )
        processed_tsr_ids.append( tsr_id )
        # Create the ordered_tsr_ids, the ordered_repo_info_dicts and the ordered_tool_panel_section_keys lists.
        if tsr_id not in ordered_tsr_ids:
            prior_install_required_ids = prior_install_required_dict[ tsr_id ]
            for prior_install_required_id in prior_install_required_ids:
                if prior_install_required_id not in ordered_tsr_ids:
                    # Install the associated repository dependency first.
                    prior_repo_info_dict, prior_tool_panel_section_key = \
                        get_repository_components_for_installation( prior_install_required_id,
                                                                    tsr_ids,
                                                                    repo_info_dicts,
                                                                    tool_panel_section_keys=tool_panel_section_keys )
                    ordered_tsr_ids.append( prior_install_required_id )
                    ordered_repo_info_dicts.append( prior_repo_info_dict )
                    ordered_tool_panel_section_keys.append( prior_tool_panel_section_key )
            repo_info_dict, tool_panel_section_key = \
                get_repository_components_for_installation( tsr_id,
                                                            tsr_ids,
                                                            repo_info_dicts,
                                                            tool_panel_section_keys=tool_panel_section_keys )
            ordered_tsr_ids.append( tsr_id )
            ordered_repo_info_dicts.append( repo_info_dict )
            ordered_tool_panel_section_keys.append( tool_panel_section_key )
    return ordered_tsr_ids, ordered_repo_info_dicts, ordered_tool_panel_section_keys

def populate_containers_dict_for_new_install( trans, tool_shed_url, tool_path, readme_files_dict, installed_repository_dependencies,
                                              missing_repository_dependencies, installed_tool_dependencies, missing_tool_dependencies,
                                              updating=False ):
    """
    Return the populated containers for a repository being installed for the first time or for an installed repository
    that is being updated and the updates include newly defined repository (and possibly tool) dependencies.
    """
    installed_tool_dependencies, missing_tool_dependencies = \
        tool_dependency_util.populate_tool_dependencies_dicts( trans=trans,
                                                               tool_shed_url=tool_shed_url,
                                                               tool_path=tool_path,
                                                               repository_installed_tool_dependencies=installed_tool_dependencies,
                                                               repository_missing_tool_dependencies=missing_tool_dependencies,
                                                               required_repo_info_dicts=None )
    # Most of the repository contents are set to None since we don't yet know what they are.
    containers_dict = \
        container_util.build_repository_containers_for_galaxy( trans=trans,
                                                               repository=None,
                                                               datatypes=None,
                                                               invalid_tools=None,
                                                               missing_repository_dependencies=missing_repository_dependencies,
                                                               missing_tool_dependencies=missing_tool_dependencies,
                                                               readme_files_dict=readme_files_dict,
                                                               repository_dependencies=installed_repository_dependencies,
                                                               tool_dependencies=installed_tool_dependencies,
                                                               valid_tools=None,
                                                               workflows=None,
                                                               valid_data_managers=None,
                                                               invalid_data_managers=None,
                                                               data_managers_errors=None,
                                                               new_install=True,
                                                               reinstalling=False )
    if not updating:
        # If we installing a new repository and not updaing an installed repository, we can merge
        # the missing_repository_dependencies container contents to the installed_repository_dependencies
        # container.  When updating an installed repository, merging will result in losing newly defined
        # dependencies included in the updates.
        containers_dict = repository_dependency_util.merge_missing_repository_dependencies_to_installed_container( containers_dict )
        # Merge the missing_tool_dependencies container contents to the installed_tool_dependencies container.
        containers_dict = tool_dependency_util.merge_missing_tool_dependencies_to_installed_container( containers_dict )
    return containers_dict

def pull_repository( repo, repository_clone_url, ctx_rev ):
    """Pull changes from a remote repository to a local one."""
    commands.pull( hg_util.get_configured_ui(), repo, source=repository_clone_url, rev=[ ctx_rev ] )

def repair_tool_shed_repository( trans, repository, repo_info_dict ):

    def add_repair_dict_entry( repository_name, error_message ):
        if repository_name in repair_dict:
            repair_dict[ repository_name ].append( error_message )
        else:
            repair_dict[ repository_name ] = [ error_message ]
        return repair_dict

    metadata = repository.metadata
    repair_dict = {}
    if repository.status in [ trans.install_model.ToolShedRepository.installation_status.DEACTIVATED ]:
        try:
            common_install_util.activate_repository( trans, repository )
        except Exception, e:
            error_message = "Error activating repository %s: %s" % ( repository.name, str( e ) )
            log.debug( error_message )
            repair_dict [ repository.name ] = error_message
    elif repository.status not in [ trans.install_model.ToolShedRepository.installation_status.INSTALLED ]:
        shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        # Reset the repository attributes to the New state for installation.
        if metadata:
            tool_section, tool_panel_section_key = \
                tool_util.handle_tool_panel_selection( trans,
                                                       metadata,
                                                       no_changes_checked=True,
                                                       tool_panel_section_id=None,
                                                       new_tool_panel_section_label=None )
        else:
            # The tools will be loaded outside of any sections in the tool panel.
            tool_panel_section_key = None
        set_repository_attributes( trans,
                                   repository,
                                   status=trans.install_model.ToolShedRepository.installation_status.NEW,
                                   error_message=None,
                                   deleted=False,
                                   uninstalled=False,
                                   remove_from_disk=True )
        install_tool_shed_repository( trans,
                                      repository,
                                      repo_info_dict,
                                      tool_panel_section_key,
                                      shed_tool_conf,
                                      tool_path,
                                      install_tool_dependencies=True,
                                      reinstalling=True )
        if repository.status in [ trans.install_model.ToolShedRepository.installation_status.ERROR ]:
            repair_dict = add_repair_dict_entry( repository.name, repository.error_message )
    else:
        # We have an installed tool shed repository, so handle tool dependencies if necessary.
        if repository.missing_tool_dependencies and metadata and 'tool_dependencies' in metadata:
            work_dir = tempfile.mkdtemp( prefix="tmp-toolshed-itdep" )
            # Reset missing tool dependencies.
            for tool_dependency in repository.missing_tool_dependencies:
                if tool_dependency.status in [ trans.install_model.ToolDependency.installation_status.ERROR,
                                               trans.install_model.ToolDependency.installation_status.INSTALLING ]:
                    tool_dependency = \
                        tool_dependency_util.set_tool_dependency_attributes( trans.app,
                                                                             tool_dependency=tool_dependency,
                                                                             status=trans.install_model.ToolDependency.installation_status.UNINSTALLED,
                                                                             error_message=None,
                                                                             remove_from_disk=True )
            # Install tool dependencies.
            suc.update_tool_shed_repository_status( trans.app,
                                                    repository,
                                                    trans.install_model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES )
            # Get the tool_dependencies.xml file from the repository.
            tool_dependencies_config = suc.get_config_from_disk( 'tool_dependencies.xml', repository.repo_path( trans.app ) )
            installed_tool_dependencies = \
                common_install_util.install_specified_tool_dependencies( app=trans.app,
                                                                         tool_shed_repository=repository,
                                                                         tool_dependencies_config=tool_dependencies_config,
                                                                         tool_dependencies=repository.tool_dependencies,
                                                                         from_tool_migration_manager=False )
            for installed_tool_dependency in installed_tool_dependencies:
                if installed_tool_dependency.status in [ trans.install_model.ToolDependency.installation_status.ERROR ]:
                    repair_dict = add_repair_dict_entry( repository.name, installed_tool_dependency.error_message )
            suc.remove_dir( work_dir )
        suc.update_tool_shed_repository_status( trans.app, repository, trans.install_model.ToolShedRepository.installation_status.INSTALLED )
    return repair_dict

def set_repository_attributes( trans, repository, status, error_message, deleted, uninstalled, remove_from_disk=False ):
    if remove_from_disk:
        relative_install_dir = repository.repo_path( trans.app )
        if relative_install_dir:
            clone_dir = os.path.abspath( relative_install_dir )
            try:
                shutil.rmtree( clone_dir )
                log.debug( "Removed repository installation directory: %s" % str( clone_dir ) )
            except Exception, e:
                log.debug( "Error removing repository installation directory %s: %s" % ( str( clone_dir ), str( e ) ) )
    repository.error_message = error_message
    repository.status = status
    repository.deleted = deleted
    repository.uninstalled = uninstalled
    trans.install_model.context.add( repository )
    trans.install_model.context.flush()

def update_repository_record( trans, repository, updated_metadata_dict, updated_changeset_revision, updated_ctx_rev ):
    """
    Update a tool_shed_repository database record with new information retrieved from the
    Tool Shed.  This happens when updating an installed repository to a new changeset revision.
    """
    repository.metadata = updated_metadata_dict
    # Update the repository.changeset_revision column in the database.
    repository.changeset_revision = updated_changeset_revision
    repository.ctx_rev = updated_ctx_rev
    # Update the repository.tool_shed_status column in the database.
    tool_shed_status_dict = suc.get_tool_shed_status_for_installed_repository( trans.app, repository )
    if tool_shed_status_dict:
        repository.tool_shed_status = tool_shed_status_dict
    else:
        repository.tool_shed_status = None
    trans.install_model.context.add( repository )
    trans.install_model.context.flush()
    trans.install_model.context.refresh( repository )
    return repository
