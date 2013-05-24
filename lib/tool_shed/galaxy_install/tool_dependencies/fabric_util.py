# For Python 2.5
from __future__ import with_statement

import common_util
import logging
import os
import shutil
import tempfile
import shutil
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

CMD_SEPARATOR = '__CMD_SEP__'
INSTALLATION_LOG = 'INSTALLATION.log'
VIRTUALENV_URL = 'https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.9.1.tar.gz'

def check_fabric_version():
    version = env.version
    if int( version.split( "." )[ 0 ] ) < 1:
        raise NotImplementedError( "Install Fabric version 1.0 or later." )

def handle_command( app, tool_dependency, install_dir, cmd, return_output=False ):
    sa_session = app.model.context.current
    with settings( warn_only=True ):
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
    if return_output:
        return output
    return output.return_code

def handle_environment_variables( app, tool_dependency, install_dir, env_var_dict, set_prior_environment_commands ):
    """
    This method works with with a combination of three tool dependency definition tag sets, which are defined in the tool_dependencies.xml file in the
    order discussed here.  The example for this discussion is the tool_dependencies.xml file contained in the osra repository, which is available at:
    
    http://testtoolshed.g2.bx.psu.edu/view/bgruening/osra 
    
    The first tag set defines a complex repository dependency like this.  This tag set ensures that changeset revision XXX of the repository named
    package_graphicsmagick_1_3 owned by YYY in the tool shed ZZZ has been previously installed.
    
    <tool_dependency>
        <package name="graphicsmagick" version="1.3.18">
            <repository changeset_revision="XXX" name="package_graphicsmagick_1_3" owner="YYY" prior_installation_required="True" toolshed="ZZZ" />
        </package>
        ...
    
    * By the way, there is an env.sh file associated with version 1.3.18 of the graphicsmagick package which looks something like this (we'll reference
    this file later in this discussion.
    ----
    GRAPHICSMAGICK_ROOT_DIR=/<my configured tool dependency path>/graphicsmagick/1.3.18/YYY/package_graphicsmagick_1_3/XXX/gmagick; 
    export GRAPHICSMAGICK_ROOT_DIR
    ----
    
    The second tag set defines a specific package dependency that has been previously installed (guaranteed by the tag set discussed above) and compiled,
    where the compiled dependency is needed by the tool dependency currently being installed (osra version 2.0.0 in this case) and complied in order for
    it's installation and compilation to succeed.  This tag set is contained within the <package name="osra" version="2.0.0"> tag set, which implies that
    version 2.0.0 of the osra package requires version 1.3.18 of the graphicsmagick package in order to successfully compile.  When this tag set is handled,
    one of the effects is that the env.sh file associated with graphicsmagick version 1.3.18 is "sourced", which undoubtedly sets or alters certain environment
    variables (e.g. PATH, PYTHONPATH, etc).
    
    <!-- populate the environment variables from the dependent repositories -->
    <action type="set_environment_for_install">
        <repository changeset_revision="XXX" name="package_graphicsmagick_1_3" owner="YYY" toolshed="ZZZ">
            <package name="graphicsmagick" version="1.3.18" />
        </repository>
    </action>
    
    The third tag set enables discovery of the same required package dependency discussed above for correctly compiling the osra version 2.0.0 package, but
    in this case the package can be discovered at tool execution time.  Using the $ENV[] option as shown in this example, the value of the environment
    variable named GRAPHICSMAGICK_ROOT_DIR (which was set in the environment using the second tag set described above) will be used to automatically alter
    the env.sh file associated with the osra version 2.0.0 tool dependency when it is installed into Galaxy.  * Refer to where we discussed the env.sh file
    for version 1.3.18 of the graphicsmagick package above. 

    <action type="set_environment">
        <environment_variable action="prepend_to" name="LD_LIBRARY_PATH">$ENV[$GRAPHICSMAGICK_ROOT_DIR]/lib/</environment_variable>
        <environment_variable action="prepend_to" name="LD_LIBRARY_PATH">$INSTALL_DIR/potrace/build/lib/</environment_variable>
        <environment_variable action="prepend_to" name="PATH">$INSTALL_DIR/bin</environment_variable>
        <!-- OSRA_DATA_FILES is only used by the galaxy wrapper and is not part of OSRA -->
        <environment_variable action="set_to" name="OSRA_DATA_FILES">$INSTALL_DIR/share</environment_variable>
    </action>

    The above tag will produce an env.sh file for version 2.0.0 of the osra package when it it installed into Galaxy that looks something like this.  Notice
    that the path to the gmagick binary is included here since it expands the defined $ENV[$GRAPHICSMAGICK_ROOT_DIR] value in the above tag set.
    
    ----
    LD_LIBRARY_PATH=/<my configured tool dependency path>/graphicsmagick/1.3.18/YYY/package_graphicsmagick_1_3/XXX/gmagick/lib/:$LD_LIBRARY_PATH;
    export LD_LIBRARY_PATH
    LD_LIBRARY_PATH=/<my configured tool dependency path>/osra/1.4.0/YYY/depends_on/XXX/potrace/build/lib/:$LD_LIBRARY_PATH;
    export LD_LIBRARY_PATH
    PATH=/<my configured tool dependency path>/osra/1.4.0/YYY/depends_on/XXX/bin:$PATH;
    export PATH
    OSRA_DATA_FILES=/<my configured tool dependency path>/osra/1.4.0/YYY/depends_on/XXX/share;
    export OSRA_DATA_FILES
    ----
    """
    env_var_value = env_var_dict[ 'value' ]
    if '$ENV[' in env_var_value and ']' in env_var_value:
        # Pull out the name of the environment variable to populate.
        inherited_env_var_name = env_var_value.split( '[' )[1].split( ']' )[0]
        to_replace = '$ENV[%s]' % inherited_env_var_name
        # Build a command line that outputs CMD_SEPARATOR + environment variable value + CMD_SEPARATOR.
        set_prior_environment_commands.extend( [ "echo '%s'" % CMD_SEPARATOR, 'echo $%s' % inherited_env_var_name, "echo '%s'" % CMD_SEPARATOR ] )
        command = ' ; '.join( set_prior_environment_commands )
        # Run the command and capture the output.
        command_return = handle_command( app, tool_dependency, install_dir, command, return_output=True )
        # And extract anything between the two instances of CMD_SEPARATOR.
        environment_variable_value = command_return.split( CMD_SEPARATOR )[1].split( CMD_SEPARATOR )[0].strip( '\n' )
        if environment_variable_value:
            log.info( 'Replacing %s with %s in env.sh for this repository.', to_replace, environment_variable_value )
            env_var_value = env_var_value.replace( to_replace, environment_variable_value )
        else:
            # If the return is empty, replace the original $ENV[] with nothing, to avoid any shell misparsings later on.
            log.error( 'Environment variable %s not found, removing from set_environment.', inherited_env_var_name )
            env_var_value = env_var_value.replace( to_replace, '$%s' % inherited_env_var_name )
        env_var_dict[ 'value' ] = env_var_value
    return env_var_dict

def install_virtualenv( app, venv_dir ):
    if not os.path.exists( venv_dir ):
        with make_tmp_dir() as work_dir:
            downloaded_filename = VIRTUALENV_URL.rsplit('/', 1)[-1]
            downloaded_file_path = common_util.url_download( work_dir, downloaded_filename, VIRTUALENV_URL )
            if common_util.istar( downloaded_file_path ):
                common_util.extract_tar( downloaded_file_path, work_dir )
                dir = common_util.tar_extraction_directory( work_dir, downloaded_filename )
            else:
                log.error( "Failed to download virtualenv: Downloaded file '%s' is not a tar file", downloaded_filename )
                return False
            full_path_to_dir = os.path.abspath( os.path.join( work_dir, dir ) )
            shutil.move( full_path_to_dir, venv_dir )
    return True

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
                        # Sometimes compressed archives extracts their content to a folder other than the default defined file name.  Using this
                        # attribute will ensure that the file name is set appropriately and can be located after download, decompression and extraction.
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
                        # Sometimes compressed archives extracts their content to a folder other than the default defined file name.  Using this
                        # attribute will ensure that the file name is set appropriately and can be located after download, decompression and extraction.
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
                            # Build a command line from the prior_installation_required, in case an environment variable is referenced
                            # in the set_environment action.
                            cmds = []
                            for env_shell_file_path in env_shell_file_paths:
                                for i, env_setting in enumerate( open( env_shell_file_path ) ):
                                    cmds.append( env_setting.strip( '\n' ) )
                            env_var_dicts = action_dict[ 'environment_variable' ]
                            for env_var_dict in env_var_dicts:
                                # Check for the presence of the $ENV[] key string and populate it if possible.
                                env_var_dict = handle_environment_variables( app, tool_dependency, install_dir, env_var_dict, cmds )
                                env_command = common_util.create_or_update_env_shell_file( install_dir, env_var_dict )
                                return_code = handle_command( app, tool_dependency, install_dir, env_command )
                                if return_code:
                                    return
                        elif action_type == 'set_environment_for_install':
                            # Currently the only action supported in this category is a list of paths to one or more tool dependency env.sh files,
                            # the environment setting in each of which will be injected into the environment for all <action type="shell_command">
                            # tags that follow this <action type="set_environment_for_install"> tag set in the tool_dependencies.xml file.
                            env_shell_file_paths = action_dict[ 'env_shell_file_paths' ]
                        elif action_type == 'setup_virtualenv':
                            # TODO: maybe should be configurable
                            venv_src_directory = os.path.abspath( os.path.join( app.config.tool_dependency_dir, '__virtualenv_src' ) )
                            if not install_virtualenv( app, venv_src_directory ):
                                log.error( 'Unable to install virtualenv' )
                                return
                            requirements = action_dict[ 'requirements' ]
                            if os.path.exists( os.path.join( dir, requirements ) ):
                                # requirements specified as path to a file
                                requirements_path = requirements
                            else:
                                # requirements specified directly in XML, create a file with these for pip.
                                requirements_path = os.path.join( install_dir, "requirements.txt" )
                                with open( requirements_path, "w" ) as f:
                                    f.write( requirements )
                            venv_directory = os.path.join( install_dir, "venv" )
                            # TODO: Consider making --no-site-packages optional.
                            setup_command = "python %s/virtualenv.py --no-site-packages '%s'" % (venv_src_directory, venv_directory)
                            # POSIXLY_CORRECT forces shell commands . and source to have the same
                            # and well defined behavior in bash/zsh.
                            activate_command = "POSIXLY_CORRECT=1; . %s" % os.path.join( venv_directory, "bin", "activate" )
                            install_command = "pip install -r '%s'" % requirements_path
                            full_setup_command = "%s; %s; %s" % ( setup_command, activate_command, install_command )
                            return_code = handle_command( app, tool_dependency, install_dir, full_setup_command )
                            if return_code:
                                return
                            site_packages_command = "%s -c 'import os, sys; print os.path.join(sys.prefix, \"lib\", \"python\" + sys.version[:3], \"site-packages\")'" % os.path.join( venv_directory, "bin", "python" )
                            output = handle_command( app, tool_dependency, install_dir, site_packages_command, return_output=True )
                            if output.return_code:
                                return
                            if not os.path.exists( output.stdout ):
                                log.error( "virtualenv's site-packages directory '%s' does not exist", output.stdout )
                                return
                            modify_env_command = common_util.create_or_update_env_shell_file( install_dir, dict( name="PYTHONPATH", action="prepend_to", value=output.stdout ) )
                            return_code = handle_command( app, tool_dependency, install_dir, modify_env_command )
                            if return_code:
                                return
                            modify_env_command = common_util.create_or_update_env_shell_file( install_dir, dict( name="PATH", action="prepend_to", value=os.path.join( venv_directory, "bin" ) ) )
                            return_code = handle_command( app, tool_dependency, install_dir, modify_env_command )
                            if return_code:
                                return
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
