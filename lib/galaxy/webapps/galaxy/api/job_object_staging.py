"""API a remote job runner uses to stage a running job's inputs from the object store.

Not part of Galaxy's user-facing API: Galaxy issues these URLs to job runners
(see ``galaxy.managers.job_object_staging``) and a URL's signature, not a user
session, authorizes the request.
"""

from fastapi import Query
from fastapi.responses import (
    RedirectResponse,
    Response,
)

from galaxy.managers.job_object_staging import (
    JobObjectStagingManager,
    StagedInputKind,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.webapps.base.api import (
    GalaxyFileResponse,
    GalaxyStreamingResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    Router,
)

router = Router(tags=["remote files"])

INPUT_PATH = "/api/jobs/{job_id}/staging/inputs/{kind}/{object_id}"
EXPIRES = Query(description="Expiry of the staging URL, in seconds since the epoch.")
SIGNATURE = Query(description="Signature Galaxy issued for this job, input and expiry.")
PATH = Query("", description="For an extra file, its path within the dataset's extra files.")


@router.cbv
class FastAPIJobObjectStaging:
    manager: JobObjectStagingManager = depends(JobObjectStagingManager)

    @router.get(INPUT_PATH, summary="Stage a job input for a remote job runner.", include_in_schema=False)
    def get_input(
        self,
        job_id: DecodedDatabaseIdField,
        kind: StagedInputKind,
        object_id: DecodedDatabaseIdField,
        exp: int = EXPIRES,
        sig: str = SIGNATURE,
        redirect: bool = Query(False, description="Allow a redirect to a presigned object store URL."),
        path: str = PATH,
    ) -> Response:
        staged = self.manager.staged_input(job_id, kind, object_id, exp, sig, redirect=redirect, path=path)
        if staged.redirect_url is not None:
            return RedirectResponse(staged.redirect_url, status_code=302)
        if staged.stream is not None:
            headers = {"Content-Length": str(staged.size)}
            return GalaxyStreamingResponse(staged.stream, media_type="application/octet-stream", headers=headers)
        assert staged.path is not None
        return GalaxyFileResponse(staged.path, media_type="application/octet-stream")

    @router.head(INPUT_PATH, summary="Size of a job input for a remote job runner.", include_in_schema=False)
    def head_input(
        self,
        job_id: DecodedDatabaseIdField,
        kind: StagedInputKind,
        object_id: DecodedDatabaseIdField,
        exp: int = EXPIRES,
        sig: str = SIGNATURE,
        path: str = PATH,
    ) -> Response:
        # Answered here rather than by redirect: a presigned GET URL rejects HEAD.
        staged = self.manager.staged_input(job_id, kind, object_id, exp, sig, head=True, path=path)
        return Response(headers={"Content-Length": str(staged.size)})
