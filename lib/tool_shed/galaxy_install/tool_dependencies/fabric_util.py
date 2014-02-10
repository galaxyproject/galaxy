# For Python 2.5
from __future__ import with_statement

import logging
import os
import shutil
import tempfile
import shutil
import td_common_util
from contextlib import contextmanager
from galaxy.util import unicodify
from galaxy.util.template import fill_template
from galaxy import eggs

eggs.require( 'ssh' )
eggs.require( 'paramiko' )
eggs.require( 'Fabric' )

from fabric.api import env
from fabric.api import hide
from fabric.api import lcd
from fabric.api import local
from fabric.api import settings
from fabric.api import prefix

log = logging.getLogger( __name__ )

INSTALLATION_LOG = 'INSTALLATION.log'
VIRTUALENV_URL = 'https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.9.1.tar.gz'


class EnvFileBuilder( object ):

    def __init__( self, install_dir ):
        self.install_dir = install_dir
        self.return_code = 0

    def append_line( self, skip_if_contained=True, make_executable=True, **kwd ):
        env_var_dict = dict( **kwd )
        env_entry, env_file = self.create_or_update_env_shell_file( self.install_dir, env_var_dict )
        return_code = file_append( env_entry, env_file, skip_if_contained=skip_if_contained, make_executable=make_executable )
        self.return_code = self.return_code or return_code
        return self.return_code
    
    @staticmethod
    def create_or_update_env_shell_file( install_dir, env_var_dict ):
        env_var_action = env_var_dict[ 'action' ]
        env_var_value = env_var_dict[ 'value' ]
        if env_var_action in [ 'prepend_to', 'set_to', 'append_to' ]:
            env_var_name = env_var_dict[ 'name' ]
            if env_var_action == 'prepend_to':
                changed_value = '%s:$%s' % ( env_var_value, env_var_name )
            elif env_var_action == 'set_to':
                changed_value = '%s' % env_var_value
            elif env_var_action == 'append_to':
                changed_value = '$%s:%s' % ( env_var_name, env_var_value )
            line = "%s=%s; export %s" % ( env_var_name, changed_value, env_var_name )
        elif env_var_action == "source":
            line = "if [ -f %s ] ; then . %s ; fi" % ( env_var_value, env_var_value )
        else:
            raise Exception( "Unknown shell file action %s" % env_var_action )
        env_shell_file_path = os.path.join( install_dir, 'env.sh' )
        return line, env_shell_file_path


class InstallEnvironment( object ):
    """Object describing the environment built up as part of the process of building and installing a package."""

    def add_env_shell_file_paths( self, paths ):
        for path in paths:
            self.env_shell_file_paths.append( str( path ) )

    def build_command( self, command, action_type='shell_command' ):
        """
        Build command line for execution from simple command, but
        configuring environment described by this object.
        """
        env_cmds = self.environment_commands( action_type )
        return '\n'.join( env_cmds + [ command ] )

    def __call__( self, install_dir ):
        with settings( warn_only=True, **td_common_util.get_env_var_values( install_dir ) ):
            with prefix( self.__setup_environment() ):
                yield

    def environment_commands( self, action_type ):
        """Build a list of commands used to construct the environment described by this object."""
        cmds = []
        for env_shell_file_path in self.env_shell_file_paths:
            if os.path.exists( env_shell_file_path ):
                for env_setting in open( env_shell_file_path ):
                    cmds.append( env_setting.strip( '\n' ) )
            else:
                log.debug( 'Invalid file %s specified, ignoring %s action.' % ( str( env_shell_file_path ), str( action_type ) ) )
        return cmds

    def environment_dict( self, action_type='template_command' ):
        env_vars = dict()
        for env_shell_file_path in self.env_shell_file_paths:
            if os.path.exists( env_shell_file_path ):
                for env_setting in open( env_shell_file_path ):
                    env_string = env_setting.split( ';' )[ 0 ]
                    env_name, env_path = env_string.split( '=' )
                    env_vars[ env_name ] = env_path
            else:
                log.debug( 'Invalid file %s specified, ignoring template_command action.' % str( env_shell_file_path ) )
        return env_vars

    def __init__( self ):
        self.env_shell_file_paths = []

    def __setup_environment( self ):
        return "&&".join( [ ". %s" % file for file in self.__valid_env_shell_file_paths() ] )

    def __valid_env_shell_file_paths( self ):
        return [ file for file in self.env_shell_file_paths if os.path.exists( file ) ]

def check_fabric_version():
    version = env.version
    if int( version.split( "." )[ 0 ] ) < 1:
        raise NotImplementedError( "Install Fabric version 1.0 or later." )

def file_append( text, file_path, skip_if_contained=True, make_executable=True ):
    '''
    Append a line to a file unless skip_if_contained is True and the line already exists in the file. This method creates the file
    if it doesn't exist.  If make_executable is True, the permissions on the file are set to executable by the owner.  This method
    is similar to a local version of fabric.contrib.files.append.
    '''
    if not os.path.exists( file_path ):
        local( 'touch %s' % file_path )
    if make_executable:
        # Explicitly set the file to the received mode if valid.
        with settings( hide( 'everything' ), warn_only=True ):
            local( 'chmod +x %s' % file_path )
    return_code = 0
    # Convert the received text to a list, in order to support adding one or more lines to the file.
    if isinstance( text, basestring ):
        text = [ text ]
    for line in text:
        # Build a regex to search for the relevant line in env.sh.
        regex = td_common_util.egrep_escape( line )
        if skip_if_contained:
            # If the line exists in the file, egrep will return a success.
            with settings( hide( 'everything' ), warn_only=True ):
                egrep_cmd = 'egrep "^%s$" %s' % ( regex, file_path )
                contains_line = local( egrep_cmd ).succeeded
            if contains_line:
                continue
        # Append the current line to the file, escaping any single quotes in the line.
        line = line.replace( "'", r"'\\''" )
        return_code = local( "echo '%s' >> %s" % ( line, file_path ) ).return_code
        if return_code:
            # Return upon the first error encountered.
            return return_code
    return return_code

def filter_actions_after_binary_installation( actions ):
    '''Filter out actions that should not be processed if a binary download succeeded.'''
    filtered_actions = []
    for action in actions:
        action_type, action_dict = action
        if action_type in [ 'set_environment', 'chmod', 'download_binary' ]:
            filtered_actions.append( action )
    return filtered_actions

def handle_action_shell_file_paths( env_file_builder, action_dict ):
    shell_file_paths = action_dict.get( 'action_shell_file_paths', [] )
    for shell_file_path in shell_file_paths:
        env_file_builder.append_line( action="source", value=shell_file_path )

def handle_command( app, tool_dependency, install_dir, cmd, return_output=False ):
    context = app.install_model.context
    with settings( warn_only=True ):
        output = local( cmd, capture=True )
    log_results( cmd, output, os.path.join( install_dir, INSTALLATION_LOG ) )
    if output.return_code:
        tool_dependency.status = app.install_model.ToolDependency.installation_status.ERROR
        if output.stderr:
            tool_dependency.error_message = unicodify( str( output.stderr )[ :32768 ] )
        elif output.stdout:
            tool_dependency.error_message = unicodify( str( output.stdout )[ :32768 ] )
        else:
            tool_dependency.error_message = "Unknown error occurred executing shell command %s, return_code: %s"  % ( str( cmd ), str( output.return_code ) )
        context.add( tool_dependency )
        context.flush()
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
        <environment_variable action="prepend_to" name="LD_LIBRARY_PATH">$ENV[GRAPHICSMAGICK_ROOT_DIR]/lib/</environment_variable>
        <environment_variable action="prepend_to" name="LD_LIBRARY_PATH">$INSTALL_DIR/potrace/build/lib/</environment_variable>
        <environment_variable action="prepend_to" name="PATH">$INSTALL_DIR/bin</environment_variable>
        <!-- OSRA_DATA_FILES is only used by the galaxy wrapper and is not part of OSRA -->
        <environment_variable action="set_to" name="OSRA_DATA_FILES">$INSTALL_DIR/share</environment_variable>
    </action>

    The above tag will produce an env.sh file for version 2.0.0 of the osra package when it it installed into Galaxy that looks something like this.  Notice
    that the path to the gmagick binary is included here since it expands the defined $ENV[GRAPHICSMAGICK_ROOT_DIR] value in the above tag set.

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
    # env_var_value is the text of an environment variable tag like this: <environment_variable action="prepend_to" name="LD_LIBRARY_PATH">
    # Here is an example of what env_var_value could look like: $ENV[GRAPHICSMAGICK_ROOT_DIR]/lib/
    if '$ENV[' in env_var_value and ']' in env_var_value:
        # Pull out the name of the environment variable to populate.
        inherited_env_var_name = env_var_value.split( '[' )[1].split( ']' )[0]
        to_replace = '$ENV[%s]' % inherited_env_var_name
        # Build a command line that outputs VARIABLE_NAME: <the value of the variable>.
        set_prior_environment_commands.append( 'echo "%s: $%s"' % ( inherited_env_var_name, inherited_env_var_name ) )
        command = ' ; '.join( set_prior_environment_commands )
        # Run the command and capture the output.
        command_return = handle_command( app, tool_dependency, install_dir, command, return_output=True )
        # And extract anything labeled with the name of the environment variable we're populating here.
        if '%s: ' % inherited_env_var_name in command_return:
            environment_variable_value = command_return.split( '\n' )
            for line in environment_variable_value:
                if line.startswith( inherited_env_var_name ):
                    inherited_env_var_value = line.replace( '%s: ' % inherited_env_var_name, '' )
                    log.info( 'Replacing %s with %s in env.sh for this repository.', to_replace, inherited_env_var_value )
                    env_var_value = env_var_value.replace( to_replace, inherited_env_var_value )
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
            try:
                dir = td_common_util.url_download( work_dir, downloaded_filename, VIRTUALENV_URL )
            except:
                log.error( "Failed to download virtualenv: td_common_util.url_download( '%s', '%s', '%s' ) threw an exception", work_dir, downloaded_filename, VIRTUALENV_URL )
                return False
            full_path_to_dir = os.path.abspath( os.path.join( work_dir, dir ) )
            shutil.move( full_path_to_dir, venv_dir )
    return True

def install_and_build_package( app, tool_dependency, actions_dict ):
    """Install a Galaxy tool dependency package either via a url or a mercurial or git clone command."""
    install_dir = actions_dict[ 'install_dir' ]
    package_name = actions_dict[ 'package_name' ]
    actions = actions_dict.get( 'actions', None )
    filtered_actions = []
    install_environment = InstallEnvironment()
    if actions:
        with make_tmp_dir() as work_dir:
            with lcd( work_dir ):
                # The first action in the list of actions will be the one that defines the installation process.  There
                # are currently three supported processes; download_binary, download_by_url and clone via a "shell_command"
                # action type.
                action_type, action_dict = actions[ 0 ]
                if action_type == 'download_binary':
                    url = action_dict[ 'url' ]
                    # Get the target directory for this download, if the user has specified one. Default to the root of $INSTALL_DIR.
                    target_directory = action_dict.get( 'target_directory', None )
                    # Attempt to download a binary from the specified URL.
                    log.debug( 'Attempting to download from %s to %s', url, str( target_directory ) )
                    downloaded_filename = None
                    try:
                        downloaded_filename = td_common_util.download_binary( url, work_dir )
                        # Filter out any actions that are not download_binary, chmod, or set_environment.
                        filtered_actions = filter_actions_after_binary_installation( actions[ 1: ] )
                        # Set actions to the same, so that the current download_binary doesn't get re-run in the
                        # filtered actions below.
                        actions = filtered_actions
                    except Exception, e:
                        log.exception( str( e ) )
                        # No binary exists, or there was an error downloading the binary from the generated URL.
                        # Proceed with the remaining actions.
                        filtered_actions = actions[ 1: ]
                        action_type, action_dict = filtered_actions[ 0 ]
                    # If the downloaded file exists, move it to $INSTALL_DIR. Put this outside the try/catch above so that
                    # any errors in the move step are correctly sent to the tool dependency error handler.
                    if downloaded_filename and os.path.exists( os.path.join( work_dir, downloaded_filename ) ):
                        if target_directory:
                            target_directory = os.path.realpath( os.path.normpath( os.path.join( install_dir, target_directory ) ) )
                            # Make sure the target directory is not outside of $INSTALL_DIR.
                            if target_directory.startswith( os.path.realpath( install_dir ) ):
                                full_path_to_dir = os.path.abspath( os.path.join( install_dir, target_directory ) )
                            else:
                                full_path_to_dir = os.path.abspath( install_dir )
                        else:
                            full_path_to_dir = os.path.abspath( install_dir )
                        td_common_util.move_file( current_dir=work_dir,
                                                  source=downloaded_filename,
                                                  destination=full_path_to_dir )
                if action_type == 'download_by_url':
                    # Eliminate the download_by_url action so remaining actions can be processed correctly.
                    filtered_actions = actions[ 1: ]
                    url = action_dict[ 'url' ]
                    is_binary = action_dict.get( 'is_binary', False )
                    log.debug( 'Attempting to download via url: %s', url )
                    if 'target_filename' in action_dict:
                        # Sometimes compressed archives extract their content to a folder other than the default
                        # defined file name.  Using this attribute will ensure that the file name is set appropriately
                        # and can be located after download, decompression and extraction.
                        downloaded_filename = action_dict[ 'target_filename' ]
                    else:
                        downloaded_filename = os.path.split( url )[ -1 ]
                    dir = td_common_util.url_download( work_dir, downloaded_filename, url, extract=True )
                    if is_binary:
                        log_file = os.path.join( install_dir, INSTALLATION_LOG )
                        if os.path.exists( log_file ):
                            logfile = open( log_file, 'ab' )
                        else:
                            logfile = open( log_file, 'wb' )
                        logfile.write( 'Successfully downloaded from url: %s\n' % action_dict[ 'url' ] )
                        logfile.close()
                    log.debug( 'Successfully downloaded from url: %s' % action_dict[ 'url' ] )
                elif action_type == 'shell_command':
                    # <action type="shell_command">git clone --recursive git://github.com/ekg/freebayes.git</action>
                    # Eliminate the shell_command clone action so remaining actions can be processed correctly.
                    filtered_actions = actions[ 1: ]
                    return_code = handle_command( app, tool_dependency, install_dir, action_dict[ 'command' ] )
                    if return_code:
                         return tool_dependency
                    dir = package_name
                elif action_type == 'download_file':
                    # <action type="download_file">http://effectors.org/download/version/TTSS_GUI-1.0.1.jar</action>
                    # Download a single file to the working directory.
                    filtered_actions = actions[ 1: ]
                    url = action_dict[ 'url' ]
                    if 'target_filename' in action_dict:
                        # Sometimes compressed archives extracts their content to a folder other than the default
                        # defined file name.  Using this attribute will ensure that the file name is set appropriately
                        # and can be located after download, decompression and extraction.
                        filename = action_dict[ 'target_filename' ]
                    else:
                        filename = url.split( '/' )[ -1 ]
                    td_common_util.url_download( work_dir, filename, url )
                    dir = os.path.curdir
                elif action_type == 'setup_r_environment':
                    # setup an R environment
                    # <action type="setup_r_environment">
                    #       <repository name="package_r_3_0_1" owner="bgruening">
                    #           <package name="R" version="3.0.1" />
                    #       </repository>
                    #       <!-- allow installing an R packages -->
                    #       <package>https://github.com/bgruening/download_store/raw/master/DESeq2-1_0_18/BiocGenerics_0.6.0.tar.gz</package>
                    # </action>
                    filtered_actions = actions[ 1: ]
                    env_shell_file_paths = action_dict.get( 'env_shell_file_paths', None )
                    if env_shell_file_paths is None:
                        log.debug( 'Missing R environment. Please check your specified R installation exists.' )
                        return tool_dependency
                    else:
                        install_environment.add_env_shell_file_paths( env_shell_file_paths )
                    log.debug( 'Handling setup_r_environment for tool dependency %s with install_environment.env_shell_file_paths:\n%s"' % \
                               ( str( tool_dependency.name ), str( install_environment.env_shell_file_paths ) ) )
                    tarball_names = []
                    for url in action_dict[ 'r_packages' ]:
                        filename = url.split( '/' )[ -1 ]
                        tarball_names.append( filename )
                        td_common_util.url_download( work_dir, filename, url, extract=False )
                    dir = os.path.curdir
                    current_dir = os.path.abspath( os.path.join( work_dir, dir ) )
                    with lcd( current_dir ):
                        with settings( warn_only=True ):
                            for tarball_name in tarball_names:
                                cmd = '''PATH=$PATH:$R_HOME/bin; export PATH; R_LIBS=$INSTALL_DIR; export R_LIBS;
                                    Rscript -e "install.packages(c('%s'),lib='$INSTALL_DIR', repos=NULL, dependencies=FALSE)"''' % ( str( tarball_name ) )
                                cmd = install_environment.build_command( td_common_util.evaluate_template( cmd, install_dir ) )
                                return_code = handle_command( app, tool_dependency, install_dir, cmd )
                                if return_code:
                                    return tool_dependency
                            # R libraries are installed to $INSTALL_DIR (install_dir), we now set the R_LIBS path to that directory
                            env_file_builder = EnvFileBuilder( install_dir )
                            # Pull in R environment (runtime).
                            handle_action_shell_file_paths( env_file_builder, action_dict )
                            env_file_builder.append_line( name="R_LIBS", action="prepend_to", value=install_dir )
                            return_code = env_file_builder.return_code
                            if return_code:
                                return tool_dependency
                elif action_type == 'setup_ruby_environment':
                    # setup an Ruby environment
                    # <action type="setup_ruby_environment">
                    #       <repository name="package_ruby_2_0" owner="bgruening">
                    #           <package name="ruby" version="2.0" />
                    #       </repository>
                    #       <!-- allow downloading and installing an Ruby package from http://rubygems.org/ -->
                    #       <package>protk</package>
                    #       <package>protk=1.2.4</package>
                    #       <package>http://url-to-some-gem-file.de/protk.gem</package>
                    # </action>
                    filtered_actions = actions[ 1: ]
                    env_shell_file_paths = action_dict.get( 'env_shell_file_paths', None )
                    if env_shell_file_paths is None:
                        log.debug( 'Missing Ruby environment, make sure your specified Ruby installation exists.' )
                        return tool_dependency
                    else:
                        install_environment.add_env_shell_file_paths( env_shell_file_paths )
                    log.debug( 'Handling setup_ruby_environment for tool dependency %s with install_environment.env_shell_file_paths:\n%s"' % \
                               ( str( tool_dependency.name ), str( install_environment.env_shell_file_paths ) ) )
                    dir = os.path.curdir
                    current_dir = os.path.abspath( os.path.join( work_dir, dir ) )
                    with lcd( current_dir ):
                        with settings( warn_only=True ):
                            ruby_package_tups = action_dict.get( 'ruby_package_tups', [] )
                            for ruby_package_tup in ruby_package_tups:
                                gem, gem_version = ruby_package_tup
                                if os.path.isfile( gem ):
                                    # we assume a local shipped gem file
                                    cmd = '''PATH=$PATH:$RUBY_HOME/bin; export PATH; GEM_HOME=$INSTALL_DIR; export GEM_HOME;
                                            gem install --local %s''' % ( gem )
                                elif gem.find( '://' ) != -1:
                                    # We assume a URL to a gem file.
                                    url = gem
                                    gem_name = url.split( '/' )[ -1 ]
                                    td_common_util.url_download( work_dir, gem_name, url, extract=False )
                                    cmd = '''PATH=$PATH:$RUBY_HOME/bin; export PATH; GEM_HOME=$INSTALL_DIR; export GEM_HOME;
                                            gem install --local %s ''' % ( gem_name )
                                else:
                                    # gem file from rubygems.org with or without version number
                                    if gem_version:
                                        # version number was specified
                                        cmd = '''PATH=$PATH:$RUBY_HOME/bin; export PATH; GEM_HOME=$INSTALL_DIR; export GEM_HOME;
                                            gem install %s --version "=%s"''' % ( gem, gem_version)
                                    else:
                                        # no version number given
                                        cmd = '''PATH=$PATH:$RUBY_HOME/bin; export PATH; GEM_HOME=$INSTALL_DIR; export GEM_HOME;
                                            gem install %s''' % ( gem )
                                cmd = install_environment.build_command( td_common_util.evaluate_template( cmd, install_dir ) )
                                return_code = handle_command( app, tool_dependency, install_dir, cmd )
                                if return_code:
                                    return tool_dependency
                            env_file_builder = EnvFileBuilder( install_dir )
                            # Pull in ruby dependencies (runtime).
                            handle_action_shell_file_paths( env_file_builder, action_dict )
                            env_file_builder.append_line( name="GEM_PATH", action="prepend_to", value=install_dir )
                            env_file_builder.append_line( name="PATH", action="prepend_to", value=os.path.join(install_dir, 'bin') )
                            return_code = env_file_builder.return_code
                            if return_code:
                                return tool_dependency
                elif action_type == 'setup_perl_environment':
                    # setup an Perl environment
                    # <action type="setup_perl_environment">
                    #       <repository name="package_perl_5_18" owner="bgruening">
                    #           <package name="perl" version="5.18.1" />
                    #       </repository>
                    #       <!-- allow downloading and installing an Perl package from cpan.org-->
                    #       <package>XML::Parser</package>
                    #       <package>http://search.cpan.org/CPAN/authors/id/C/CJ/CJFIELDS/BioPerl-1.6.922.tar.gz</package>
                    # </action>
                    filtered_actions = actions[ 1: ]
                    env_shell_file_paths = action_dict.get( 'env_shell_file_paths', None )
                    if env_shell_file_paths is None:
                        log.debug( 'Missing Rerl environment, make sure your specified Rerl installation exists.' )
                        return tool_dependency
                    else:
                        install_environment.add_env_shell_file_paths( env_shell_file_paths )
                    log.debug( 'Handling setup_perl_environment for tool dependency %s with install_environment.env_shell_file_paths:\n%s"' % \
                               ( str( tool_dependency.name ), str( install_environment.env_shell_file_paths ) ) )
                    dir = os.path.curdir
                    current_dir = os.path.abspath( os.path.join( work_dir, dir ) )
                    with lcd( current_dir ):
                        with settings( warn_only=True ):
                            perl_packages = action_dict.get( 'perl_packages', [] )
                            for perl_package in perl_packages:
                                # If set to a true value then MakeMaker's prompt function will always
                                # return the default without waiting for user input.
                                cmd = '''PERL_MM_USE_DEFAULT=1; export PERL_MM_USE_DEFAULT; '''
                                if perl_package.find( '://' ) != -1:
                                    # We assume a URL to a gem file.
                                    url = perl_package
                                    perl_package_name = url.split( '/' )[ -1 ]
                                    dir = td_common_util.url_download( work_dir, perl_package_name, url, extract=True )
                                    # Search for Build.PL or Makefile.PL (ExtUtils::MakeMaker vs. Module::Build).
                                    tmp_work_dir = os.path.join( work_dir, dir )
                                    if os.path.exists( os.path.join( tmp_work_dir, 'Makefile.PL' ) ):
                                        cmd += '''perl Makefile.PL INSTALL_BASE=$INSTALL_DIR && make && make install'''
                                    elif os.path.exists( os.path.join( tmp_work_dir, 'Build.PL' ) ):
                                        cmd += '''perl Build.PL --install_base $INSTALL_DIR && perl Build && perl Build install'''
                                    else:
                                        log.debug( 'No Makefile.PL or Build.PL file found in %s. Skipping installation of %s.' % ( url, perl_package_name ) )
                                        return tool_dependency
                                    with lcd( tmp_work_dir ):
                                        cmd = install_environment.build_command( td_common_util.evaluate_template( cmd, install_dir ) )
                                        return_code = handle_command( app, tool_dependency, install_dir, cmd )
                                        if return_code:
                                            return tool_dependency
                                else:
                                    # perl package from CPAN without version number.
                                    # cpanm should be installed with the parent perl distribution, otherwise this will not work.
                                    cmd += '''cpanm --local-lib=$INSTALL_DIR %s''' % ( perl_package )
                                    cmd = install_environment.build_command( td_common_util.evaluate_template( cmd, install_dir ) )
                                    return_code = handle_command( app, tool_dependency, install_dir, cmd )
                                    if return_code:
                                        return tool_dependency
                            env_file_builder = EnvFileBuilder( install_dir )
                            # Pull in perl dependencies (runtime).
                            handle_action_shell_file_paths( env_file_builder, action_dict )
                            # Recursively add dependent PERL5LIB and PATH to env.sh & anything else needed.
                            env_file_builder.append_line( name="PERL5LIB", action="prepend_to", value=os.path.join( install_dir, 'lib', 'perl5' ) )
                            env_file_builder.append_line( name="PATH", action="prepend_to", value=os.path.join( install_dir, 'bin' ) )
                            return_code = env_file_builder.return_code
                            if return_code:
                                return tool_dependency
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
                for action_tup in filtered_actions:
                    current_dir = os.path.abspath( os.path.join( work_dir, dir ) )
                    with lcd( current_dir ):
                        action_type, action_dict = action_tup
                        if action_type == 'make_directory':
                            if os.path.isabs( action_dict[ 'full_path' ] ):
                                full_path = action_dict[ 'full_path' ]
                            else:
                                full_path = os.path.join( current_dir, action_dict[ 'full_path' ] )
                            td_common_util.make_directory( full_path=full_path )
                        elif action_type == 'move_directory_files':
                            td_common_util.move_directory_files( current_dir=current_dir,
                                                                 source_dir=os.path.join( action_dict[ 'source_directory' ] ),
                                                                 destination_dir=os.path.join( action_dict[ 'destination_directory' ] ) )
                        elif action_type == 'move_file':
                            td_common_util.move_file( current_dir=current_dir,
                                                      source=os.path.join( action_dict[ 'source' ] ),
                                                      destination=os.path.join( action_dict[ 'destination' ] ),
                                                      rename_to=action_dict[ 'rename_to' ] )
                        elif action_type == 'set_environment':
                            # Currently the only action supported in this category is "environment_variable".
                            # Build a command line from the prior_installation_required, in case an environment variable is referenced
                            # in the set_environment action.
                            cmds = install_environment.environment_commands( 'set_environment' )
                            env_var_dicts = action_dict[ 'environment_variable' ]
                            env_file_builder = EnvFileBuilder( install_dir )
                            for env_var_dict in env_var_dicts:
                                # Check for the presence of the $ENV[] key string and populate it if possible.
                                env_var_dict = handle_environment_variables( app, tool_dependency, install_dir, env_var_dict, cmds )
                                env_file_builder.append_line( **env_var_dict )
                            return_code = env_file_builder.return_code
                            if return_code:
                                return tool_dependency
                        elif action_type == 'set_environment_for_install':
                            # Currently the only action supported in this category is a list of paths to one or more tool dependency env.sh files,
                            # the environment setting in each of which will be injected into the environment for all <action type="shell_command">
                            # tags that follow this <action type="set_environment_for_install"> tag set in the tool_dependencies.xml file.
                            install_environment.add_env_shell_file_paths( action_dict[ 'env_shell_file_paths' ] )
                        elif action_type == 'setup_virtualenv':
                            # TODO: maybe should be configurable
                            venv_src_directory = os.path.abspath( os.path.join( app.config.tool_dependency_dir, '__virtualenv_src' ) )
                            if not install_virtualenv( app, venv_src_directory ):
                                log.error( 'Unable to install virtualenv' )
                                return tool_dependency
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
                            install_command = "python '%s' install -r '%s'" % ( os.path.join( venv_directory, "bin", "pip" ), requirements_path )
                            full_setup_command = "%s; %s; %s" % ( setup_command, activate_command, install_command )
                            return_code = handle_command( app, tool_dependency, install_dir, full_setup_command )
                            if return_code:
                                return tool_dependency
                            site_packages_command = "%s -c 'import os, sys; print os.path.join(sys.prefix, \"lib\", \"python\" + sys.version[:3], \"site-packages\")'" % os.path.join( venv_directory, "bin", "python" )
                            output = handle_command( app, tool_dependency, install_dir, site_packages_command, return_output=True )
                            if output.return_code:
                                return tool_dependency
                            if not os.path.exists( output.stdout ):
                                log.debug( "virtualenv's site-packages directory '%s' does not exist", output.stdout )
                                return tool_dependency
                            env_file_builder = EnvFileBuilder( install_dir )
                            env_file_builder.append_line( name="PYTHONPATH", action="prepend_to", value=output.stdout )
                            env_file_builder.append_line( name="PATH", action="prepend_to", value=os.path.join( venv_directory, "bin" ) )
                            return_code = env_file_builder.return_code
                            if return_code:
                                return tool_dependency
                        elif action_type == 'shell_command':
                            with settings( warn_only=True ):
                                cmd = install_environment.build_command( action_dict[ 'command' ] )
                                return_code = handle_command( app, tool_dependency, install_dir, cmd )
                                if return_code:
                                    return tool_dependency
                        elif action_type == 'template_command':
                            env_vars = dict()
                            env_vars = install_environment.environment_dict()
                            env_vars.update( td_common_util.get_env_var_values( install_dir ) )
                            language = action_dict[ 'language' ]
                            with settings( warn_only=True, **env_vars ):
                                if language == 'cheetah':
                                    # We need to import fabric.api.env so that we can access all collected environment variables.
                                    cmd = fill_template( '#from fabric.api import env\n%s' % action_dict[ 'command' ], context=env_vars )
                                    return_code = handle_command( app, tool_dependency, install_dir, cmd )
                                    if return_code:
                                        return tool_dependency
                        elif action_type == 'make_install':
                            # make; make install; allow providing make options
                            with settings( warn_only=True ):
                                make_opts = action_dict.get( 'make_opts', '' )
                                cmd = install_environment.build_command( 'make %s && make install' % make_opts )
                                return_code = handle_command( app, tool_dependency, install_dir, cmd )
                                if return_code:
                                    return tool_dependency
                        elif action_type == 'autoconf':
                            # Handle configure, make and make install allow providing configuration options
                            with settings( warn_only=True ):
                                configure_opts = action_dict.get( 'configure_opts', '' )
                                if 'prefix=' in configure_opts:
                                    pre_cmd = './configure %s && make && make install' % configure_opts
                                else:
                                    pre_cmd = './configure --prefix=$INSTALL_DIR %s && make && make install' % configure_opts
                                cmd = install_environment.build_command( td_common_util.evaluate_template( pre_cmd, install_dir ) )
                                return_code = handle_command( app, tool_dependency, install_dir, cmd )
                                if return_code:
                                    return tool_dependency
                        elif action_type == 'download_file':
                            # Download a single file to the current working directory.
                            url = action_dict[ 'url' ]
                            if 'target_filename' in action_dict:
                                filename = action_dict[ 'target_filename' ]
                            else:
                                filename = url.split( '/' )[ -1 ]
                            extract = action_dict.get( 'extract', False )
                            td_common_util.url_download( current_dir, filename, url, extract=extract )
                        elif action_type == 'change_directory':
                            target_directory = os.path.realpath( os.path.normpath( os.path.join( current_dir, action_dict[ 'directory' ] ) ) )
                            if target_directory.startswith( os.path.realpath( current_dir ) ) and os.path.exists( target_directory ):
                                # Change directory to a directory within the current working directory.
                                dir = target_directory
                            elif target_directory.startswith( os.path.realpath( work_dir ) ) and os.path.exists( target_directory ):
                                # Change directory to a directory above the current working directory, but within the defined work_dir.
                                dir = target_directory.replace( os.path.realpath( work_dir ), '' ).lstrip( '/' )
                            else:
                                log.error( 'Invalid or nonexistent directory %s specified, ignoring change_directory action.', target_directory )
                        elif action_type == 'chmod':
                            for target_file, mode in action_dict[ 'change_modes' ]:
                                if os.path.exists( target_file ):
                                    os.chmod( target_file, mode )
                                else:
                                    log.error( 'Invalid file %s specified, ignoring %s action.', target_file, action_type )
                        elif action_type == 'download_binary':
                            url = action_dict[ 'url' ]
                            target_directory = action_dict.get( 'target_directory', None )
                            try:
                                downloaded_filename = td_common_util.download_binary( url, work_dir )
                            except Exception, e:
                                log.exception( str( e ) )
                            # If the downloaded file exists, move it to $INSTALL_DIR. Put this outside the try/catch above so that
                            # any errors in the move step are correctly sent to the tool dependency error handler.
                            if downloaded_filename and os.path.exists( os.path.join( work_dir, downloaded_filename ) ):
                                if target_directory:
                                    target_directory = os.path.realpath( os.path.normpath( os.path.join( install_dir, target_directory ) ) )
                                    # Make sure the target directory is not outside of $INSTALL_DIR.
                                    if target_directory.startswith( os.path.realpath( install_dir ) ):
                                        full_path_to_dir = os.path.abspath( os.path.join( install_dir, target_directory ) )
                                    else:
                                        full_path_to_dir = os.path.abspath( install_dir )
                                else:
                                    full_path_to_dir = os.path.abspath( install_dir )
                                td_common_util.move_file( current_dir=work_dir,
                                                          source=downloaded_filename,
                                                          destination=full_path_to_dir )
    return tool_dependency

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
    work_dir = tempfile.mkdtemp( prefix="tmp-toolshed-mtd" )
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
