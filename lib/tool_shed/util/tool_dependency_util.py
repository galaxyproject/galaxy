import logging
import os
import shutil

from sqlalchemy import and_

from galaxy import util
from galaxy.web.form_builder import SelectField
from tool_shed.util import hg_util
from tool_shed.util import xml_util

log = logging.getLogger( __name__ )


def build_tool_dependencies_select_field( app, tool_shed_repository, name, multiple=True, display='checkboxes',
                                          uninstalled_only=False ):
    """
    Generate a SelectField consisting of the current list of tool dependency ids
    for an installed tool shed repository.
    """
    tool_dependencies_select_field = SelectField( name=name, multiple=multiple, display=display )
    for tool_dependency in tool_shed_repository.tool_dependencies:
        if uninstalled_only:
            if tool_dependency.status not in [ app.install_model.ToolDependency.installation_status.NEVER_INSTALLED,
                                               app.install_model.ToolDependency.installation_status.UNINSTALLED ]:
                continue
        else:
            if tool_dependency.status in [ app.install_model.ToolDependency.installation_status.NEVER_INSTALLED,
                                           app.install_model.ToolDependency.installation_status.UNINSTALLED ]:
                continue
        option_label = '%s version %s' % ( str( tool_dependency.name ), str( tool_dependency.version ) )
        option_value = app.security.encode_id( tool_dependency.id )
        tool_dependencies_select_field.add_option( option_label, option_value )
    return tool_dependencies_select_field


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
            set_tool_dependency_attributes(app, tool_dependency=tool_dependency, status=status)
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


def get_platform_info_dict():
    '''Return a dict with information about the current platform.'''
    platform_dict = {}
    sysname, nodename, release, version, machine = os.uname()
    platform_dict[ 'os' ] = sysname.lower()
    platform_dict[ 'architecture' ] = machine.lower()
    return platform_dict


def get_tool_dependency( app, id ):
    """Get a tool_dependency from the database via id"""
    return app.install_model.context.query( app.install_model.ToolDependency ).get( app.security.decode_id( id ) )


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
        except Exception as e:
            removed = False
            error_message = "Error removing tool dependency installation directory %s: %s" % ( str( dependency_install_dir ), str( e ) )
            log.warning( error_message )
    else:
        removed = True
        error_message = ''
    return removed, error_message


def set_tool_dependency_attributes( app, tool_dependency, status, error_message=None ):
    sa_session = app.install_model.context
    if status == app.install_model.ToolDependency.installation_status.UNINSTALLED:
        installation_directory = tool_dependency.installation_directory( app )
        remove_tool_dependency_installation_directory( installation_directory )
    tool_dependency.error_message = error_message
    if str( tool_dependency.status ) != str( status ):
        tool_shed_repository = tool_dependency.tool_shed_repository
        debug_msg = 'Updating an existing record for version %s of tool dependency %s for revision %s of repository %s ' % \
            ( str( tool_dependency.version ), str( tool_dependency.name ), str( tool_shed_repository.changeset_revision ), str( tool_shed_repository.name ) )
        debug_msg += 'by updating the status from %s to %s.' % ( str( tool_dependency.status ), str( status ) )
        log.debug( debug_msg )
    tool_dependency.status = status
    sa_session.add( tool_dependency )
    sa_session.flush()
    return tool_dependency
