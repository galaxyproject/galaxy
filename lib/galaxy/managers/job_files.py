"""Manager for the per-job credentials used by job_files / job_ports /
job_tokens endpoints, and for the path-allowlist policy that decides what
a job runner may read or write on the Galaxy server.

This consolidates three pieces of policy that were previously duplicated
across :mod:`galaxy.webapps.galaxy.api.job_files`,
:mod:`galaxy.webapps.galaxy.api.job_tokens` and
:mod:`galaxy.job_execution.ports.view`:

* Decoding the encoded job id and looking the ``Job`` up.
* Constant-time comparison of the supplied ``job_key`` against the
  expected value, derived from a per-job ``kind`` (see :mod:`job_security`).
* Verifying the job is in a non-terminal state — runners cannot modify
  jobs that have already finished.
* Path policy: what files the runner is allowed to read (its working
  directory plus the job's own input/output datasets) and write (its
  working directory plus its own outputs, with a tighter sub-allowlist
  for jobs bound to a user-registered compute resource).
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import (
    Optional,
    Union,
)

from galaxy import (
    exceptions,
    util,
)
from galaxy.job_execution.job_security import (
    job_files_kind_for_job,
    job_token_kind_for_job,
)
from galaxy.model import (
    Job,
    JobToInputDatasetAssociation,
    JobToInputLibraryDatasetAssociation,
    JobToOutputDatasetAssociation,
    JobToOutputLibraryDatasetAssociation,
)
from galaxy.structured_app import MinimalManagerApp


class JobFilesManager:
    """Per-job credential and path-policy gatekeeper.

    Constructed once per app; methods are stateless and safe to call
    concurrently. Holds a ``MinimalManagerApp`` to reach the
    ``IdEncodingHelper``, SQLAlchemy session, and object store — three
    dependencies that always travel together for this kind of check.
    """

    def __init__(self, app: MinimalManagerApp) -> None:
        self._app = app

    # ---- authorization ---------------------------------------------------

    def authorize_for_files(self, encoded_job_id: str, supplied_job_key: Optional[str]) -> Job:
        """Verify a ``job_key`` for the job_files / job_ports endpoints.

        Raises :class:`~galaxy.exceptions.ItemAccessibilityException` on any
        failure (missing key, unknown job, wrong key, terminal job).
        """
        return self._authorize(
            encoded_job_id,
            supplied_job_key,
            job_files_kind_for_job,
            exceptions.ItemAccessibilityException,
        )

    def authorize_for_token(self, encoded_job_id: str, supplied_job_key: Optional[str]) -> Job:
        """Verify a ``job_key`` for the OIDC-token endpoint.

        Raises :class:`~galaxy.exceptions.AuthenticationFailed` on a missing,
        unknown, or wrong key, and :class:`~galaxy.exceptions.ItemAccessibilityException`
        on a terminal job. Distinct exception classes preserve the legacy
        per-endpoint HTTP status mapping.
        """
        return self._authorize(
            encoded_job_id,
            supplied_job_key,
            job_token_kind_for_job,
            exceptions.AuthenticationFailed,
        )

    def _authorize(
        self,
        encoded_job_id: str,
        supplied_job_key: Optional[str],
        kind_for_job: Callable[[Job], str],
        raise_class: type[Exception],
    ) -> Job:
        if not supplied_job_key:
            raise raise_class("Invalid job_key supplied.")
        job_id = self._app.security.decode_id(encoded_job_id)
        session = self._app.model.session
        job = session.get(Job, job_id)
        if job is None:
            raise raise_class("Invalid job_key supplied.")
        # Pick the kind from the job's compute-resource binding (if any) — verifying
        # with the wrong kind yields a plain mismatch, so callers see the
        # same response we'd give for a forged key.
        expected = self._app.security.encode_id(job_id, kind=kind_for_job(job))
        if not util.safe_str_cmp(str(supplied_job_key), expected):
            raise raise_class("Invalid job_key supplied.")
        if job.state not in Job.non_ready_states:
            raise exceptions.ItemAccessibilityException(
                "Attempting to read or modify the files of a job that has already completed."
            )
        return job

    # ---- path policy -----------------------------------------------------

    def assert_readable(self, job: Job, path: str) -> None:
        """Verify ``path`` is one the job runner is allowed to read.

        Permitted: the job's working directory tree, any of its input
        dataset files (and extra-files paths), and any of its output
        dataset files (so a runner can re-read its own outputs).
        Symlinks are rejected outright as defense in depth.
        """
        if os.path.islink(path):
            raise exceptions.ItemAccessibilityException("Job is not authorized to read supplied path.")
        if self._in_working_directory(job, path):
            return
        if self._is_job_dataset_path(job, path, include_inputs=True):
            return
        raise exceptions.ItemAccessibilityException("Job is not authorized to read supplied path.")

    def assert_writable(self, job: Job, path: str) -> None:
        """Verify ``path`` is one the job runner is allowed to write.

        Jobs not bound to a compute resource: anywhere under the job working directory or to any
        output dataset path / extra_files dir.

        Jobs bound to a user-registered compute resource: a tighter subset — only ``<job_dir>/working/**`` (the
        tool's CWD where ``galaxy.json`` and discovered outputs land) and
        output dataset paths. See :func:`_compute_resource_writable_working_dir_path`
        for the rationale on excluding ``metadata/outputs_populated``,
        ``container_runtime.json``, ``tool_script.sh``, and ``configs/**``.
        Symlinks are rejected outright.
        """
        if os.path.islink(path):
            raise exceptions.ItemAccessibilityException("Job is not authorized to write to supplied path.")
        if self._is_job_dataset_path(job, path, include_inputs=False):
            return
        if self._is_compute_resource_job(job):
            if self._compute_resource_writable_working_dir_path(job, path):
                return
        else:
            if self._in_working_directory(job, path):
                return
        raise exceptions.ItemAccessibilityException("Job is not authorized to write to supplied path.")

    # ---- internal helpers ------------------------------------------------

    def _is_compute_resource_job(self, job: Job) -> bool:
        params = job.destination_params or {}
        return params.get("compute_resource_id") is not None

    def _compute_resource_writable_working_dir_path(self, job: Job, path: str) -> bool:
        """Compute-resource write allowlist within the working directory.

        Allowed: ``<job_dir>/working/**`` only. ``metadata/outputs_populated/**``
        is the remote-extended-metadata model-import-store and would let a
        compute-resource node mutate cross-user state on edit; ``container_runtime.json``
        is interactive-tool port registration (callers must go through
        ``/api/jobs/{id}/ports`` for the audit trail); ``tool_script.sh``
        and ``configs/**`` are Galaxy-produced inputs that a remote
        compute resource has no legitimate reason to rewrite.
        """
        job_dir = os.path.realpath(
            self._app.object_store.get_filename(job, base_dir="job_work", dir_only=True, extra_dir=str(job.id))
        )
        tool_cwd = os.path.join(job_dir, "working")
        return util.in_directory(os.path.realpath(path), tool_cwd)

    def _is_job_dataset_path(self, job: Job, path: str, include_inputs: bool) -> bool:
        """True if ``path`` matches one of this job's dataset files or sits
        inside one of its dataset extra-files directories.

        ``include_inputs=True`` for reads (so a runner can fetch the inputs
        it needs to stage); ``False`` for writes (writes target outputs
        only — a runner never overwrites an input).
        """
        assocs: list[
            Union[
                JobToInputDatasetAssociation,
                JobToInputLibraryDatasetAssociation,
                JobToOutputDatasetAssociation,
                JobToOutputLibraryDatasetAssociation,
            ]
        ] = [*job.output_datasets, *job.output_library_datasets]
        if include_inputs:
            assocs = [*job.input_datasets, *job.input_library_datasets, *assocs]
        # ``realpath`` defeats out-of-tree symlink redirects.
        target = os.path.realpath(path)
        for assoc in assocs:
            dataset = assoc.dataset
            if not dataset:
                continue
            if os.path.realpath(dataset.get_file_name()) == target:
                return True
            extra = dataset.extra_files_path
            if extra and util.in_directory(target, os.path.realpath(extra)):
                return True
        return False

    def _in_working_directory(self, job: Job, path: str) -> bool:
        working_directory = self._app.object_store.get_filename(
            job, base_dir="job_work", dir_only=True, extra_dir=str(job.id)
        )
        return util.in_directory(os.path.realpath(path), os.path.realpath(working_directory))
