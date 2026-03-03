import os
import shutil
import tempfile

from galaxy.selenium.navigates_galaxy import (
    ConfigTemplateParameter,
    FileSourceInstance,
)
from ._base_user_file_sources import BaseUserObjectStoreSeleniumIntegration
from ._sftp_server import SFTPServerMixin
from .framework import (
    managed_history,
    selenium_test,
)


class TestObjectStoreSelectionSeleniumIntegration(BaseUserObjectStoreSeleniumIntegration, SFTPServerMixin):
    """Selenium tests for the SSH user file source template.

    A single in-process SFTP server is started for the whole class and torn
    down afterwards.  The server's host/port/credentials are passed as
    template parameters when creating the file source instance in the Galaxy UI.
    """

    example_filename = "ssh.yml"
    _sftp_root: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)

        # Create the SFTP server root and pre-seed it with a file to upload.
        cls._sftp_root = tempfile.mkdtemp(prefix="galaxy_test_sftp_")
        with open(os.path.join(cls._sftp_root, "test_file.txt"), "w") as fh:
            fh.write("Hello from SSH file source test\n")

        cls.start_sftp_server(cls._sftp_root)

    @classmethod
    def tearDownClass(cls):
        cls.stop_sftp_server()
        if hasattr(cls, "_sftp_root"):
            shutil.rmtree(cls._sftp_root, ignore_errors=True)
        super().tearDownClass()

    @selenium_test
    @managed_history
    def test_create_and_use(self):
        random_name = self._get_random_name(prefix="ssh test")
        instance = FileSourceInstance(
            template_id="ssh",
            name=random_name,
            description="SSH file source backed by a local in-process SFTP server",
            parameters=[
                ConfigTemplateParameter("string", "host", "127.0.0.1"),
                ConfigTemplateParameter("integer", "port", self._sftp_server.port),
                ConfigTemplateParameter("string", "user", self._sftp_server.username),
                ConfigTemplateParameter("string", "path", "/"),
                ConfigTemplateParameter("string", "password", self._sftp_server.password),
            ],
        )
        uri_root = self.create_file_source_template(instance)
        self.upload_uri(f"{uri_root}/test_file.txt", wait=True)
