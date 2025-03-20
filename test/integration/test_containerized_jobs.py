"""Integration tests for running tools in Docker containers."""

import json
import os
import unittest
from typing import (
    Any,
    Dict,
)

from galaxy.util.commands import which
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import IntegrationTestCase
from .test_job_environments import BaseJobEnvironmentIntegrationTestCase

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

# local_docker
# local_docker_inline_container_resolvers (using only fallback resolver)_
DOCKERIZED_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "dockerized_job_conf.yml")
# define an environment (local_singularity) for local execution with singularity enabled
SINGULARITY_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "singularity_job_conf.yml")

EXTENDED_TIMEOUT = 120


class MulledJobTestCases:
    """
    test cases for mulled containers
    """

    dataset_populator: DatasetPopulator
    container_type: str

    def _run_and_get_contents(self, tool_id: str, history_id: str):
        run_response = self.dataset_populator.run_tool(tool_id, {}, history_id)
        job_id = run_response["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(job_id=job_id, assert_ok=True, timeout=EXTENDED_TIMEOUT)
        job_metrics = self.dataset_populator._get(f"/api/jobs/{job_id}/metrics").json()
        # would be nice if it wasn't just a list of unpredictable order ...
        container_id = None
        container_type = None
        for metric in job_metrics:
            if metric["name"] == "container_id":
                container_id = metric["value"]
            if metric["name"] == "container_type":
                container_type = metric["value"]
        assert container_id, "Job metrics did not include container_id"
        assert container_type, "Job metrics did not include container_type"
        assert container_type == self.container_type
        return self.dataset_populator.get_history_dataset_content(
            history_id, content_id=run_response["outputs"][0]["id"]
        )

    def test_explicit(self, history_id: str) -> None:
        """
        tool having one package + one explicit container requirement
        """
        output = self._run_and_get_contents("mulled_example_explicit", history_id)
        assert "0.7.15-r1140" in output

    def test_mulled_simple(self, history_id: str) -> None:
        """
        tool having one package requirement
        """
        output = self._run_and_get_contents("mulled_example_simple", history_id)
        assert "0.7.15-r1140" in output

    def test_mulled_explicit_invalid_case(self, history_id: str) -> None:
        """
        tool having one package + one (invalid? due to capitalization) explicit container requirement
        """
        output = self._run_and_get_contents("mulled_example_invalid_case", history_id)
        assert "0.7.15-r1140" in output


class ContainerizedIntegrationTestCase(IntegrationTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        skip_if_container_type_unavailable(cls)
        super().setUpClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = DOCKERIZED_JOB_CONFIG_FILE
        disable_dependency_resolution(config)


def disable_dependency_resolution(config: Dict[str, Any]) -> None:
    # Disable tool dependency resolution.
    config["tool_dependency_dir"] = "none"
    config["conda_auto_init"] = False
    config["conda_auto_install"] = False


def skip_if_container_type_unavailable(cls) -> None:
    if not which(cls.container_type):
        raise unittest.SkipTest(f"Executable '{cls.container_type}' not found on PATH")


class TestDockerizedJobsIntegration(BaseJobEnvironmentIntegrationTestCase, MulledJobTestCases):
    dataset_populator: DatasetPopulator
    jobs_directory: str
    job_config_file = DOCKERIZED_JOB_CONFIG_FILE
    build_mulled_resolver = "build_mulled"
    container_type = "docker"

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)

    @classmethod
    def setUpClass(cls) -> None:
        skip_if_container_type_unavailable(cls)
        super().setUpClass()

    def setUp(self) -> None:
        super().setUp()

    def test_container_job_environment(self) -> None:
        """
        test job environment for non-legacy tools
        """
        job_env = self._run_and_get_environment_properties("job_environment_default")

        euid = os.geteuid()
        egid = os.getgid()

        assert job_env.user_id == str(euid), job_env.user_id
        assert job_env.group_id == str(egid), job_env.group_id
        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert job_env.home.startswith(self.jobs_directory)
        assert job_env.home.endswith("/home")

    def test_container_job_environment_legacy(self) -> None:
        """
        test that legacy tools use the user's home (/home/...)
        use the current user's home and do not use a dir in the JWD as home
        """
        job_env = self._run_and_get_environment_properties("job_environment_default_legacy")

        euid = os.geteuid()
        egid = os.getgid()

        assert job_env.user_id == str(euid), job_env.user_id
        assert job_env.group_id == str(egid), job_env.group_id
        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert not job_env.home.startswith(self.jobs_directory)
        assert not job_env.home.endswith("/home")

    def test_container_job_environment_explicit_shared_home(self) -> None:
        """
        test that non-legacy tools that explicitly specify
        <command use_shared_home="true"> use the current user's home
        """
        job_env = self._run_and_get_environment_properties("job_environment_explicit_shared_home")

        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert not job_env.home.startswith(self.jobs_directory)
        assert not job_env.home.endswith("/home"), job_env.home

    def test_container_job_environment_explicit_isolated_home(self) -> None:
        """
        test that non-legacy tools that explicitly specify
        <command use_shared_home="false"> (the default) use a separate dir in the JWD as home
        """
        job_env = self._run_and_get_environment_properties("job_environment_explicit_isolated_home")

        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert job_env.home.startswith(self.jobs_directory)
        assert job_env.home.endswith("/home"), job_env.home

    def test_build_mulled(self) -> None:
        """
        test building of a mulled container using the build_mulled container resolver
        triggered via API dependency_resolvers/toolbox/install
        """
        resolver_type = self.build_mulled_resolver
        tool_ids = ["mulled_example_multi_1"]
        endpoint = "dependency_resolvers/toolbox/install"
        data = {
            "tool_ids": json.dumps(tool_ids),
            "resolver_type": resolver_type,
            "container_type": self.container_type,
            "include_containers": True,
        }
        create_response = self._post(endpoint, data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        create_response = self._get(
            "dependency_resolvers/toolbox",
            data={
                "tool_ids": tool_ids,
                "container_type": self.container_type,
                "include_containers": True,
                "index_by": "tools",
            },
            admin=True,
        )
        response = create_response.json()
        assert len(response) == 1
        status = response[0]["status"]
        assert status[0]["model_class"] == "ContainerDependency"
        assert status[0]["dependency_type"] == self.container_type
        self._assert_container_description_identifier(
            status[0]["container_description"]["identifier"],
            "mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:a6419f25efff953fc505dbd5ee734856180bb619-0",
        )

    def _assert_container_description_identifier(self, identifier: str, expected_hash: str):
        """
        function to check the identifier of container against a mulled hash
        here we assert that locally built containers are cached in the "local"
        namespace as if they were from quay.io

        may need to be overwritten in derived classes.
        """
        assert identifier == f"quay.io/local/{expected_hash}"


class TestMappingContainerResolver(IntegrationTestCase):
    """
    - test mapping resolver
    - test global container resolvers given in extra yaml file referenced via
      `container_resolvers_config_file` in galaxy.yml
    - container resolvers defined per destination in the job config
      should be ignored
      (TODO this is not tested since a fallback resolver pointing to the same container
       would be used)
    """

    dataset_populator: DatasetPopulator
    jobs_directory: str
    framework_tool_and_types = True
    container_type = "docker"
    job_config_file = DOCKERIZED_JOB_CONFIG_FILE

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)
        container_resolvers_config_path = os.path.join(cls.jobs_directory, "container_resolvers.yml")
        with open(container_resolvers_config_path, "w") as f:
            f.write(
                """
- type: mapping
  mappings:
    - container_type: docker
      tool_id: mulled_example_broken_no_requirements
      identifier: 'quay.io/biocontainers/bwa:0.7.15--0'
"""
            )
        config["container_resolvers_config_file"] = container_resolvers_config_path

    @classmethod
    def setUpClass(cls) -> None:
        skip_if_container_type_unavailable(cls)
        super().setUpClass()

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_explicit_mapping(self, history_id: str) -> None:
        self.dataset_populator.run_tool("mulled_example_broken_no_requirements", {}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(history_id, timeout=EXTENDED_TIMEOUT)
        assert "0.7.15-r1140" in output


class TestInlineContainerConfiguration(TestMappingContainerResolver):
    """
    Same as TestMappingContainerResolver, but defining container resolvers
    via `container_resolvers` (not testing the YAML parsing of inline container
    resolvers from galaxy.yml)
    """

    jobs_directory: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)
        config.pop("container_resolvers_config_file")
        container_resolvers_config = [
            {
                "type": "mapping",
                "mappings": [
                    {
                        "container_type": "docker",
                        "tool_id": "mulled_example_broken_no_requirements",
                        "identifier": "quay.io/biocontainers/bwa:0.7.15--0",
                    }
                ],
            }
        ]
        config["container_resolvers"] = container_resolvers_config


class TestPerDestinationContainerConfiguration(TestMappingContainerResolver):
    """
    This tests:
    - that container_resolvers_config_file works when specified in a destination
    - and it does so also in presence of a global container_resolvers_config
    """

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        # make sure that job_config_file is unset and set job_config
        # its the same content as dockerized_job_conf.yml + the per
        # destination container_resolver_config_file
        try:
            config.pop("job_config_file")
        except KeyError:
            pass
        config["job_config"] = {
            "runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner", "workers": 1}},
            "execution": {
                "default": "local_docker",
                "environments": {
                    "local_docker": {"runner": "local", "docker_enabled": True},
                    "local_docker_inline_container_resolvers": {
                        "runner": "local",
                        "docker_enabled": True,
                        "container_resolvers_config_file": os.path.join(
                            SCRIPT_DIRECTORY, "fallback_container_resolver.yml"
                        ),
                    },
                },
            },
            "tools": [
                {"id": "upload1", "environment": "local_upload"},
                {
                    "id": "mulled_example_broken_no_requirements",
                    "environment": "local_docker_inline_container_resolvers",
                },
            ],
        }
        # define a global container_resolvers (that can not work .. thereby
        # showing that the per destination config is used) and make sure that
        # container_resolvers_config_file is not set
        try:
            config.pop("container_resolvers_config_file")
        except KeyError:
            pass
        container_resolvers_config = [
            {
                "type": "mapping",
                "mappings": [
                    {
                        "container_type": "docker",
                        "tool_id": "some_bogus_too_id",
                        "identifier": "quay.io/biocontainers/bwa:0.7.15--0",
                    }
                ],
            }
        ]
        config["container_resolvers"] = container_resolvers_config


class TestInlineJobEnvironmentContainerResolver(IntegrationTestCase):
    """
    Test
    - container resolvers config given inline in job configuration (DOCKERIZED_JOB_CONFIG_FILE)
    - job config maps the tool to a destination (local_docker_inline_container_resolvers)
      which only runs the fallback container resolver (which uses bwa 0.7.15)
    - tool defines no requirements (irrelevant for this test)
    """

    dataset_populator: DatasetPopulator
    jobs_directory: str
    framework_tool_and_types = True
    container_type = "docker"
    job_config_file = DOCKERIZED_JOB_CONFIG_FILE

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)

    @classmethod
    def setUpClass(cls) -> None:
        skip_if_container_type_unavailable(cls)
        super().setUpClass()

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_inline_environment_container_resolver_configuration(self, history_id: str) -> None:
        self.dataset_populator.run_tool("mulled_example_broken_no_requirements_fallback", {}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(history_id, timeout=EXTENDED_TIMEOUT)
        assert "0.7.15-r1140" in output


class TestSingularityJobsIntegration(TestDockerizedJobsIntegration):
    job_config_file = SINGULARITY_JOB_CONFIG_FILE
    build_mulled_resolver = "build_mulled_singularity"
    container_type = "singularity"

    def _assert_container_description_identifier(self, identifier, expected_hash):
        assert os.path.exists(identifier)
        assert identifier.endswith(f"singularity/mulled/{expected_hash}")
