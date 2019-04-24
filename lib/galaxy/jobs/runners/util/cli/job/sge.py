from logging import getLogger
try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et

try:
    from galaxy.model import Job
    job_states = Job.states
except ImportError:
    # Not in Galaxy, map Galaxy job states to Pulsar ones.
    from pulsar.util import enum
    job_states = enum(RUNNING='running', OK='complete', QUEUED='queued')

from ..job import BaseJobExec

log = getLogger(__name__)

ERROR_MESSAGE_UNRECOGNIZED_ARG = 'Unrecognized long argument passed to sge CLI plugin: %s'

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


class Sge(BaseJobExec):

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
            except KeyError:
                log.warning(ERROR_MESSAGE_UNRECOGNIZED_ARG % k)
        template_pbsargs = ''
        for k, v in pbsargs.items():
            template_pbsargs += '#PBS %s %s\n' % (k, v)
        return dict(headers=template_pbsargs)

    def submit(self, script_file):
        return 'qsub %s' % script_file

    def delete(self, job_id):
        return 'qdel %s' % job_id

    def get_status(self, job_ids=None):
        return 'qstat -q IIHG, UI -g d -xml'

    def get_single_status(self, job_id):
        return 'qstat -j %s' % job_id

    def parse_status(self, status, job_ids):
        # in case there's noise in the output, find the big blob 'o xml
        rval = {}
        try:
            tree = et.fromstring(status)
            assert tree.tag == 'job_info'
        except Exception:
            log.warning('No valid qstat XML return from `qstat -xml`, got the following: %s' % status)
            return None
        for queue_info in tree.findall('queue_info'):
            for job in queue_info.findall('job_list'):
                id = job.find('JB_job_number').text
                if id in job_ids:
                    state = job.find('state').text.upper()
                    # map PBS job states to Galaxy job states.
                    rval[id] = self._get_job_state(state)
        return rval

    def parse_single_status(self, status, job_id):
        for line in status.splitlines():
            line = line.split(' = ')
            if line[0].strip() == 'job_state':
                return self._get_job_state(line[1].strip())
        # no state found, job has exited
        return job_states.OK

    def _get_job_state(self, state):
        try:
            return {
                'E': job_states.ERROR,
                'R': job_states.RUNNING,
                'Q': job_states.QUEUED,
                'C': job_states.OK
            }.get(state)
        except KeyError:
            raise KeyError("Failed to map sge status code [%s] to job state." % state)


__all__ = ('Sge',)
