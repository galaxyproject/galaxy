from galaxy.selenium.navigates_galaxy import (
    ConfigTemplateParameter,
    ObjectStoreInstance,
)
from ._base_user_object_stores import BaseUserObjectStoreSeleniumIntegration
from .framework import (
    managed_history,
    selenium_test,
)

PLAY_HOST = "play.min.io"
PLAY_PORT = "9000"
GALAXY_TEST_PLAY_MINIO_KEY = "LEHFJDNqSA4xcJmmezU7"
GALAXY_TEST_PLAY_MINIO_SECRET = "E3ycZrp2nV8WscER8HqgsPPL2aFc2uuTbRchelcX"
GALAXY_TEST_PLAY_MINIO_BUCKET = "gxtest1"


class TestUserObjectStoreGenericS3Legacy(BaseUserObjectStoreSeleniumIntegration):
    example_filename = "production_generic_s3_legacy.yml"

    @managed_history
    @selenium_test
    def test_create_and_use(self):
        random_name = self._get_random_name(prefix="generic s3 object store using play.min.io")
        instance = ObjectStoreInstance(
            template_id="generic_s3_legacy",
            name=random_name,
            description="automated test for legacy generic s3 object store against play.min.io",
            parameters=[
                ConfigTemplateParameter("string", "access_key", GALAXY_TEST_PLAY_MINIO_KEY),
                ConfigTemplateParameter("string", "secret_key", GALAXY_TEST_PLAY_MINIO_SECRET),
                ConfigTemplateParameter("string", "bucket", GALAXY_TEST_PLAY_MINIO_BUCKET),
                ConfigTemplateParameter("string", "host", PLAY_HOST),
                ConfigTemplateParameter("integer", "port", PLAY_PORT),
            ],
        )
        object_store_id = self.create_object_store_template(instance)
        assert object_store_id
