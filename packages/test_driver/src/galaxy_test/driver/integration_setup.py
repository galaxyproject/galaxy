"""
Test classes that should be shared between test scenarios.
"""

import os
import shutil
from time import (
    monotonic,
    sleep,
)
from typing import ClassVar
from unittest.mock import (
    MagicMock,
    patch,
)

from galaxy.app import UniverseApplication
from galaxy.model import StoredWorkflow
from galaxy.model.item_attrs import add_item_annotation
from galaxy.workflow import (
    curated,
    iwc_manifest,
)
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
        temp_dir = os.path.realpath(cls._test_driver.mkdtemp())
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


class CuratedWorkflowsNetworkGuard:
    """Keeps curated workflow tests offline.

    The feature's one outbound request is the IWC manifest download. Both it and
    the refresh that would trigger it are replaced with functions that raise, and
    every test asserts the download was never attempted.
    """

    download_mock: MagicMock
    refresh_mock: MagicMock

    def setUp(self):
        super().setUp()  # type: ignore[misc]
        curated.clear_caches()

        self._download_patch = patch.object(
            iwc_manifest,
            "download_manifest",
            side_effect=AssertionError("curated workflow tests must never contact iwc.galaxyproject.org"),
        )
        self.download_mock = self._download_patch.start()

        self._refresh_patch = patch.object(
            curated,
            "refresh_projection",
            side_effect=RuntimeError("curated catalog refresh is disabled in tests"),
        )
        self.refresh_mock = self._refresh_patch.start()

    def tearDown(self):
        try:
            # Drain any background refresh thread before the patches come off --
            # a thread that outlived the test would otherwise reach the real
            # fetcher. The network assertion runs last, once every thread the
            # test could have started is known to have finished.
            self._wait_for_refresh_to_settle()
            self._refresh_patch.stop()
            self._download_patch.stop()
            self._assert_no_network_access()
        finally:
            super().tearDown()  # type: ignore[misc]

    def _assert_no_network_access(self) -> None:
        self.download_mock.assert_not_called()

    @staticmethod
    def _wait_for_refresh_to_settle(timeout: float = 30.0) -> None:
        # Reads private module state on purpose: the flag flips to False only
        # after the background thread has finished with ``refresh_projection``,
        # which is precisely the condition that makes unpatching safe.
        deadline = monotonic() + timeout
        while curated._refresh_in_flight and monotonic() < deadline:
            sleep(0.05)


def store_raw_annotation(app: UniverseApplication, workflow_id: str, annotation: str) -> None:
    """Annotate a stored workflow straight in the database.

    Bypasses the API write path on purpose, so a test can store exactly the
    text it means to - including text a write would sanitize.
    """
    sa_session = app.model.session
    stored_workflow = sa_session.get(StoredWorkflow, app.security.decode_id(workflow_id))
    assert stored_workflow is not None
    add_item_annotation(sa_session, stored_workflow.user, stored_workflow, annotation)
    sa_session.commit()
