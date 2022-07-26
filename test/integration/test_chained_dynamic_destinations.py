"""Integration tests for chained dynamic job destinations."""

import os
import tempfile

from galaxy_test.base.populators import skip_without_tool
from .test_job_environments import BaseJobEnvironmentIntegrationTestCase

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
CHAINED_DYNDESTS_JOB_CONFIG = os.path.join(SCRIPT_DIRECTORY, "chained_dyndest_job_conf.xml")


class ChainedDynamicDestinationIntegrationTestCase(BaseJobEnvironmentIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = tempfile.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = CHAINED_DYNDESTS_JOB_CONFIG

    @skip_without_tool("job_environment_default")
    def test_default_environment_1801(self):
        job_env = self._run_and_get_environment_properties()

        # Since dynamic destinations compute final tmp_dir parameter to be
        # $(mktemp from1and2and3XXXXXXXXXXXX), tmpdir should start
        # with from1and2and3.
        basename = os.path.basename(job_env.tmp)
        assert basename.startswith("from1and2and3"), job_env.tmp
