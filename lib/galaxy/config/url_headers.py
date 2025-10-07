"""
Configuration and management for URL request headers allow-list with URL pattern matching.

This module provides functionality to:
1. Load and parse URL headers configuration from YAML with URL patterns
2. Validate whether headers are allowed for specific URLs based on patterns
3. Determine if headers should be treated as sensitive (encrypted)

This is a security feature to control what headers can be sent when Galaxy
fetches external URLs on behalf of users, with fine-grained control based
on the target URL.
"""

import logging
import re
from typing import Optional

import yaml
from pydantic import (
    BaseModel,
    field_validator,
)

log = logging.getLogger(__name__)


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


class UrlHeadersConfig:
    """
    Manages the configuration for allowed URL request headers with pattern matching.

    This class loads and manages the allow-list of headers that can be included
    in URL fetch requests based on URL patterns, along with their sensitivity settings.
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the URL headers configuration.

        Args:
            config_file: Path to the YAML configuration file. If None or file
                        doesn't exist, no headers will be allowed.
        """
        self._patterns: list[UrlPatternConfig] = []
        self._compiled_patterns: list[tuple[re.Pattern[str], UrlPatternConfig]] = []
        self._config_file = config_file

        if config_file:
            self._load_config(config_file)

    def _load_config(self, config_file: str) -> None:
        """Load configuration from YAML file."""
        try:
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f)

            if not config_data:
                log.info(f"URL headers config file {config_file} is empty - no headers will be allowed")
                return

            # Load patterns
            patterns_data = config_data.get("patterns", [])
            if patterns_data:
                for pattern_data in patterns_data:
                    try:
                        pattern_config = UrlPatternConfig(**pattern_data)
                        self._patterns.append(pattern_config)

                        # Compile regex pattern
                        try:
                            compiled_pattern = re.compile(pattern_config.url_pattern)
                            self._compiled_patterns.append((compiled_pattern, pattern_config))
                            log.debug(
                                f"Loaded URL pattern: {pattern_config.url_pattern} "
                                f"({len(pattern_config.headers)} headers)"
                            )
                        except re.error as e:
                            log.warning(f"Invalid regex pattern '{pattern_config.url_pattern}' in {config_file}: {e}")

                    except Exception as e:
                        log.warning(f"Invalid pattern configuration in {config_file}: {pattern_data} - {e}")

            log.info(f"Loaded {len(self._patterns)} URL patterns from {config_file}")

        except FileNotFoundError:
            log.info(f"URL headers config file {config_file} not found - no headers will be allowed")
        except yaml.YAMLError as e:
            log.error(f"Error parsing URL headers config file {config_file}: {e}")
        except Exception as e:
            log.error(f"Error loading URL headers config file {config_file}: {e}")

    def _find_matching_pattern(self, url: str) -> Optional[UrlPatternConfig]:
        """
        Find the first URL pattern that matches the given URL.

        Args:
            url: The URL to match against patterns

        Returns:
            The first matching UrlPatternConfig, or None if no pattern matches
        """
        for compiled_pattern, pattern_config in self._compiled_patterns:
            if compiled_pattern.match(url):
                log.debug(f"URL '{url}' matched pattern: {pattern_config.url_pattern}")
                return pattern_config
        return None

    def is_header_allowed_for_url(self, header_name: str, url: str) -> bool:
        """
        Check if a header is allowed for a specific URL.

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
