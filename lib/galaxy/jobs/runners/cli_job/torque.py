"""
Command-line interface to TORQUE PBS
"""

import os
import logging

from galaxy.model import Job
job_states = Job.states

from galaxy.jobs.runners.cli_job import BaseJobExec

log = logging.getLogger( __name__ )

__all__ = ('Torque',)

try:
    import xml.etree.cElementTree as et
except:
    import xml.etree.ElementTree as et

job_template = """#!/bin/sh
%s
GALAXY_LIB="%s"
if [ "$GALAXY_LIB" != "None" ]; then
    if [ -n "$PYTHONPATH" ]; then
        export PYTHONPATH="$GALAXY_LIB:$PYTHONPATH"
    else
        export PYTHONPATH="$GALAXY_LIB"
    fi
fi
%s
cd %s
%s
echo $? > %s
"""

argmap = { 'Execution_Time'     : '-a',
           'Account_Name'       : '-A',
           'Checkpoint'         : '-c',
           'Error_Path'         : '-e',
           'Group_List'         : '-g',
           'Hold_Types'         : '-h',
           'Join_Paths'         : '-j',
           'Keep_Files'         : '-k',
           'Resource_List'      : '-l',
           'Mail_Points'        : '-m',
           'Mail_Users'         : '-M',
           'Job_Name'           : '-N',
           'Output_Path'        : '-o',
           'Priority'           : '-p',
           'Rerunable'          : '-r',
           'Shell_Path_List'    : '-S',
           'job_array_request'  : '-t',
           'User_List'          : '-u',
           'Variable_List'      : '-v' }

class Torque(BaseJobExec):
    def __init__(self, **params):
        self.params = {}
        for k, v in params.items():
            self.params[k] = v

    def get_job_template(self, ofile, efile, job_name, job_wrapper, command_line, ecfile):
        pbsargs = { '-o' : ofile,
                    '-e' : efile,
                    '-N' : job_name }
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
        return job_template % (template_pbsargs,
                               job_wrapper.galaxy_lib_dir,
                               job_wrapper.get_env_setup_clause(),
                               os.path.abspath(job_wrapper.working_directory),
                               command_line,
                               ecfile)

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
            except Exception, e:
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
                    rval[id] = self.__get_job_state(state)
        return rval

    def parse_single_status(self, status, job_id):
        for line in status.splitlines():
            line = line.split(' = ')
            if line[0] == 'job_state':
                return line[1]
        # no state found, job has exited
        return job_states.OK

    def __get_job_state(self, state):
        return { 'R' : job_states.RUNNING,
                 'Q' : job_states.QUEUED }.get(state, state)
