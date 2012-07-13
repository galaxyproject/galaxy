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

def create_or_update_tool_dependency( app, tool_shed_repository, name, version, type, status, set_status=True ):
    # Called from Galaxy (never the tool shed) when a new repository is being installed or when an uninstalled repository is being reinstalled.
    sa_session = app.model.context.current
    # First see if an appropriate tool_dependency record exists for the received tool_shed_repository.
    tool_dependency = get_tool_dependency_by_name_version_type_repository( app, tool_shed_repository, name, version, type )
    if tool_dependency:
        if set_status:
            tool_dependency.status = status
    else:
        # Create a new tool_dependency record for the tool_shed_repository.
        tool_dependency = app.model.ToolDependency( tool_shed_repository.id, name, version, type, status )
    sa_session.add( tool_dependency )
    sa_session.flush()
    return tool_dependency
def get_tool_dependency_by_name_version_type_repository( app, repository, name, version, type ):
    sa_session = app.model.context.current
    return sa_session.query( app.model.ToolDependency ) \
                     .filter( and_( app.model.ToolDependency.table.c.tool_shed_repository_id == repository.id,
                                    app.model.ToolDependency.table.c.name == name,
                                    app.model.ToolDependency.table.c.version == version,
                                    app.model.ToolDependency.table.c.type == type ) ) \
                     .first()
def get_tool_dependency_install_dir( app, repository, package_name, package_version ):
    return os.path.abspath( os.path.join( app.config.tool_dependency_dir,
                                          package_name,
                                          package_version,
                                          repository.owner,
                                          repository.name,
                                          repository.installed_changeset_revision ) )
def install_package( app, elem, tool_shed_repository, tool_dependencies=None ):
    # The value of tool_dependencies is a partial or full list of ToolDependency records associated with the tool_shed_repository.
    sa_session = app.model.context.current
    tool_dependency = None
    # The value of package_name should match the value of the "package" type in the tool config's <requirements> tag set, but it's not required.
    package_name = elem.get( 'name', None )
    package_version = elem.get( 'version', None )
    if package_name and package_version:
        if tool_dependencies:
            install_dir = get_tool_dependency_install_dir( app, tool_shed_repository, package_name, package_version )
            if not os.path.exists( install_dir ):
                for package_elem in elem:
                    if package_elem.tag == 'install':
                        # <install version="1.0">
                        package_install_version = package_elem.get( 'version', '1.0' )
                        tool_dependency = create_or_update_tool_dependency( app,
                                                                            tool_shed_repository,
                                                                            name=package_name,
                                                                            version=package_version,
                                                                            type='package',
                                                                            status=app.model.ToolDependency.installation_status.INSTALLING,
                                                                            set_status=True )
                        if package_install_version == '1.0':
                            # Handle tool dependency installation using a fabric method included in the Galaxy framework.
                            for actions_elem in package_elem:
                                install_via_fabric( app, tool_dependency, actions_elem, install_dir, package_name=package_name )
                                sa_session.refresh( tool_dependency )
                                if tool_dependency.status != app.model.ToolDependency.installation_status.ERROR:
                                    print package_name, 'version', package_version, 'installed in', install_dir
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
            else:
                print '\nSkipping installation of tool dependency', package_name, 'version', package_version, 'since it is installed in', install_dir, '\n'
                tool_dependency = get_tool_dependency_by_name_version_type_repository( app, tool_shed_repository, package_name, package_version, 'package' )
                tool_dependency.status = app.model.ToolDependency.installation_status.INSTALLED
                sa_session.add( tool_dependency )
                sa_session.flush()
    return tool_dependency
def install_via_fabric( app, tool_dependency, actions_elem, install_dir, package_name=None, proprietary_fabfile_path=None, **kwd ):
    """Parse a tool_dependency.xml file's <actions> tag set to gather information for the installation via fabric."""
    sa_session = app.model.context.current
    if not os.path.exists( install_dir ):
        os.makedirs( install_dir )
    actions_dict = dict( install_dir=install_dir )
    if package_name:
        actions_dict[ 'package_name' ] = package_name
    actions = []
    for action_elem in actions_elem:
        action_dict = {}
        action_type = action_elem.get( 'type', 'shell_command' )
        if action_type == 'shell_command':
            # <action type="shell_command">make</action>
            action_elem_text = action_elem.text.replace( '$INSTALL_DIR', install_dir )
            if action_elem_text:
                action_dict[ 'command' ] = action_elem_text
            else:
                continue
        elif action_type == 'download_by_url':
            # <action type="download_by_url">http://sourceforge.net/projects/samtools/files/samtools/0.1.18/samtools-0.1.18.tar.bz2</action>
            if action_elem.text:
                action_dict[ 'url' ] = action_elem.text
            else:
                continue
        elif action_type in [ 'move_directory_files', 'move_file' ]:
            # <action type="move_file">
            #     <source>misc/some_file</source>
            #     <destination>$INSTALL_DIR/bin</destination>
            # </action>
            # <action type="move_directory_files">
            #     <source_directory>bin</source_directory>
            #     <destination_directory>$INSTALL_DIR/bin</destination_directory>
            # </action>
            for move_elem in action_elem:
                move_elem_text = move_elem.text.replace( '$INSTALL_DIR', install_dir )
                if move_elem_text:
                    action_dict[ move_elem.tag ] = move_elem_text
        elif action_type == 'set_environment':
            # <action type="set_environment">
            #     <environment_variable name="PATH" action="prepend_to">$INSTALL_DIR/bin</environment_variable>
            # </action>
            for env_elem in action_elem:
                if env_elem.tag == 'environment_variable':
                    env_var_name = env_elem.get( 'name', 'PATH' )
                    env_var_action = env_elem.get( 'action', 'prepend_to' )
                    env_var_text = env_elem.text.replace( '$INSTALL_DIR', install_dir )
                    if env_var_text:
                        action_dict[ env_elem.tag ] = dict( name=env_var_name, action=env_var_action, value=env_var_text )
        else:
            continue
        actions.append( ( action_type, action_dict ) )
    if actions:
        actions_dict[ 'actions' ] = actions
    if proprietary_fabfile_path:
        # TODO: this is not yet supported or functional, but when it is handle it using the fabric api.
        # run_proprietary_fabric_method( app, elem, proprietary_fabfile_path, install_dir, package_name=package_name )
        raise Exception( 'Tool dependency installation using proprietary fabric scripts is not yet supported.' )
    else:
        try:
            # There is currently only one fabric method.
            install_and_build_package( app, tool_dependency, actions_dict )
        except Exception, e:
            tool_dependency.status = app.model.ToolDependency.installation_status.ERROR
            tool_dependency.error_message = str( e )
            sa_session.add( tool_dependency )
            sa_session.flush()
        if tool_dependency.status != app.model.ToolDependency.installation_status.ERROR:
            tool_dependency.status = app.model.ToolDependency.installation_status.INSTALLED
            sa_session.add( tool_dependency )
            sa_session.flush()
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
                    params_str += 'actions=%s,' % tool_shed_encode( encoding_sep.join( actions ) )
            else:
                if param_elem.text:
                    param_value = tool_shed_encode( param_elem.text )
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
    message = handle_post_build_processing( app, tool_dependency, install_dir, env_dependency_path, package_name=package_name )
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
