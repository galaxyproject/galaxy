import logging
import os
import shutil

from galaxy import eggs
eggs.require( 'elementtree' )
from elementtree import ElementTree, ElementInclude

from galaxy.model.orm import and_
import tool_shed.util.shed_util_common as suc

from galaxy import util

log = logging.getLogger( __name__ )

def add_installation_directories_to_tool_dependencies( trans, tool_dependencies ):
    """
    Determine the path to the installation directory for each of the received tool dependencies.  This path will be displayed within the tool dependencies
    container on the select_tool_panel_section or reselect_tool_panel_section pages when installing or reinstalling repositories that contain tools with the
    defined tool dependencies.  The list of tool dependencies may be associated with more than a single repository.
    """
    for dependency_key, requirements_dict in tool_dependencies.items():
        if dependency_key in [ 'set_environment' ]:
            continue
        repository_name = requirements_dict.get( 'repository_name', 'unknown' )
        repository_owner = requirements_dict.get( 'repository_owner', 'unknown' )
        changeset_revision = requirements_dict.get( 'changeset_revision', 'unknown' )
        dependency_name = requirements_dict[ 'name' ]
        version = requirements_dict[ 'version' ]
        type = requirements_dict[ 'type' ]
        if trans.app.config.tool_dependency_dir:
            root_dir = trans.app.config.tool_dependency_dir
        else:
            root_dir = '<set your tool_dependency_dir in your Galaxy configuration file>'
        install_dir = os.path.join( root_dir,
                                    dependency_name,
                                    version,
                                    repository_owner,
                                    repository_name,
                                    changeset_revision )
        requirements_dict[ 'install_dir' ] = install_dir
        tool_dependencies[ dependency_key ] = requirements_dict
    return tool_dependencies

def create_or_update_tool_dependency( app, tool_shed_repository, name, version, type, status, set_status=True ):
    # Called from Galaxy (never the tool shed) when a new repository is being installed or when an uninstalled repository is being reinstalled.
    sa_session = app.model.context.current
    # First see if an appropriate tool_dependency record exists for the received tool_shed_repository.
    if version:
        tool_dependency = get_tool_dependency_by_name_version_type_repository( app, tool_shed_repository, name, version, type )
    else:
        tool_dependency = get_tool_dependency_by_name_type_repository( app, tool_shed_repository, name, type )
    if tool_dependency:
        if set_status:
            tool_dependency.status = status
    else:
        # Create a new tool_dependency record for the tool_shed_repository.
        tool_dependency = app.model.ToolDependency( tool_shed_repository.id, name, version, type, status )
    sa_session.add( tool_dependency )
    sa_session.flush()
    return tool_dependency

def create_tool_dependency_objects( app, tool_shed_repository, relative_install_dir, set_status=True ):
    """Create or update a ToolDependency for each entry in tool_dependencies_config.  This method is called when installing a new tool_shed_repository."""
    tool_dependency_objects = []
    shed_config_dict = tool_shed_repository.get_shed_config_dict( app )
    if shed_config_dict.get( 'tool_path' ):
        relative_install_dir = os.path.join( shed_config_dict.get( 'tool_path' ), relative_install_dir )
    # Get the tool_dependencies.xml file from the repository.
    tool_dependencies_config = suc.get_config_from_disk( 'tool_dependencies.xml', relative_install_dir )
    try:
        tree = ElementTree.parse( tool_dependencies_config )
    except Exception, e:
        log.debug( "Exception attempting to parse tool_dependencies.xml: %s" %str( e ) )
        return tool_dependency_objects
    root = tree.getroot()
    ElementInclude.include( root )
    fabric_version_checked = False
    for elem in root:
        tool_dependency_type = elem.tag
        if tool_dependency_type == 'package':
            name = elem.get( 'name', None )
            version = elem.get( 'version', None )
            if name and version:
                tool_dependency = create_or_update_tool_dependency( app,
                                                                    tool_shed_repository,
                                                                    name=name,
                                                                    version=version,
                                                                    type=tool_dependency_type,
                                                                    status=app.model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                                    set_status=set_status )
                tool_dependency_objects.append( tool_dependency )
        elif tool_dependency_type == 'set_environment':
            for env_elem in elem:
                # <environment_variable name="R_SCRIPT_PATH" action="set_to">$REPOSITORY_INSTALL_DIR</environment_variable>
                name = env_elem.get( 'name', None )
                action = env_elem.get( 'action', None )
                if name and action:
                    tool_dependency = create_or_update_tool_dependency( app,
                                                                        tool_shed_repository,
                                                                        name=name,
                                                                        version=None,
                                                                        type=tool_dependency_type,
                                                                        status=app.model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                                        set_status=set_status )
                    tool_dependency_objects.append( tool_dependency )
    return tool_dependency_objects

def generate_message_for_invalid_tool_dependencies( metadata_dict ):
    """
    Due to support for orphan tool dependencies (which are always valid) tool dependency definitions can only be invalid if they include a definition for a complex
    repository dependency and the repository dependency definition is invalid.  This method retrieves the error message associated with the invalid tool dependency
    for display in the caller.
    """
    message = ''
    if metadata_dict:
        invalid_tool_dependencies = metadata_dict.get( 'invalid_tool_dependencies', None )
        if invalid_tool_dependencies:
            for td_key, requirement_dict in invalid_tool_dependencies.items():
                error = requirement_dict.get( 'error', None )
                if error:
                    message = '%s  ' % str( error )
    return message

def generate_message_for_orphan_tool_dependencies( metadata_dict ):
    """
    The introduction of the support for orphan tool dependency definitions in tool shed repositories has resulted in the inability
    to define an improperly configured tool dependency definition / tool config requirements tag combination as an invalid tool
    dependency.  This is certainly a weakness which cannot be correctly handled since now the only way to categorize a tool dependency
    as invalid is if it consists of a complex repository dependency that is invalid.  Any tool dependency definition other than those
    is considered valid but perhaps an orphan due to it's actual invalidity.
    """
    message = ''
    if metadata_dict:
        orphan_tool_dependencies = metadata_dict.get( 'orphan_tool_dependencies', None )
        if orphan_tool_dependencies:
            if 'tools' not in metadata_dict and 'invalid_tools' not in metadata_dict:
                message += "This repository contains no tools, so these tool dependencies are considered orphans within this repository.<br/>"
            for td_key, requirements_dict in orphan_tool_dependencies.items():
                if td_key == 'set_environment':
                    # "set_environment": [{"name": "R_SCRIPT_PATH", "type": "set_environment"}]
                    message += "The settings for <b>name</b> and <b>type</b> from a contained tool configuration file's <b>requirement</b> tag "
                    message += "does not match the information for the following tool dependency definitions in the <b>tool_dependencies.xml</b> "
                    message += "file, so these tool dependencies are considered orphans within this repository.<br/>"
                    for env_requirements_dict in requirements_dict:
                        name = env_requirements_dict[ 'name' ]
                        type = env_requirements_dict[ 'type' ]
                        message += "<b>* name:</b> %s, <b>type:</b> %s<br/>" % ( str( name ), str( type ) )
                else:
                    # "R/2.15.1": {"name": "R", "readme": "some string", "type": "package", "version": "2.15.1"}
                    message += "The settings for <b>name</b>, <b>version</b> and <b>type</b> from a contained tool configuration file's "
                    message += "<b>requirement</b> tag does not match the information for the following tool dependency definitions in the "
                    message += "<b>tool_dependencies.xml</b> file, so these tool dependencies are considered orphans within this repository.<br/>"
                    name = requirements_dict[ 'name' ]
                    type = requirements_dict[ 'type' ]
                    version = requirements_dict[ 'version' ]
                    message += "<b>* name:</b> %s, <b>type:</b> %s, <b>version:</b> %s<br/>" % ( str( name ), str( type ), str( version ) )
                message += "<br/>"
    return message

def get_installed_and_missing_tool_dependencies( trans, repository, all_tool_dependencies ):
    if all_tool_dependencies:
        tool_dependencies = {}
        missing_tool_dependencies = {}
        for td_key, val in all_tool_dependencies.items():
            if td_key in [ 'set_environment' ]:
                for index, td_info_dict in enumerate( val ):
                    name = td_info_dict[ 'name' ]
                    version = None
                    type = td_info_dict[ 'type' ]
                    tool_dependency = get_tool_dependency_by_name_type_repository( trans.app, repository, name, type )
                    if tool_dependency:
                        td_info_dict[ 'repository_id' ] = repository.id
                        td_info_dict[ 'tool_dependency_id' ] = tool_dependency.id
                        if tool_dependency.status:
                            tool_dependency_status = str( tool_dependency.status )
                        else:
                            tool_dependency_status = 'Never installed'
                        td_info_dict[ 'status' ] = tool_dependency_status
                        val[ index ] = td_info_dict
                        if tool_dependency.status == trans.model.ToolDependency.installation_status.INSTALLED:
                            tool_dependencies[ td_key ] = val
                        else:
                            missing_tool_dependencies[ td_key ] = val
            else:
                name = val[ 'name' ]
                version = val[ 'version' ]
                type = val[ 'type' ]
                tool_dependency = get_tool_dependency_by_name_version_type_repository( trans.app, repository, name, version, type )
                if tool_dependency:
                    val[ 'repository_id' ] = repository.id
                    val[ 'tool_dependency_id' ] = tool_dependency.id
                    if tool_dependency.status:
                        tool_dependency_status = str( tool_dependency.status )
                    else:
                        tool_dependency_status = 'Never installed'
                    val[ 'status' ] = tool_dependency_status
                    if tool_dependency.status == trans.model.ToolDependency.installation_status.INSTALLED:
                        tool_dependencies[ td_key ] = val
                    else:
                        missing_tool_dependencies[ td_key ] = val
    else:
        tool_dependencies = None
        missing_tool_dependencies = None
    return tool_dependencies, missing_tool_dependencies

def get_tool_dependency( trans, id ):
    """Get a tool_dependency from the database via id"""
    return trans.sa_session.query( trans.model.ToolDependency ).get( trans.security.decode_id( id ) )

def get_tool_dependency_by_name_type_repository( app, repository, name, type ):
    sa_session = app.model.context.current
    return sa_session.query( app.model.ToolDependency ) \
                     .filter( and_( app.model.ToolDependency.table.c.tool_shed_repository_id == repository.id,
                                    app.model.ToolDependency.table.c.name == name,
                                    app.model.ToolDependency.table.c.type == type ) ) \
                     .first()

def get_tool_dependency_by_name_version_type_repository( app, repository, name, version, type ):
    sa_session = app.model.context.current
    return sa_session.query( app.model.ToolDependency ) \
                     .filter( and_( app.model.ToolDependency.table.c.tool_shed_repository_id == repository.id,
                                    app.model.ToolDependency.table.c.name == name,
                                    app.model.ToolDependency.table.c.version == version,
                                    app.model.ToolDependency.table.c.type == type ) ) \
                     .first()

def get_tool_dependency_ids( as_string=False, **kwd ):
    tool_dependency_id = kwd.get( 'tool_dependency_id', None )
    tool_dependency_ids = util.listify( kwd.get( 'tool_dependency_ids', None ) )
    if not tool_dependency_ids:
        tool_dependency_ids = util.listify( kwd.get( 'id', None ) )
    if tool_dependency_id and tool_dependency_id not in tool_dependency_ids:
        tool_dependency_ids.append( tool_dependency_id )
    if as_string:
        return ','.join( tool_dependency_ids )
    return tool_dependency_ids

def merge_missing_tool_dependencies_to_installed_container( containers_dict ):
    """ Merge the list of missing tool dependencies into the list of installed tool dependencies."""
    missing_td_container_root = containers_dict.get( 'missing_tool_dependencies', None )
    if missing_td_container_root:
        # The missing_td_container_root will be a root folder containing a single sub_folder.
        missing_td_container = missing_td_container_root.folders[ 0 ]
        installed_td_container_root = containers_dict.get( 'tool_dependencies', None )
        # The installed_td_container_root will be a root folder containing a single sub_folder.
        if installed_td_container_root:
            installed_td_container = installed_td_container_root.folders[ 0 ]
            installed_td_container.label = 'Tool dependencies'
            for index, td in enumerate( missing_td_container.tool_dependencies ):
                # Skip the header row.
                if index == 0:
                    continue
                installed_td_container.tool_dependencies.append( td )
            installed_td_container_root.folders = [ installed_td_container ]
            containers_dict[ 'tool_dependencies' ] = installed_td_container_root
        else:
            # Change the folder label from 'Missing tool dependencies' to be 'Tool dependencies' for display.
            root_container = containers_dict[ 'missing_tool_dependencies' ]
            for sub_container in root_container.folders:
                # There should only be 1 subfolder.
                sub_container.label = 'Tool dependencies'
            containers_dict[ 'tool_dependencies' ] = root_container
    containers_dict[ 'missing_tool_dependencies' ] = None
    return containers_dict

def populate_tool_dependencies_dicts( trans, tool_shed_url, tool_path, repository_installed_tool_dependencies, repository_missing_tool_dependencies,
                                      required_repo_info_dicts ):
    """
    Return the populated installed_tool_dependencies and missing_tool_dependencies dictionaries for all repositories defined by entries in the received
    required_repo_info_dicts.
    """
    installed_tool_dependencies = None
    missing_tool_dependencies = None
    if repository_installed_tool_dependencies is None:
        repository_installed_tool_dependencies = {}
    else:
        # Add the install_dir attribute to the tool_dependencies.
        repository_installed_tool_dependencies = add_installation_directories_to_tool_dependencies( trans=trans,
                                                                                                    tool_dependencies=repository_installed_tool_dependencies )
    if repository_missing_tool_dependencies is None:
        repository_missing_tool_dependencies = {}
    else:
        # Add the install_dir attribute to the tool_dependencies.
        repository_missing_tool_dependencies = add_installation_directories_to_tool_dependencies( trans=trans,
                                                                                                  tool_dependencies=repository_missing_tool_dependencies )
    if required_repo_info_dicts:
        # Handle the tool dependencies defined for each of the repository's repository dependencies.
        for rid in required_repo_info_dicts:
            for name, repo_info_tuple in rid.items():
                description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
                    suc.get_repo_info_tuple_contents( repo_info_tuple )
                if tool_dependencies:
                    # Add the install_dir attribute to the tool_dependencies.
                    tool_dependencies = add_installation_directories_to_tool_dependencies( trans=trans,
                                                                                           tool_dependencies=tool_dependencies )
                    # The required_repository may have been installed with a different changeset revision.
                    required_repository, installed_changeset_revision = suc.repository_was_previously_installed( trans, tool_shed_url, name, repo_info_tuple )
                    if required_repository:
                        required_repository_installed_tool_dependencies, required_repository_missing_tool_dependencies = \
                            get_installed_and_missing_tool_dependencies( trans, required_repository, tool_dependencies )
                        if required_repository_installed_tool_dependencies:
                            # Add the install_dir attribute to the tool_dependencies.
                            required_repository_installed_tool_dependencies = add_installation_directories_to_tool_dependencies( trans=trans,
                                                                                                                                 tool_dependencies=required_repository_installed_tool_dependencies )
                            for td_key, td_dict in required_repository_installed_tool_dependencies.items():
                                if td_key not in repository_installed_tool_dependencies:
                                    repository_installed_tool_dependencies[ td_key ] = td_dict
                        if required_repository_missing_tool_dependencies:
                            # Add the install_dir attribute to the tool_dependencies.
                            required_repository_missing_tool_dependencies = add_installation_directories_to_tool_dependencies( trans=trans,
                                                                                                                               tool_dependencies=required_repository_missing_tool_dependencies )
                            for td_key, td_dict in required_repository_missing_tool_dependencies.items():
                                if td_key not in repository_missing_tool_dependencies:
                                    repository_missing_tool_dependencies[ td_key ] = td_dict
    if repository_installed_tool_dependencies:
        installed_tool_dependencies = repository_installed_tool_dependencies
    if repository_missing_tool_dependencies:
        missing_tool_dependencies = repository_missing_tool_dependencies
    return installed_tool_dependencies, missing_tool_dependencies

def remove_tool_dependency( trans, tool_dependency ):
    dependency_install_dir = tool_dependency.installation_directory( trans.app )
    removed, error_message = remove_tool_dependency_installation_directory( dependency_install_dir )
    if removed:
        tool_dependency.status = trans.model.ToolDependency.installation_status.UNINSTALLED
        tool_dependency.error_message = None
        trans.sa_session.add( tool_dependency )
        trans.sa_session.flush()
    return removed, error_message

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
