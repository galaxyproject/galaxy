import logging
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from string import Template
import fabric_util
import td_common_util
import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_util
from tool_shed.util import encoding_util
from tool_shed.util import tool_dependency_util
from tool_shed.util import xml_util
from tool_shed.galaxy_install.tool_dependencies import td_common_util
from galaxy.model.orm import and_
from galaxy.util import asbool
from galaxy.util import listify

log = logging.getLogger( __name__ )

def create_temporary_tool_dependencies_config( app, tool_shed_url, name, owner, changeset_revision ):
    """Make a call to the tool shed to get the required repository's tool_dependencies.xml file."""
    url = url_join( tool_shed_url,
                    'repository/get_tool_dependencies_config_contents?name=%s&owner=%s&changeset_revision=%s' % ( name, owner, changeset_revision ) )
    text = common_util.tool_shed_get( app, tool_shed_url, url )
    if text:
        # Write the contents to a temporary file on disk so it can be reloaded and parsed.
        fh = tempfile.NamedTemporaryFile( 'wb', prefix="tmp-toolshed-cttdc"  )
        tmp_filename = fh.name
        fh.close()
        fh = open( tmp_filename, 'wb' )
        fh.write( text )
        fh.close()
        return tmp_filename
    else:
        message = "Unable to retrieve required tool_dependencies.xml file from the tool shed for revision "
        message += "%s of installed repository %s owned by %s." % ( str( changeset_revision ), str( name ), str( owner ) )
        raise Exception( message )
        return None

def create_tool_dependency_with_initialized_env_sh_file( app, dependent_install_dir, tool_shed_repository, required_repository, package_name,
                                                         package_version, tool_dependencies_config ):
    """
    Create or get a tool_dependency record that is defined by the received package_name and package_version.  An env.sh file will be
    created for the tool_dependency in the received dependent_install_dir.
    """
    #The received required_repository refers to a tool_shed_repository record that is defined as a complex repository dependency for this
    # tool_dependency.  The required_repository may or may not be currently installed (it doesn't matter).  If it is installed, it is
    # associated with a tool_dependency that has an env.sh file that this new tool_dependency must be able to locate and "source".  If it
    # is not installed, we can still determine where that env.sh file will be, so we'll initialize this new tool_dependency's env.sh file
    # in either case.  If the require repository end up with an installation error, this new tool dependency will still be fine because its
    # containing repository will be defined as missing dependencies.
    tool_dependencies = []
    if not os.path.exists( dependent_install_dir ):
        os.makedirs( dependent_install_dir )
    required_tool_dependency_env_file_path = None
    if tool_dependencies_config:
        required_td_tree, error_message = xml_util.parse_xml( tool_dependencies_config )
        if required_td_tree:
            required_td_root = required_td_tree.getroot()
            for required_td_elem in required_td_root:
                # Find the appropriate package name and version.
                if required_td_elem.tag == 'package':
                    # <package name="bwa" version="0.5.9">
                    required_td_package_name = required_td_elem.get( 'name', None )
                    required_td_package_version = required_td_elem.get( 'version', None )
                    # Check the database to see if we have a record for the required tool dependency (we may not which is ok).  If we
                    # find a record, we need to see if it is in an error state and if so handle it appropriately.
                    required_tool_dependency = \
                        tool_dependency_util.get_tool_dependency_by_name_version_type_repository( app,
                                                                                                  required_repository,
                                                                                                  required_td_package_name,
                                                                                                  required_td_package_version,
                                                                                                  'package' )
                    if required_td_package_name == package_name and required_td_package_version == package_version:
                        # Get or create a database tool_dependency record with which the installed package on disk will be associated.
                        tool_dependency = \
                            tool_dependency_util.create_or_update_tool_dependency( app=app,
                                                                                   tool_shed_repository=tool_shed_repository,
                                                                                   name=package_name,
                                                                                   version=package_version,
                                                                                   type='package',
                                                                                   status=app.install_model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                                                   set_status=True )
                        # Create an env.sh file for the tool_dependency whose first line will source the env.sh file located in
                        # the path defined by required_tool_dependency_env_file_path.  It doesn't matter if the required env.sh
                        # file currently exists..
                        required_tool_dependency_env_file_path = \
                            tool_dependency_util.get_required_repository_package_env_sh_path( app,
                                                                                              package_name,
                                                                                              package_version,
                                                                                              required_repository )
                        env_file_builder = fabric_util.EnvFileBuilder( tool_dependency.installation_directory( app ) )
                        env_file_builder.append_line( action="source", value=required_tool_dependency_env_file_path )
                        return_code = env_file_builder.return_code
                        if return_code:
                            error_message = 'Error defining env.sh file for package %s, return_code: %s' % \
                                ( str( package_name ), str( return_code ) )
                            tool_dependency = \
                                tool_dependency_util.handle_tool_dependency_installation_error( app,
                                                                                                tool_dependency,
                                                                                                error_message,
                                                                                                remove_installation_path=False )
                        elif required_tool_dependency is not None and required_tool_dependency.in_error_state:
                            error_message = "This tool dependency's required tool dependency %s version %s has status %s." % \
                                ( str( required_tool_dependency.name ), str( required_tool_dependency.version ), str( required_tool_dependency.status ) )
                            tool_dependency = \
                                tool_dependency_util.handle_tool_dependency_installation_error( app,
                                                                                                tool_dependency,
                                                                                                error_message,
                                                                                                remove_installation_path=False )
                        else:
                            tool_dependency = \
                                tool_dependency_util.set_tool_dependency_attributes( app,
                                                                                     tool_dependency=tool_dependency,
                                                                                     status=app.install_model.ToolDependency.installation_status.INSTALLED )
                        tool_dependencies.append( tool_dependency )
    return tool_dependencies

def get_absolute_path_to_file_in_repository( repo_files_dir, file_name ):
    """Return the absolute path to a specified disk file contained in a repository."""
    stripped_file_name = strip_path( file_name )
    file_path = None
    for root, dirs, files in os.walk( repo_files_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name == stripped_file_name:
                    return os.path.abspath( os.path.join( root, name ) )
    return file_path

def get_tool_shed_repository_by_tool_shed_name_owner_changeset_revision( app, tool_shed_url, name, owner, changeset_revision ):
    sa_session = app.install_model.context
    tool_shed = td_common_util.clean_tool_shed_url( tool_shed_url )
    tool_shed_repository =  sa_session.query( app.install_model.ToolShedRepository ) \
                                      .filter( and_( app.install_model.ToolShedRepository.table.c.tool_shed == tool_shed,
                                                     app.install_model.ToolShedRepository.table.c.name == name,
                                                     app.install_model.ToolShedRepository.table.c.owner == owner,
                                                     app.install_model.ToolShedRepository.table.c.changeset_revision == changeset_revision ) ) \
                                      .first()
    if tool_shed_repository:
        return tool_shed_repository
    # The tool_shed_repository must have been updated to a newer changeset revision than the one defined in the repository_dependencies.xml file,
    # so call the tool shed to get all appropriate newer changeset revisions.
    text = get_updated_changeset_revisions_from_tool_shed( app, tool_shed_url, name, owner, changeset_revision )
    if text:
        changeset_revisions = listify( text )
        for changeset_revision in changeset_revisions:
            tool_shed_repository = sa_session.query( app.install_model.ToolShedRepository ) \
                                             .filter( and_( app.install_model.ToolShedRepository.table.c.tool_shed == tool_shed,
                                                            app.install_model.ToolShedRepository.table.c.name == name,
                                                            app.install_model.ToolShedRepository.table.c.owner == owner,
                                                            app.install_model.ToolShedRepository.table.c.changeset_revision == changeset_revision ) ) \
                                             .first()
            if tool_shed_repository:
                return tool_shed_repository
    return None

def get_tool_shed_repository_install_dir( app, tool_shed_repository ):
    return os.path.abspath( tool_shed_repository.repo_files_directory( app ) )

def get_updated_changeset_revisions_from_tool_shed( app, tool_shed_url, name, owner, changeset_revision ):
    """
    Get all appropriate newer changeset revisions for the repository defined by
    the received tool_shed_url / name / owner combination.
    """
    url = suc.url_join( tool_shed_url,
                        'repository/updated_changeset_revisions?name=%s&owner=%s&changeset_revision=%s' % ( name, owner, changeset_revision ) )
    text = common_util.tool_shed_get( app, tool_shed_url, url )
    return text


def handle_complex_repository_dependency_for_package( app, elem, package_name, package_version, tool_shed_repository, from_install_manager=False ):
    """
    Inspect the repository defined by a complex repository dependency definition and take certain steps to enable installation
    of the received package name and version to proceed.  The received elem is the <repository> tag set which defines the complex
    repository dependency.  The received tool_shed_repository is the installed tool shed repository for which the tool dependency
    defined by the received package_name and package_version is being installed.
    """
    handled_tool_dependencies = []
    tool_shed = elem.attrib[ 'toolshed' ]
    required_repository_name = elem.attrib[ 'name' ]
    required_repository_owner = elem.attrib[ 'owner' ]
    default_required_repository_changeset_revision = elem.attrib[ 'changeset_revision' ]
    required_repository = get_tool_shed_repository_by_tool_shed_name_owner_changeset_revision( app,
                                                                                               tool_shed,
                                                                                               required_repository_name,
                                                                                               required_repository_owner,
                                                                                               default_required_repository_changeset_revision )
    tmp_filename = None
    if required_repository:
        required_repository_changeset_revision = required_repository.installed_changeset_revision
        # Define the installation directory for the required tool dependency package in the required repository.
        required_repository_package_install_dir = \
            tool_dependency_util.get_tool_dependency_install_dir( app=app,
                                                                  repository_name=required_repository_name,
                                                                  repository_owner=required_repository_owner,
                                                                  repository_changeset_revision=required_repository_changeset_revision,
                                                                  tool_dependency_type='package',
                                                                  tool_dependency_name=package_name,
                                                                  tool_dependency_version=package_version )
        # Define this dependent repository's tool dependency installation directory that will contain the env.sh file with a path to the
        # required repository's installed tool dependency package.
        dependent_install_dir = \
            tool_dependency_util.get_tool_dependency_install_dir( app=app,
                                                                  repository_name=tool_shed_repository.name,
                                                                  repository_owner=tool_shed_repository.owner,
                                                                  repository_changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                                  tool_dependency_type='package',
                                                                  tool_dependency_name=package_name,
                                                                  tool_dependency_version=package_version )
        if os.path.exists( dependent_install_dir ):
            # The install manager handles tool migration stages and the sync_database_with_file_system() method handles two
            # scenarios: (1) where a Galaxy file system environment related to installed tool shed repositories and tool dependencies
            # has somehow (over time )gotten out of sync with the Galaxy database tables associated with these installed items, and
            # (2) the Tool Shed's install and test framework which installs repositories in 2 stages, those of type
            # tool_dependency_definition followed by those containing valid tools and tool functional test components.  Neither of
            # these scenarios apply when the install manager is running.
            if from_install_manager:
                can_install_tool_dependency = True
            else:
                # Notice that we'll throw away the following tool_dependency if it can be installed.
                tool_dependency, can_install_tool_dependency = \
                    tool_dependency_util.sync_database_with_file_system( app,
                                                                         tool_shed_repository,
                                                                         package_name,
                                                                         package_version,
                                                                         dependent_install_dir,
                                                                         tool_dependency_type='package' )
                if not can_install_tool_dependency:
                    log.debug( "Tool dependency %s version %s cannot be installed (it was probably previously installed), " % \
                        ( str( tool_dependency.name, str( tool_dependency.version ) ) ) )
                    log.debug( "so appending it to the list of handled tool dependencies." )
                    handled_tool_dependencies.append( tool_dependency )
        else:
            can_install_tool_dependency = True
        if can_install_tool_dependency:
            # Set this dependent repository's tool dependency env.sh file with a path to the required repository's installed tool dependency package.
            # We can get everything we need from the discovered installed required_repository.
            if required_repository.is_deactivated_or_installed:
                if not os.path.exists( required_repository_package_install_dir ):
                    print 'Missing required tool dependency directory %s' % str( required_repository_package_install_dir )
                repo_files_dir = required_repository.repo_files_directory( app )
                tool_dependencies_config = get_absolute_path_to_file_in_repository( repo_files_dir, 'tool_dependencies.xml' )
                if tool_dependencies_config:
                    config_to_use = tool_dependencies_config
                else:
                    message = "Unable to locate required tool_dependencies.xml file for revision %s of installed repository %s owned by %s." % \
                        ( str( required_repository.changeset_revision ), str( required_repository.name ), str( required_repository.owner ) )
                    raise Exception( message )
            else:
                # Make a call to the tool shed to get the changeset revision to which the current value of required_repository_changeset_revision
                # should be updated if it's not current.
                text = get_updated_changeset_revisions_from_tool_shed( app=app,
                                                                       tool_shed_url=tool_shed,
                                                                       name=required_repository_name,
                                                                       owner=required_repository_owner,
                                                                       changeset_revision=required_repository_changeset_revision )
                if text:
                    updated_changeset_revisions = listify( text )
                    # The list of changeset revisions is in reverse order, so the newest will be first.
                    required_repository_changeset_revision = updated_changeset_revisions[ 0 ]
                # Make a call to the tool shed to get the required repository's tool_dependencies.xml file.
                tmp_filename = create_temporary_tool_dependencies_config( app,
                                                                          tool_shed,
                                                                          required_repository_name,
                                                                          required_repository_owner,
                                                                          required_repository_changeset_revision )
                config_to_use = tmp_filename
            handled_tool_dependencies = create_tool_dependency_with_initialized_env_sh_file( app=app,
                                                                                            dependent_install_dir=dependent_install_dir,
                                                                                            tool_shed_repository=tool_shed_repository,
                                                                                            required_repository=required_repository,
                                                                                            package_name=package_name,
                                                                                            package_version=package_version,
                                                                                            tool_dependencies_config=config_to_use )
            suc.remove_file( tmp_filename )
    else:
        message = "Unable to locate required tool shed repository named %s owned by %s with revision %s." % \
            ( str( required_repository_name ), str( required_repository_owner ), str( default_required_repository_changeset_revision ) )
        raise Exception( message )
    return handled_tool_dependencies

def install_and_build_package_via_fabric( app, tool_dependency, actions_dict ):
    sa_session = app.install_model.context
    try:
        # There is currently only one fabric method.
        tool_dependency = fabric_util.install_and_build_package( app, tool_dependency, actions_dict )
    except Exception, e:
        log.exception( 'Error installing tool dependency %s version %s.', str( tool_dependency.name ), str( tool_dependency.version ) )
        # Since there was an installation error, update the tool dependency status to Error. The remove_installation_path option must
        # be left False here.
        error_message = '%s\n%s' % ( td_common_util.format_traceback(), str( e ) )
        tool_dependency = tool_dependency_util.handle_tool_dependency_installation_error( app, 
                                                                                          tool_dependency, 
                                                                                          error_message, 
                                                                                          remove_installation_path=False )
    tool_dependency = tool_dependency_util.mark_tool_dependency_installed( app, tool_dependency )
    return tool_dependency

def install_package( app, elem, tool_shed_repository, tool_dependencies=None, from_install_manager=False ):
    # The value of tool_dependencies is a partial or full list of ToolDependency records associated with the tool_shed_repository.
    sa_session = app.install_model.context
    tool_dependency = None
    # The value of package_name should match the value of the "package" type in the tool config's <requirements> tag set, but it's not required.
    package_name = elem.get( 'name', None )
    package_version = elem.get( 'version', None )
    if tool_dependencies and package_name and package_version:
        for package_elem in elem:
            if package_elem.tag == 'repository':
                # We have a complex repository dependency definition.
                rd_tool_dependencies = handle_complex_repository_dependency_for_package( app,
                                                                                         package_elem,
                                                                                         package_name,
                                                                                         package_version,
                                                                                         tool_shed_repository,
                                                                                         from_install_manager=from_install_manager )
                for rd_tool_dependency in rd_tool_dependencies:
                    if rd_tool_dependency.status == app.install_model.ToolDependency.installation_status.ERROR:
                        # We'll log the error here, but continue installing packages since some may not require this dependency.
                        print "Error installing tool dependency for required repository: %s" % str( rd_tool_dependency.error_message )
            elif package_elem.tag == 'install':
                # <install version="1.0">
                # Get the installation directory for tool dependencies that will be installed for the received tool_shed_repository.
                install_dir = tool_dependency_util.get_tool_dependency_install_dir( app=app,
                                                                                    repository_name=tool_shed_repository.name,
                                                                                    repository_owner=tool_shed_repository.owner,
                                                                                    repository_changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                                                    tool_dependency_type='package',
                                                                                    tool_dependency_name=package_name,
                                                                                    tool_dependency_version=package_version )
                if os.path.exists( install_dir ):
                    # The install manager handles tool migration stages and the sync_database_with_file_system() method handles two
                    # scenarios: (1) where a Galaxy file system environment related to installed tool shed repositories and tool dependencies
                    # has somehow (over time )gotten out of sync with the Galaxy database tables associated with these installed items, and
                    # (2) the Tool Shed's install and test framework which installs repositories in 2 stages, those of type
                    # tool_dependency_definition followed by those containing valid tools and tool functional test components.  Neither of
                    # these scenarios apply when the install manager is running.
                    if from_install_manager:
                        can_install_tool_dependency = True
                    else:
                        # Notice that we'll throw away the following tool_dependency if it can be installed.
                        tool_dependency, can_install_tool_dependency = \
                            tool_dependency_util.sync_database_with_file_system( app,
                                                                                 tool_shed_repository,
                                                                                 package_name,
                                                                                 package_version,
                                                                                 install_dir,
                                                                                 tool_dependency_type='package' )
                        if not can_install_tool_dependency:
                            log.debug( "Tool dependency %s version %s cannot be installed (it was probably previously installed), so returning it." % \
                                ( str( tool_dependency.name, str( tool_dependency.version ) ) ) )
                            return tool_dependency
                else:
                    can_install_tool_dependency = True
                if can_install_tool_dependency:
                    package_install_version = package_elem.get( 'version', '1.0' )
                    tool_dependency = tool_dependency_util.create_or_update_tool_dependency( app=app,
                                                                                             tool_shed_repository=tool_shed_repository,
                                                                                             name=package_name,
                                                                                             version=package_version,
                                                                                             type='package',
                                                                                             status=app.install_model.ToolDependency.installation_status.INSTALLING,
                                                                                             set_status=True )
                    # Get the information about the current platform in case the tool dependency definition includes tag sets for installing
                    # compiled binaries.
                    platform_info_dict = tool_dependency_util.get_platform_info_dict()
                    if package_install_version == '1.0':
                        # Handle tool dependency installation using a fabric method included in the Galaxy framework.
                        actions_elem_tuples = td_common_util.parse_package_elem( package_elem,
                                                                                 platform_info_dict=platform_info_dict,
                                                                                 include_after_install_actions=True )
                        if actions_elem_tuples:
                            # At this point we have a list of <actions> elems that are either defined within an <actions_group> tag set with <actions>
                            # sub-elements that contains os and architecture attributes filtered by the platform into which the appropriate compiled
                            # binary will be installed, or not defined within an <actions_group> tag set and not filtered.
                            binary_installed = False
                            for in_actions_group, actions_elems in actions_elem_tuples:
                                if in_actions_group:
                                    # Platform matching is only performed inside <actions_group> tag sets, os and architecture attributes are otherwise
                                    # ignored.
                                    for actions_elem in actions_elems:
                                        system = actions_elem.get( 'os' )
                                        architecture = actions_elem.get( 'architecture' )
                                        # If this <actions> element has the os and architecture attributes defined, then we only want to process until a
                                        # successful installation is achieved.
                                        if system and architecture:
                                            # If an <actions> tag has been defined that matches our current platform, and the recipe specified within
                                            # that <actions> tag has been successfully processed, skip any remaining platform-specific <actions> tags.
                                            # We cannot break out of the look here because there may be <action> tags at the end of the <actions_group>
                                            # tag set that must be processed.
                                            if binary_installed:
                                                continue
                                            # No platform-specific <actions> recipe has yet resulted in a successful installation.
                                            tool_dependency = install_via_fabric( app, 
                                                                                  tool_dependency, 
                                                                                  install_dir, 
                                                                                  package_name=package_name, 
                                                                                  actions_elem=actions_elem, 
                                                                                  action_elem=None )
                                            if tool_dependency.status == app.install_model.ToolDependency.installation_status.INSTALLED:
                                                # If an <actions> tag was found that matches the current platform, and the install_via_fabric method 
                                                # did not result in an error state, set binary_installed to True in order to skip any remaining 
                                                # platform-specific <actions> tags.
                                                binary_installed = True
                                            else:
                                                # Process the next matching <actions> tag, or any defined <actions> tags that do not contain platform
                                                # dependent recipes.
                                                log.debug( 'Error downloading binary for tool dependency %s version %s: %s' % \
                                                    ( str( package_name ), str( package_version ), str( tool_dependency.error_message ) ) )
                                        else:
                                            # If no <actions> tags have been defined that match our current platform, or none of the matching
                                            # <actions> tags resulted in a successful tool dependency status, proceed with one and only one
                                            # <actions> tag that is not defined to be platform-specific.
                                            if not binary_installed:
                                                log.debug( 'Proceeding with install and compile recipe for tool dependency %s.' % str( tool_dependency.name ) )
                                                # Make sure to reset for installation if attempt at binary installation resulted in an error.
                                                can_install = True
                                                if tool_dependency.status != app.install_model.ToolDependency.installation_status.NEVER_INSTALLED:
                                                    removed, error_message = tool_dependency_util.remove_tool_dependency( app, tool_dependency )
                                                    if not removed:
                                                        log.debug( 'Error removing old files from installation directory %s: %s' % \
                                                            ( str( tool_dependency.installation_directory( app ), str( error_message ) ) ) )
                                                        can_install = False
                                                if can_install:
                                                    tool_dependency = install_via_fabric( app, 
                                                                                          tool_dependency, 
                                                                                          install_dir, 
                                                                                          package_name=package_name, 
                                                                                          actions_elem=actions_elem, 
                                                                                          action_elem=None )
                                        # Perform any final actions that have been defined within the actions_group tag set, but outside of 
                                        # an <actions> tag, such as a set_environment entry, or a download_file or download_by_url command to
                                        # retrieve extra data for this tool dependency. Only do this if the tool dependency is not in an error
                                        # state, otherwise skip this action.
                                        if actions_elem.tag == 'action' and tool_dependency.status != app.install_model.ToolDependency.installation_status.ERROR:
                                            tool_dependency = install_via_fabric( app, 
                                                                                  tool_dependency, 
                                                                                  install_dir, 
                                                                                  package_name=package_name, 
                                                                                  actions_elem=None, 
                                                                                  action_elem=actions_elem )
                                else:
                                    # <actions> tags outside of an <actions_group> tag shall not check os or architecture, and if the attributes are
                                    # defined, they will be ignored. All <actions> tags outside of an <actions_group> tag set shall always be processed.
                                    # This is the default and original behavior of the install_package method.
                                    tool_dependency = install_via_fabric( app, 
                                                                          tool_dependency, 
                                                                          install_dir, 
                                                                          package_name=package_name, 
                                                                          actions_elem=actions_elems, 
                                                                          action_elem=None )
                                    if tool_dependency.status != app.install_model.ToolDependency.installation_status.ERROR:
                                        log.debug( 'Tool dependency %s version %s has been installed in %s.' % \
                                            ( str( package_name ), str( package_version ), str( install_dir ) ) )
                        else:
                            error_message = 'Version %s of the %s package cannot be installed because ' % ( str( package_version ), str( package_name ) )
                            error_message += 'the recipe for installing the package is missing either an &lt;actions&gt; tag set or an &lt;actions_group&gt; '
                            error_message += 'tag set.'
                            # Since there was an installation error, update the tool dependency status to Error. The remove_installation_path option must
                            # be left False here.
                            tool_dependency = tool_dependency_util.handle_tool_dependency_installation_error( app, 
                                                                                                              tool_dependency, 
                                                                                                              error_message, 
                                                                                                              remove_installation_path=False )
                            return tool_dependency
                    else:
                        raise NotImplementedError( 'Only install version 1.0 is currently supported (i.e., change your tag to be <install version="1.0">).' )
            elif package_elem.tag == 'readme':
                # Nothing to be done.
                continue
            #elif package_elem.tag == 'proprietary_fabfile':
            #    # TODO: This is not yet supported or functionally correct...
            #    # Handle tool dependency installation where the repository includes one or more proprietary fabric scripts.
            #    if not fabric_version_checked:
            #        check_fabric_version()
            #        fabric_version_checked = True
            #    fabfile_name = package_elem.get( 'name', None )
            #    proprietary_fabfile_path = os.path.abspath( os.path.join( os.path.split( tool_dependencies_config )[ 0 ], fabfile_name ) )
            #    print 'Installing tool dependencies via fabric script ', proprietary_fabfile_path
    return tool_dependency

def install_via_fabric( app, tool_dependency, install_dir, package_name=None, proprietary_fabfile_path=None, actions_elem=None, action_elem=None, **kwd ):
    """Parse a tool_dependency.xml file's <actions> tag set to gather information for the installation via fabric."""
    sa_session = app.install_model.context
    if not os.path.exists( install_dir ):
        os.makedirs( install_dir )
    actions_dict = dict( install_dir=install_dir )
    if package_name:
        actions_dict[ 'package_name' ] = package_name
    actions = []
    all_env_shell_file_paths = []
    env_var_dicts = []
    if actions_elem is not None:
        elems = actions_elem
        if elems.get( 'os' ) is not None and elems.get( 'architecture' ) is not None:
            is_binary_download = True
        else:
            is_binary_download = False
    elif action_elem is not None:
        # We were provided with a single <action> element to perform certain actions after a platform-specific tarball was downloaded.
        elems = [ action_elem ]
    else:
        elems = []
    for action_elem in elems:
        # Make sure to skip all comments, since they are now included in the XML tree.
        if action_elem.tag != 'action':
            continue
        action_dict = {}
        action_type = action_elem.get( 'type', 'shell_command' )
        if action_type == 'download_binary':
            platform_info_dict = tool_dependency_util.get_platform_info_dict()
            platform_info_dict[ 'name' ] = tool_dependency.name
            platform_info_dict[ 'version' ] = tool_dependency.version
            url_template_elems = action_elem.findall( 'url_template' )
            # Check if there are multiple url_template elements, each with attrib entries for a specific platform.
            if len( url_template_elems ) > 1:
                # <base_url os="darwin" extract="false">http://hgdownload.cse.ucsc.edu/admin/exe/macOSX.${architecture}/faToTwoBit</base_url>
                # This method returns the url_elem that best matches the current platform as received from os.uname().
                # Currently checked attributes are os and architecture.
                # These correspond to the values sysname and processor from the Python documentation for os.uname().
                url_template_elem = tool_dependency_util.get_download_url_for_platform( url_template_elems, platform_info_dict )
            else:
                url_template_elem = url_template_elems[ 0 ]
            action_dict[ 'url' ] = Template( url_template_elem.text ).safe_substitute( platform_info_dict )
            action_dict[ 'target_directory' ] = action_elem.get( 'target_directory', None )
        elif action_type == 'shell_command':
            # <action type="shell_command">make</action>
            action_elem_text = td_common_util.evaluate_template( action_elem.text, install_dir )
            if action_elem_text:
                action_dict[ 'command' ] = action_elem_text
            else:
                continue
        elif action_type == 'template_command':
            # Default to Cheetah as it's the first template language supported.
            language = action_elem.get( 'language', 'cheetah' ).lower()
            if language == 'cheetah':
                # Cheetah template syntax.
                # <action type="template_command" language="cheetah">
                #     #if env.PATH:
                #         make
                #     #end if
                # </action>
                action_elem_text = action_elem.text.strip()
                if action_elem_text:
                    action_dict[ 'language' ] = language
                    action_dict[ 'command' ] = action_elem_text
                else:
                    continue
            else:
                log.debug( "Unsupported template language '%s'. Not proceeding." % str( language ) )
                raise Exception( "Unsupported template language '%s' in tool dependency definition." % str( language ) )
        elif action_type == 'download_by_url':
            # <action type="download_by_url">http://sourceforge.net/projects/samtools/files/samtools/0.1.18/samtools-0.1.18.tar.bz2</action>
            if is_binary_download:
                action_dict[ 'is_binary' ] = True
            if action_elem.text:
                action_dict[ 'url' ] = action_elem.text
                target_filename = action_elem.get( 'target_filename', None )
                if target_filename:
                    action_dict[ 'target_filename' ] = target_filename
            else:
                continue
        elif action_type == 'download_file':
            # <action type="download_file">http://effectors.org/download/version/TTSS_GUI-1.0.1.jar</action>
            if action_elem.text:
                action_dict[ 'url' ] = action_elem.text
                target_filename = action_elem.get( 'target_filename', None )
                if target_filename:
                    action_dict[ 'target_filename' ] = target_filename
                action_dict[ 'extract' ] = asbool( action_elem.get( 'extract', False ) )
            else:
                continue
        elif action_type == 'make_directory':
            # <action type="make_directory">$INSTALL_DIR/lib/python</action>
            if action_elem.text:
                action_dict[ 'full_path' ] = td_common_util.evaluate_template( action_elem.text, install_dir )
            else:
                continue
        elif action_type == 'change_directory':
            # <action type="change_directory">PHYLIP-3.6b</action>
            if action_elem.text:
                action_dict[ 'directory' ] = action_elem.text
            else:
                continue
        elif action_type == 'move_directory_files':
            # <action type="move_directory_files">
            #     <source_directory>bin</source_directory>
            #     <destination_directory>$INSTALL_DIR/bin</destination_directory>
            # </action>
            for move_elem in action_elem:
                move_elem_text = td_common_util.evaluate_template( move_elem.text, install_dir )
                if move_elem_text:
                    action_dict[ move_elem.tag ] = move_elem_text
        elif action_type == 'move_file':
            # <action type="move_file" rename_to="new_file_name">
            #     <source>misc/some_file</source>
            #     <destination>$INSTALL_DIR/bin</destination>
            # </action>
            action_dict[ 'source' ] = td_common_util.evaluate_template( action_elem.find( 'source' ).text, install_dir )
            action_dict[ 'destination' ] = td_common_util.evaluate_template( action_elem.find( 'destination' ).text, install_dir )
            action_dict[ 'rename_to' ] = action_elem.get( 'rename_to' )
        elif action_type == 'set_environment':
            # <action type="set_environment">
            #     <environment_variable name="PYTHONPATH" action="append_to">$INSTALL_DIR/lib/python</environment_variable>
            #     <environment_variable name="PATH" action="prepend_to">$INSTALL_DIR/bin</environment_variable>
            # </action>
            for env_elem in action_elem:
                if env_elem.tag == 'environment_variable':
                    env_var_dict = td_common_util.create_env_var_dict( env_elem, tool_dependency_install_dir=install_dir )
                    if env_var_dict:
                        env_var_dicts.append( env_var_dict )
            if env_var_dicts:
                # The last child of an <action type="set_environment"> might be a comment, so manually set it to be 'environment_variable'.
                action_dict[ 'environment_variable' ] = env_var_dicts
            else:
                continue
        elif action_type == 'set_environment_for_install':
            # <action type="set_environment_for_install">
            #    <repository toolshed="http://localhost:9009/" name="package_numpy_1_7" owner="test" changeset_revision="c84c6a8be056">
            #        <package name="numpy" version="1.7.1" />
            #    </repository>
            # </action>
            # This action type allows for defining an environment that will properly compile a tool dependency.  Currently, tag set definitions like
            # that above are supported, but in the future other approaches to setting environment variables or other environment attributes can be
            # supported.  The above tag set will result in the installed and compiled numpy version 1.7.1 binary to be used when compiling the current
            # tool dependency package.  See the package_matplotlib_1_2 repository in the test tool shed for a real-world example.
            for env_elem in action_elem:
                if env_elem.tag == 'repository':
                    env_shell_file_paths = td_common_util.get_env_shell_file_paths( app, env_elem )
                    if env_shell_file_paths:
                        all_env_shell_file_paths.extend( env_shell_file_paths )
            if all_env_shell_file_paths:
                action_dict[ 'env_shell_file_paths' ] = all_env_shell_file_paths
            else:
                continue
        elif action_type == 'setup_virtualenv':
            # <action type="setup_virtualenv" />
            ## Install requirements from file requirements.txt of downloaded bundle - or -
            # <action type="setup_virtualenv">tools/requirements.txt</action>
            ## Install requirements from specified file from downloaded bundle -or -
            # <action type="setup_virtualenv">pyyaml==3.2.0
            # lxml==2.3.0</action>
            ## Manually specify contents of requirements.txt file to create dynamically.
            action_dict[ 'requirements' ] = td_common_util.evaluate_template( action_elem.text or 'requirements.txt', install_dir )
        elif action_type == 'autoconf':
            # Handle configure, make and make install allow providing configuration options
            if action_elem.text:
                configure_opts = td_common_util.evaluate_template( action_elem.text, install_dir )
                action_dict[ 'configure_opts' ] = configure_opts
        elif action_type == 'setup_r_environment':
            # setup an R environment.
            # <action type="setup_r_environment">
            #       <repository name="package_r_3_0_1" owner="bgruening">
            #           <package name="R" version="3.0.1" />
            #       </repository>
            #       <!-- allow installing an R packages -->
            #       <package>https://github.com/bgruening/download_store/raw/master/DESeq2-1_0_18/BiocGenerics_0.6.0.tar.gz</package>
            # </action>
            # Discover all child repository dependency tags and define the path to an env.sh file associated with each repository.
            # This will potentially update the value of the 'env_shell_file_paths' entry in action_dict.
            action_dict = td_common_util.get_env_shell_file_paths_from_setup_environment_elem( app, all_env_shell_file_paths, action_elem, action_dict )
            r_packages = list()
            for env_elem in action_elem:
                if env_elem.tag == 'package':
                    r_packages.append( env_elem.text.strip() )
            if r_packages:
                action_dict[ 'r_packages' ] = r_packages
            else:
                continue
        elif action_type == 'setup_ruby_environment':
            # setup a Ruby environment.
            # <action type="setup_ruby_environment">
            #       <repository name="package_ruby_2_0" owner="bgruening">
            #           <package name="ruby" version="2.0" />
            #       </repository>
            #       <!-- allow downloading and installing an Ruby package from http://rubygems.org/ -->
            #       <package>protk</package>
            #       <package>protk=1.2.4</package>
            #       <package>http://url-to-some-gem-file.de/protk.gem</package>
            # </action>
            # Discover all child repository dependency tags and define the path to an env.sh file associated with each repository.
            # This will potentially update the value of the 'env_shell_file_paths' entry in action_dict.
            action_dict = td_common_util.get_env_shell_file_paths_from_setup_environment_elem( app, all_env_shell_file_paths, action_elem, action_dict )
            ruby_package_tups = []
            for env_elem in action_elem:
                if env_elem.tag == 'package':
                    #A valid gem definition can be:
                    #    protk=1.2.4
                    #    protk
                    #    ftp://ftp.gruening.de/protk.gem
                    gem_token = env_elem.text.strip().split( '=' )
                    if len( gem_token ) == 2:
                        # version string
                        gem_name = gem_token[ 0 ]
                        gem_version = gem_token[ 1 ]
                        ruby_package_tups.append( ( gem_name, gem_version ) )
                    else:
                        # gem name for rubygems.org without version number
                        gem = env_elem.text.strip()
                        ruby_package_tups.append( ( gem, None ) )
            if ruby_package_tups:
                action_dict[ 'ruby_package_tups' ] = ruby_package_tups
            else:
                continue
        elif action_type == 'setup_perl_environment':
            # setup a Perl environment.
            # <action type="setup_perl_environment">
            #       <repository name="package_perl_5_18" owner="bgruening">
            #           <package name="perl" version="5.18.1" />
            #       </repository>
            #       <!-- allow downloading and installing an Perl package from cpan.org-->
            #       <package>XML::Parser</package>
            #       <package>http://search.cpan.org/CPAN/authors/id/C/CJ/CJFIELDS/BioPerl-1.6.922.tar.gz</package>
            # </action>
            # Discover all child repository dependency tags and define the path to an env.sh file associated with each repository.
            # This will potentially update the value of the 'env_shell_file_paths' entry in action_dict.
            action_dict = td_common_util.get_env_shell_file_paths_from_setup_environment_elem( app, all_env_shell_file_paths, action_elem, action_dict )
            perl_packages = []
            for env_elem in action_elem:
                if env_elem.tag == 'package':
                    # A valid package definition can be:
                    #    XML::Parser
                    #     http://search.cpan.org/CPAN/authors/id/C/CJ/CJFIELDS/BioPerl-1.6.922.tar.gz
                    # Unfortunately CPAN does not support versioning, so if you want real reproducibility you need to specify
                    # the tarball path and the right order of different tarballs manually.
                    perl_packages.append( env_elem.text.strip() )
            if perl_packages:
                action_dict[ 'perl_packages' ] = perl_packages
            else:
                continue
        elif action_type == 'make_install':
            # make; make install; allow providing make options
            if action_elem.text:
                make_opts = td_common_util.evaluate_template( action_elem.text, install_dir )
                action_dict[ 'make_opts' ] = make_opts
        elif action_type == 'chmod':
            # Change the read, write, and execute bits on a file.
            # <action type="chmod">
            #   <file mode="750">$INSTALL_DIR/bin/faToTwoBit</file>
            # </action>
            file_elems = action_elem.findall( 'file' )
            chmod_actions = []
            # A unix octal mode is the sum of the following values:
            # Owner:
            # 400 Read    200 Write    100 Execute
            # Group:
            # 040 Read    020 Write    010 Execute
            # World:
            # 004 Read    002 Write    001 Execute
            for file_elem in file_elems:
                # So by the above table, owner read/write/execute and group read permission would be 740.
                # Python's os.chmod uses base 10 modes, convert received unix-style octal modes to base 10.
                received_mode = int( file_elem.get( 'mode', 600 ), base=8 )
                # For added security, ensure that the setuid and setgid bits are not set.
                mode = received_mode & ~( stat.S_ISUID | stat.S_ISGID )
                file = td_common_util.evaluate_template( file_elem.text, install_dir )
                chmod_tuple = ( file, mode )
                chmod_actions.append( chmod_tuple )
            action_dict[ 'change_modes' ] = chmod_actions
        else:
            log.debug( "Unsupported action type '%s'. Not proceeding." % str( action_type ) )
            raise Exception( "Unsupported action type '%s' in tool dependency definition." % str( action_type ) )
        action_tuple = ( action_type, action_dict )
        if action_type == 'set_environment':
            if action_tuple not in actions:
                actions.append( action_tuple )
        else:
            actions.append( action_tuple )
    if actions:
        actions_dict[ 'actions' ] = actions
    if proprietary_fabfile_path:
        # TODO: this is not yet supported or functional, but when it is handle it using the fabric api.
        # run_proprietary_fabric_method( app, elem, proprietary_fabfile_path, install_dir, package_name=package_name )
        raise Exception( 'Tool dependency installation using proprietary fabric scripts is not yet supported.' )
    else:
        tool_dependency = install_and_build_package_via_fabric( app, tool_dependency, actions_dict )
    return tool_dependency

def run_proprietary_fabric_method( app, elem, proprietary_fabfile_path, install_dir, package_name=None, **kwd ):
    """
    TODO: Handle this using the fabric api.
    Parse a tool_dependency.xml file's fabfile <method> tag set to build the method parameters and execute the method.
    """
    if not os.path.exists( install_dir ):
        os.makedirs( install_dir )
    # Default value for env_dependency_path.
    env_dependency_path = install_dir
    method_name = elem.get( 'name', None )
    params_str = ''
    actions = []
    for param_elem in elem:
        param_name = param_elem.get( 'name' )
        if param_name:
            if param_name == 'actions':
                for action_elem in param_elem:
                    actions.append( action_elem.text.replace( '$INSTALL_DIR', install_dir ) )
                if actions:
                    params_str += 'actions=%s,' % encoding_util.tool_shed_encode( encoding_util.encoding_sep.join( actions ) )
            else:
                if param_elem.text:
                    param_value = encoding_util.tool_shed_encode( param_elem.text )
                    params_str += '%s=%s,' % ( param_name, param_value )
    if package_name:
        params_str += 'package_name=%s' % package_name
    else:
        params_str = params_str.rstrip( ',' )
    try:
        cmd = 'fab -f %s %s:%s' % ( proprietary_fabfile_path, method_name, params_str )
        returncode, message = run_subprocess( app, cmd )
    except Exception, e:
        return "Exception executing fabric script %s: %s.  " % ( str( proprietary_fabfile_path ), str( e ) )
    if returncode:
        return message
    handle_environment_settings( app, tool_dependency, install_dir, cmd )

def run_subprocess( app, cmd ):
    env = os.environ
    PYTHONPATH = env.get( 'PYTHONPATH', '' )
    if PYTHONPATH:
        env[ 'PYTHONPATH' ] = '%s:%s' % ( os.path.abspath( os.path.join( app.config.root, 'lib' ) ), PYTHONPATH )
    else:
        env[ 'PYTHONPATH' ] = os.path.abspath( os.path.join( app.config.root, 'lib' ) )
    message = ''
    tmp_name = tempfile.NamedTemporaryFile( prefix="tmp-toolshed-rs" ).name
    tmp_stderr = open( tmp_name, 'wb' )
    proc = subprocess.Popen( cmd, shell=True, env=env, stderr=tmp_stderr.fileno() )
    returncode = proc.wait()
    tmp_stderr.close()
    if returncode:
        tmp_stderr = open( tmp_name, 'rb' )
        message = '%s\n' % str( tmp_stderr.read() )
        tmp_stderr.close()
    suc.remove_file( tmp_name )
    return returncode, message

def set_environment( app, elem, tool_shed_repository, attr_tups_of_dependencies_for_install ):
    """
    Create a ToolDependency to set an environment variable.  This is different from the process used to set an environment variable that is associated
    with a package.  An example entry in a tool_dependencies.xml file is::

        <set_environment version="1.0">
            <environment_variable name="R_SCRIPT_PATH" action="set_to">$REPOSITORY_INSTALL_DIR</environment_variable>
        </set_environment>
    """
    # TODO: Add support for a repository dependency definition within this tool dependency type's tag set.  This should look something like
    # the following.  See the implementation of support for this in the tool dependency package type's method above.
    # <set_environment version="1.0">
    #    <repository toolshed="<tool shed>" name="<repository name>" owner="<repository owner>" changeset_revision="<changeset revision>" />
    # </set_environment>
    sa_session = app.install_model.context
    tool_dependency = None
    env_var_version = elem.get( 'version', '1.0' )
    for env_var_elem in elem:
        # Althoug we're in a loop here, this method will always return only a single ToolDependency or None.
        env_var_name = env_var_elem.get( 'name', None )
        # The value of env_var_name must match the text value of at least 1 <requirement> tag in the tool config's <requirements> tag set whose
        # "type" attribute is "set_environment" (e.g., <requirement type="set_environment">R_SCRIPT_PATH</requirement>).
        env_var_action = env_var_elem.get( 'action', None )
        if env_var_name and env_var_action:
            # Tool dependencies of type "set_environmnet" always have the version attribute set to None.
            attr_tup = ( env_var_name, None, 'set_environment' )
            if attr_tup in attr_tups_of_dependencies_for_install:
                install_dir = tool_dependency_util.get_tool_dependency_install_dir( app=app,
                                                                                    repository_name=tool_shed_repository.name,
                                                                                    repository_owner=tool_shed_repository.owner,
                                                                                    repository_changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                                                    tool_dependency_type='set_environment',
                                                                                    tool_dependency_name=env_var_name,
                                                                                    tool_dependency_version=None )
                tool_shed_repository_install_dir = get_tool_shed_repository_install_dir( app, tool_shed_repository )
                env_var_dict = td_common_util.create_env_var_dict( env_var_elem, tool_shed_repository_install_dir=tool_shed_repository_install_dir )
                if env_var_dict:
                    if not os.path.exists( install_dir ):
                        os.makedirs( install_dir )
                    tool_dependency = tool_dependency_util.create_or_update_tool_dependency( app=app,
                                                                                             tool_shed_repository=tool_shed_repository,
                                                                                             name=env_var_name,
                                                                                             version=None,
                                                                                             type='set_environment',
                                                                                             status=app.install_model.ToolDependency.installation_status.INSTALLING,
                                                                                             set_status=True )
                    if env_var_version == '1.0':
                        # Create this tool dependency's env.sh file.
                        env_file_builder = fabric_util.EnvFileBuilder( install_dir )
                        return_code = env_file_builder.append_line( skip_if_contained=True, make_executable=True, **env_var_dict )
                        if return_code:
                            error_message = 'Error creating env.sh file for tool dependency %s, return_code: %s' % \
                                ( str( tool_dependency.name ), str( return_code ) )
                            log.debug( error_message )
                            tool_dependency = tool_dependency_util.set_tool_dependency_attributes( app,
                                                                                                   tool_dependency=tool_dependency,
                                                                                                   status=app.install_model.ToolDependency.installation_status.ERROR,
                                                                                                   error_message=error_message,
                                                                                                   remove_from_disk=False )
                        else:
                            if tool_dependency.status not in [ app.install_model.ToolDependency.installation_status.ERROR,
                                                              app.install_model.ToolDependency.installation_status.INSTALLED ]:
                                tool_dependency = tool_dependency_util.set_tool_dependency_attributes( app,
                                                                                                       tool_dependency=tool_dependency,
                                                                                                       status=app.install_model.ToolDependency.installation_status.INSTALLED,
                                                                                                       error_message=None,
                                                                                                       remove_from_disk=False )
                                log.debug( 'Environment variable %s set in %s for tool dependency %s.' % \
                                    ( str( env_var_name ), str( install_dir ), str( tool_dependency.name ) ) )
                    else:
                        error_message = 'Only set_environment version 1.0 is currently supported (i.e., change your tag to be <set_environment version="1.0">).'
                        tool_dependency = tool_dependency_util.set_tool_dependency_attributes( app,
                                                                                               tool_dependency=tool_dependency,
                                                                                               status=app.install_model.ToolDependency.installation_status.ERROR,
                                                                                               error_message=error_message,
                                                                                               remove_from_disk=False )
    return tool_dependency

def strip_path( fpath ):
    if not fpath:
        return fpath
    try:
        file_path, file_name = os.path.split( fpath )
    except:
        file_name = fpath
    return file_name

def url_join( *args ):
    parts = []
    for arg in args:
        parts.append( arg.strip( '/' ) )
    return '/'.join( parts )
