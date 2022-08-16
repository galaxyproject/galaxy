"""Integration tests for the TES runner."""
import collections
import os
import tempfile

from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_without_tool,
)
from galaxy_test.driver import integration_util
from .test_job_environments import BaseJobEnvironmentIntegrationTestCase

Config = collections.namedtuple('Config', 'path')
TOOL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'tools'))


def job_config():
    job_conf_template = ("""<job_conf>
    <plugins>
        <plugin id="tes" type="runner" load="galaxy.jobs.runners.tes:TESJobRunner">
        </plugin>
    </plugins>
    <destinations default="tes_destination">
        <destination id="tes_destination" runner="tes">
            <param id="tes_master_addr">https://vipulchhabra99-galaxy-j4pv7gx9cqp6v-9080.githubpreview.dev</param>
            <param id="docker_enabled">true</param>
            <env id="SOME_ENV_VAR">42</env>
        </destination>
    </destinations>
</job_conf>
""")

    with tempfile.NamedTemporaryFile(suffix="_tes_integration_job_conf.xml", mode="w", delete=False) as job_conf:
        job_conf.write(job_conf_template)
    return Config(job_conf.name)


@integration_util.skip_unless_tes()
class BaseTESIntegrationTestCase(BaseJobEnvironmentIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()

    @classmethod
    def setUpClass(cls):
        cls.jobs_directory = os.path.realpath(tempfile.mkdtemp())
        cls.job_config = job_config()
        super().setUpClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["jobs_directory"] = cls.jobs_directory
        config["file_path"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config.path
        config["default_job_shell"] = '/bin/sh'
        config["galaxy_infrastructure_url"] = "http://localhost:$GALAXY_WEB_PORT"

    @skip_without_tool('job_properties')
    def test_error_job(self):
        inputs = {
            'failbool': True
        }
        running_response = self.dataset_populator.run_tool(
            "job_properties",
            inputs,
            self.history_id,
            assert_ok=False,
        )
        result = self.dataset_populator.wait_for_tool_run(run_response=running_response, history_id=self.history_id, assert_ok=False).json()
        details = self.dataset_populator.get_job_details(result['jobs'][0]['id'], full=True).json()

        assert details['exit_code'] == 1
        assert details['stdout'] == 'The bool is not true\n\n'
        assert 'The bool is very not true\n' in details['stderr']

    @skip_without_tool('create_2')
    def test_walltime_limit(self):
        running_response = self.dataset_populator.run_tool(
            'create_2',
            {'sleep_time': 60},
            self.history_id,
            assert_ok=False
        )
        result = self.dataset_populator.wait_for_tool_run(run_response=running_response,
                                                          history_id=self.history_id,
                                                          assert_ok=False).json()
        details = self.dataset_populator.get_job_details(result['jobs'][0]['id'], full=True).json()
        assert details['state'] == 'error'
        hda_details = self.dataset_populator.get_history_dataset_details(self.history_id, assert_ok=False)
        assert hda_details['misc_info'] == 'Unable to reach the defined URL from TES Container'
