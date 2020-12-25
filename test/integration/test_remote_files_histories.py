"""Test history import/export from galaxy.files plugins."""
import os

from .test_remote_files import ConfiguresRemoteFilesIntegrationTestCase


class RemoteFilesHistoryImportExportIntegrationTestCase(ConfiguresRemoteFilesIntegrationTestCase):

    framework_tool_and_types = True

    def test_history_import_from_library_dir(self):
        f = open(self.test_data_resolver.get_filename("exports/1901_two_datasets.tgz"), 'rb')
        import_path = os.path.join(self.library_dir, "to_import.tgz")
        with open(import_path, 'wb') as out:
            out.write(f.read())
        import_uri = "gximport://to_import.tgz"
        import_data = dict(archive_source=import_uri, archive_type="url")
        imported_history_id = self.dataset_populator.import_history_and_wait_for_name(import_data, "API Test History")
        self.dataset_populator.wait_on_history_length(imported_history_id, 2)
        self.dataset_populator.delete_history(imported_history_id)

    def test_history_import_from_ftp_dir(self):
        f = open(self.test_data_resolver.get_filename("exports/1901_two_datasets.tgz"), 'rb')
        import_path = os.path.join(self.user_ftp_dir, "to_import.tgz")
        with open(import_path, 'wb') as out:
            out.write(f.read())
        import_uri = "gxftp://to_import.tgz"
        # Consider distinguishing between url and uri...
        import_data = dict(archive_source=import_uri, archive_type="url")
        imported_history_id = self.dataset_populator.import_history_and_wait_for_name(import_data, "API Test History")
        self.dataset_populator.wait_on_history_length(imported_history_id, 2)
        self.dataset_populator.delete_history(imported_history_id)
