import os
from abc import (
    ABCMeta,
    abstractmethod,
)
from typing import (
    Any,
    TYPE_CHECKING,
)

from galaxy.job_execution.datasets import DeferrableObjectsT
from galaxy.job_execution.setup import JobIO
from galaxy.model import Job

if TYPE_CHECKING:
    from galaxy.job_execution.protection import ProtectionPlan


def dataset_path_to_extra_path(path: str) -> str:
    base_path = path[0 : -len(".dat")]
    return f"{base_path}_files"


class ComputeEnvironment(metaclass=ABCMeta):
    """Definition of the job as it will be run on the (potentially) remote
    compute server.
    """

    def __init__(self):
        self.materialized_objects: dict[str, DeferrableObjectsT] = {}

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

    def container_path_rewrite(self, path):
        """Rewrite a resolved container image path for the compute environment.

        No-op by default; overridden where Galaxy and the compute environment
        may resolve container images at different filesystem paths (e.g. Pulsar
        in ``rewrite_parameters`` mode).
        """
        return None

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
    def get_file_sources_dict(self) -> dict[str, Any]:
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

    def get_file_sources_dict(self) -> dict[str, Any]:
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


class ProtectedInputsComputeEnvironment(ComputeEnvironment):
    """Point the tool at decrypted copies of protected inputs, delegate everything else.

    The decrypted copies are produced on the compute host before the tool runs, as
    described by the job's :class:`~galaxy.job_execution.protection.ProtectionPlan`.
    """

    def __init__(self, base: ComputeEnvironment, plan: "ProtectionPlan"):
        self.base = base
        self.plan = plan

    def __getattr__(self, name: str) -> Any:
        # Runner specific attributes, e.g. Pulsar's path mapper.
        return getattr(self.base, name)

    @property
    def materialized_objects(self) -> dict[str, DeferrableObjectsT]:
        return self.base.materialized_objects

    @materialized_objects.setter
    def materialized_objects(self, value: dict[str, DeferrableObjectsT]) -> None:
        # Set by the tool evaluator, read by runners from the environment they created.
        self.base.materialized_objects = value

    def input_path_rewrite(self, dataset):
        base_path = self.base.input_path_rewrite(dataset)
        protected_input = self.plan.staged_input(dataset.dataset.id)
        return protected_input.primary.staged_path if protected_input else base_path

    def input_extra_files_rewrite(self, dataset):
        base_path = self.base.input_extra_files_rewrite(dataset)
        protected_input = self.plan.staged_input(dataset.dataset.id)
        return protected_input.staged_extra_files_path if protected_input else base_path

    def output_names(self):
        return self.base.output_names()

    def output_path_rewrite(self, dataset):
        return self.base.output_path_rewrite(dataset)

    def output_extra_files_rewrite(self, dataset):
        return self.base.output_extra_files_rewrite(dataset)

    def input_metadata_rewrite(self, dataset, metadata_value):
        return self.base.input_metadata_rewrite(dataset, metadata_value)

    def unstructured_path_rewrite(self, path):
        return self.base.unstructured_path_rewrite(path)

    def container_path_rewrite(self, path):
        return self.base.container_path_rewrite(path)

    def working_directory(self):
        return self.base.working_directory()

    def config_directory(self):
        return self.base.config_directory()

    def env_config_directory(self):
        return self.base.env_config_directory()

    def sep(self):
        return self.base.sep()

    def new_file_path(self):
        return self.base.new_file_path()

    def tool_directory(self):
        return self.base.tool_directory()

    def version_path(self):
        return self.base.version_path()

    def home_directory(self):
        return self.base.home_directory()

    def tmp_directory(self):
        return self.base.tmp_directory()

    def galaxy_url(self):
        return self.base.galaxy_url()

    def get_file_sources_dict(self) -> dict[str, Any]:
        return self.base.get_file_sources_dict()
