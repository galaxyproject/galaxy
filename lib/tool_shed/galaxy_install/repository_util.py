import os, logging, threading, urllib2
from galaxy.web import url_for
from galaxy.webapps.tool_shed.util import container_util
import tool_shed.util.shed_util_common as suc
from tool_shed.util import encoding_util, repository_dependency_util, tool_dependency_util, tool_util

from galaxy import eggs
import pkg_resources

pkg_resources.require( 'mercurial' )
from mercurial import hg, ui, commands

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
                                                                                                   toolshed_base_url=str( url_for( '/', qualified=True ) ).rstrip( '/' ),
                                                                                                   key_rd_dicts_to_be_processed=None,
                                                                                                   all_repository_dependencies=None,
                                                                                                   handled_key_rd_dicts=None,
                                                                                                   circular_repository_dependencies=None )
                tool_dependencies = metadata.get( 'tool_dependencies', None )
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

def get_update_to_changeset_revision_and_ctx_rev( trans, repository ):
    """Return the changeset revision hash to which the repository can be updated."""
    changeset_revision_dict = {}
    tool_shed_url = suc.get_url_from_repository_tool_shed( trans.app, repository )
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
    containers_dict = suc.build_repository_containers_for_galaxy( trans=trans,
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
