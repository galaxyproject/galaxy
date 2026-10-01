"""API for asynchronous job running mechanisms can use to fetch or put files
related to running and queued jobs.
"""

import logging

from galaxy import exceptions
from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.job_files import JobFilesManager
from galaxy.web import (
    expose_api_anonymous_and_sessionless,
    expose_api_raw_anonymous_and_sessionless,
)
from . import (
    BaseGalaxyAPIController,
    depends,
)

log = logging.getLogger(__name__)


class JobFilesAPIController(BaseGalaxyAPIController):
    """This job files controller allows remote job running mechanisms to
    read and modify the current state of files for queued and running jobs.
    It is certainly not meant to represent part of Galaxy's stable, user
    facing API.

    Furthermore, even if a user key corresponds to the user running the job,
    it should not be accepted for authorization - this API allows access to
    low-level unfiltered files and such authorization would break Galaxy's
    security model for tool execution.
    """

    job_files_manager = depends(JobFilesManager)

    @expose_api_raw_anonymous_and_sessionless
    def index(self, trans: ProvidesAppContext, job_id: str, **kwargs):
        """
        GET /api/jobs/{job_id}/files

        Get a file required to staging a job (proper datasets, extra inputs,
        task-split inputs, working directory files).
        """
        path = self.job_files_manager.readable_path(job_id, kwargs.get("path"), kwargs.get("job_key"))
        return open(path, "rb")

    @expose_api_anonymous_and_sessionless
    def create(self, trans: ProvidesAppContext, job_id: str, payload, **kwargs):
        """
        POST /api/jobs/{job_id}/files

        Populate an output file (formal dataset, task split part, working
        directory file (such as those related to metadata)). This should be
        a multipart post with a 'file' parameter containing the contents of
        the actual file to create.
        """
        path = payload.get("path")
        self.job_files_manager.authorize_write(job_id, path, payload.get("job_key"))
        if "__file_path" in payload:
            source_path = self.job_files_manager.nginx_upload_path(payload["__file_path"])
        elif "session_id" in payload:
            source_path = self.job_files_manager.tus_upload_path(payload["session_id"])
        else:
            upload = payload.get("file", payload.get("__file"))
            if upload is None:
                raise exceptions.RequestParameterMissingException("No file uploaded.")
            source_path = upload.file.name
        self.job_files_manager.write(path, source_path)
        return {"message": "ok"}

    @expose_api_anonymous_and_sessionless
    def tus_patch(self, trans: ProvidesAppContext, **kwds):
        return None

    @expose_api_anonymous_and_sessionless
    def tus_hooks(self, trans: ProvidesAppContext, **kwds):
        pass
