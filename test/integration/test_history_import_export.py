from galaxy_test.api.test_histories import ImportExportTests
from galaxy_test.driver.integration_util import IntegrationTestCase


class ImportExportHistoryOutputsToWorkingDirTestCase(ImportExportTests, IntegrationTestCase):
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self._set_up_populators()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config['metadata_strategy'] = 'extended'
        config['outputs_to_working_directory'] = True
