from galaxy_test.api.test_histories import ImportExportHistoryTestCase
from galaxy_test.driver.integration_util import IntegrationTestCase


class ImportExportHistoryOutputsToWorkingDirTestCase(ImportExportHistoryTestCase, IntegrationTestCase):

    framework_tool_and_types = True

    def setUp(self):
        super(ImportExportHistoryOutputsToWorkingDirTestCase, self).setUp()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config['outputs_to_working_directory'] = True
