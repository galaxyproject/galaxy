"""Integration tests for Pulsar jobs whose files fail to transfer through Galaxy's job files API."""

import http.client
import re
import threading
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from typing import ClassVar
from urllib.parse import urlsplit

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

JOB_FILES_PATH = re.compile(r"^/api/jobs/[^/]+/files\?")
HOP_BY_HOP_HEADERS = {"connection", "content-length", "host", "transfer-encoding"}


class FlakyJobFilesProxy(ThreadingHTTPServer):
    """Forwards requests to Galaxy, answering the next job files request of an armed method with a 502.

    Pulsar does not retry staging by default, so a single 502 fails the job like the
    transient gateway errors seen in production.
    """

    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("localhost", 0), _FlakyJobFilesHandler)
        self.galaxy_url = ""
        self.failed_requests: list[str] = []
        self._fail_method: str | None = None
        self._lock = threading.Lock()

    @property
    def url(self) -> str:
        return f"http://localhost:{self.server_address[1]}"

    def fail_next(self, method: str) -> None:
        with self._lock:
            self._fail_method = method

    def should_fail(self, method: str, path: str) -> bool:
        with self._lock:
            if self._fail_method != method or not JOB_FILES_PATH.match(path):
                return False
            self._fail_method = None
            self.failed_requests.append(f"{method} {path}")
            return True


class _FlakyJobFilesHandler(BaseHTTPRequestHandler):
    server: FlakyJobFilesProxy

    def do_GET(self) -> None:
        self._forward()

    def do_POST(self) -> None:
        self._forward()

    def do_PUT(self) -> None:
        self._forward()

    def log_message(self, format, *args) -> None:
        pass

    def _forward(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        if self.server.should_fail(self.command, self.path):
            self.send_error(502, "Bad Gateway")
            return
        target = urlsplit(self.server.galaxy_url)
        connection = http.client.HTTPConnection(target.hostname or "localhost", target.port, timeout=60)
        try:
            headers = {key: value for key, value in self.headers.items() if key.lower() not in HOP_BY_HOP_HEADERS}
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            data = response.read()
        finally:
            connection.close()
        self.send_response(response.status)
        for key, value in response.getheaders():
            if key.lower() not in HOP_BY_HOP_HEADERS:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _job_config(galaxy_url: str) -> dict:
    staging = {"runner": "pulsar_embed", "default_file_action": "remote_transfer"}
    return {
        "runners": {
            "local": {"load": "galaxy.jobs.runners.local:LocalJobRunner"},
            "pulsar_embed": {
                "load": "galaxy.jobs.runners.pulsar:PulsarEmbeddedJobRunner",
                "galaxy_url": galaxy_url,
                "pulsar_app_config": {
                    "tool_dependency_dir": "none",
                    "conda_auto_init": False,
                    "conda_auto_install": False,
                },
            },
        },
        "execution": {
            "default": "staging_no_resubmit",
            "environments": {
                "local": {"runner": "local"},
                "staging_no_resubmit": staging,
                "input_staging_resubmit": {
                    **staging,
                    "resubmit": [{"condition": "input_staging_failed", "environment": "staging_retry"}],
                },
                "output_staging_resubmit": {
                    **staging,
                    "resubmit": [{"condition": "output_staging_failed", "environment": "staging_retry"}],
                },
                "staging_retry": staging,
            },
        },
        "tools": [
            {"class": "local", "environment": "local"},
            {"id": "cat", "environment": "input_staging_resubmit"},
            {"id": "job_properties", "environment": "output_staging_resubmit"},
        ],
    }


class TestEmbeddedPulsarStagingFailureIntegration(integration_util.IntegrationTestCase):
    framework_tool_and_types = True
    dataset_populator: DatasetPopulator
    proxy: ClassVar[FlakyJobFilesProxy]

    @classmethod
    def setUpClass(cls):
        cls.proxy = FlakyJobFilesProxy()
        threading.Thread(target=cls.proxy.serve_forever, daemon=True).start()
        try:
            super().setUpClass()
        except BaseException:
            cls.proxy.shutdown()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls.proxy.shutdown()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config"] = _job_config(cls.proxy.url)
        config["job_metrics"] = [{"type": "core"}]

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.proxy.galaxy_url = self.url
        self.proxy.failed_requests.clear()

    def _assert_resubmitted_once(self, run):
        job_id = run["jobs"][0]["id"]
        assert self.dataset_populator.get_job_details(job_id).json()["state"] == "ok"
        metrics = self._get(f"jobs/{job_id}/metrics", admin=True).json()
        assert {metric["name"]: metric["value"] for metric in metrics}["resubmission_count"] == "1"
        assert len(self.proxy.failed_requests) == 1

    def test_input_staging_failure_is_resubmitted(self):
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset(history_id, content="abc", wait=True)
            self.proxy.fail_next("GET")
            run = self.dataset_populator.run_tool("cat", {"input1": {"src": "hda", "id": dataset["id"]}}, history_id)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            self._assert_resubmitted_once(run)

    def test_output_staging_failure_is_resubmitted(self):
        with self.dataset_populator.test_history() as history_id:
            self.proxy.fail_next("POST")
            run = self.dataset_populator.run_tool("job_properties", {"thebool": True}, history_id)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            self._assert_resubmitted_once(run)

    def test_input_staging_failure_reason_is_shown(self):
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset(history_id, content="abc", wait=True)
            self.proxy.fail_next("GET")
            run = self.dataset_populator.run_tool(
                "cat_default", {"input1": {"src": "hda", "id": dataset["id"]}}, history_id
            )
            self.dataset_populator.wait_for_job(run["jobs"][0]["id"], assert_ok=False)
            output = self.dataset_populator.get_history_dataset_details(
                history_id, dataset_id=run["outputs"][0]["id"], assert_ok=False
            )
            assert output["state"] == "error"
            assert re.fullmatch(r"Failed to transfer input '[^']+': HTTP 502", output["misc_info"]), output["misc_info"]
            assert len(self.proxy.failed_requests) == 1
