"""
Job runner plugin for executing jobs on the local system via the command line.
"""
import datetime
import errno
import logging
import os
import subprocess
import tempfile
import threading
from time import sleep
from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState
)


from galaxy import model
from galaxy.job_execution.output_collect import default_exit_code_file
from galaxy.util import (
    asbool,
    DATABASE_MAX_STRING_SIZE,
    shrink_stream_by_size
)
from ..runners import (
    BaseJobRunner,
    JobState
)

log = logging.getLogger(__name__)
stdout = ''
stderr = 'None'

DEFAULT_POOL_SLEEP_TIME = 60

class HmgmRunner(AsynchronousJobRunner):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "HmgmRunner"

    def __init__(self, app, nworkers):
        super(HmgmRunner, self).__init__(app, nworkers)
        self._init_monitor_thread()
        self._init_worker_threads()
        log.info("initializing hmgm job runner")

    def queue_job(self, job_wrapper):
        self.prepare_job(job_wrapper)
        job_destination = job_wrapper.job_destination
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper, job_id=job_wrapper.job_id, job_destination=job_destination)
        # Proceed with general initialization
        self.monitor_queue.put(ajs)

    def check_watched_items(self):
            """
            This method is responsible for iterating over self.watched and handling
            state changes and updating self.watched with a new list of watched job
            states. Subclasses can opt to override this directly (as older job runners will
            initially) or just override check_watched_item and allow the list processing to
            reuse the logic here.
            """
#             log.debug("Inside hmgm.py check_watched_items")
            new_watched = []
            for async_job_state in self.watched:
                # AMPPD - don't fail the whole thing if we have a single error. 
                try:
                    new_async_job_state = self.check_watched_item(async_job_state)
                    if new_async_job_state:
                        new_watched.append(new_async_job_state)
                except Exception as e:
                    try:
                        log.exception('AMPPD: Unhandled exception checking watched item')
                        log.debug(str(e))
                        log.debug("Async Job Id: " + str(async_job_state.job_wrapper.job_id))
                        if async_job_state is not None:
                            log.debug("*** Async Job State: ****")
                            log.debug(repr(async_job_state))
                            log.debug("*** End Async Job State: ****")
                            self._fail_job_local(async_job_state.job_wrapper, "Exception checking HMGM watched item")
                        else:
                            log.debug("Job state was empty")
                    except Exception as ex:
                        log.debug("Could not print job details");
                        log.debug(str(ex))
            self.watched = new_watched

    # This is the main logic to determine what to do with thread.  Should it re-queue, be killed, or complete
    def check_watched_item(self, job_state):
        # If this job has been deleted, don't execute again.  Exit. 
        if job_state.job_wrapper.get_state() == model.Job.states.DELETED:
            job_state.running = False
            log.info("Job deleted by user before it entered the queue")
            if job_state.job_wrapper.cleanup_job in ("always", "onsuccess"):
                job_state.job_wrapper.cleanup()
            return None

        exit_code = self._run_job(job_state.job_wrapper)
        log.debug("Hmgm Exit Code: " + str(exit_code))
        # This is a success code: The HMGM is complete
        
        if exit_code==0:
            job_state.running = False
            job_state.job_wrapper.change_state(model.Job.states.OK)
            try:
                # Write the output
                self.create_log_file(job_state, exit_code)
            except Exception as e:
                log.debug("Job wrapper finish method failed with exit_code 0")
                log.debug(str(e))
                # AMPPD: Disable this to stop jobs with bad logs from failing.  
                #log.exception("Job wrapper finish method failed")
                # self._fail_job_local(job_state.job_wrapper, "Unable to finish job")
            self.mark_as_finished(job_state)
            return None
        # This HMGM job is not complete, try again later
        # Note: using exit code 255 instead of 1 to avoid potential conflicts where tool scripts use 1  to represent error
        elif exit_code==255:
            job_state.running = False
            try:
                # Write the output
                self.create_log_file(job_state, exit_code)
                job_state.job_wrapper.change_state(model.Job.states.QUEUED)
            except Exception as e:
                log.debug("Job wrapper finish method failed with exit_code 1")
                log.debug(str(e))
                # AMPPD: Disable this to stop jobs with bad logs from failing.  
                #log.exception("Job wrapper finish method failed")
                # self._fail_job_local(job_state.job_wrapper, "Unable to finish job")                
            # Sleep the current thread.  Let's not iterate through too fast when re-queueing tasks
            sleep(DEFAULT_POOL_SLEEP_TIME)
            return job_state
        # Or we got an error
        else:
            job_state.running = False
            job_state.job_wrapper.change_state(model.Job.states.ERROR)
            return None

    # Copy stdout and stderr from process to files expected by job_state
    def create_log_file(self, job_state, exit_code):
        try:
            # Write stdout
            log_file = open(job_state.output_file, "w")
            log_file.write(self.stdout)
            log_file.close()
            
            # Write stderr
            log_file = open(job_state.error_file, "w")
            log_file.write(self.stderr)
            log_file.close()

            # Write exit code
            log_file = open(job_state.exit_code_file, "w")
            log_file.write(str(exit_code))
            log_file.close()

            log.debug("CREATE OUTPUT FILE: " + str(job_state.output_file))
            log.debug("CREATE ERROR FILE: " + str(job_state.error_file))
            log.debug("CREATE EXIT CODE FILE: " + str(job_state.exit_code_file))
        except IOError as e:
            log.error('Could not access task log file %s' % str(e))
            log.debug("IO Error occurred when accessing the files.")
            return False
        return True
    
    def stop_job(self, job_wrapper):
        # if our local job has JobExternalOutputMetadata associated, then our primary job has to have already finished
        job = job_wrapper.get_job()
        job_ext_output_metadata = job.get_external_output_metadata()
        try:
            pid = job_ext_output_metadata[0].job_runner_external_pid  # every JobExternalOutputMetadata has a pid set, we just need to take from one of them
            assert pid not in [None, '']
        except Exception:
            # metadata internal or job not complete yet
            pid = job.get_job_runner_external_id()
        if pid in [None, '']:
            log.warning("stop_job(): %s: no PID in database for job, unable to stop" % job.id)
            return
        pid = int(pid)
        if not check_pg(pid):
            log.warning("stop_job(): %s: Process group %d was already dead or can't be signaled" % (job.id, pid))
            # Kill works fine in cases where the job is actually running.  But in the case of HMGMs, this often isn't the case.  
            # Instead, mark the job as deleted and handle appropriately before we run it next time.  
            job_wrapper.change_state(model.Job.states.DELETED)
            return
        log.debug('stop_job(): %s: Terminating process group %d', job.id, pid)
        kill_pg(pid)
    
    # Run job is a slightly modified version of run_job in runners/local.py - queue_job().  It builds a command line proc
    # to execute, reads the stdout and stderr, and returns the status
    def _run_job(self, job_wrapper):
        # Removed: no need to prepare local job here
        # Removed: stderr and stdout made class variables
        exit_code = 0

        # command line has been added to the wrapper by prepare_job()
        command_line, exit_code_path = self.__command_line(job_wrapper)
        job_id = job_wrapper.get_id_tag()

        try:
            stdout_file = tempfile.NamedTemporaryFile(mode='wb+', suffix='_stdout', dir=job_wrapper.working_directory)
            stderr_file = tempfile.NamedTemporaryFile(mode='wb+', suffix='_stderr', dir=job_wrapper.working_directory)
            log.debug('(%s) executing job script: %s' % (job_id, command_line))

            proc = subprocess.Popen(args=command_line,
                                    shell=True,
                                    cwd=job_wrapper.working_directory,
                                    stdout=stdout_file,
                                    stderr=stderr_file,
                                    # Removed: env
                                    preexec_fn=os.setpgrp)

            proc.terminated_by_shutdown = False
             # Removed: no current need for _proc_lock s
            try:
                job_wrapper.set_job_destination(job_wrapper.job_destination, proc.pid)
                job_wrapper.change_state(model.Job.states.RUNNING)

                # Removed: terminated check

                # Reap the process and get the exit code.
                exit_code = proc.wait()
                            
            # Begin change: Handle exception here   
            except Exception:
                log.warning("Failed to read exit code from process")
            # End change

            try:
                exit_code = int(open(exit_code_path, 'r').read())      
            except Exception:
                log.warning("Failed to read exit code from path %s" % exit_code_path)
                # Remove "pass"
                
            if proc.terminated_by_shutdown:
                self._fail_job_local(job_wrapper, "job terminated by Galaxy shutdown")
                return -1

            stdout_file.seek(0)
            stderr_file.seek(0)
            self.stdout = shrink_stream_by_size(stdout_file, DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True)
            self.stderr = shrink_stream_by_size(stderr_file, DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True)
            stdout_file.close()
            stderr_file.close()
            log.debug('execution finished: %s' % command_line)
        except Exception:
            log.exception("failure running job %d", job_wrapper.job_id)
            self._fail_job_local(job_wrapper, "failure running job")
            # Begin change: Return "Fail" exit code here
            return -1
            # End change
        # Begin change: Return exit code
        return exit_code
        # End change

    def recover(self, job, job_wrapper):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        job_id = job.get_job_runner_external_id()
        if job_id is None:
            self.put(job_wrapper)
            return
        self.prepare_job(job_wrapper)
        job_destination = job_wrapper.job_destination
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper, job_id=job_id, job_destination=job_destination)
        self.monitor_queue.put(ajs)

    # Copied from runners/local.py
    def _fail_job_local(self, job_wrapper, message):
        job_destination = job_wrapper.job_destination
        job_state = JobState(job_wrapper, job_destination)
        job_state.fail_message = message
        job_state.stop_job = False
        self.fail_job(job_state, exception=True)

    # Copied from runners/local.py with modifications
    def __command_line(self, job_wrapper):
        """
        """
        command_line = job_wrapper.runner_command_line

        # AMP: do not use local slots (differs from local.py)
        # slots would be cleaner name, but don't want deployers to see examples and think it
        # is going to work with other job runners.
        slots_statement = 'GALAXY_SLOTS="1"; export GALAXY_SLOTS;'

        job_id = job_wrapper.get_id_tag()
        job_file = JobState.default_job_file(job_wrapper.working_directory, job_id)
        exit_code_path = default_exit_code_file(job_wrapper.working_directory, job_id)
        job_script_props = {
            'slots_statement': slots_statement,
            'command': command_line,
            'exit_code_path': exit_code_path,
            'working_directory': job_wrapper.working_directory,
            'shell': job_wrapper.shell,
        }
        job_file_contents = self.get_job_file(job_wrapper, **job_script_props)
        self.write_executable_script(job_file, job_file_contents)
        return job_file, exit_code_path
    
