"""
Utilities for working with tool IDs and GUIDs.

Tool IDs come in several formats:
- Short ID: Just the tool identifier (e.g., "bwa", "qiime2__feature_classifier__classify_sklearn")
- GUID: Full toolshed identifier (e.g., "toolshed.g2.bx.psu.edu/repos/owner/name/tool_id/version")

This module provides utilities to parse and convert between these formats.
"""

import re


def extract_tool_id_from_xml(xml_content: str, max_read: int = 2000) -> str | None:
    """
    Extract tool ID from XML content using a simple regex.

    This is a fast extraction method that doesn't require full XML parsing.
    Useful when you need just the ID without macro expansion or validation.

    Args:
        xml_content: The XML content to parse (can be partial).
        max_read: Maximum characters to read from content (default: 2000).

    Returns:
        The tool ID if found, None otherwise.

    Example:
        >>> extract_tool_id_from_xml('<tool id="bwa" version="1.0">')
        'bwa'
    """
    content = xml_content[:max_read] if len(xml_content) > max_read else xml_content
    match = re.search(r'<tool[^>]+id=["\']([^"\']+)["\']', content)
    return match.group(1) if match else None


def extract_tool_id_from_file(file_path: str, max_read: int = 2000) -> str | None:
    """
    Extract tool ID from an XML file.

    Args:
        file_path: Path to the tool XML file.
        max_read: Maximum characters to read from file (default: 2000).

    Returns:
        The tool ID if found, None otherwise.
    """
    try:
        with open(file_path) as f:
            content = f.read(max_read)
        return extract_tool_id_from_xml(content, max_read=max_read)
    except Exception:
        return None


def extract_short_id_from_guid(guid: str) -> str | None:
    """
    Extract the short tool ID from a toolshed GUID.

    GUIDs have the format: toolshed.domain/repos/owner/name/tool_id/version
    This extracts just the tool_id part.

    Args:
        guid: The full toolshed GUID.

    Returns:
        The short tool ID, or the original guid if it's not in the expected format.

    Examples:
        >>> extract_short_id_from_guid("toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.1.0")
        'bwa'
        >>> extract_short_id_from_guid("toolshed.g2.bx.psu.edu/repos/iuc/qiime2__feature_classifier__classify_sklearn/qiime2__feature_classifier__classify_sklearn/2024.5.0+q2galaxy.2024.5.0")
        'qiime2__feature_classifier__classify_sklearn'
        >>> extract_short_id_from_guid("simple_tool")
        'simple_tool'
    """
    if "/" not in guid:
        # Not a GUID, return as-is
        return guid

    # Split on "/" and extract the second-to-last part
    # Format: toolshed.domain/repos/owner/name/tool_id/version
    # Parts: [domain, "repos", owner, name, tool_id, version]
    parts = guid.split("/")
    if len(parts) >= 2:
        # The tool_id is typically the second-to-last part (before version)
        tool_id = parts[-2]
        return tool_id

    return guid


def build_guid(tool_shed: str, owner: str, name: str, tool_id: str, version: str) -> str:
    """
    Build a full toolshed GUID from components.

    Args:
        tool_shed: The toolshed domain (e.g., "toolshed.g2.bx.psu.edu").
        owner: Repository owner.
        name: Repository name.
        tool_id: Tool ID.
        version: Tool version.

    Returns:
        The full GUID string.

    Example:
        >>> build_guid("toolshed.g2.bx.psu.edu", "devteam", "bwa", "bwa", "0.1.0")
        'toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.1.0'
    """
    return f"{tool_shed}/repos/{owner}/{name}/{tool_id}/{version}"


def is_toolshed_guid(tool_id: str) -> bool:
    """
    Check if a tool ID is a toolshed GUID.

    Args:
        tool_id: The tool ID to check.

    Returns:
        True if this looks like a toolshed GUID, False otherwise.

    Examples:
        >>> is_toolshed_guid("toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.1.0")
        True
        >>> is_toolshed_guid("bwa")
        False
    """
    return "/repos/" in tool_id
