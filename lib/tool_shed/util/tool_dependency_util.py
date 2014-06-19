import logging
import os
import shutil
from galaxy import eggs
from galaxy import util
from galaxy.model.orm import and_
from galaxy.model.orm import or_
import tool_shed.util.shed_util_common as suc
import tool_shed.repository_types.util as rt_util
from tool_shed.util import basic_util
from tool_shed.util import hg_util
from tool_shed.util import xml_util

log = logging.getLogger( __name__ )

def add_installation_directories_to_tool_dependencies( app, tool_dependencies ):
    """
    Determine the path to the installation directory for each of the received tool dependencies.  This path will be
    displayed within the tool dependencies container on the select_tool_panel_section or reselect_tool_panel_section
    pages when installing or reinstalling repositories that contain tools with the defined tool dependencies.  The
    list of tool dependencies may be associated with more than a single repository.
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
        if app.config.tool_dependency_dir:
            root_dir = app.config.tool_dependency_dir
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
    """Create or update a tool_dependency record in the Galaxy database."""
    # Called from Galaxy (never the tool shed) when a new repository is being installed or when an uninstalled
    # repository is being reinstalled.
    context = app.install_model.context
    # First see if an appropriate tool_dependency record exists for the received tool_shed_repository.
    if version:
        tool_dependency = get_tool_dependency_by_name_version_type_repository( app, tool_shed_repository, name, version, type )
    else:
        tool_dependency = get_tool_dependency_by_name_type_repository( app, tool_shed_repository, name, type )
    if tool_dependency:
        # In some cases we should not override the current status of an existing tool_dependency, so do so only
        # if set_status is True.
        if set_status:
            if str( tool_dependency.status ) != str( status ):
                debug_msg = 'Updating an existing record for version %s of tool dependency %s for revision %s of repository %s ' % \
                    ( str( version ), str( name ), str( tool_shed_repository.changeset_revision ), str( tool_shed_repository.name ) )
                debug_msg += 'by updating the status from %s to %s.' % ( str( tool_dependency.status ), str( status ) )
                log.debug( debug_msg )
            tool_dependency.status = status
            context.add( tool_dependency )
            context.flush()
    else:
        # Create a new tool_dependency record for the tool_shed_repository.
        debug_msg = 'Creating a new record for version %s of tool dependency %s for revision %s of repository %s.  ' % \
             ( str( version ), str( name ), str( tool_shed_repository.changeset_revision ), str( tool_shed_repository.name ) )
        debug_msg += 'The status is being set to %s.' % str( status )
        log.debug( debug_msg )
        tool_dependency = app.install_model.ToolDependency( tool_shed_repository.id, name, version, type, status )
        context.add( tool_dependency )
        context.flush()
    return tool_dependency

def create_tool_dependency_objects( app, tool_shed_repository, relative_install_dir, set_status=True ):
    """
    Create or update a ToolDependency for each entry in tool_dependencies_config.  This method is called when
    installing a new tool_shed_repository.
    """
    tool_dependency_objects = []
    shed_config_dict = tool_shed_repository.get_shed_config_dict( app )
    if shed_config_dict.get( 'tool_path' ):
        relative_install_dir = os.path.join( shed_config_dict.get( 'tool_path' ), relative_install_dir )
    # Get the tool_dependencies.xml file from the repository.
    tool_dependencies_config = hg_util.get_config_from_disk( 'tool_dependencies.xml', relative_install_dir )
    tree, error_message = xml_util.parse_xml( tool_dependencies_config )
    if tree is None:
        return tool_dependency_objects
    root = tree.getroot()
    for elem in root:
        tool_dependency_type = elem.tag
        if tool_dependency_type == 'package':
            name = elem.get( 'name', None )
            version = elem.get( 'version', None )
            if name and version:
                status = app.install_model.ToolDependency.installation_status.NEVER_INSTALLED
                tool_dependency = create_or_update_tool_dependency( app,
                                                                    tool_shed_repository,
                                                                    name=name,
                                                                    version=version,
                                                                    type=tool_dependency_type,
                                                                    status=status,
                                                                    set_status=set_status )
                tool_dependency_objects.append( tool_dependency )
        elif tool_dependency_type == 'set_environment':
            for env_elem in elem:
                # <environment_variable name="R_SCRIPT_PATH" action="set_to">$REPOSITORY_INSTALL_DIR</environment_variable>
                name = env_elem.get( 'name', None )
                action = env_elem.get( 'action', None )
                if name and action:
                    status = app.install_model.ToolDependency.installation_status.NEVER_INSTALLED
                    tool_dependency = create_or_update_tool_dependency( app,
                                                                        tool_shed_repository,
                                                                        name=name,
                                                                        version=None,
                                                                        type=tool_dependency_type,
                                                                        status=status,
                                                                        set_status=set_status )
                    tool_dependency_objects.append( tool_dependency )
    return tool_dependency_objects

def generate_message_for_invalid_tool_dependencies( metadata_dict ):
    """
    Tool dependency definitions can only be invalid if they include a definition for a complex repository dependency and the repository
    dependency definition is invalid.  This method retrieves the error message associated with the invalid tool dependency for display
    in the caller.
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

def generate_message_for_orphan_tool_dependencies( trans, repository, metadata_dict ):
    """
    The designation of a ToolDependency into the "orphan" category has evolved over time, and is significantly restricted since the
    introduction of the TOOL_DEPENDENCY_DEFINITION repository type.  This designation is still critical, however, in that it handles
    the case where a repository contains both tools and a tool_dependencies.xml file, but the definition in the tool_dependencies.xml
    file is in no way related to anything defined by any of the contained tool's requirements tag sets.  This is important in that it
    is often a result of a typo (e.g., dependency name or version) that differs between the tool dependency definition within the
    tool_dependencies.xml file and what is defined in the tool config's <requirements> tag sets.  In these cases, the user should be
    presented with a warning message, and this warning message is is in fact displayed if the following is_orphan attribute is True.
    This is tricky because in some cases it may be intentional, and tool dependencies that are categorized as "orphan" are in fact valid.
    """
    has_orphan_package_dependencies = False
    has_orphan_set_environment_dependencies = False
    message = ''
    package_orphans_str = ''
    set_environment_orphans_str = ''
    # Tool dependencies are categorized as orphan only if the repository contains tools.
    if metadata_dict:
        tools = metadata_dict.get( 'tools', [] )
        invalid_tools = metadata_dict.get( 'invalid_tools', [] )
        tool_dependencies = metadata_dict.get( 'tool_dependencies', {} )
        # The use of the orphan_tool_dependencies category in metadata has been deprecated, but we still need to check in case
        # the metadata is out of date.
        orphan_tool_dependencies = metadata_dict.get( 'orphan_tool_dependencies', {} )
        # Updating should cause no problems here since a tool dependency cannot be included in both dictionaries.
        tool_dependencies.update( orphan_tool_dependencies )
        if tool_dependencies and ( tools or invalid_tools ):
            for td_key, requirements_dict in tool_dependencies.items():
                if td_key == 'set_environment':
                    # "set_environment": [{"name": "R_SCRIPT_PATH", "type": "set_environment"}]
                    for env_requirements_dict in requirements_dict:
                        name = env_requirements_dict[ 'name' ]
                        type = env_requirements_dict[ 'type' ]
                        if tool_dependency_is_orphan( type, name, None, tools ):
                            if not has_orphan_set_environment_dependencies:
                                has_orphan_set_environment_dependencies = True
                            set_environment_orphans_str += "<b>* name:</b> %s, <b>type:</b> %s<br/>" % ( str( name ), str( type ) )
                else:
                    # "R/2.15.1": {"name": "R", "readme": "some string", "type": "package", "version": "2.15.1"}
                    name = requirements_dict[ 'name' ]
                    type = requirements_dict[ 'type' ]
                    version = requirements_dict[ 'version' ]
                    if tool_dependency_is_orphan( type, name, version, tools ):
                        if not has_orphan_package_dependencies:
                            has_orphan_package_dependencies = True
                        package_orphans_str += "<b>* name:</b> %s, <b>type:</b> %s, <b>version:</b> %s<br/>" % \
                            ( str( name ), str( type ), str( version ) )
    if has_orphan_package_dependencies:
        message += "The settings for <b>name</b>, <b>version</b> and <b>type</b> from a contained tool configuration file's "
        message += "<b>requirement</b> tag does not match the information for the following tool dependency definitions in the "
        message += "<b>tool_dependencies.xml</b> file, so these tool dependencies have no relationship with any tools within "
        message += "this repository.<br/>"
        message += package_orphans_str
    if has_orphan_set_environment_dependencies:
        message += "The settings for <b>name</b> and <b>type</b> from a contained tool configuration file's <b>requirement</b> tag "
        message += "does not match the information for the following tool dependency definitions in the <b>tool_dependencies.xml</b> "
        message += "file, so these tool dependencies have no relationship with any tools within this repository.<br/>"
        message += set_environment_orphans_str
    return message

def get_download_url_for_platform( url_templates, platform_info_dict ):
    '''
    Compare the dict returned by get_platform_info() with the values specified in the url_template element. Return
    true if and only if all defined attributes match the corresponding dict entries. If an entry is not
    defined in the url_template element, it is assumed to be irrelevant at this stage. For example,
    <url_template os="darwin">http://hgdownload.cse.ucsc.edu/admin/exe/macOSX.${architecture}/faToTwoBit</url_template>
    where the OS must be 'darwin', but the architecture is filled in later using string.Template.
    '''
    os_ok = False
    architecture_ok = False
    for url_template in url_templates:
        os_name = url_template.get( 'os', None )
        architecture = url_template.get( 'architecture', None )
        if os_name:
            if os_name.lower() == platform_info_dict[ 'os' ]:
                os_ok = True
            else:
                os_ok = False
        else:
            os_ok = True
        if architecture:
            if architecture.lower() == platform_info_dict[ 'architecture' ]:
                architecture_ok = True
            else:
                architecture_ok = False
        else:
            architecture_ok = True
        if os_ok and architecture_ok:
            return url_template
    return None

def get_installed_and_missing_tool_dependencies_for_installed_repository( app, repository, all_tool_dependencies ):
    """
    Return the lists of installed tool dependencies and missing tool dependencies for a Tool Shed
    repository that has been installed into Galaxy.
    """
    if all_tool_dependencies:
        tool_dependencies = {}
        missing_tool_dependencies = {}
        for td_key, val in all_tool_dependencies.items():
            if td_key in [ 'set_environment' ]:
                for index, td_info_dict in enumerate( val ):
                    name = td_info_dict[ 'name' ]
                    version = None
                    type = td_info_dict[ 'type' ]
                    tool_dependency = get_tool_dependency_by_name_type_repository( app, repository, name, type )
                    if tool_dependency:
                        td_info_dict[ 'repository_id' ] = repository.id
                        td_info_dict[ 'tool_dependency_id' ] = tool_dependency.id
                        if tool_dependency.status:
                            tool_dependency_status = str( tool_dependency.status )
                        else:
                            tool_dependency_status = 'Never installed'
                        td_info_dict[ 'status' ] = tool_dependency_status
                        val[ index ] = td_info_dict
                        if tool_dependency.status == app.install_model.ToolDependency.installation_status.INSTALLED:
                            tool_dependencies[ td_key ] = val
                        else:
                            missing_tool_dependencies[ td_key ] = val
            else:
                name = val[ 'name' ]
                version = val[ 'version' ]
                type = val[ 'type' ]
                tool_dependency = get_tool_dependency_by_name_version_type_repository( app, repository, name, version, type )
                if tool_dependency:
                    val[ 'repository_id' ] = repository.id
                    val[ 'tool_dependency_id' ] = tool_dependency.id
                    if tool_dependency.status:
                        tool_dependency_status = str( tool_dependency.status )
                    else:
                        tool_dependency_status = 'Never installed'
                    val[ 'status' ] = tool_dependency_status
                    if tool_dependency.status == app.install_model.ToolDependency.installation_status.INSTALLED:
                        tool_dependencies[ td_key ] = val
                    else:
                        missing_tool_dependencies[ td_key ] = val
    else:
        tool_dependencies = None
        missing_tool_dependencies = None
    return tool_dependencies, missing_tool_dependencies

def get_platform_info_dict():
    '''Return a dict with information about the current platform.'''
    platform_dict = {}
    sysname, nodename, release, version, machine = os.uname()
    platform_dict[ 'os' ] = sysname.lower()
    platform_dict[ 'architecture' ] = machine.lower()
    return platform_dict

def get_required_repository_package_env_sh_path( app, package_name, package_version, required_repository ):
    """Return path to env.sh file in required repository if the required repository has been installed."""
    env_sh_file_dir = get_tool_dependency_install_dir( app=app,
                                                       repository_name=required_repository.name,
                                                       repository_owner=required_repository.owner,
                                                       repository_changeset_revision=required_repository.installed_changeset_revision,
                                                       tool_dependency_type='package',
                                                       tool_dependency_name=package_name,
                                                       tool_dependency_version=package_version )
    env_sh_file_path = os.path.join( env_sh_file_dir, 'env.sh' )
    return env_sh_file_path

def get_tool_dependency( trans, id ):
    """Get a tool_dependency from the database via id"""
    return trans.install_model.context.query( trans.install_model.ToolDependency ).get( trans.security.decode_id( id ) )

def get_tool_dependency_by_name_type_repository( app, repository, name, type ):
    context = app.install_model.context
    return context.query( app.install_model.ToolDependency ) \
                     .filter( and_( app.install_model.ToolDependency.table.c.tool_shed_repository_id == repository.id,
                                    app.install_model.ToolDependency.table.c.name == name,
                                    app.install_model.ToolDependency.table.c.type == type ) ) \
                     .first()

def get_tool_dependency_by_name_version_type( app, name, version, type ):
    context = app.install_model.context
    return context.query( app.install_model.ToolDependency ) \
                     .filter( and_( app.install_model.ToolDependency.table.c.name == name,
                                    app.install_model.ToolDependency.table.c.version == version,
                                    app.install_model.ToolDependency.table.c.type == type ) ) \
                     .first()

def get_tool_dependency_by_name_version_type_repository( app, repository, name, version, type ):
    context = app.install_model.context
    return context.query( app.install_model.ToolDependency ) \
                     .filter( and_( app.install_model.ToolDependency.table.c.tool_shed_repository_id == repository.id,
                                    app.install_model.ToolDependency.table.c.name == name,
                                    app.install_model.ToolDependency.table.c.version == version,
                                    app.install_model.ToolDependency.table.c.type == type ) ) \
                     .first()

def get_tool_dependency_ids( as_string=False, **kwd ):
    tool_dependency_id = kwd.get( 'tool_dependency_id', None )
    if 'tool_dependency_ids' in kwd:
        tool_dependency_ids = util.listify( kwd[ 'tool_dependency_ids' ] )
    elif 'id' in kwd:
        tool_dependency_ids = util.listify( kwd[ 'id' ] )
    elif 'inst_td_ids' in kwd:
        tool_dependency_ids = util.listify( kwd[ 'inst_td_ids' ] )
    elif 'uninstalled_tool_dependency_ids' in kwd:
        tool_dependency_ids = util.listify( kwd[ 'uninstalled_tool_dependency_ids' ] )
    else:
        tool_dependency_ids = []
    if tool_dependency_id and tool_dependency_id not in tool_dependency_ids:
        tool_dependency_ids.append( tool_dependency_id )
    if as_string:
        return ','.join( tool_dependency_ids )
    return tool_dependency_ids

def get_tool_dependency_install_dir( app, repository_name, repository_owner, repository_changeset_revision, tool_dependency_type,
                                     tool_dependency_name, tool_dependency_version ):
    if tool_dependency_type == 'package':
        return os.path.abspath( os.path.join( app.config.tool_dependency_dir,
                                              tool_dependency_name,
                                              tool_dependency_version,
                                              repository_owner,
                                              repository_name,
                                              repository_changeset_revision ) )
    if tool_dependency_type == 'set_environment':
        return os.path.abspath( os.path.join( app.config.tool_dependency_dir,
                                              'environment_settings',
                                              tool_dependency_name,
                                              repository_owner,
                                              repository_name,
                                              repository_changeset_revision ) )

def handle_tool_dependency_installation_error( app, tool_dependency, error_message, remove_installation_path=False ):
    # Since there was an installation error, remove the installation directory because the install_package method uses 
    # this: "if os.path.exists( install_dir ):". Setting remove_installation_path to True should rarely occur. It is
    # currently set to True only to handle issues with installing tool dependencies into an Amazon S3 bucket. 
    sa_session = app.install_model.context
    tool_shed_repository = tool_dependency.tool_shed_repository
    install_dir = get_tool_dependency_install_dir( app=app,
                                                   repository_name=tool_shed_repository.name,
                                                   repository_owner=tool_shed_repository.owner,
                                                   repository_changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                   tool_dependency_type=tool_dependency.type,
                                                   tool_dependency_name=tool_dependency.name,
                                                   tool_dependency_version=tool_dependency.version )
    if remove_installation_path:
        # This will be True only in the case where an exception was encountered during the installation process after
        # the installation path was created but before any information was written to the installation log and the
        # tool dependency status was not set to "Installed" or "Error". 
        if os.path.exists( install_dir ):
            log.debug( 'Attempting to remove installation directory %s for version %s of tool dependency %s %s' % \
                ( str( install_dir ), str( tool_dependency.version ), str( tool_dependency.type ), str( tool_dependency.name ) ) )
            log.debug( 'due to the following installation error:\n%s' % str( error_message ) )
            try:
                shutil.rmtree( install_dir )
            except Exception, e:
                log.exception( 'Error removing existing installation directory %s.', install_dir )
    tool_dependency.status = app.install_model.ToolDependency.installation_status.ERROR
    tool_dependency.error_message = error_message
    sa_session.add( tool_dependency )
    sa_session.flush()
    return tool_dependency

def parse_package_elem( package_elem, platform_info_dict=None, include_after_install_actions=True ):
    """
    Parse a <package> element within a tool dependency definition and return a list of action tuples.
    This method is called when setting metadata on a repository that includes a tool_dependencies.xml
    file or when installing a repository that includes a tool_dependencies.xml file.  If installing,
    platform_info_dict must be a valid dictionary and include_after_install_actions must be True.
    """
    # The actions_elem_tuples list contains <actions> tag sets (possibly inside of an <actions_group>
    # tag set) to be processed in the order they are defined in the tool_dependencies.xml file.
    actions_elem_tuples = []
    # The tag sets that will go into the actions_elem_list are those that install a compiled binary if
    # the architecture and operating system match its defined attributes.  If compiled binary is not
    # installed, the first <actions> tag set [following those that have the os and architecture attributes]
    # that does not have os or architecture attributes will be processed.  This tag set must contain the
    # recipe for downloading and compiling source.
    actions_elem_list = []
    for elem in package_elem:
        if elem.tag == 'actions':
            # We have an <actions> tag that should not be matched against a specific combination of
            # architecture and operating system.
            in_actions_group = False
            actions_elem_tuples.append( ( in_actions_group, elem ) )
        elif elem.tag == 'actions_group':
            # We have an actions_group element, and its child <actions> elements should therefore be compared
            # with the current operating system
            # and processor architecture.
            in_actions_group = True
            # Record the number of <actions> elements so we can filter out any <action> elements that precede
            # <actions> elements.
            actions_elem_count = len( elem.findall( 'actions' ) )
            # Record the number of <actions> elements that have both architecture and os specified, in order
            # to filter out any platform-independent <actions> elements that come before platform-specific
            # <actions> elements.
            platform_actions_elements = []
            for actions_elem in elem.findall( 'actions' ):
                if actions_elem.get( 'architecture' ) is not None and actions_elem.get( 'os' ) is not None:
                    platform_actions_elements.append( actions_elem )
            platform_actions_element_count = len( platform_actions_elements )
            platform_actions_elements_processed = 0
            actions_elems_processed = 0
            # The tag sets that will go into the after_install_actions list are <action> tags instead of <actions>
            # tags.  These will be processed only if they are at the very end of the <actions_group> tag set (after
            # all <actions> tag sets). See below for details.
            after_install_actions = []
            # Inspect the <actions_group> element and build the actions_elem_list and the after_install_actions list.
            for child_element in elem:
                if child_element.tag == 'actions':
                    actions_elems_processed += 1
                    system = child_element.get( 'os' )
                    architecture = child_element.get( 'architecture' )
                    # Skip <actions> tags that have only one of architecture or os specified, in order for the
                    # count in platform_actions_elements_processed to remain accurate.
                    if ( system and not architecture ) or ( architecture and not system ):
                        log.debug( 'Error: Both architecture and os attributes must be specified in an <actions> tag.' )
                        continue
                    # Since we are inside an <actions_group> tag set, compare it with our current platform information
                    # and filter the <actions> tag sets that don't match. Require both the os and architecture attributes
                    # to be defined in order to find a match.
                    if system and architecture:
                        platform_actions_elements_processed += 1
                        # If either the os or architecture do not match the platform, this <actions> tag will not be
                        # considered a match. Skip it and proceed with checking the next one.
                        if platform_info_dict:
                            if platform_info_dict[ 'os' ] != system or platform_info_dict[ 'architecture' ] != architecture:
                                continue
                        else:
                            # We must not be installing a repository into Galaxy, so determining if we can install a
                            # binary is not necessary.
                            continue
                    else:
                        # <actions> tags without both os and architecture attributes are only allowed to be specified
                        # after platform-specific <actions> tags. If we find a platform-independent <actions> tag before
                        # all platform-specific <actions> tags have been processed.
                        if platform_actions_elements_processed < platform_actions_element_count:
                            debug_msg = 'Error: <actions> tags without os and architecture attributes are only allowed '
                            debug_msg += 'after all <actions> tags with os and architecture attributes have been defined.  '
                            debug_msg += 'Skipping the <actions> tag set with no os or architecture attributes that has '
                            debug_msg += 'been defined between two <actions> tag sets that have these attributes defined.  '
                            log.debug( debug_msg )
                            continue
                    # If we reach this point, it means one of two things: 1) The system and architecture attributes are
                    # not defined in this <actions> tag, or 2) The system and architecture attributes are defined, and
                    # they are an exact match for the current platform. Append the child element to the list of elements
                    # to process.
                    actions_elem_list.append( child_element )
                elif child_element.tag == 'action':
                    # Any <action> tags within an <actions_group> tag set must come after all <actions> tags.
                    if actions_elems_processed == actions_elem_count:
                        # If all <actions> elements have been processed, then this <action> element can be appended to the
                        # list of actions to execute within this group.
                        after_install_actions.append( child_element )
                    else:
                        # If any <actions> elements remain to be processed, then log a message stating that <action>
                        # elements are not allowed to precede any <actions> elements within an <actions_group> tag set.
                        debug_msg = 'Error: <action> tags are only allowed at the end of an <actions_group> tag set after '
                        debug_msg += 'all <actions> tags.  Skipping <%s> element with type %s.' % \
                            ( child_element.tag, child_element.get( 'type', 'unknown' ) )
                        log.debug( debug_msg )
                        continue
            if platform_info_dict is None and not include_after_install_actions:
                # We must be setting metadata on a repository.
                if len( actions_elem_list ) >= 1:
                    actions_elem_tuples.append( ( in_actions_group, actions_elem_list[ 0 ] ) )
                else:
                    # We are processing a recipe that contains only an <actions_group> tag set for installing a binary,
                    # but does not include an additional recipe for installing and compiling from source.
                    actions_elem_tuples.append( ( in_actions_group, [] ) )
            elif platform_info_dict is not None and include_after_install_actions:
                # We must be installing a repository.
                if after_install_actions:
                    actions_elem_list.extend( after_install_actions )
                actions_elem_tuples.append( ( in_actions_group, actions_elem_list ) )
        else:
            # Skip any element that is not <actions> or <actions_group> - this will skip comments, <repository> tags
            # and <readme> tags.
            in_actions_group = False
            continue
    return actions_elem_tuples

def populate_tool_dependencies_dicts( app, tool_shed_url, tool_path, repository_installed_tool_dependencies,
                                      repository_missing_tool_dependencies, required_repo_info_dicts ):
    """
    Return the populated installed_tool_dependencies and missing_tool_dependencies dictionaries for all
    repositories defined by entries in the received required_repo_info_dicts.
    """
    installed_tool_dependencies = None
    missing_tool_dependencies = None
    if repository_installed_tool_dependencies is None:
        repository_installed_tool_dependencies = {}
    else:
        # Add the install_dir attribute to the tool_dependencies.
        repository_installed_tool_dependencies = \
            add_installation_directories_to_tool_dependencies( app=app,
                                                               tool_dependencies=repository_installed_tool_dependencies )
    if repository_missing_tool_dependencies is None:
        repository_missing_tool_dependencies = {}
    else:
        # Add the install_dir attribute to the tool_dependencies.
        repository_missing_tool_dependencies = \
            add_installation_directories_to_tool_dependencies( app=app,
                                                               tool_dependencies=repository_missing_tool_dependencies )
    if required_repo_info_dicts:
        # Handle the tool dependencies defined for each of the repository's repository dependencies.
        for rid in required_repo_info_dicts:
            for name, repo_info_tuple in rid.items():
                description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
                    suc.get_repo_info_tuple_contents( repo_info_tuple )
                if tool_dependencies:
                    # Add the install_dir attribute to the tool_dependencies.
                    tool_dependencies = add_installation_directories_to_tool_dependencies( app=app,
                                                                                           tool_dependencies=tool_dependencies )
                    # The required_repository may have been installed with a different changeset revision.
                    required_repository, installed_changeset_revision = \
                        suc.repository_was_previously_installed( app, tool_shed_url, name, repo_info_tuple, from_tip=False )
                    if required_repository:
                        required_repository_installed_tool_dependencies, required_repository_missing_tool_dependencies = \
                            get_installed_and_missing_tool_dependencies_for_installed_repository( app,
                                                                                                  required_repository,
                                                                                                  tool_dependencies )
                        if required_repository_installed_tool_dependencies:
                            # Add the install_dir attribute to the tool_dependencies.
                            required_repository_installed_tool_dependencies = \
                                add_installation_directories_to_tool_dependencies( app=app,
                                                                                   tool_dependencies=required_repository_installed_tool_dependencies )
                            for td_key, td_dict in required_repository_installed_tool_dependencies.items():
                                if td_key not in repository_installed_tool_dependencies:
                                    repository_installed_tool_dependencies[ td_key ] = td_dict
                        if required_repository_missing_tool_dependencies:
                            # Add the install_dir attribute to the tool_dependencies.
                            required_repository_missing_tool_dependencies = \
                                add_installation_directories_to_tool_dependencies( app=app,
                                                                                   tool_dependencies=required_repository_missing_tool_dependencies )
                            for td_key, td_dict in required_repository_missing_tool_dependencies.items():
                                if td_key not in repository_missing_tool_dependencies:
                                    repository_missing_tool_dependencies[ td_key ] = td_dict
    if repository_installed_tool_dependencies:
        installed_tool_dependencies = repository_installed_tool_dependencies
    if repository_missing_tool_dependencies:
        missing_tool_dependencies = repository_missing_tool_dependencies
    return installed_tool_dependencies, missing_tool_dependencies

def remove_tool_dependency( app, tool_dependency ):
    """The received tool_dependency must be in an error state."""
    context = app.install_model.context
    dependency_install_dir = tool_dependency.installation_directory( app )
    removed, error_message = remove_tool_dependency_installation_directory( dependency_install_dir )
    if removed:
        tool_dependency.status = app.install_model.ToolDependency.installation_status.UNINSTALLED
        tool_dependency.error_message = None
        context.add( tool_dependency )
        context.flush()
        # Since the received tool_dependency is in an error state, nothing will need to be changed in any
        # of the in-memory dictionaries in the installed_repository_manager because changing the state from
        # error to uninstalled requires no in-memory changes..
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

def set_tool_dependency_attributes( app, tool_dependency, status, error_message=None, remove_from_disk=False ):
    sa_session = app.install_model.context
    if remove_from_disk:
        installation_directory = tool_dependency.installation_directory( app )
        removed, err_msg = remove_tool_dependency_installation_directory( installation_directory )
    tool_dependency.error_message = error_message
    tool_dependency.status = status
    sa_session.add( tool_dependency )
    sa_session.flush()
    return tool_dependency

def sync_database_with_file_system( app, tool_shed_repository, tool_dependency_name, tool_dependency_version,
                                    tool_dependency_install_dir, tool_dependency_type='package' ):
    """
    The installation directory defined by the received tool_dependency_install_dir exists, so check for
    the presence of INSTALLATION_LOG.  If the files exists, we'll assume the tool dependency is installed,
    but not necessarily successfully (it could be in an error state on disk.  However, we can justifiably
    assume here that no matter the state, an associated database record will exist.
    """
    # This method should be reached very rarely.  It implies that either the Galaxy environment became corrupted (i.e.,
    # the database records for installed tool dependencies is not synchronized with tool dependencies on disk) or the Tool
    # Shed's install and test framework is running.  The Tool Shed's install and test framework installs repositories
    # in 2 stages, those of type tool_dependency_definition followed by those containing valid tools and tool functional
    # test components.
    log.debug( "Synchronizing the database with the file system..." )
    try:
        log.debug( "The value of app.config.running_functional_tests is: %s" % str( app.config.running_functional_tests ) )
    except:
        pass
    sa_session = app.install_model.context
    can_install_tool_dependency = False
    tool_dependency = get_tool_dependency_by_name_version_type_repository( app,
                                                                           tool_shed_repository,
                                                                           tool_dependency_name,
                                                                           tool_dependency_version,
                                                                           tool_dependency_type )
    if tool_dependency.status == app.install_model.ToolDependency.installation_status.INSTALLING:
        # The tool dependency is in an Installing state, so we don't want to do anything to it.  If the tool
        # dependency is being installed by someone else, we don't want to interfere with that.  This assumes
        # the installation by "someone else" is not hung in an Installing state, which is a weakness if that
        # "someone else" never repaired it.
        log.debug( 'Skipping installation of tool dependency %s version %s because it has a status of %s' % \
            ( str( tool_dependency.name ), str( tool_dependency.version ), str( tool_dependency.status ) ) )
    else:
        # We have a pre-existing installation directory on the file system, but our associated database record is
        # in a state that allowed us to arrive here.  At this point, we'll inspect the installation directory to
        # see if we have a "proper installation" and if so, synchronize the database record rather than reinstalling
        # the dependency if we're "running_functional_tests".  If we're not "running_functional_tests, we'll set
        # the tool dependency's installation status to ERROR.
        tool_dependency_installation_directory_contents = os.listdir( tool_dependency_install_dir )
        if basic_util.INSTALLATION_LOG in tool_dependency_installation_directory_contents:
            # Since this tool dependency's installation directory contains an installation log, we consider it to be
            # installed.  In some cases the record may be missing from the database due to some activity outside of
            # the control of the Tool Shed.  Since a new record was created for it and we don't know the state of the
            # files on disk, we will set it to an error state (unless we are running Tool Shed functional tests - see
            # below).
            log.debug( 'Skipping installation of tool dependency %s version %s because it is installed in %s' % \
                ( str( tool_dependency.name ), str( tool_dependency.version ), str( tool_dependency_install_dir ) ) )
            if app.config.running_functional_tests:
                # If we are running functional tests, the state will be set to Installed because previously compiled
                # tool dependencies are not deleted by default, from the "install and test" framework..
                tool_dependency.status = app.install_model.ToolDependency.installation_status.INSTALLED
            else:
                error_message = 'The installation directory for this tool dependency had contents but the database had no record. '
                error_message += 'The installation log may show this tool dependency to be correctly installed, but due to the '
                error_message += 'missing database record it is now being set to Error.'
                tool_dependency.status = app.install_model.ToolDependency.installation_status.ERROR
                tool_dependency.error_message = error_message
        else:
            error_message = '\nInstallation path %s for tool dependency %s version %s exists, but the expected file %s' % \
                ( str( tool_dependency_install_dir ),
                  str( tool_dependency_name ),
                  str( tool_dependency_version ),
                  str( basic_util.INSTALLATION_LOG ) )
            error_message += ' is missing.  This indicates an installation error so the tool dependency is being'
            error_message += ' prepared for re-installation.'
            print error_message
            tool_dependency.status = app.install_model.ToolDependency.installation_status.NEVER_INSTALLED
            basic_util.remove_dir( tool_dependency_install_dir )
            can_install_tool_dependency = True
        sa_session.add( tool_dependency )
        sa_session.flush()
    try:
        log.debug( "Returning from sync_database_with_file_system with tool_dependency %s, can_install_tool_dependency %s." % \
            ( str( tool_dependency.name ), str( can_install_tool_dependency ) ) )
    except Exception, e:
        log.debug( str( e ) )
    return tool_dependency, can_install_tool_dependency

def tool_dependency_is_orphan( type, name, version, tools ):
    """
    Determine if the combination of the received type, name and version is defined in the <requirement> tag for at least one tool in the
    received list of tools.  If not, the tool dependency defined by the combination is considered an orphan in its repository in the tool
    shed.
    """
    if type == 'package':
        if name and version:
            for tool_dict in tools:
                requirements = tool_dict.get( 'requirements', [] )
                for requirement_dict in requirements:
                    req_name = requirement_dict.get( 'name', None )
                    req_version = requirement_dict.get( 'version', None )
                    req_type = requirement_dict.get( 'type', None )
                    if req_name == name and req_version == version and req_type == type:
                        return False
    elif type == 'set_environment':
        if name:
            for tool_dict in tools:
                requirements = tool_dict.get( 'requirements', [] )
                for requirement_dict in requirements:
                    req_name = requirement_dict.get( 'name', None )
                    req_type = requirement_dict.get( 'type', None )
                    if req_name == name and req_type == type:
                        return False
    return True
