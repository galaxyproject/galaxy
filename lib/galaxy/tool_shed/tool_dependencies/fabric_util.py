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
def handle_post_build_processing( tool_dependency_dir, install_dir, package_name=None ):
    cmd = "echo 'PATH=%s/bin:$PATH; export PATH' > %s/env.sh;chmod +x %s/env.sh" % ( install_dir, install_dir, install_dir )
    message = ''
    output = local( cmd, capture=True )
    log_results( cmd, output, os.path.join( install_dir, 'env_sh.log' ) )
    if output.return_code:
        message = '%s  %s' % ( message, str( output.stderr ) )
    """
    Since automatic dependency installation requires a version attribute in the tool's <requirement> tag, we don't have to
    create a default symlink, but we'll keep this code around for a bit just in case we need it later.
    if package_name:
        package_dir = os.path.join( tool_dependency_dir, package_name )
        package_default = os.path.join( package_dir, 'default' )
        if not os.path.islink( package_default ):
            cmd = 'ln -s %s %s' % ( install_dir, package_default )
            output = local( cmd, capture=True )
            if output.return_code:
                message = '%s\n%s' % ( message, str( output.stderr ) )
    """
    return message
def install_and_build_package( params_dict ):
    """Install a Galaxy tool dependency package either via a url or a mercurial or git clone command."""
    install_dir = params_dict[ 'install_dir' ]
    download_url = params_dict.get( 'download_url', None )
    clone_cmd = params_dict.get( 'clone_cmd', None )
    build_commands = params_dict.get( 'build_commands', None )
    package_name = params_dict.get( 'package_name', None )
    with make_tmp_dir() as work_dir:
        with lcd( work_dir ):
            if download_url:
                downloaded_filename = os.path.split( download_url )[ -1 ]
                downloaded_file_path = common_util.url_download( work_dir, downloaded_filename, download_url )
                if common_util.istar( downloaded_file_path ):
                    common_util.extract_tar( downloaded_file_path, work_dir )
                    dir = common_util.tar_extraction_directory( work_dir, downloaded_filename )
                else:
                    dir = work_dir
            elif clone_cmd:
                output = local( clone_cmd, capture=True )
                log_results( clone_cmd, output, os.path.join( install_dir, 'clone_repository.log' ) )
                if output.return_code:
                    return '%s.  ' % str( output.stderr )
                dir = package_name
            if build_commands:
                with lcd( dir ):
                    current_dir = os.path.abspath( os.path.join( work_dir, dir ) )
                    for build_command_tup in build_commands:
                        build_command_key, build_command_dict = build_command_tup
                        if build_command_key.find( 'v^v^v' ) >= 0:
                            build_command_items = build_command_key.split( 'v^v^v' )
                            build_command_name = build_command_items[ 0 ]
                            build_command = build_command_items[ 1 ]
                        elif build_command_key in common_util.ALL_BUILD_COMMAND_NAMES:
                            build_command_name = build_command_key
                        else:
                            build_command_name = None
                        if build_command_name:
                            if build_command_name == 'change_directory':
                                current_dir = os.path.join( current_dir, build_command )
                                lcd( current_dir )
                            elif build_command_name == 'move_directory_files':
                                common_util.move_directory_files( current_dir=current_dir,
                                                                  source_dir=os.path.join( build_command_dict[ 'source_directory' ] ),
                                                                  destination_dir=os.path.join( build_command_dict[ 'destination_directory' ] ) )
                            elif build_command_name == 'move_file':
                                common_util.move_file( current_dir=current_dir,
                                                       source=os.path.join( build_command_dict[ 'source' ] ),
                                                       destination_dir=os.path.join( build_command_dict[ 'destination' ] ) )
                        else:
                            build_command = build_command_key
                            with settings( warn_only=True ):
                                output = local( build_command, capture=True )
                                log_results( build_command, output, os.path.join( install_dir, 'build_commands.log' ) )
                                if output.return_code:
                                    return '%s.  ' % str( output.stderr )
    return ''
def log_results( command, fabric_AttributeString, file_path ):
    """
    Write attributes of fabric.operations._AttributeString (which is the output of executing command using fabric's local() method)
    to a specified log file.
    """
    if os.path.exists( file_path ):
        logfile = open( file_path, 'ab' )
    else:
        logfile = open( file_path, 'wb' )
    logfile.write( "\n#############################################" )
    logfile.write( '\n%s\nSTDOUT\n' % command )
    logfile.write( "#############################################\n" )
    logfile.write( str( fabric_AttributeString.stdout ) )
    logfile.write( "\n#############################################" )
    logfile.write( '\n%s\nSTDERR\n' % command )
    logfile.write( "#############################################\n" )
    logfile.write( str( fabric_AttributeString.stderr ) )
    logfile.close()
