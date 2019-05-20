""" API for asynchronous job running mechanisms can use to fetch or put files
related to running and queued jobs.
"""
import logging

from galaxy import exceptions
from galaxy.managers.realtime import RealTimeManager
from galaxy.web import expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class ToolEntryPointsAPIController(BaseAPIController):

    @expose_api_anonymous_and_sessionless
    def access_entry_point(self, trans, id, **kwd):
        # Because of auto id encoding needed for link from grid, the item.id keyword must be 'id'
        if not id:
            raise exceptions.RequestParameterMissingException("Must supply entry point ID.")
        entry_point_id = self.decode_id(id)
        return {"target": RealTimeManager(self.app).access_entry_point_target(trans, entry_point_id)}
