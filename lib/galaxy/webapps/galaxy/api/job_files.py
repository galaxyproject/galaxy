"""API for asynchronous job running mechanisms can use to fetch or put files
related to running and queued jobs.
"""

import logging
import os
import re
import shutil

from galaxy import (
    exceptions,
    util,
)
from galaxy.job_execution.job_security import resolve_job_key
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

    manager: JobFilesManager = depends(JobFilesManager)

    @expose_api_raw_anonymous_and_sessionless
    def index(self, trans: ProvidesAppContext, job_id: str, **kwargs):
        """
        GET /api/jobs/{job_id}/files

        Get a file required to staging a job (proper datasets, extra inputs,
        task-split inputs, working directory files).

        :type   job_id: str
        :param  job_id: encoded id string of the job
        :type   path: str
        :param  path: Path to file.
        :type   job_key: str
        :param  job_key: A key used to authenticate this request as acting on
                         behalf or a job runner for the specified job.

        ..note:
            This API method is intended only for consumption by job runners,
            not end users.

        :rtype:     binary
        :returns:   contents of file
        """
        if "path" not in kwargs:
            raise exceptions.ObjectAttributeMissingException("Job files action requires a valid 'path'.")
        # ``trans.request`` is a webob ``Request`` at runtime — ``request.headers``
        # is webob-only and not part of the ``GalaxyAbstractRequest`` interface
        # that ``ProvidesAppContext`` declares, hence the ignore.
        auth_header = trans.request.headers.get("Authorization")  # type: ignore[attr-defined]
        supplied = resolve_job_key(auth_header, kwargs.get("job_key"))
        job = self.manager.authorize_for_files(job_id, supplied)
        path = kwargs["path"]
        self.manager.assert_readable(job, path)
        try:
            return open(path, "rb")
        except FileNotFoundError:
            # We know that the job is not terminal, but users (or admin scripts) can purge input datasets.
            # Here we discriminate that case from truly unexpected bugs.
            # Not failing the job here, this is or should be handled by pulsar.
            match = re.match(r"(galaxy_)?dataset_(.*)\.dat", os.path.basename(path))
            if match:
                # This looks like a galaxy dataset, check if any job input has been deleted.
                if any(jtid.dataset.dataset.purged for jtid in job.input_datasets):
                    raise exceptions.ItemDeletionException("Input dataset(s) for job have been purged.")
            else:
                raise

    @expose_api_anonymous_and_sessionless
    def create(self, trans: ProvidesAppContext, job_id: str, payload, **kwargs):
        """
        create( self, trans, job_id, payload, **kwargs )
        * POST /api/jobs/{job_id}/files
            Populate an output file (formal dataset, task split part, working
            directory file (such as those related to metadata)). This should be
            a multipart post with a 'file' parameter containing the contents of
            the actual file to create.

        :type   job_id: str
        :param  job_id: encoded id string of the job
        :type   payload:    dict
        :param  payload:    dictionary structure containing::
            'job_key'   = Key authenticating
            'path'      = Path to file to create.

        ..note:
            This API method is intended only for consumption by job runners,
            not end users.

        :rtype:     dict
        :returns:   an okay message
        """
        path = payload.get("path")
        if not path:
            raise exceptions.RequestParameterInvalidException("'path' parameter not provided or empty.")
        auth_header = trans.request.headers.get("Authorization")  # type: ignore[attr-defined]
        supplied = resolve_job_key(auth_header, payload.get("job_key"))
        job = self.manager.authorize_for_files(job_id, supplied)
        self.manager.assert_writable(job, path)

        # Is this writing an unneeded file? Should this just copy in Python?
        if "__file_path" in payload:
            file_path = payload.get("__file_path")
            upload_store = trans.app.config.nginx_upload_job_files_store
            assert upload_store, (
                "Request appears to have been processed by"
                " nginx_upload_module but Galaxy is not"
                " configured to recognize it"
            )
            assert file_path.startswith(
                upload_store
            ), f"Filename provided by nginx ({file_path}) is not in correct directory ({upload_store})"
            input_file = open(file_path)
        elif "session_id" in payload:
            # code stolen from basic.py
            session_id = payload["session_id"]
            upload_store = (
                trans.app.config.tus_upload_store_job_files
                or trans.app.config.tus_upload_store
                or trans.app.config.new_file_path
            )
            if re.match(r"^[\w-]+$", session_id) is None:
                raise ValueError("Invalid session id format.")
            local_filename = os.path.abspath(os.path.join(upload_store, session_id))
            input_file = open(local_filename)
        else:
            input_file = payload.get("file", payload.get("__file", None)).file
        target_dir = os.path.dirname(path)
        util.safe_makedirs(target_dir)
        try:
            if os.path.exists(path) and (path.endswith("tool_stdout") or path.endswith("tool_stderr")):
                with open(path, "ab") as destination:
                    shutil.copyfileobj(open(input_file.name, "rb"), destination)
            else:
                shutil.move(input_file.name, path)
        finally:
            try:
                input_file.close()
            except OSError:
                # Fails to close file if not using nginx upload because the
                # tempfile has moved and Python wants to delete it.
                pass
        return {"message": "ok"}

    @expose_api_anonymous_and_sessionless
    def tus_patch(self, trans, **kwds):
        """
        Exposed as PATCH /api/job_files/resumable_upload.

        I think based on the docs, a separate tusd server is needed for job files if
        also hosting one for use facing uploads.

        Setting up tusd for job files should just look like (I think):

        tusd -host localhost -port 1080 -upload-dir=<galaxy_root>/database/tmp

        See more discussion of checking upload access, but we shouldn't need the
        API key and session stuff the user upload tusd server should be configured with.

        Also shouldn't need a hooks endpoint for this reason but if you want to add one
        the target CLI entry would be -hooks-http=<galaxy_url>/api/job_files/tus_hooks
        and the action is featured below.

        I would love to check the job state with __authorize_job_access on the first
        POST but it seems like TusMiddleware doesn't default to coming in here for that
        initial POST the way it does for the subsequent PATCHes. Ultimately, the upload
        is still authorized before the write done with POST /api/jobs/<job_id>/files
        so I think there is no route here to mess with user data - the worst of the security
        issues that can be caused is filling up the sever with needless files that aren't
        acted on. Since this endpoint is not meant for public consumption - all the job
        files stuff and the TUS server should be blocked to public IPs anyway and restricted
        to your Pulsar servers and similar targeting could be accomplished with a user account
        and the user facing upload endpoints.
        """
        return None

    @expose_api_anonymous_and_sessionless
    def tus_hooks(self, trans: ProvidesAppContext, **kwds):
        """No-op but if hook specified the way we do for user upload it would hit this action.

        Exposed as PATCH /api/job_files/tus_hooks and documented in the docstring for
        tus_patch.
        """
        pass
