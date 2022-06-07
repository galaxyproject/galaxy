"""Integration tests for running tools in Docker containers."""

import json
import os
import unittest

from galaxy.util.commands import which
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from .test_job_environments import BaseJobEnvironmentIntegrationTestCase

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
DOCKERIZED_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "dockerized_job_conf.yml")
SINGULARITY_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "singularity_job_conf.yml")
EXTENDED_TIMEOUT = 120


class MulledJobTestCases:
    def test_explicit(self):
        self.dataset_populator.run_tool("mulled_example_explicit", {}, self.history_id)
        self.dataset_populator.wait_for_history(self.history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(self.history_id, timeout=EXTENDED_TIMEOUT)
        assert "0.7.15-r1140" in output

    def test_mulled_simple(self):
        self.dataset_populator.run_tool("mulled_example_simple", {}, self.history_id)
        self.dataset_populator.wait_for_history(self.history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(self.history_id, timeout=EXTENDED_TIMEOUT)
        assert "0.7.15-r1140" in output

    def test_mulled_explicit_invalid_case(self):
        self.dataset_populator.run_tool("mulled_example_invalid_case", {}, self.history_id)
        self.dataset_populator.wait_for_history(self.history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(self.history_id, timeout=EXTENDED_TIMEOUT)
        assert "0.7.15-r1140" in output


class ContainerizedIntegrationTestCase(integration_util.IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        skip_if_container_type_unavailable(cls)
        super().setUpClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = DOCKERIZED_JOB_CONFIG_FILE
        disable_dependency_resolution(config)


def disable_dependency_resolution(config):
    # Disable tool dependency resolution.
    config["tool_dependency_dir"] = "none"
    config["conda_auto_init"] = False
    config["conda_auto_install"] = False


def skip_if_container_type_unavailable(cls):
    if not which(cls.container_type):
        raise unittest.SkipTest("Executable '%s' not found on PATH" % cls.container_type)


class DockerizedJobsIntegrationTestCase(BaseJobEnvironmentIntegrationTestCase, MulledJobTestCases):

    job_config_file = DOCKERIZED_JOB_CONFIG_FILE
    build_mulled_resolver = "build_mulled"
    container_type = "docker"

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)

    @classmethod
    def setUpClass(cls):
        skip_if_container_type_unavailable(cls)
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.history_id = self.dataset_populator.new_history()

    def test_container_job_environment(self):
        job_env = self._run_and_get_environment_properties("job_environment_default")

        euid = os.geteuid()
        egid = os.getgid()

        assert job_env.user_id == str(euid), job_env.user_id
        assert job_env.group_id == str(egid), job_env.group_id
        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert job_env.home.startswith(self.jobs_directory)
        assert job_env.home.endswith("/home")

    def test_container_job_environment_legacy(self):
        job_env = self._run_and_get_environment_properties("job_environment_default_legacy")

        euid = os.geteuid()
        egid = os.getgid()

        assert job_env.user_id == str(euid), job_env.user_id
        assert job_env.group_id == str(egid), job_env.group_id
        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert not job_env.home.endswith("/home")

    def test_container_job_environment_explicit_shared_home(self):
        job_env = self._run_and_get_environment_properties("job_environment_explicit_shared_home")

        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert not job_env.home.endswith("/home")

    def test_container_job_environment_explicit_isolated_home(self):
        job_env = self._run_and_get_environment_properties("job_environment_explicit_isolated_home")

        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert job_env.home.endswith("/home")

    def test_build_mulled(self):
        if not which("docker"):
            raise unittest.SkipTest("Docker not found on PATH, required for building images via involucro")
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
        assert status[0]["container_description"]["identifier"].startswith("quay.io/local/mulled-v2-")


class MappingContainerResolverTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True
    container_type = "docker"
    job_config_file = DOCKERIZED_JOB_CONFIG_FILE

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
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
    def setUpClass(cls):
        skip_if_container_type_unavailable(cls)
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()

    def test_explicit_mapping(self):
        self.dataset_populator.run_tool("mulled_example_broken_no_requirements", {}, self.history_id)
        self.dataset_populator.wait_for_history(self.history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(self.history_id, timeout=EXTENDED_TIMEOUT)
        assert "0.7.15-r1140" in output


class InlineContainerConfigurationTestCase(MappingContainerResolverTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)
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


class InlineJobEnvironmentContainerResolverTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True
    container_type = "docker"
    job_config_file = DOCKERIZED_JOB_CONFIG_FILE

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)

    @classmethod
    def setUpClass(cls):
        skip_if_container_type_unavailable(cls)
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()

    def test_inline_environment_container_resolver_configuration(self):
        self.dataset_populator.run_tool("mulled_example_broken_no_requirements_fallback", {}, self.history_id)
        self.dataset_populator.wait_for_history(self.history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(self.history_id, timeout=EXTENDED_TIMEOUT)
        assert "0.7.15-r1140" in output


# Singularity 2.4 in the official Vagrant issue has some problems running this test
# case by default because subdirectories of /tmp don't bind correctly. Overridding
# TMPDIR can fix this.
# TMPDIR=/home/vagrant/tmp/ pytest test/integration/test_containerized_jobs.py::SingularityJobsIntegrationTestCase
class SingularityJobsIntegrationTestCase(DockerizedJobsIntegrationTestCase):

    job_config_file = SINGULARITY_JOB_CONFIG_FILE
    build_mulled_resolver = "build_mulled_singularity"
    container_type = "singularity"
