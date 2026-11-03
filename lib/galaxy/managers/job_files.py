"""Read and write files of queued and running jobs on behalf of remote job runners."""

import logging
import os
import re
import shutil

from galaxy import (
    exceptions,
    util,
)
from galaxy.config import GalaxyAppConfiguration
from galaxy.job_execution.setup import (
    JobFilesManifest,
    JobWorkingDirectory,
    read_job_files_manifest,
)
from galaxy.model import (
    Job,
    JobToOutputDatasetAssociation,
    JobToOutputLibraryDatasetAssociation,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.objectstore import BaseObjectStore
from galaxy.security.idencoding import IdEncodingHelper

log = logging.getLogger(__name__)

APPENDABLE_FILE_NAMES = ("tool_stdout", "tool_stderr")
# Job directories Pulsar stages results back to: the tool working directory, ``outputs`` (datasets written there with
# ``outputs_to_working_directory``, tool streams, the version file) and the metadata directory.
STRICT_WRITABLE_DIRECTORIES = ("working", "outputs", "metadata")
# The extended metadata model store, written only by jobs that run extended metadata remotely.
MODEL_STORE_DIRECTORY = ["metadata", "outputs_populated"]


class JobFilesManager:
    """Job runner access to low-level job files, authorized by job key only - never by user credentials.

    With ``job_files_strict_access``, a job may read only the files its manifest lists, which are the files Galaxy
    told the runner to stage, and write only its outputs and the job directories results are staged back to.
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
        manifest = self._manifest(job)
        readable = manifest is not None and path in manifest.readable_paths
        if not readable and not self._config.job_files_strict_access:
            log.warning(
                "Job %s read %s, which is not in its job files manifest. This read will be refused once "
                "job_files_strict_access is enabled.",
                job.id,
                path,
            )
            readable = True
        if readable and os.path.isfile(path):
            return path
        if readable and os.path.exists(path):
            raise exceptions.RequestParameterInvalidException("Path does not refer to a file.")
        # Inputs may be purged while the job is queued or running; pulsar handles that error.
        if re.match(r"(galaxy_)?dataset_(.*)\.dat", os.path.basename(path)):
            # Purging an input commits the HDA as purged before it removes the file and
            # commits the dataset as purged, so check both to cover the window in between.
            if any(
                jtid.dataset and (jtid.dataset.purged or (jtid.dataset.dataset and jtid.dataset.dataset.purged))
                for jtid in job.input_datasets
            ):
                raise exceptions.ItemDeletionException("Input dataset(s) for job have been purged.")
        if not readable:
            raise exceptions.ItemAccessibilityException("Job is not authorized to read supplied path.")
        raise exceptions.ObjectNotFound("File not found.")

    def authorize_write(self, encoded_job_id: str, path: str | None, job_key: str | None) -> str:
        """Return a directory to stage uploads for ``path`` in - same filesystem, outside any extra files path."""
        job, path = self._authorize(encoded_job_id, path, job_key)
        if not os.path.isabs(path):
            raise exceptions.RequestParameterInvalidException("'path' parameter must be an absolute path.")
        strict_directory = self._strict_write_directory(job, path)
        if self._config.job_files_strict_access:
            if strict_directory is None:
                raise exceptions.ItemAccessibilityException("Job is not authorized to write to supplied path.")
            return strict_directory
        working_directory = JobWorkingDirectory(job, self._object_store).resolve()
        if util.in_directory(path, working_directory):
            directory = working_directory
        elif dataset_path := self._output_dataset_path(job, path):
            directory = os.path.dirname(dataset_path)
        else:
            raise exceptions.ItemAccessibilityException("Job is not authorized to write to supplied path.")
        if strict_directory is None:
            log.warning(
                "Job %s wrote %s, which is not one of its outputs or job directories results are staged back to. "
                "This write will be refused once job_files_strict_access is enabled.",
                job.id,
                path,
            )
        return directory

    def _strict_write_directory(self, job: Job, path: str) -> str | None:
        """Return a staging directory if ``job_files_strict_access`` allows writing ``path``, otherwise ``None``.

        Allowed are the job's outputs and the job directories results are staged back to. Job scripts, the manifest,
        ``configs/`` and ``inputs/`` are Galaxy-produced inputs the runner has no reason to rewrite.
        """
        if os.path.islink(path):
            return None
        working_directory = JobWorkingDirectory(job, self._object_store).resolve()
        job_directory = os.path.realpath(working_directory)
        # Relative to the resolved job directory, so that a symlink among the allowed directories can't widen them.
        relative = os.path.relpath(os.path.realpath(path), job_directory).split(os.sep)
        if len(relative) > 1 and relative[0] in STRICT_WRITABLE_DIRECTORIES:
            if relative[:2] != MODEL_STORE_DIRECTORY:
                return working_directory
            manifest = self._manifest(job)
            if manifest and manifest.remote_extended_metadata:
                return working_directory
        if dataset_path := self._output_dataset_path(job, path):
            return os.path.dirname(dataset_path)
        return None

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

    def write(self, encoded_job_id: str, path: str, source_path: str) -> None:
        """Move ``source_path`` to ``path``, or append it if ``path`` is an existing tool stream."""
        util.safe_makedirs(os.path.dirname(path))
        if os.path.exists(path) and self._is_tool_stream(encoded_job_id, path):
            with open(source_path, "rb") as source, open(path, "ab") as destination:
                shutil.copyfileobj(source, destination)
            os.unlink(source_path)
        else:
            shutil.move(source_path, path)

    def _is_tool_stream(self, encoded_job_id: str, path: str) -> bool:
        if not path.endswith(APPENDABLE_FILE_NAMES):
            return False
        job = self._active_job(self._security.decode_id(encoded_job_id))
        outputs_directory = os.path.join(JobWorkingDirectory(job, self._object_store).resolve(), "outputs")
        if any(path == os.path.join(outputs_directory, name) for name in APPENDABLE_FILE_NAMES):
            return True
        if self._config.job_files_strict_access:
            return False
        log.warning(
            "Job %s appended to %s, which is not one of its tool streams. This file will be replaced instead once "
            "job_files_strict_access is enabled.",
            job.id,
            path,
        )
        return True

    def _manifest(self, job: Job) -> JobFilesManifest | None:
        return read_job_files_manifest(JobWorkingDirectory(job, self._object_store).resolve())

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
