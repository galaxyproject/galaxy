"""API asynchronous job running mechanisms can use to get a fresh OIDC token."""

import logging
from typing import Optional

from fastapi import (
    Header,
    Query,
)
from fastapi.responses import PlainTextResponse

from galaxy.authnz.util import provider_name_to_backend
from galaxy.job_execution.job_security import resolve_job_key
from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.job_files import JobFilesManager
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)
router = Router(tags=["remote files"])


@router.cbv
class FastAPIJobTokens:
    manager: JobFilesManager = depends(JobFilesManager)

    @router.get(
        "/api/jobs/{job_id}/oidc-tokens",
        summary="Get a fresh OIDC token",
        description="Allows remote job running mechanisms to get a fresh OIDC token that "
        "can be used on remote side to authorize user. "
        "It is not meant to represent part of Galaxy's stable, user facing API",
        tags=["oidc_tokens"],
        response_class=PlainTextResponse,
    )
    def get_token(
        self,
        job_id: EncodedDatabaseIdField,
        provider: str = Query(
            description=("OIDC provider name"),
        ),
        job_key: Optional[str] = Query(
            None,
            description=(
                "A key used to authenticate this request as acting on behalf of a job runner for "
                "the specified job. Prefer the ``Authorization: Bearer <key>`` header; this "
                "query-string form is kept only for backward compatibility with older Pulsar "
                "versions that embed the secret in the URL."
            ),
        ),
        authorization: Optional[str] = Header(None),
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> str:
        supplied = resolve_job_key(authorization, job_key)
        job = self.manager.authorize_for_token(job_id, supplied)
        assert job.user is not None
        trans.app.authnz_manager.refresh_expiring_oidc_tokens(trans, job.user)  # type: ignore[attr-defined]
        tokens = job.user.get_oidc_tokens(provider_name_to_backend(provider))
        return tokens["id"]
