"""Integration tests for the Pulsar embedded runner."""

import collections
import os
import tempfile

from base import integration_util

from base.populators import (
    DatasetPopulator,
    skip_without_tool,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
SIMPLE_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "simple_job_conf.xml")


JobEnviromentProperties = collections.namedtuple("JobEnvironmentProperties", [
    "user_id",
    "group_id",
    "pwd",
    "home",
    "tmp",
])


class RunsEnvironmentJobs:

    def _run_and_get_environment_properties(self, tool_id="job_environment_default"):
        with self.dataset_populator.test_history() as history_id:
            self.dataset_populator.run_tool(tool_id, {}, history_id)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            return self._environment_properties(history_id)

    def _environment_properties(self, history_id):
        user_id = self.dataset_populator.get_history_dataset_content(history_id, hid=1).strip()
        group_id = self.dataset_populator.get_history_dataset_content(history_id, hid=2).strip()
        pwd = self.dataset_populator.get_history_dataset_content(history_id, hid=3).strip()
        home = self.dataset_populator.get_history_dataset_content(history_id, hid=4).strip()
        tmp = self.dataset_populator.get_history_dataset_content(history_id, hid=5).strip()

        return JobEnviromentProperties(user_id, group_id, pwd, home, tmp)


class BaseJobEnvironmentIntegrationTestCase(integration_util.IntegrationTestCase, RunsEnvironmentJobs):

    framework_tool_and_types = True

    def setUp(self):
        super(BaseJobEnvironmentIntegrationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)


class DefaultJobEnvironmentIntegrationTestCase(BaseJobEnvironmentIntegrationTestCase):

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls.jobs_directory = tempfile.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = SIMPLE_JOB_CONFIG_FILE  # Ensure no Docker for these tests

    @skip_without_tool("job_environment_default")
    def test_default_environment_1801(self):
        job_env = self._run_and_get_environment_properties()

        euid = os.geteuid()
        egid = os.getgid()

        assert job_env.user_id == str(euid), job_env.user_id
        assert job_env.group_id == str(egid), job_env.group_id
        assert job_env.pwd.startswith(self.jobs_directory)
        assert job_env.pwd.endswith("/working")
        assert job_env.home == job_env.pwd, job_env.home

    @skip_without_tool("job_environment_default_legacy")
    def test_default_environment_legacy(self):
        job_env = self._run_and_get_environment_properties("job_environment_default_legacy")

        euid = os.geteuid()
        egid = os.getgid()
        home = os.getenv("HOME")

        assert job_env.user_id == str(euid), job_env.user_id
        assert job_env.group_id == str(egid), job_env.group_id
        assert job_env.home == home, job_env.home

    @skip_without_tool("job_environment_force_legacy_home")
    def test_default_environment_force_legacy_home(self):
        # Home should not overridden because we haven't set legacy_home_dir in job_conf
        # or app, so it should just HOME.
        job_env = self._run_and_get_environment_properties("job_environment_force_legacy_home")
        home = os.getenv("HOME")
        assert job_env.home == home, job_env.home


class LegacyHomeJobEnvironmentIntegrationTestCase(BaseJobEnvironmentIntegrationTestCase):

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls.jobs_directory = tempfile.mkdtemp()
        cls.legacy_home_directory = tempfile.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = SIMPLE_JOB_CONFIG_FILE  # Ensure no Docker for these tests
        config["legacy_home_dir"] = cls.legacy_home_directory

    @skip_without_tool("job_environment_default")
    def test_default_environment(self):
        # Test legacy_home_dir ignored for newer tools by default
        job_env = self._run_and_get_environment_properties()
        assert job_env.home == job_env.pwd, job_env.home

    @skip_without_tool("job_environment_default_legacy")
    def test_default_environment_legacy(self):
        # legacy_home_dir used by default for older tools
        job_env = self._run_and_get_environment_properties("job_environment_default_legacy")
        assert job_env.home == self.legacy_home_directory, job_env.home

    @skip_without_tool("job_environment_force_legacy_home")
    def test_default_environment_force_legacy_home(self):
        # legacy_home_dir used for newer tools if forced in tool XML
        job_env = self._run_and_get_environment_properties("job_environment_force_legacy_home")
        assert job_env.home == self.legacy_home_directory, job_env.home
