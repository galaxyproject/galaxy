"""
Kind of fail save job control via the DRMAA API.
Tested for UNIVA grid engine
"""
import drmaa
import logging
import os
import re
import signal
import subprocess
import time

from galaxy import model
from galaxy.jobs.runners.drmaa import DRMAAJobRunner

log = logging.getLogger( __name__ )

__all__ = ( 'DRMAAUnivaJobRunner', )

MEMORY_LIMIT_SCAN_SIZE = 1024 * 1024  # 1MB

"""
TODO
find out what it means if there is no error code file (.ec)
can this also be used

tool wrapper:
- A tool that is the bash script itself.
- bash script (create long array, dd into variable)
- C
- C++
- python
- java
- perl
"""


class DRMAAUnivaJobRunner( DRMAAJobRunner ):
    runner_name = "DRMAAUnivaRunner"
    # restrict job name length as in the DRMAAJobRunner
    # restrict_job_name_length = 15

    def _complete_terminal_job( self, ajs, drmaa_state, **kwargs ):
        def _get_drmaa_state_with_qstat(job_id, job_info):
            """
            get job state with qstat. qstat only returns infos for jobs that
            are queued, suspended, ..., or just finished (i.e. jobs are still
            in the system).
            information on finished jobs can only be found by qacct
            or in the spool directories of the GE.
            Hence if qstat does print an appropriate error message
            the state is assumed as FINISHED
            job_id the job id
            adds the states (ABORTED|RUNNING|SUSPENDED|PENDING|FINISHED) to
                job_info['states']
            """
            # from man qstat for the jobs status output if called with qstat -j ID
            # the  status of the job - one of
            # d(eletion),             qdel has been used
            # E(rror),                pending jobs hat couldn’t be started due to job properties
            # h(old),                 job currently is not eligible for execution due to a hold state assigned to it
            # r(unning),              job is about to be executed or is already executing
            # R(estarted),            the job was restarted. This can be caused by a job migration or because of one of the reasons described in the -r section
            # s(uspended),            caused by suspending the job via qmod -s
            # S(uspended),            either that the queue containing the job is suspended ... or that a pending job got suspended due to a preemptive action that was either triggered automatically by the system or by a manual preemption request triggered via qmod(1) -p ... S
            # e(N)hanced suspended,   preemptive states shown for pending jobs triggered either automatically or via qmod(1) -p ... N or -p ... P
            # (P)reempted,            -"-
            # t(ransfering),          job is about to be executed or is already executing
            # T(hreshold) or          shows that at least one suspend threshold of the corresponding queue was exceeded (see queue_conf(5)) and that the job has been suspended as a consequence
            # w(aiting).              or that the job is waiting for completion of the jobs to which job dependencies have been assigned to the job
            #
            # Note:
            # - For finished jobs an error message is given:
            #   Following jobs do not exist or permissions are not sufficient:
            #   264210
            #   -> Hence we can not determine with qstat if the job is in DONE (successfully) or FAILED state
            # - For queued jobs there is no output of the job_state
            #   This could be obtained using qstat without the

#             dE drmaa.JobState.UNDETERMINED: 'process status cannot be determined',
#             drmaa.JobState.QUEUED_ACTIVE: 'job is queued and active',
#             h drmaa.JobState.SYSTEM_ON_HOLD: 'job is queued and in system hold',
#             w drmaa.JobState.USER_ON_HOLD: 'job is queued and in user hold',
#             drmaa.JobState.USER_SYSTEM_ON_HOLD: 'job is queued and in user and system hold',
#             rRt drmaa.JobState.RUNNING: 'job is running',
#             SNPT drmaa.JobState.SYSTEM_SUSPENDED: 'job is system suspended',
#             s drmaa.JobState.USER_SUSPENDED: 'job is user suspended',
#             drmaa.JobState.DONE: 'job finished normally',
#             drmaa.JobState.FAILED: 'job finished, but failed',
            qstat_states = dict(d="ABORTED", t="RUNNING", r="RUNNING" ,
                                s="SUSPENDED", S="SUSPENDED", N="SUSPENDED",
                                P="SUSPENDED", T="SUSPENDED",
                                R="RUNNING",
                                w="PENDING", h="PENDING",
                                E="PENDING")
            cmd = ['qstat', '-j', job_id]
            p = subprocess.Popen( cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
            stdout, stderr = p.communicate()
            # the return code of qstat or stderr is not checked directly
            # because if an invalid jobid is given (e.g. for a finished job)
            # return code is 1 and stderr is
            # "Following jobs do not exist or permissions are not sufficient:
            # 264210"
            # hence it is checked if the stdout/stderr contains the job_id
            jobnumber = None
            se = []
            # try to get jobid from stderr
            for line in stderr:
                se.append( line )
                if str(job_id) in line:
                    jobnumber = str(job_id)
            stderr = "\n".join(se)
            # get state
            for line in stdout:
                if not line.startswith("job_state"):
                    continue
                line = line.split()
                if not line[-1] in qstat_states:
                    log.exception( "DRMAAFS: job {job_id} has unknown state '{state}".format(job_id=job_id, state=line[2]) )
                job_info["state"] = qstat_states[ line[-1] ]
            # check sanity of qstat output
            if len(stderr) > 0:
                if jobnumber is not None and jobnumber == str(job_id):
                    job_info["state"] = "FINISHED"
                else:
                    stderr = stderr.strip()
                    log.exception( '`%s` returned %s, stderr: %s' % ( ' '.join( cmd ), p.returncode, stderr ) )
                    return False
            return True

        def _get_drmaa_state_with_qacct(job_id, job_info):
            '''
            get the job state with qacct
            job_info dict where state, signal, time_wasted, and memory_wasted can be stored
            return True in case of success and False otherwise
                - state is "ERROR", "SIGNAL", "ABORTED"
                - ERROR tool error (return code between 1 and 128 or job marked as failed)
                - SIGNAL tool killed by a signal (ie return code > 128)
                    then the signal is returned
                - ABORTED job was deleted (then signal is always "" even if
                    there is a signal [SIGKILL] reported from the GE)
            '''
            signals = dict((k, v) for v, k in reversed(sorted(signal.__dict__.items()))
               if v.startswith('SIG') and not v.startswith('SIG_'))
            cmd = ['qacct', '-j', job_id]
            p = subprocess.Popen( cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                stderr = stderr.strip()
                log.exception( '`%s` returned %s, stderr: %s' % ( ' '.join( cmd ), p.returncode, stderr ) )
                return False

            qacct = dict()
            for line in stdout:
                # remove header
                if line.startswith("="):
                    continue
                line = line.split()
                qacct[ line[0] ] = " ".join(line[1:])
            # qacct has three fields of interest: failed, exit_status, deleted_by
            # experiments
            #            failed  exit_status deleted_by
            # BASH ------------------------------------
            # time-limit 100     137
            # mem-limit  0       2
            # python --------------------------------------------------------------
            # time-limit
            # mem-limit
            # C -------------------------------------------------------------------
            # time-limit
            # mem-limit
            # C++ -----------------------------------------------------------------
            # time-limit
            # mem-limit
            # JAVA ----------------------------------------------------------------
            # time-limit
            # mem-limit
            # perl ----------------------------------------------------------------
            # time-limit
            # mem-limit
            # bash other tests ----------------------------------------------------
            # qdel       100     137          user@mail

            # deleted_by
            # If the job (the array task) has been deleted via qdel, "<username>@<hostname>", else
            # "NONE". If qdel was called multiple times, every invocation is recorded in a comma
            # separated list.
            if "deleted_by" in qacct and qacct["deleted_by"] is not None:
                logging.error( "DRMAAUniva: job {job_id} was aborted by {culprit}".format(job_id=job_id, culprit=qacct["deleted_by"]) )
                job_info["state"] = "ABORTED"
                return True

            # exit_status
            # Exit status of the job script (or Univa Grid Engine specific status in case of certain
            # error conditions). The exit status is determined by following the normal shell conventions
            # If the command terminates normally the value of the command is its exit status.
            # However, in the case that the command exits abnormally, a value of 0200 (octal), 128
            # (decimal) is added to the value of the command to make up the exit status.
            # For example: If a job dies through signal 9 (SIGKILL) then the exit status
            # becomes 128 + 9 = 137.
            if "exit_status" in qacct:
                qacct["exit_status"] = int(qacct["exit_status"])
                if qacct["exit_status"] < 1:
                    pass
                if 0 < qacct["exit_status"] < 129:
                    logging.error( "DRMAAUniva: job {job_id} has exit status {status}".format(job_id=job_id, status=qacct["exit_status"]) )
                    job_info["state"] = "ERROR"
                else:
                    logging.error( "DRMAAUniva: job {job_id} was killed by signal {signal}".format(job_id=job_id, signal=qacct["exit_status"] - 128) )
                    job_info["state"] "SIGNAL"
                    job_info["signal"] = signals[ qacct["exit_status"] - 128 ]

            # failed
            # Indicates the problem which occurred in case a job could not be started on the execution
            # host (e.g. because the owner of the job did not have a valid account on that
            # machine). If Univa Grid Engine tries to start a job multiple times, this may lead to
            # multiple entries in the accounting file corresponding to the same job ID.
            # for the codes see https://docs.oracle.com/cd/E19957-01/820-0699/chp11-2/index.html
            if "failed" in qacct:
                code = int(qacct["failed"].split()[0])
                if code == 0:
                    pass
                # this happens in case of a signal which is covered already
                if code == 100:
                    pass
                else:
                    logging.error( "DRMAAUniva: job {job_id} failed with failure {failure}".format(job_id=job_id, failure=qacct["failed"]) )
                    job_info["state"] = "ERROR"
            job_info["time_wasted"] = qacct["wallclock"]
            job_info["memory_wasted"] = qacct["maxvmem"]
            return True

        def _get_drmaa_state_with_wait( job_id, ds, job_info ):
            '''
            TRY to get the job state with the python-drmaa wait function
            this function will not work if the job was started as real user
            since the external runner uses a different drmaa session
            jobid: the jobid
            ds: drmaa session
            job_info dict where state, signal, time_wasted, and memory_wasted can be stored
            returns True in case of sucess and False otherwise (ie in case the drmaa library call)
                - state is one of ABORTED, SIGNAL, ERROR
                - ABORTED job has been aborted
                - SIGNAL signal received, signal is returned != ""
                - ERROR exitcode != 0, core dump, or unclear condition
            '''
            # experiments
            #            exitStatus coreDump hasExited hasSignal Signal  wasAborted
            # BASH ----------------------------------------------------------------
            # time-limit 0          0        0         1         SIGKILL 0
            # mem-limit  2          0        1         0                 0            with creating a large array and dd into variable
            # python --------------------------------------------------------------
            # time-limit 0          0        0         1         SIGKILL 0
            # mem-limit  1          0        1         0                 0
            # C -------------------------------------------------------------------
            # time-limit 0          0        0         1         SIGKILL 0
            # mem-limit  0          1        0         1         SIGSEGV 0          SegFault when accessing unallocated memory
            # C++ -----------------------------------------------------------------
            # time-limit 0          0        0         1         SIGKILL 0
            # mem-limit  0          1        0         1         SIGABRT 0          because of memory
            # JAVA ----------------------------------------------------------------
            # time-limit 0          0        0         1         SIGKILL 0
            # mem-limit  1          0        1         0                 0
            # perl ----------------------------------------------------------------
            # time-limit 0          0        0         0         SIGKILL 0
            # mem-limit  1          0        1         0                 0

            # bash other tests ----------------------------------------------------
            # no exit    0          0        1         0                 0
            # qdel       0          0        0         0                 1
            # TODO just return 0 if external runner is used
            # TODO do not run for running jobs
            try:
                rv = ds.session.wait(job_id, drmaa.Session.TIMEOUT_NO_WAIT)
            except Exception as e:
                logging.exception("could not determine status of job {jobid} using drmaa.wait error was {error}".format(jobid=job_id, error=str( e )))
                return False
            # documentation of the variables adapted from the drmaa C library documentation at
            # https://linux.die.net/man/3/drmaa_wait
            # currently not used are
            # - rv.jobId
            # - rv.resourceUsage (which contains info on runtime and memory usage)
            # - rv.hasSignal (since we test the terminatedSignal anyway, and the meaning
            #    of hasSignal=0 could be anything from success to failure)
            # - hasExited
            # ** wasAborted**
            # wasAborted is a non-zero value for a job that ended before entering the running state.
            # Note: seems to be non-zero also if it is already running
            # **exitStatus**
            # If hasExited is a non-zero value, the exitStatus variable gives the
            # exit code that the job passed to exit or the value that the child
            # process returned from main.
            # **hasCoreDump**
            # If hasSignal is a non-zero value, hasCoreDump is a non-zero value if a core image
            # of the terminated job was created.

            # **hasExited**
            # non-zero value for a job that terminated normally. A zero value can also indicate
            # that although the job has terminated normally, an exit status is not available,
            # or that it is not known whether the job terminated normally.
            # In both cases exitStatus will not provide exit status information.
            # A non-zero value returned in exited indicates more detailed diagnosis can be
            # provided by means of hasSignal, terminatedSignal and hasCoreDump.
            # **hasSignal**
            # non-zero integer for a job that terminated due to the receipt of a signal.
            # A zero value can also indicate that although the job has terminated due to the
            # receipt of a signal, the signal is not available, or it is not known whether
            # the job terminated due to the receipt of a signal.
            # In both cases terminatedSignal will not provide signal information.
            # A non-zero value returned in signaled indicates signal information can be
            # retrieved from terminatedSignal.
            # **terminatedSignal**
            # If hasSignal is a non-zero value, the terminatedSignal is a
            # a string representation of the signal that caused the termination
            # of the job. For signals declared by POSIX.1, the symbolic names
            # are returned (e.g., SIGABRT, SIGALRM).
            # For signals not declared by POSIX, any other string may be returned.
            # check if job was aborted
            if rv.wasAborted:
                logging.error( "DRMAAUniva: job {job_id} was aborted according to wait()".format(job_id=job_id) )
                job_info["state"] = "ABORTED"

            # determine if something went wrong. this could be application errors
            # but also violation of scheduler constraints
            if rv.exitStatus != 0:
                logging.error( "DRMAAUniva: job {job_id} has exit status {status}".format(job_id=job_id, status=rv.exitStatus) )
                job_info["state"] "ERROR"

            #
            if not rv.hasExited or rv.hasSignal:
                if rv.hasCoreDump != 0:
                    logging.error( "DRMAAUniva: job {job_id} has core dump".format(job_id=job_id) )
                    job_info["state"] = "ERROR"
                elif len(rv.terminatedSignal) > 0:
                    logging.error( "DRMAAUniva: job {job_id} was kill by signal {signal}".format(job_id=job_id, signal=rv.terminatedSignal) )
                    job_info["state"] "SIGNAL"
                    job_info["signal"] = rv.terminatedSignal
                elif rv.wasAborted == 0:
                    logging.error( "DRMAAUniva: job {job_id} has finished in unclear condition".format(job_id=job_id) )
                    job_info["state"] = "ERROR"
            # make use of this
            job_info["time_wasted"] = float(rv.resourceUsage['maxvmem'])
            job_info["memory_wasted"] = float(rv.resourceUsage['wallclock'])
            return True

        def _get_drmaa_state(job_id, ds):
            """
            get the state using qstat, wait, qacct using the above functions
            """
            # initialize job_info dict
            job_info = dict()
            # qacct for running / queued / ... jobs
            qstat = _get_drmaa_state_with_qstat(job_id, job_info)
            # if qstat was unsuccessful (we assume that something went wrong)
            # or the state is FINISHED or ERROR we run qacct or drmma_wait
            # to get more detailed info
            if not qstat or job_info["state"] in [ "FINISHED" ]:
                pass
            elif job_info["state"] in [ "RUNNING", "SUSPENDED", "PENDING" ]:
                return job_info
            else:
                logging.error( "DRMAAUniva: job {job_id} has unknown state {state}".format(job_id=job_id, state=job_info["state"]) )
            # run wait for ended (finished/error) jobs
            # if this fails (eg. for jobs started as system user get info using qacct)
            if not _get_drmaa_state_with_wait(job_id, ds, job_info):
                if not _get_drmaa_state_with_qacct(job_id, job_info):
                    logging.error( "DRMAAUniva: job {job_id} could not get info with qacct or drmaa.wait".format(job_id=job_id) )
            return job_info

        def _parse_native_specs( job_id, native_spec ):
            """
            determine requested run time and memory from native specs
            native_spec (e.g. h_rt=01:00:02 -l h_vmem=1G) the native
            job_id the job ID (only used for logging)
            specification string passed to GE
            return time,mem (or None,None if nothing found)
            """
            time = None
            mem = None
            # parse time
            m = re.search( "rt=([0-9]+):([0-9]{2}):([0-9]{2})\s", native_spec )
            if m is not None:
                time = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            else:
                m = re.search( "rt=([0-9]+)", native_spec )
                if m is not None:
                    time = int(m.group(1))
            # parse memory
            m = re.search( "mem=([0-9])([KGM]*)", native_spec )
            if m is not None:
                mem = int(m.group(1))
                if m.group(2) == 'K':
                    mem *= 1024
                elif m.group(2) == 'M':
                    mem *= 1024 * 1024
                elif m.group(2) == 'G':
                    mem *= 1024 * 1024 * 1024
                elif m.group(2) == '':
                    pass
                else:
                    logging.error( "DRMAAUniva: job {job_id} has unparsable memory native spec {spec}".format(job_id=job_id, spec=native_spec) )
            return time, mem

        job_info = _get_drmaa_state(ajs.job_id, self.ds)

        if "state" not in job_info or job_info["state"] in [ "SIGNAL", "ERROR" ]:
            # get configured job destination
            job_destination = ajs.job_wrapper.job_destination
            native_spec = job_destination.params.get('nativeSpecification', None)
            # determine time and memory that was granted for the job
            granted_time, granted_mem = _parse_native_specs( native_spec )

            # check if the output contains indicators for a memory violation
            memviolation = self.__check_memory_limit( ajs.error_file )
            # check job for run time or memory violation
            if ("signal" in job_info and job_info["signal"] == "SIGKILL") and job_info["wasted_time"] > granted_time:
                log.info( '(%s/%s) Job hit walltime', ajs.job_wrapper.get_id_tag(), ajs.job_id )
                ajs.fail_message = "This job was terminated because it ran longer than the maximum allowed job run time."
                ajs.runner_state = ajs.runner_states.WALLTIME_REACHED
            elif memviolation or job_info["wasted_time"] > granted_mem:
                log.info( '(%s/%s) Job hit memory limit', ajs.job_wrapper.get_id_tag(), ajs.job_id )
                ajs.fail_message = "This job was terminated because it used more than the maximum allowed memory."
                ajs.runner_state = ajs.runner_states.MEMORY_LIMIT_REACHED
        elif job_info["state"] in [ "RUNNING", "SUSPENDED", "PENDING" ]:
            log.warning( '(%s/%s) Job is %s, returning to monitor queue', ajs.job_wrapper.get_id_tag(), ajs.job_id, job_info["state"] )
            return True  # job was not actually terminal
        elif job_info["state"] in [ "ABORTED" ]:
            log.info( '(%s/%s) Job was cancelled (e.g. with qdel)', ajs.job_wrapper.get_id_tag(), ajs.job_id )
            ajs.fail_message = "This job failed because it was cancelled by an administrator."
            drmaa_state = self.drmaa_job_states.FAILED
        else:
            logging.error( "DRMAAUniva: job {job_id} determined unknown state {state}".format(job_id=ajs.job_id, spec=job_info["state"]) )
            drmaa_state = self.drmaa_job_states.DONE
        # by default, finish the job with the state from drmaa
        #
        return super( DRMAAUnivaJobRunner, self )._complete_terminal_job( ajs, drmaa_state=drmaa_state )

    def __check_memory_limit( self, efile_path ):
        """
        A very poor implementation of tail, but it doesn't need to be fancy
        since we are only searching the last 2K
        checks for an error message that indicates an memory constraint violation
        returns True if such an indicator is found and False otherwise
        """
        # list of error output from different programming languages in case
        # of memory allocation errors for bash, Python, C++, JAVA, Perl
        memerrors = set(["xrealloc: cannot allocate",
                         "MemoryError",
                         "std::bad_alloc",
                         "java.lang.OutOfMemoryError: Java heap space",
                         "Out of memory!"])

        try:
            log.debug( 'Checking %s for exceeded memory messages from programs', efile_path )
            with open( efile_path ) as f:
                if os.path.getsize(efile_path) > MEMORY_LIMIT_SCAN_SIZE:
                    f.seek(-MEMORY_LIMIT_SCAN_SIZE, os.SEEK_END)
                    f.readline()
                for line in f.readlines():
                    stripped_line = line.strip()
                    for err in memerrors:
                        if err in stripped_line:
                            return True
        except:
            log.exception('Error reading end of %s:', efile_path)

        return False
