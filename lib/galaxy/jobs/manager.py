"""
Top-level Galaxy job manager, moves jobs to handler(s)
"""

import os
import time
import random
import logging
import threading
from Queue import Queue, Empty

from sqlalchemy.sql.expression import and_, or_

from galaxy import model
from galaxy.jobs import handler, Sleeper, NoopQueue
from galaxy.util.json import from_json_string

log = logging.getLogger( __name__ )

class JobManager( object ):
    """
    Highest level interface to job management.

    TODO: Currently the app accesses "job_queue" and "job_stop_queue" directly.
          This should be decoupled.
    """
    def __init__( self, app ):
        self.app = app
        self.job_handler = NoopHandler()
        if self.app.config.server_name in self.app.config.job_handlers:
            self.job_handler = handler.JobHandler( app )
        if self.app.config.server_name == self.app.config.job_manager:
            job_handler = NoopHandler()
            # In the case that webapp == manager == handler, pass jobs in memory
            if not self.app.config.track_jobs_in_database:
                job_handler = self.job_handler
            # Otherwise, even if the manager == one of the handlers, its handler will pick up jobs from the database
            self.job_queue = JobManagerQueue( app, job_handler )
            self.job_stop_queue = JobManagerStopQueue( app, job_handler )
            if self.app.config.enable_beta_job_managers:
                from galaxy.jobs.deferred import DeferredJobQueue
                self.deferred_job_queue = DeferredJobQueue( app )
        else:
            self.job_queue = self.job_stop_queue = NoopQueue()
        self.job_handler.start()
    def shutdown( self ):
        self.job_queue.shutdown()
        self.job_stop_queue.shutdown()
        self.job_handler.shutdown()

class JobManagerQueue( object ):
    """
    Job manager, waits for jobs to be runnable and then dispatches to a
    JobHandler.
    """
    STOP_SIGNAL = object()
    def __init__( self, app, job_handler ):
        self.app = app
        self.job_handler = job_handler # the (singular) handler if we are passing jobs in memory

        self.sa_session = app.model.context
        self.job_lock = False
        # Keep track of the pid that started the job manager, only it
        # has valid threads
        self.parent_pid = os.getpid()
        # Contains new jobs. Note this is not used if track_jobs_in_database is True
        self.queue = Queue()
        # Helper for interruptable sleep
        self.sleeper = Sleeper()
        self.running = True
        self.monitor_thread = threading.Thread( target=self.__monitor )
        # Recover jobs at startup
        self.__check_jobs_at_startup()
        # Start the queue
        self.monitor_thread.start()
        log.info( "job manager queue started" )

    def __check_jobs_at_startup( self ):
        """
        Checks all jobs that are in the 'new', 'queued' or 'running' state in
        the database and requeues or cleans up as necessary.  Only run as the
        job manager starts.
        """
        for job in self.sa_session.query( model.Job ).enable_eagerloads( False ) \
                                  .filter( ( ( model.Job.state == model.Job.states.NEW ) \
                                             | ( model.Job.state == model.Job.states.RUNNING ) \
                                             | ( model.Job.state == model.Job.states.QUEUED ) ) \
                                           & ( model.Job.handler == None ) ):
            if job.tool_id not in self.app.toolbox.tools_by_id:
                log.warning( "(%s) Tool '%s' removed from tool config, unable to recover job" % ( job.id, job.tool_id ) )
                JobWrapper( job, self ).fail( 'This tool was disabled before the job completed.  Please contact your Galaxy administrator.' )
            else:
                job.handler = self.__get_handler( job ) # handler's recovery method will take it from here
                log.info( "(%d) Job in '%s' state had no handler at job manager startup, assigned '%s' handler" % ( job.id, job.state, job.handler ) )
        if self.sa_session.dirty:
            self.sa_session.flush()

    def __monitor( self ):
        """
        Continually iterate the waiting jobs and dispatch to a handler
        """
        # HACK: Delay until after forking, we need a way to do post fork notification!!!
        time.sleep( 10 )
        while self.running:
            try:
                self.__monitor_step()
            except:
                log.exception( "Exception in monitor_step" )
            # Sleep
            self.sleeper.sleep( 1 )

    def __monitor_step( self ):
        """
        Called repeatedly by `monitor` to process waiting jobs. Gets any new
        jobs (either from the database or from its own queue), then assigns a
        handler.
        """
        # Do nothing if the queue is locked
        if self.job_lock:
            log.info( 'Job queue is administratively locked, sleeping...' )
            time.sleep( 10 )
            return
        # Pull all new jobs from the queue at once
        jobs_to_check = []
        if self.app.config.track_jobs_in_database:
            # Clear the session so we get fresh states for job and all datasets
            self.sa_session.expunge_all()
            # Fetch all new jobs
            jobs_to_check = self.sa_session.query( model.Job ).enable_eagerloads( False ) \
                                .filter( ( model.Job.state == model.Job.states.NEW ) \
                                         & ( model.Job.handler == None ) ).all()
        else:
            # Get job objects and append to watch queue for any which were
            # previously waiting
            try:
                while 1:
                    message = self.queue.get_nowait()
                    if message is self.STOP_SIGNAL:
                        return
                    # Unpack the message
                    job_id, tool_id = message
                    # Get the job object and append to watch queue
                    jobs_to_check.append( self.sa_session.query( model.Job ).get( job_id ) )
            except Empty:
                pass

        for job in jobs_to_check:
            job.handler = self.__get_handler( job )
            log.debug( "(%s) Job assigned to handler '%s'" % ( job.id, job.handler ) )
            self.sa_session.add( job )

        # If tracking in the database, handlers will pick up the job now
        self.sa_session.flush()

        time.sleep( 5 )

        # This only does something in the case that there is only one handler and it is this Galaxy process
        for job in jobs_to_check:
            self.job_handler.job_queue.put( job.id, job.tool_id )

    def __get_handler( self, job ):
        try:
            params = None
            if job.params:
                params = from_json_string( job.params )
            return self.app.toolbox.tools_by_id.get( job.tool_id, None ).get_job_handler( params )
        except:
            log.exception( "(%s) Caught exception attempting to get tool-specific job handler for tool '%s', selecting at random from available handlers instead:" % ( job.id, job.tool_id ) )
            return random.choice( self.app.config.job_handlers )

    def put( self, job_id, tool ):
        """Add a job to the queue (by job identifier)"""
        if not self.app.config.track_jobs_in_database:
            self.queue.put( ( job_id, tool.id ) )
            self.sleeper.wake()

    def shutdown( self ):
        """Attempts to gracefully shut down the worker thread"""
        if self.parent_pid != os.getpid():
            # We're not the real job queue, do nothing
            return
        else:
            log.info( "sending stop signal to worker thread" )
            self.running = False
            if not self.app.config.track_jobs_in_database:
                self.queue.put( self.STOP_SIGNAL )
            self.sleeper.wake()
            log.info( "job manager queue stopped" )

class JobManagerStopQueue( object ):
    """
    A queue for jobs which need to be terminated prematurely.
    """
    STOP_SIGNAL = object()
    def __init__( self, app, job_handler ):
        self.app = app
        self.job_handler = job_handler

        self.sa_session = app.model.context

        # Keep track of the pid that started the job manager, only it
        # has valid threads
        self.parent_pid = os.getpid()
        # Contains new jobs. Note this is not used if track_jobs_in_database is True
        self.queue = Queue()

        # Contains jobs that are waiting (only use from monitor thread)
        self.waiting = []

        # Helper for interruptable sleep
        self.sleeper = Sleeper()
        self.running = True
        self.monitor_thread = threading.Thread( target=self.monitor )
        self.monitor_thread.start()
        log.info( "job manager stop queue started" )

    def monitor( self ):
        """
        Continually iterate the waiting jobs, stop any that are found.
        """
        # HACK: Delay until after forking, we need a way to do post fork notification!!!
        time.sleep( 10 )
        while self.running:
            try:
                self.monitor_step()
            except:
                log.exception( "Exception in monitor_step" )
            # Sleep
            self.sleeper.sleep( 1 )

    def monitor_step( self ):
        """
        Called repeatedly by `monitor` to stop jobs.
        """
        jobs_to_check = []
        # Pull from the queue even if tracking in the database (in the case of Administrative stopped jobs)
        try:
            while 1:
                message = self.queue.get_nowait()
                if message is self.STOP_SIGNAL:
                    return
                # Unpack the message
                job_id, error_msg = message
                # Get the job object and append to watch queue
                jobs_to_check.append( ( self.sa_session.query( model.Job ).get( job_id ), error_msg ) )
        except Empty:
            pass

        # If tracking in the database, the handler will pick up the stop itself.  Otherwise, notify the handler.
        for job, error_msg in jobs_to_check:
            self.job_handler.job_stop_queue.put( job.id, error_msg )

    def put( self, job_id, error_msg=None ):
        self.queue.put( ( job_id, error_msg ) )

    def shutdown( self ):
        """Attempts to gracefully shut down the worker thread"""
        if self.parent_pid != os.getpid():
            # We're not the real job queue, do nothing
            return
        else:
            log.info( "sending stop signal to worker thread" )
            self.running = False
            if not self.app.config.track_jobs_in_database:
                self.queue.put( self.STOP_SIGNAL )
            self.sleeper.wake()
            log.info( "job manager stop queue stopped" )

class NoopHandler( object ):
    def __init__( self, *args, **kwargs ):
        self.job_queue = NoopQueue()
        self.job_stop_queue = NoopQueue()
    def start( self ):
        pass
    def shutdown( self, *args ):
        pass
