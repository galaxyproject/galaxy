import errno
import logging
import os
from time import sleep

from galaxy import model
from galaxy.jobs import TaskWrapper
from galaxy.jobs.runners import BaseJobRunner

log = logging.getLogger( __name__ )

__all__ = ( 'TaskedJobRunner', )


class TaskedJobRunner( BaseJobRunner ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "TaskRunner"

    def __init__( self, app, nworkers ):
        """Start the job runner with 'nworkers' worker threads"""
        super( TaskedJobRunner, self ).__init__( app, nworkers )
        self._init_worker_threads()

    def queue_job( self, job_wrapper ):
        # prepare the job
        if not self.prepare_job( job_wrapper ):
            return

        # command line has been added to the wrapper by prepare_job()
        command_line = job_wrapper.runner_command_line

        stderr = stdout = ''

        # Persist the destination
        job_wrapper.set_job_destination(job_wrapper.job_destination)

        # This is the job's exit code, which will depend on the tasks'
        # exit code. The overall job's exit code will be one of two values:
        # o if the job is successful, then the last task scanned will be
        #   used to determine the exit code. Note that this is not the same
        #   thing as the last task to complete, which could be added later.
        # o if a task fails, then the job will fail and the failing task's
        #   exit code will become the job's exit code.
        job_exit_code = None

        try:
            job_wrapper.change_state( model.Job.states.RUNNING )
            self.sa_session.flush()
            # Split with the defined method.
            parallelism = job_wrapper.get_parallelism()
            try:
                splitter = getattr(__import__('galaxy.jobs.splitters', globals(), locals(), [parallelism.method]), parallelism.method)
            except:
                job_wrapper.change_state( model.Job.states.ERROR )
                job_wrapper.fail("Job Splitting Failed, no match for '%s'" % parallelism)
                return
            tasks = splitter.do_split(job_wrapper)
            # Not an option for now.  Task objects don't *do* anything
            # useful yet, but we'll want them tracked outside this thread
            # to do anything.
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
            tasks_complete = False
            count_complete = 0
            sleep_time = 1
            # sleep/loop until no more progress can be made. That is when
            # all tasks are one of { OK, ERROR, DELETED }. If a task
            completed_states = [ model.Task.states.OK,
                                 model.Task.states.ERROR,
                                 model.Task.states.DELETED ]

            # TODO: Should we report an error (and not merge outputs) if
            # one of the subtasks errored out?  Should we prevent any that
            # are pending from being started in that case?
            # SM: I'm
            # If any task has an error, then we will stop all of them
            # immediately. Tasks that are in the QUEUED state will be
            # moved to the DELETED state. The task's runner should
            # ignore tasks that are not in the QUEUED state.
            # Deleted tasks are not included right now.
            #
            while tasks_complete is False:
                count_complete = 0
                tasks_complete = True
                for tw in task_wrappers:
                    task_state = tw.get_state()
                    if ( model.Task.states.ERROR == task_state ):
                        job_exit_code = tw.get_exit_code()
                        log.debug( "Canceling job %d: Task %s returned an error"
                                   % ( tw.job_id, tw.task_id ) )
                        self._cancel_job( job_wrapper, task_wrappers )
                        tasks_complete = True
                        break
                    elif task_state not in completed_states:
                        tasks_complete = False
                    else:
                        job_exit_code = tw.get_exit_code()
                        count_complete = count_complete + 1
                if tasks_complete is False:
                    sleep( sleep_time )
                    if sleep_time < 8:
                        sleep_time *= 2
            job_wrapper.reclaim_ownership()      # if running as the actual user, change ownership before merging.
            log.debug('execution finished - beginning merge: %s' % command_line)
            stdout, stderr = splitter.do_merge(job_wrapper, task_wrappers)
        except Exception:
            job_wrapper.fail( "failure running job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return

        # run the metadata setting script here
        # this is terminate-able when output dataset/job is deleted
        # so that long running set_meta()s can be canceled without having to reboot the server
        self._handle_metadata_externally(job_wrapper, resolve_requirements=True )
        # Finish the job
        try:
            job_wrapper.finish( stdout, stderr, job_exit_code )
        except:
            log.exception("Job wrapper finish method failed")
            job_wrapper.fail("Unable to finish job", exception=True)

    def stop_job( self, job ):
        # We need to stop all subtasks. This is going to stay in the task
        # runner because the task runner also starts all the tasks.
        # First, get the list of tasks from job.tasks, which uses SQL
        # alchemy to retrieve a job's list of tasks.
        tasks = job.get_tasks()
        if ( len( tasks ) > 0 ):
            for task in tasks:
                log.debug( "Killing task's job " + str(task.get_id()) )
                self.app.job_manager.job_handler.dispatcher.stop(task)

        # There were no subtasks, so just kill the job. We'll touch
        # this if the tasks runner is used but the tool does not use
        # parallelism.
        else:
            # if our local job has JobExternalOutputMetadata associated, then our primary job has to have already finished
            if job.external_output_metadata:
                pid = job.external_output_metadata[0].job_runner_external_pid  # every JobExternalOutputMetadata has a pid set, we just need to take from one of them
            else:
                pid = job.job_runner_external_id
            if pid in [ None, '' ]:
                log.warning( "stop_job(): %s: no PID in database for job, unable to stop" % job.id )
                return
            self._stop_pid( pid, job.id )

    def recover( self, job, job_wrapper ):
        # DBTODO Task Recovery, this should be possible.
        job_wrapper.change_state( model.Job.states.ERROR, info="This job was killed when Galaxy was restarted.  Please retry the job." )

    def _cancel_job( self, job_wrapper, task_wrappers ):
        """
        Cancel the given job. The job's state will be set to ERROR.
        Any running tasks will be cancelled, and any queued/pending
        tasks will be marked as DELETED so that runners know not
        to run those tasks.
        """
        job = job_wrapper.get_job()
        job.set_state( model.Job.states.ERROR )

        # For every task (except the one that already had an error)
        #       - If the task is queued, then mark it as deleted
        #         so that the runner will not run it later. (It would
        #         be great to remove stuff from a runner's queue before
        #         the runner picks it up, but that isn't possible in
        #         most APIs.)
        #       - If the task is running, then tell the runner
        #         (via the dispatcher) to cancel the task.
        #       - Else the task is new or waiting (which should be
        #         impossible) or in an error or deleted state already,
        #         so skip it.
        # This is currently done in two loops. If a running task is
        # cancelled, then a queued task could take its place before
        # it's marked as deleted.
        # TODO: Eliminate the chance of a race condition wrt state.
        for task_wrapper in task_wrappers:
            task = task_wrapper.get_task()
            task_state = task.get_state()
            if ( model.Task.states.QUEUED == task_state ):
                log.debug( "_cancel_job for job %d: Task %d is not running; setting state to DELETED"
                           % ( job.get_id(), task.get_id() ) )
                task_wrapper.change_state( task.states.DELETED )
        # If a task failed, then the caller will have waited a few seconds
        # before recognizing the failure. In that time, a queued task could
        # have been picked up by a runner but not marked as running.
        # So wait a few seconds so that we can eliminate such tasks once they
        # are running.
        sleep(5)
        for task_wrapper in task_wrappers:
            if ( model.Task.states.RUNNING == task_wrapper.get_state() ):
                task = task_wrapper.get_task()
                log.debug( "_cancel_job for job %d: Stopping running task %d"
                           % ( job.get_id(), task.get_id() ) )
                job_wrapper.app.job_manager.job_handler.dispatcher.stop( task )

    def _check_pid( self, pid ):
        # DBTODO Need to check all subtask pids and return some sort of cumulative result.
        return True
        try:
            os.kill( pid, 0 )
            return True
        except OSError as e:
            if e.errno == errno.ESRCH:
                log.debug( "_check_pid(): PID %d is dead" % pid )
            else:
                log.warning( "_check_pid(): Got errno %s when attempting to check PID %d: %s" % ( errno.errorcode[e.errno], pid, e.strerror ) )
            return False

    def _stop_pid( self, pid, job_id ):
        """
        This method stops the given process id whether it's a task or job.
        It is meant to be a private helper method, but it is mostly reusable.
        The first argument is the process id to stop, and the second id is the
        job's id (which is used for logging messages only right now).
        """
        pid = int( pid )
        log.debug( "Stopping pid %s" % pid )
        if not self._check_pid( pid ):
            log.warning( "_stop_pid(): %s: PID %d was already dead or can't be signaled" % ( job_id, pid ) )
            return
        for sig in [ 15, 9 ]:
            try:
                os.killpg( pid, sig )
            except OSError as e:
                # This warning could be bogus; many tasks are stopped with
                # SIGTERM (signal 15), but ymmv depending on the platform.
                log.warning( "_stop_pid(): %s: Got errno %s when attempting to signal %d to PID %d: %s" % ( job_id, errno.errorcode[e.errno], sig, pid, e.strerror ) )
                return
            # TODO: If we're stopping lots of tasks, then we will want to put this
            # avoid a two-second overhead using some other asynchronous method.
            sleep( 2 )
            if not self._check_pid( pid ):
                log.debug( "_stop_pid(): %s: PID %d successfully killed with signal %d" % ( job_id, pid, sig ) )
                return
        else:
            log.warning( "_stop_pid(): %s: PID %d refuses to die after signaling TERM/KILL" % ( job_id, pid ) )
