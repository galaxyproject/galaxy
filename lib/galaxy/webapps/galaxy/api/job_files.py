""" API for asynchronous job running mechanisms can use to fetch or put files
related to running and queued jobs.
"""
from galaxy.job_execution.files import JobFilesView
from galaxy.web import (
    expose_api_anonymous_and_sessionless,
    expose_api_raw_anonymous_and_sessionless,
)
from galaxy.webapps.base.controller import BaseAPIController


class JobFilesAPIController(BaseAPIController):
    """ This job files controller allows remote job running mechanisms to
    read and modify the current state of files for queued and running jobs.
    It is certainly not meant to represent part of Galaxy's stable, user
    facing API.

    Furthermore, even if a user key corresponds to the user running the job,
    it should not be accepted for authorization - this API allows access to
    low-level unfiltered files and such authorization would break Galaxy's
    security model for tool execution.
    """

    def __init__(self, app):
        self._job_files_view = JobFilesView(app)

    @expose_api_raw_anonymous_and_sessionless
    def index(self, trans, job_id, **kwargs):
        """
        index( self, trans, job_id, **kwargs )
        * GET /api/jobs/{job_id}/files
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
        return self._job_files_view.get_file(job_id, **kwargs)

    @expose_api_anonymous_and_sessionless
    def create(self, trans, job_id, payload, **kwargs):
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
        payload.update(kwargs)
        return self._job_files_view.post_file(job_id, **payload)
