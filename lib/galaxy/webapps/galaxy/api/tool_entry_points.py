""" API for asynchronous job running mechanisms can use to fetch or put files
related to running and queued jobs.
"""
import logging

from galaxy import exceptions, util
from galaxy.managers.realtime import RealTimeManager
from galaxy.web import expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class ToolEntryPointsAPIController(BaseAPIController):

    def __init__(self, app):
        self.app = app
        self.realtime_manager = RealTimeManager(app)

    @expose_api_anonymous_and_sessionless
    def index(self, trans, running=False, job_id=None, **kwd):
        """
        * GET /api/entry_points
            Returns tool entry point information. Currently passing a job_id
            parameter is required, as this becomes more general that won't be
            needed.

        :type   job_id: string
        :param  job_id: Encoded job id

        :type   running: boolean
        :param  running: filter to only include running job entry points.

        :rtype:     list
        :returns:   list of entry point dictionaries.
        """
        running = util.asbool(running)
        if job_id is None and not running:
            raise exceptions.RequestParameterInvalidException("Currently this API must passed a job id or running=true")

        if job_id is not None and running:
            raise exceptions.RequestParameterInvalidException("Currently this API must passed only a job id or running=true")

        if job_id is not None:
            job = trans.sa_session.query(trans.app.model.Job).get(self.decode_id(job_id))
            if not self.realtime_manager.can_access_job(trans, job):
                raise exceptions.ItemAccessibilityException()
            entry_points = job.realtimetool_entry_points
        if running:
            entry_points = self.realtime_manager.get_nonterminal_for_user_by_trans(trans)

        rval = []
        for entry_point in entry_points:
            as_dict = self.encode_all_ids(trans, entry_point.to_dict(), True)
            target = self.realtime_manager.target_if_active(trans, entry_point)
            if target:
                as_dict["target"] = target
            rval.append(as_dict)
        return rval

    @expose_api_anonymous_and_sessionless
    def access_entry_point(self, trans, id, **kwd):
        """
        * GET /api/entry_points/{id}/access
            Return the URL target described by the entry point.

        :type   id: string
        :param  id: Encoded entry point id

        :rtype:     dictionary
        :returns:   dictionary containing target for realtime entry point
        """
        # Because of auto id encoding needed for link from grid, the item.id keyword must be 'id'
        if not id:
            raise exceptions.RequestParameterMissingException("Must supply entry point ID.")
        entry_point_id = self.decode_id(id)
        return {"target": self.realtime_manager.access_entry_point_target(trans, entry_point_id)}
