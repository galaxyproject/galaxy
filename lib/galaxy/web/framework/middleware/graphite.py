"""
Middleware for sending request statistics to graphite
"""
from __future__ import absolute_import

import time
import logging
log = logging.getLogger(__name__)

try:
    import graphitesend
except ImportError:
    # This middleware will never be used without graphite. This block allows
    # unit tests pass on systems without it.
    graphitesend = None


class GraphiteMiddleware(object):
    """
    This middleware will log request durations to the configured graphite
    instance.
    """

    def __init__(self,
                 application,
                 graphite_host,
                 graphite_port,
                 graphite_prefix):
        if not graphitesend:
            raise ImportError("graphite middleware configured, but no graphite python module found. "
                              "Please install the python graphitesend module to use this functionality.")
        self.application = application
        try:
            self.graphite_client = graphitesend.init(graphite_server=graphite_host, graphite_port=int(graphite_port), prefix=graphite_prefix.rstrip('.'))
        except graphitesend.graphitesend.GraphiteSendException:
            self.graphite_client = None
            log.exception("Could not instantiate graphite metrics logger. It will be disabled until Galaxy restart")

    def __call__(self, environ, start_response):
        start_time = time.time()
        req = self.application(environ, start_response)
        # If graphite is disabled, exit early.
        if not self.graphite_client:
            return req

        dt = int((time.time() - start_time) * 1000)
        try:
            self.graphite_client.send(environ.get('controller_action_key', None) or environ.get('PATH_INFO', "NOPATH").strip('/').replace('/', '.'), dt)
        except graphitesend.GraphiteSendException:
            log.exception("Graphite Error")
        return req
