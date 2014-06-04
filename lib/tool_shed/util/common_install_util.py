import copy
import logging
import os
import urllib
import urllib2
from galaxy import util
from galaxy import web
from galaxy.util import json
from galaxy.tools.deps.resolvers import INDETERMINATE_DEPENDENCY
import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_util
from tool_shed.util import container_util
from tool_shed.util import encoding_util
from tool_shed.util import data_manager_util
from tool_shed.util import datatype_util
from tool_shed.util import tool_dependency_util
from tool_shed.util import tool_util
from tool_shed.util import xml_util

from tool_shed.galaxy_install.install_manager import InstallManager
from tool_shed.galaxy_install.tool_dependencies.recipe.recipe_manager import StepManager
from tool_shed.galaxy_install.tool_dependencies.recipe.recipe_manager import TagManager

log = logging.getLogger( __name__ )

def activate_repository( trans, repository ):
    """Activate an installed tool shed repository that has been marked as deactivated."""
    repository_clone_url = common_util.generate_clone_url_for_installed_repository( trans.app, repository )
    shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir( trans.app, repository )
    repository.deleted = False
    repository.status = trans.install_model.ToolShedRepository.installation_status.INSTALLED
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
    trans.install_model.context.add( repository )
    trans.install_model.context.flush()
    if repository.includes_datatypes:
        if tool_path:
            repository_install_dir = os.path.abspath( os.path.join( tool_path, relative_install_dir ) )
        else:
            repository_install_dir = os.path.abspath( relative_install_dir )
        # Activate proprietary datatypes.
        installed_repository_dict = datatype_util.load_installed_datatypes( trans.app, repository, repository_install_dir, deactivate=False )
        if installed_repository_dict:
            converter_path = installed_repository_dict.get( 'converter_path' )
            if converter_path is not None:
                datatype_util.load_installed_datatype_converters( trans.app, installed_repository_dict, deactivate=False )
            display_path = installed_repository_dict.get( 'display_path' )
            if display_path is not None:
                datatype_util.load_installed_display_applications( trans.app, installed_repository_dict, deactivate=False )

def get_dependencies_for_repository( trans, tool_shed_url, repo_info_dict, includes_tool_dependencies, updating=False ):
    """
    Return dictionaries containing the sets of installed and missing tool dependencies and repository
    dependencies associated with the repository defined by the received repo_info_dict.
    """
    repository = None
    installed_rd = {}
    installed_td = {}
    missing_rd = {}
    missing_td = {}
    name = repo_info_dict.keys()[ 0 ]
    repo_info_tuple = repo_info_dict[ name ]
    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
        suc.get_repo_info_tuple_contents( repo_info_tuple )
    if tool_dependencies:
        if not includes_tool_dependencies:
            includes_tool_dependencies = True
        # Inspect the tool_dependencies dictionary to separate the installed and missing tool dependencies.
        # We don't add to installed_td and missing_td here because at this point they are empty.
        installed_td, missing_td = \
            get_installed_and_missing_tool_dependencies_for_repository( trans, tool_dependencies )
    # In cases where a repository dependency is required only for compiling a dependent repository's
    # tool dependency, the value of repository_dependencies will be an empty dictionary here.
    if repository_dependencies:
        # We have a repository with one or more defined repository dependencies.
        if not repository:
            repository = suc.get_repository_for_dependency_relationship( trans.app,
                                                                         tool_shed_url,
                                                                         name,
                                                                         repository_owner,
                                                                         changeset_revision )
        if not updating and repository and repository.metadata:
            installed_rd, missing_rd = get_installed_and_missing_repository_dependencies( trans, repository )
        else:
            installed_rd, missing_rd = \
                get_installed_and_missing_repository_dependencies_for_new_or_updated_install( trans, repo_info_tuple )
        # Discover all repository dependencies and retrieve information for installing them.
        all_repo_info_dict = get_required_repo_info_dicts( trans, tool_shed_url, util.listify( repo_info_dict ) )
        has_repository_dependencies = all_repo_info_dict.get( 'has_repository_dependencies', False )
        has_repository_dependencies_only_if_compiling_contained_td = \
            all_repo_info_dict.get( 'has_repository_dependencies_only_if_compiling_contained_td', False )
        includes_tools_for_display_in_tool_panel = all_repo_info_dict.get( 'includes_tools_for_display_in_tool_panel', False )
        includes_tool_dependencies = all_repo_info_dict.get( 'includes_tool_dependencies', False )
        includes_tools = all_repo_info_dict.get( 'includes_tools', False )
        required_repo_info_dicts = all_repo_info_dict.get( 'all_repo_info_dicts', [] )
        # Display tool dependencies defined for each of the repository dependencies.
        if required_repo_info_dicts:
            required_tool_dependencies = {}
            for rid in required_repo_info_dicts:
                for name, repo_info_tuple in rid.items():
                    description, repository_clone_url, changeset_revision, ctx_rev, \
                        repository_owner, rid_repository_dependencies, rid_tool_dependencies = \
                        suc.get_repo_info_tuple_contents( repo_info_tuple )
                    if rid_tool_dependencies:
                        for td_key, td_dict in rid_tool_dependencies.items():
                            if td_key not in required_tool_dependencies:
                                required_tool_dependencies[ td_key ] = td_dict
            if required_tool_dependencies:
                # Discover and categorize all tool dependencies defined for this repository's repository dependencies.
                required_installed_td, required_missing_td = \
                    get_installed_and_missing_tool_dependencies_for_repository( trans, required_tool_dependencies )
                if required_installed_td:
                    if not includes_tool_dependencies:
                        includes_tool_dependencies = True
                    for td_key, td_dict in required_installed_td.items():
                        if td_key not in installed_td:
                            installed_td[ td_key ] = td_dict
                if required_missing_td:
                    if not includes_tool_dependencies:
                        includes_tool_dependencies = True
                    for td_key, td_dict in required_missing_td.items():
                        if td_key not in missing_td:
                            missing_td[ td_key ] = td_dict
    else:
        # We have a single repository with (possibly) no defined repository dependencies.
        all_repo_info_dict = get_required_repo_info_dicts( trans, tool_shed_url, util.listify( repo_info_dict ) )
        has_repository_dependencies = all_repo_info_dict.get( 'has_repository_dependencies', False )
        has_repository_dependencies_only_if_compiling_contained_td = \
            all_repo_info_dict.get( 'has_repository_dependencies_only_if_compiling_contained_td', False )
        includes_tools_for_display_in_tool_panel = all_repo_info_dict.get( 'includes_tools_for_display_in_tool_panel', False )
        includes_tool_dependencies = all_repo_info_dict.get( 'includes_tool_dependencies', False )
        includes_tools = all_repo_info_dict.get( 'includes_tools', False )
        required_repo_info_dicts = all_repo_info_dict.get( 'all_repo_info_dicts', [] )
    dependencies_for_repository_dict = \
        dict( changeset_revision=changeset_revision,
              has_repository_dependencies=has_repository_dependencies,
              has_repository_dependencies_only_if_compiling_contained_td=has_repository_dependencies_only_if_compiling_contained_td,
              includes_tool_dependencies=includes_tool_dependencies,
              includes_tools=includes_tools,
              includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
              installed_repository_dependencies=installed_rd,
              installed_tool_dependencies=installed_td,
              missing_repository_dependencies=missing_rd,
              missing_tool_dependencies=missing_td,
              name=name,
              repository_owner=repository_owner )
    return dependencies_for_repository_dict

def get_installed_and_missing_repository_dependencies( trans, repository ):
    """
    Return the installed and missing repository dependencies for a tool shed repository that has a record
    in the Galaxy database, but may or may not be installed.  In this case, the repository dependencies are
    associated with the repository in the database.  Do not include a repository dependency if it is required
    only to compile a tool dependency defined for the dependent repository since these special kinds of repository
    dependencies are really a dependency of the dependent repository's contained tool dependency, and only
    if that tool dependency requires compilation.
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
            prior_installation_required = suc.set_prior_installation_required( trans.app, repository, tsr )
            only_if_compiling_contained_td = suc.set_only_if_compiling_contained_td( repository, tsr )
            rd_tup = [ tsr.tool_shed,
                       tsr.name,
                       tsr.owner,
                       tsr.changeset_revision,
                       prior_installation_required,
                       only_if_compiling_contained_td,
                       tsr.id,
                       tsr.status ]
            if tsr.status == trans.install_model.ToolShedRepository.installation_status.INSTALLED:
                installed_rd_tups.append( rd_tup )
            else:
                # We'll only add the rd_tup to the missing_rd_tups list if the received repository has tool dependencies that are not
                # correctly installed.  This may prove to be a weak check since the repository in question may not have anything to do
                # with compiling the missing tool dependencies.  If we discover that this is a problem, more granular checking will be
                # necessary here.
                if repository.missing_tool_dependencies:
                    if not repository_dependency_needed_only_for_compiling_tool_dependency( repository, tsr ):
                        missing_rd_tups.append( rd_tup )
                else:
                    missing_rd_tups.append( rd_tup )
        if installed_rd_tups or missing_rd_tups:
            # Get the description from the metadata in case it has a value.
            repository_dependencies = metadata.get( 'repository_dependencies', {} )
            description = repository_dependencies.get( 'description', None )
            # We need to add a root_key entry to one or both of installed_repository_dependencies dictionary and the
            # missing_repository_dependencies dictionaries for proper display parsing.
            root_key = container_util.generate_repository_dependencies_key_for_repository( repository.tool_shed,
                                                                                           repository.name,
                                                                                           repository.owner,
                                                                                           repository.installed_changeset_revision,
                                                                                           prior_installation_required,
                                                                                           only_if_compiling_contained_td )
            if installed_rd_tups:
                installed_repository_dependencies[ 'root_key' ] = root_key
                installed_repository_dependencies[ root_key ] = installed_rd_tups
                installed_repository_dependencies[ 'description' ] = description
            if missing_rd_tups:
                missing_repository_dependencies[ 'root_key' ] = root_key
                missing_repository_dependencies[ root_key ] = missing_rd_tups
                missing_repository_dependencies[ 'description' ] = description
    return installed_repository_dependencies, missing_repository_dependencies

def get_installed_and_missing_repository_dependencies_for_new_or_updated_install( trans, repo_info_tuple ):
    """
    Parse the received repository_dependencies dictionary that is associated with a repository being
    installed into Galaxy for the first time and attempt to determine repository dependencies that are
    already installed and those that are not.
    """
    missing_repository_dependencies = {}
    installed_repository_dependencies = {}
    missing_rd_tups = []
    installed_rd_tups = []
    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
        suc.get_repo_info_tuple_contents( repo_info_tuple )
    if repository_dependencies:
        description = repository_dependencies[ 'description' ]
        root_key = repository_dependencies[ 'root_key' ]
        # The repository dependencies container will include only the immediate repository dependencies of
        # this repository, so the container will be only a single level in depth.
        for key, rd_tups in repository_dependencies.items():
            if key in [ 'description', 'root_key' ]:
                continue
            for rd_tup in rd_tups:
                tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
                    common_util.parse_repository_dependency_tuple( rd_tup )
                # Updates to installed repository revisions may have occurred, so make sure to locate the
                # appropriate repository revision if one exists.  We need to create a temporary repo_info_tuple
                # that includes the correct repository owner which we get from the current rd_tup.  The current
                # tuple looks like: ( description, repository_clone_url, changeset_revision, ctx_rev, repository_owner,
                #                     repository_dependencies, installed_td )
                tmp_clone_url = common_util.generate_clone_url_from_repo_info_tup( trans, rd_tup )
                tmp_repo_info_tuple = ( None, tmp_clone_url, changeset_revision, None, owner, None, None )
                repository, installed_changeset_revision = suc.repository_was_previously_installed( trans,
                                                                                                    tool_shed,
                                                                                                    name,
                                                                                                    tmp_repo_info_tuple )
                if repository:
                    new_rd_tup = [ tool_shed,
                                   name,
                                   owner,
                                   changeset_revision,
                                   prior_installation_required,
                                   only_if_compiling_contained_td,
                                   repository.id,
                                   repository.status ]
                    if repository.status == trans.install_model.ToolShedRepository.installation_status.INSTALLED:
                        if new_rd_tup not in installed_rd_tups:
                            installed_rd_tups.append( new_rd_tup )
                    else:
                        # A repository dependency that is not installed will not be considered missing if its value
                        # for only_if_compiling_contained_td is True  This is because this type of repository dependency
                        # will only be considered at the time that the specified tool dependency is being installed, and
                        # even then only if the compiled binary of the tool dependency could not be installed due to the
                        # unsupported installation environment.
                        if not util.asbool( only_if_compiling_contained_td ):
                            if new_rd_tup not in missing_rd_tups:
                                missing_rd_tups.append( new_rd_tup )
                else:
                    new_rd_tup = [ tool_shed,
                                   name,
                                   owner,
                                   changeset_revision,
                                   prior_installation_required,
                                   only_if_compiling_contained_td,
                                   None,
                                  'Never installed' ]
                    if not util.asbool( only_if_compiling_contained_td ):
                        # A repository dependency that is not installed will not be considered missing if its value for
                        # only_if_compiling_contained_td is True - see above...
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

def get_installed_and_missing_tool_dependencies_for_repository( trans, tool_dependencies_dict ):
    """
    Return the lists of installed tool dependencies and missing tool dependencies for a set of repositories
    being installed into Galaxy.
    """
    # FIXME: This implementation breaks when updates to a repository contain dependencies that result in
    # multiple entries for a specific tool dependency.  A scenario where this can happen is where 2 repositories
    # define  the same dependency internally (not using the complex repository dependency definition to a separate
    # package repository approach).  If 2 repositories contain the same tool_dependencies.xml file, one dependency
    # will be lost since the values in these returned dictionaries are not lists.  All tool dependency dictionaries
    # should have lists as values.  These scenarios are probably extreme corner cases, but still should be handled.
    installed_tool_dependencies = {}
    missing_tool_dependencies = {}
    if tool_dependencies_dict:
        # Make sure not to change anything in the received tool_dependencies_dict as that would be a bad side-effect!
        tmp_tool_dependencies_dict = copy.deepcopy( tool_dependencies_dict )
        for td_key, val in tmp_tool_dependencies_dict.items():
            # Default the status to NEVER_INSTALLED.
            tool_dependency_status = trans.install_model.ToolDependency.installation_status.NEVER_INSTALLED
            # Set environment tool dependencies are a list.
            if td_key == 'set_environment':
                new_val = []
                for requirement_dict in val:
                    # {'repository_name': 'xx',
                    #  'name': 'bwa',
                    #  'version': '0.5.9',
                    #  'repository_owner': 'yy',
                    #  'changeset_revision': 'zz',
                    #  'type': 'package'}
                    tool_dependency = \
                        tool_dependency_util.get_tool_dependency_by_name_version_type( trans.app,
                                                                                       requirement_dict.get( 'name', None ),
                                                                                       requirement_dict.get( 'version', None ),
                                                                                       requirement_dict.get( 'type', 'package' ) )
                    if tool_dependency:
                        tool_dependency_status = tool_dependency.status
                    requirement_dict[ 'status' ] = tool_dependency_status
                    new_val.append( requirement_dict )
                    if tool_dependency_status in [ trans.install_model.ToolDependency.installation_status.INSTALLED ]:
                        if td_key in installed_tool_dependencies:
                            installed_tool_dependencies[ td_key ].extend( new_val )
                        else:
                            installed_tool_dependencies[ td_key ] = new_val
                    else:
                        if td_key in missing_tool_dependencies:
                            missing_tool_dependencies[ td_key ].extend( new_val )
                        else:
                            missing_tool_dependencies[ td_key ] = new_val
            else:
                # The val dictionary looks something like this:
                # {'repository_name': 'xx',
                #  'name': 'bwa',
                #  'version': '0.5.9',
                #  'repository_owner': 'yy',
                #  'changeset_revision': 'zz',
                #  'type': 'package'}
                tool_dependency = tool_dependency_util.get_tool_dependency_by_name_version_type( trans.app,
                                                                                                 val.get( 'name', None ),
                                                                                                 val.get( 'version', None ),
                                                                                                 val.get( 'type', 'package' ) )
                if tool_dependency:
                    tool_dependency_status = tool_dependency.status
                val[ 'status' ] = tool_dependency_status
            if tool_dependency_status in [ trans.install_model.ToolDependency.installation_status.INSTALLED ]:
                installed_tool_dependencies[ td_key ] = val
            else:
                missing_tool_dependencies[ td_key ] = val
    return installed_tool_dependencies, missing_tool_dependencies

def get_required_repo_info_dicts( trans, tool_shed_url, repo_info_dicts ):
    """
    Inspect the list of repo_info_dicts for repository dependencies and append a repo_info_dict for each of
    them to the list.  All repository_dependencies entries in each of the received repo_info_dicts includes
    all required repositories, so only one pass through this method is required to retrieve all repository
    dependencies.
    """
    all_required_repo_info_dict = {}
    all_repo_info_dicts = []
    if repo_info_dicts:
        # We'll send tuples of ( tool_shed, repository_name, repository_owner, changeset_revision ) to the tool
        # shed to discover repository ids.
        required_repository_tups = []
        for repo_info_dict in repo_info_dicts:
            if repo_info_dict not in all_repo_info_dicts:
                all_repo_info_dicts.append( repo_info_dict )
            for repository_name, repo_info_tup in repo_info_dict.items():
                description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
                    suc.get_repo_info_tuple_contents( repo_info_tup )
                if repository_dependencies:
                    for key, val in repository_dependencies.items():
                        if key in [ 'root_key', 'description' ]:
                            continue
                        repository_components_tuple = container_util.get_components_from_key( key )
                        components_list = suc.extract_components_from_tuple( repository_components_tuple )
                        # Skip listing a repository dependency if it is required only to compile a tool dependency
                        # defined for the dependent repository since in this case, the repository dependency is really
                        # a dependency of the dependent repository's contained tool dependency, and only if that
                        # tool dependency requires compilation.
                        # For backward compatibility to the 12/20/12 Galaxy release.
                        prior_installation_required = 'False'
                        only_if_compiling_contained_td = 'False'
                        if len( components_list ) == 4:
                            prior_installation_required = 'False'
                            only_if_compiling_contained_td = 'False'
                        elif len( components_list ) == 5:
                            prior_installation_required = components_list[ 4 ]
                            only_if_compiling_contained_td = 'False'
                        if not util.asbool( only_if_compiling_contained_td ):
                            if components_list not in required_repository_tups:
                                required_repository_tups.append( components_list )
                        for components_list in val:
                            try:
                                only_if_compiling_contained_td = components_list[ 5 ]
                            except:
                                only_if_compiling_contained_td = 'False'
                            # Skip listing a repository dependency if it is required only to compile a tool dependency
                            # defined for the dependent repository (see above comment).
                            if not util.asbool( only_if_compiling_contained_td ):
                                if components_list not in required_repository_tups:
                                    required_repository_tups.append( components_list )
                else:
                    # We have a single repository with no dependencies.
                    components_list = [ tool_shed_url, repository_name, repository_owner, changeset_revision ]
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
                if trans.webapp.name == 'galaxy':
                    # Handle secure / insecure Tool Shed URL protocol changes and port changes.
                    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( trans.app, tool_shed_url )
                url = common_util.url_join( tool_shed_url, '/repository/get_required_repo_info_dict' )
                # Fix for handling 307 redirect not being handled nicely by urllib2.urlopen when the urllib2.Request has data provided
                url = urllib2.urlopen( urllib2.Request( url ) ).geturl()
                request = urllib2.Request( url, data=urllib.urlencode( dict( encoded_str=encoded_required_repository_str ) ) )
                response = urllib2.urlopen( request ).read()
                if response:
                    try:
                        required_repo_info_dict = json.from_json_string( response )
                    except Exception, e:
                        log.exception( e )
                        return all_repo_info_dicts
                    required_repo_info_dicts = []
                    for k, v in required_repo_info_dict.items():
                        if k == 'repo_info_dicts':
                            encoded_dict_strings = required_repo_info_dict[ 'repo_info_dicts' ]
                            for encoded_dict_str in encoded_dict_strings:
                                decoded_dict = encoding_util.tool_shed_decode( encoded_dict_str )
                                required_repo_info_dicts.append( decoded_dict )
                        else:
                            if k not in all_required_repo_info_dict:
                                all_required_repo_info_dict[ k ] = v
                            else:
                                if v and not all_required_repo_info_dict[ k ]:
                                    all_required_repo_info_dict[ k ] = v
                        if required_repo_info_dicts:
                            for required_repo_info_dict in required_repo_info_dicts:
                                # Each required_repo_info_dict has a single entry, and all_repo_info_dicts is a list
                                # of dictionaries, each of which has a single entry.  We'll check keys here rather than
                                # the entire dictionary because a dictionary entry in all_repo_info_dicts will include
                                # lists of discovered repository dependencies, but these lists will be empty in the
                                # required_repo_info_dict since dependency discovery has not yet been performed for these
                                # dictionaries.
                                required_repo_info_dict_key = required_repo_info_dict.keys()[ 0 ]
                                all_repo_info_dicts_keys = [ d.keys()[ 0 ] for d in all_repo_info_dicts ]
                                if required_repo_info_dict_key not in all_repo_info_dicts_keys:
                                    all_repo_info_dicts.append( required_repo_info_dict )
                    all_required_repo_info_dict[ 'all_repo_info_dicts' ] = all_repo_info_dicts
    return all_required_repo_info_dict

def install_specified_tool_dependencies( app, tool_shed_repository, tool_dependencies_config, tool_dependencies,
                                         from_tool_migration_manager=False ):
    """
    Follow the recipe in the received tool_dependencies_config to install specified packages for
    repository tools.  The received list of tool_dependencies are the database records for those
    dependencies defined in the tool_dependencies_config that are to be installed.  This list may
    be a subset of the set of dependencies defined in the tool_dependencies_config.  This allows
    for filtering out dependencies that have not been checked for installation on the 'Manage tool
    dependencies' page for an installed Tool Shed repository.
    """
    attr_tups_of_dependencies_for_install = [ ( td.name, td.version, td.type ) for td in tool_dependencies ]
    installed_packages = []
    install_manager = InstallManager()
    tag_manager = TagManager()
    # Parse the tool_dependencies.xml config.
    tree, error_message = xml_util.parse_xml( tool_dependencies_config )
    if tree is None:
        log.debug( "The received tool_dependencies.xml file is likely invalid: %s" % str( error_message ) )
        return installed_packages
    root = tree.getroot()
    elems = []
    for elem in root:
        if elem.tag == 'set_environment':
            version = elem.get( 'version', '1.0' )
            if version != '1.0':
                raise Exception( 'The <set_environment> tag must have a version attribute with value 1.0' )
            for sub_elem in elem:
                elems.append( sub_elem )
        else:
            elems.append( elem )
    for elem in elems:
        name = elem.get( 'name', None )
        version = elem.get( 'version', None )
        type = elem.get( 'type', None )
        if type is None:
            if elem.tag in [ 'environment_variable', 'set_environment' ]:
                type = 'set_environment'
            else:
                type = 'package'
        if ( name and type == 'set_environment' ) or ( name and version ):
            # elem is a package set_environment tag set.
            attr_tup = ( name, version, type )
            try:
                index = attr_tups_of_dependencies_for_install.index( attr_tup )
            except Exception, e:
                index = None
            if index is not None:
                tool_dependency = tool_dependencies[ index ]
                # If the tool_dependency.type is 'set_environment', then the call to process_tag_set() will
                # handle everything - no additional installation is necessary.
                tool_dependency, proceed_with_install, action_elem_tuples = \
                    tag_manager.process_tag_set( app,
                                                 tool_shed_repository,
                                                 tool_dependency,
                                                 elem,
                                                 name,
                                                 version,
                                                 from_tool_migration_manager=from_tool_migration_manager,
                                                 tool_dependency_db_records=tool_dependencies )
                if ( tool_dependency.type == 'package' and proceed_with_install ):
                    try:
                        tool_dependency = install_manager.install_package( app, 
                                                                           elem, 
                                                                           tool_shed_repository, 
                                                                           tool_dependencies=tool_dependencies, 
                                                                           from_tool_migration_manager=from_tool_migration_manager )
                    except Exception, e:
                        error_message = "Error installing tool dependency %s version %s: %s" % \
                            ( str( name ), str( version ), str( e ) )
                        log.exception( error_message )
                        if tool_dependency:
                            # Since there was an installation error, update the tool dependency status to Error. The
                            # remove_installation_path option must be left False here.
                            tool_dependency = \
                                tool_dependency_util.handle_tool_dependency_installation_error( app, 
                                                                                                tool_dependency, 
                                                                                                error_message, 
                                                                                                remove_installation_path=False )
                    if tool_dependency and tool_dependency.status in [ app.install_model.ToolDependency.installation_status.INSTALLED,
                                                                       app.install_model.ToolDependency.installation_status.ERROR ]:
                        installed_packages.append( tool_dependency )
                        if app.config.manage_dependency_relationships:
                            # Add the tool_dependency to the in-memory dictionaries in the installed_repository_manager.
                            app.installed_repository_manager.handle_tool_dependency_install( tool_shed_repository, tool_dependency )
    return installed_packages

def repository_dependency_needed_only_for_compiling_tool_dependency( repository, repository_dependency ):
    for rd_tup in repository.tuples_of_repository_dependencies_needed_for_compiling_td:
        tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = rd_tup
        # TODO: we may discover that we need to check more than just installed_changeset_revision and changeset_revision here, in which
        # case we'll need to contact the tool shed to get the list of all possible changeset_revisions.
        cleaned_tool_shed = common_util.remove_protocol_and_port_from_tool_shed_url( tool_shed )
        cleaned_repository_dependency_tool_shed = \
            common_util.remove_protocol_and_port_from_tool_shed_url( str( repository_dependency.tool_shed ) )
        if cleaned_repository_dependency_tool_shed == cleaned_tool_shed and \
            repository_dependency.name == name and \
            repository_dependency.owner == owner and \
            ( repository_dependency.installed_changeset_revision == changeset_revision or \
              repository_dependency.changeset_revision == changeset_revision ):
            return True
    return False
