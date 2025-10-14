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
        matching_patterns = self.find_all_matching(url)
        if not matching_patterns:
            return False

        result = self._find_header_in_patterns(header_name, matching_patterns)
        return result is not None

    def is_header_sensitive_for_url(self, header_name: str, url: str) -> bool:
        """
        Check if a header should be treated as sensitive for a specific URL.

        If multiple patterns match the URL and define the same header, the header
        is treated as sensitive if ANY matching pattern marks it as sensitive
        (secure by default).

        Args:
            header_name: The header name to check (case-insensitive)
            url: The target URL

        Returns:
            True if the header is allowed and marked as sensitive in any matching pattern,
            False otherwise
        """
        matching_patterns = self.find_all_matching(url)
        if not matching_patterns:
            return False

        header_name_lower = header_name.lower()
        for pattern_config in matching_patterns:
            for header_config in pattern_config.headers:
                if header_config.name.lower() == header_name_lower:
                    if header_config.sensitive:
                        return True
        return False


class UrlHeadersConfigFactory:
    """Factory for creating UrlHeadersConfig instances."""

    @staticmethod
    def _load_patterns_from_file(config_file: str) -> list[UrlPatternConfig]:
        """Load pattern configurations from a YAML file.

        Args:
            config_file: Path to the YAML configuration file

        Returns:
            List of UrlPatternConfig objects

        Raises:
            UrlHeadersConfigurationException: If file cannot be read or parsed
        """
        try:
            with open(config_file) as f:
                config_data = yaml.safe_load(f)
        except FileNotFoundError as e:
            raise UrlHeadersConfigurationException(
                f"URL headers configuration file not found: {config_file}. "
                "Please check the 'url_headers_config_file' setting in your Galaxy configuration."
            ) from e
        except yaml.YAMLError as e:
            raise UrlHeadersConfigurationException(
                f"Failed to parse URL headers configuration file {config_file}: {e}. Please check the YAML syntax."
            ) from e
        except Exception as e:
            raise UrlHeadersConfigurationException(
                f"Failed to read URL headers configuration file {config_file}: {e}"
            ) from e

        if not config_data:
            return []

        patterns_data = config_data.get("patterns", [])
        if not patterns_data:
            return []

        patterns = []
        for i, pattern_data in enumerate(patterns_data):
            try:
                pattern_config = UrlPatternConfig(**pattern_data)
                patterns.append(pattern_config)
            except Exception as e:
                raise UrlHeadersConfigurationException(
                    f"Invalid pattern configuration at index {i} in {config_file}: {e}. "
                    "Each pattern must have 'url_pattern' (valid regex) and 'headers' (list of header configs)."
                ) from e

        return patterns

    @staticmethod
    def from_app_config(app_config: GalaxyAppConfiguration) -> UrlHeadersConfig:
        """
        Create a UrlHeadersConfig from Galaxy app configuration.

        Args:
            app_config: Galaxy application configuration

        Returns:
            UrlHeadersConfiguration if config file is specified and exists,
            NullUrlHeadersConfiguration otherwise

        Raises:
            UrlHeadersConfigurationException: If config file exists but is invalid
        """
        config_file = app_config.url_headers_config_file
        if not config_file:
            return NullUrlHeadersConfiguration()

        return UrlHeadersConfigFactory.from_file(config_file)

    @staticmethod
    def from_file(config_file: str) -> UrlHeadersConfig:
        """
        Create a UrlHeadersConfig from a YAML file.

        If the file doesn't exist, returns NullUrlHeadersConfiguration for backwards compatibility.

        Args:
            config_file: Path to the YAML configuration file

        Returns:
            UrlHeadersConfiguration with patterns loaded from the file, or
            NullUrlHeadersConfiguration if file doesn't exist

        Raises:
            UrlHeadersConfigurationException: If file exists but contains errors
        """
        try:
            config = UrlHeadersConfiguration()
            patterns = UrlHeadersConfigFactory._load_patterns_from_file(config_file)

            for pattern in patterns:
                config._add_pattern(pattern)

            log.info(f"Loaded {len(config._patterns)} URL patterns from {config_file}")
            return config
        except UrlHeadersConfigurationException as e:
            # If the file doesn't exist, return null config for backwards compatibility
            if "not found" in str(e):
                log.warning(f"URL headers configuration file not found: {config_file}. Using null configuration.")
                return NullUrlHeadersConfiguration()
            # For any other configuration error, re-raise
            raise

    @staticmethod
    def from_dict(config_dict: dict) -> UrlHeadersConfig:
        """
        Create a UrlHeadersConfig from a dictionary (useful for testing).

        Args:
            config_dict: Dictionary containing URL headers configuration with 'patterns' key

        Returns:
            UrlHeadersConfiguration with patterns loaded from the dictionary

        Raises:
            UrlHeadersConfigurationException: If configuration is invalid

        Example:
            config_dict = {
                "patterns": [
                    {
                        "url_pattern": "^https://api\\.github\\.com/.*",
                        "headers": [
                            {"name": "Authorization", "sensitive": True},
                            {"name": "Accept", "sensitive": False}
                        ]
                    }
                ]
            }
            config = UrlHeadersConfigFactory.from_dict(config_dict)
        """
        config = UrlHeadersConfiguration()

        if not config_dict:
            return config

        patterns_data = config_dict.get("patterns", [])
        if not patterns_data:
            return config

        for i, pattern_data in enumerate(patterns_data):
            try:
                pattern_config = UrlPatternConfig(**pattern_data)
                config._add_pattern(pattern_config)
            except Exception as e:
                raise UrlHeadersConfigurationException(
                    f"Invalid pattern configuration at index {i}: {e}. "
                    "Each pattern must have 'url_pattern' (valid regex) and 'headers' (list of header configs)."
                ) from e

        log.info(f"Loaded {len(config._patterns)} URL patterns from dictionary")
        return config

    @staticmethod
    def create_null_config() -> NullUrlHeadersConfiguration:
        """
        Create a null configuration that doesn't allow any headers.

        Returns:
            NullUrlHeadersConfiguration instance
        """
        return NullUrlHeadersConfiguration()
