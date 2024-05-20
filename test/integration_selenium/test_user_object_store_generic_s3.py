from galaxy.selenium.navigates_galaxy import (
    ConfigTemplateParameter,
    ObjectStoreInstance,
)
from ._base_user_object_stores import BaseUserObjectStoreSeleniumIntegration
from .framework import (
    managed_history,
    selenium_test,
)
from .test_user_object_store_generic_s3_legacy import (
    GALAXY_TEST_PLAY_MINIO_BUCKET,
    GALAXY_TEST_PLAY_MINIO_KEY,
    GALAXY_TEST_PLAY_MINIO_SECRET,
    PLAY_HOST,
    PLAY_PORT,
)

PLAY_ENDPOINT_URL = f"https://{PLAY_HOST}:{PLAY_PORT}/"


class TestUserObjectStoreGenericS3(BaseUserObjectStoreSeleniumIntegration):
    example_filename = "production_generic_s3.yml"

    @managed_history
    @selenium_test
    def test_create_and_use(self):
        random_name = self._get_random_name(prefix="generic s3 object store using play.min.io")
        instance = ObjectStoreInstance(
            template_id="generic_s3",
            name=random_name,
            description="automated test for legacy generic s3 object store against play.min.io",
            parameters=[
                ConfigTemplateParameter("string", "access_key", GALAXY_TEST_PLAY_MINIO_KEY),
                ConfigTemplateParameter("string", "secret_key", GALAXY_TEST_PLAY_MINIO_SECRET),
                ConfigTemplateParameter("string", "bucket", GALAXY_TEST_PLAY_MINIO_BUCKET),
                ConfigTemplateParameter("string", "endpoint_url", PLAY_ENDPOINT_URL),
            ],
        )
        object_store_id = self.create_object_store_template(instance)
        assert object_store_id
