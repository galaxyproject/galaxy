import os

from galaxy.selenium.navigates_galaxy import (
    ConfigTemplateParameter,
    ObjectStoreInstance,
)
from galaxy.util.unittest_utils import skip_unless_environ
from ._base_user_object_stores import BaseUserObjectStoreSeleniumIntegration
from .framework import (
    managed_history,
    selenium_test,
)


class TestUserObjectStoreAzureBlob(BaseUserObjectStoreSeleniumIntegration):
    example_filename = "production_azure_blob.yml"

    @skip_unless_environ("GALAXY_TEST_AZURE_CONTAINER_NAME")
    @skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_KEY")
    @skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_NAME")
    @managed_history
    @selenium_test
    def test_create_and_use(self):
        random_name = self._get_random_name(prefix="azure object store")
        instance = ObjectStoreInstance(
            template_id="azure",
            name=random_name,
            description="automated test for azure object store",
            parameters=[
                ConfigTemplateParameter("string", "container_name", os.environ["GALAXY_TEST_AZURE_CONTAINER_NAME"]),
                ConfigTemplateParameter("string", "account_name", os.environ["GALAXY_TEST_AZURE_ACCOUNT_NAME"]),
                ConfigTemplateParameter("string", "account_key", os.environ["GALAXY_TEST_AZURE_ACCOUNT_KEY"]),
            ],
        )
        object_store_id = self.create_object_store_template(instance)
        assert object_store_id
