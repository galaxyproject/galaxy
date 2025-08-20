"""
Improved test for MemoryFilesSource using the decorator-based generic test suite.

This demonstrates the new approach that eliminates code duplication while
maintaining individual test execution and proper pytest reporting.
"""

from typing import Any

from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.sources import BaseFilesSource
from galaxy.files.sources.memory import MemoryFilesSource
from galaxy.files.unittest_utils import TestConfiguredFileSources
from ._base import (
    BaseFileSourceTestSuite,
    generate_file_source_tests,
)

ROOT_URI = "memory://test1"
MEMORY_PLUGIN = {
    "type": "memory",
    "id": "test1",
    "doc": "Test memory file source",
    "writable": True,
}


@generate_file_source_tests
class TestMemoryFilesSource(BaseFileSourceTestSuite):
    """
    Test suite for MemoryFilesSource using the decorator-based generic test framework.

    The @generate_file_source_tests decorator automatically creates individual
    test functions for each test method in BaseFileSourceTestSuite.
    """

    @property
    def root_uri(self) -> str:
        return ROOT_URI

    @property
    def plugin_config(self) -> dict[str, Any]:
        return MEMORY_PLUGIN

    def get_configured_file_sources(self) -> TestConfiguredFileSources:
        """Create and return configured file sources with test data."""
        file_sources_config = FileSourcePluginsConfig()
        plugin = self.plugin_config.copy()
        file_sources = TestConfiguredFileSources(
            file_sources_config, conf_dict={self.plugin_config["id"]: plugin}, test_root=None
        )

        # Populate with test data
        file_source = self.get_file_source_instance(file_sources)
        self.populate_test_scenario(file_source)

        return file_sources

    def get_file_source_instance(self, file_sources: TestConfiguredFileSources) -> BaseFilesSource:
        """Return the MemoryFilesSource instance."""
        file_source_pair = file_sources.get_file_source_path(self.root_uri)
        file_source = file_source_pair.file_source
        assert isinstance(file_source, MemoryFilesSource)
        return file_source
