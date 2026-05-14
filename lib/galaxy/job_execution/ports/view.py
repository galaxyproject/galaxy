import logging

from galaxy import (
    model,
    util,
)
from galaxy.exceptions import (
    ItemAccessibilityException,
    ObjectAttributeMissingException,
)
from galaxy.job_execution.job_security import job_files_kind_for_job

log = logging.getLogger(__name__)


class JobPortsView:
    def __init__(self, app):
        self._app = app

    def register_container_information(self, job_id, **kwd):
        job = self.__authorize_job_access(job_id, **kwd)
        container_runtime = kwd.get("container_runtime")
        log.info(kwd)
        self._app.interactivetool_manager.configure_entry_points(job, container_runtime)
        return {"message": "ok"}

    def __authorize_job_access(self, encoded_job_id, **kwargs):
        # ``job_key`` should already be resolved from header-or-body by the
        # controller (see ``JobPortsAPIController.create``); we still validate
        # presence here so direct callers can't bypass the check.
        if (key := "job_key") not in kwargs or not kwargs[key]:
            error_message = f"Job files action requires a valid '{key}'."
            raise ObjectAttributeMissingException(error_message)

        job_id = self._security.decode_id(encoded_job_id)
        sa_session = self._app.model.session
        job = sa_session.query(model.Job).get(job_id)
        if job is None:
            raise ItemAccessibilityException("Invalid job_key supplied.")

        # Same kind selection as the job_files endpoint — BYOC jobs use a
        # tenant-scoped encryption ``kind`` so a key lifted from another
        # tenant's Pulsar node will not validate here.
        expected = self._security.encode_id(job_id, kind=job_files_kind_for_job(job))
        if not util.safe_str_cmp(kwargs["job_key"], expected):
            raise ItemAccessibilityException("Invalid job_key supplied.")

        # Verify job is active. Don't update the contents of complete jobs.
        if not job.running:
            error_message = "Attempting to read or modify the files of a job that has already completed."
            raise ItemAccessibilityException(error_message)
        return job

    @property
    def _security(self):
        return self._app.security
