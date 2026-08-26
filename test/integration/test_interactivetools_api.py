"""Integration tests for realtime tools."""

import json
import os
import subprocess
from typing import (
    Any,
)

import pytest
import requests

from galaxy_test.base import api_asserts
from galaxy_test.base.populators import (
    DatasetPopulator,
    wait_on,
)
from galaxy_test.driver import integration_util
from .test_coexecution import (
    CONTAINERIZED_TEMPLATE,
    job_config,
    set_infrastucture_url,
)
from .test_containerized_jobs import (
    ContainerizedIntegrationTestCase,
    disable_dependency_resolution,
    DOCKERIZED_JOB_CONFIG_FILE,
)
from .test_kubernetes_runner import (
    job_config as kubernetes_job_config,
    KubeSetupConfigTuple,
    persistent_volume,
    persistent_volume_claim,
    TOOL_DIR,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE_DOCKER = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_docker_job_conf.yml")
# The Kubernetes runner builds ingress hosts as "<subdomain>.<interactivetools_proxy_host>".
# Nothing connects to this host - the entry point is only inspected through the API and
# through the ingress object the runner created - but it has to be a valid DNS name.
KUBERNETES_PROXY_HOST = "interactivetool.test.invalid"


class AbstractTestCases:
    class BaseInteractiveToolsTestCase(ContainerizedIntegrationTestCase):
        """Configuration and helpers shared by interactive tool test cases.

        Holds no tests itself so that deployments which cannot reach an
        interactive tool through a proxy can still reuse the helpers.
        """

        dataset_populator: DatasetPopulator
        framework_tool_and_types = True
        container_type = "docker"
        enable_realtime_mapping = True

        def setUp(self) -> None:
            super().setUp()
            self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

        # Move helpers to populators.py
        def wait_on_proxied_content(self, target: str) -> str:
            def get_hosted_content() -> str | None:
                try:
                    scheme, rest = target.split("://", 1)
                    prefix, host_and_port = rest.split(".interactivetool.")
                    faked_host = rest
                    if "/" in rest:
                        faked_host = rest.split("/", 1)[0]
                    url = f"{scheme}://{host_and_port}"
                    response = requests.get(url, timeout=1, headers={"Host": faked_host})
                    response.raise_for_status()
                    return response.text
                except Exception as e:
                    print(e)
                    return None

            content = wait_on(get_hosted_content, f"realtime hosted content at {target}")
            return content

        def entry_point_target(self, entry_point_id: str) -> str:
            entry_point_access_response = self._get(f"entry_points/{entry_point_id}/access")
            api_asserts.assert_status_code_is(entry_point_access_response, 200)
            access_json = entry_point_access_response.json()
            api_asserts.assert_has_key(access_json, "target")
            return access_json["target"]

        def wait_on_entry_points_active(self, job_id: str, expected_num: int = 1) -> list[dict[str, Any]]:
            def active_entry_points() -> list[dict[str, Any]] | None:
                entry_points = self.entry_points_for_job(job_id)
                if len(entry_points) != expected_num:
                    return None
                elif any(not e["active"] for e in entry_points):
                    job_json = self._get(f"jobs/{job_id}?full=true").json()
                    if job_json["state"] == "error":
                        raise Exception(f"Interactive tool job {job_id} failed: {job_json}")
                    return None
                else:
                    return entry_points

            # It currently takes at least 90 seconds until we can be sure the container monitor failed.
            # Can be decreased when galaxy_ext/container_monitor/monitor.py changes
            return wait_on(active_entry_points, "entry points to become active", timeout=120)

        def entry_points_for_job(self, job_id: str) -> list[dict[str, Any]]:
            entry_points_response = self._get(f"entry_points?job_id={job_id}")
            api_asserts.assert_status_code_is(entry_points_response, 200)
            return entry_points_response.json()

    class BaseInteractiveToolsIntegrationTestCase(BaseInteractiveToolsTestCase):
        def test_simple_execution(self, history_id: str) -> None:
            response_dict = self.dataset_populator.run_tool("interactivetool_simple", {}, history_id)
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

        def test_multi_server_realtime_tool(self, history_id: str) -> None:
            response_dict = self.dataset_populator.run_tool("interactivetool_two_entry_points", {}, history_id)
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
            stop_response = self.dataset_populator._delete(f"entry_points/{entry_point0['id']}")
            stop_response.raise_for_status()
            self.dataset_populator.wait_for_job(job0["id"], assert_ok=True)
            job_details_response = self.dataset_populator.get_job_details(job0["id"], full=True)
            job_details_response.raise_for_status()
            job_details = job_details_response.json()
            assert job_details["state"] == "ok"
            it_output_details_response = self.dataset_populator.get_history_dataset_details_raw(
                history_id, dataset_id=job_details["outputs"]["test_output"]["id"]
            )
            it_output_details_response.raise_for_status()
            it_output_details = it_output_details_response.json()
            assert it_output_details["state"] == "ok"
            assert not it_output_details["deleted"]


class TestInteractiveToolsIntegration(AbstractTestCases.BaseInteractiveToolsIntegrationTestCase):
    pass


class TestInteractiveToolsPulsarIntegration(AbstractTestCases.BaseInteractiveToolsIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        config["job_config_file"] = EMBEDDED_PULSAR_JOB_CONFIG_FILE_DOCKER
        config["galaxy_infrastructure_url"] = "http://localhost:$GALAXY_WEB_PORT"
        disable_dependency_resolution(config)


class TestInteractiveToolsShortURLIntegration(AbstractTestCases.BaseInteractiveToolsIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = DOCKERIZED_JOB_CONFIG_FILE


class TestInteractiveToolsRemoteProxyIntegration(AbstractTestCases.BaseInteractiveToolsIntegrationTestCase):
    """
    $ cd gx-it-proxy
    $ ./lib/createdb.js --sessions $HOME/gxitexproxy.sqlite
    $ ./lib/main.js --port 9001 --ip 0.0.0.0 --verbose --sessions $HOME/gxitexproxy.sqlite
    $ # Need to create new DB for each test I think, duplicate IDs are the problem I think because each test starts at 1
    $ GALAXY_TEST_EXTERNAL_PROXY_HOST="localhost:9001" GALAXY_TEST_EXTERNAL_PROXY_MAP="$HOME/gxitexproxy.sqlite" pytest -s test/integration/test_interactivetools_api.py::TestInteractiveToolsRemoteProxyIntegration
    """

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        interactivetools_map = os.environ.get("GALAXY_TEST_EXTERNAL_PROXY_MAP")
        interactivetools_proxy_host = os.environ.get("GALAXY_TEST_EXTERNAL_PROXY_HOST")
        if not interactivetools_map or not interactivetools_proxy_host:
            pytest.skip(
                f"External proxy not configured for test [map={interactivetools_map},host={interactivetools_proxy_host}]"
            )
        config["job_config_file"] = DOCKERIZED_JOB_CONFIG_FILE
        config["interactivetools_proxy_host"] = interactivetools_proxy_host
        config["interactivetools_map"] = interactivetools_map
        disable_dependency_resolution(config)


@integration_util.skip_unless_kubernetes()
@integration_util.skip_unless_amqp()
@integration_util.skip_if_github_workflow()
class TestKubeInteractiveToolsRemoteProxyIntegration(AbstractTestCases.BaseInteractiveToolsIntegrationTestCase):
    """
    $ git clone https://github.com/galaxyproject/gx-it-proxy.git $HOME/gx-it-proxy
    $ cd $HOME/gx-it-proxy/docker/k8s
    $ # Setup proxy inside K8 cluster with kubectl - including forwarding port 8910
    $ bash run.sh
    $ cd ../..  # back session.
    $ # Need new DB for every test.
    $ rm -rf $HOME/gxitk8proxy.sqlite
    $ ./lib/createdb.js --sessions $HOME/gxitk8proxy.sqlite
    $ ./lib/main.js --port 9002 --ip 0.0.0.0 --verbose --sessions $HOME/gxitk8proxy.sqlite --forwardIP localhost --forwardPort 8910 &
    $ cd back/to/galaxy
    $ GALAXY_TEST_K8S_EXTERNAL_PROXY_HOST="localhost:9002" GALAXY_TEST_K8S_EXTERNAL_PROXY_MAP="$HOME/gxitk8proxy.sqlite" pytest -s test/integration/test_interactivetools_api.py::TestKubeInteractiveToolsRemoteProxyIntegration
    """

    jobs_directory: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        cls.jobs_directory = os.path.realpath(cls._test_driver.mkdtemp())
        interactivetools_map = os.environ.get("GALAXY_TEST_K8S_EXTERNAL_PROXY_MAP")
        interactivetools_proxy_host = os.environ.get("GALAXY_TEST_K8S_EXTERNAL_PROXY_HOST")
        if not interactivetools_map or not interactivetools_proxy_host:
            pytest.skip(
                f"External proxy not configured for test [map={interactivetools_map},host={interactivetools_proxy_host}]"
            )

        config["interactivetools_proxy_host"] = interactivetools_proxy_host
        config["interactivetools_map"] = interactivetools_map

        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        config["job_config_file"] = job_config(CONTAINERIZED_TEMPLATE, cls.jobs_directory)
        config["default_job_shell"] = "/bin/sh"

        set_infrastucture_url(config)
        disable_dependency_resolution(config)


@integration_util.skip_unless_kubernetes()
class TestKubernetesNativeInteractiveToolsIntegration(AbstractTestCases.BaseInteractiveToolsTestCase):
    """Interactive tools submitted through ``KubernetesJobRunner`` itself.

    ``TestKubeInteractiveToolsRemoteProxyIntegration`` covers interactive tools on
    Kubernetes via Pulsar, so it never touches this runner. It also needs an
    externally started gx-it-proxy to reach the tool over HTTP, which is why it is
    skipped in CI. This case asserts only what the runner is responsible for -
    configuring the entry points and creating a matching ingress - so it needs no
    proxy and can run wherever a cluster is available.
    """

    jobs_directory: str
    persistent_volume_claims: list[KubeSetupConfigTuple]
    persistent_volumes: list[KubeSetupConfigTuple]

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        cls.jobs_directory = os.path.realpath(cls._test_driver.mkdtemp())
        volumes = [
            (cls.jobs_directory, "it-jobs-directory-volume", "it-jobs-directory-claim"),
            (TOOL_DIR, "it-tool-directory-volume", "it-tool-directory-claim"),
        ]
        cls.persistent_volumes = []
        cls.persistent_volume_claims = []
        for path, volume, claim in volumes:
            volume_obj = persistent_volume(path, volume)
            volume_obj.setup()
            cls.persistent_volumes.append(volume_obj)
            claim_obj = persistent_volume_claim(volume, claim)
            claim_obj.setup()
            cls.persistent_volume_claims.append(claim_obj)
        super().handle_galaxy_config_kwds(config)
        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        config["job_config_file"] = kubernetes_job_config(
            cls.jobs_directory,
            jobs_directory_claim="it-jobs-directory-claim",
            tool_directory_claim="it-tool-directory-claim",
        ).path
        config["default_job_shell"] = "/bin/sh"
        config["interactivetools_proxy_host"] = KUBERNETES_PROXY_HOST

    @classmethod
    def tearDownClass(cls) -> None:
        for claim in cls.persistent_volume_claims:
            claim.teardown()
        for volume in cls.persistent_volumes:
            volume.teardown()
        super().tearDownClass()

    @staticmethod
    def ingress_for_tool(tool_id: str) -> dict[str, Any]:
        ingresses = json.loads(subprocess.check_output(["kubectl", "get", "ingress", "-o", "json"]))["items"]
        matching = [
            i
            for i in ingresses
            if (i["metadata"].get("annotations") or {}).get("app.galaxyproject.org/tool_id") == tool_id
        ]
        assert len(matching) == 1, f"Expected exactly one ingress for {tool_id}, got {matching}"
        return matching[0]

    def test_entry_point_and_ingress(self, history_id: str) -> None:
        response_dict = self.dataset_populator.run_tool("interactivetool_simple", {}, history_id)
        job_id = response_dict["jobs"][0]["id"]
        entry_points = self.wait_on_entry_points_active(job_id)
        assert len(entry_points) == 1

        # interactivetool_simple declares requires_domain, so the runner routes it by
        # host and the ingress path stays at the root.
        ingress = self.ingress_for_tool("interactivetool_simple")
        rules = ingress["spec"]["rules"]
        assert len(rules) == 1, rules
        assert rules[0]["host"].endswith(f".{KUBERNETES_PROXY_HOST}"), rules[0]["host"]
        paths = rules[0]["http"]["paths"]
        assert len(paths) == 1, paths
        assert paths[0]["path"] == "/", paths[0]

        # Stop the entry point so the tool container does not outlive the test.
        stop_response = self.dataset_populator._delete(f'entry_points/{entry_points[0]["id"]}')
        stop_response.raise_for_status()
        self.dataset_populator.wait_for_job(job_id, assert_ok=True)
