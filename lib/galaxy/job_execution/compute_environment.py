import os
from abc import (
    ABCMeta,
    abstractmethod,
)
from typing import (
    Any,
    TypedDict,
)

from galaxy.job_execution.datasets import DeferrableObjectsT
from galaxy.job_execution.setup import JobIO
from galaxy.model import (
    Dataset,
    Job,
    MetadataFile,
)


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
    def input_metadata_rewrite(self, dataset, metadata_name: str, metadata_file: MetadataFile):
        """Path rewrite for the input dataset's metadata file of this name."""

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

    def input_metadata_rewrite(self, dataset, metadata_name: str, metadata_file: MetadataFile):
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


class RemoteEvaluationPaths(TypedDict):
    """Compute paths of a job's files, the contents of ``compute_environment.json``."""

    datasets: dict[str, str]
    extra_files: dict[str, str]
    metadata_files: dict[str, str]
    unstructured: dict[str, str]


class RemoteComputeEnvironment(SharedComputeEnvironment):
    """Resolve job files through the compute paths Galaxy recorded for remote tool evaluation.

    Files are looked up by database ids, which the imported job model keeps, so evaluation
    needs no object store.
    """

    def __init__(self, job_io: JobIO, job: Job, paths: RemoteEvaluationPaths):
        super().__init__(job_io, job)
        self.paths = paths

    def input_path_rewrite(self, dataset):
        path = self.paths["datasets"].get(str(dataset.dataset.id))
        if path is None:
            # Deferred inputs are materialized by the evaluator, into files outside the object store.
            return super().input_path_rewrite(dataset)
        return path

    def output_path_rewrite(self, dataset):
        return self.paths["datasets"][str(dataset.dataset.id)]

    def input_extra_files_rewrite(self, dataset):
        path = self.paths["extra_files"].get(str(dataset.dataset.id))
        if path is None:
            return super().input_extra_files_rewrite(dataset)
        return path

    def input_metadata_rewrite(self, dataset, metadata_name: str, metadata_file: MetadataFile):
        return self.paths["metadata_files"].get(metadata_file_key(dataset, metadata_name))

    def unstructured_path_rewrite(self, path):
        return self.paths["unstructured"].get(path)


def metadata_file_key(dataset_instance, metadata_name: str) -> str:
    # Metadata file uuids may be missing or shared between rows, and their ids aren't exported.
    return f"{dataset_instance.__class__.__name__}:{dataset_instance.id}:{metadata_name}"


def remote_evaluation_paths(
    job_io: JobIO, compute_environment: ComputeEnvironment, unstructured: dict[str, str] | None = None
) -> RemoteEvaluationPaths:
    """Record where the job's files are for the compute environment, by dataset id and metadata name."""
    datasets: dict[str, str] = {}
    extra_files: dict[str, str] = {}
    metadata_files: dict[str, str] = {}
    for dataset in job_io.get_input_datasets():
        if dataset.state == Dataset.states.DEFERRED:
            # The evaluator materializes these.
            continue
        assert dataset.dataset
        dataset_id = str(dataset.dataset.id)
        datasets[dataset_id] = compute_environment.input_path_rewrite(dataset) or str(job_io.get_input_path(dataset))
        if dataset.dataset.extra_files_path_exists():
            extra_files[dataset_id] = compute_environment.input_extra_files_rewrite(dataset)
        for name, value in dataset.metadata.items():
            if isinstance(value, MetadataFile):
                metadata_files[metadata_file_key(dataset, name)] = (
                    compute_environment.input_metadata_rewrite(dataset, name, value) or value.get_file_name()
                )
    for output_dataset, path in job_io.get_output_hdas_and_fnames().values():
        assert output_dataset.dataset
        datasets[str(output_dataset.dataset.id)] = compute_environment.output_path_rewrite(output_dataset) or str(path)
    return {
        "datasets": datasets,
        "extra_files": extra_files,
        "metadata_files": metadata_files,
        "unstructured": unstructured or {},
    }
