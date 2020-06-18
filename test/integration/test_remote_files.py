import operator
import os
from tempfile import mkdtemp

from galaxy.exceptions import error_codes
from galaxy_test.base.api_asserts import assert_error_code_is, assert_error_message_contains
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_JOB_CONF = os.path.join(SCRIPT_DIRECTORY, "file_sources_conf.yml")

USERNAME = 'user--bx--psu--edu'
USER_EMAIL = 'user@bx.psu.edu'


class RemoteFilesIntegrationTestCase(integration_util.IntegrationTestCase):

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        root = os.path.realpath(mkdtemp())
        cls._test_driver.temp_directories.append(root)
        cls.root = root
        cls.library_dir = os.path.join(root, "library")
        cls.user_library_dir = os.path.join(root, "user_library")
        cls.ftp_upload_dir = os.path.join(root, "ftp")
        config["library_import_dir"] = cls.library_dir
        config["user_library_import_dir"] = cls.user_library_dir
        config["ftp_upload_dir"] = cls.ftp_upload_dir
        config["ftp_upload_site"] = "ftp://cow.com"

        for d in [cls.library_dir, cls.user_library_dir, cls.ftp_upload_dir]:
            os.mkdir(d)

    def test_index(self):
        index = self.galaxy_interactor.get("remote_files?target=importdir").json()
        self._assert_index_empty(index)

        _write_file_fixtures(self.root, self.library_dir)
        index = self.galaxy_interactor.get("remote_files?target=importdir").json()
        self._assert_index_matches_fixtures(index)

        # Get a 404 if the directory doesn't exist.
        index = self.galaxy_interactor.get("remote_files?target=userdir").json()
        assert_error_code_is(index, error_codes.USER_OBJECT_NOT_FOUND)

        users_dir = os.path.join(self.user_library_dir, USER_EMAIL)
        os.mkdir(users_dir)

        index = self.galaxy_interactor.get("remote_files?target=userdir").json()
        self._assert_index_empty(index)

        _write_file_fixtures(self.root, users_dir)

        index = self.galaxy_interactor.get("remote_files?target=userdir").json()
        self._assert_index_matches_fixtures(index)

        index = self.galaxy_interactor.get("remote_files?target=userdir&format=jstree").json()
        self._assert_index_matches_fixtures_jstree(index)

    def _assert_index_empty(self, index):
        assert len(index) == 0

    def _assert_index_matches_fixtures(self, index):
        paths = map(operator.itemgetter("path"), index)
        assert "a" in paths
        assert "subdir1/c" in paths

    def _assert_index_matches_fixtures_jstree(self, index):
        a_file = index[0]
        assert a_file["li_attr"]["full_path"] == "a"
        subdir1 = index[1]
        assert subdir1["type"] == "folder"
        assert subdir1["state"]["disabled"]
        assert subdir1["li_attr"]["full_path"] == "subdir1"
        subdir1_children = subdir1["children"]
        assert len(subdir1_children) == 2
        c = subdir1_children[0]
        assert c["li_attr"]["full_path"] == "subdir1/c"


class RemoteFilesNotConfiguredIntegrationTestCase(integration_util.IntegrationTestCase):

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["library_import_dir"] = None
        config["user_library_import_dir"] = None
        config["ftp_upload_dir"] = None

    def test_configuration_statuses(self):
        importfiles = self.galaxy_interactor.get("remote_files?target=importdir")
        assert_error_code_is(importfiles, error_codes.CONFIG_DOES_NOT_ALLOW)
        assert_error_message_contains(importfiles, 'import directory')

        importfiles = self.galaxy_interactor.get("remote_files?target=ftpdir")
        assert_error_code_is(importfiles, error_codes.CONFIG_DOES_NOT_ALLOW)
        assert_error_message_contains(importfiles, 'FTP directories')

        importfiles = self.galaxy_interactor.get("remote_files?target=userdir")
        assert_error_code_is(importfiles, error_codes.CONFIG_DOES_NOT_ALLOW)
        assert_error_message_contains(importfiles, 'user directories')

        # invalid request parameter waitwhat...
        importfiles = self.galaxy_interactor.get("remote_files?target=waitwhat")
        assert_error_code_is(importfiles, error_codes.USER_REQUEST_INVALID_PARAMETER)


def _write_file_fixtures(tmp, root):
    if not os.path.exists(root):
        os.mkdir(root)
    os.symlink(os.path.join(tmp, "b"), os.path.join(root, "unsafe"))
    with open(os.path.join(root, "a"), "w") as f:
        f.write("a\n")
    with open(os.path.join(tmp, "b"), "w") as f:
        f.write("b\n")

    subdir1 = os.path.join(root, "subdir1")
    os.mkdir(subdir1)
    with open(os.path.join(subdir1, "c"), "w") as f:
        f.write("c\n")

    subdir2 = os.path.join(subdir1, "subdir2")
    os.mkdir(subdir2)
    with open(os.path.join(subdir2, "d"), "w") as f:
        f.write("d\n")

    return tmp, root
