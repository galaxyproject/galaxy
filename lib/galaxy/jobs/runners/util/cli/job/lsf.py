# A simple CLI runner for slurm that can be used when running Galaxy from a
# non-submit host and using a Slurm cluster.
from logging import getLogger

try:
    from galaxy.model import Job
    job_states = Job.states
except ImportError:
    # Not in Galaxy, map Galaxy job states to Pulsar ones.
    from pulsar.util import enum
    job_states = enum(RUNNING='running', OK='complete', QUEUED='queued', ERROR="failed")

from ..job import BaseJobExec

log = getLogger(__name__)

argmap = {
    'memory': '-M',
    'cores': '-n',
    'queue': '-q',
    'working_dir': '-cwd'
}


class LSF(BaseJobExec):

    def __init__(self, **params):
        self.params = {}
        for k, v in params.items():
            self.params[k] = v

    def job_script_kwargs(self, ofile, efile, job_name):
        scriptargs = {'-o': ofile,
                      '-e': efile,
                      '-J': job_name}

        # Map arguments using argmap.
        for k, v in self.params.items():
            if k == 'plugin':
                continue
            try:
                if not k.startswith('-'):
                    k = argmap[k]
                if k == 'memory':
                    # Memory requires both -m and -R rusage[mem=v] request
                    scriptargs['-R'] = "\"rusage[mem=%s]\"" % v
                scriptargs[k] = v
            except Exception:
                log.warning('Unrecognized long argument passed to LSF CLI plugin: %s' % k)

        # Generated template.
        template_scriptargs = ''
        for k, v in scriptargs.items():
            template_scriptargs += '#BSUB %s %s\n' % (k, v)
        return dict(headers=template_scriptargs)

    def submit(self, script_file):
        # bsub returns Job <9147983> is submitted to default queue <research-rh7>.
        # This should be really handled outside with something like
        # parse_external. Currently CLI runner expect this to just send it in the last position
        # of the string.
        return "bsub <%s | awk '{ print $2}' | sed 's/[<>]//g'" % script_file

    def delete(self, job_id):
        return 'bstop %s' % job_id

    def get_status(self, job_ids=None):
        return "bjobs -o \"id stat delimiter='^'\" -noheader"  # check this

    def get_single_status(self, job_id):
        return "bjobs -o stat -noheader " + job_id

    def parse_status(self, status, job_ids):
        # Get status for each job, skipping header.
        rval = {}
        for line in status.splitlines()[1:]:
            id, state = line.split('^')
            if id in job_ids:
                # map job states to Galaxy job states.
                rval[id] = self._get_job_state(state)
        return rval

    def parse_single_status(self, status, job_id):
        if "is not found" in status:
            raise Exception("Job %s not found in LSF" % job_id)
        return self._get_job_state(status)

    def _get_job_state(self, state):
        # based on:
        # https://www.ibm.com/support/knowledgecenter/en/SSETD4_9.1.3/lsf_admin/job_state_lsf.html
        # https://www.ibm.com/support/knowledgecenter/en/SSETD4_9.1.2/lsf_command_ref/bjobs.1.html
        try:
            return {
                'EXIT': job_states.ERROR,
                'RUN': job_states.RUNNING,
                'PEND': job_states.QUEUED,
                'DONE': job_states.OK,
                'PSUSP': job_states.ERROR,
                'USUSP': job_states.ERROR,
                'SSUSP': job_states.ERROR,
                'UNKWN': job_states.ERROR,
                'WAIT' : job_states.QUEUED,
                'ZOMBI' : job_states.ERROR
            }.get(state)
        except KeyError:
            raise KeyError("Failed to map LSF status code [%s] to job state." % state)


__all__ = ('LSF',)
