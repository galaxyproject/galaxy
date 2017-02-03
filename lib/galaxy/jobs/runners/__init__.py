"""
Base classes for job runner plugins.
"""

import os
import time
import string
import logging
import datetime
import threading
import subprocess

from Queue import Queue, Empty

import galaxy.jobs
from galaxy.jobs.command_factory import build_command
from galaxy import model
from galaxy.util import DATABASE_MAX_STRING_SIZE, shrink_stream_by_size
from galaxy.util import in_directory
from galaxy.util import ParamsWithSpecs
from galaxy.util import ExecutionTimer
from galaxy.util.bunch import Bunch
from galaxy.jobs.runners.util.job_script import write_script
from galaxy.jobs.runners.util.job_script import job_script
from galaxy.jobs.runners.util.env import env_to_statement

from .state_handler_factory import build_state_handlers

log = logging.getLogger( __name__ )

STOP_SIGNAL = object()


JOB_RUNNER_PARAMETER_UNKNOWN_MESSAGE = "Invalid job runner parameter for this plugin: %s"
JOB_RUNNER_PARAMETER_MAP_PROBLEM_MESSAGE = "Job runner parameter '%s' value '%s' could not be converted to the correct type"
JOB_RUNNER_PARAMETER_VALIDATION_FAILED_MESSAGE = "Job runner parameter %s failed validation"

GALAXY_LIB_ADJUST_TEMPLATE = """GALAXY_LIB="%s"; if [ "$GALAXY_LIB" != "None" ]; then if [ -n "$PYTHONPATH" ]; then PYTHONPATH="$GALAXY_LIB:$PYTHONPATH"; else PYTHONPATH="$GALAXY_LIB"; fi; export PYTHONPATH; fi;"""
GALAXY_VENV_TEMPLATE = """GALAXY_VIRTUAL_ENV="%s"; if [ "$GALAXY_VIRTUAL_ENV" != "None" -a -z "$VIRTUAL_ENV" -a -f "$GALAXY_VIRTUAL_ENV/bin/activate" ]; then . "$GALAXY_VIRTUAL_ENV/bin/activate"; fi;"""


class RunnerParams( ParamsWithSpecs ):

    def _param_unknown_error( self, name ):
        raise Exception( JOB_RUNNER_PARAMETER_UNKNOWN_MESSAGE % name )

    def _param_map_error( self, name, value ):
        raise Exception( JOB_RUNNER_PARAMETER_MAP_PROBLEM_MESSAGE % ( name, value ) )

    def _param_vaildation_error( self, name, value ):
        raise Exception( JOB_RUNNER_PARAMETER_VALIDATION_FAILED_MESSAGE % name )


class BaseJobRunner( object ):
    DEFAULT_SPECS = dict( recheck_missing_job_retries=dict( map=int, valid=lambda x: x >= 0, default=0 ) )

    def __init__( self, app, nworkers, **kwargs ):
        """Start the job runner
        """
        self.app = app
        self.sa_session = app.model.context
        self.nworkers = nworkers
        runner_param_specs = self.DEFAULT_SPECS.copy()
        if 'runner_param_specs' in kwargs:
            runner_param_specs.update( kwargs.pop( 'runner_param_specs' ) )
        if kwargs:
            log.debug( 'Loading %s with params: %s', self.runner_name, kwargs )
        self.runner_params = RunnerParams( specs=runner_param_specs, params=kwargs )
        self.runner_state_handlers = build_state_handlers()

    def _init_worker_threads(self):
        """Start ``nworkers`` worker threads.
        """
        self.work_queue = Queue()
        self.work_threads = []
        log.debug('Starting %s %s workers' % (self.nworkers, self.runner_name))
        for i in range(self.nworkers):
            worker = threading.Thread( name="%s.work_thread-%d" % (self.runner_name, i), target=self.run_next )
            worker.setDaemon( True )
            worker.start()
            self.work_threads.append( worker )

    def run_next(self):
        """Run the next item in the work queue (a job waiting to run)
        """
        while True:
            ( method, arg ) = self.work_queue.get()
            if method is STOP_SIGNAL:
                return
            # id and name are collected first so that the call of method() is the last exception.
            try:
                if isinstance(arg, AsynchronousJobState):
                    job_id = arg.job_wrapper.get_id_tag()
                else:
                    # arg should be a JobWrapper/TaskWrapper
                    job_id = arg.get_id_tag()
            except:
                job_id = 'unknown'
            try:
                name = method.__name__
            except:
                name = 'unknown'
            try:
                method(arg)
            except:
                log.exception( "(%s) Unhandled exception calling %s" % ( job_id, name ) )

    # Causes a runner's `queue_job` method to be called from a worker thread
    def put(self, job_wrapper):
        """Add a job to the queue (by job identifier), indicate that the job is ready to run.
        """
        put_timer = ExecutionTimer()
        job = job_wrapper.get_job()
        # Change to queued state before handing to worker thread so the runner won't pick it up again
        job_wrapper.change_state( model.Job.states.QUEUED, flush=False, job=job )
        # Persist the destination so that the job will be included in counts if using concurrency limits
        job_wrapper.set_job_destination( job_wrapper.job_destination, None, flush=False, job=job )
        self.sa_session.flush()
        self.mark_as_queued(job_wrapper)
        log.debug("Job [%s] queued %s" % (job_wrapper.job_id, put_timer))

    def mark_as_queued(self, job_wrapper):
        self.work_queue.put( ( self.queue_job, job_wrapper ) )

    def shutdown( self ):
        """Attempts to gracefully shut down the worker threads
        """
        log.info( "%s: Sending stop signal to %s worker threads" % ( self.runner_name, len( self.work_threads ) ) )
        for i in range( len( self.work_threads ) ):
            self.work_queue.put( ( STOP_SIGNAL, None ) )

    # Most runners should override the legacy URL handler methods and destination param method
    def url_to_destination(self, url):
        """
        Convert a legacy URL to a JobDestination.

        Job runner URLs are deprecated, JobDestinations should be used instead.
        This base class method converts from a URL to a very basic
        JobDestination without destination params.
        """
        return galaxy.jobs.JobDestination(runner=url.split(':')[0])

    def parse_destination_params(self, params):
        """Parse the JobDestination ``params`` dict and return the runner's native representation of those params.
        """
        raise NotImplementedError()

    def prepare_job(self, job_wrapper, include_metadata=False, include_work_dir_outputs=True,
                    modify_command_for_container=True):
        """Some sanity checks that all runners' queue_job() methods are likely to want to do
        """
        job_id = job_wrapper.get_id_tag()
        job_state = job_wrapper.get_state()
        job_wrapper.is_ready = False
        job_wrapper.runner_command_line = None

        # Make sure the job hasn't been deleted
        if job_state == model.Job.states.DELETED:
            log.debug( "(%s) Job deleted by user before it entered the %s queue" % ( job_id, self.runner_name ) )
            if self.app.config.cleanup_job in ( "always", "onsuccess" ):
                job_wrapper.cleanup()
            return False
        elif job_state != model.Job.states.QUEUED:
            log.info( "(%s) Job is in state %s, skipping execution" % ( job_id, job_state ) )
            # cleanup may not be safe in all states
            return False

        # Prepare the job
        try:
            job_wrapper.prepare()
            job_wrapper.runner_command_line = self.build_command_line(
                job_wrapper,
                include_metadata=include_metadata,
                include_work_dir_outputs=include_work_dir_outputs,
                modify_command_for_container=modify_command_for_container
            )
        except Exception as e:
            log.exception("(%s) Failure preparing job" % job_id)
            job_wrapper.fail( e.message if hasattr( e, 'message' ) else "Job preparation failed", exception=True )
            return False

        if not job_wrapper.runner_command_line:
            job_wrapper.finish( '', '' )
            return False

        return True

    # Runners must override the job handling methods
    def queue_job(self, job_wrapper):
        raise NotImplementedError()

    def stop_job(self, job):
        raise NotImplementedError()

    def recover(self, job, job_wrapper):
        raise NotImplementedError()

    def build_command_line( self, job_wrapper, include_metadata=False, include_work_dir_outputs=True,
                            modify_command_for_container=True ):
        container = self._find_container( job_wrapper )
        if not container and job_wrapper.requires_containerization:
            raise Exception("Failed to find a container when required, contact Galaxy admin.")
        return build_command(
            self,
            job_wrapper,
            include_metadata=include_metadata,
            include_work_dir_outputs=include_work_dir_outputs,
            modify_command_for_container=modify_command_for_container,
            container=container
        )

    def get_work_dir_outputs( self, job_wrapper, job_working_directory=None, tool_working_directory=None ):
        """
        Returns list of pairs (source_file, destination) describing path
        to work_dir output file and ultimate destination.
        """
        if tool_working_directory is not None and job_working_directory is not None:
            raise Exception("get_work_dir_outputs called with both a job and tool working directory, only one may be specified")

        if tool_working_directory is None:
            if not job_working_directory:
                job_working_directory = os.path.abspath( job_wrapper.working_directory )
            tool_working_directory = os.path.join(job_working_directory, "working")

        # Set up dict of dataset id --> output path; output path can be real or
        # false depending on outputs_to_working_directory
        output_paths = {}
        for dataset_path in job_wrapper.get_output_fnames():
            path = dataset_path.real_path
            if self.app.config.outputs_to_working_directory:
                path = dataset_path.false_path
            output_paths[ dataset_path.dataset_id ] = path

        output_pairs = []
        # Walk job's output associations to find and use from_work_dir attributes.
        job = job_wrapper.get_job()
        job_tool = job_wrapper.tool
        for (joda, dataset) in self._walk_dataset_outputs( job ):
            if joda and job_tool:
                hda_tool_output = job_tool.find_output_def( joda.name )
                if hda_tool_output and hda_tool_output.from_work_dir:
                    # Copy from working dir to HDA.
                    # TODO: move instead of copy to save time?
                    source_file = os.path.join( tool_working_directory, hda_tool_output.from_work_dir )
                    destination = job_wrapper.get_output_destination( output_paths[ dataset.dataset_id ] )
                    if in_directory( source_file, tool_working_directory ):
                        output_pairs.append( ( source_file, destination ) )
                    else:
                        # Security violation.
                        log.exception( "from_work_dir specified a location not in the working directory: %s, %s" % ( source_file, job_wrapper.working_directory ) )
        return output_pairs

    def _walk_dataset_outputs( self, job ):
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            for dataset in dataset_assoc.dataset.dataset.history_associations + dataset_assoc.dataset.dataset.library_associations:
                if isinstance( dataset, self.app.model.HistoryDatasetAssociation ):
                    joda = self.sa_session.query( self.app.model.JobToOutputDatasetAssociation ).filter_by( job=job, dataset=dataset ).first()
                    yield (joda, dataset)
        # TODO: why is this not just something easy like:
        # for dataset_assoc in job.output_datasets + job.output_library_datasets:
        #      yield (dataset_assoc, dataset_assoc.dataset)
        #  I don't understand the reworking it backwards.  -John

    def _handle_metadata_externally( self, job_wrapper, resolve_requirements=False ):
        """
        Set metadata externally. Used by the Pulsar job runner where this
        shouldn't be attached to command line to execute.
        """
        # run the metadata setting script here
        # this is terminate-able when output dataset/job is deleted
        # so that long running set_meta()s can be canceled without having to reboot the server
        if job_wrapper.get_state() not in [ model.Job.states.ERROR, model.Job.states.DELETED ] and job_wrapper.output_paths:
            lib_adjust = GALAXY_LIB_ADJUST_TEMPLATE % job_wrapper.galaxy_lib_dir
            venv = GALAXY_VENV_TEMPLATE % job_wrapper.galaxy_virtual_env
            external_metadata_script = job_wrapper.setup_external_metadata( output_fnames=job_wrapper.get_output_fnames(),
                                                                            set_extension=True,
                                                                            tmp_dir=job_wrapper.working_directory,
                                                                            # We don't want to overwrite metadata that was copied over in init_meta(), as per established behavior
                                                                            kwds={ 'overwrite' : False } )
            external_metadata_script = "%s %s %s" % (lib_adjust, venv, external_metadata_script)
            if resolve_requirements:
                dependency_shell_commands = self.app.datatypes_registry.set_external_metadata_tool.build_dependency_shell_commands(job_directory=job_wrapper.working_directory)
                if dependency_shell_commands:
                    if isinstance( dependency_shell_commands, list ):
                        dependency_shell_commands = "&&".join( dependency_shell_commands )
                    external_metadata_script = "%s&&%s" % ( dependency_shell_commands, external_metadata_script )
            log.debug( 'executing external set_meta script for job %d: %s' % ( job_wrapper.job_id, external_metadata_script ) )
            external_metadata_proc = subprocess.Popen( args=external_metadata_script,
                                                       shell=True,
                                                       cwd=job_wrapper.working_directory,
                                                       env=os.environ,
                                                       preexec_fn=os.setpgrp )
            job_wrapper.external_output_metadata.set_job_runner_external_pid( external_metadata_proc.pid, self.sa_session )
            external_metadata_proc.wait()
            log.debug( 'execution of external set_meta for job %d finished' % job_wrapper.job_id )

    def get_job_file(self, job_wrapper, **kwds):
        job_metrics = job_wrapper.app.job_metrics
        job_instrumenter = job_metrics.job_instrumenters[ job_wrapper.job_destination.id ]

        env_setup_commands = kwds.get( 'env_setup_commands', [] )
        env_setup_commands.append( job_wrapper.get_env_setup_clause() or '' )
        destination = job_wrapper.job_destination or {}
        envs = destination.get( "env", [] )
        envs.extend( job_wrapper.environment_variables )
        for env in envs:
            env_setup_commands.append( env_to_statement( env ) )
        command_line = job_wrapper.runner_command_line
        options = dict(
            job_instrumenter=job_instrumenter,
            galaxy_lib=job_wrapper.galaxy_lib_dir,
            galaxy_virtual_env=job_wrapper.galaxy_virtual_env,
            env_setup_commands=env_setup_commands,
            working_directory=os.path.abspath( job_wrapper.working_directory ),
            command=command_line,
            shell=job_wrapper.shell,
            preserve_python_environment=job_wrapper.tool.requires_galaxy_python_environment,
        )
        # Additional logging to enable if debugging from_work_dir handling, metadata
        # commands, etc... (or just peak in the job script.)
        job_id = job_wrapper.job_id
        log.debug( '(%s) command is: %s' % ( job_id, command_line ) )
        options.update(**kwds)
        return job_script(**options)

    def write_executable_script( self, path, contents, mode=0o755 ):
        write_script( path, contents, self.app.config, mode=mode )

    def _find_container(
        self,
        job_wrapper,
        compute_working_directory=None,
        compute_tool_directory=None,
        compute_job_directory=None,
    ):
        job_directory_type = "galaxy" if compute_working_directory is None else "pulsar"
        if not compute_working_directory:
            compute_working_directory = job_wrapper.tool_working_directory

        if not compute_job_directory:
            compute_job_directory = job_wrapper.working_directory

        if not compute_tool_directory:
            compute_tool_directory = job_wrapper.tool.tool_dir

        tool = job_wrapper.tool
        from galaxy.tools.deps import containers
        tool_info = containers.ToolInfo(tool.containers, tool.requirements)
        job_info = containers.JobInfo(
            compute_working_directory,
            compute_tool_directory,
            compute_job_directory,
            job_directory_type,
        )

        destination_info = job_wrapper.job_destination.params
        return self.app.container_finder.find_container(
            tool_info,
            destination_info,
            job_info
        )

    def _handle_runner_state( self, runner_state, job_state ):
        try:
            for handler in self.runner_state_handlers.get(runner_state, []):
                handler(self.app, self, job_state)
                if job_state.runner_state_handled:
                    break
        except:
            log.exception('Caught exception in runner state handler:')

    def fail_job( self, job_state, exception=False ):
        if getattr( job_state, 'stop_job', True ):
            self.stop_job( self.sa_session.query( self.app.model.Job ).get( job_state.job_wrapper.job_id ) )
        self._handle_runner_state( 'failure', job_state )
        # Not convinced this is the best way to indicate this state, but
        # something necessary
        if not job_state.runner_state_handled:
            job_state.job_wrapper.fail( getattr( job_state, 'fail_message', 'Job failed' ), exception=exception )
            if job_state.job_wrapper.cleanup_job == "always":
                job_state.cleanup()

    def mark_as_resubmitted( self, job_state, info=None ):
        job_state.job_wrapper.mark_as_resubmitted( info=info )
        if not self.app.config.track_jobs_in_database:
            job_state.job_wrapper.change_state( model.Job.states.QUEUED )
            self.app.job_manager.job_handler.dispatcher.put( job_state.job_wrapper )


class JobState( object ):
    """
    Encapsulate state of jobs.
    """
    runner_states = Bunch(
        WALLTIME_REACHED='walltime_reached',
        MEMORY_LIMIT_REACHED='memory_limit_reached',
        UNKNOWN_ERROR='unknown_error',
        GLOBAL_WALLTIME_REACHED='global_walltime_reached',
        OUTPUT_SIZE_LIMIT='output_size_limit'
    )

    def __init__( self, job_wrapper, job_destination ):
        self.runner_state_handled = False
        self.job_wrapper = job_wrapper
        self.job_destination = job_destination

    def set_defaults( self, files_dir ):
        if self.job_wrapper is not None:
            id_tag = self.job_wrapper.get_id_tag()
            if files_dir is not None:
                self.job_file = JobState.default_job_file( files_dir, id_tag )
                self.output_file = os.path.join( files_dir, 'galaxy_%s.o' % id_tag )
                self.error_file = os.path.join( files_dir, 'galaxy_%s.e' % id_tag )
                self.exit_code_file = os.path.join( files_dir, 'galaxy_%s.ec' % id_tag )
            job_name = 'g%s' % id_tag
            if self.job_wrapper.tool.old_id:
                job_name += '_%s' % self.job_wrapper.tool.old_id
            if self.job_wrapper.user:
                job_name += '_%s' % self.job_wrapper.user
            self.job_name = ''.join( map( lambda x: x if x in ( string.letters + string.digits + '_' ) else '_', job_name ) )

    @staticmethod
    def default_job_file( files_dir, id_tag ):
        return os.path.join( files_dir, 'galaxy_%s.sh' % id_tag )

    @staticmethod
    def default_exit_code_file( files_dir, id_tag ):
        return os.path.join( files_dir, 'galaxy_%s.ec' % id_tag )


class AsynchronousJobState( JobState ):
    """
    Encapsulate the state of an asynchronous job, this should be subclassed as
    needed for various job runners to capture additional information needed
    to communicate with distributed resource manager.
    """

    def __init__( self, files_dir=None, job_wrapper=None, job_id=None, job_file=None, output_file=None, error_file=None, exit_code_file=None, job_name=None, job_destination=None  ):
        super( AsynchronousJobState, self ).__init__( job_wrapper, job_destination )
        self.old_state = None
        self._running = False
        self.check_count = 0
        self.start_time = None

        # job_id is the DRM's job id, not the Galaxy job id
        self.job_id = job_id

        self.job_file = job_file
        self.output_file = output_file
        self.error_file = error_file
        self.exit_code_file = exit_code_file
        self.job_name = job_name

        self.set_defaults( files_dir )

        self.cleanup_file_attributes = [ 'job_file', 'output_file', 'error_file', 'exit_code_file' ]

    @property
    def running( self ):
        return self._running

    @running.setter
    def running( self, is_running ):
        self._running = is_running
        # This will be invalid for job recovery
        if self.start_time is None:
            self.start_time = datetime.datetime.now()

    def check_limits( self, runtime=None ):
        limit_state = None
        if self.job_wrapper.has_limits():
            self.check_count += 1
            if self.running and (self.check_count % 20 == 0):
                if runtime is None:
                    runtime = datetime.datetime.now() - (self.start_time or datetime.datetime.now())
                self.check_count = 0
                limit_state = self.job_wrapper.check_limits( runtime=runtime )
        if limit_state is not None:
            # Set up the job for failure, but the runner will do the actual work
            self.runner_state, self.fail_message = limit_state
            self.stop_job = True
            return True
        return False

    def cleanup( self ):
        for file in [ getattr( self, a ) for a in self.cleanup_file_attributes if hasattr( self, a ) ]:
            try:
                os.unlink( file )
            except Exception as e:
                log.debug( "(%s/%s) Unable to cleanup %s: %s" % ( self.job_wrapper.get_id_tag(), self.job_id, file, str( e ) ) )

    def register_cleanup_file_attribute( self, attribute ):
        if attribute not in self.cleanup_file_attributes:
            self.cleanup_file_attributes.append( attribute )


class AsynchronousJobRunner( BaseJobRunner ):
    """Parent class for any job runner that runs jobs asynchronously (e.g. via
    a distributed resource manager).  Provides general methods for having a
    thread to monitor the state of asynchronous jobs and submitting those jobs
    to the correct methods (queue, finish, cleanup) at appropriate times..
    """

    def __init__( self, app, nworkers, **kwargs ):
        super( AsynchronousJobRunner, self ).__init__( app, nworkers, **kwargs )
        # 'watched' and 'queue' are both used to keep track of jobs to watch.
        # 'queue' is used to add new watched jobs, and can be called from
        # any thread (usually by the 'queue_job' method). 'watched' must only
        # be modified by the monitor thread, which will move items from 'queue'
        # to 'watched' and then manage the watched jobs.
        self.watched = []
        self.monitor_queue = Queue()

    def _init_monitor_thread(self):
        self.monitor_thread = threading.Thread( name="%s.monitor_thread" % self.runner_name, target=self.monitor )
        self.monitor_thread.setDaemon( True )
        self.monitor_thread.start()

    def handle_stop(self):
        # DRMAA and SGE runners should override this and disconnect.
        pass

    def monitor( self ):
        """
        Watches jobs currently in the monitor queue and deals with state
        changes (queued to running) and job completion.
        """
        while True:
            # Take any new watched jobs and put them on the monitor list
            try:
                while True:
                    async_job_state = self.monitor_queue.get_nowait()
                    if async_job_state is STOP_SIGNAL:
                        # TODO: This is where any cleanup would occur
                        self.handle_stop()
                        return
                    self.watched.append( async_job_state )
            except Empty:
                pass
            # Iterate over the list of watched jobs and check state
            try:
                self.check_watched_items()
            except Exception:
                log.exception('Unhandled exception checking active jobs')
            # Sleep a bit before the next state check
            time.sleep( 1 )

    def monitor_job(self, job_state):
        self.monitor_queue.put( job_state )

    def shutdown( self ):
        """Attempts to gracefully shut down the monitor thread"""
        log.info( "%s: Sending stop signal to monitor thread" % self.runner_name )
        self.monitor_queue.put( STOP_SIGNAL )
        # Call the parent's shutdown method to stop workers
        super( AsynchronousJobRunner, self ).shutdown()

    def check_watched_items(self):
        """
        This method is responsible for iterating over self.watched and handling
        state changes and updating self.watched with a new list of watched job
        states. Subclasses can opt to override this directly (as older job runners will
        initially) or just override check_watched_item and allow the list processing to
        reuse the logic here.
        """
        new_watched = []
        for async_job_state in self.watched:
            new_async_job_state = self.check_watched_item(async_job_state)
            if new_async_job_state:
                new_watched.append(new_async_job_state)
        self.watched = new_watched

    # Subclasses should implement this unless they override check_watched_items all together.
    def check_watched_item(self, job_state):
        raise NotImplementedError()

    def finish_job( self, job_state ):
        """
        Get the output/error for a finished job, pass to `job_wrapper.finish`
        and cleanup all the job's temporary files.
        """
        galaxy_id_tag = job_state.job_wrapper.get_id_tag()
        external_job_id = job_state.job_id

        # To ensure that files below are readable, ownership must be reclaimed first
        job_state.job_wrapper.reclaim_ownership()

        # wait for the files to appear
        which_try = 0
        while which_try < (self.app.config.retry_job_output_collection + 1):
            try:
                stdout = shrink_stream_by_size( open( job_state.output_file, "r" ), DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True )
                stderr = shrink_stream_by_size( open( job_state.error_file, "r" ), DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True )
                which_try = (self.app.config.retry_job_output_collection + 1)
            except Exception as e:
                if which_try == self.app.config.retry_job_output_collection:
                    stdout = ''
                    stderr = 'Job output not returned from cluster'
                    log.error( '(%s/%s) %s: %s' % ( galaxy_id_tag, external_job_id, stderr, str( e ) ) )
                else:
                    time.sleep(1)
                which_try += 1

        try:
            # This should be an 8-bit exit code, but read ahead anyway:
            exit_code_str = open( job_state.exit_code_file, "r" ).read(32)
        except:
            # By default, the exit code is 0, which typically indicates success.
            exit_code_str = "0"

        try:
            # Decode the exit code. If it's bogus, then just use 0.
            exit_code = int(exit_code_str)
        except:
            log.warning( "(%s/%s) Exit code '%s' invalid. Using 0." % ( galaxy_id_tag, external_job_id, exit_code_str ) )
            exit_code = 0

        # clean up the job files
        cleanup_job = job_state.job_wrapper.cleanup_job
        if cleanup_job == "always" or ( not stderr and cleanup_job == "onsuccess" ):
            job_state.cleanup()

        try:
            job_state.job_wrapper.finish( stdout, stderr, exit_code )
        except:
            log.exception( "(%s/%s) Job wrapper finish method failed" % ( galaxy_id_tag, external_job_id ) )
            job_state.job_wrapper.fail( "Unable to finish job", exception=True )

    def mark_as_finished(self, job_state):
        self.work_queue.put( ( self.finish_job, job_state ) )

    def mark_as_failed(self, job_state):
        self.work_queue.put( ( self.fail_job, job_state ) )
