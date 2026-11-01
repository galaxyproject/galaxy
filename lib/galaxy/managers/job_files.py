"""Read and write files of queued and running jobs on behalf of remote job runners."""

import os
import re
import shutil

from galaxy import (
    exceptions,
    util,
)
from galaxy.config import GalaxyAppConfiguration
from galaxy.job_execution.setup import (
    input_metadata_file_names,
    JobWorkingDirectory,
    restrict_job_files,
)
from galaxy.model import (
    Job,
    JobToInputDatasetAssociation,
    JobToInputLibraryDatasetAssociation,
    JobToOutputDatasetAssociation,
    JobToOutputLibraryDatasetAssociation,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.objectstore import BaseObjectStore
from galaxy.security.idencoding import IdEncodingHelper

APPENDABLE_FILE_NAMES = ("tool_stdout", "tool_stderr")
# Job directories Pulsar stages results back to: the tool working directory, ``outputs`` (datasets written there with
# ``outputs_to_working_directory``, tool streams, the version file) and the metadata directory.
RESTRICTED_WRITABLE_DIRECTORIES = ("working", "outputs", "metadata")
# The extended metadata model store, which Galaxy imports with permission to edit any object it names.
RESTRICTED_UNWRITABLE_DIRECTORY = ["metadata", "outputs_populated"]
# Written for extended metadata, holds the object store's credentials.
RESTRICTED_UNREADABLE_FILE = os.path.join("metadata", "object_store_conf.json")


class JobFilesManager:
    """Job runner access to low-level job files, authorized by job key only - never by user credentials.

    Reads aren't limited to the job's own files, since tools also read unstructured inputs such as ``.loc`` files -
    except for jobs ``restrict_job_files`` confines, whose runners may only read and write the job's own files.
    """

    def __init__(
        self,
        config: GalaxyAppConfiguration,
        security: IdEncodingHelper,
        object_store: BaseObjectStore,
        sa_session: galaxy_scoped_session,
    ):
        self._config = config
        self._security = security
        self._object_store = object_store
        self._sa_session = sa_session

    @property
    def upload_dir(self) -> str:
        return str(self._config.new_file_path)

    def readable_path(self, encoded_job_id: str, path: str | None, job_key: str | None) -> str:
        job, path = self._authorize(encoded_job_id, path, job_key)
        readable = not restrict_job_files(job) or self._is_job_file(job, path)
        if readable and os.path.isfile(path):
            return path
        if readable and os.path.exists(path):
            raise exceptions.RequestParameterInvalidException("Path does not refer to a file.")
        # Inputs may be purged while the job is queued or running; pulsar handles that error.
        if re.match(r"(galaxy_)?dataset_(.*)\.dat", os.path.basename(path)):
            input_datasets = [jtid.dataset.dataset for jtid in job.input_datasets if jtid.dataset]
            if any(dataset and dataset.purged for dataset in input_datasets):
                raise exceptions.ItemDeletionException("Input dataset(s) for job have been purged.")
        if not readable:
            raise exceptions.ItemAccessibilityException("Job is not authorized to read supplied path.")
        raise exceptions.ObjectNotFound("File not found.")

    def authorize_write(self, encoded_job_id: str, path: str | None, job_key: str | None) -> str:
        """Return a directory to stage uploads for ``path`` in - same filesystem, outside any extra files path."""
        job, path = self._authorize(encoded_job_id, path, job_key)
        if not os.path.isabs(path):
            raise exceptions.RequestParameterInvalidException("'path' parameter must be an absolute path.")
        if restrict_job_files(job):
            return self._authorize_restricted_write(job, path)
        working_directory = JobWorkingDirectory(job, self._object_store).resolve()
        if util.in_directory(path, working_directory):
            return working_directory
        if dataset_path := self._output_dataset_path(job, path):
            return os.path.dirname(dataset_path)
        raise exceptions.ItemAccessibilityException("Job is not authorized to write to supplied path.")

    def _authorize_restricted_write(self, job: Job, path: str) -> str:
        """Allow only the job's outputs and the job directories results are staged back to.

        Job scripts, ``configs/`` and ``inputs/`` are Galaxy-produced inputs the runner has no reason to rewrite.
        """
        if os.path.islink(path):
            raise exceptions.ItemAccessibilityException("Job is not authorized to write to supplied path.")
        if dataset_path := self._output_dataset_path(job, path):
            return os.path.dirname(dataset_path)
        working_directory = JobWorkingDirectory(job, self._object_store).resolve()
        job_directory = os.path.realpath(working_directory)
        # Relative to the resolved job directory, so that a symlink among the allowed directories can't widen them.
        relative = os.path.relpath(os.path.realpath(path), job_directory).split(os.sep)
        if (
            len(relative) > 1
            and relative[0] in RESTRICTED_WRITABLE_DIRECTORIES
            and relative[:2] != RESTRICTED_UNWRITABLE_DIRECTORY
        ):
            return working_directory
        raise exceptions.ItemAccessibilityException("Job is not authorized to write to supplied path.")

    def _is_job_file(self, job: Job, path: str) -> bool:
        """Whether ``path`` is in the job directory or is one of the job's datasets, inputs and their files included."""
        target = os.path.realpath(path)
        job_directory = os.path.realpath(JobWorkingDirectory(job, self._object_store).resolve())
        if util.in_directory(target, job_directory):
            return target != os.path.join(job_directory, RESTRICTED_UNREADABLE_FILE)
        if self._output_dataset_path(job, path):
            return True
        input_assocs: list[JobToInputDatasetAssociation | JobToInputLibraryDatasetAssociation] = [
            *job.input_datasets,
            *job.input_library_datasets,
        ]
        # A purged input has an empty file name, which must not resolve to the Galaxy process cwd.
        inputs = [
            assoc.dataset for assoc in input_assocs if assoc.dataset and assoc.dataset.get_file_name(sync_cache=False)
        ]
        for dataset in inputs:
            if os.path.realpath(dataset.get_file_name(sync_cache=False)) == target:
                return True
            if util.in_directory(target, dataset.extra_files_path):
                return True
        # Resolving metadata files can touch the object store, so only once the cheaper checks failed.
        return any(
            os.path.realpath(file_name) == target
            for dataset in inputs
            for file_name in input_metadata_file_names(dataset, sync_cache=False)
        )

    def assert_job_active(self, encoded_job_id: str) -> None:
        """Check that a job whose write was already authorized is still queued or running."""
        self._active_job(self._security.decode_id(encoded_job_id))

    def nginx_upload_path(self, file_path: str) -> str:
        upload_store = self._config.nginx_upload_job_files_store
        if not upload_store:
            raise exceptions.ConfigDoesNotAllowException(
                "Request appears to have been processed by nginx_upload_module but Galaxy is not configured to recognize it."
            )
        file_path = os.path.abspath(file_path)
        if not util.in_directory(file_path, upload_store):
            raise exceptions.RequestParameterInvalidException(
                "Filename provided by nginx is not in the configured upload directory."
            )
        if not os.path.isfile(file_path):
            raise exceptions.RequestParameterInvalidException("File provided by nginx does not exist.")
        return file_path

    def tus_upload_path(self, session_id: str) -> str:
        if re.match(r"^[\w-]+$", session_id) is None:
            raise exceptions.RequestParameterInvalidException("Invalid session id format.")
        upload_path = os.path.abspath(os.path.join(self._config.job_files_tus_upload_dir, session_id))
        if not os.path.isfile(upload_path):
            raise exceptions.RequestParameterInvalidException("No upload found for session id.")
        return upload_path

    def write(self, path: str, source_path: str) -> None:
        """Move ``source_path`` to ``path``, or append it if ``path`` is an existing tool stream."""
        util.safe_makedirs(os.path.dirname(path))
        if os.path.exists(path) and path.endswith(APPENDABLE_FILE_NAMES):
            with open(source_path, "rb") as source, open(path, "ab") as destination:
                shutil.copyfileobj(source, destination)
            os.unlink(source_path)
        else:
            shutil.move(source_path, path)

    def _authorize(self, encoded_job_id: str, path: str | None, job_key: str | None) -> tuple[Job, str]:
        if path is None:
            raise exceptions.ObjectAttributeMissingException("Job files action requires a valid 'path'.")
        if job_key is None:
            raise exceptions.ObjectAttributeMissingException("Job files action requires a valid 'job_key'.")
        job_id = self._security.decode_id(encoded_job_id)
        if not util.safe_str_cmp(job_key, self._security.encode_id(job_id, kind="jobs_files")):
            raise exceptions.ItemAccessibilityException("Invalid job_key supplied.")
        job = self._active_job(job_id)
        if not path:
            raise exceptions.RequestParameterInvalidException("'path' parameter not provided or empty.")
        return job, path

    def _active_job(self, job_id: int) -> Job:
        job = self._sa_session.get(Job, job_id)
        if not job:
            raise exceptions.ObjectNotFound("Job not found.")
        if job.state not in Job.non_ready_states:
            raise exceptions.ItemAccessibilityException(
                "Attempting to read or modify the files of a job that has already completed."
            )
        return job

    def _output_dataset_path(self, job: Job, path: str) -> str | None:
        """Return the file of the output dataset that ``path`` is, or is an extra file of."""
        all_output_assocs: list[JobToOutputDatasetAssociation | JobToOutputLibraryDatasetAssociation] = [
            *job.output_datasets,
            *job.output_library_datasets,
        ]
        for assoc in all_output_assocs:
            dataset = assoc.dataset
            if not dataset:
                continue
            dataset_path = dataset.get_file_name()
            # A purged dataset, or one missing from its object store, has an empty file name,
            # and ``abspath("")`` is the Galaxy process cwd.
            if not dataset_path:
                continue
            if os.path.abspath(dataset_path) == os.path.abspath(path) or util.in_directory(
                path, dataset.extra_files_path
            ):
                return dataset_path
        return None
