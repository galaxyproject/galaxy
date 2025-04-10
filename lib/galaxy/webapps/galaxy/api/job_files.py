"""
API for asynchronous job running mechanisms can use to fetch or put files related to running and queued jobs.
"""

import logging
import os
import re
import shutil
from typing import IO
from urllib.parse import unquote

from fastapi import (
    File,
    Form,
    HTTPException,
    Path,
    Query,
    UploadFile,
)
from typing_extensions import Annotated

from galaxy import (
    exceptions,
    util,
)
from galaxy.managers.context import ProvidesAppContext
from galaxy.model import Job
from galaxy.webapps.base.api import GalaxyFileResponse
from galaxy.webapps.galaxy.api import (
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)


router = Router(
    # keep the endpoint in the undocumented section of the API docs `/api/docs`, as all endpoints from `FastAPIJobFiles`
    # are certainly not meant to represent part of Galaxy's stable, user facing API
    tags=["undocumented"]
)


@router.cbv
class FastAPIJobFiles:
    """
    This job files controller allows remote job running mechanisms to read and modify the current state of files for
    queued and running jobs. It is certainly not meant to represent part of Galaxy's stable, user facing API.

    Furthermore, even if a user key corresponds to the user running the job, it should not be accepted for authorization
    - this API allows access to low-level unfiltered files and such authorization would break Galaxy's security model
    for tool execution.
    """

    # The ARC remote job runner (`lib.galaxy.jobs.runners.pulsar.PulsarARCJobRunner`) expects this endpoint not only to
    # answer `GET` and `HEAD` requests, but also even to return HTTP codes other than 404 when `PROPFIND` requests are
    # issued. The latter are not part of the HTTP spec, but it is used in the WebDAV protocol. The correct answer to
    # such requests is likely 501 (not implemented).
    #
    # FastAPI answers HEAD requests automatically for `GET` endpoints, and returns HTTP 405 (method not allowed) for
    # `PROPFIND`, which maybe is not fully correct but tolerable because it is one less quirk to maintain.
    #
    # However, because of the way legacy WSGI endpoints are injected into the FastAPI app (using
    # `app.mount("/", wsgi_handler)`), the built-in support for `HEAD` requests and for returning HTTP 405 for
    # `PROPFIND` breaks, because such requests are passed to the `wsgi_handler` sub-application. This means that the
    # endpoint still needs to include some code to handle this behavior.
    #
    # When ALL routes have been migrated to ASGI (no WSGI handler sub-application needed anymore), some lines of code
    # can be removed, they are labeled using comments.
    # @router.get(  # use me when ALL endpoints have been migrated to FastAPI
    @router.api_route(  # remove me when ALL endpoints have been migrated to FastAPI
        "/api/jobs/{job_id}/files",
        summary="Get a file required to staging a job.",
        responses={
            200: {
                "description": "Contents of file.",
                "content": {"application/json": None, "application/octet-stream": {"example": None}},
            },
            400: {
                "description": "Path does not refer to a file.",
                "content": {
                    "application/json": {
                        "example": {"detail": "Path does not refer to a file."},
                    }
                },
            },
            404: {
                "description": "File not found.",
                "content": {
                    "application/json": {
                        "example": {"detail": "File not found."},
                    }
                },
            },
            500: {"description": "Input dataset(s) for job have been purged."},
        },
        methods=["GET", "HEAD", "PROPFIND"],  # remove me when ALL endpoints have been migrated to FastAPI
    )
    def index(
        self,
        job_id: Annotated[str, Path(description="Encoded id string of the job.")],
        path: Annotated[
            str,
            Query(
                description="Path to file.",
            ),
        ],
        job_key: Annotated[
            str,
            Query(
                description=(
                    "A key used to authenticate this request as acting on behalf or a job runner for the specified job."
                ),
            ),
        ],
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> GalaxyFileResponse:
        """
        Get a file required to staging a job (proper datasets, extra inputs, task-split inputs, working directory
        files).

        This API method is intended only for consumption by job runners, not end users.
        """
        path = unquote(path)

        job = self.__authorize_job_access(trans, job_id, path=path, job_key=job_key)

        # PROPFIND is not implemented, but the endpoint needs to return a non-404 error code for it
        # remove me when ALL endpoints have been migrated to FastAPI
        if trans.request.method == "PROPFIND":
            raise HTTPException(status_code=501, detail="Not implemented yet.")

        if not os.path.exists(path):
            # We know that the job is not terminal, but users (or admin scripts) can purge input datasets.
            # Here we discriminate that case from truly unexpected bugs.
            # Not failing the job here, this is or should be handled by pulsar.
            match = re.match(r"(galaxy_)?dataset_(.*)\.dat", os.path.basename(path))
            if match:
                # This looks like a galaxy dataset, check if any job input has been deleted.
                if any(jtid.dataset.dataset.purged for jtid in job.input_datasets):
                    raise exceptions.ItemDeletionException("Input dataset(s) for job have been purged.")
            else:
                raise HTTPException(status_code=404, detail="File not found.")
        elif not os.path.isfile(path):
            raise HTTPException(status_code=400, detail="Path does not refer to a file.")

        return GalaxyFileResponse(path)

    @router.post(
        "/api/jobs/{job_id}/files",
        summary="Populate an output file.",
        responses={
            200: {"description": "An okay message.", "content": {"application/json": {"example": {"message": "ok"}}}},
            400: {"description": "Bad request (including no file contents provided)."},
        },
    )
    def create(
        self,
        job_id: Annotated[str, Path(description="Encoded id string of the job.")],
        path: Annotated[str, Form(description="Path to file to create.")],
        job_key: Annotated[
            str,
            Form(
                description=(
                    "A key used to authenticate this request as acting on behalf or a job runner for the specified job."
                )
            ),
        ],
        file: UploadFile = File(None, description="Contents of the file to create."),
        session_id: str = Form(None),
        underscore_file_path: str = Form(
            None,
            alias="__file_path",
            validation_alias="__file_path",
            # both `alias` and `validation_alias` are needed for body parameters, see
            # https://github.com/fastapi/fastapi/issues/10286#issuecomment-1727642960
        ),
        underscore_file: UploadFile = File(
            None,
            alias="__file",
            validation_alias="__file",
            # both `alias` and `validation_alias` are needed for body parameters, see
            # https://github.com/fastapi/fastapi/issues/10286#issuecomment-1727642960
        ),
        trans: ProvidesAppContext = DependsOnTrans,
    ):
        """
        Populate an output file (formal dataset, task split part, working directory file (such as those related to
        metadata). This should be a multipart POST with a 'file' parameter containing the contents of the actual file to
        create.

        This API method is intended only for consumption by job runners, not end users.
        """
        path = unquote(path)

        job = self.__authorize_job_access(trans, job_id, path=path, job_key=job_key)
        self.__check_job_can_write_to_path(trans, job, path)

        input_file: IO[bytes]
        input_file_path: str
        # Is this writing an unneeded file? Should this just copy in Python?
        if underscore_file_path:
            input_file_path = underscore_file_path
            upload_store = trans.app.config.nginx_upload_job_files_store
            assert upload_store, (
                "Request appears to have been processed by"
                " nginx_upload_module but Galaxy is not"
                " configured to recognize it"
            )
            assert input_file_path.startswith(
                upload_store
            ), f"Filename provided by nginx ({input_file_path}) is not in correct directory ({upload_store})"
            input_file = open(input_file_path, "rb")
        elif session_id is not None:
            # code stolen from basic.py
            upload_store = (
                trans.app.config.tus_upload_store_job_files
                or trans.app.config.tus_upload_store
                or trans.app.config.new_file_path
            )
            if re.match(r"^[\w-]+$", session_id) is None:
                raise ValueError("Invalid session id format.")
            local_filename = os.path.abspath(os.path.join(upload_store, session_id))
            input_file_path = local_filename
            input_file = open(local_filename, "rb")
        elif file:
            input_file_path = file.file.name
            input_file = open(file.file.name, "rb")
        elif underscore_file:
            input_file_path = underscore_file.file.name
            input_file = open(underscore_file.file.name, "rb")
        else:
            raise HTTPException(status_code=400, detail="No file contents provided.")

        target_dir = os.path.dirname(path)
        util.safe_makedirs(target_dir)
        try:
            if os.path.exists(path) and (path.endswith("tool_stdout") or path.endswith("tool_stderr")):
                with open(path, "ab") as destination:
                    shutil.copyfileobj(input_file, destination)
            else:
                shutil.move(input_file_path, path)
        finally:
            try:
                input_file.close()
            except OSError:
                # Fails to close file if not using nginx upload because the
                # tempfile has moved and Python wants to delete it.
                pass

        return {"message": "ok"}

    @router.patch(
        "/api/job_files/resumable_upload/{session_id}",
        summary="Upload job files using the TUS protocol.",
        responses={
            # 200: None,
            # Galaxy adds an HTTP 200 response to the API docs. Even though it should be removed for this endpoint,
            # because it simply can never happen, there is no mechanism to remove it (the above won't work).
            501: {"description": "Default response, since this endpoint is not implemented yet."},
        },
    )
    def tus_patch(
        self,
        session_id: Annotated[str, Path(description="Resumable upload session id.")],
        trans: ProvidesAppContext = DependsOnTrans,
    ):
        """
        I think based on the docs, a separate tusd server is needed for job files if
        also hosting one for use facing uploads.

        Setting up tusd for job files should just look like (I think):

        `tusd -host localhost -port 1080 -upload-dir=<galaxy_root>/database/tmp`

        See more discussion of checking upload access, but we shouldn't need the
        API key and session stuff the user upload tusd server should be configured with.

        Also shouldn't need a hooks endpoint for this reason but if you want to add one
        the target CLI entry would be `-hooks-http=<galaxy_url>/api/job_files/tus_hooks`
        and the action is featured below.

        I would love to check the job state with `__authorize_job_access` on the first
        POST but it seems like `TusMiddleware` doesn't default to coming in here for that
        initial POST the way it does for the subsequent PATCHes. Ultimately, the upload
        is still authorized before the write done with POST `/api/jobs/<job_id>/files`
        so I think there is no route here to mess with user data - the worst of the security
        issues that can be caused is filling up the sever with needless files that aren't
        acted on. Since this endpoint is not meant for public consumption - all the job
        files stuff and the TUS server should be blocked to public IPs anyway and restricted
        to your Pulsar servers and similar targeting could be accomplished with a user account
        and the user facing upload endpoints.
        """
        ...
        raise HTTPException(status_code=501, detail="Not implemented yet.")

    @router.post(
        "/api/job_files/resumable_upload",
        summary="Upload job files using the TUS protocol.",
        responses={
            # 200: None,
            # Galaxy adds an HTTP 200 response to the API docs. Even though it should be removed for this endpoint,
            # because it simply can never happen, there is no mechanism to remove it (the above won't work).
            501: {"description": "Default response, since this endpoint is not implemented yet."},
        },
    )
    def tus_post(self, trans: ProvidesAppContext = DependsOnTrans):
        """
        User facing upload has this endpoint enabled but the middleware completely masks it and the endpoint is not
        used. Probably it isn't needed there, but I am keeping the doc here until we remove both routes.
        """
        ...
        raise HTTPException(status_code=501, detail="Not implemented yet.")

    @router.post(
        "/api/job_files/tus_hooks",
        summary="No-op but if hook specified the way we do for user upload it would hit this action.",
        responses={
            # 200: None,
            # Galaxy adds an HTTP 200 response to the API docs. Even though it should be removed for this endpoint,
            # because it simply can never happen, there is no mechanism to remove it (the above won't work).
            501: {"description": "Default response, since this endpoint is not implemented yet."},
        },
    )
    def tus_hooks(
        self,
        trans: ProvidesAppContext = DependsOnTrans,
    ):
        """
        No-op but if hook specified the way we do for user upload it would hit this action.
        """
        ...
        raise HTTPException(status_code=501, detail="Not implemented yet.")

    def __authorize_job_access(self, trans, encoded_job_id, path, job_key):
        job_id = trans.security.decode_id(encoded_job_id)
        job_key_from_job_id = trans.security.encode_id(job_id, kind="jobs_files")
        if not util.safe_str_cmp(str(job_key), job_key_from_job_id):
            raise exceptions.ItemAccessibilityException("Invalid job_key supplied.")

        # Verify job is active. Don't update the contents of complete jobs.
        job = trans.sa_session.get(Job, job_id)
        if job.state not in Job.non_ready_states:
            error_message = "Attempting to read or modify the files of a job that has already completed."
            raise exceptions.ItemAccessibilityException(error_message)
        return job

    def __check_job_can_write_to_path(self, trans, job, path):
        """
        Verify an idealized job runner should actually be able to write to the specified path - it must be a dataset
        output, a dataset "extra file", or a some place in the working directory of this job.

        Would like similar checks for reading the unstructured nature of loc
        files make this very difficult. (See abandoned work here
        https://gist.github.com/jmchilton/9103619.)
        """
        in_work_dir = self.__in_working_directory(job, path, trans.app)
        if not in_work_dir and not self.__is_output_dataset_path(job, path):
            raise exceptions.ItemAccessibilityException("Job is not authorized to write to supplied path.")

    def __is_output_dataset_path(self, job, path):
        """
        Check if is an output path for this job or a file in the output's extra files path.
        """
        da_lists = [job.output_datasets, job.output_library_datasets]
        for da_list in da_lists:
            for job_dataset_association in da_list:
                dataset = job_dataset_association.dataset
                if not dataset:
                    continue
                if os.path.abspath(dataset.get_file_name()) == os.path.abspath(path):
                    return True
                elif util.in_directory(path, dataset.extra_files_path):
                    return True
        return False

    def __in_working_directory(self, job, path, app):
        working_directory = app.object_store.get_filename(
            job, base_dir="job_work", dir_only=True, extra_dir=str(job.id)
        )
        return util.in_directory(path, working_directory)
