"""
Per-request SQL debugging middleware.
"""
import logging

log = logging.getLogger(__name__)


class SQLDebugMiddleware(object):

    def __init__(self, application, galaxy, config=None):
        #: the wrapped webapp
        self.application = application

    def __call__(self, environ, start_response):
        query_string = environ.get('QUERY_STRING')
        if "sql_debug=1" in query_string:
            import galaxy.app
            if galaxy.app.app.model.thread_local_log:
                galaxy.app.app.model.thread_local_log.log = True

        return self.application(environ, start_response)
