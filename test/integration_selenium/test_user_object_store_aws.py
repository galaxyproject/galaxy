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


class TestUserObjectStoreAwsS3(BaseUserObjectStoreSeleniumIntegration):
    example_filename = "production_aws_s3.yml"

    @skip_unless_environ("GALAXY_TEST_AWS_ACCESS_KEY")
    @skip_unless_environ("GALAXY_TEST_AWS_SECRET_KEY")
    @skip_unless_environ("GALAXY_TEST_AWS_BUCKET")
    @managed_history
    @selenium_test
    def test_create_and_use(self):
        random_name = self._get_random_name(prefix="aws s3 object store")
        instance = ObjectStoreInstance(
            template_id="aws_s3",
            name=random_name,
            description="automated test for aws s3 object stores",
            parameters=[
                ConfigTemplateParameter("string", "access_key", os.environ["GALAXY_TEST_AWS_ACCESS_KEY"]),
                ConfigTemplateParameter("string", "secret_key", os.environ["GALAXY_TEST_AWS_SECRET_KEY"]),
                ConfigTemplateParameter("string", "bucket", os.environ["GALAXY_TEST_AWS_BUCKET"]),
            ],
        )
        object_store_id = self.create_object_store_template(instance)
        assert object_store_id
