"""API endpoint that lets the interactive-tool container-monitor report back
the host/port a running entry point can be reached at.
"""

import logging
from typing import Any

from galaxy.exceptions import ObjectAttributeMissingException
from galaxy.job_execution.job_security import resolve_job_key
from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.job_files import JobFilesManager
from galaxy.web import expose_api_anonymous_and_sessionless
from . import (
    BaseGalaxyAPIController,
    depends,
)

log = logging.getLogger(__name__)


class JobPortsAPIController(BaseGalaxyAPIController):
    """This job files controller allows remote job running mechanisms to
    modify the current state of ports for queued and running jobs.
    It is certainly not meant to represent part of Galaxy's stable, user
    facing API.

    See the JobFiles API for information about per-job API keys.
    """

    manager: JobFilesManager = depends(JobFilesManager)

    @expose_api_anonymous_and_sessionless
    def create(
        self,
        trans: ProvidesAppContext,
        job_id: str,
        payload: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, str]:
        """
        create( self, trans, job_id, payload, **kwargs )
        * POST /api/jobs/{job_id}/ports
            Populate port information for interactive tools.

        :type   job_id: str
        :param  job_id: encoded id string of the job
        :type   payload:    dict
        :param  payload:    dictionary structure containing::
            'job_key'           = Key authenticating
            'container_runtime' = Path to file to create.

        ..note:
            This API method is intended only for consumption by job runners,
            not end users.

        :rtype:     dict
        :returns:   an okay message
        """
        payload.update(kwargs)
        auth_header = trans.request.headers.get("Authorization")  # type: ignore[attr-defined]
        supplied = resolve_job_key(auth_header, payload.get("job_key"))
        if not supplied:
            raise ObjectAttributeMissingException("Job files action requires a valid 'job_key'.")
        job = self.manager.authorize_for_files(job_id, supplied)
        container_runtime = payload.get("container_runtime")
        if container_runtime is None:
            raise ObjectAttributeMissingException("Job ports action requires a 'container_runtime' mapping.")
        log.info(payload)
        trans.app.interactivetool_manager.configure_entry_points(job, container_runtime)
        return {"message": "ok"}
