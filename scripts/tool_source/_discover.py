"""
Tool discovery utilities.

Used by ``populate_store.py`` to walk Galaxy's tool configuration without
booting a full ToolBox.
"""

import logging
import os
import string
from collections.abc import (
    Iterable,
    Iterator,
)
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Optional,
    TYPE_CHECKING,
)

from galaxy.tool_util.toolbox.parser import (
    get_toolbox_parser,
    ToolConfItem,
    ToolConfSection,
)

if TYPE_CHECKING:
    from galaxy.config import GalaxyAppConfiguration

log = logging.getLogger(__name__)


@dataclass
class DiscoveredTool:
    """Information about a discovered tool file."""

    path: str  # Absolute path to tool file
    tool_conf: str  # Path to the tool_conf file that referenced this tool
    tool_path: Optional[str]  # The tool_path from the tool_conf
    guid: Optional[str] = None  # GUID for shed tools
    is_shed_tool: bool = False
    # Conf-level ``hidden="true"`` on the ``<tool>`` element (NOT the XML
    # body's ``<tool hidden="true">`` — that's already on the parsed source).
    # ToolBox._load_tool_tag_set forces ``tool.hidden = True`` when this is
    # set; the lazy path needs the same flag to make ``hidden_tool_versions``
    # in /api/tools/{id} match the eager toolbox.
    hidden: bool = False


def get_tool_configs(config: "GalaxyAppConfiguration") -> list[str]:
    """
    Get all tool configuration file paths from Galaxy config.

    Args:
        config: Galaxy configuration object.

    Returns:
        List of tool configuration file paths (tool_conf.xml, shed_tool_conf.xml, etc.)
    """
    configs = []

    # Get main tool config files
    if hasattr(config, "tool_configs") and config.tool_configs:
        configs.extend(config.tool_configs)

    # Ensure shed_tool_config_file is included if not already
    if hasattr(config, "shed_tool_config_file") and config.shed_tool_config_file:
        if config.shed_tool_config_file not in configs:
            configs.append(config.shed_tool_config_file)

    # Include migrated_tools_config if present
    if hasattr(config, "migrated_tools_config") and config.migrated_tools_config:
        if config.migrated_tools_config not in configs:
            configs.append(config.migrated_tools_config)

    return configs


def _resolve_tool_path(tool_path: Optional[str], config_filename: str, root_dir: Optional[str] = None) -> str:
    """
    Resolve the tool_path to an absolute directory path.

    Args:
        tool_path: The tool_path from the tool_conf, may be None or relative.
        config_filename: The path to the tool_conf file.
        root_dir: Optional Galaxy root directory.

    Returns:
        Absolute path to the tool directory.
    """
    if tool_path is None:
        # Default to 'tools' relative to Galaxy root or config dir
        if root_dir:
            return os.path.join(root_dir, "tools")
        config_dir = os.path.dirname(os.path.abspath(config_filename))
        # Assume config is in config/ dir, tools is at same level
        return os.path.join(os.path.dirname(config_dir), "tools")

    # Expand the ``${tool_conf_dir}`` template that test/functional/tools/sample_tool_conf.xml
    # (and similar shipped confs) use. Without this, the literal substring is taken
    # as a directory name and every tool file ends up at a non-existent path —
    # silently dropped at the os.path.exists() check below.
    tool_conf_dir = os.path.dirname(os.path.abspath(config_filename))
    tool_path = string.Template(tool_path).safe_substitute({"tool_conf_dir": tool_conf_dir})

    if os.path.isabs(tool_path):
        return tool_path

    # tool_path is relative - resolve relative to config file location
    return os.path.abspath(os.path.join(tool_conf_dir, tool_path))


def _resolve_file_template_kwds(root_dir: Optional[str]) -> dict[str, str]:
    """Resolve template variables that tool conf ``file=...`` attributes may use.

    Mirrors :py:meth:`galaxy.tools.ToolBox._path_template_kwds`. The galaxy
    import is optional so this script-local helper still works when galaxy is
    not importable; falls back to a path computed from ``root_dir``.
    """
    try:
        # Lazy + optional: helper must still work outside a galaxy install.
        from galaxy.tools import MODEL_TOOLS_PATH  # type: ignore[attr-defined]
    except Exception:
        if root_dir:
            MODEL_TOOLS_PATH = os.path.abspath(os.path.join(root_dir, "lib", "galaxy", "tools"))
        else:
            return {}
    return {"model_tools_path": MODEL_TOOLS_PATH}


def _iter_tool_items(items: Iterable[ToolConfItem]) -> Iterator[ToolConfItem]:
    """
    Recursively iterate over tool items, including those nested in sections.

    Yields ``tool`` and ``tool_dir`` items. ``tool_dir`` items reference an
    on-disk directory rather than a single file; the caller is responsible for
    walking the directory.
    """
    for item in items:
        if item.type in ("tool", "tool_dir"):
            yield item
        elif isinstance(item, ToolConfSection):
            yield from _iter_tool_items(item.items)


def _looks_like_a_tool(path: str) -> bool:
    """Cheap filter mirroring ``galaxy.tool_util.toolbox.base.looks_like_a_tool``.

    We only want XML or YAML/CWL files that plausibly define a tool. Avoid
    importing the real ``looks_like_a_tool`` so this script-local helper still
    works without galaxy on sys.path.
    """
    name = os.path.basename(path)
    if name.startswith((".", "_")) or "macro" in name.lower():
        return False
    ext = os.path.splitext(name)[1].lower()
    if ext == ".xml":
        try:
            with open(path, encoding="utf-8") as fh:
                head = fh.read(2000)
        except Exception:
            return False
        return "<tool" in head
    if ext in (".yml", ".yaml"):
        try:
            with open(path, encoding="utf-8") as fh:
                head = fh.read(2000)
        except Exception:
            return False
        # YAML user-defined tools start with ``class: GalaxyUserTool`` /
        # ``class: GalaxyTool``; CWL via ``cwlVersion:`` is acceptable too.
        return "class: Galaxy" in head or "cwlVersion" in head
    return False


def _walk_tool_dir(directory: str, recursive: bool) -> Iterator[str]:
    """Yield candidate tool file paths under ``directory``.

    Mirrors the behaviour of ``ToolBox.__watch_directory`` (skips hidden /
    private entries, recurses by default). Filtering against
    ``_looks_like_a_tool`` is the caller's responsibility — yielding all
    candidates here keeps logging at the discovery layer.
    """
    if not os.path.isdir(directory):
        log.debug(f"tool_dir does not exist: {directory}")
        return
    for name in sorted(os.listdir(directory)):
        if name.startswith((".", "_")):
            continue
        child = os.path.join(directory, name)
        if os.path.isdir(child):
            if recursive:
                yield from _walk_tool_dir(child, recursive)
        else:
            yield child


def discover_tools_from_config(
    config_filename: str,
    root_dir: Optional[str] = None,
) -> Iterator[DiscoveredTool]:
    """
    Discover all tools from a single tool configuration file.

    Args:
        config_filename: Path to a tool_conf.xml or similar file.
        root_dir: Optional Galaxy root directory for resolving relative paths.

    Yields:
        DiscoveredTool objects for each tool found.
    """
    if not os.path.exists(config_filename):
        log.debug(f"Tool config file does not exist: {config_filename}")
        return

    try:
        tool_conf_source = get_toolbox_parser(config_filename)
    except Exception as e:
        log.warning(f"Failed to parse tool config {config_filename}: {e}")
        return

    tool_path = tool_conf_source.parse_tool_path()
    resolved_tool_path = _resolve_tool_path(tool_path, config_filename, root_dir)
    is_shed_conf = tool_conf_source.is_shed_tool_conf()

    # Match what AbstractToolBox._path_template_kwds does for ToolBox: tool
    # confs may reference Galaxy-internal tool files via ``${model_tools_path}``
    # (e.g. ``<tool file="${model_tools_path}/apply_rules.xml" />`` in
    # tool_conf.xml.sample). Without expanding this, those tools are silently
    # dropped at the os.path.exists check below.
    file_template_kwds = _resolve_file_template_kwds(root_dir)

    for item in _iter_tool_items(tool_conf_source.parse_items()):
        if item.type == "tool_dir":
            dir_attr = item.get("dir")
            if not dir_attr:
                continue
            dir_attr = string.Template(dir_attr).safe_substitute(file_template_kwds)
            if os.path.isabs(dir_attr):
                directory = dir_attr
            else:
                directory = os.path.join(resolved_tool_path, dir_attr)
            recursive = str(item.get("recursive", "true")).lower() != "false"
            for candidate in _walk_tool_dir(os.path.normpath(directory), recursive):
                if not _looks_like_a_tool(candidate):
                    continue
                yield DiscoveredTool(
                    path=candidate,
                    tool_conf=config_filename,
                    tool_path=resolved_tool_path,
                    guid=None,
                    is_shed_tool=is_shed_conf,
                )
            continue

        tool_file = item.get("file")
        if not tool_file:
            continue

        tool_file = string.Template(tool_file).safe_substitute(file_template_kwds)

        # Resolve tool file path
        if os.path.isabs(tool_file):
            tool_path_abs = tool_file
        else:
            tool_path_abs = os.path.join(resolved_tool_path, tool_file)

        # Normalize path
        tool_path_abs = os.path.normpath(tool_path_abs)

        if not os.path.exists(tool_path_abs):
            log.debug(f"Tool file does not exist: {tool_path_abs}")
            continue

        yield DiscoveredTool(
            path=tool_path_abs,
            tool_conf=config_filename,
            tool_path=resolved_tool_path,
            guid=item.get("guid"),
            is_shed_tool=is_shed_conf,
            hidden=str(item.get("hidden", "false")).lower() == "true",
        )


def discover_tools(
    config: "GalaxyAppConfiguration",
    include_bundled: bool = True,
) -> Iterator[DiscoveredTool]:
    """
    Discover all tools from Galaxy configuration.

    This reads all tool configuration files and yields information about
    each discovered tool file.

    Args:
        config: Galaxy configuration object.
        include_bundled: Whether to include bundled tools from lib/galaxy/tools/bundled.

    Yields:
        DiscoveredTool objects for each tool found.
    """
    root_dir = getattr(config, "root", None)
    seen_paths: set = set()

    # Discover from all tool config files
    for config_filename in get_tool_configs(config):
        for tool in discover_tools_from_config(config_filename, root_dir):
            if tool.path not in seen_paths:
                seen_paths.add(tool.path)
                yield tool

    # Include bundled tools if requested
    if include_bundled and root_dir:
        bundled_dir = Path(root_dir) / "lib" / "galaxy" / "tools" / "bundled"
        if bundled_dir.exists():
            for xml_file in bundled_dir.rglob("*.xml"):
                path_str = str(xml_file)
                # Skip macro files and already-seen files
                if path_str in seen_paths:
                    continue
                if "macro" in xml_file.name.lower():
                    continue
                # Quick check if it's a tool file
                try:
                    with open(xml_file) as f:
                        content = f.read(500)  # Read just enough to check
                    if "<tool" in content:
                        seen_paths.add(path_str)
                        yield DiscoveredTool(
                            path=path_str,
                            tool_conf="bundled",
                            tool_path=str(bundled_dir),
                            is_shed_tool=False,
                        )
                except Exception:
                    pass


def discover_tool_files(
    config: "GalaxyAppConfiguration",
    include_bundled: bool = True,
) -> list[str]:
    """
    Get a list of all tool file paths from Galaxy configuration.

    This is a convenience function that returns just the paths.

    Args:
        config: Galaxy configuration object.
        include_bundled: Whether to include bundled tools.

    Returns:
        List of absolute paths to tool files.
    """
    return [tool.path for tool in discover_tools(config, include_bundled)]


__all__ = (
    "DiscoveredTool",
    "discover_tools",
    "discover_tools_from_config",
    "discover_tool_files",
    "get_tool_configs",
)
