""" API for asynchronous job running mechanisms can use to fetch or put files
related to running and queued jobs.
"""
import logging

from galaxy import (
    exceptions,
    model,
    util,
)
from galaxy.authnz.util import provider_name_to_backend
from galaxy.web import expose_api_raw_anonymous_and_sessionless
from . import BaseGalaxyAPIController

log = logging.getLogger(__name__)


class JobTokensAPIController(BaseGalaxyAPIController):
    """This job token controller allows remote job running mechanisms to
    get a fresh OIDC token that can be used on remote side to authorize user.
    It is not meant to represent part of Galaxy's stable, user
    facing API.
    """

    @expose_api_raw_anonymous_and_sessionless
    def get_token(self, trans, job_id, **kwargs):
        """
        GET /api/jobs/{job_id}/oidc-tokens

        Get a fresh OIDC token

        :type   job_id: str
        :param  job_id: encoded id string of the job
        :type   provider: str
        :param  provider: Path to file.
        :type   job_key: str
        :param  job_key: A key used to authenticate this request as acting on
                         behalf or a job runner for the specified job.

        ..note:
            This API method is intended only for consumption by job runners,
            not end users.

        :rtype:     str
        :returns:   OIDC ID token
        """
        job = self.__authorize_job_access(trans, job_id, **kwargs)
        trans.app.authnz_manager.refresh_expiring_oidc_tokens(trans, job.user)  # type: ignore[attr-defined]
        provider = kwargs.get("provider", None)
        tokens = job.user.get_oidc_tokens(provider_name_to_backend(provider))
        return tokens["id"]

    def __authorize_job_access(self, trans, encoded_job_id, **kwargs):
        for key in ["provider", "job_key"]:
            if key not in kwargs:
                error_message = f"Job files action requires a valid '{key}'."
                raise exceptions.ObjectAttributeMissingException(error_message)

        job_id = trans.security.decode_id(encoded_job_id)
        job = trans.sa_session.query(model.Job).get(job_id)
        secret = "jobs_token"
        try:
            for plugin in self.app.job_config.runner_plugins:
                if plugin["id"] == job.job_runner_name:
                    secret = plugin["kwds"]["secret"]
        except Exception:
            pass

        job_key = trans.security.encode_id(job_id, kind=secret)
        if not util.safe_str_cmp(kwargs["job_key"], job_key):
            raise exceptions.ItemAccessibilityException("Invalid job_key supplied.")

        # Verify job is active
        job = trans.sa_session.query(model.Job).get(job_id)
        if job.finished:
            error_message = "Attempting to get oidc token for a job that has already completed."
            raise exceptions.ItemAccessibilityException(error_message)
        return job
