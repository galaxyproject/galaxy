"""Integration tests for realtime tools."""

import os

import requests

from galaxy_test.base import api_asserts
from galaxy_test.base.populators import (
    DatasetPopulator,
    wait_on,
)
from .test_containerized_jobs import (
    ContainerizedIntegrationTestCase,
    disable_dependency_resolution,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE_DOCKER = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_docker_job_conf.yml")


class BaseInteractiveToolsIntegrationTestCase(ContainerizedIntegrationTestCase):
    framework_tool_and_types = True
    container_type = "docker"
    require_uwsgi = True
    enable_realtime_mapping = True

    def setUp(self):
        super(BaseInteractiveToolsIntegrationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()

    # Move helpers to populators.py
    def wait_on_proxied_content(self, target):
        def get_hosted_content():
            try:
                scheme, rest = target.split("://", 1)
                prefix, host_and_port = rest.split(".interactivetool.")
                faked_host = rest
                if "/" in rest:
                    faked_host = rest.split("/", 1)[0]
                url = "%s://%s" % (scheme, host_and_port)
                response = requests.get(url, timeout=1, headers={"Host": faked_host})
                return response.text
            except Exception as e:
                print(e)
                return None

        content = wait_on(get_hosted_content, "realtime hosted content at %s" % target)
        return content

    def entry_point_target(self, entry_point_id):
        entry_point_access_response = self._get("entry_points/%s/access" % entry_point_id)
        api_asserts.assert_status_code_is(entry_point_access_response, 200)
        access_json = entry_point_access_response.json()
        api_asserts.assert_has_key(access_json, "target")
        return access_json["target"]

    def wait_on_entry_points_active(self, job_id, expected_num=1):
        def active_entry_points():
            entry_points = self.entry_points_for_job(job_id)
            if len(entry_points) != expected_num:
                return None
            elif any([not e["active"] for e in entry_points]):
                return None
            else:
                return entry_points

        return wait_on(active_entry_points, "entry points to become active")

    def entry_points_for_job(self, job_id):
        entry_points_response = self._get("entry_points?job_id=%s" % job_id)
        api_asserts.assert_status_code_is(entry_points_response, 200)
        return entry_points_response.json()


class RunsInterativeToolTests(object):

    def test_simple_execution(self):
        response_dict = self.dataset_populator.run_tool("interactivetool_simple", {}, self.history_id, assert_ok=True)
        assert "jobs" in response_dict, response_dict
        jobs = response_dict["jobs"]
        assert isinstance(jobs, list)
        assert len(jobs) == 1
        job0 = jobs[0]
        entry_points = self.wait_on_entry_points_active(job0["id"])
        assert len(entry_points) == 1
        entry_point0 = entry_points[0]
        target = self.entry_point_target(entry_point0["id"])
        content = self.wait_on_proxied_content(target)
        assert content == "moo cow\n", content

    def test_multi_server_realtime_tool(self):
        response_dict = self.dataset_populator.run_tool("interactivetool_two_entry_points", {}, self.history_id, assert_ok=True)
        assert "jobs" in response_dict, response_dict
        jobs = response_dict["jobs"]
        assert isinstance(jobs, list)
        assert len(jobs) == 1
        job0 = jobs[0]
        entry_points = self.wait_on_entry_points_active(job0["id"], expected_num=2)
        entry_point0 = entry_points[0]
        entry_point1 = entry_points[1]
        target0 = self.entry_point_target(entry_point0["id"])
        target1 = self.entry_point_target(entry_point1["id"])
        assert target0 != target1
        content0 = self.wait_on_proxied_content(target0)
        assert content0 == "moo cow\n", content0

        content1 = self.wait_on_proxied_content(target1)
        assert content1 == "moo cow\n", content1


class InteractiveToolsIntegrationTestCase(BaseInteractiveToolsIntegrationTestCase, RunsInterativeToolTests):
    pass


class InteractiveToolsPulsarIntegrationTestCase(BaseInteractiveToolsIntegrationTestCase, RunsInterativeToolTests):

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["job_config_file"] = EMBEDDED_PULSAR_JOB_CONFIG_FILE_DOCKER
        config["galaxy_infrastructure_url"] = 'http://localhost:$UWSGI_PORT'
        disable_dependency_resolution(config)
