"""
Middleware for sending request statistics to statsd
"""
from __future__ import absolute_import
import time
import statsd


class StatsdMiddleware(object):
    """
    This logging middleware will log request durations to the configured statsd
    instance.
    """

    def __init__(self,
                 application,
                 statsd_host,
                 statsd_port):
        self.application = application
        self.statsd_client = statsd.StatsClient(statsd_host, statsd_port, prefix='galaxy')

    def __call__(self, environ, start_response):
        start_time = time.time()
        req = self.application(environ, start_response)
        dt = int((time.time() - start_time) * 1000)
        self.statsd_client.timing(environ.get('PATH_INFO', "NOPATH").strip('/').replace('/', '.'), dt)
        return req
