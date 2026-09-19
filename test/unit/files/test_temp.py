"""
Improved test for TempFilesSource using the decorator-based generic test suite.

This demonstrates the new approach that eliminates code duplication while
maintaining individual test execution and proper pytest reporting.
"""

from typing import Any

from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.sources import BaseFilesSource
from galaxy.files.sources.temp import TempFilesSource
from galaxy.files.unittest_utils import (
    setup_root,
    TestConfiguredFileSources,
)
from ._base import (
    BaseFileSourceTestSuite,
    generate_file_source_tests,
)

ROOT_URI = "temp://test1"
TEMP_PLUGIN = {
    "type": "temp",
    "id": "test1",
    "doc": "Test temporal file source",
    "writable": True,
}


@generate_file_source_tests
class TestTempFilesSource(BaseFileSourceTestSuite):
    """
    Test suite for TempFilesSource using the decorator-based generic test framework.

    The @generate_file_source_tests decorator automatically creates individual
    test functions for each test method in BaseFileSourceTestSuite.
    """

    @property
    def root_uri(self) -> str:
        return ROOT_URI

    @property
    def plugin_config(self) -> dict[str, Any]:
        return TEMP_PLUGIN

    def get_configured_file_sources(self) -> TestConfiguredFileSources:
        """Create and return configured file sources with test data."""
        tmp, root = setup_root()
        file_sources_config = FileSourcePluginsConfig()
        plugin = self.plugin_config.copy()
        plugin["root_path"] = root
        file_sources = TestConfiguredFileSources(
            file_sources_config, conf_dict={self.plugin_config["id"]: plugin}, test_root=root
        )

        # Populate with test data
        file_source = self.get_file_source_instance(file_sources)
        self.populate_test_scenario(file_source)

        return file_sources

    def get_file_source_instance(self, file_sources: TestConfiguredFileSources) -> BaseFilesSource:
        """Return the TempFilesSource instance."""
        file_source_pair = file_sources.get_file_source_path(self.root_uri)
        file_source = file_source_pair.file_source
        assert isinstance(file_source, TempFilesSource)
        return file_source
