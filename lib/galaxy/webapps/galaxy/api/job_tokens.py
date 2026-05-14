"""API asynchronous job running mechanisms can use to get a fresh OIDC token."""

import logging
from typing import Optional

from fastapi import (
    Header,
    Query,
)
from fastapi.responses import PlainTextResponse

from galaxy import (
    exceptions,
    util,
)
from galaxy.authnz.util import provider_name_to_backend
from galaxy.job_execution.job_security import (
    job_token_kind_for_job,
    resolve_job_key,
)
from galaxy.managers.context import ProvidesAppContext
from galaxy.model import Job
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.webapps.galaxy.api import (
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)
router = Router(tags=["remote files"])


@router.cbv
class FastAPIJobTokens:
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
        supplied = resolve_job_key({"Authorization": authorization or ""}, job_key)
        if not supplied:
            raise exceptions.AuthenticationFailed("Invalid job_key supplied.")
        job = self.__authorize_job_access(trans, job_id, supplied)
        trans.app.authnz_manager.refresh_expiring_oidc_tokens(trans, job.user)  # type: ignore[attr-defined]
        tokens = job.user.get_oidc_tokens(provider_name_to_backend(provider))
        return tokens["id"]

    def __authorize_job_access(self, trans, encoded_job_id, job_key):
        session = trans.sa_session
        job_id = trans.security.decode_id(encoded_job_id)
        job = session.get(Job, job_id)
        if job is None:
            raise exceptions.AuthenticationFailed("Invalid job_key supplied.")

        expected = trans.security.encode_id(job_id, kind=job_token_kind_for_job(job))
        if not util.safe_str_cmp(expected, job_key):
            raise exceptions.AuthenticationFailed("Invalid job_key supplied.")

        # Verify job is active
        if job.state not in Job.non_ready_states:
            error_message = "Attempting to get oidc token for a job that has already completed."
            raise exceptions.ItemAccessibilityException(error_message)
        return job
