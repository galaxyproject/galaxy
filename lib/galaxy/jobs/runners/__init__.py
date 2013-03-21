"""
Base classes for job runner plugins.
"""

import os
import time
import string
import logging
import threading

from Queue import Queue, Empty

import galaxy.jobs
from galaxy import model

log = logging.getLogger( __name__ )

STOP_SIGNAL = object()

class BaseJobRunner( object ):
    def __init__( self, app, nworkers ):
        """Start the job runner
        """
        self.app = app
        self.sa_session = app.model.context
        self.nworkers = nworkers

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
        while 1:
            ( method, arg ) = self.work_queue.get()
            if method is STOP_SIGNAL:
                return
            # id and name are collected first so that the call of method() is the last exception.
            try:
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
        # Change to queued state before handing to worker thread so the runner won't pick it up again
        job_wrapper.change_state( model.Job.states.QUEUED )
        # Persist the destination so that the job will be included in counts if using concurrency limits
        job_wrapper.set_job_destination( job_wrapper.job_destination, None )
        self.mark_as_queued(job_wrapper)

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

    # Runners must override the job handling methods
    def queue_job(self, job_wrapper):
        """Some sanity checks that all runners' queue_job() methods are likely to want to do
        """
        job_id = job_wrapper.get_id_tag()
        job_state = job_wrapper.get_state()
        job_wrapper.is_ready = False

        # Make sure the job hasn't been deleted
        if job_state == model.Job.states.DELETED:
            log.debug( "(%s) Job deleted by user before it entered the %s queue"  % ( job_id, self.runner_name ) )
            if self.app.config.cleanup_job in ( "always", "onsuccess" ):
                job_wrapper.cleanup()
            return
        elif job_state != model.Job.states.QUEUED:
            log.info( "(%d) Job is in state %s, skipping execution"  % ( job_id, job_state ) ) 
            # cleanup may not be safe in all states
            return

        # Prepare the job
        try:
            job_wrapper.prepare()
            job_wrapper.runner_command_line = self.build_command_line( job_wrapper )
        except:
            log.exception("(%s) Failure preparing job" % job_id)
            job_wrapper.fail( "failure preparing job", exception=True )
            return

        job_wrapper.is_ready = True

    def stop_job(self, job):
        raise NotImplementedError()

    def recover(self, job, job_wrapper):
        raise NotImplementedError()

    def build_command_line( self, job_wrapper, include_metadata=False, include_work_dir_outputs=True ):
        """
        Compose the sequence of commands necessary to execute a job. This will
        currently include:

            - environment settings corresponding to any requirement tags
            - preparing input files
            - command line taken from job wrapper
            - commands to set metadata (if include_metadata is True)
        """

        commands = job_wrapper.get_command_line()
        # All job runners currently handle this case which should never
        # occur
        if not commands:
            return None
        # Prepend version string
        if job_wrapper.version_string_cmd:
            commands = "%s &> %s; " % ( job_wrapper.version_string_cmd, job_wrapper.get_version_string_path() ) + commands
        # prepend getting input files (if defined)
        if hasattr(job_wrapper, 'prepare_input_files_cmds') and job_wrapper.prepare_input_files_cmds is not None:
            commands = "; ".join( job_wrapper.prepare_input_files_cmds + [ commands ] ) 
        # Prepend dependency injection
        if job_wrapper.dependency_shell_commands:
            commands = "; ".join( job_wrapper.dependency_shell_commands + [ commands ] ) 

        # Append commands to copy job outputs based on from_work_dir attribute.
        if include_work_dir_outputs:
            work_dir_outputs = self.get_work_dir_outputs( job_wrapper )
            if work_dir_outputs:
                commands += "; " + "; ".join( [ "if [ -f %s ] ; then cp %s %s ; fi" % 
                    ( source_file, source_file, destination ) for ( source_file, destination ) in work_dir_outputs ] )

        # Append metadata setting commands, we don't want to overwrite metadata
        # that was copied over in init_meta(), as per established behavior
        if include_metadata and self.app.config.set_metadata_externally:
            commands += "; cd %s; " % os.path.abspath( os.getcwd() )
            commands += job_wrapper.setup_external_metadata( 
                            exec_dir = os.path.abspath( os.getcwd() ),
                            tmp_dir = job_wrapper.working_directory,
                            dataset_files_path = self.app.model.Dataset.file_path,
                            output_fnames = job_wrapper.get_output_fnames(),
                            set_extension = False,
                            kwds = { 'overwrite' : False } ) 
        return commands

    def get_work_dir_outputs( self, job_wrapper ):
        """
        Returns list of pairs (source_file, destination) describing path
        to work_dir output file and ultimate destination.
        """

        def in_directory( file, directory ):
            """
            Return true, if the common prefix of both is equal to directory
            e.g. /a/b/c/d.rst and directory is /a/b, the common prefix is /a/b
            """

            # Make both absolute.
            directory = os.path.abspath( directory )
            file = os.path.abspath( file )

            return os.path.commonprefix( [ file, directory ] ) == directory

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
        job_tool = self.app.toolbox.tools_by_id.get( job.tool_id, None )
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            for dataset in dataset_assoc.dataset.dataset.history_associations + dataset_assoc.dataset.dataset.library_associations:
                if isinstance( dataset, self.app.model.HistoryDatasetAssociation ):
                    joda = self.sa_session.query( self.app.model.JobToOutputDatasetAssociation ).filter_by( job=job, dataset=dataset ).first()
                    if joda and job_tool:
                        hda_tool_output = job_tool.outputs.get( joda.name, None )
                        if hda_tool_output and hda_tool_output.from_work_dir:
                            # Copy from working dir to HDA.
                            # TODO: move instead of copy to save time?
                            source_file = os.path.join( os.path.abspath( job_wrapper.working_directory ), hda_tool_output.from_work_dir )
                            destination = output_paths[ dataset.dataset_id ]
                            if in_directory( source_file, job_wrapper.working_directory ):
                                output_pairs.append( ( source_file, destination ) )
                                log.debug( "Copying %s to %s as directed by from_work_dir" % ( source_file, destination ) )
                            else:
                                # Security violation.
                                log.exception( "from_work_dir specified a location not in the working directory: %s, %s" % ( source_file, job_wrapper.working_directory ) )
        return output_pairs

class AsynchronousJobState( object ):
    """
    Encapsulate the state of an asynchronous job, this should be subclassed as
    needed for various job runners to capture additional information needed
    to communicate with distributed resource manager.
    """

    def __init__( self, files_dir=None, job_wrapper=None, job_id=None, job_file=None, output_file=None, error_file=None, exit_code_file=None, job_name=None, job_destination=None  ):
        self.old_state = None
        self.running = False
        self.check_count = 0

        self.job_wrapper = job_wrapper
        # job_id is the DRM's job id, not the Galaxy job id
        self.job_id = job_id
        self.job_destination = job_destination

        self.job_file = job_file
        self.output_file = output_file
        self.error_file = error_file
        self.exit_code_file = exit_code_file
        self.job_name = job_name

        self.set_defaults( files_dir )

    def set_defaults( self, files_dir ):
        if self.job_wrapper is not None:
            id_tag = self.job_wrapper.get_id_tag()
            if files_dir is not None:
                self.job_file = os.path.join( files_dir, 'galaxy_%s.sh' % id_tag )
                self.output_file = os.path.join( files_dir, 'galaxy_%s.o' % id_tag )
                self.error_file = os.path.join( files_dir, 'galaxy_%s.e' % id_tag )
                self.exit_code_file = os.path.join( files_dir, 'galaxy_%s.ec' % id_tag )
            job_name = 'g%s' % id_tag
            if self.job_wrapper.tool.old_id:
                job_name += '_%s' % self.job_wrapper.tool.old_id
            if self.job_wrapper.user:
                job_name += '_%s' % self.job_wrapper.user
            self.job_name = ''.join( map( lambda x: x if x in ( string.letters + string.digits + '_' ) else '_', job_name ) )

class AsynchronousJobRunner( BaseJobRunner ):
    """Parent class for any job runner that runs jobs asynchronously (e.g. via
    a distributed resource manager).  Provides general methods for having a
    thread to monitor the state of asynchronous jobs and submitting those jobs
    to the correct methods (queue, finish, cleanup) at appropriate times..
    """

    def __init__( self, app, nworkers ):
        super( AsynchronousJobRunner, self ).__init__( app, nworkers )
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
        while 1:
            # Take any new watched jobs and put them on the monitor list
            try:
                while 1: 
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
            except Exception, e:
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
    def check_watched_item(self):
        raise NotImplementedError()

    def finish_job(self, job_state):
        raise NotImplementedError()

    def fail_job(self, job_state):
        raise NotImplementedError()

    def mark_as_finished(self, job_state):
        self.work_queue.put( ( self.finish_job, job_state ) )

    def mark_as_failed(self, job_state):
        self.work_queue.put( ( self.fail_job, job_state ) )
