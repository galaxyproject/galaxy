import os

from galaxy.selenium.navigates_galaxy import (
    ConfigTemplateParameter,
    FileSourceInstance,
)
from galaxy.util.unittest_utils import skip_unless_environ
from ._base_user_file_sources import BaseUserObjectStoreSeleniumIntegration
from .framework import (
    managed_history,
    selenium_test,
)


class TestObjectStoreSelectionSeleniumIntegration(BaseUserObjectStoreSeleniumIntegration):

    @skip_unless_environ("GALAXY_TEST_AZURE_CONTAINER_NAME")
    @skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_KEY")
    @skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_NAME")
    @managed_history
    @selenium_test
    def test_create_and_use(self):
        history_id = self.current_history_id()
        self.navigate_to_user_preferences()
        random_name = self._get_random_name(prefix="azure source")
        instance = FileSourceInstance(
            template_id="azure",
            name=random_name,
            description="automated test for azure file source",
            parameters=[
                ConfigTemplateParameter("string", "container_name", os.environ["GALAXY_TEST_AZURE_CONTAINER_NAME"]),
                ConfigTemplateParameter("string", "account_name", os.environ["GALAXY_TEST_AZURE_ACCOUNT_NAME"]),
                ConfigTemplateParameter("string", "account_key", os.environ["GALAXY_TEST_AZURE_ACCOUNT_KEY"]),
            ],
        )
        uri_root = self.create_file_source_template(instance)
        published_uri = self.dataset_populator.export_dataset_to_remote_file(
            history_id,
            "my file contents",
            "my_cool_file",
            uri_root,
        )
        self.upload_uri(published_uri, wait=True)
