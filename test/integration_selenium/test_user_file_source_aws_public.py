from galaxy.selenium.navigates_galaxy import (
    ConfigTemplateParameter,
    FileSourceInstance,
)
from ._base_user_file_sources import BaseUserObjectStoreSeleniumIntegration
from .framework import (
    managed_history,
    selenium_test,
)


class TestUserFileSourceAwsPublicSeleniumIntegration(BaseUserObjectStoreSeleniumIntegration):
    example_filename = "production_aws_public_bucket.yml"

    @managed_history
    @selenium_test
    def test_create_and_use(self):
        random_name = self._get_random_name(prefix="Encyclopedia of DNA Elements ENCODE")
        instance = FileSourceInstance(
            template_id="aws_public",
            name=random_name,
            description="The Encyclopedia of DNA Elements (ENCODE) Consortium is an international collaboration of research groups funded by the National Human Genome Research Institute (NHGRI)",
            parameters=[
                ConfigTemplateParameter("string", "bucket", "encode-public"),
            ],
        )
        uri_root = self.create_file_source_template(instance)
        self.upload_uri(f"{uri_root}/robots.txt", wait=True)
