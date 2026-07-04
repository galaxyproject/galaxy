"""
Tool discovery utilities.

Walks Galaxy's tool configuration files to enumerate every ``<tool>`` referenced
from any tool_conf without booting a full ``ToolBox``. Used by the populator
(``galaxy.tool_source_store.populator``) and by callers that need to compare
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

from galaxy.tool_util.loader_directory import looks_like_a_tool
from galaxy.tool_util.toolbox.parser import (
    get_toolbox_parser,
    ToolConfItem,
    ToolConfSection,
)
from galaxy.util import (
    listify,
    parse_xml,
)

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
    # Conf-level ``hidden="true"`` on the ``<tool>`` element (NOT the XML
    # body's ``<tool hidden="true">`` — that's already on the parsed source).
    # ToolBox._load_tool_tag_set forces ``tool.hidden = True`` when this is
    # set; the lazy path needs the same flag to make ``hidden_tool_versions``
    # in /api/tools/{id} match the eager toolbox.
    hidden: bool = False
    # Conf-level ``labels="a,b"`` on the ``<tool>`` element. Same population
    # ownership as ``hidden`` above: parsed once at populator time so the
    # toolbox doesn't have to re-discover them in a post-walk sync.
    labels: list[str] = field(default_factory=list)
    # Parent ``<section id="..." name="...">`` of this tool, if any. The
    # populator stamps these onto ``ToolIndexEntry`` so the panel render in
    # ``LazyToolBox`` doesn't need a separate post-walk pass to find them.
    section_id: str | None = None
    section_name: str | None = None


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
    if config.tool_configs:
        configs.extend(config.tool_configs)

    # Ensure shed_tool_config_file is included if not already
    if config.shed_tool_config_file:
        if config.shed_tool_config_file not in configs:
            configs.append(config.shed_tool_config_file)

    # Include migrated_tools_config if present
    if config.migrated_tools_config:
        if config.migrated_tools_config not in configs:
            configs.append(config.migrated_tools_config)

    return configs


def _resolve_tool_path(tool_path: str | None, config_filename: str, root_dir: str | None = None) -> str:
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


def _resolve_file_template_kwds() -> dict[str, str]:
    """Resolve template variables that tool conf ``file=...`` attributes may use.

    Mirrors :py:meth:`galaxy.tools.ToolBox._path_template_kwds`.
    """
    # Local import: only a path constant is needed, and a module-level import
    # would pull the whole galaxy.tools package into every discover() caller.
    from galaxy.tools import MODEL_TOOLS_PATH

    return {"model_tools_path": MODEL_TOOLS_PATH}


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
    root_dir: str | None = None,
    enable_beta_formats: bool = False,
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
    file_template_kwds = _resolve_file_template_kwds()

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
        )


def _iter_data_manager_tools(config: "GalaxyAppConfiguration") -> Iterator[DiscoveredTool]:
    """Yield the tool files referenced by data manager configs.

    Data manager tools are loaded via ``DataManagers`` →
    ``toolbox.load_hidden_tool`` rather than from any tool_conf, so the conf
    walk misses them. Path and guid resolution mirror
    :meth:`galaxy.tools.data_manager.manager.DataManager._load_from_element`.
    """
    conf_files = [f for f in listify(config.data_manager_config_file or "") if f]
    if config.shed_data_manager_config_file:
        conf_files.append(config.shed_data_manager_config_file)
    for conf in conf_files:
        if not os.path.exists(conf):
            continue
        try:
            root = parse_xml(conf).getroot()
        except Exception as e:
            log.warning("Skipping data manager config %s: %s", conf, e)
            continue
        if root.tag != "data_managers":
            continue
        conf_tool_path = root.get("tool_path") or config.tool_path or "."
        for dm_elem in root.findall("data_manager"):
            tool_path = conf_tool_path
            path = dm_elem.get("tool_file")
            guid = None
            if path is None:
                tool_elem = dm_elem.find("tool")
                if tool_elem is None:
                    continue
                path = tool_elem.get("file")
                guid = tool_elem.get("guid")
                shed_conf_file = dm_elem.get("shed_conf_file")
                if shed_conf_file and os.path.exists(shed_conf_file):
                    try:
                        shed_tool_path = get_toolbox_parser(shed_conf_file).parse_tool_path()
                        if shed_tool_path:
                            tool_path = shed_tool_path
                    except Exception as e:
                        log.warning("Could not resolve tool_path from %s: %s", shed_conf_file, e)
            if not path:
                continue
            resolved = os.path.abspath(os.path.join(tool_path, path))
            if not os.path.exists(resolved):
                # Mirror DataManagers.load_from_xml: fall back to resolving
                # relative to the conf file (planemo-managed layouts).
                fallback = os.path.abspath(os.path.join(os.path.dirname(conf), path))
                if os.path.exists(fallback):
                    resolved = fallback
                    tool_path = os.path.dirname(conf)
            yield DiscoveredTool(
                path=resolved,
                tool_conf=conf,
                tool_path=tool_path,
                guid=guid,
                is_shed_tool=guid is not None,
                # ``hidden`` stays False: eager loads these via
                # ``load_hidden_tool``, which only means "not in the panel"
                # — ``Tool.hidden`` remains falsy, and the flat
                # ``/api/tools?in_panel=false`` listing filters on it.
                # Panel absence is already guaranteed by the missing
                # ``panel_section_id``.
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
    for config_filename in get_tool_configs(config):
        for tool in discover_tools_from_config(config_filename, root_dir, config.enable_beta_tool_formats):
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

    # Galaxy-internal "hidden lib" tools (``set_metadata_tool``, the
    # ``imp_exp`` history exporters, ``data_fetch``). They're loaded after
    # boot via ``toolbox.load_hidden_lib_tool`` rather than from any
    # tool_conf, so the conf walk above misses them. Indexing them here
    # lets ``LazyToolBox.create_tool`` resolve them on lookup without an
    # ad-hoc fall-through.
    try:
        from galaxy.tools.special_tools import hidden_lib_tool_paths

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
    except Exception as e:
        log.debug("Failed to enumerate hidden-lib tool paths: %s", e)

    # Data manager tools — loaded post-boot via ``DataManagers``, not from
    # any tool_conf.
    for dm_tool in _iter_data_manager_tools(config):
        if dm_tool.path in seen_paths or not os.path.exists(dm_tool.path):
            continue
        seen_paths.add(dm_tool.path)
        yield dm_tool

    # Datatype converters. ``Registry.load_datatype_converters`` calls
    # ``toolbox.load_tool`` per converter after boot; strict
    # ``LazyToolBox.create_tool`` raises on miss, so they need to be in
    # the index. Use the active datatypes registry (populated by
    # ``set_datatypes_registry`` at app boot / CLI startup) as the
    # source of truth — same list that ``load_datatype_converters``
    # iterates, so we never index a converter the registry won't load
    # and vice versa.
    try:
        from galaxy.model import _get_datatypes_registry

        registry = _get_datatypes_registry()
        if registry is not None and getattr(registry, "converters_path", None):
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
    "get_tool_configs",
)
