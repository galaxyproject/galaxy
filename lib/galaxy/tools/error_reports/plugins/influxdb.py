"""The module describes the ``influxdb`` error plugin plugin."""

import logging
from datetime import (
    datetime,
    timezone,
)

try:
    import influxdb
except ImportError:
    # This middleware will never be used without influxdb.
    influxdb = None

from galaxy.util import unicodify
from . import ErrorPlugin

log = logging.getLogger(__name__)


class InfluxDBPlugin(ErrorPlugin):
    """Send error report to InfluxDB"""

    plugin_type = "influxdb"

    def __init__(self, **kwargs):
        if not influxdb:
            raise ImportError(
                "Could not find InfluxDB Client, this error reporter will be disabled; please pip install influxdb"
            )

        self.app = kwargs["app"]
        # Neither of these matter
        self.verbose = False
        self.user_submission = False
        # Anything with influxdb_ gets sent to the client initialization
        influx_args = {k[len("influxdb_") :]: v for (k, v) in kwargs.items() if k.startswith("influxdb_")}
        print(influx_args)
        self.client = influxdb.InfluxDBClient(**influx_args)

    def submit_report(self, dataset, job, tool, **kwargs):
        """Submit the error report to sentry"""
        self.client.write_points(
            [
                {
                    "measurement": "galaxy_tool_error",
                    "time": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "fields": {"value": 1},
                    "tags": {
                        "exit_code": job.exit_code,
                        "tool_id": unicodify(job.tool_id),
                        "tool_version": unicodify(job.tool_version),
                        "tool_xml": unicodify(tool.config_file) if tool else None,
                        "destination_id": unicodify(job.destination_id),
                        "handler": unicodify(job.handler),
                    },
                }
            ]
        )
        return ("Submitted to InfluxDB", "success")


__all__ = ("InfluxDBPlugin",)
