"""
Per-request SQL debugging middleware.
"""

import logging

from galaxy.model.orm.engine_factory import (
    log_request_query_counts,
    reset_request_query_counts,
)

log = logging.getLogger(__name__)


class SQLDebugMiddleware:
    def __init__(self, application, galaxy, config=None):
        #: the wrapped webapp
        self.application = application

    def __call__(self, environ, start_response):
        query_string = environ.get("QUERY_STRING")
        if "sql_debug=1" in query_string:
            import galaxy.app

            if galaxy.app.app.model.thread_local_log:
                galaxy.app.app.model.thread_local_log.log = True

        try:
            reset_request_query_counts()
            return self.application(environ, start_response)
        finally:
            log_request_query_counts(environ.get("PATH_INFO"))
