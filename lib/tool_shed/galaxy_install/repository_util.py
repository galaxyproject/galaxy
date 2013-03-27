import logging
import os
import shutil
import tempfile
import threading
import urllib2
from galaxy import tools
from galaxy.util import json
from galaxy import web
from galaxy.model.orm import or_
from galaxy.webapps.tool_shed.util import container_util
import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_install_util
from tool_shed.util import data_manager_util
from tool_shed.util import datatype_util
from tool_shed.util import encoding_util
from tool_shed.util import repository_dependency_util
from tool_shed.util import metadata_util
from tool_shed.util import tool_dependency_util
from tool_shed.util import tool_util

from galaxy import eggs
import pkg_resources

pkg_resources.require( 'mercurial' )
from mercurial import commands
from mercurial import hg
from mercurial import ui

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree
from elementtree.ElementTree import Element

log = logging.getLogger( __name__ )

def create_repo_info_dict( trans, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_name=None, repository=None,
                           repository_metadata=None, tool_dependencies=None, repository_dependencies=None ):
    """
    Return a dictionary that includes all of the information needed to install a repository into a local Galaxy instance.  The dictionary will also
    contain the recursive list of repository dependencies defined for the repository, as well as the defined tool dependencies.  
    
    This method is called from Galaxy under three scenarios:
    1. During the tool shed repository installation process via the tool shed's get_repository_information() method.  In this case both the received
    repository and repository_metadata will be objects., but tool_dependencies and repository_dependencies will be None
    2. When a tool shed repository that was uninstalled from a Galaxy instance is being reinstalled with no updates available.  In this case, both
    repository and repository_metadata will be None, but tool_dependencies and repository_dependencies will be objects previously retrieved from the
    tool shed if the repository includes definitions for them.
    3. When a tool shed repository that was uninstalled from a Galaxy instance is being reinstalled with updates available.  In this case, this
    method is reached via the tool shed's get_updated_repository_information() method, and both repository and repository_metadata will be objects
    but tool_dependencies and repository_dependencies will be None.
    """
    repo_info_dict = {}
    repository = suc.get_repository_by_name_and_owner( trans.app, repository_name, repository_owner )
    if trans.webapp.name == 'tool_shed':
        # We're in the tool shed.
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, trans.security.encode_id( repository.id ), changeset_revision )
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                # Get a dictionary of all repositories upon which the contents of the received repository depends.
                repository_dependencies = \
                    repository_dependency_util.get_repository_dependencies_for_changeset_revision( trans=trans,
                                                                                                   repository=repository,
                                                                                                   repository_metadata=repository_metadata,
                                                                                                   toolshed_base_url=str( web.url_for( '/', qualified=True ) ).rstrip( '/' ),
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
    # Cast unicode to string.
    repo_info_dict[ str( repository.name ) ] = ( str( repository.description ),
                                                 str( repository_clone_url ),
                                                 str( changeset_revision ),
                                                 str( ctx_rev ),
                                                 str( repository_owner ),
                                                 repository_dependencies,
                                                 tool_dependencies )
    return repo_info_dict

def get_repo_info_dict( trans, repository_id, changeset_revision ):
    repository = suc.get_repository_in_tool_shed( trans, repository_id )
    repository_clone_url = suc.generate_clone_url_for_repository_in_tool_shed( trans, repository )
    repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, repository_id, changeset_revision )
    metadata = repository_metadata.metadata
    if 'tools' in metadata:
        includes_tools = True
    else:
        includes_tools = False
    includes_tools_for_display_in_tool_panel = repository_metadata.includes_tools_for_display_in_tool_panel
    if 'repository_dependencies' in metadata:
        has_repository_dependencies = True
    else:
        has_repository_dependencies = False
    if 'tool_dependencies' in metadata:
        includes_tool_dependencies = True
    else:
        includes_tool_dependencies = False
    repo_dir = repository.repo_path( trans.app )
    repo = hg.repository( suc.get_configured_ui(), repo_dir )
    ctx = suc.get_changectx_for_changeset( repo, changeset_revision )
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
    return repo_info_dict, includes_tools, includes_tool_dependencies, includes_tools_for_display_in_tool_panel, has_repository_dependencies

def get_update_to_changeset_revision_and_ctx_rev( trans, repository ):
    """Return the changeset revision hash to which the repository can be updated."""
    changeset_revision_dict = {}
    tool_shed_url = suc.get_url_from_tool_shed( trans.app, repository.tool_shed )
    url = suc.url_join( tool_shed_url, 'repository/get_changeset_revision_and_ctx_rev?name=%s&owner=%s&changeset_revision=%s' % \
        ( repository.name, repository.owner, repository.installed_changeset_revision ) )
    try:
        response = urllib2.urlopen( url )
        encoded_update_dict = response.read()
        if encoded_update_dict:
            update_dict = encoding_util.tool_shed_decode( encoded_update_dict )
            includes_data_managers = update_dict.get( 'includes_data_managers', False )
            includes_datatypes = update_dict.get( 'includes_datatypes', False )
            includes_tools = update_dict.get( 'includes_tools', False )
            includes_tools_for_display_in_tool_panel = update_dict.get( 'includes_tools_for_display_in_tool_panel', False )
            includes_tool_dependencies = update_dict.get( 'includes_tool_dependencies', False )
            includes_workflows = update_dict.get( 'includes_workflows', False )
            has_repository_dependencies = update_dict.get( 'has_repository_dependencies', False )
            changeset_revision = update_dict.get( 'changeset_revision', None )
            ctx_rev = update_dict.get( 'ctx_rev', None )
        response.close()
        changeset_revision_dict[ 'includes_data_managers' ] = includes_data_managers
        changeset_revision_dict[ 'includes_datatypes' ] = includes_datatypes
        changeset_revision_dict[ 'includes_tools' ] = includes_tools
        changeset_revision_dict[ 'includes_tools_for_display_in_tool_panel' ] = includes_tools_for_display_in_tool_panel
        changeset_revision_dict[ 'includes_tool_dependencies' ] = includes_tool_dependencies
        changeset_revision_dict[ 'includes_workflows' ] = includes_workflows
        changeset_revision_dict[ 'has_repository_dependencies' ] = has_repository_dependencies
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
        changeset_revision_dict[ 'changeset_revision' ] = None
        changeset_revision_dict[ 'ctx_rev' ] = None
    return changeset_revision_dict

def handle_repository_contents( trans, tool_shed_repository, tool_path, repository_clone_url, relative_install_dir, tool_shed=None, tool_section=None, shed_tool_conf=None,
                                reinstalling=False ):
    """
    Generate the metadata for the installed tool shed repository, among other things.  This method is called from Galaxy (never the tool shed)
    when an administrator is installing a new repository or reinstalling an uninstalled repository.
    """
    shed_config_dict = trans.app.toolbox.get_shed_config_dict_by_filename( shed_tool_conf )
    metadata_dict, invalid_file_tups = metadata_util.generate_metadata_for_changeset_revision( app=trans.app,
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
    trans.sa_session.add( tool_shed_repository )
    trans.sa_session.flush()
    if 'tool_dependencies' in metadata_dict and not reinstalling:
        tool_dependencies = tool_dependency_util.create_tool_dependency_objects( trans.app, tool_shed_repository, relative_install_dir, set_status=True )
    if 'tools' in metadata_dict:
        tool_panel_dict = tool_util.generate_tool_panel_dict_for_new_install( metadata_dict[ 'tools' ], tool_section )
        sample_files = metadata_dict.get( 'sample_files', [] )
        tool_index_sample_files = tool_util.get_tool_index_sample_files( sample_files )
        tool_util.copy_sample_files( trans.app, tool_index_sample_files, tool_path=tool_path )
        sample_files_copied = [ str( s ) for s in tool_index_sample_files ]
        repository_tools_tups = suc.get_repository_tools_tups( trans.app, metadata_dict )
        if repository_tools_tups:
            # Handle missing data table entries for tool parameters that are dynamically generated select lists.
            repository_tools_tups = tool_util.handle_missing_data_table_entry( trans.app, relative_install_dir, tool_path, repository_tools_tups )
            # Handle missing index files for tool parameters that are dynamically generated select lists.
            repository_tools_tups, sample_files_copied = tool_util.handle_missing_index_file( trans.app, tool_path, sample_files, repository_tools_tups, sample_files_copied )
            # Copy remaining sample files included in the repository to the ~/tool-data directory of the local Galaxy instance.
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
        tool_shed_repository.status = trans.model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES
        if not tool_shed_repository.includes_datatypes:
            tool_shed_repository.includes_datatypes = True
        trans.sa_session.add( tool_shed_repository )
        trans.sa_session.flush()
        files_dir = relative_install_dir
        if shed_config_dict.get( 'tool_path' ):
            files_dir = os.path.join( shed_config_dict[ 'tool_path' ], files_dir )
        datatypes_config = suc.get_config_from_disk( 'datatypes_conf.xml', files_dir )
        # Load data types required by tools.
        converter_path, display_path = datatype_util.alter_config_and_load_prorietary_datatypes( trans.app, datatypes_config, files_dir, override=False )
        if converter_path or display_path:
            # Create a dictionary of tool shed repository related information.
            repository_dict = datatype_util.create_repository_dict_for_proprietary_datatypes( tool_shed=tool_shed,
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
    new_tool_panel_section = installation_dict[ 'new_tool_panel_section' ]
    no_changes_checked = installation_dict[ 'no_changes_checked' ]
    reinstalling = installation_dict[ 'reinstalling' ]
    repo_info_dicts = installation_dict[ 'repo_info_dicts' ]
    tool_panel_section = installation_dict[ 'tool_panel_section' ]
    tool_path = installation_dict[ 'tool_path' ]
    tool_shed_url = installation_dict[ 'tool_shed_url' ]
    created_or_updated_tool_shed_repositories, tool_panel_section_keys, repo_info_dicts, filtered_repo_info_dicts, message = \
        repository_dependency_util.create_repository_dependency_objects( trans=trans,
                                                                         tool_path=tool_path,
                                                                         tool_shed_url=tool_shed_url,
                                                                         repo_info_dicts=repo_info_dicts,
                                                                         reinstalling=reinstalling,
                                                                         install_repository_dependencies=install_repository_dependencies,
                                                                         no_changes_checked=no_changes_checked,
                                                                         tool_panel_section=tool_panel_section,
                                                                         new_tool_panel_section=new_tool_panel_section )
    if message and len( repo_info_dicts ) == 1 and not using_api:
        installed_tool_shed_repository = created_or_updated_tool_shed_repositories[ 0 ]
        message += 'Click <a href="%s">here</a> to manage the repository.  ' % \
            ( web.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( installed_tool_shed_repository.id ) ) )
    return created_or_updated_tool_shed_repositories, tool_panel_section_keys, repo_info_dicts, filtered_repo_info_dicts, message

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
    new_tool_panel_section = installation_dict[ 'new_tool_panel_section' ]
    shed_tool_conf = installation_dict[ 'shed_tool_conf' ]
    status = installation_dict[ 'status' ]
    tool_panel_section = installation_dict[ 'tool_panel_section' ]
    tool_panel_section_keys = installation_dict[ 'tool_panel_section_keys' ]
    tool_path = installation_dict[ 'tool_path' ]
    tool_shed_url = installation_dict[ 'tool_shed_url' ]
    # Handle contained tools.
    if includes_tools_for_display_in_tool_panel and ( new_tool_panel_section or tool_panel_section ):
        if new_tool_panel_section:
            section_id = new_tool_panel_section.lower().replace( ' ', '_' )
            tool_panel_section_key = 'section_%s' % str( section_id )
            if tool_panel_section_key in trans.app.toolbox.tool_panel:
                # Appending a tool to an existing section in trans.app.toolbox.tool_panel
                log.debug( "Appending to tool panel section: %s" % new_tool_panel_section )
                tool_section = trans.app.toolbox.tool_panel[ tool_panel_section_key ]
            else:
                # Appending a new section to trans.app.toolbox.tool_panel
                log.debug( "Loading new tool panel section: %s" % new_tool_panel_section )
                elem = Element( 'section' )
                elem.attrib[ 'name' ] = new_tool_panel_section
                elem.attrib[ 'id' ] = section_id
                elem.attrib[ 'version' ] = ''
                tool_section = tools.ToolSection( elem )
                trans.app.toolbox.tool_panel[ tool_panel_section_key ] = tool_section
        else:
            tool_panel_section_key = 'section_%s' % tool_panel_section
            tool_section = trans.app.toolbox.tool_panel[ tool_panel_section_key ]
    else:
        tool_panel_section_key = None
        tool_section = None
    encoded_repository_ids = [ trans.security.encode_id( tsr.id ) for tsr in created_or_updated_tool_shed_repositories ]
    # Create a one-to-one mapping of tool shed repository id and tool panel section key.  All tools contained in the repositories being installed will be loaded
    # into the same section in the tool panel.
    for tsr in created_or_updated_tool_shed_repositories:
        tool_panel_section_keys.append( tool_panel_section_key )
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
        tsr = trans.sa_session.query( trans.model.ToolShedRepository ).get( tsr_id )
        tool_shed_repositories.append( tsr )
    clause_list = []
    for tsr_id in tsr_ids:
        clause_list.append( trans.model.ToolShedRepository.table.c.id == tsr_id )
    query = trans.sa_session.query( trans.model.ToolShedRepository ).filter( or_( *clause_list ) )
    return encoded_kwd, query, tool_shed_repositories, encoded_repository_ids

def install_tool_shed_repository( trans, tool_shed_repository, repo_info_dict, tool_panel_section_key, shed_tool_conf, tool_path, install_tool_dependencies,
                                  reinstalling=False ):
    if tool_panel_section_key:
        tool_section = trans.app.toolbox.tool_panel[ tool_panel_section_key ]
    else:
        tool_section = None
    if isinstance( repo_info_dict, basestring ):
        repo_info_dict = encoding_util.tool_shed_decode( repo_info_dict )
    # Clone each repository to the configured location.
    suc.update_tool_shed_repository_status( trans.app, tool_shed_repository, trans.model.ToolShedRepository.installation_status.CLONING )
    repo_info_tuple = repo_info_dict[ tool_shed_repository.name ]
    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = repo_info_tuple
    relative_clone_dir = suc.generate_tool_shed_repository_install_dir( repository_clone_url, tool_shed_repository.installed_changeset_revision )
    clone_dir = os.path.join( tool_path, relative_clone_dir )
    relative_install_dir = os.path.join( relative_clone_dir, tool_shed_repository.name )
    install_dir = os.path.join( tool_path, relative_install_dir )
    cloned_ok, error_message = suc.clone_repository( repository_clone_url, os.path.abspath( install_dir ), ctx_rev )
    if cloned_ok:
        if reinstalling:
            # Since we're reinstalling the repository we need to find the latest changeset revision to which is can be updated.
            changeset_revision_dict = get_update_to_changeset_revision_and_ctx_rev( trans, tool_shed_repository )
            current_changeset_revision = changeset_revision_dict.get( 'changeset_revision', None )
            current_ctx_rev = changeset_revision_dict.get( 'ctx_rev', None )
            if current_ctx_rev != ctx_rev:
                repo = hg.repository( suc.get_configured_ui(), path=os.path.abspath( install_dir ) )
                pull_repository( repo, repository_clone_url, current_changeset_revision )
                suc.update_repository( repo, ctx_rev=current_ctx_rev )
        handle_repository_contents( trans,
                                    tool_shed_repository=tool_shed_repository,
                                    tool_path=tool_path,
                                    repository_clone_url=repository_clone_url,
                                    relative_install_dir=relative_install_dir,
                                    tool_shed=tool_shed_repository.tool_shed,
                                    tool_section=tool_section,
                                    shed_tool_conf=shed_tool_conf,
                                    reinstalling=reinstalling )
        trans.sa_session.refresh( tool_shed_repository )
        metadata = tool_shed_repository.metadata
        if 'tools' in metadata:
            # Get the tool_versions from the tool shed for each tool in the installed change set.
            suc.update_tool_shed_repository_status( trans.app,
                                                    tool_shed_repository,
                                                    trans.model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS )
            tool_shed_url = suc.get_url_from_tool_shed( trans.app, tool_shed_repository.tool_shed )
            url = suc.url_join( tool_shed_url,
                                '/repository/get_tool_versions?name=%s&owner=%s&changeset_revision=%s' % \
                                ( tool_shed_repository.name, tool_shed_repository.owner, tool_shed_repository.changeset_revision ) )
            response = urllib2.urlopen( url )
            text = response.read()
            response.close()
            if text:
                tool_version_dicts = json.from_json_string( text )
                tool_util.handle_tool_versions( trans.app, tool_version_dicts, tool_shed_repository )
            else:
                message += "Version information for the tools included in the <b>%s</b> repository is missing.  " % name
                message += "Reset all of this repository's metadata in the tool shed, then set the installed tool versions "
                message += "from the installed repository's <b>Repository Actions</b> menu.  "
                status = 'error'
        if install_tool_dependencies and tool_shed_repository.tool_dependencies and 'tool_dependencies' in metadata:
            work_dir = tempfile.mkdtemp()
            # Install tool dependencies.
            suc.update_tool_shed_repository_status( trans.app,
                                                    tool_shed_repository,
                                                    trans.model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES )
            # Get the tool_dependencies.xml file from the repository.
            tool_dependencies_config = suc.get_config_from_disk( 'tool_dependencies.xml', install_dir )#relative_install_dir )
            installed_tool_dependencies = common_install_util.handle_tool_dependencies( app=trans.app,
                                                                                        tool_shed_repository=tool_shed_repository,
                                                                                        tool_dependencies_config=tool_dependencies_config,
                                                                                        tool_dependencies=tool_shed_repository.tool_dependencies )
            try:
                shutil.rmtree( work_dir )
            except:
                pass
        suc.update_tool_shed_repository_status( trans.app, tool_shed_repository, trans.model.ToolShedRepository.installation_status.INSTALLED )
    else:
        # An error occurred while cloning the repository, so reset everything necessary to enable another attempt.
        suc.set_repository_attributes( trans,
                                       tool_shed_repository,
                                       status=trans.model.ToolShedRepository.installation_status.ERROR,
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
                    # Generate the label by retrieving the repository name.
                    toolshed, name, owner, changeset_revision = container_util.get_components_from_key( old_container_repository_dependencies_folder.key )
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

def populate_containers_dict_for_new_install( trans, tool_shed_url, tool_path, readme_files_dict, installed_repository_dependencies, missing_repository_dependencies,
                                              installed_tool_dependencies, missing_tool_dependencies ):
    """Return the populated containers for a repository being installed for the first time."""
    installed_tool_dependencies, missing_tool_dependencies = \
        tool_dependency_util.populate_tool_dependencies_dicts( trans=trans,
                                                               tool_shed_url=tool_shed_url,
                                                               tool_path=tool_path,
                                                               repository_installed_tool_dependencies=installed_tool_dependencies,
                                                               repository_missing_tool_dependencies=missing_tool_dependencies,
                                                               required_repo_info_dicts=None )
    # Since we are installing a new repository, most of the repository contents are set to None since we don't yet know what they are.
    containers_dict = container_util.build_repository_containers_for_galaxy( trans=trans,
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
    # Merge the missing_repository_dependencies container contents to the installed_repository_dependencies container.
    containers_dict = repository_dependency_util.merge_missing_repository_dependencies_to_installed_container( containers_dict )
    # Merge the missing_tool_dependencies container contents to the installed_tool_dependencies container.
    containers_dict = tool_dependency_util.merge_missing_tool_dependencies_to_installed_container( containers_dict )
    return containers_dict

def pull_repository( repo, repository_clone_url, ctx_rev ):
    """Pull changes from a remote repository to a local one."""
    commands.pull( suc.get_configured_ui(), repo, source=repository_clone_url, rev=[ ctx_rev ] )
