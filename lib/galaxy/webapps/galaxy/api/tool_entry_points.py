"""API for asynchronous job running mechanisms can use to fetch or put files
related to running and queued jobs.
"""

import logging

from galaxy import (
    exceptions,
    util,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import (
    InteractiveToolEntryPoint,
    Job,
)
from galaxy.security.idencoding import IdAsLowercaseAlphanumEncodingHelper
from galaxy.structured_app import StructuredApp
from galaxy.web import expose_api_anonymous_and_sessionless
from . import BaseGalaxyAPIController

log = logging.getLogger(__name__)


class ToolEntryPointsAPIController(BaseGalaxyAPIController):
    def __init__(self, app: StructuredApp):
        self.app = app
        self.interactivetool_manager = app.interactivetool_manager

    @expose_api_anonymous_and_sessionless
    def index(self, trans: ProvidesUserContext, running=False, job_id=None, **kwd):
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
            raise exceptions.RequestParameterInvalidException(
                "Currently this API must passed only a job id or running=true"
            )

        if job_id is not None:
            job = trans.sa_session.get(Job, self.decode_id(job_id))
            assert job
            if not self.interactivetool_manager.can_access_job(trans, job):
                raise exceptions.ItemAccessibilityException()
            entry_points = job.interactivetool_entry_points
        if running:
            entry_points = self.interactivetool_manager.get_nonterminal_for_user_by_trans(trans)

        rval = []
        for entry_point in entry_points:
            entrypoint_id_encoder = IdAsLowercaseAlphanumEncodingHelper(trans.security)
            as_dict = entry_point.to_dict()
            as_dict["id"] = entrypoint_id_encoder.encode_id(as_dict["id"])
            as_dict_no_id = {k: v for k, v in as_dict.items() if k != "id"}
            as_dict.update(self.encode_all_ids(trans, as_dict_no_id, True))
            target = self.interactivetool_manager.target_if_active(trans, entry_point)
            if target:
                as_dict["target"] = target
            rval.append(as_dict)
        return rval

    @expose_api_anonymous_and_sessionless
    def access_entry_point(self, trans: ProvidesUserContext, id, **kwd):
        """
        * GET /api/entry_points/{id}/access
            Return the URL target described by the entry point.

        :type   id: string
        :param  id: Encoded entry point id

        :rtype:     dictionary
        :returns:   dictionary containing target for interactivetool entry point
        """
        # Because of auto id encoding needed for link from grid, the item.id keyword must be 'id'
        if not id:
            raise exceptions.RequestParameterMissingException("Must supply entry point ID.")
        entrypoint_id_encoder = IdAsLowercaseAlphanumEncodingHelper(trans.security)
        entry_point_id = entrypoint_id_encoder.decode_id(id)
        return {"target": self.interactivetool_manager.access_entry_point_target(trans, entry_point_id)}

    @expose_api_anonymous_and_sessionless
    def stop_entry_point(self, trans: ProvidesUserContext, id, **kwds):
        """
        DELETE /api/entry_points/{id}
        """
        if not id:
            raise exceptions.RequestParameterMissingException("Must supply entry point id")
        try:
            entrypoint_id_encoder = IdAsLowercaseAlphanumEncodingHelper(trans.security)
            entry_point_id = entrypoint_id_encoder.decode_id(id)
            entry_point = trans.sa_session.get(InteractiveToolEntryPoint, entry_point_id)
        except Exception:
            raise exceptions.RequestParameterInvalidException("entry point invalid")
        if self.app.interactivetool_manager.can_access_entry_point(trans, entry_point):
            self.app.interactivetool_manager.stop(trans, entry_point)
        else:
            raise exceptions.ItemAccessibilityException("entry point is not accessible")
