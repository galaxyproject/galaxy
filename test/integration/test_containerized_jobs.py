"""Integration tests for running tools in Docker containers."""

import os
import unittest

from base import integration_util
from base.populators import (
    DatasetPopulator,
)

from galaxy.tools.deps.commands import which
from .test_job_environments import RunsEnvironmentJobs

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
DOCKERIZED_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "dockerized_job_conf.xml")
SINGULARITY_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "singularity_job_conf.xml")
EXTENDED_TIMEOUT = 120


class MulledJobTestCases(object):
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


@integration_util.skip_unless_docker()
class DockerizedJobsIntegrationTestCase(integration_util.IntegrationTestCase, RunsEnvironmentJobs, MulledJobTestCases):

    framework_tool_and_types = True
    job_config_file = DOCKERIZED_JOB_CONFIG_FILE
    build_mulled_resolver = 'build_mulled'
    container_type = 'docker'
    default_container_home_dir = '/'

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        # Disable tool dependency resolution.
        config["tool_dependency_dir"] = "none"
        config["conda_auto_init"] = False
        config["conda_auto_install"] = False
        config["enable_beta_mulled_containers"] = "true"

    @classmethod
    def setUpClass(cls):
        if not which(cls.container_type):
            raise unittest.SkipTest("Executable '%s' not found on PATH" % cls.container_type)
        super(DockerizedJobsIntegrationTestCase, cls).setUpClass()

    def setUp(self):
        super(DockerizedJobsIntegrationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
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
        # Should we change env_pass_through to just always include TMP and HOME for docker?
        # I'm not sure, if yes this would change.
        assert job_env.home == self.default_container_home_dir, job_env.home

    def test_build_mulled(self):
        if not which('docker'):
            raise unittest.SkipTest("Docker not found on PATH, required for building images via involucro")
        resolver_type = self.build_mulled_resolver
        tool_id = 'mulled_example_multi_1'
        endpoint = "tools/%s/dependencies" % tool_id
        data = {'id': tool_id, 'resolver_type': resolver_type}
        create_response = self._post(endpoint, data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        assert any([True for d in response if d['dependency_type'] == self.container_type])


class SingularityJobsIntegrationTestCase(DockerizedJobsIntegrationTestCase):

    job_config_file = SINGULARITY_JOB_CONFIG_FILE
    build_mulled_resolver = 'build_mulled_singularity'
    container_type = 'singularity'
    # singularity passes $HOME by default
    default_container_home_dir = os.environ.get('HOME', '/')
