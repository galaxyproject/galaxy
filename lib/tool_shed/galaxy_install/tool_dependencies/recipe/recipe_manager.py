import logging
import os
import Queue
import shutil
import stat
import subprocess
import tempfile
import threading
import time

from contextlib import contextmanager

# TODO: eliminate the use of fabric here.
from galaxy import eggs

eggs.require( 'paramiko' )
eggs.require( 'ssh' )
eggs.require( 'Fabric' )

from fabric.operations import _AttributeString
from fabric import state
from fabric.api import prefix

from galaxy.util import DATABASE_MAX_STRING_SIZE
from galaxy.util import DATABASE_MAX_STRING_SIZE_PRETTY
from galaxy.util import shrink_string_by_size
from galaxy.util import unicodify

from tool_shed.galaxy_install.tool_dependencies import td_common_util
from tool_shed.galaxy_install.tool_dependencies.recipe import step_handler

log = logging.getLogger( __name__ )


class AsynchronousReader( threading.Thread ):
    """
    A helper class to implement asynchronous reading of a stream in a separate thread.  Read lines are pushed
    onto a queue to be consumed in another thread.
    """
 
    def __init__( self, fd, queue ):
        threading.Thread.__init__( self )
        self._fd = fd
        self._queue = queue
        self.lines = []
 
    def run( self ):
        """Read lines and put them on the queue."""
        thread_lock = threading.Lock()
        thread_lock.acquire()
        for line in iter( self._fd.readline, '' ):
            stripped_line = line.rstrip()
            self.lines.append( stripped_line )
            self._queue.put( stripped_line )
        thread_lock.release()
 
    def installation_complete( self ):
        """Make sure there is more installation and compilation logging content expected."""
        return not self.is_alive() and self._queue.empty()


class EnvFileBuilder( object ):

    def __init__( self, install_dir ):
        self.install_dir = install_dir
        self.return_code = 0

    def append_line( self, make_executable=True, **kwd ):
        env_var_dict = dict( **kwd )
        env_entry, env_file = self.create_or_update_env_shell_file( self.install_dir, env_var_dict )
        return_code = self.file_append( env_entry, env_file, make_executable=make_executable )
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

    def file_append( self, text, file_path, make_executable=True ):
        """
        Append a line to a file unless the line already exists in the file.  This method creates the file if
        it doesn't exist.  If make_executable is True, the permissions on the file are set to executable by
        the owner.
        """
        file_dir = os.path.dirname( file_path )
        if not os.path.exists( file_dir ):
            try:
                os.makedirs( file_dir )
            except Exception, e:
                log.exception( str( e ) )
                return 1
        if os.path.exists( file_path ):
            try:
                new_env_file_contents = []
                env_file_contents = file( file_path, 'r' ).readlines()
                # Clean out blank lines from the env.sh file.
                for line in env_file_contents:
                    line = line.rstrip()
                    if line:
                        new_env_file_contents.append( line )
                env_file_contents = new_env_file_contents
            except Exception, e:
                log.exception( str( e ) )
                return 1
        else:
            env_file_handle = open( file_path, 'w' )
            env_file_handle.close()
            env_file_contents = []
        if make_executable:
            # Explicitly set the file's executable bits.
            try:
                os.chmod( file_path, int( '111', base=8 ) | os.stat( file_path )[ stat.ST_MODE ] )
            except Exception, e:
                log.exception( str( e ) )
                return 1
        # Convert the received text to a list, in order to support adding one or more lines to the file.
        if isinstance( text, basestring ):
            text = [ text ]
        for line in text:
            line = line.rstrip()
            if line and line not in env_file_contents:
                env_file_contents.append( line )
        try:
            file( file_path, 'w' ).write( '\n'.join( env_file_contents ) )
        except Exception, e:
            log.exception( str( e ) )
            return 1
        return 0

    def handle_action_shell_file_paths( self, action_dict ):
        shell_file_paths = action_dict.get( 'action_shell_file_paths', [] )
        for shell_file_path in shell_file_paths:
            self.append_line( action="source", value=shell_file_path )


class InstallEnvironment( object ):
    """Object describing the environment built up as part of the process of building and installing a package."""


    def __init__( self ):
        self.env_shell_file_paths = []

    def __call__( self, install_dir ):
        with settings( warn_only=True, **td_common_util.get_env_var_values( install_dir ) ):
            with prefix( self.__setup_environment() ):
                yield

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

    def close_file_descriptor( self, fd ):
        """Attempt to close a file descriptor."""
        start_timer = time.time()
        error = ''
        while True:
            try:
                fd.close()
                break
            except IOError, e:
                # Undoubtedly close() was called during a concurrent operation on the same file object.
                log.debug( 'Error closing file descriptor: %s' % str( e ) )
                time.sleep( .5 )
            current_wait_time = time.time() - start_timer
            if current_wait_time >= 600:
                error = 'Error closing file descriptor: %s' % str( e )
                break
        return error

    def enqueue_output( self, stdout, stdout_queue, stderr, stderr_queue ):
        """
        This method places streamed stdout and stderr into a threaded IPC queue target.  Received data
        is printed and saved to that thread's queue. The calling thread can then retrieve the data using
        thread.stdout and thread.stderr.
        """
        stdout_logger = logging.getLogger( 'fabric_util.STDOUT' )
        stderr_logger = logging.getLogger( 'fabric_util.STDERR' )
        for line in iter( stdout.readline, '' ):
            output = line.rstrip()
            stdout_logger.debug( output )
            stdout_queue.put( output )
        stdout_queue.put( None )
        for line in iter( stderr.readline, '' ):
            output = line.rstrip()
            stderr_logger.debug( output )
            stderr_queue.put( output )
        stderr_queue.put( None )

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

    def handle_command( self, app, tool_dependency, install_dir, cmd, return_output=False ):
        """Handle a command and log the results."""
        context = app.install_model.context
        command = str( cmd )
        output = self.handle_complex_command( command )
        self.log_results( cmd, output, os.path.join( install_dir, td_common_util.INSTALLATION_LOG ) )
        stdout = output.stdout
        stderr = output.stderr
        if len( stdout ) > DATABASE_MAX_STRING_SIZE:
            print "Length of stdout > %s, so only a portion will be saved in the database." % str( DATABASE_MAX_STRING_SIZE_PRETTY )
            stdout = shrink_string_by_size( stdout, DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True )
        if len( stderr ) > DATABASE_MAX_STRING_SIZE:
            print "Length of stderr > %s, so only a portion will be saved in the database." % str( DATABASE_MAX_STRING_SIZE_PRETTY )
            stderr = shrink_string_by_size( stderr, DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True )
        if output.return_code not in [ 0 ]:
            tool_dependency.status = app.install_model.ToolDependency.installation_status.ERROR
            if stderr:
                tool_dependency.error_message = unicodify( stderr )
            elif stdout:
                tool_dependency.error_message = unicodify( stdout )
            else:
                # We have a problem if there was no stdout and no stderr.
                tool_dependency.error_message = "Unknown error occurred executing shell command %s, return_code: %s"  % \
                    ( str( cmd ), str( output.return_code ) )
            context.add( tool_dependency )
            context.flush()
        if return_output:
            return output
        return output.return_code

    def handle_complex_command( self, command ):
        """
        Wrap subprocess.Popen in such a way that the stderr and stdout from running a shell command will
        be captured and logged in nearly real time.  This is similar to fabric.local, but allows us to
        retain control over the process.  This method is named "complex" because it uses queues and
        threads to execute a command while capturing and displaying the output.
        """
        # Launch the command as subprocess.  A bufsize of 1 means line buffered.
        process_handle = subprocess.Popen( str( command ),
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           bufsize=1,
                                           close_fds=False,
                                           shell=True,
                                           cwd=state.env[ 'lcwd' ] )
        pid = process_handle.pid
        # Launch the asynchronous readers of the process' stdout and stderr.
        stdout_queue = Queue.Queue()
        stdout_reader = AsynchronousReader( process_handle.stdout, stdout_queue )
        stdout_reader.start()
        stderr_queue = Queue.Queue()
        stderr_reader = AsynchronousReader( process_handle.stderr, stderr_queue )
        stderr_reader.start()
        # Place streamed stdout and stderr into a threaded IPC queue target so it can
        # be printed and stored for later retrieval when generating the INSTALLATION.log.
        stdio_thread = threading.Thread( target=self.enqueue_output,
                                         args=( process_handle.stdout,
                                                stdout_queue,
                                                process_handle.stderr,
                                                stderr_queue ) )
        thread_lock = threading.Lock()
        thread_lock.acquire()
        stdio_thread.start()
        # Check the queues for output until there is nothing more to get.
        start_timer = time.time()
        while not stdout_reader.installation_complete() or not stderr_reader.installation_complete():
            # Show what we received from standard output.
            while not stdout_queue.empty():
                try:
                    line = stdout_queue.get()
                except Queue.Empty:
                    line = None
                    break
                if line:
                    print line
                    start_timer = time.time()
                else:
                    break
            # Show what we received from standard error.
            while not stderr_queue.empty():
                try:
                    line = stderr_queue.get()
                except Queue.Empty:
                    line = None
                    break
                if line:
                    print line
                    start_timer = time.time()
                else:
                    stderr_queue.task_done()
                    break
            # Sleep a bit before asking the readers again.
            time.sleep( .1 )
            current_wait_time = time.time() - start_timer
            if stdout_queue.empty() and stderr_queue.empty() and current_wait_time > td_common_util.NO_OUTPUT_TIMEOUT:
                err_msg = "\nShutting down process id %s because it generated no output for the defined timeout period of %.1f seconds.\n" % \
                        ( pid, td_common_util.NO_OUTPUT_TIMEOUT )
                stderr_reader.lines.append( err_msg )
                process_handle.kill()
                break
        thread_lock.release()
        # Wait until each of the threads we've started terminate.  The following calls will block each thread
        # until it terminates either normally, through an unhandled exception, or until the timeout occurs.
        stdio_thread.join( td_common_util.NO_OUTPUT_TIMEOUT )
        stdout_reader.join( td_common_util.NO_OUTPUT_TIMEOUT )
        stderr_reader.join( td_common_util.NO_OUTPUT_TIMEOUT )
        # Close subprocess' file descriptors.
        error = self.close_file_descriptor( process_handle.stdout )
        error = self.close_file_descriptor( process_handle.stderr )
        stdout = '\n'.join( stdout_reader.lines )
        stderr = '\n'.join( stderr_reader.lines )
        # Handle error condition (deal with stdout being None, too)
        output = _AttributeString( stdout.strip() if stdout else "" )
        errors = _AttributeString( stderr.strip() if stderr else "" )
        # Make sure the process has finished.
        process_handle.poll()
        output.return_code = process_handle.returncode
        output.stderr = errors
        return output

    def log_results( self, command, fabric_AttributeString, file_path ):
        """Write attributes of fabric.operations._AttributeString to a specified log file."""
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
    def make_tmp_dir( self ):
        work_dir = tempfile.mkdtemp( prefix="tmp-toolshed-mtd" )
        yield work_dir
        if os.path.exists( work_dir ):
            try:
                shutil.rmtree( work_dir )
            except Exception, e:
                log.exception( str( e ) )

    def __setup_environment( self ):
        return "&&".join( [ ". %s" % file for file in self.__valid_env_shell_file_paths() ] )

    def __valid_env_shell_file_paths( self ):
        return [ file for file in self.env_shell_file_paths if os.path.exists( file ) ]


class RecipeManager( object ):

    def __init__( self ):
        self.step_handlers_by_type = self.load_step_handlers()

    def get_step_handler_by_type( self, type ):
        return self.step_handlers_by_type.get( type, None )

    def execute_step( self, app, tool_dependency, package_name, actions, action_type, action_dict, filtered_actions,
                      env_file_builder, install_environment, work_dir, install_dir, current_dir=None, initial_download=False ):
        if actions:
            step_handler = self.get_step_handler_by_type( action_type )
            tool_dependency, filtered_actions, dir = step_handler.execute_step( app=app,
                                                                                tool_dependency=tool_dependency,
                                                                                package_name=package_name,
                                                                                actions=actions,
                                                                                action_dict=action_dict,
                                                                                filtered_actions=filtered_actions,
                                                                                env_file_builder=env_file_builder,
                                                                                install_environment=install_environment,
                                                                                work_dir=work_dir,
                                                                                install_dir=install_dir,
                                                                                current_dir=current_dir,
                                                                                initial_download=initial_download )
        else:
            dir = None
        return tool_dependency, filtered_actions, dir

    def load_step_handlers( self ):
        step_handlers_by_type = dict( assert_directory_executable=step_handler.AssertDirectoryExecutable(),
                                      assert_directory_exists=step_handler.AssertDirectoryExists(),
                                      assert_file_executable=step_handler.AssertFileExecutable(),
                                      assert_file_exists=step_handler.AssertFileExists(),
                                      autoconf=step_handler.Autoconf(),
                                      change_directory=step_handler.ChangeDirectory(),
                                      chmod=step_handler.Chmod(),
                                      download_binary=step_handler.DownloadBinary(),
                                      download_by_url=step_handler.DownloadByUrl(),
                                      download_file=step_handler.DownloadFile(),
                                      make_directory=step_handler.MakeDirectory(),
                                      make_install=step_handler.MakeInstall(),
                                      move_directory_files=step_handler.MoveDirectoryFiles(),
                                      move_file=step_handler.MoveFile(),
                                      set_environment=step_handler.SetEnvironment(),
                                      set_environment_for_install=step_handler.SetEnvironmentForInstall(),
                                      setup_perl_environment=step_handler.SetupPerlEnvironment(),
                                      setup_r_environment=step_handler.SetupREnvironment(),
                                      setup_ruby_environment=step_handler.SetupRubyEnvironment(),
                                      setup_virtual_env=step_handler.SetupVirtualEnv(),
                                      shell_command=step_handler.ShellCommand(),
                                      template_command=step_handler.TemplateCommand() )
        return step_handlers_by_type

    def prepare_step( self, app, tool_dependency, action_type, action_elem, action_dict, install_dir, is_binary_download ):
        """
        Prepare the recipe step for later execution.  This generally alters the received action_dict
        with new information needed during this step's execution.
        """
        if action_elem is not None:
            step_handler = self.get_step_handler_by_type( action_type )
            action_dict = step_handler.prepare_step( app=app,
                                                     tool_dependency=tool_dependency,
                                                     action_elem=action_elem,
                                                     action_dict=action_dict,
                                                     install_dir=install_dir,
                                                     is_binary_download=is_binary_download )
        return action_dict
        