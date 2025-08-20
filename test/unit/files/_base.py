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
    ) -> list[Any]:
        """Assert that listing a path returns entries with the expected names."""
        result, count = file_source.list(path, recursive=recursive)
        assert count == len(expected_names), f"Expected {len(expected_names)} items, got {count}"
        actual_names = sorted([entry.name for entry in result])
        expected_names_sorted = sorted(expected_names)
        assert actual_names == expected_names_sorted, f"Expected {expected_names_sorted}, got {actual_names}"
        return result

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
        self.assert_list_contains_names(file_source, "/", recursive=False, expected_names=["a", "b", "c", "dir1"])

        # Test subdirectory
        self.assert_list_contains_names(file_source, "/dir1", recursive=False, expected_names=["d", "e", "sub1"])

    def test_recursive_listing(self) -> None:
        """Test recursive directory listing."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        expected_names = ["a", "b", "c", "dir1", "d", "e", "sub1", "f"]
        result, count = file_source.list("/", recursive=True)

        # For recursive listings, the exact behavior may vary between implementations
        # We verify that we get at least the expected number of items
        assert count == len(expected_names), f"Expected {len(expected_names)} items, got {count}"
        assert len(result) == len(expected_names), f"Expected {len(expected_names)} results, got {len(result)}"

    def test_pagination_functionality(self) -> None:
        """Test pagination when supported by the file source."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        if not file_source.supports_pagination:
            pytest.skip("File source does not support pagination")

        # Get all entries for comparison
        all_entries, total_count = file_source.list("/", recursive=False)
        assert total_count == 4  # a, b, c, dir1
        assert len(all_entries) == 4

        # Test first entry
        result, count = file_source.list("/", recursive=False, limit=1, offset=0)
        assert count == 4
        assert len(result) == 1
        assert result[0] == all_entries[0]

        # Test second entry
        result, count = file_source.list("/", recursive=False, limit=1, offset=1)
        assert count == 4
        assert len(result) == 1
        assert result[0] == all_entries[1]

        # Test multiple entries
        result, count = file_source.list("/", recursive=False, limit=2, offset=1)
        assert count == 4
        assert len(result) == 2
        assert result[0] == all_entries[1]
        assert result[1] == all_entries[2]

    def test_pagination_with_limit_exceeding_total(self) -> None:
        """Test pagination when limit exceeds total number of entries."""
        file_source = self.get_file_source_instance(self.get_configured_file_sources())

        if not file_source.supports_pagination:
            pytest.skip("File source does not support pagination")

        # Test with limit larger than total entries
        result, count = file_source.list("/", recursive=False, limit=10, offset=0)
        assert count == 4  # Total entries: a, b, c, dir1
        assert len(result) == 4  # Should return all available entries

        # Test with offset at the end
        result, count = file_source.list("/", recursive=False, limit=5, offset=3)
        assert count == 4
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
