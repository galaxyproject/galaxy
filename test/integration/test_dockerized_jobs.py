"""Integration tests for running tools in Docker containers."""

import os
import tempfile

from base import integration_util
from base.populators import (
    DatasetPopulator,
)

from .test_job_environments import RunsEnvironmentJobs

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
DOCKERIZED_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "dockerized_job_conf.xml")


@integration_util.skip_unless_docker()
class DockerizedJobsIntegrationTestCase(integration_util.IntegrationTestCase, RunsEnvironmentJobs):

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls.jobs_directory = tempfile.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = DOCKERIZED_JOB_CONFIG_FILE
        # Disable tool dependency resolution.
        config["tool_dependency_dir"] = "none"
        config["enable_beta_mulled_containers"] = "true"

    def setUp(self):
        super(DockerizedJobsIntegrationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()

    def test_explicit(self):
        self.dataset_populator.run_tool("mulled_example_explicit", {}, self.history_id)
        self.dataset_populator.wait_for_history(self.history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(self.history_id)
        assert "0.7.15-r1140" in output

    def test_mulled_simple(self):
        self.dataset_populator.run_tool("mulled_example_simple", {}, self.history_id)
        self.dataset_populator.wait_for_history(self.history_id, assert_ok=True)
        output = self.dataset_populator.get_history_dataset_content(self.history_id)
        assert "0.7.15-r1140" in output

    def test_docker_job_enviornment(self):
        job_env = self._run_and_get_environment_properties("job_environment_default")

        euid = os.geteuid()
        egid = os.getgid()

        assert job_env.user_id == str(euid), job_env.user_id
        assert job_env.group_id == str(egid), job_env.group_id
        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert job_env.home.startswith(self.jobs_directory)
        assert job_env.home.endswith("/home")

    def test_docker_job_environment_legacy(self):
        job_env = self._run_and_get_environment_properties("job_environment_default_legacy")

        euid = os.geteuid()
        egid = os.getgid()

        assert job_env.user_id == str(euid), job_env.user_id
        assert job_env.group_id == str(egid), job_env.group_id
        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        # Should we change env_pass_through to just always include TMP and HOME for docker?
        # I'm not sure, if yes this would change.
        assert job_env.home == "/", job_env.home
