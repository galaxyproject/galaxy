"""Read and write files of queued and running jobs on behalf of remote job runners."""

import os
import re
import shutil
from collections.abc import Callable

from galaxy import (
    exceptions,
    util,
)
from galaxy.config import GalaxyAppConfiguration
from galaxy.job_execution.job_security import (
    JOB_FILES_KIND,
    job_files_kind_for_job,
    job_token_kind_for_job,
)
from galaxy.job_execution.setup import JobWorkingDirectory
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


class JobFilesManager:
    """Job runner access to low-level job files, authorized by job key only - never by user credentials.

    Reads aren't limited to the job's own files, since tools also read unstructured inputs such as ``.loc`` files.
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
        # Reads are otherwise unrestricted because tools legitimately read
        # unstructured server-side inputs such as .loc files. A user-registered
        # compute resource is not trusted with those, so it sees only the files
        # of the job it holds a key for.
        if self._is_compute_resource_job(job) and not self._is_job_file(job, path):
            raise exceptions.ItemAccessibilityException("Job is not authorized to read supplied path.")
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
        job, path = self._authorize(encoded_job_id, path, job_key)
        if not path:
            raise exceptions.RequestParameterInvalidException("'path' parameter not provided or empty.")
        if os.path.islink(path):
            raise exceptions.ItemAccessibilityException("Job is not authorized to write to supplied path.")
        if dataset_path := self._output_dataset_path(job, path):
            return os.path.dirname(dataset_path)
        working_directory = JobWorkingDirectory(job, self._object_store).resolve()
        if self._is_compute_resource_job(job):
            # A user-registered compute resource gets only the tool's CWD.
            # ``metadata/outputs_populated/**`` is the remote-extended-metadata
            # model-import-store and would let a compute-resource node mutate
            # cross-user state; ``container_runtime.json`` is interactive-tool port
            # registration, which must go through ``/api/jobs/{id}/ports`` for the
            # audit trail; ``tool_script.sh`` and ``configs/**`` are Galaxy-produced
            # inputs a remote resource has no reason to rewrite.
            tool_cwd = os.path.join(os.path.realpath(working_directory), "working")
            if util.in_directory(os.path.realpath(path), tool_cwd):
                return working_directory
        elif util.in_directory(path, working_directory):
            return working_directory
        raise exceptions.ItemAccessibilityException("Job is not authorized to write to supplied path.")

    @staticmethod
    def _is_compute_resource_job(job: Job) -> bool:
        return (job.destination_params or {}).get("compute_resource_id") is not None

    def _is_job_file(self, job: Job, path: str) -> bool:
        """True if ``path`` is in the job's working directory or is one of its
        own datasets - inputs included, since a runner stages those."""
        if util.in_directory(path, JobWorkingDirectory(job, self._object_store).resolve()):
            return True
        if self._output_dataset_path(job, path):
            return True
        target = os.path.realpath(path)
        inputs: list[JobToInputDatasetAssociation | JobToInputLibraryDatasetAssociation] = [
            *job.input_datasets,
            *job.input_library_datasets,
        ]
        for assoc in inputs:
            dataset = assoc.dataset
            if not dataset:
                continue
            file_name = dataset.get_file_name()
            if not file_name:
                continue
            if os.path.realpath(file_name) == target:
                return True
            extra = dataset.extra_files_path
            if extra and util.in_directory(target, os.path.realpath(extra)):
                return True
        return False

    def authorize_for_files(self, encoded_job_id: str, job_key: str | None) -> Job:
        """Verify a file-staging ``job_key`` for an endpoint that acts on the job
        itself rather than on a path, and return the job."""
        return self._authorize_credential(
            encoded_job_id, job_key, job_files_kind_for_job, exceptions.ItemAccessibilityException
        )

    def authorize_for_token(self, encoded_job_id: str, job_key: str | None) -> Job:
        """Verify an OIDC-token ``job_key`` and return the job.

        A bad key is an authentication failure here rather than an access error,
        which is what the token endpoint has always reported.
        """
        return self._authorize_credential(
            encoded_job_id, job_key, job_token_kind_for_job, exceptions.AuthenticationFailed
        )

    def _authorize_credential(
        self,
        encoded_job_id: str,
        job_key: str | None,
        kind_for_job: Callable[[Job], str],
        raise_class: type[Exception],
    ) -> Job:
        """Shared key check for the pathless endpoints.

        A missing job and a wrong key raise the same thing: the expected key
        depends on the job's compute-resource binding, so the job has to be
        loaded first, and the caller must not learn which of the two it was.
        """
        if not job_key:
            raise raise_class("Invalid job_key supplied.")
        job_id = self._security.decode_id(encoded_job_id)
        job = self._sa_session.get(Job, job_id)
        if job is None or not util.safe_str_cmp(job_key, self._security.encode_id(job_id, kind=kind_for_job(job))):
            raise raise_class("Invalid job_key supplied.")
        if job.state not in Job.non_ready_states:
            raise exceptions.ItemAccessibilityException(
                "Attempting to read or modify the files of a job that has already completed."
            )
        return job

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
        # The credential is scoped to the job's compute resource, so the expected
        # key depends on the job's destination params. An id with no job behind it
        # has no binding to read, so it falls back to the untenanted kind and the
        # mismatch below stays indistinguishable from a forged key.
        job = self._sa_session.get(Job, job_id)
        kind = job_files_kind_for_job(job) if job is not None else JOB_FILES_KIND
        if not util.safe_str_cmp(job_key, self._security.encode_id(job_id, kind=kind)):
            raise exceptions.ItemAccessibilityException("Invalid job_key supplied.")
        return self._active_job(job_id), path

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
            # A purged dataset — or one whose object store entry has gone missing —
            # has an empty file name, and ``abspath("")`` is the Galaxy process cwd.
            # Treating that as one of the job's files would hand a runner the
            # install root, so skip it.
            if not dataset_path:
                continue
            if os.path.abspath(dataset_path) == os.path.abspath(path) or util.in_directory(
                path, dataset.extra_files_path
            ):
                return dataset_path
        return None
