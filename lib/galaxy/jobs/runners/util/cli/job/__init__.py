"""
Abstract base class for cli job plugins.
"""

from abc import (
    ABCMeta,
    abstractmethod,
)
from enum import Enum
from typing import (
    Dict,
    List,
)

from typing_extensions import TypeAlias

try:
    from galaxy.model import Job

    job_states: TypeAlias = Job.states
except ImportError:
    # Not in Galaxy, map Galaxy job states to Pulsar ones.
    class job_states(str, Enum):  # type: ignore[no-redef]
        RUNNING = "running"
        OK = "complete"
        QUEUED = "queued"
        ERROR = "failed"


class BaseJobExec(metaclass=ABCMeta):
    def __init__(self, **params):
        """
        Constructor for CLI job executor.
        """
        self.params = params.copy()

    def job_script_kwargs(self, ofile, efile, job_name):
        """Return extra keyword argument for consumption by job script
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
    def parse_status(self, status: str, job_ids: List[str]) -> Dict[str, job_states]:
        """
        Parse the statuses of output from get_status command.
        """

    @abstractmethod
    def parse_single_status(self, status: str, job_id: str) -> job_states:
        """
        Parse the status of output from get_single_status command.
        """

    def get_failure_reason(self, job_id):
        """
        Return the failure reason for the given job_id.
        """
        return None

    def parse_failure_reason(self, reason, job_id):
        """
        Parses the failure reason, assigning it against a
        """
        return None


__all__ = (
    "BaseJobExec",
    "job_states",
)
