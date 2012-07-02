"""
Base class for cli job plugins
"""

class BaseJobExec(object):
    def __init__(self, **params):
        raise NotImplementedError()
    def get_job_template(self, ofile, efile, job_name, job_wrapper, command_line, ecfile):
        raise NotImplementedError()
    def submit(self, script_file):
        raise NotImplementedError()
    def delete(self, job_id):
        raise NotImplementedError()
    def get_status(self, job_ids=None):
        raise NotImplementedError()
    def get_single_status(self, job_id):
        raise NotImplementedError()
    def parse_status(self, status, job_ids):
        raise NotImplementedError()
    def parse_single_status(self, status, job_id):
        raise NotImplementedError()
