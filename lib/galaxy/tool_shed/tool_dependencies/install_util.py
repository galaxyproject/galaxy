import sys, os, subprocess, tempfile
import common_util
import fabric_util
from galaxy.tool_shed import encoding_util
from galaxy.model.orm import and_

from galaxy import eggs
import pkg_resources

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree, ElementInclude
from elementtree.ElementTree import Element, SubElement

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
def get_tool_dependency_install_dir( app, repository, type, name, version ):
    if type == 'package':
        return os.path.abspath( os.path.join( app.config.tool_dependency_dir,
                                              name,
                                              version,
                                              repository.owner,
                                              repository.name,
                                              repository.installed_changeset_revision ) )
    if type == 'set_environment':
        return os.path.abspath( os.path.join( app.config.tool_dependency_dir,
                                              'environment_settings',
                                              name,
                                              repository.owner,
                                              repository.name,
                                              repository.installed_changeset_revision ) )
def get_tool_shed_repository_install_dir( app, tool_shed_repository ):
    return os.path.abspath( tool_shed_repository.repo_files_directory( app ) )
def install_package( app, elem, tool_shed_repository, tool_dependencies=None ):
    # The value of tool_dependencies is a partial or full list of ToolDependency records associated with the tool_shed_repository.
    sa_session = app.model.context.current
    tool_dependency = None
    # The value of package_name should match the value of the "package" type in the tool config's <requirements> tag set, but it's not required.
    package_name = elem.get( 'name', None )
    package_version = elem.get( 'version', None )
    if package_name and package_version:
        if tool_dependencies:
            install_dir = get_tool_dependency_install_dir( app,
                                                           repository=tool_shed_repository,
                                                           type='package',
                                                           name=package_name,
                                                           version=package_version )
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
                if 'target_filename' in action_elem.attrib:
                    action_dict[ 'target_filename' ] = action_elem.attrib[ 'target_filename' ]
            else:
                continue
        elif action_type == 'make_directory':
            # <action type="make_directory">$INSTALL_DIR/lib/python</action>
            if action_elem.text:
                action_dict[ 'full_path' ] = action_elem.text.replace( '$INSTALL_DIR', install_dir )
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
            #     <environment_variable name="PYTHONPATH" action="append_to">$INSTALL_DIR/lib/python</environment_variable>
            #     <environment_variable name="PATH" action="prepend_to">$INSTALL_DIR/bin</environment_variable>
            # </action>
            env_var_dicts = []
            for env_elem in action_elem:
                if env_elem.tag == 'environment_variable':
                    env_var_dict = common_util.create_env_var_dict( env_elem, tool_dependency_install_dir=install_dir )
                    if env_var_dict:
                        env_var_dicts.append( env_var_dict )  
            if env_var_dicts:
                action_dict[ env_elem.tag ] = env_var_dicts
            else:
                continue
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
            fabric_util.install_and_build_package( app, tool_dependency, actions_dict )
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
def set_environment( app, elem, tool_shed_repository ):
    """
    Create a ToolDependency to set an environment variable.  This is different from the process used to set an environment variable that is associated
    with a package.  An example entry in a tool_dependencies.xml file is::

        <set_environment version="1.0">
            <environment_variable name="R_SCRIPT_PATH" action="set_to">$REPOSITORY_INSTALL_DIR</environment_variable>
        </set_environment>
    """
    sa_session = app.model.context.current
    tool_dependency = None
    env_var_version = elem.get( 'version', '1.0' )
    for env_var_elem in elem:
        # The value of env_var_name must match the text value of at least 1 <requirement> tag in the tool config's <requirements> tag set whose
        # "type" attribute is "set_environment" (e.g., <requirement type="set_environment">R_SCRIPT_PATH</requirement>).
        env_var_name = env_var_elem.get( 'name', None )
        env_var_action = env_var_elem.get( 'action', None )
        if env_var_name and env_var_action:
            install_dir = get_tool_dependency_install_dir( app,
                                                           repository=tool_shed_repository,
                                                           type='set_environment',
                                                           name=env_var_name,
                                                           version=None )
            tool_shed_repository_install_dir = get_tool_shed_repository_install_dir( app, tool_shed_repository )
            env_var_dict = common_util.create_env_var_dict( env_var_elem, tool_shed_repository_install_dir=tool_shed_repository_install_dir )
            if env_var_dict:
                if not os.path.exists( install_dir ):
                    os.makedirs( install_dir )
                tool_dependency = create_or_update_tool_dependency( app,
                                                                    tool_shed_repository,
                                                                    name=env_var_name,
                                                                    version=None,
                                                                    type='set_environment',
                                                                    status=app.model.ToolDependency.installation_status.INSTALLING,
                                                                    set_status=True )
                cmd = common_util.create_or_update_env_shell_file( install_dir, env_var_dict )
                if env_var_version == '1.0':
                    # Handle setting environment variables using a fabric method.
                    fabric_util.handle_command( app, tool_dependency, install_dir, cmd )
                    sa_session.refresh( tool_dependency )
                    if tool_dependency.status != app.model.ToolDependency.installation_status.ERROR:
                        tool_dependency.status = app.model.ToolDependency.installation_status.INSTALLED
                        sa_session.add( tool_dependency )
                        sa_session.flush()
                        print 'Environment variable ', env_var_name, 'set in', install_dir
