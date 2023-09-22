# GALAXY_CONFIG_OVERRIDE_STATSD_PREFIX="galaxy" GALAXY_CONFIG_OVERRIDE_STATSD_HOST="localhost" GALAXY_CONFIG_OVERRIDE_STATSD_INFLUXDB="true" GALAXY_CONFIG_OVERRIDE_DATABASE_LOG_QUERY_COUNTS="true" GALAXY_CONFIG_OVERRIDE_ENABLE_PER_REQUEST_SQL_DEBUGGING="true" GALAXY_CONFIG_OVERRIDE_SLOW_QUERY_LOG_THRESHOLD=".05" ./run_tests.sh --structured_data_report_file 'test.json' --api  lib/galaxy_test/api/test_configuration.py
import os
import uuid
from urllib.parse import urlencode

import pytest
import requests

from galaxy.util import DEFAULT_SOCKET_TIMEOUT
from galaxy.web import statsd_client as statsd


@pytest.fixture(scope="session", autouse=True)
def celery_includes():
    yield ["galaxy.celery.tasks"]


def get_timings(test_uuid):
    # timestamps didn't work - telegraf didn't sample at small enough granularity
    # fs = datetime.datetime.fromtimestamp(from_timestamp).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    # ts = datetime.datetime.fromtimestamp(to_timestamp).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    params = {
        "db": "telegraf",
        "q": f"select * from galaxy_ where test='{test_uuid}'",
    }
    query = urlencode(params)
    headers = {"content-type": "application/json"}
    url = f"http://localhost:8086/query?{query}"
    response = requests.get(url, headers=headers, timeout=DEFAULT_SOCKET_TIMEOUT)
    if response.ok:
        return response.json()
    else:
        return None


def pytest_configure(config):
    if config.pluginmanager.hasplugin("pytest_jsonreport"):
        if config.getoption("json_report"):
            config.pluginmanager.register(JsonReportHooks())


class JsonReportHooks:
    def pytest_json_runtest_metadata(self, item, call):
        if call.when == "setup":
            statsd.CURRENT_TEST = str(uuid.uuid4())
            statsd.CURRENT_TEST_METRICS = {"timing": {}, "counter": {}}
            return {}
        if call.when == "teardown":
            statsd.CURRENT_TEST = None
            statsd.CURRENT_TEST_METRICS = None
            return {}
        if call.when != "call":
            return {}
        return {
            "start": call.start,
            "stop": call.stop,
            "uuid": statsd.CURRENT_TEST,
            "local_metrics": statsd.CURRENT_TEST_METRICS,
        }

    def pytest_json_modifyreport(self, json_report):
        if os.environ.get("GALAXY_TEST_COLLECT_STATSD", "0") != "0":
            for test in json_report["tests"]:
                metadata = test["metadata"]
                test_uuid = metadata["uuid"]
                metadata["statsd_metrics"] = get_timings(test_uuid)
