from galaxy.selenium.navigates_galaxy import (
    ConfigTemplateParameter,
    FileSourceInstance,
)
from galaxy_test.selenium.upload_activity_helpers import UsesUploadActivity
from ._base_user_file_sources import BaseUserObjectStoreSeleniumIntegration
from .framework import (
    managed_history,
    selenium_test,
)


class TestObjectStoreSelectionSeleniumIntegration(BaseUserObjectStoreSeleniumIntegration, UsesUploadActivity):
    example_filename = "production_ftp.yml"

    @selenium_test
    @managed_history
    def test_create_and_use(self):
        random_name = self._get_random_name(prefix="scene ftp")
        instance = FileSourceInstance(
            template_id="ftp",
            name=random_name,
            description="Archive of computer art from demoscene subsculture",
            parameters=[
                ConfigTemplateParameter("string", "host", "ftp.scene.org"),
                ConfigTemplateParameter("string", "user", "ftp"),
                ConfigTemplateParameter("string", "password", "email@example.com"),
            ],
        )
        uri_root = self.create_file_source_template(instance)
        self.upload_context("paste-links").stage_paste_link(f"{uri_root}/welcome.msg").start()
        self.wait_for_history()
