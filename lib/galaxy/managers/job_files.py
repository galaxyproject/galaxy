"""Read and write files of queued and running jobs on behalf of remote job runners."""

import logging
import os
import re
import shutil

from galaxy import (
    exceptions,
    util,
)
from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.model import (
    Job,
    JobToOutputDatasetAssociation,
    JobToOutputLibraryDatasetAssociation,
)
from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)

APPENDABLE_FILE_NAMES = ("tool_stdout", "tool_stderr")


class JobFilesManager:
    """Job runner access to low-level job files, authorized by job key only - never by user credentials."""

    def __init__(self, app: MinimalManagerApp):
        self._app = app

    @property
    def upload_dir(self) -> str:
        return str(self._app.config.new_file_path)

    def readable_path(self, encoded_job_id: str, path: str | None, job_key: str | None) -> str:
        job = self._authorize(encoded_job_id, path, job_key)
        assert path is not None
        if os.path.isfile(path):
            return path
        if os.path.exists(path):
            raise exceptions.RequestParameterInvalidException("Path does not refer to a file.")
        # Inputs may be purged while the job is queued or running; pulsar handles that error.
        if re.match(r"(galaxy_)?dataset_(.*)\.dat", os.path.basename(path)):
            input_datasets = [jtid.dataset.dataset for jtid in job.input_datasets if jtid.dataset]
            if any(dataset and dataset.purged for dataset in input_datasets):
                raise exceptions.ItemDeletionException("Input dataset(s) for job have been purged.")
        raise exceptions.ObjectNotFound("File not found.")

    def authorize_write(self, encoded_job_id: str, path: str | None, job_key: str | None) -> str:
        """Return a directory to stage uploads for ``path`` in - same filesystem, outside any extra files path."""
        job = self._authorize(encoded_job_id, path, job_key)
        if not path:
            raise exceptions.RequestParameterInvalidException("'path' parameter not provided or empty.")
        working_directory = JobWorkingDirectory(job, self._app.object_store).resolve()
        if util.in_directory(path, working_directory):
            return working_directory
        if dataset_path := self._output_dataset_path(job, path):
            return os.path.dirname(dataset_path)
        raise exceptions.ItemAccessibilityException("Job is not authorized to write to supplied path.")

    def nginx_upload_path(self, file_path: str) -> str:
        upload_store = self._app.config.nginx_upload_job_files_store
        if not upload_store:
            raise exceptions.ConfigDoesNotAllowException(
                "Request appears to have been processed by nginx_upload_module but Galaxy is not configured to recognize it."
            )
        file_path = os.path.abspath(file_path)
        if not util.in_directory(file_path, upload_store):
            raise exceptions.RequestParameterInvalidException(
                "Filename provided by nginx is not in the configured upload directory."
            )
        return file_path

    def tus_upload_path(self, session_id: str) -> str:
        config = self._app.config
        upload_store = config.tus_upload_store_job_files or config.tus_upload_store or config.new_file_path
        if re.match(r"^[\w-]+$", session_id) is None:
            raise exceptions.RequestParameterInvalidException("Invalid session id format.")
        return os.path.abspath(os.path.join(upload_store, session_id))

    def write(self, path: str, source_path: str) -> None:
        """Move ``source_path`` to ``path``, or append it if ``path`` is an existing tool stream."""
        util.safe_makedirs(os.path.dirname(path))
        if os.path.exists(path) and path.endswith(APPENDABLE_FILE_NAMES):
            with open(source_path, "rb") as source, open(path, "ab") as destination:
                shutil.copyfileobj(source, destination)
            os.unlink(source_path)
        else:
            shutil.move(source_path, path)

    def _authorize(self, encoded_job_id: str, path: str | None, job_key: str | None) -> Job:
        for key, value in (("path", path), ("job_key", job_key)):
            if value is None:
                raise exceptions.ObjectAttributeMissingException(f"Job files action requires a valid '{key}'.")
        security = self._app.security
        job_id = security.decode_id(encoded_job_id)
        if not util.safe_str_cmp(str(job_key), security.encode_id(job_id, kind="jobs_files")):
            raise exceptions.ItemAccessibilityException("Invalid job_key supplied.")
        job = self._app.model.session.get(Job, job_id)
        assert job
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
            if os.path.abspath(dataset_path) == os.path.abspath(path) or util.in_directory(
                path, dataset.extra_files_path
            ):
                return dataset_path
        return None
