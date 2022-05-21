import sys
from typing import (
    Dict,
    Optional,
    Type,
)

try:
    import statsd
except ImportError:
    statsd = None

from galaxy.util import asbool


# TODO: optimize with two separate implementations around statsd_influxdb?
class VanillaGalaxyStatsdClient:
    def __init__(self, statsd_host, statsd_port, statsd_prefix, statsd_influxdb, statsd_mock_calls=False):
        if not statsd:
            raise ImportError(
                "Statsd logging configured, but no statsd python module found. "
                "Please install the python statsd module to use this functionality."
            )

        self.metric_infix = ""
        self.statsd_influxdb = asbool(statsd_influxdb)
        if self.statsd_influxdb:
            statsd_prefix = statsd_prefix.strip(",")
        if statsd_mock_calls:
            self.statsd_client = MockStatsClient()
        else:
            self.statsd_client = statsd.StatsClient(statsd_host, statsd_port, prefix=statsd_prefix)

    def timing(self, path, time, tags=None):
        infix = self._effective_infix(path, tags)
        self.statsd_client.timing(infix + path, time)

    def incr(self, path, n=1, tags=None):
        infix = self._effective_infix(path, tags)
        self.statsd_client.incr(infix + path, n)

    def _effective_infix(self, path, tags):
        tags = tags or {}
        if self.statsd_influxdb and tags:
            return f",{','.join(f'{k}={v}' for k, v in tags.items())}" + ",path="
        if self.statsd_influxdb:
            return ",path="
        else:
            return ""


CURRENT_TEST: Optional[str] = None
CURRENT_TEST_METRICS: Optional[Dict[str, Dict]] = None


class PyTestGalaxyStatsdClient(VanillaGalaxyStatsdClient):
    def timing(self, path, time, tags=None):
        metrics = CURRENT_TEST_METRICS
        if metrics is not None:
            timing = metrics["timing"]
            if path not in timing:
                timing[path] = []
            timing[path].append({"time": time, "tags": tags})
        super().timing(path, time, tags=tags)

    def incr(self, path, n=1, tags=None):
        metrics = CURRENT_TEST_METRICS
        if metrics is not None:
            counter = metrics["counter"]
            if path not in counter:
                counter[path] = []
            counter[path].append({"n": n, "tags": tags})
        super().incr(path, n=n, tags=tags)

    def _effective_infix(self, path, tags):
        current_test = CURRENT_TEST
        if current_test is not None:
            tags = tags or {}
            tags["test"] = current_test
        return super()._effective_infix(path, tags)


class MockStatsClient:
    def timing(self, path, time, tags=None):
        pass

    def incr(self, path, n=1, tags=None):
        pass


GalaxyStatsdClient: Type[VanillaGalaxyStatsdClient]
# Replace stats collector if in pytest environment
if "pytest" in sys.modules:
    GalaxyStatsdClient = PyTestGalaxyStatsdClient
else:
    GalaxyStatsdClient = VanillaGalaxyStatsdClient


__all__ = ("GalaxyStatsdClient",)
