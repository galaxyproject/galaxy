"""
Generic test suite for BaseFilesSource implementations.

This module provides a reusable test suite that can validate the basic behavior of any
BaseFilesSource implementation. It includes tests for basic file operations,
directory listing, pagination, search, and error handling.

The test suite uses a decorator-based approach to automatically generate individual
test functions, eliminating code duplication while maintaining pytest compatibility.
"""

import tempfile
from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Any,
    Callable,
    Optional,
)

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.files.models import (
    AnyRemoteEntry,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.files.sources import BaseFilesSource
from galaxy.files.unittest_utils import TestConfiguredFileSources
from ._util import (
    assert_realizes_contains,
    user_context_fixture,
)


def generate_file_source_tests(test_suite_class: type["BaseFileSourceTestSuite"]) -> type:
    """
    Class decorator that automatically generates individual test functions for each test method
    in the BaseFileSourceTestSuite.

    Usage:
        @generate_file_source_tests
        class TestMyFileSource(BaseFileSourceTestSuite):
            # Only implement abstract methods
            pass
    """
    # Get all test methods from the base class
    test_methods = [
        method_name
        for method_name in dir(BaseFileSourceTestSuite)
        if method_name.startswith("test_") and callable(getattr(BaseFileSourceTestSuite, method_name))
    ]

    # Generate wrapper functions for each test method
    for method_name in test_methods:
        test_method = getattr(BaseFileSourceTestSuite, method_name)

        def create_test_wrapper(method: Callable) -> Callable:
            def test_wrapper(self) -> None:
                """Generated test wrapper function."""
                method(self)

            # Preserve original method metadata
            test_wrapper.__name__ = method.__name__
            test_wrapper.__doc__ = method.__doc__ or f"Test {method.__name__.replace('_', ' ')}"
            test_wrapper.__qualname__ = f"{test_suite_class.__name__}.{method.__name__}"

            return test_wrapper

        # Add the wrapper function to the class
        setattr(test_suite_class, method_name, create_test_wrapper(test_method))

    return test_suite_class


class BaseFileSourceTestSuite(ABC):
    """
    Abstract base class for testing BaseFilesSource implementations.

    This class provides a comprehensive test suite that can be inherited by
    specific file source test classes. Subclasses need to implement the
    abstract methods to provide the file source configuration and setup.
    """

    @property
    @abstractmethod
    def root_uri(self) -> str:
        """Return the root URI for the file source (e.g., 'temp://test1')."""
        pass

    @property
    @abstractmethod
    def plugin_config(self) -> dict[str, Any]:
        """Return the plugin configuration dictionary."""
        pass

    @abstractmethod
    def get_configured_file_sources(self) -> TestConfiguredFileSources:
        """Return a configured file sources instance with test data populated."""
        pass

    @abstractmethod
    def get_file_source_instance(self, file_sources: TestConfiguredFileSources) -> BaseFilesSource:
        """Return the specific file source instance from the configured file sources."""
        pass

    def populate_test_scenario(self, file_source: BaseFilesSource) -> None:
        """
        Create a standard directory structure for testing.

        Creates the following structure:
        /a (file with content "a")
        /b (file with content "b")
        /c (file with content "c")
        /dir1/d (file with content "d")
        /dir1/e (file with content "e")
        /dir1/sub1/f (file with content "f")
        """
        user_context = user_context_fixture()

        test_files = [
            ("/a", "a"),
            ("/b", "b"),
            ("/c", "c"),
            ("/dir1/d", "d"),
            ("/dir1/e", "e"),
            ("/dir1/sub1/f", "f"),
        ]

        for path, content in test_files:
            self._upload_content_to_path(file_source, path, content, user_context)

    def _upload_content_to_path(
        self, file_source: BaseFilesSource, target_path: str, content: str, user_context: Optional[Any] = None
    ) -> None:
        """Helper method to upload content to a specific path in the file source."""
        with tempfile.NamedTemporaryFile(mode="w") as temp_file:
            temp_file.write(content)
            temp_file.flush()
            file_source.write_from(target_path, temp_file.name, user_context=user_context)

    def assert_list_contains_names(
        self, file_source: BaseFilesSource, path: str, recursive: bool, expected_names: list[str]
    ) -> list[AnyRemoteEntry]:
        """Assert that listing a path returns entries with the expected names."""
        result, count = file_source.list(path, recursive=recursive)
        expected_count = len(expected_names)
        assert count == expected_count, f"Expected {expected_count} items, got {count}"
        actual_names = sorted([entry.name for entry in result])
        expected_names_sorted = sorted(expected_names)
        assert actual_names == expected_names_sorted, f"Expected {expected_names_sorted}, got {actual_names}"
        return result

    def assert_entry_properties(
        self, entry: AnyRemoteEntry, expected_name: str, expected_class: str, expected_path: str
    ) -> None:
        """Assert that an entry has all the expected properties and values."""
        assert entry is not None, f"Expected to find entry '{expected_name}' in the listing"
        assert entry.class_ == expected_class, f"Expected '{expected_name}' to be a {expected_class} entry"
        assert entry.name == expected_name, f"Entry '{expected_name}' should have name '{expected_name}'"
        assert entry.path == expected_path, f"Entry '{expected_name}' should have path '{expected_path}'"
        assert entry.uri == f"{self.root_uri}{expected_path}", f"Entry '{expected_name}' should have correct URI"

        # Additional checks for file entries
        if expected_class == "File":
            assert isinstance(entry, RemoteFile), f"Entry '{expected_name}' should be a RemoteFile instance"
            assert hasattr(entry, "size"), f"File entry '{expected_name}' should have a size attribute"
            assert entry.size > 0, f"File '{expected_name}' should have a size greater than 0"
        elif expected_class == "Directory":
            assert isinstance(entry, RemoteDirectory), f"Entry '{expected_name}' should be a RemoteDirectory instance"

    def verify_all_entries(self, entries: list[AnyRemoteEntry], expected_entries: dict[str, tuple[str, str]]) -> None:
        """
        Verify all entries in a listing have the correct properties.

        Args:
            entries: List of entries from file source listing
            expected_entries: Dict mapping entry name to (class, path) tuple
        """
        # Verify count matches expected
        expected_count = len(expected_entries)
        actual_count = len(entries)
        assert actual_count == expected_count, f"Expected {expected_count} entries, got {actual_count}"

        # Create a lookup dict for quick access
        entries_by_name = {entry.name: entry for entry in entries}

        # Verify we have all expected entries
        missing_entries = set(expected_entries.keys()) - set(entries_by_name.keys())
        assert not missing_entries, f"Missing expected entries: {missing_entries}"

        # Verify each expected entry has correct properties
        for name, (expected_class, expected_path) in expected_entries.items():
            entry = entries_by_name[name]
            self.assert_entry_properties(entry, name, expected_class, expected_path)

    # Test methods that can be used directly or called from specific test classes

    def test_basic_file_access(self) -> None:
        """Test basic file access and content verification."""
        file_sources = self.get_configured_file_sources()

        test_cases = [
            ("a", "a"),
            ("b", "b"),
            ("c", "c"),
            ("dir1/d", "d"),
            ("dir1/e", "e"),
            ("dir1/sub1/f", "f"),
        ]

        for file_path, expected_content in test_cases:
            full_uri = f"{self.root_uri}/{file_path}"
            assert_realizes_contains(file_sources, full_uri, expected_content)

    def test_non_recursive_listing(self) -> None:
        """Test non-recursive directory listing."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        # Test root directory
        root_expected_entries = {
            "a": ("File", "/a"),
            "b": ("File", "/b"),
            "c": ("File", "/c"),
            "dir1": ("Directory", "/dir1"),
        }

        root_result, count = file_source.list("/", recursive=False)
        assert count == len(root_expected_entries), f"Expected {len(root_expected_entries)} items, got {count}"
        self.verify_all_entries(root_result, root_expected_entries)

        # Test subdirectory
        subdir_expected_entries = {
            "d": ("File", "/dir1/d"),
            "e": ("File", "/dir1/e"),
            "sub1": ("Directory", "/dir1/sub1"),
        }

        subdir_result, count = file_source.list("/dir1", recursive=False)
        assert count == len(subdir_expected_entries), f"Expected {len(subdir_expected_entries)} items, got {count}"
        self.verify_all_entries(subdir_result, subdir_expected_entries)

    def test_recursive_listing(self) -> None:
        """Test recursive directory listing."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        # Define expected entries with their properties
        expected_entries = {
            "a": ("File", "/a"),
            "b": ("File", "/b"),
            "c": ("File", "/c"),
            "dir1": ("Directory", "/dir1"),
            "d": ("File", "/dir1/d"),
            "e": ("File", "/dir1/e"),
            "sub1": ("Directory", "/dir1/sub1"),
            "f": ("File", "/dir1/sub1/f"),
        }

        result, count = file_source.list("/", recursive=True)
        assert count == len(expected_entries), f"Expected {len(expected_entries)} items, got {count}"
        self.verify_all_entries(result, expected_entries)

    def test_pagination_functionality(self) -> None:
        """Test pagination when supported by the file source."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        if not file_source.supports_pagination:
            pytest.skip("File source does not support pagination")

        # Define expected entries for root directory
        root_expected_entries = {
            "a": ("File", "/a"),
            "b": ("File", "/b"),
            "c": ("File", "/c"),
            "dir1": ("Directory", "/dir1"),
        }

        # Get all entries for comparison and verify their properties
        all_entries, total_count = file_source.list("/", recursive=False)
        assert total_count == len(root_expected_entries)
        self.verify_all_entries(all_entries, root_expected_entries)

        # Test first entry
        result, count = file_source.list("/", recursive=False, limit=1, offset=0)
        assert count == len(root_expected_entries)
        assert len(result) == 1
        assert result[0] == all_entries[0]
        # Verify the single entry properties
        first_entry = result[0]
        expected_class, expected_path = root_expected_entries[first_entry.name]
        self.assert_entry_properties(first_entry, first_entry.name, expected_class, expected_path)

        # Test second entry
        result, count = file_source.list("/", recursive=False, limit=1, offset=1)
        assert count == len(root_expected_entries)
        assert len(result) == 1
        assert result[0] == all_entries[1]
        # Verify the single entry properties
        second_entry = result[0]
        expected_class, expected_path = root_expected_entries[second_entry.name]
        self.assert_entry_properties(second_entry, second_entry.name, expected_class, expected_path)

        # Test multiple entries
        result, count = file_source.list("/", recursive=False, limit=2, offset=1)
        assert count == len(root_expected_entries)
        assert len(result) == 2
        assert result[0] == all_entries[1]
        assert result[1] == all_entries[2]

    def test_pagination_with_limit_exceeding_total(self) -> None:
        """Test pagination when limit exceeds total number of entries."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        if not file_source.supports_pagination:
            pytest.skip("File source does not support pagination")

        # Define expected entries for counting
        root_expected_entries = {
            "a": ("File", "/a"),
            "b": ("File", "/b"),
            "c": ("File", "/c"),
            "dir1": ("Directory", "/dir1"),
        }
        expected_count = len(root_expected_entries)

        # Test with limit larger than total entries
        result, count = file_source.list("/", recursive=False, limit=10, offset=0)
        assert count == expected_count
        assert len(result) == expected_count  # Should return all available entries

        # Test with offset at the end
        result, count = file_source.list("/", recursive=False, limit=5, offset=3)
        assert count == expected_count
        assert len(result) == 1  # Only one entry left after offset=3

    def test_search_functionality(self) -> None:
        """Test search functionality when supported by the file source."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        if not file_source.supports_search:
            pytest.skip("File source does not support search")

        # Test searching for specific files
        test_cases = [
            ("a", ["a"]),
            ("b", ["b"]),
            ("c", ["c"]),
        ]

        for query, expected_names in test_cases:
            result, count = file_source.list("/", recursive=False, query=query)
            assert count == len(expected_names)
            assert len(result) == len(expected_names)
            if expected_names:
                assert result[0].name == expected_names[0]

        # Test searching for directory content (should return parent directory)
        result, count = file_source.list("/", recursive=False, query="d")
        assert count == 1
        assert len(result) == 1
        assert result[0].name == "dir1"

        # Test searching in subdirectory
        result, count = file_source.list("/dir1", recursive=False, query="e")
        assert count == 1
        assert len(result) == 1
        assert result[0].name == "e"

    def test_search_no_results(self) -> None:
        """Test search functionality when no results are found."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        if not file_source.supports_search:
            pytest.skip("File source does not support search")

        # Search for non-existent file
        result, count = file_source.list("/", recursive=False, query="nonexistent")
        assert count == 0
        assert len(result) == 0

        # Search in subdirectory for file that exists elsewhere
        result, count = file_source.list("/dir1", recursive=False, query="a")
        assert count == 0
        assert len(result) == 0

    def test_search_case_sensitivity(self) -> None:
        """Test search functionality case sensitivity behavior."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        if not file_source.supports_search:
            pytest.skip("File source does not support search")

        # Test case sensitivity (behavior may vary by implementation)
        result_lower, count_lower = file_source.list("/", recursive=False, query="a")
        result_upper, count_upper = file_source.list("/", recursive=False, query="A")

        # At minimum, lowercase should work (since our test files use lowercase)
        assert count_lower >= 1
        assert len(result_lower) >= 1

    def test_empty_search_query(self) -> None:
        """Test that empty search query returns all entries."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        if not file_source.supports_search:
            pytest.skip("File source does not support search")

        all_entries, all_count = file_source.list("/", recursive=False)
        empty_query_result, empty_query_count = file_source.list("/", recursive=False, query="")

        assert empty_query_count == all_count
        assert len(empty_query_result) == len(all_entries)
        assert empty_query_result == all_entries

    def test_pagination_not_supported_error(self) -> None:
        """Test that pagination raises error when not supported."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        if file_source.supports_pagination:
            pytest.skip("File source supports pagination - this test is for file sources without pagination support")

        with pytest.raises(RequestParameterInvalidException) as exc_info:
            file_source.list("/", recursive=False, limit=1, offset=0)
        assert "Pagination is not supported" in str(exc_info.value)

    def test_search_not_supported_error(self) -> None:
        """Test that search raises error when not supported."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        if file_source.supports_search:
            pytest.skip("File source supports search - this test is for file sources without search support")

        with pytest.raises(RequestParameterInvalidException) as exc_info:
            file_source.list("/", recursive=False, query="test")
        assert "Server-side search is not supported by this file source" in str(exc_info.value)

    def test_sorting_not_supported_error(self) -> None:
        """Test that sorting raises error when not supported (default behavior)."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        if file_source.supports_sorting:
            pytest.skip("File source supports sorting - this test is for file sources without sorting support")

        with pytest.raises(RequestParameterInvalidException) as exc_info:
            file_source.list("/", recursive=False, sort_by="name")
        assert "Server-side sorting is not supported by this file source" in str(exc_info.value)

    def test_pagination_parameter_validation(self) -> None:
        """Test validation of pagination parameters."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        if not file_source.supports_pagination:
            pytest.skip("File source does not support pagination")

        # Test negative limit
        with pytest.raises(RequestParameterInvalidException) as exc_info:
            file_source.list("/", recursive=False, limit=-1, offset=0)
        assert "Limit must be greater than 0" in str(exc_info.value)

        # Test zero limit
        with pytest.raises(RequestParameterInvalidException) as exc_info:
            file_source.list("/", recursive=False, limit=0, offset=0)
        assert "Limit must be greater than 0" in str(exc_info.value)

        # Test negative offset
        with pytest.raises(RequestParameterInvalidException) as exc_info:
            file_source.list("/", recursive=False, limit=1, offset=-1)
        assert "Offset must be greater than or equal to 0" in str(exc_info.value)

    def test_comprehensive_entry_properties(self) -> None:
        """Test comprehensive verification of all entry properties across different listing scenarios."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        # Define all expected entries across the test scenario
        all_expected_entries = {
            "a": ("File", "/a"),
            "b": ("File", "/b"),
            "c": ("File", "/c"),
            "dir1": ("Directory", "/dir1"),
            "d": ("File", "/dir1/d"),
            "e": ("File", "/dir1/e"),
            "sub1": ("Directory", "/dir1/sub1"),
            "f": ("File", "/dir1/sub1/f"),
        }

        # Test root directory listing
        root_expected = {k: v for k, v in all_expected_entries.items() if v[1].startswith("/") and "/" not in v[1][1:]}
        root_result, root_count = file_source.list("/", recursive=False)
        assert root_count == len(root_expected)
        self.verify_all_entries(root_result, root_expected)

        # Test subdirectory listing (/dir1)
        dir1_expected = {
            k: v for k, v in all_expected_entries.items() if v[1].startswith("/dir1/") and v[1].count("/") == 2
        }
        dir1_result, dir1_count = file_source.list("/dir1", recursive=False)
        assert dir1_count == len(dir1_expected)
        self.verify_all_entries(dir1_result, dir1_expected)

        # Test nested subdirectory listing (/dir1/sub1)
        sub1_expected = {
            k: v for k, v in all_expected_entries.items() if v[1].startswith("/dir1/sub1/") and v[1].count("/") == 3
        }
        sub1_result, sub1_count = file_source.list("/dir1/sub1", recursive=False)
        assert sub1_count == len(sub1_expected)
        self.verify_all_entries(sub1_result, sub1_expected)

        # Test recursive listing includes all expected entries with correct properties
        recursive_result, recursive_count = file_source.list("/", recursive=True)
        assert recursive_count == len(all_expected_entries)
        self.verify_all_entries(recursive_result, all_expected_entries)

    def test_file_source_properties(self) -> None:
        """Test basic file source properties and metadata."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        # Test that the file source has required properties
        assert hasattr(file_source, "id")
        assert hasattr(file_source, "label")
        assert hasattr(file_source, "plugin_type")

        # Test browsable capability
        assert file_source.get_browsable() is True

        # Test URI generation
        uri_root = file_source.get_uri_root()
        assert uri_root is not None
        assert isinstance(uri_root, str)
        assert len(uri_root) > 0

    def test_to_dict_serialization(self) -> None:
        """Test file source serialization to dictionary."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        # Test basic serialization
        result = file_source.to_dict()
        assert isinstance(result, dict)

        required_keys = ["id", "type", "label", "writable", "browsable", "scheme", "supports"]
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

        # Test supports section
        supports = result["supports"]
        assert isinstance(supports, dict)
        assert "pagination" in supports
        assert "search" in supports
        assert "sorting" in supports

        # Test serialization with user context
        user_context = user_context_fixture()
        result_with_context = file_source.to_dict(user_context=user_context)
        assert isinstance(result_with_context, dict)
