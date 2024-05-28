""" API asynchronous job running mechanisms can use to get a fresh OIDC token.
"""

import logging

from fastapi import Query
from fastapi.responses import PlainTextResponse

from galaxy import (
    exceptions,
    util,
)
from galaxy.authnz.util import provider_name_to_backend
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
        job_key: str = Query(
            description=(
                "A key used to authenticate this request as acting on behalf or a job runner for the specified job"
            ),
        ),
        provider: str = Query(
            description=("OIDC provider name"),
        ),
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> str:
        job = self.__authorize_job_access(trans, job_id, job_key)
        trans.app.authnz_manager.refresh_expiring_oidc_tokens(trans, job.user)  # type: ignore[attr-defined]
        tokens = job.user.get_oidc_tokens(provider_name_to_backend(provider))
        return tokens["id"]

    def __authorize_job_access(self, trans, encoded_job_id, job_key):
        session = trans.sa_session
        job_id = trans.security.decode_id(encoded_job_id)
        job = session.get(Job, job_id)
        secret = job.destination_params.get("job_secret_base", "jobs_token")

        job_key_internal = trans.security.encode_id(job_id, kind=secret)
        if not util.safe_str_cmp(job_key_internal, job_key):
            raise exceptions.AuthenticationFailed("Invalid job_key supplied.")

        # Verify job is active
        job = session.get(Job, job_id)
        if job.state not in Job.non_ready_states:
            error_message = "Attempting to get oidc token for a job that has already completed."
            raise exceptions.ItemAccessibilityException(error_message)
        return job
