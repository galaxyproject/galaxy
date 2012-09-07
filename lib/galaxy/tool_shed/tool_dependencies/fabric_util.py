# For Python 2.5
from __future__ import with_statement

import os, shutil, tempfile
from contextlib import contextmanager
import common_util

from galaxy import eggs
import pkg_resources

pkg_resources.require('ssh' )
pkg_resources.require( 'Fabric' )

from fabric.api import env, lcd, local, settings

INSTALLATION_LOG = 'INSTALLATION.log'

def check_fabric_version():
    version = env.version
    if int( version.split( "." )[ 0 ] ) < 1:
        raise NotImplementedError( "Install Fabric version 1.0 or later." )
def set_galaxy_environment( galaxy_user, tool_dependency_dir, host='localhost', shell='/bin/bash -l -c' ):
    """General Galaxy environment configuration"""
    env.user = galaxy_user
    env.install_dir = tool_dependency_dir
    env.host_string = host
    env.shell = shell
    env.use_sudo = False
    env.safe_cmd = local
    return env
@contextmanager
def make_tmp_dir():
    work_dir = tempfile.mkdtemp()
    yield work_dir
    if os.path.exists( work_dir ):
        local( 'rm -rf %s' % work_dir )
def handle_post_build_processing( app, tool_dependency, install_dir, env_dependency_path, package_name=None ):
    # TODO: This method is deprecated and should be eliminated when the implementation for handling proprietary fabric scripts is implemented.
    sa_session = app.model.context.current
    cmd = "echo 'PATH=%s:$PATH; export PATH' > %s/env.sh;chmod +x %s/env.sh" % ( env_dependency_path, install_dir, install_dir )
    output = local( cmd, capture=True )
    log_results( cmd, output, os.path.join( install_dir, INSTALLATION_LOG ) )
    if output.return_code:
        tool_dependency.status = app.model.ToolDependency.installation_status.ERROR
        tool_dependency.error_message = str( output.stderr )
        sa_session.add( tool_dependency )
        sa_session.flush()
def install_and_build_package( app, tool_dependency, actions_dict ):
    """Install a Galaxy tool dependency package either via a url or a mercurial or git clone command."""
    sa_session = app.model.context.current
    install_dir = actions_dict[ 'install_dir' ]
    package_name = actions_dict[ 'package_name' ]
    #download_url = actions_dict.get( 'download_url', None )
    #clone_cmd = actions_dict.get( 'clone_cmd', None )
    actions = actions_dict.get( 'actions', None )
    if actions:
        with make_tmp_dir() as work_dir:
            with lcd( work_dir ):
                # The first action in the list of actions will be the one that defines the installation process.  There
                # are currently only two supported processes; download_by_url and clone via a "shell_command" action type.
                action_type, action_dict = actions[ 0 ]
                if action_type == 'download_by_url':
                    # <action type="download_by_url">http://sourceforge.net/projects/samtools/files/samtools/0.1.18/samtools-0.1.18.tar.bz2</action>
                    url = action_dict[ 'url' ]
                    downloaded_filename = os.path.split( url )[ -1 ]
                    downloaded_file_path = common_util.url_download( work_dir, downloaded_filename, url )
                    if common_util.istar( downloaded_file_path ):
                        common_util.extract_tar( downloaded_file_path, work_dir )
                        dir = common_util.tar_extraction_directory( work_dir, downloaded_filename )
                    else:
                        dir = work_dir
                elif action_type == 'shell_command':
                    # <action type="shell_command">git clone --recursive git://github.com/ekg/freebayes.git</action>
                    clone_cmd = action_dict[ 'command' ]
                    output = local( clone_cmd, capture=True )
                    log_results( clone_cmd, output, os.path.join( install_dir, INSTALLATION_LOG ) )
                    if output.return_code:
                        tool_dependency.status = app.model.ToolDependency.installation_status.ERROR
                        tool_dependency.error_message = str( output.stderr )
                        sa_session.add( tool_dependency )
                        sa_session.flush()
                        return
                    dir = package_name
                if not os.path.exists( dir ):
                    os.makedirs( dir )
                # The package has been down-loaded, so we can now perform all of the actions defined for building it.
                with lcd( dir ):                
                    for action_tup in actions[ 1: ]:
                        action_type, action_dict = action_tup
                        current_dir = os.path.abspath( os.path.join( work_dir, dir ) )
                        if action_type == 'make_directory':
                            common_util.make_directory( full_path=action_dict[ 'full_path' ] )
                        elif action_type == 'move_directory_files':
                            common_util.move_directory_files( current_dir=current_dir,
                                                              source_dir=os.path.join( action_dict[ 'source_directory' ] ),
                                                              destination_dir=os.path.join( action_dict[ 'destination_directory' ] ) )
                        elif action_type == 'move_file':
                            common_util.move_file( current_dir=current_dir,
                                                   source=os.path.join( action_dict[ 'source' ] ),
                                                   destination_dir=os.path.join( action_dict[ 'destination' ] ) )
                        elif action_type == 'set_environment':
                            # Currently the only action supported in this category is "environment_variable".
                            env_var_dicts = action_dict[ 'environment_variable' ]
                            for env_var_dict in env_var_dicts:
                                env_var_name = env_var_dict[ 'name' ]
                                env_var_action = env_var_dict[ 'action' ]
                                env_var_value = env_var_dict[ 'value' ]
                                if env_var_action == 'prepend_to':
                                    changed_value = '%s:$%s' % ( env_var_value, env_var_name )
                                elif env_var_action == 'set_to':
                                    changed_value = '%s' % env_var_value
                                elif env_var_action == 'append_to':
                                    changed_value = '$%s:%s' % ( env_var_name, env_var_value )
                                env_shell_file_path = '%s/env.sh' % install_dir
                                if os.path.exists( env_shell_file_path ):
                                    write_action = '>>'
                                else:
                                    write_action = '>'
                                cmd = "echo '%s=%s; export %s' %s %s;chmod +x %s" % ( env_var_name,
                                                                                      changed_value,
                                                                                      env_var_name,
                                                                                      write_action,
                                                                                      env_shell_file_path,
                                                                                      env_shell_file_path )
                                output = local( cmd, capture=True )
                                log_results( cmd, output, os.path.join( install_dir, INSTALLATION_LOG ) )
                                if output.return_code:
                                    tool_dependency.status = app.model.ToolDependency.installation_status.ERROR
                                    tool_dependency.error_message = str( output.stderr )
                                    sa_session.add( tool_dependency )
                                    sa_session.flush()
                                    return
                        elif action_type == 'shell_command':
                            action = action_dict[ 'command' ]
                            with settings( warn_only=True ):
                                output = local( action, capture=True )
                                log_results( action, output, os.path.join( install_dir, INSTALLATION_LOG ) )
                                if output.return_code:
                                    tool_dependency.status = app.model.ToolDependency.installation_status.ERROR
                                    tool_dependency.error_message = str( output.stderr )
                                    sa_session.add( tool_dependency )
                                    sa_session.flush()
                                    return
def log_results( command, fabric_AttributeString, file_path ):
    """
    Write attributes of fabric.operations._AttributeString (which is the output of executing command using fabric's local() method)
    to a specified log file.
    """
    if os.path.exists( file_path ):
        logfile = open( file_path, 'ab' )
    else:
        logfile = open( file_path, 'wb' )
    logfile.write( "\n#############################################\n" )
    logfile.write( '%s\nSTDOUT\n' % command )
    logfile.write( str( fabric_AttributeString.stdout ) )
    logfile.write( "\n#############################################\n" )
    logfile.write( "\n#############################################\n" )
    logfile.write( '%s\nSTDERR\n' % command )
    logfile.write( str( fabric_AttributeString.stderr ) )
    logfile.write( "\n#############################################\n" )
    logfile.close()
