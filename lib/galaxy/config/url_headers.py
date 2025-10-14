import abc
import logging
import re
from typing import Optional

import yaml
from pydantic import (
    BaseModel,
    field_validator,
)

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ConfigDoesNotAllowException

log = logging.getLogger(__name__)


class UrlHeadersConfigurationException(Exception):
    """Raised when there is an error in the URL headers configuration."""

    pass


class HeaderConfig(BaseModel):
    """Configuration for a single header."""

    name: str
    sensitive: bool = False

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Header name cannot be empty")
        return v.strip()


class UrlPatternConfig(BaseModel):
    """Configuration for a URL pattern and its allowed headers."""

    url_pattern: str
    headers: list[HeaderConfig] = []

    @field_validator("url_pattern")
    @classmethod
    def pattern_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("URL pattern cannot be empty")
        return v.strip()


class UrlHeadersConfig(abc.ABC):
    """
    Manages the configuration for allowed URL request headers with pattern matching.
    """

    @abc.abstractmethod
    def is_header_allowed_for_url(self, header_name: str, url: str) -> bool:
        pass

    @abc.abstractmethod
    def is_header_sensitive_for_url(self, header_name: str, url: str) -> bool:
        pass

    @abc.abstractmethod
    def find_all_matching(self, url: str) -> list[UrlPatternConfig]:
        pass


class NullUrlHeadersConfiguration(UrlHeadersConfig):
    """
    Default configuration when there is no real configuration for allowing URL request headers.

    This configuration raises exceptions when any method is called, providing fail-fast
    behavior to clearly indicate that headers require configuration.
    """

    _ERROR_MESSAGE = (
        "No URL headers configuration is available. "
        "Headers require explicit configuration to be allowed. "
        "Please contact your Galaxy administrator to configure URL headers."
    )

    def is_header_allowed_for_url(self, header_name: str, url: str) -> bool:
        """
        Raises an exception - headers require configuration.

        Raises:
            ConfigDoesNotAllowException: Always raised to indicate missing configuration
        """
        raise ConfigDoesNotAllowException(f"Cannot check if header '{header_name}' is allowed: {self._ERROR_MESSAGE}")

    def is_header_sensitive_for_url(self, header_name: str, url: str) -> bool:
        """
        Raises an exception - headers require configuration.

        Raises:
            ConfigDoesNotAllowException: Always raised to indicate missing configuration
        """
        raise ConfigDoesNotAllowException(f"Cannot check if header '{header_name}' is sensitive: {self._ERROR_MESSAGE}")

    def find_all_matching(self, url: str) -> list[UrlPatternConfig]:
        """
        Raises an exception - no patterns are configured.

        Raises:
            ConfigDoesNotAllowException: Always raised to indicate missing configuration
        """
        raise ConfigDoesNotAllowException(f"Cannot find matching patterns for URL '{url}': {self._ERROR_MESSAGE}")


class UrlHeadersConfiguration(UrlHeadersConfig):
    """Contains valid configuration to allow URL request headers."""

    def __init__(self):
        self._patterns: list[UrlPatternConfig] = []
        self._compiled_patterns: list[tuple[re.Pattern[str], UrlPatternConfig]] = []

    def _add_pattern(self, pattern_config: UrlPatternConfig) -> None:
        self._patterns.append(pattern_config)
        try:
            compiled_pattern = re.compile(pattern_config.url_pattern)
            self._compiled_patterns.append((compiled_pattern, pattern_config))
        except re.error as e:
            raise UrlHeadersConfigurationException(
                f"Invalid regex pattern '{pattern_config.url_pattern}' in URL headers configuration: {e}"
            ) from e

    def find_all_matching(self, url: str) -> list[UrlPatternConfig]:
        """
        Find all URL patterns that match the given URL.

        Args:
            url: The URL to match against patterns

        Returns:
            List of all matching UrlPatternConfig objects (may be empty)
        """
        matching_patterns = []
        for compiled_pattern, pattern_config in self._compiled_patterns:
            if compiled_pattern.match(url):
                matching_patterns.append(pattern_config)
        return matching_patterns

    def _find_header_in_patterns(
        self, header_name: str, matching_patterns: list[UrlPatternConfig]
    ) -> Optional[tuple[HeaderConfig, UrlPatternConfig]]:
        """
        Find a header configuration in matching patterns.

        Args:
            header_name: The header name to find (case-insensitive)
            matching_patterns: List of patterns to search

        Returns:
            Tuple of (HeaderConfig, UrlPatternConfig) for first match, or None if not found
        """
        header_name_lower = header_name.lower()
        for pattern_config in matching_patterns:
            for header_config in pattern_config.headers:
                if header_config.name.lower() == header_name_lower:
                    return (header_config, pattern_config)
        return None

    def is_header_allowed_for_url(self, header_name: str, url: str) -> bool:
        """
        Check if a header is allowed for a specific URL.

        If multiple patterns match the URL, the header is allowed if it appears
        in ANY of the matching patterns.

        Args:
            header_name: The header name to check (case-insensitive)
            url: The target URL

        Returns:
            True if the header is allowed for this URL, False otherwise
        """
        pattern_config = self._find_matching_pattern(url)
        if not pattern_config:
            log.debug(f"No pattern matched URL '{url}' - header '{header_name}' denied")
            return False

        # Check if header is allowed in this pattern
        header_name_lower = header_name.lower()
        for header_config in pattern_config.headers:
            if header_config.name.lower() == header_name_lower:
                return True

        log.debug(f"Header '{header_name}' not allowed for URL '{url}' " f"(pattern: {pattern_config.url_pattern})")
        return False

    def is_header_sensitive_for_url(self, header_name: str, url: str) -> bool:
        """
        Check if a header should be treated as sensitive for a specific URL.

        Args:
            header_name: The header name to check (case-insensitive)
            url: The target URL

        Returns:
            True if the header is allowed and marked as sensitive, False otherwise
        """
        pattern_config = self._find_matching_pattern(url)
        if not pattern_config:
            return False

        header_name_lower = header_name.lower()
        for header_config in pattern_config.headers:
            if header_config.name.lower() == header_name_lower:
                return header_config.sensitive

        return False

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"UrlHeadersConfig(file={self._config_file}, patterns={len(self._patterns)})"

    def __repr__(self) -> str:
        """String representation for debugging."""
        return self.__str__()
