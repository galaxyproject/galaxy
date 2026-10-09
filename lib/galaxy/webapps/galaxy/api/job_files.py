"""API for asynchronous job running mechanisms can use to fetch or put files
related to running and queued jobs.
"""

import logging
import os
import shutil
import tempfile
import time
from typing import Annotated
from urllib.parse import parse_qsl

import anyio
from fastapi import (
    Path,
    Query,
    Request,
)
from python_multipart import create_form_parser
from python_multipart.exceptions import FormParserError
from python_multipart.multipart import (
    Field,
    File,
    FormParser,
)
from starlette.requests import ClientDisconnect

from galaxy import (
    exceptions,
    util,
)
from galaxy.managers.job_files import JobFilesManager
from galaxy.webapps.base.api import (
    GalaxyFileResponse,
    release_request_sessions,
)
from . import (
    depends,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["jobs"])

UPLOAD_STAGING_PREFIX = ".job_files_upload_"
PARSER_WRITE_SIZE = 256 * 1024
RECHECK_BODY_SIZE = 1024 * 1024
RECHECK_SECONDS = 1.0

JOB_FILES_DESCRIPTION = (
    "Only for consumption by remote job runners (e.g. Pulsar) acting on behalf of a queued or running job, "
    "authorized by `job_key` - not part of Galaxy's stable, user facing API."
)

JobIdPathParam = Annotated[str, Path(description="Encoded id string of the job.")]
FilePathQueryParam = Annotated[str | None, Query(description="Path to file.")]
JobKeyQueryParam = Annotated[
    str | None,
    Query(description="A key used to authenticate this request as acting on behalf of a job runner for the job."),
]

UPLOAD_FIELD_PROPERTIES = {
    "path": {"type": "string", "description": "Path to file to create, if not given as a query parameter."},
    "job_key": {"type": "string", "description": "Job key, if not given as a query parameter."},
    "session_id": {"type": "string", "description": "Completed job files TUS upload to use as contents."},
    "__file_path": {"type": "string", "description": "File stored by nginx_upload_module to use as contents."},
}
UPLOAD_FIELDS_SCHEMA = {"type": "object", "properties": UPLOAD_FIELD_PROPERTIES}
UPLOAD_FORM_SCHEMA = {
    "type": "object",
    "properties": {
        **UPLOAD_FIELD_PROPERTIES,
        "file": {"type": "string", "format": "binary", "description": "Contents of the file to create."},
        "__file": {"type": "string", "format": "binary", "description": "Alias of `file`."},
    },
}


@router.cbv
class FastAPIJobFiles:
    manager: JobFilesManager = depends(JobFilesManager)

    @router.get(
        "/api/jobs/{job_id}/files",
        summary="Get a file required to stage a job.",
        description=JOB_FILES_DESCRIPTION,
        response_class=GalaxyFileResponse,
        public=True,
    )
    @router.head("/api/jobs/{job_id}/files", include_in_schema=False)
    def index(
        self,
        job_id: JobIdPathParam,
        path: FilePathQueryParam = None,
        job_key: JobKeyQueryParam = None,
    ) -> GalaxyFileResponse:
        return GalaxyFileResponse(self.manager.readable_path(job_id, path, job_key))

    @router.post(
        "/api/jobs/{job_id}/files",
        summary="Populate an output or working directory file of a job.",
        description=JOB_FILES_DESCRIPTION,
        public=True,
        openapi_extra={
            "requestBody": {
                "content": {
                    "multipart/form-data": {"schema": UPLOAD_FORM_SCHEMA},
                    "application/x-www-form-urlencoded": {"schema": UPLOAD_FIELDS_SCHEMA},
                }
            }
        },
    )
    async def create(
        self,
        request: Request,
        job_id: JobIdPathParam,
        path: FilePathQueryParam = None,
        job_key: JobKeyQueryParam = None,
    ) -> dict[str, str]:
        params = dict(request.query_params)
        query_auth = path is not None and job_key is not None
        staging_dir = await anyio.to_thread.run_sync(self._start_upload, job_id, path, job_key, query_auth)
        started = time.monotonic()
        try:
            try:
                fields, uploads = await _parse_body(request, staging_dir)
            except ClientDisconnect:
                # Nobody is left to read the response; a 4xx keeps the disconnect out of the error logs.
                raise exceptions.RequestParameterInvalidException("Client disconnected during job files upload.")
            for key, value in fields.items():
                params.setdefault(key, value)
            # A long upload can outlive the job; a small one arrives right after the first check.
            recheck = query_auth and _long_upload(request, time.monotonic() - started)
            await anyio.to_thread.run_sync(self._finish_upload, job_id, params, uploads, query_auth, recheck)
        finally:
            await anyio.to_thread.run_sync(_remove_staging_dir, staging_dir)
        return {"message": "ok"}

    def _start_upload(self, job_id: str, path: str | None, job_key: str | None, query_auth: bool) -> str:
        """Return a new directory to stage the upload in, authorizing first when the query allows it."""
        if query_auth:
            # Authorize before reading the body so the upload is staged on the target's filesystem and renamed.
            staging_parent = self.manager.authorize_write(job_id, path, job_key)
            util.safe_makedirs(staging_parent)
        else:
            staging_parent = self.manager.upload_dir
        release_request_sessions()
        return tempfile.mkdtemp(prefix=UPLOAD_STAGING_PREFIX, dir=staging_parent)

    def _finish_upload(
        self, job_id: str, params: dict[str, str], uploads: dict[str, str], query_auth: bool, recheck: bool
    ) -> None:
        path = params.get("path")
        if not query_auth:
            self.manager.authorize_write(job_id, path, params.get("job_key"))
        elif recheck:
            # The path was authorized before the body was read; only the job can have finished since.
            self.manager.assert_job_active(job_id)
        assert path
        if "__file_path" in params:
            source_path = self.manager.nginx_upload_path(params["__file_path"])
        elif "session_id" in params:
            source_path = self.manager.tus_upload_path(params["session_id"])
        elif upload := uploads.get("file", uploads.get("__file")):
            source_path = upload
        else:
            raise exceptions.RequestParameterMissingException("No file uploaded.")
        self.manager.write(path, source_path)

    @router.post("/api/job_files/tus_hooks", include_in_schema=False)
    def tus_hooks(self) -> None:
        """Accept every hook from a job files tusd server whose ``-hooks-http`` points here.

        Deployments configure this (e.g. with Gravity's ``hooks_http``). Uploads are authorized
        when ``POST /api/jobs/{job_id}/files`` consumes them by ``session_id``.
        """
        return None


def _remove_staging_dir(staging_dir: str) -> None:
    try:
        shutil.rmtree(staging_dir)
    except OSError:
        log.warning("Failed to remove job files upload staging directory %s", staging_dir, exc_info=True)


def _long_upload(request: Request, elapsed: float) -> bool:
    content_length = request.headers.get("content-length")
    return content_length is None or int(content_length) >= RECHECK_BODY_SIZE or elapsed >= RECHECK_SECONDS


def _finalize_parser(parser: FormParser, remaining: bytes, files: list[File]) -> None:
    if remaining:
        parser.write(remaining)
    parser.finalize()
    for file in files:
        if file.in_memory:
            file.flush_to_disk()


async def _parse_body(request: Request, upload_dir: str) -> tuple[dict[str, str], dict[str, str]]:
    """Return form fields and the named files in ``upload_dir`` that file parts were streamed to, by part name."""
    content_type = request.headers.get("content-type")
    if not content_type:
        return {}, {}
    if content_type.startswith("application/x-www-form-urlencoded"):
        body = await request.body()
        return dict(parse_qsl(body.decode("latin-1"), keep_blank_values=True)), {}

    fields: dict[str, str] = {}
    files: list[File] = []

    def on_field(field: Field) -> None:
        if field.field_name is not None:
            fields[field.field_name.decode()] = (field.value or b"").decode()

    try:
        parser = create_form_parser(
            {"Content-Type": content_type.encode("latin-1")},
            on_field,
            files.append,
            config={"UPLOAD_DIR": upload_dir, "UPLOAD_DELETE_TMP": False, "MAX_MEMORY_FILE_SIZE": 0},
        )
        # Hand the parser at least PARSER_WRITE_SIZE per threadpool call; a small upload takes a single call.
        pending: list[bytes] = []
        pending_size = 0
        async for chunk in request.stream():
            pending.append(chunk)
            pending_size += len(chunk)
            if pending_size >= PARSER_WRITE_SIZE:
                await anyio.to_thread.run_sync(parser.write, b"".join(pending))
                pending, pending_size = [], 0
        await anyio.to_thread.run_sync(_finalize_parser, parser, b"".join(pending), files)
        uploads = {
            file.field_name.decode(): os.fsdecode(file.actual_file_name)
            for file in files
            if file.field_name is not None and file.actual_file_name is not None
        }
    except (FormParserError, ValueError) as e:
        raise exceptions.RequestParameterInvalidException(f"Failed to parse job files upload: {e}")
    finally:
        for file in files:
            file.close()
    return fields, uploads
