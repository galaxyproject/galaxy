"""
Test classes that should be shared between test scenarios.
"""

import os
import shutil
from tempfile import mkdtemp
from typing import ClassVar

from galaxy_test.driver.driver_util import GalaxyTestDriver

REQUIRED_ROLE_EXPRESSION = "user@bx.psu.edu"
GROUP_A = "fs_test_group"
GROUP_B = "group name with spaces"
REQUIRED_GROUP_EXPRESSION = f"{GROUP_A} or '{GROUP_B}'"


def get_posix_file_source_config(
    root_dir: str, roles: str, groups: str, include_test_data_dir: bool, prefer_links: bool = False
) -> str:
    rval = f"""
- type: posix
  id: posix_test
  label: Posix
  doc: Files from local path
  root: {root_dir}
  writable: true
  requires_roles: {roles}
  requires_groups: {groups}
"""
    if prefer_links:
        rval += f"""
- type: posix
  id: linking_source
  label: Posix
  doc: Files from local path to links
  root: {root_dir}
  writable: true
  prefer_links: true
"""

    if include_test_data_dir:
        rval += """
- type: posix
  id: testdatafiles
  label: Galaxy Stock Test Data
  doc: Galaxy's test-data directory.
  root: test-data
  writable: false
"""
    return rval


def create_file_source_config_file_on(
    temp_dir: str,
    root_dir: str,
    include_test_data_dir: bool,
    required_role_expression: str,
    required_group_expression: str,
    prefer_links: bool = False,
):
    file_contents = get_posix_file_source_config(
        root_dir, required_role_expression, required_group_expression, include_test_data_dir, prefer_links=prefer_links
    )
    file_path = os.path.join(temp_dir, "file_sources_conf_posix.yml")
    with open(file_path, "w") as f:
        f.write(file_contents)
    return file_path


class PosixFileSourceSetup:
    _test_driver: GalaxyTestDriver
    root_dir: str
    include_test_data_dir: ClassVar[bool] = False
    # Require role for access but do not require groups by default on every test to simplify them
    required_role_expression: str = REQUIRED_ROLE_EXPRESSION
    required_group_expression: str = ""
    prefer_links: bool = False

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        temp_dir = os.path.realpath(mkdtemp())
        cls._test_driver.temp_directories.append(temp_dir)
        cls.root_dir = os.path.join(temp_dir, "root")

        file_sources_config_file = create_file_source_config_file_on(
            temp_dir,
            cls.root_dir,
            cls.include_test_data_dir,
            cls.required_role_expression,
            cls.required_group_expression,
            prefer_links=cls.prefer_links,
        )
        config["file_sources_config_file"] = file_sources_config_file

        # Disable all stock plugins
        config["ftp_upload_dir"] = None
        config["library_import_dir"] = None
        config["user_library_import_dir"] = None

    def _write_file_fixtures(self):
        root = self.root_dir
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
