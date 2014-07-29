try:
    import xml.etree.cElementTree as et
except:
    import xml.etree.ElementTree as et

try:
    from galaxy.model import Job
    job_states = Job.states
except ImportError:
    # Not in Galaxy, map Galaxy job states to Pulsar ones.
    from galaxy.util import enum
    job_states = enum(RUNNING='running', OK='complete', QUEUED='queued')

from ..job import BaseJobExec

__all__ = ('Torque',)

from logging import getLogger
log = getLogger(__name__)

argmap = {'destination': '-q',
          'Execution_Time': '-a',
          'Account_Name': '-A',
          'Checkpoint': '-c',
          'Error_Path': '-e',
          'Group_List': '-g',
          'Hold_Types': '-h',
          'Join_Paths': '-j',
          'Keep_Files': '-k',
          'Resource_List': '-l',
          'Mail_Points': '-m',
          'Mail_Users': '-M',
          'Job_Name': '-N',
          'Output_Path': '-o',
          'Priority': '-p',
          'Rerunable': '-r',
          'Shell_Path_List': '-S',
          'job_array_request': '-t',
          'User_List': '-u',
          'Variable_List': '-v'}


class Torque(BaseJobExec):

    def __init__(self, **params):
        self.params = {}
        for k, v in params.items():
            self.params[k] = v

    def job_script_kwargs(self, ofile, efile, job_name):
        pbsargs = {'-o': ofile,
                   '-e': efile,
                   '-N': job_name}
        for k, v in self.params.items():
            if k == 'plugin':
                continue
            try:
                if not k.startswith('-'):
                    k = argmap[k]
                pbsargs[k] = v
            except:
                log.warning('Unrecognized long argument passed to Torque CLI plugin: %s' % k)
        template_pbsargs = ''
        for k, v in pbsargs.items():
            template_pbsargs += '#PBS %s %s\n' % (k, v)
        return dict(headers=template_pbsargs)

    def submit(self, script_file):
        return 'qsub %s' % script_file

    def delete(self, job_id):
        return 'qdel %s' % job_id

    def get_status(self, job_ids=None):
        return 'qstat -x'

    def get_single_status(self, job_id):
        return 'qstat -f %s' % job_id

    def parse_status(self, status, job_ids):
        # in case there's noise in the output, find the big blob 'o xml
        tree = None
        rval = {}
        for line in status.strip().splitlines():
            try:
                tree = et.fromstring(line.strip())
                assert tree.tag == 'Data'
                break
            except Exception:
                tree = None
        if tree is None:
            log.warning('No valid qstat XML return from `qstat -x`, got the following: %s' % status)
            return None
        else:
            for job in tree.findall('Job'):
                id = job.find('Job_Id').text
                if id in job_ids:
                    state = job.find('job_state').text
                    # map PBS job states to Galaxy job states.
                    rval[id] = self._get_job_state(state)
        return rval

    def parse_single_status(self, status, job_id):
        for line in status.splitlines():
            line = line.split(' = ')
            if line[0] == 'job_state':
                return self._get_job_state(line[1].strip())
        # no state found, job has exited
        return job_states.OK

    def _get_job_state(self, state):
        try:
            return {
                'E': job_states.RUNNING,
                'R': job_states.RUNNING,
                'Q': job_states.QUEUED,
                'C': job_states.OK
            }.get(state)
        except KeyError:
            raise KeyError("Failed to map torque status code [%s] to job state." % state)
