import tempfile
from contextlib import ExitStack

from galaxy.files.unittest_utils.ftp_server import serve_ftp_directory
from galaxy.selenium.navigates_galaxy import (
    ConfigTemplateParameter,
    FileSourceInstance,
)
from ._base_user_file_sources import BaseUserObjectStoreSeleniumIntegration
from .framework import (
    managed_history,
    selenium_test,
)


class TestObjectStoreSelectionSeleniumIntegration(BaseUserObjectStoreSeleniumIntegration):
    example_filename = "production_ftp.yml"
    ftp_server: ExitStack
    ftp_host: str
    ftp_port: int

    @classmethod
    def setUpClass(cls):
        cls.ftp_server = ExitStack()
        root = cls.ftp_server.enter_context(tempfile.TemporaryDirectory())
        with open(f"{root}/welcome.msg", "w") as f:
            f.write("Welcome to the test FTP server.\n")
        cls.ftp_host, cls.ftp_port = cls.ftp_server.enter_context(serve_ftp_directory(root))
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.ftp_server.close()

    @selenium_test
    @managed_history
    def test_create_and_use(self):
        random_name = self._get_random_name(prefix="local ftp")
        instance = FileSourceInstance(
            template_id="ftp",
            name=random_name,
            description="Local FTP server started by the test",
            parameters=[
                ConfigTemplateParameter("string", "host", self.ftp_host),
                ConfigTemplateParameter("integer", "port", self.ftp_port),
                ConfigTemplateParameter("string", "user", "anonymous"),
                ConfigTemplateParameter("string", "password", "email@example.com"),
            ],
        )
        uri_root = self.create_file_source_template(instance)
        self.upload_uri(f"{uri_root}/welcome.msg", wait=True)
