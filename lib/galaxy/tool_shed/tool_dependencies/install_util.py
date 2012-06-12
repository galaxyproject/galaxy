import sys, os, subprocess, tempfile
from common_util import *
from fabric_util import *
from galaxy.tool_shed.encoding_util import *
from galaxy.model.orm import *

from galaxy import eggs
import pkg_resources

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree, ElementInclude
from elementtree.ElementTree import Element, SubElement

def create_or_update_tool_dependency( app, tool_shed_repository, changeset_revision, name, version, type ):
    """
    This method is called from Galaxy (never the tool shed) when a new tool_shed_repository is being installed or when an ininstalled repository is
    being reinstalled.
    """
    # First see if a tool_dependency record exists for the received changeset_revision.
    sa_session = app.model.context.current
    tool_dependency = get_tool_dependency_by_shed_changeset_revision( app, tool_shed_repository, name, version, type, changeset_revision )
    if tool_dependency:
        tool_dependency.uninstalled = False
    else:
        # Check the tool_shed_repository's set of tool_depnedency records for any that are marked uninstalled.  If one is found, set uninstalled to
        # False and update the value of installed_changeset_revision.
        found = False
        for tool_dependency in tool_shed_repository.tool_dependencies:
            if tool_dependency.name == name and tool_dependency.version == version and tool_dependency.type == type and tool_dependency.uninstalled:
                found = True
                tool_dependency.uninstalled = False
                tool_dependency.installed_changeset_revision = changeset_revision
                break
        if not found:
            # Create a new tool_dependency record for the tool_shed_repository.
            tool_dependency = app.model.ToolDependency( tool_shed_repository_id=tool_shed_repository.id,
                                                        installed_changeset_revision=changeset_revision,
                                                        name=name,
                                                        version=version,
                                                        type=type )
    sa_session.add( tool_dependency )
    sa_session.flush()
    return tool_dependency
def get_install_dir( app, repository, installed_changeset_revision, package_name, package_version ):
    return os.path.abspath( os.path.join( app.config.tool_dependency_dir,
                                          package_name,
                                          package_version,
                                          repository.owner,
                                          repository.name,
                                          installed_changeset_revision ) )
def get_tool_dependency_by_shed_changeset_revision( app, repository, dependency_name, dependency_version, dependency_type, changeset_revision ):
    sa_session = app.model.context.current
    return sa_session.query( app.model.ToolDependency ) \
                     .filter( and_( app.model.ToolDependency.table.c.tool_shed_repository_id == repository.id,
                                    app.model.ToolDependency.table.c.name == dependency_name,
                                    app.model.ToolDependency.table.c.version == dependency_version,
                                    app.model.ToolDependency.table.c.type == dependency_type,
                                    app.model.ToolDependency.table.c.installed_changeset_revision == changeset_revision ) ) \
                     .first()
def install_package( app, elem, tool_shed_repository, installed_changeset_revision ):
    # The value of package_name should match the value of the "package" type in the tool config's <requirements> tag set, but it's not required.
    message = ''
    package_name = elem.get( 'name', None )
    package_version = elem.get( 'version', None )
    if package_name and package_version:
        install_dir = get_install_dir( app, tool_shed_repository, installed_changeset_revision, package_name, package_version )
        if not_installed( install_dir ):
            for package_elem in elem:
                if package_elem.tag == 'proprietary_fabfile':
                    # TODO: This is not yet working...
                    # Handle tool dependency installation where the repository includes one or more proprietary fabric scripts.
                    if not fabric_version_checked:
                        check_fabric_version()
                        fabric_version_checked = True
                    fabfile_name = package_elem.get( 'name', None )
                    fabfile_path = os.path.abspath( os.path.join( os.path.split( tool_dependencies_config )[ 0 ], fabfile_name ) )
                    print 'Installing tool dependencies via fabric script ', fabfile_path
                elif package_elem.tag == 'fabfile':
                    # Handle tool dependency installation using a fabric script provided by Galaxy.  Example tag set definition:
                    fabfile_path = None
                for method_elem in package_elem.findall( 'method' ):
                    error_message = run_fabric_method( app,
                                                       method_elem,
                                                       fabfile_path,
                                                       app.config.tool_dependency_dir,
                                                       install_dir,
                                                       package_name=package_name )
                    if error_message:
                        message += '%s' % error_message
                    else:
                        tool_dependency = create_or_update_tool_dependency( app,
                                                                            tool_shed_repository,
                                                                            installed_changeset_revision,
                                                                            name=package_name,
                                                                            version=package_version,
                                                                            type='package' )
                        print package_name, 'version', package_version, 'installed in', install_dir
        else:
            print '\nSkipping installation of tool dependency', package_name, 'version', package_version, 'since it is installed in', install_dir, '\n'
    return message
def not_installed( install_dir ):
    # TODO: try executing a binary or something in addition to just seeing if the install_dir exists.
    return not os.path.exists( install_dir )
def run_fabric_method( app, elem, fabfile_path, tool_dependency_dir, install_dir, package_name=None, **kwd ):
    """Parse a tool_dependency.xml file's fabfile <method> tag set to build the method parameters and execute the method."""
    if not os.path.exists( install_dir ):
        os.makedirs( install_dir )
    method_name = elem.get( 'name', None )
    params_dict = dict( install_dir=install_dir )
    build_commands = []
    for param_elem in elem:
        param_name = param_elem.get( 'name' )
        if param_name:
            if param_name == 'build_commands':
                for build_command_elem in param_elem:
                    build_command_dict = {}
                    build_command_name = build_command_elem.get( 'name' )
                    if build_command_name:
                        if build_command_name in MOVE_BUILD_COMMAND_NAMES:
                            build_command_key = build_command_name
                            for move_elem in build_command_elem:
                                move_elem_text = move_elem.text.replace( '$INSTALL_DIR', install_dir )
                                if move_elem_text:
                                    build_command_dict[ move_elem.tag ] = move_elem_text
                        elif build_command_elem.text:
                            build_command_key = '%sv^v^v%s' % ( build_command_name, build_command_elem.text )
                        else:
                            continue
                    else:
                        build_command_key = build_command_elem.text.replace( '$INSTALL_DIR', install_dir )
                        if not build_command_key:
                            continue
                    build_commands.append( ( build_command_key, build_command_dict ) )
                if build_commands:
                    params_dict[ 'build_commands' ] = build_commands
            else:
                if param_elem.text:
                    params_dict[ param_name ] = param_elem.text
    if package_name:
        params_dict[ 'package_name' ] = package_name
    if fabfile_path:
        # TODO: Handle this using the fabric api.
        # run_proprietary_fabric_method( app, elem, fabfile_path, tool_dependency_dir, install_dir, package_name=package_name )
        return 'Tool dependency installation using proprietary fabric scripts is not yet supported.  '
    else:
        # There is currently only 1 fabric method, install_and_build_package().
        try:
            message = install_and_build_package( params_dict )
            if message:
                return message
        except Exception, e:
            return '%s.  ' % str( e )
        try:
            message = handle_post_build_processing( tool_dependency_dir, install_dir, package_name=package_name )
            if message:
                return message
        except:
            return '%s.  ' % str( e )
        return ''
def run_proprietary_fabric_method( app, elem, fabfile_path, tool_dependency_dir, install_dir, package_name=None, **kwd ):
    """
    TODO: Handle this using the fabric api.
    Parse a tool_dependency.xml file's fabfile <method> tag set to build the method parameters and execute the method.
    """
    if not os.path.exists( install_dir ):
        os.makedirs( install_dir )
    method_name = elem.get( 'name', None )
    params_str = ''
    build_commands = []
    for param_elem in elem:
        param_name = param_elem.get( 'name' )
        if param_name:
            if param_name == 'build_commands':
                for build_command_elem in param_elem:
                    build_commands.append( build_command_elem.text.replace( '$INSTALL_DIR', install_dir ) )
                if build_commands:
                    params_str += 'build_commands=%s,' % tool_shed_encode( encoding_sep.join( build_commands ) )
            else:
                if param_elem.text:
                    param_value = tool_shed_encode( param_elem.text )
                    params_str += '%s=%s,' % ( param_name, param_value )
    if package_name:
        params_str += 'package_name=%s' % package_name
    else:
        params_str = params_str.rstrip( ',' )
    try:
        cmd = 'fab -f %s %s:%s' % ( fabfile_path, method_name, params_str )
        returncode, message = run_subprocess( app, cmd )
    except Exception, e:
        return "Exception executing fabric script %s: %s.  " % ( str( fabfile_path ), str( e ) )
    if returncode:
        return message    
    message = handle_post_build_processing( tool_dependency_dir, install_dir, package_name=package_name )
    if message:
        return message
    else:
        return ''
def run_subprocess( app, cmd ):
    env = os.environ
    PYTHONPATH = env.get( 'PYTHONPATH', '' )
    if PYTHONPATH:
        env[ 'PYTHONPATH' ] = '%s:%s' % ( os.path.abspath( os.path.join( app.config.root, 'lib' ) ), PYTHONPATH )
    else:
        env[ 'PYTHONPATH' ] = os.path.abspath( os.path.join( app.config.root, 'lib' ) )
    message = ''
    tmp_name = tempfile.NamedTemporaryFile().name
    tmp_stderr = open( tmp_name, 'wb' )
    proc = subprocess.Popen( cmd, shell=True, env=env, stderr=tmp_stderr.fileno() )
    returncode = proc.wait()
    tmp_stderr.close()
    if returncode:
        tmp_stderr = open( tmp_name, 'rb' )
        message = '%s\n' % str( tmp_stderr.read() )
        tmp_stderr.close()
    return returncode, message
