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

__all__ = ('LocalJobRunner', )

DEFAULT_POOL_SLEEP_TIME = 1
# TODO: Set to false and just get rid of this option. It would simplify this
# class nicely. -John
DEFAULT_EMBED_METADATA_IN_JOB = True


class LocalJobRunner(BaseJobRunner):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "LocalRunner"

    def __init__(self, app, nworkers):
        """Start the job runner """

        # create a local copy of os.environ to use as env for subprocess.Popen
        self._environ = os.environ.copy()
        self._proc_lock = threading.Lock()
        self._procs = []

        # Set TEMP if a valid temp value is not already set
        if not ('TMPDIR' in self._environ or 'TEMP' in self._environ or 'TMP' in self._environ):
            self._environ['TEMP'] = os.path.abspath(tempfile.gettempdir())

        super(LocalJobRunner, self).__init__(app, nworkers)
        self._init_worker_threads()

    def __command_line(self, job_wrapper):
        """
        """
        command_line = job_wrapper.runner_command_line

        # slots would be cleaner name, but don't want deployers to see examples and think it
        # is going to work with other job runners.
        slots = job_wrapper.job_destination.params.get("local_slots", None) or os.environ.get("GALAXY_SLOTS", None)
        if slots:
            slots_statement = 'GALAXY_SLOTS="%d"; export GALAXY_SLOTS; GALAXY_SLOTS_CONFIGURED="1"; export GALAXY_SLOTS_CONFIGURED;' % (int(slots))
        else:
            slots_statement = 'GALAXY_SLOTS="1"; export GALAXY_SLOTS;'

        job_id = job_wrapper.get_id_tag()
        job_file = JobState.default_job_file(job_wrapper.working_directory, job_id)
        exit_code_path = JobState.default_exit_code_file(job_wrapper.working_directory, job_id)
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

    def queue_job(self, job_wrapper):
        if not self._prepare_job_local(job_wrapper):
            return

        stderr = stdout = ''
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
                                    env=self._environ,
                                    preexec_fn=os.setpgrp)

            proc.terminated_by_shutdown = False
            with self._proc_lock:
                self._procs.append(proc)

            try:
                job_wrapper.set_job_destination(job_wrapper.job_destination, proc.pid)
                job_wrapper.change_state(model.Job.states.RUNNING)

                terminated = self.__poll_if_needed(proc, job_wrapper, job_id)
                if terminated:
                    return

                # Reap the process and get the exit code.
                exit_code = proc.wait()

            finally:
                with self._proc_lock:
                    self._procs.remove(proc)

            try:
                exit_code = int(open(exit_code_path, 'r').read())
            except Exception:
                log.warning("Failed to read exit code from path %s" % exit_code_path)
                pass

            if proc.terminated_by_shutdown:
                self._fail_job_local(job_wrapper, "job terminated by Galaxy shutdown")
                return

            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout = shrink_stream_by_size(stdout_file, DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True)
            stderr = shrink_stream_by_size(stderr_file, DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True)
            stdout_file.close()
            stderr_file.close()
            log.debug('execution finished: %s' % command_line)
        except Exception:
            log.exception("failure running job %d", job_wrapper.job_id)
            self._fail_job_local(job_wrapper, "failure running job")
            return

        self._handle_metadata_if_needed(job_wrapper)

        job_destination = job_wrapper.job_destination
        job_state = JobState(job_wrapper, job_destination)
        job_state.stop_job = False
        # Finish the job!
        try:
            self._finish_or_resubmit_job(job_state, stdout, stderr, exit_code)
        except Exception:
            log.exception("Job wrapper finish method failed")
            self._fail_job_local(job_wrapper, "Unable to finish job")

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
        if not self._check_pid(pid):
            log.warning("stop_job(): %s: PID %d was already dead or can't be signaled" % (job.id, pid))
            return
        for sig in [15, 9]:
            try:
                os.killpg(pid, sig)
            except OSError as e:
                log.warning("stop_job(): %s: Got errno %s when attempting to signal %d to PID %d: %s" % (job.id, errno.errorcode[e.errno], sig, pid, e.strerror))
                return  # give up
            sleep(2)
            if not self._check_pid(pid):
                log.debug("stop_job(): %s: PID %d successfully killed with signal %d" % (job.id, pid, sig))
                return
        else:
            log.warning("stop_job(): %s: PID %d refuses to die after signaling TERM/KILL" % (job.id, pid))

    def recover(self, job, job_wrapper):
        # local jobs can't be recovered
        job_wrapper.change_state(model.Job.states.ERROR, info="This job was killed when Galaxy was restarted.  Please retry the job.")

    def shutdown(self):
        super(LocalJobRunner, self).shutdown()
        with self._proc_lock:
            for proc in self._procs:
                proc.terminated_by_shutdown = True
                self._terminate(proc)

    def _fail_job_local(self, job_wrapper, message):
        job_destination = job_wrapper.job_destination
        job_state = JobState(job_wrapper, job_destination)
        job_state.fail_message = message
        job_state.stop_job = False
        self.fail_job(job_state, exception=True)

    def _handle_metadata_if_needed(self, job_wrapper):
        if not self._embed_metadata(job_wrapper):
            self._handle_metadata_externally(job_wrapper, resolve_requirements=True)

    def _embed_metadata(self, job_wrapper):
        job_destination = job_wrapper.job_destination
        embed_metadata = asbool(job_destination.params.get("embed_metadata_in_job", DEFAULT_EMBED_METADATA_IN_JOB))
        return embed_metadata

    def _prepare_job_local(self, job_wrapper):
        return self.prepare_job(job_wrapper, include_metadata=self._embed_metadata(job_wrapper))

    def _check_pid(self, pid):
        try:
            os.kill(pid, 0)
            return True
        except OSError as e:
            if e.errno == errno.ESRCH:
                log.debug("_check_pid(): PID %d is dead" % pid)
            else:
                log.warning("_check_pid(): Got errno %s when attempting to check PID %d: %s" % (errno.errorcode[e.errno], pid, e.strerror))
            return False

    def _terminate(self, proc):
        os.killpg(proc.pid, 15)
        sleep(1)
        if proc.poll() is None:
            os.killpg(proc.pid, 9)
        return proc.wait()  # reap

    def __poll_if_needed(self, proc, job_wrapper, job_id):
        # Only poll if needed (i.e. job limits are set)
        if not job_wrapper.has_limits():
            return

        job_start = datetime.datetime.now()
        i = 0
        # Iterate until the process exits, periodically checking its limits
        while proc.poll() is None:
            i += 1
            if (i % 20) == 0:
                limit_state = job_wrapper.check_limits(runtime=datetime.datetime.now() - job_start)
                if limit_state is not None:
                    job_wrapper.fail(limit_state[1])
                    log.debug('(%s) Terminating process group' % job_id)
                    self._terminate(proc)
                    return True
            else:
                sleep(DEFAULT_POOL_SLEEP_TIME)
