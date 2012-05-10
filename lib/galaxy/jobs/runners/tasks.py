import logging
import subprocess
from Queue import Queue
import threading

from galaxy import model

import os, errno
from time import sleep

from galaxy.jobs import TaskWrapper

log = logging.getLogger( __name__ )

__all__ = [ 'TaskedJobRunner' ]

class TaskedJobRunner( object ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    STOP_SIGNAL = object()
    def __init__( self, app ):
        """Start the job runner with 'nworkers' worker threads"""
        self.app = app
        self.sa_session = app.model.context
        # start workers
        self.queue = Queue()
        self.threads = []
        nworkers = app.config.local_task_queue_workers
        log.info( "Starting tasked-job runners" )
        for i in range( nworkers  ):
            worker = threading.Thread( target=self.run_next )
            worker.start()
            self.threads.append( worker )
        log.debug( "%d workers ready", nworkers )

    def run_next( self ):
        """Run the next job, waiting until one is available if neccesary"""
        while 1:
            job_wrapper = self.queue.get()
            if job_wrapper is self.STOP_SIGNAL:
                return
            try:
                self.run_job( job_wrapper )
            except:
                log.exception( "Uncaught exception running tasked job" )

    def run_job( self, job_wrapper ):
        job_wrapper.set_runner( 'tasks:///', None )
        stderr = stdout = command_line = ''
        # Prepare the job to run
        try:
            job_wrapper.prepare()
            command_line = job_wrapper.get_command_line()
        except:
            job_wrapper.fail( "failure preparing job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return
        # If we were able to get a command line, run the job.  ( must be passed to tasks )
        if command_line:
            try:
                # DBTODO read tool info and use the right kind of parallelism.  
                # For now, the only splitter is the 'basic' one
                job_wrapper.change_state( model.Job.states.RUNNING )
                self.sa_session.flush()
                # Split with the tool-defined method.
                try:
                    splitter = getattr(__import__('galaxy.jobs.splitters',  globals(),  locals(),  [job_wrapper.tool.parallelism.method]),  job_wrapper.tool.parallelism.method)
                except:   
                    job_wrapper.change_state( model.Job.states.ERROR )
                    job_wrapper.fail("Job Splitting Failed, no match for '%s'" % job_wrapper.tool.parallelism)
                    return
                tasks = splitter.do_split(job_wrapper)

                # Not an option for now.  Task objects don't *do* anything useful yet, but we'll want them tracked outside this thread to do anything.
                # if track_tasks_in_database:
                task_wrappers = []
                for task in tasks:
                    self.sa_session.add(task)
                self.sa_session.flush()
                
                # Must flush prior to the creation and queueing of task wrappers.
                for task in tasks:
                    tw = TaskWrapper(task, job_wrapper.queue)
                    task_wrappers.append(tw)
                    self.app.job_manager.job_handler.dispatcher.put(tw)
                tasks_incomplete = False
                count_complete = 0
                sleep_time = 1
                # sleep/loop until no more progress can be made. That is when
                # all tasks are one of { OK, ERROR, DELETED }
                completed_states = [ model.Task.states.OK, \
                                    model.Task.states.ERROR, \
                                    model.Task.states.DELETED ]
                # TODO: Should we report an error (and not merge outputs) if one of the subtasks errored out?
                # Should we prevent any that are pending from being started in that case?
                while tasks_incomplete is False:
                    count_complete = 0
                    tasks_incomplete = True
                    for tw in task_wrappers:
                        task_state = tw.get_state()
                        if not task_state in completed_states:
                            tasks_incomplete = False
                        else:
                            count_complete = count_complete + 1
                    if tasks_incomplete is False:
                        # log.debug('Tasks complete: %s. Sleeping %s' % (count_complete, sleep_time))
                        sleep( sleep_time )
                        if sleep_time < 8:
                            sleep_time *= 2
                
                import time

                job_wrapper.reclaim_ownership()      # if running as the actual user, change ownership before merging.

                log.debug('execution finished - beginning merge: %s' % command_line)
                stdout,  stderr = splitter.do_merge(job_wrapper,  task_wrappers)
                
            except Exception:
                job_wrapper.fail( "failure running job", exception=True )
                log.exception("failure running job %d" % job_wrapper.job_id)
                return

        #run the metadata setting script here
        #this is terminate-able when output dataset/job is deleted
        #so that long running set_meta()s can be canceled without having to reboot the server
        if job_wrapper.get_state() not in [ model.Job.states.ERROR, model.Job.states.DELETED ] and self.app.config.set_metadata_externally and job_wrapper.output_paths:
            external_metadata_script = job_wrapper.setup_external_metadata( output_fnames = job_wrapper.get_output_fnames(),
                                                                            set_extension = True,
                                                                            kwds = { 'overwrite' : False } ) #we don't want to overwrite metadata that was copied over in init_meta(), as per established behavior
            log.debug( 'executing external set_meta script for job %d: %s' % ( job_wrapper.job_id, external_metadata_script ) )
            external_metadata_proc = subprocess.Popen( args = external_metadata_script, 
                                         shell = True, 
                                         env = os.environ,
                                         preexec_fn = os.setpgrp )
            job_wrapper.external_output_metadata.set_job_runner_external_pid( external_metadata_proc.pid, self.sa_session )
            external_metadata_proc.wait()
            log.debug( 'execution of external set_meta finished for job %d' % job_wrapper.job_id )
        
        # Finish the job                
        try:
            job_wrapper.finish( stdout, stderr )
        except:
            log.exception("Job wrapper finish method failed")
            job_wrapper.fail("Unable to finish job", exception=True)

    def put( self, job_wrapper ):
        """Add a job to the queue (by job identifier)"""
        # Change to queued state before handing to worker thread so the runner won't pick it up again
        job_wrapper.change_state( model.Job.states.QUEUED )
        self.queue.put( job_wrapper )
    
    def shutdown( self ):
        """Attempts to gracefully shut down the worker threads"""
        log.info( "sending stop signal to worker threads" )
        for i in range( len( self.threads ) ):
            self.queue.put( self.STOP_SIGNAL )
        log.info( "local job runner stopped" )

    def check_pid( self, pid ):
        # DBTODO Need to check all subtask pids and return some sort of cumulative result.
        return True
        try:
            os.kill( pid, 0 )
            return True
        except OSError, e:
            if e.errno == errno.ESRCH:
                log.debug( "check_pid(): PID %d is dead" % pid )
            else:
                log.warning( "check_pid(): Got errno %s when attempting to check PID %d: %s" %( errno.errorcode[e.errno], pid, e.strerror ) )
            return False

    def stop_job( self, job ):
        # DBTODO Call stop on all of the tasks.
        #if our local job has JobExternalOutputMetadata associated, then our primary job has to have already finished
        if job.external_output_metadata:
            pid = job.external_output_metadata[0].job_runner_external_pid #every JobExternalOutputMetadata has a pid set, we just need to take from one of them
        else:
            pid = job.job_runner_external_id
        if pid in [ None, '' ]:
            log.warning( "stop_job(): %s: no PID in database for job, unable to stop" % job.id )
            return
        pid = int( pid )
        if not self.check_pid( pid ):
            log.warning( "stop_job(): %s: PID %d was already dead or can't be signaled" % ( job.id, pid ) )
            return
        for sig in [ 15, 9 ]:
            try:
                os.killpg( pid, sig )
            except OSError, e:
                log.warning( "stop_job(): %s: Got errno %s when attempting to signal %d to PID %d: %s" % ( job.id, errno.errorcode[e.errno], sig, pid, e.strerror ) )
                return  # give up
            sleep( 2 )
            if not self.check_pid( pid ):
                log.debug( "stop_job(): %s: PID %d successfully killed with signal %d" %( job.id, pid, sig ) )
                return
        else:
            log.warning( "stop_job(): %s: PID %d refuses to die after signaling TERM/KILL" %( job.id, pid ) )

    def recover( self, job, job_wrapper ):
        # DBTODO Task Recovery, this should be possible.
        job_wrapper.change_state( model.Job.states.ERROR, info = "This job was killed when Galaxy was restarted.  Please retry the job." )

