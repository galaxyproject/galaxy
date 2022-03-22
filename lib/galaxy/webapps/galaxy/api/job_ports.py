""" API for asynchronous job running mechanisms can use to fetch or put files
related to running and queued jobs.
"""
from galaxy.job_execution.ports import JobPortsView
from galaxy.structured_app import StructuredApp
from galaxy.web import expose_api_anonymous_and_sessionless
from . import BaseGalaxyAPIController


class JobPortsAPIController(BaseGalaxyAPIController):
    """This job files controller allows remote job running mechanisms to
    modify the current state of ports for queued and running jobs.
    It is certainly not meant to represent part of Galaxy's stable, user
    facing API.

    See the JobFiles API for information about per-job API keys.
    """

    def __init__(self, app: StructuredApp):
        super().__init__(app)
        self._job_ports_view = JobPortsView(app)

    @expose_api_anonymous_and_sessionless
    def create(self, trans, job_id, payload, **kwargs):
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
        return self._job_ports_view.register_container_information(job_id, **payload)
