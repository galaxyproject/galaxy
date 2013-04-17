import logging
import os
from galaxy import eggs
from galaxy import util
from galaxy.util import json
from galaxy.webapps.tool_shed.util import container_util
import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_util
from tool_shed.util import encoding_util
from tool_shed.util import data_manager_util
from tool_shed.util import datatype_util
from tool_shed.util import tool_util
from tool_shed.galaxy_install.tool_dependencies.install_util import install_package
from tool_shed.galaxy_install.tool_dependencies.install_util import set_environment

import pkg_resources

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree
from elementtree import ElementInclude
from elementtree.ElementTree import Element
from elementtree.ElementTree import SubElement

log = logging.getLogger( __name__ )

def activate_repository( trans, repository ):
    """Activate an installed tool shed repository that has been marked as deactivated."""
    repository_clone_url = suc.generate_clone_url_for_installed_repository( trans.app, repository )
    shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir( trans.app, repository )
    repository.deleted = False
    repository.status = trans.model.ToolShedRepository.installation_status.INSTALLED
    if repository.includes_tools_for_display_in_tool_panel:
        metadata = repository.metadata
        repository_tools_tups = suc.get_repository_tools_tups( trans.app, metadata )
        # Reload tools into the appropriate tool panel section.
        tool_panel_dict = repository.metadata[ 'tool_panel_section' ]
        tool_util.add_to_tool_panel( trans.app,
                                     repository.name,
                                     repository_clone_url,
                                     repository.installed_changeset_revision,
                                     repository_tools_tups,
                                     repository.owner,
                                     shed_tool_conf,
                                     tool_panel_dict,
                                     new_install=False )
        if repository.includes_data_managers:
            tp, data_manager_relative_install_dir = repository.get_tool_relative_path( trans.app )
            # Hack to add repository.name here, which is actually the root of the installed repository
            data_manager_relative_install_dir = os.path.join( data_manager_relative_install_dir, repository.name )
            new_data_managers = data_manager_util.install_data_managers( trans.app,
                                                                         trans.app.config.shed_data_manager_config_file,
                                                                         metadata,
                                                                         repository.get_shed_config_dict( trans.app ),
                                                                         data_manager_relative_install_dir,
                                                                         repository,
                                                                         repository_tools_tups )
    trans.sa_session.add( repository )
    trans.sa_session.flush()
    if repository.includes_datatypes:
        if tool_path:
            repository_install_dir = os.path.abspath( os.path.join( tool_path, relative_install_dir ) )
        else:
            repository_install_dir = os.path.abspath( relative_install_dir )
        # Activate proprietary datatypes.
        installed_repository_dict = datatype_util.load_installed_datatypes( trans.app, repository, repository_install_dir, deactivate=False )
        if installed_repository_dict and 'converter_path' in installed_repository_dict:
            datatype_util.load_installed_datatype_converters( trans.app, installed_repository_dict, deactivate=False )
        if installed_repository_dict and 'display_path' in installed_repository_dict:
            datatype_util.load_installed_display_applications( trans.app, installed_repository_dict, deactivate=False )

def get_dependencies_for_repository( trans, tool_shed_url, repo_info_dict, includes_tool_dependencies ):
    """
    Return dictionaries containing the sets of installed and missing tool dependencies and repository dependencies associated with the repository defined
    by the received repo_info_dict.
    """
    name = repo_info_dict.keys()[ 0 ]
    repo_info_tuple = repo_info_dict[ name ]
    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, installed_td = \
        suc.get_repo_info_tuple_contents( repo_info_tuple )
    if repository_dependencies:
        missing_td = {}
        # Handle the scenario where a repository was installed, then uninstalled and an error occurred during the re-installation process.
        # In this case, a record for the repository will exist in the database with the status of 'New'.
        repository = suc.get_repository_for_dependency_relationship( trans.app, tool_shed_url, name, repository_owner, changeset_revision )
        if repository and repository.metadata:
            installed_rd, missing_rd = get_installed_and_missing_repository_dependencies( trans, repository )
        else:
            installed_rd, missing_rd = get_installed_and_missing_repository_dependencies_for_new_install( trans, repo_info_tuple )
        # Discover all repository dependencies and retrieve information for installing them.
        required_repo_info_dicts = get_required_repo_info_dicts( trans, tool_shed_url, util.listify( repo_info_dict ) )
        # Display tool dependencies defined for each of the repository dependencies.
        if required_repo_info_dicts:
            all_tool_dependencies = {}
            for rid in required_repo_info_dicts:
                for name, repo_info_tuple in rid.items():
                    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, rid_installed_td = \
                        suc.get_repo_info_tuple_contents( repo_info_tuple )
                    if rid_installed_td:
                        for td_key, td_dict in rid_installed_td.items():
                            if td_key not in all_tool_dependencies:
                                all_tool_dependencies[ td_key ] = td_dict
            if all_tool_dependencies:
                if installed_td is None:
                    installed_td = {}
                else:
                    # Move all tool dependencies to the missing_tool_dependencies container.
                    for td_key, td_dict in installed_td.items():
                        if td_key not in missing_td:
                            missing_td[ td_key ] = td_dict
                    installed_td = {}
                # Discover and categorize all tool dependencies defined for this repository's repository dependencies.
                required_tool_dependencies, required_missing_tool_dependencies = \
                    get_installed_and_missing_tool_dependencies_for_new_install( trans, all_tool_dependencies )
                if required_tool_dependencies:
                    if not includes_tool_dependencies:
                        includes_tool_dependencies = True
                    for td_key, td_dict in required_tool_dependencies.items():
                        if td_key not in installed_td:
                            installed_td[ td_key ] = td_dict
                if required_missing_tool_dependencies:
                    if not includes_tool_dependencies:
                        includes_tool_dependencies = True
                    for td_key, td_dict in required_missing_tool_dependencies.items():
                        if td_key not in missing_td:
                            missing_td[ td_key ] = td_dict
    else:
        installed_rd = None
        missing_rd = None
        missing_td = None
    return name, repository_owner, changeset_revision, includes_tool_dependencies, installed_rd, missing_rd, installed_td, missing_td

def get_installed_and_missing_repository_dependencies( trans, repository ):
    """
    Return the installed and missing repository dependencies for a tool shed repository that has a record in the Galaxy database, but
    may or may not be installed.  In this case, the repository dependencies are associated with the repository in the database.
    """
    missing_repository_dependencies = {}
    installed_repository_dependencies = {}
    has_repository_dependencies = repository.has_repository_dependencies
    if has_repository_dependencies:
        # The repository dependencies container will include only the immediate repository dependencies of this repository, so the container
        # will be only a single level in depth.
        metadata = repository.metadata
        installed_rd_tups = []
        missing_rd_tups = []
        for tsr in repository.repository_dependencies:
            prior_installation_required = suc.set_prior_installation_required( repository, tsr )
            rd_tup = [ tsr.tool_shed, tsr.name, tsr.owner, tsr.changeset_revision, prior_installation_required, tsr.id, tsr.status ]
            if tsr.status == trans.model.ToolShedRepository.installation_status.INSTALLED:
                installed_rd_tups.append( rd_tup )
            else:
               missing_rd_tups.append( rd_tup )
        if installed_rd_tups or missing_rd_tups:
            # Get the description from the metadata in case it has a value.
            repository_dependencies = metadata.get( 'repository_dependencies', {} )
            description = repository_dependencies.get( 'description', None )
            # We need to add a root_key entry to one or both of installed_repository_dependencies dictionary and the missing_repository_dependencies
            # dictionary for proper display parsing.
            root_key = container_util.generate_repository_dependencies_key_for_repository( repository.tool_shed,
                                                                                           repository.name,
                                                                                           repository.owner,
                                                                                           repository.installed_changeset_revision,
                                                                                           prior_installation_required )
            if installed_rd_tups:
                installed_repository_dependencies[ 'root_key' ] = root_key
                installed_repository_dependencies[ root_key ] = installed_rd_tups
                installed_repository_dependencies[ 'description' ] = description
            if missing_rd_tups:
                missing_repository_dependencies[ 'root_key' ] = root_key
                missing_repository_dependencies[ root_key ] = missing_rd_tups
                missing_repository_dependencies[ 'description' ] = description 
    return installed_repository_dependencies, missing_repository_dependencies

def get_installed_and_missing_repository_dependencies_for_new_install( trans, repo_info_tuple ):
    """
    Parse the received repository_dependencies dictionary that is associated with a repository being installed into Galaxy for the first time
    and attempt to determine repository dependencies that are already installed and those that are not.
    """
    missing_repository_dependencies = {}
    installed_repository_dependencies = {}
    missing_rd_tups = []
    installed_rd_tups = []
    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, installed_td = \
        suc.get_repo_info_tuple_contents( repo_info_tuple )
    if repository_dependencies:
        description = repository_dependencies[ 'description' ]
        root_key = repository_dependencies[ 'root_key' ]
        # The repository dependencies container will include only the immediate repository dependencies of this repository, so the container will be
        # only a single level in depth.
        for key, rd_tups in repository_dependencies.items():
            if key in [ 'description', 'root_key' ]:
                continue
            for rd_tup in rd_tups:
                tool_shed, name, owner, changeset_revision, prior_installation_required = suc.parse_repository_dependency_tuple( rd_tup )
                # Updates to installed repository revisions may have occurred, so make sure to locate the appropriate repository revision if one exists.
                # We need to create a temporary repo_info_tuple that includes the correct repository owner which we get from the current rd_tup.  The current
                # tuple looks like: ( description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, installed_td )
                tmp_clone_url = suc.generate_clone_url_from_repo_info_tup( rd_tup )
                tmp_repo_info_tuple = ( None, tmp_clone_url, changeset_revision, None, owner, None, None )
                repository, current_changeset_revision = suc.repository_was_previously_installed( trans, tool_shed, name, tmp_repo_info_tuple )
                if repository:
                    new_rd_tup = [ tool_shed, name, owner, changeset_revision, prior_installation_required, repository.id, repository.status ]
                    if repository.status == trans.model.ToolShedRepository.installation_status.INSTALLED:
                        if new_rd_tup not in installed_rd_tups:
                            installed_rd_tups.append( new_rd_tup )
                    else:
                        if new_rd_tup not in missing_rd_tups:
                            missing_rd_tups.append( new_rd_tup )
                else:
                    new_rd_tup = [ tool_shed, name, owner, changeset_revision, prior_installation_required, None, 'Never installed' ]
                    if new_rd_tup not in missing_rd_tups:
                        missing_rd_tups.append( new_rd_tup )
    if installed_rd_tups:
        installed_repository_dependencies[ 'root_key' ] = root_key
        installed_repository_dependencies[ root_key ] = installed_rd_tups
        installed_repository_dependencies[ 'description' ] = description
    if missing_rd_tups:
        missing_repository_dependencies[ 'root_key' ] = root_key
        missing_repository_dependencies[ root_key ] = missing_rd_tups
        missing_repository_dependencies[ 'description' ] = description
    return installed_repository_dependencies, missing_repository_dependencies

def get_installed_and_missing_tool_dependencies_for_new_install( trans, all_tool_dependencies ):
    """Return the lists of installed tool dependencies and missing tool dependencies for a set of repositories being installed into Galaxy."""
    # FIXME: this method currently populates and returns only missing tool dependencies since tool dependencies defined for complex repository dependency
    # relationships is not currently supported.  This method should be enhanced to search for installed tool dependencies defined as complex repository
    # dependency relationships when that feature is implemented.
    if all_tool_dependencies:
        tool_dependencies = {}
        missing_tool_dependencies = {}
        for td_key, val in all_tool_dependencies.items():
            # Set environment tool dependencies are a list, set each member to never installed.
            if td_key == 'set_environment':
                new_val = []
                for requirement_dict in val:
                    requirement_dict[ 'status' ] = trans.model.ToolDependency.installation_status.NEVER_INSTALLED
                    new_val.append( requirement_dict )
                missing_tool_dependencies[ td_key ] = new_val
            else:
                # Since we have a new install, missing tool dependencies have never been installed.
                val[ 'status' ] = trans.model.ToolDependency.installation_status.NEVER_INSTALLED
                missing_tool_dependencies[ td_key ] = val
    else:
        tool_dependencies = None
        missing_tool_dependencies = None
    return tool_dependencies, missing_tool_dependencies

def get_required_repo_info_dicts( trans, tool_shed_url, repo_info_dicts ):
    """
    Inspect the list of repo_info_dicts for repository dependencies and append a repo_info_dict for each of them to the list.  All
    repository_dependencies entries in each of the received repo_info_dicts includes all required repositories, so only one pass through
    this method is required to retrieve all repository dependencies.
    """
    all_repo_info_dicts = []
    if repo_info_dicts:
        # We'll send tuples of ( tool_shed, repository_name, repository_owner, changeset_revision ) to the tool shed to discover repository ids.
        required_repository_tups = []
        for repo_info_dict in repo_info_dicts:
            for repository_name, repo_info_tup in repo_info_dict.items():
                description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
                    suc.get_repo_info_tuple_contents( repo_info_tup )
                if repository_dependencies:
                    for key, val in repository_dependencies.items():
                        if key in [ 'root_key', 'description' ]:
                            continue
                        try:
                            toolshed, name, owner, changeset_revision, prior_installation_required = container_util.get_components_from_key( key )
                            components_list = [ toolshed, name, owner, changeset_revision, prior_installation_required ]
                        except ValueError:
                            # For backward compatibility to the 12/20/12 Galaxy release, default prior_installation_required to False in the caller.
                            toolshed, name, owner, changeset_revision = container_util.get_components_from_key( key )
                            components_list = [ toolshed, name, owner, changeset_revision ]
                        if components_list not in required_repository_tups:
                            required_repository_tups.append( components_list )
                        for components_list in val:
                            if components_list not in required_repository_tups:
                                required_repository_tups.append( components_list )
            if required_repository_tups:
                # The value of required_repository_tups is a list of tuples, so we need to encode it.
                encoded_required_repository_tups = []
                for required_repository_tup in required_repository_tups:
                    # Convert every item in required_repository_tup to a string.
                    required_repository_tup = [ str( item ) for item in required_repository_tup ]
                    encoded_required_repository_tups.append( encoding_util.encoding_sep.join( required_repository_tup ) )
                encoded_required_repository_str = encoding_util.encoding_sep2.join( encoded_required_repository_tups )
                encoded_required_repository_str = encoding_util.tool_shed_encode( encoded_required_repository_str )
                url = suc.url_join( tool_shed_url, '/repository/get_required_repo_info_dict?encoded_str=%s' % encoded_required_repository_str )
                text = common_util.tool_shed_get( trans.app, tool_shed_url, url )
                if text:
                    required_repo_info_dict = json.from_json_string( text )
                    required_repo_info_dicts = []
                    encoded_dict_strings = required_repo_info_dict[ 'repo_info_dicts' ]
                    for encoded_dict_str in encoded_dict_strings:
                        decoded_dict = encoding_util.tool_shed_decode( encoded_dict_str )
                        required_repo_info_dicts.append( decoded_dict )                        
                    if required_repo_info_dicts:                            
                        for required_repo_info_dict in required_repo_info_dicts:
                            if required_repo_info_dict not in all_repo_info_dicts:
                                all_repo_info_dicts.append( required_repo_info_dict )
    return all_repo_info_dicts

def handle_tool_dependencies( app, tool_shed_repository, tool_dependencies_config, tool_dependencies ):
    """
    Install and build tool dependencies defined in the tool_dependencies_config.  This config's tag sets can currently refer to installation
    methods in Galaxy's tool_dependencies module.  In the future, proprietary fabric scripts contained in the repository will be supported.
    Future enhancements to handling tool dependencies may provide installation processes in addition to fabric based processes.  The dependencies
    will be installed in:
    ~/<app.config.tool_dependency_dir>/<package_name>/<package_version>/<repo_owner>/<repo_name>/<repo_installed_changeset_revision>
    """
    installed_tool_dependencies = []
    # Parse the tool_dependencies.xml config.
    try:
        tree = ElementTree.parse( tool_dependencies_config )
    except Exception, e:
        log.debug( "Exception attempting to parse %s: %s" % ( str( tool_dependencies_config ), str( e ) ) )
        return installed_tool_dependencies
    root = tree.getroot()
    ElementInclude.include( root )
    fabric_version_checked = False
    for elem in root:
        if elem.tag == 'package':
            # Only install the tool_dependency if it is not already installed.
            package_name = elem.get( 'name', None )
            package_version = elem.get( 'version', None )
            if package_name and package_version:
                for tool_dependency in tool_dependencies:
                    if tool_dependency.name==package_name and tool_dependency.version==package_version:
                        break
                if tool_dependency.can_install:
                    tool_dependency = install_package( app, elem, tool_shed_repository, tool_dependencies=tool_dependencies )
                    if tool_dependency and tool_dependency.status in [ app.model.ToolDependency.installation_status.INSTALLED,
                                                                       app.model.ToolDependency.installation_status.ERROR ]:
                        installed_tool_dependencies.append( tool_dependency )
        elif elem.tag == 'set_environment':
            tool_dependency = set_environment( app, elem, tool_shed_repository )
            if tool_dependency and tool_dependency.status in [ app.model.ToolDependency.installation_status.INSTALLED,
                                                               app.model.ToolDependency.installation_status.ERROR ]:
                installed_tool_dependencies.append( tool_dependency )
    return installed_tool_dependencies
