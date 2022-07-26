import os

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
MOCK_BIOTOOLS_CONTENT = os.path.join(SCRIPT_DIRECTORY, "mock_biotools_content")


class DynamicEdamLoadingIntegrationTestCase(integration_util.IntegrationTestCase):
    """Test mapping over tools with extended metadata enabled."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["biotools_content_directory"] = MOCK_BIOTOOLS_CONTENT
        config["biotools_use_api"] = False

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_edam_properties(self):
        result = self._get("tools/bibtex")
        result.raise_for_status()
        result_json = result.json()
        assert "edam_operations" in result_json
        assert "edam_topics" in result_json
        edam_operations = result_json["edam_operations"]
        edam_topics = result_json["edam_topics"]
        assert len(edam_operations) == 4
        assert "operation_3198" in edam_operations
        assert len(edam_topics) == 1
        assert "topic_0102" in edam_topics
