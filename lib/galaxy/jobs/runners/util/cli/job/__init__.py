"""
Abstract base class for cli job plugins.
"""
from abc import ABCMeta, abstractmethod


class BaseJobExec(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, **params):
        """
        Constructor for CLI job executor.
        """

    def job_script_kwargs(self, ofile, efile, job_name):
        """ Return extra keyword argument for consumption by job script
        module.
        """
        return {}

    @abstractmethod
    def submit(self, script_file):
        """
        Given specified script_file path, yield command to submit it
        to external job manager.
        """

    @abstractmethod
    def delete(self, job_id):
        """
        Given job id, return command to stop execution or dequeue specified
        job.
        """

    @abstractmethod
    def get_status(self, job_ids=None):
        """
        Return command to get statuses of specified job ids.
        """

    @abstractmethod
    def get_single_status(self, job_id):
        """
        Return command to get the status of a single, specified job.
        """

    @abstractmethod
    def parse_status(self, status, job_ids):
        """
        Parse the statuses of output from get_status command.
        """

    @abstractmethod
    def parse_single_status(self, status, job_id):
        """
        Parse the status of output from get_single_status command.
        """
