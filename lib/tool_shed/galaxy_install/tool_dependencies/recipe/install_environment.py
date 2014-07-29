import logging
import os
import Queue
import shutil
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

from tool_shed.galaxy_install.tool_dependencies.recipe import asynchronous_reader

from tool_shed.util import basic_util

log = logging.getLogger( __name__ )


class InstallEnvironment( object ):
    """Object describing the environment built up as part of the process of building and installing a package."""


    def __init__( self, app, tool_shed_repository_install_dir, install_dir  ):
        """
        The value of the received tool_shed_repository_install_dir is the root installation directory
        of the repository containing the tool dependency, and the value of the received install_dir is
        the root installation directory of the tool dependency.
        """
        self.app = app
        self.env_shell_file_paths = []
        self.install_dir = install_dir
        self.tool_shed_repository_install_dir = tool_shed_repository_install_dir

    def __call__( self ):
        with settings( warn_only=True, **basic_util.get_env_var_values( self ) ):
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
        stdout_logger = logging.getLogger( 'install_environment.STDOUT' )
        stderr_logger = logging.getLogger( 'install_environment.STDERR' )
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

    def handle_command( self, tool_dependency, cmd, return_output=False ):
        """Handle a command and log the results."""
        context = self.app.install_model.context
        command = str( cmd )
        output = self.handle_complex_command( command )
        self.log_results( cmd, output, os.path.join( self.install_dir, basic_util.INSTALLATION_LOG ) )
        stdout = output.stdout
        stderr = output.stderr
        if len( stdout ) > DATABASE_MAX_STRING_SIZE:
            print "Length of stdout > %s, so only a portion will be saved in the database." % str( DATABASE_MAX_STRING_SIZE_PRETTY )
            stdout = shrink_string_by_size( stdout, DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True )
        if len( stderr ) > DATABASE_MAX_STRING_SIZE:
            print "Length of stderr > %s, so only a portion will be saved in the database." % str( DATABASE_MAX_STRING_SIZE_PRETTY )
            stderr = shrink_string_by_size( stderr, DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True )
        if output.return_code not in [ 0 ]:
            tool_dependency.status = self.app.install_model.ToolDependency.installation_status.ERROR
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
        stdout_reader = asynchronous_reader.AsynchronousReader( process_handle.stdout, stdout_queue )
        stdout_reader.start()
        stderr_queue = Queue.Queue()
        stderr_reader = asynchronous_reader.AsynchronousReader( process_handle.stderr, stderr_queue )
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
            if stdout_queue.empty() and stderr_queue.empty() and current_wait_time > basic_util.NO_OUTPUT_TIMEOUT:
                err_msg = "\nShutting down process id %s because it generated no output for the defined timeout period of %.1f seconds.\n" % \
                        ( pid, basic_util.NO_OUTPUT_TIMEOUT )
                stderr_reader.lines.append( err_msg )
                process_handle.kill()
                break
        thread_lock.release()
        # Wait until each of the threads we've started terminate.  The following calls will block each thread
        # until it terminates either normally, through an unhandled exception, or until the timeout occurs.
        stdio_thread.join( basic_util.NO_OUTPUT_TIMEOUT )
        stdout_reader.join( basic_util.NO_OUTPUT_TIMEOUT )
        stderr_reader.join( basic_util.NO_OUTPUT_TIMEOUT )
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
