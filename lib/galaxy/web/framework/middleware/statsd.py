"""
Middleware for sending request statistics to statsd.
"""

import time

from galaxy.model.orm.engine_factory import QUERY_COUNT_LOCAL
from galaxy.web.statsd_client import GalaxyStatsdClient


class StatsdMiddleware:
    """
    This middleware will log request durations to the configured statsd
    instance.
    """

    def __init__(self, application, statsd_host, statsd_port, statsd_prefix, statsd_influxdb, statsd_mock_calls):
        self.application = application
        self.galaxy_stasd_client = GalaxyStatsdClient(
            statsd_host,
            statsd_port,
            statsd_prefix,
            statsd_influxdb,
            statsd_mock_calls,
        )

    def __call__(self, environ, start_response):
        start_time = time.time()
        req = self.application(environ, start_response)
        dt = int((time.time() - start_time) * 1000)
        page = environ.get("controller_action_key", None) or environ.get("PATH_INFO", "NOPATH").strip("/").replace(
            "/", "."
        )
        self.galaxy_stasd_client.timing(page, dt)
        try:
            times = QUERY_COUNT_LOCAL.times
            self.galaxy_stasd_client.timing(f"sql.{page}", sum(times) * 1000.0)
            self.galaxy_stasd_client.incr(f"sqlqueries.{page}", len(times))
        except AttributeError:
            # Not logging query counts, skip
            pass
        return req
