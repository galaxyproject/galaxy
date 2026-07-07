"""
Tool discovery utilities.

Walks Galaxy's tool configuration files to enumerate every ``<tool>`` referenced
from any tool_conf without booting a full ``ToolBox``. Used by the populator
(``galaxy.tools.source_store.populator``) and by callers that need to compare
on-disk confs against the indexed tool set (cold-start auto-populate,
``reset_shed_tools``).
"""

import logging
import os
import string
from collections.abc import (
    Iterable,
    Iterator,
)
from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
from typing import (
    TYPE_CHECKING,
)

from galaxy.model import _get_datatypes_registry
from galaxy.tool_util.loader_directory import (
    looks_like_a_tool,
    looks_like_a_tool_xml,
)
from galaxy.tool_util.toolbox.base import (
    resolve_tool_path,
    walk_tool_directories,
)
from galaxy.tool_util.toolbox.parser import (
    get_toolbox_parser,
    ToolConfItem,
    ToolConfSection,
)
from galaxy.tools import MODEL_TOOLS_PATH
from galaxy.tools.special_tools import hidden_lib_tool_paths

if TYPE_CHECKING:
    from galaxy.config import GalaxyAppConfiguration

log = logging.getLogger(__name__)


@dataclass
class DiscoveredTool:
    """Information about a discovered tool file."""

    path: str  # Absolute path to tool file
    tool_conf: str  # Path to the tool_conf file that referenced this tool
    tool_path: str | None  # The tool_path from the tool_conf
    guid: str | None = None  # GUID for shed tools
    is_shed_tool: bool = False
    # Shed conf ``<tool>`` child elements. The populator keys shed entries
    # by guid and stamps these on the index entry, so shed stubs answer
    # repository metadata without materialising — mirroring what the eager
    # walk reads via ``get_tool_repository_from_xml_item``.
    tool_shed: str | None = None
    repository_name: str | None = None
    repository_owner: str | None = None
    installed_changeset_revision: str | None = None
    # Conf-level ``hidden="true"`` on the ``<tool>`` element (NOT the XML
    # body's ``<tool hidden="true">`` — that's already on the parsed source).
    # ToolBox._load_tool_tag_set forces ``tool.hidden = True`` when this is
    # set; index consumers need the same flag to reproduce
    # ``hidden_tool_versions`` in /api/tools/{id}.
    hidden: bool = False
    # Conf-level ``labels="a,b"`` on the ``<tool>`` element. Same population
    # ownership as ``hidden`` above: parsed once at populator time so the
    # toolbox doesn't have to re-discover them in a post-walk sync.
    labels: list[str] = field(default_factory=list)
    # Parent ``<section id="..." name="...">`` of this tool, if any; the
    # populator stamps these onto ``ToolIndexEntry``.
    section_id: str | None = None
    section_name: str | None = None


def _iter_tool_items(
    items: Iterable[ToolConfItem],
    parent_section: ToolConfSection | None = None,
) -> Iterator[tuple[ToolConfItem, ToolConfSection | None]]:
    """
    Recursively iterate over tool items, including those nested in sections.

    Yields ``(item, parent_section)`` pairs for each ``tool`` and ``tool_dir``
    entry. ``parent_section`` is the immediate enclosing ``ToolConfSection`` or
    ``None`` for top-level items. ``tool_dir`` items reference an on-disk
    directory rather than a single file; the caller is responsible for walking
    the directory.
    """
    for item in items:
        if item.type in ("tool", "tool_dir"):
            yield item, parent_section
        elif isinstance(item, ToolConfSection):
            yield from _iter_tool_items(item.items, parent_section=item)


def _walk_tool_dir(directory: str, recursive: bool) -> Iterator[str]:
    """Yield candidate tool file paths under ``directory`` via the same
    ``walk_tool_directories`` walk that ``ToolBox.__watch_directory`` uses.
    Filtering against ``looks_like_a_tool`` is the caller's responsibility.
    """
    if not os.path.isdir(directory):
        log.debug(f"tool_dir does not exist: {directory}")
        return
    for _dirpath, files in walk_tool_directories(directory, recursive):
        yield from files


def discover_tools_from_config(
    config_filename: str,
    default_tool_path: str | None = None,
    enable_beta_formats: bool = False,
) -> Iterator[DiscoveredTool]:
    """
    Discover all tools from a single tool configuration file.

    Args:
        config_filename: Path to a tool_conf.xml or similar file.
        default_tool_path: Directory tool files are relative to when the conf
            doesn't set ``tool_path`` — same fallback the toolbox applies
            (``config.tool_path``).

    Yields:
        DiscoveredTool objects for each tool found.
    """
    if not os.path.exists(config_filename):
        log.debug(f"Tool config file does not exist: {config_filename}")
        return

    try:
        tool_conf_source = get_toolbox_parser(config_filename)
    except Exception as e:
        log.error(f"Failed to parse tool config {config_filename}: {e}")
        return

    tool_path = tool_conf_source.parse_tool_path()
    resolved_tool_path = resolve_tool_path(tool_path, config_filename, default_tool_path)
    is_shed_conf = tool_conf_source.is_shed_tool_conf()

    # Match what AbstractToolBox._path_template_kwds does for ToolBox: tool
    # confs may reference Galaxy-internal tool files via ``${model_tools_path}``
    # (e.g. ``<tool file="${model_tools_path}/apply_rules.xml" />`` in
    # tool_conf.xml.sample). Without expanding this, those tools are silently
    # dropped at the os.path.exists check below.
    file_template_kwds = {"model_tools_path": MODEL_TOOLS_PATH}

    for item, section in _iter_tool_items(tool_conf_source.parse_items()):
        section_id = section.get("id") if section is not None else None
        section_name = section.get("name") if section is not None else None
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
                if not looks_like_a_tool(candidate, enable_beta_formats=enable_beta_formats):
                    continue
                yield DiscoveredTool(
                    path=candidate,
                    tool_conf=config_filename,
                    tool_path=resolved_tool_path,
                    guid=None,
                    is_shed_tool=is_shed_conf,
                    section_id=section_id,
                    section_name=section_name,
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

        tool_shed = repository_name = repository_owner = installed_changeset_revision = None
        if is_shed_conf and item.elem is not None:
            tool_shed = item.elem.findtext("tool_shed")
            repository_name = item.elem.findtext("repository_name")
            repository_owner = item.elem.findtext("repository_owner")
            installed_changeset_revision = item.elem.findtext("installed_changeset_revision")

        yield DiscoveredTool(
            path=tool_path_abs,
            tool_conf=config_filename,
            tool_path=resolved_tool_path,
            guid=item.get("guid"),
            is_shed_tool=is_shed_conf,
            hidden=str(item.get("hidden", "false")).lower() == "true",
            labels=list(item.labels or ()),
            section_id=section_id,
            section_name=section_name,
            tool_shed=tool_shed,
            repository_name=repository_name,
            repository_owner=repository_owner,
            installed_changeset_revision=installed_changeset_revision,
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
    root_dir = config.root
    seen_paths: set = set()

    # Discover from all tool config files
    for config_filename in config.all_tool_config_files():
        for tool in discover_tools_from_config(config_filename, config.tool_path, config.enable_beta_tool_formats):
            if tool.path not in seen_paths:
                seen_paths.add(tool.path)
                yield tool

    # Include bundled tools if requested
    if include_bundled and root_dir:
        bundled_dir = Path(root_dir) / "lib" / "galaxy" / "tools" / "bundled"
        if bundled_dir.exists():
            for xml_file in bundled_dir.rglob("*.xml"):
                path_str = str(xml_file)
                if path_str in seen_paths or not looks_like_a_tool_xml(path_str):
                    continue
                seen_paths.add(path_str)
                yield DiscoveredTool(
                    path=path_str,
                    tool_conf="bundled",
                    tool_path=str(bundled_dir),
                    is_shed_tool=False,
                )

    # Galaxy-internal "hidden lib" tools (``set_metadata_tool``, the
    # ``imp_exp`` history exporters, ``data_fetch``). They're loaded after
    # boot via ``toolbox.load_hidden_lib_tool`` rather than from any
    # tool_conf, so the conf walk above misses them; index them too.
    for path in hidden_lib_tool_paths():
        if path in seen_paths or not os.path.exists(path):
            continue
        seen_paths.add(path)
        yield DiscoveredTool(
            path=path,
            tool_conf="<hidden-lib>",
            tool_path=os.path.dirname(path),
            is_shed_tool=False,
        )

    # Datatype converters. ``Registry.load_datatype_converters`` calls
    # ``toolbox.load_tool`` per converter after boot, so converters
    # belong in the index. Use the active datatypes registry (populated by
    # ``set_datatypes_registry`` at app boot / CLI startup) as the
    # source of truth — same list that ``load_datatype_converters``
    # iterates, so we never index a converter the registry won't load
    # and vice versa.
    try:
        registry = _get_datatypes_registry()
        if registry is not None and registry.converters_path:
            for tool_config, _src_dt, _tgt_dt in registry.converters:
                path = os.path.normpath(os.path.join(registry.converters_path, tool_config))
                if path in seen_paths or not os.path.exists(path):
                    continue
                seen_paths.add(path)
                yield DiscoveredTool(
                    path=path,
                    tool_conf="<converter>",
                    tool_path=registry.converters_path,
                    is_shed_tool=False,
                )
    except Exception as e:
        log.debug("Failed to enumerate datatype converters: %s", e)


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
)
