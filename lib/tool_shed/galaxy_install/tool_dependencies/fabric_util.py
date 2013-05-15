# For Python 2.5
from __future__ import with_statement

import common_util
import logging
import os
import shutil
import tempfile
from contextlib import contextmanager

from galaxy import eggs
import pkg_resources

pkg_resources.require('ssh' )
pkg_resources.require( 'Fabric' )

from fabric.api import env
from fabric.api import lcd
from fabric.api import local
from fabric.api import settings

log = logging.getLogger( __name__ )

INSTALLATION_LOG = 'INSTALLATION.log'

def check_fabric_version():
    version = env.version
    if int( version.split( "." )[ 0 ] ) < 1:
        raise NotImplementedError( "Install Fabric version 1.0 or later." )

def handle_command( app, tool_dependency, install_dir, cmd ):
    sa_session = app.model.context.current
    output = local( cmd, capture=True )
    log_results( cmd, output, os.path.join( install_dir, INSTALLATION_LOG ) )
    if output.return_code:
        tool_dependency.status = app.model.ToolDependency.installation_status.ERROR
        if output.stderr:
            tool_dependency.error_message = str( output.stderr )[ :32768 ]
        elif output.stdout:
            tool_dependency.error_message = str( output.stdout )[ :32768 ]
        else:
            tool_dependency.error_message = "Unknown error occurred executing shell command %s, return_code: %s"  % ( str( cmd ), str( output.return_code ) )
        sa_session.add( tool_dependency )
        sa_session.flush()
    return output.return_code

def install_and_build_package( app, tool_dependency, actions_dict ):
    """Install a Galaxy tool dependency package either via a url or a mercurial or git clone command."""
    sa_session = app.model.context.current
    install_dir = actions_dict[ 'install_dir' ]
    package_name = actions_dict[ 'package_name' ]
    actions = actions_dict.get( 'actions', None )
    filtered_actions = []
    env_shell_file_paths = []
    if actions:
        with make_tmp_dir() as work_dir:
            with lcd( work_dir ):
                # The first action in the list of actions will be the one that defines the installation process.  There
                # are currently only two supported processes; download_by_url and clone via a "shell_command" action type.
                action_type, action_dict = actions[ 0 ]
                if action_type == 'download_by_url':
                    # Eliminate the download_by_url action so remaining actions can be processed correctly.
                    filtered_actions = actions[ 1: ]
                    url = action_dict[ 'url' ]
                    if 'target_filename' in action_dict:
                        downloaded_filename = action_dict[ 'target_filename' ]
                    else:
                        downloaded_filename = os.path.split( url )[ -1 ]
                    downloaded_file_path = common_util.url_download( work_dir, downloaded_filename, url )
                    if common_util.istar( downloaded_file_path ):
                        # <action type="download_by_url">http://sourceforge.net/projects/samtools/files/samtools/0.1.18/samtools-0.1.18.tar.bz2</action>
                        common_util.extract_tar( downloaded_file_path, work_dir )
                        dir = common_util.tar_extraction_directory( work_dir, downloaded_filename )
                    elif common_util.isjar( downloaded_file_path ):
                        dir = os.path.curdir
                    elif common_util.iszip( downloaded_file_path ):
                        # <action type="download_by_url">http://downloads.sourceforge.net/project/picard/picard-tools/1.56/picard-tools-1.56.zip</action>
                        zip_archive_extracted = common_util.extract_zip( downloaded_file_path, work_dir )
                        dir = common_util.zip_extraction_directory( work_dir, downloaded_filename )
                    else:
                        dir = os.path.curdir
                elif action_type == 'shell_command':
                    # <action type="shell_command">git clone --recursive git://github.com/ekg/freebayes.git</action>
                    # Eliminate the shell_command clone action so remaining actions can be processed correctly.
                    filtered_actions = actions[ 1: ]
                    return_code = handle_command( app, tool_dependency, install_dir, action_dict[ 'command' ] )
                    if return_code:
                        return
                    dir = package_name
                elif action_type == 'download_file':
                    # <action type="download_file">http://effectors.org/download/version/TTSS_GUI-1.0.1.jar</action>
                    # Download a single file to the working directory.
                    filtered_actions = actions[ 1: ]
                    url = action_dict[ 'url' ]
                    if action_dict[ 'target_filename' ]:
                        filename = action_dict[ 'target_filename' ]
                    else:
                        filename = url.split( '/' )[ -1 ]
                    common_util.url_download( work_dir, filename, url )
                    dir = os.path.curdir
                else:
                    # We're handling a complex repository dependency where we only have a set_environment tag set.
                    # <action type="set_environment">
                    #    <environment_variable name="PATH" action="prepend_to">$INSTALL_DIR/bin</environment_variable>
                    # </action>
                    filtered_actions = [ a for a in actions ]
                    dir = install_dir
                # We need to be careful in determining if the value of dir is a valid directory because we're dealing with 2 environments, the fabric local
                # environment and the python environment.  Checking the path as follows should work.
                full_path_to_dir = os.path.abspath( os.path.join( work_dir, dir ) )
                if not os.path.exists( full_path_to_dir ):
                    os.makedirs( full_path_to_dir )
                # The package has been down-loaded, so we can now perform all of the actions defined for building it.
                with lcd( dir ):
                    for action_tup in filtered_actions:
                        action_type, action_dict = action_tup
                        current_dir = os.path.abspath( os.path.join( work_dir, dir ) )
                        if action_type == 'make_directory':
                            common_util.make_directory( full_path=action_dict[ 'full_path' ] )
                        elif action_type == 'move_directory_files':
                            common_util.move_directory_files( current_dir=current_dir,
                                                              source_dir=os.path.join( action_dict[ 'source_directory' ] ),
                                                              destination_dir=os.path.join( action_dict[ 'destination_directory' ] ) )
                        elif action_type == 'move_file':
                            # TODO: Remove this hack that resets current_dir so that the pre-compiled bwa binary can be found.
                            # current_dir = '/Users/gvk/workspaces_2008/bwa/bwa-0.5.9'
                            common_util.move_file( current_dir=current_dir,
                                                   source=os.path.join( action_dict[ 'source' ] ),
                                                   destination_dir=os.path.join( action_dict[ 'destination' ] ) )
                        elif action_type == 'set_environment':
                            # Currently the only action supported in this category is "environment_variable".
                            env_var_dicts = action_dict[ 'environment_variable' ]
                            for env_var_dict in env_var_dicts:
                                cmd = common_util.create_or_update_env_shell_file( install_dir, env_var_dict )
                                return_code = handle_command( app, tool_dependency, install_dir, cmd )
                                if return_code:
                                    return
                        elif action_type == 'set_environment_for_install':
                            # Currently the only action supported in this category is a list of paths to one or more tool dependency env.sh files,
                            # the environment setting in each of which will be injected into the environment for all <action type="shell_command">
                            # tags that follow this <action type="set_environment_for_install"> tag set in the tool_dependencies.xml file.
                            env_shell_file_paths = action_dict[ 'env_shell_file_paths' ]
                        elif action_type == 'shell_command':
                            with settings( warn_only=True ):
                                cmd = ''
                                for env_shell_file_path in env_shell_file_paths:
                                    for i, env_setting in enumerate( open( env_shell_file_path ) ):
                                        cmd += '%s\n' % env_setting
                                cmd += action_dict[ 'command' ]
                                return_code = handle_command( app, tool_dependency, install_dir, cmd )
                                if return_code:
                                    return
                        elif action_type == 'download_file':
                            # Download a single file to the current directory.
                            url = action_dict[ 'url' ]
                            if action_dict[ 'target_filename' ]:
                                filename = action_dict[ 'target_filename' ]
                            else:
                                filename = url.split( '/' )[ -1 ]
                            common_util.url_download( current_dir, filename, url )

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

@contextmanager
def make_tmp_dir():
    work_dir = tempfile.mkdtemp()
    yield work_dir
    if os.path.exists( work_dir ):
        local( 'rm -rf %s' % work_dir )

def set_galaxy_environment( galaxy_user, tool_dependency_dir, host='localhost', shell='/bin/bash -l -c' ):
    """General Galaxy environment configuration.  This method is not currently used."""
    env.user = galaxy_user
    env.install_dir = tool_dependency_dir
    env.host_string = host
    env.shell = shell
    env.use_sudo = False
    env.safe_cmd = local
    return env
