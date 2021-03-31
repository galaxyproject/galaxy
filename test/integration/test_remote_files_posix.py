# Before running this test, start nginx+webdav in Docker using following command:
# docker run -v `pwd`/test/integration/webdav/data:/media  -e WEBDAV_USERNAME=alice -e WEBDAV_PASSWORD=secret1234 -p 7083:7083 jmchilton/webdavdev
# Apache Docker host (shown next) doesn't work because displayname not set in response.
# docker run -v `pwd`/test/integration/webdav:/var/lib/dav  -e AUTH_TYPE=Basic -e USERNAME=alice -e PASSWORD=secret1234  -e LOCATION=/ -p 7083:80 bytemark/webdav

import os
import shutil
from tempfile import mkdtemp

from galaxy_test.base import api_asserts
from galaxy_test.driver import integration_util

REQUIRED_ROLES = "user@bx.psu.edu"
REQUIRED_GROUPS = "fs_test_group"


def get_posix_file_source_config(root_dir: str, roles: str, groups: str) -> str:
    return f"""
- type: posix
  id: posix_test
  label: Posix
  doc: Files from local path
  root: {root_dir}
  writable: true
  requires_roles: {roles}
  requires_groups: {groups}

"""


def create_file_source_config_file_on(temp_dir, root_dir):
    file_contents = get_posix_file_source_config(root_dir, REQUIRED_ROLES, REQUIRED_GROUPS)
    file_path = os.path.join(temp_dir, "file_sources_conf_posix.yml")
    with open(file_path, "w") as f:
        f.write(file_contents)
    return file_path


class PosixFileSourceIntegrationTestCase(integration_util.IntegrationTestCase):

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        temp_dir = os.path.realpath(mkdtemp())
        cls._test_driver.temp_directories.append(temp_dir)
        cls.root_dir = os.path.join(temp_dir, "root")

        file_sources_config_file = create_file_source_config_file_on(temp_dir, cls.root_dir)
        config["file_sources_config_file"] = file_sources_config_file

        # Disable all stock plugins
        config["ftp_upload_dir"] = None
        config["library_import_dir"] = None
        config["user_library_import_dir"] = None

    def setUp(self):
        super().setUp()
        self._write_file_fixtures()

    def test_plugin_config(self):
        plugin_config_response = self.galaxy_interactor.get("remote_files/plugins")
        api_asserts.assert_status_code_is_ok(plugin_config_response)
        plugins = plugin_config_response.json()
        assert len(plugins) == 1
        assert plugins[0]["type"] == "posix"
        assert plugins[0]["uri_root"] == "gxfiles://posix_test"
        assert plugins[0]["writable"] is True
        assert plugins[0]["requires_roles"] == REQUIRED_ROLES
        assert plugins[0]["requires_groups"] == REQUIRED_GROUPS

    def test_admin_access(self):
        data = {"target": "gxfiles://posix_test"}
        list_response = self.galaxy_interactor.get("remote_files", data, admin=True)
        api_asserts.assert_status_code_is_ok(list_response)
        remote_files = list_response.json()
        print(remote_files)
        assert len(remote_files) == 2
        assert remote_files[0]["name"] == "a"
        assert remote_files[1]["name"] == "subdir1"

    def test_user_require_role(self):
        data = {"target": "gxfiles://posix_test"}

        list_response = self.galaxy_interactor.get("remote_files", data)
        api_asserts.assert_status_code_is_ok(list_response)
        remote_files = list_response.json()
        assert len(remote_files) > 0

        with self._different_user():
            list_response = self.galaxy_interactor.get("remote_files", data)
            api_asserts.assert_status_code_is(list_response, 403)

            list_response = self.galaxy_interactor.get("remote_files", data, admin=True)
            api_asserts.assert_status_code_is_ok(list_response)
            remote_files = list_response.json()
            assert len(remote_files) > 0

    def test_user_require_group(self):
        data = {"target": "gxfiles://posix_test"}
        list_response = self.galaxy_interactor.get("remote_files", data)
        api_asserts.assert_status_code_is(list_response, 403)

        with self._different_user():
            list_response = self.galaxy_interactor.get("remote_files", data)
            api_asserts.assert_status_code_is(list_response, 403)

    def _write_file_fixtures(self):
        root = PosixFileSourceIntegrationTestCase.root_dir
        if os.path.exists(root):
            shutil.rmtree(root)
        os.mkdir(root)

        with open(os.path.join(root, "a"), "w") as f:
            f.write("a\n")

        subdir1 = os.path.join(root, "subdir1")
        os.mkdir(subdir1)
        with open(os.path.join(subdir1, "b"), "w") as f:
            f.write("b\n")

        return root
