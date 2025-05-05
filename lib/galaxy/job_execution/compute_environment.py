import os
from abc import (
    ABCMeta,
    abstractmethod,
)
from typing import (
    Any,
    Dict,
)

from galaxy.job_execution.datasets import DeferrableObjectsT
from galaxy.job_execution.setup import JobIO
from galaxy.model import Job


def dataset_path_to_extra_path(path: str) -> str:
    base_path = path[0 : -len(".dat")]
    return f"{base_path}_files"


class ComputeEnvironment(metaclass=ABCMeta):
    """Definition of the job as it will be run on the (potentially) remote
    compute server.
    """

    def __init__(self):
        self.materialized_objects: Dict[str, DeferrableObjectsT] = {}

    @abstractmethod
    def output_names(self):
        """Output unqualified filenames defined by job."""

    @abstractmethod
    def input_path_rewrite(self, dataset):
        """Input path for specified dataset."""

    @abstractmethod
    def output_path_rewrite(self, dataset):
        """Output path for specified dataset."""

    @abstractmethod
    def input_extra_files_rewrite(self, dataset):
        """Input extra files path rewrite for specified dataset."""

    @abstractmethod
    def output_extra_files_rewrite(self, dataset):
        """Output extra files path rewrite for specified dataset."""

    @abstractmethod
    def input_metadata_rewrite(self, dataset, metadata_value):
        """Input metadata path rewrite for specified dataset."""

    @abstractmethod
    def unstructured_path_rewrite(self, path):
        """Rewrite loc file paths, etc.."""

    @abstractmethod
    def working_directory(self):
        """Job working directory (potentially remote)"""

    @abstractmethod
    def config_directory(self):
        """Directory containing config files (potentially remote)"""

    @abstractmethod
    def env_config_directory(self):
        """Working directory (possibly as environment variable evaluation)."""

    @abstractmethod
    def sep(self):
        """os.path.sep for the platform this job will execute in."""

    @abstractmethod
    def new_file_path(self):
        """Absolute path to dump new files for this job on compute server."""

    @abstractmethod
    def tool_directory(self):
        """Absolute path to tool files for this job on compute server."""

    @abstractmethod
    def version_path(self):
        """Location of the version file for the underlying tool."""

    @abstractmethod
    def home_directory(self):
        """Home directory of target job - none if HOME should not be set."""

    @abstractmethod
    def tmp_directory(self):
        """Temp directory of target job - none if HOME should not be set."""

    @abstractmethod
    def galaxy_url(self):
        """URL to access Galaxy API from for this compute environment."""

    @abstractmethod
    def get_file_sources_dict(self) -> Dict[str, Any]:
        """Return file sources dict for current user."""


class SimpleComputeEnvironment:
    def config_directory(self):
        return os.path.join(self.working_directory(), "configs")  # type: ignore[attr-defined]

    def sep(self):
        return os.path.sep


class SharedComputeEnvironment(SimpleComputeEnvironment, ComputeEnvironment):
    """Default ComputeEnvironment for job and task wrapper to pass
    to ToolEvaluator - valid when Galaxy and compute share all the relevant
    file systems.
    """

    job_id: JobIO
    job: Job

    def __init__(self, job_io: JobIO, job: Job):
        self.job_io = job_io
        self.job = job

    def get_file_sources_dict(self) -> Dict[str, Any]:
        return self.job_io.file_sources_dict

    def output_names(self):
        return self.job_io.get_output_basenames()

    def output_paths(self):
        return self.job_io.get_output_fnames()

    def input_path_rewrite(self, dataset):
        return str(self.job_io.get_input_path(dataset))

    def output_path_rewrite(self, dataset):
        return str(self.job_io.get_output_path(dataset))

    def input_extra_files_rewrite(self, dataset):
        input_path_rewrite = self.input_path_rewrite(dataset)
        return dataset_path_to_extra_path(input_path_rewrite)

    def output_extra_files_rewrite(self, dataset):
        output_path_rewrite = self.output_path_rewrite(dataset)
        return dataset_path_to_extra_path(output_path_rewrite)

    def input_metadata_rewrite(self, dataset, metadata_value):
        return None

    def unstructured_path_rewrite(self, path):
        return None

    def working_directory(self):
        return self.job_io.working_directory

    def env_config_directory(self):
        """Working directory (possibly as environment variable evaluation)."""
        return "$_GALAXY_JOB_DIR"

    def new_file_path(self):
        return self.job_io.new_file_path

    def version_path(self):
        return self.job_io.version_path

    def tool_directory(self):
        return self.job_io.tool_directory

    def home_directory(self):
        return self.job_io.home_directory

    def tmp_directory(self):
        return self.job_io.tmp_directory

    def galaxy_url(self):
        return self.job_io.galaxy_url
