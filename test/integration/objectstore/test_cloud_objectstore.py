import hashlib

from galaxy_test.driver import integration_util
from ._base import BaseCloudObjectStoreIntegrationTestCase

TEST_TOOL_IDS = [
    "multi_output",
    "multi_output_configured",
    "composite_output",
    "metadata",
    "output_format",
]


class TestCloudObjectStoreIntegration(BaseCloudObjectStoreIntegrationTestCase):
    def test_big_dataset_roundtrip(self):
        # 12 MiB crosses the configured 5 MiB multipart threshold, so this
        # dataset uploads to MinIO through cloudbridge's multipart path.
        with self.dataset_populator.test_history() as history_id:
            content = ("x" * 1023 + "\n") * (12 * 1024)
            hda = self.dataset_populator.new_dataset(history_id, content=content, wait=True)
            fetched = self.dataset_populator.get_history_dataset_content(history_id, dataset=hda)
            assert hashlib.sha256(fetched.encode()).hexdigest() == hashlib.sha256(content.encode()).hexdigest()


instance = integration_util.integration_module_instance(TestCloudObjectStoreIntegration)
test_tools = integration_util.integration_tool_runner(TEST_TOOL_IDS)
