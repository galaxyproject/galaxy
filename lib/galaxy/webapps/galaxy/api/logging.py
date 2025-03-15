"""
API to allow admin users to view and set logging levels for Galaxy loggers.
"""

import logging
import threading

from galaxy.managers.context import ProvidesUserContext
from galaxy.util.logging import get_log_levels
from . import DependsOnTrans, Router

log = logging.getLogger(__name__)
router = Router(tags=["logging"])

@router.cbv
class FastApiLoggingManager:

    @router.get(
        "/api/logging", summary="Get logging levels for all configured loggers", require_admin=True
    )
    def index(self, trans=DependsOnTrans):
        log.info("Getting all logger leverls")
        return get_log_levels(None)

    @router.get(
        "/api/logging/{logger_name}",
        summary="Get the logging level for one or more loggers",
        response_description="The logging level for the logger(s)",
        require_admin=True
    )
    def get(self, logger_name, trans: ProvidesUserContext = DependsOnTrans):
        log.info("Getting log level for %s", logger_name)
        return get_log_levels(logger_name)

    @router.post(
        "/api/logging/{logger_name}", summary="Set the logging level for one or more loggers", require_admin=True
    )
    def set(self, logger_name, level, trans: ProvidesUserContext = DependsOnTrans):
        log.info("Setting log level for %s to %s", logger_name, level)
        # We don't need the response, but we want to make sure the task is done before we return
        trans.app.queue_worker.send_control_task("set_logging_levels", kwargs={"name":logger_name, "level":level}, get_response=True)
        return get_log_levels(logger_name)

