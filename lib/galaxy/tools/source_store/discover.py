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
    Collection,
    Iterable,
    Iterator,
)
from concurrent.futures import ThreadPoolExecutor
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
from galaxy.util import (
    listify,
    parse_xml,
)

if TYPE_CHECKING:
    from galaxy.config import GalaxyAppConfiguration

log = logging.getLogger(__name__)

# Sentinel ``tool_conf`` for datatype-converter discoveries — they have no
# panel conf; the registry loads them after boot via ``load_tool``.
CONVERTER_TOOL_CONF = "<converter>"
BUNDLED_TOOL_CONF = "<bundled>"
HIDDEN_LIB_TOOL_CONF = "<hidden-lib>"
ADHOC_TOOL_CONF = "<adhoc>"
NON_PANEL_TOOL_CONFS = frozenset(
    {
        ADHOC_TOOL_CONF,
        BUNDLED_TOOL_CONF,
        CONVERTER_TOOL_CONF,
        HIDDEN_LIB_TOOL_CONF,
    }
)


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
    # ``<data_manager id="...">`` conf id for tools referenced from data
    # manager configs — may differ from the tool XML id, and the registry
    # is keyed by it.
    data_manager_id: str | None = None
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


def _resolve_tool_dir(item: ToolConfItem, resolved_tool_path: str) -> str | None:
    """Resolve a ``tool_dir`` conf item to an absolute directory path."""
    dir_attr = item.get("dir")
    if not dir_attr:
        return None
    dir_attr = string.Template(dir_attr).safe_substitute({"model_tools_path": MODEL_TOOLS_PATH})
    if not os.path.isabs(dir_attr):
        dir_attr = os.path.join(resolved_tool_path, dir_attr)
    return os.path.normpath(dir_attr)


def _tool_dir_recursive(item: ToolConfItem) -> bool:
    return str(item.get("recursive", "true")).lower() != "false"


def conf_tool_directories(config: "GalaxyAppConfiguration") -> list[tuple[str, bool]]:
    """Resolve every ``tool_dir`` conf entry to ``(directory, recursive)``.

    A ``tool_dir`` places tools on disk without naming them in any conf, so
    conf-content hashing alone can't see additions there — the freshness
    probe folds these directories' mtimes in on top of the conf contents.
    """
    out: list[tuple[str, bool]] = []
    for config_filename in config.all_tool_config_files():
        if not os.path.exists(config_filename):
            continue
        try:
            tool_conf_source = get_toolbox_parser(config_filename)
        except Exception as e:
            log.error(f"Failed to parse tool config {config_filename}: {e}")
            continue
        resolved_tool_path = resolve_tool_path(tool_conf_source.parse_tool_path(), config_filename, config.tool_path)
        for item, _section in _iter_tool_items(tool_conf_source.parse_items()):
            if item.type != "tool_dir":
                continue
            directory = _resolve_tool_dir(item, resolved_tool_path)
            if directory is not None:
                out.append((directory, _tool_dir_recursive(item)))
    return out


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
    parallel: int = 1,
) -> Iterator[DiscoveredTool]:
    """
    Discover all tools from a single tool configuration file.

    Args:
        config_filename: Path to a tool_conf.xml or similar file.
        default_tool_path: Directory tool files are relative to when the conf
            doesn't set ``tool_path`` — same fallback the toolbox applies
            (``config.tool_path``).
        parallel: Worker count for the per-tool existence checks. On network
            filesystems (CVMFS) each stat costs tens of ms, so a shed conf
            listing thousands of tools takes minutes checked serially; the
            populator threads its ``--parallel`` value through here.

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

    items = list(_iter_tool_items(tool_conf_source.parse_items()))

    # Pre-resolve every ``<tool file=...>`` path and run the existence checks
    # through a thread pool; the loop below then consumes the results in conf
    # document order.
    file_paths: dict[int, str] = {}
    for i, (item, _section) in enumerate(items):
        if item.type == "tool_dir":
            continue
        tool_file = item.get("file")
        if not tool_file:
            continue
        tool_file = string.Template(tool_file).safe_substitute(file_template_kwds)
        if not os.path.isabs(tool_file):
            tool_file = os.path.join(resolved_tool_path, tool_file)
        file_paths[i] = os.path.normpath(tool_file)
    unique_paths = list(set(file_paths.values()))
    if parallel > 1 and unique_paths:
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            exists_by_path = dict(zip(unique_paths, executor.map(os.path.exists, unique_paths)))
    else:
        exists_by_path = {path: os.path.exists(path) for path in unique_paths}

    for i, (item, section) in enumerate(items):
        section_id = section.get("id") if section is not None else None
        section_name = section.get("name") if section is not None else None
        if item.type == "tool_dir":
            directory = _resolve_tool_dir(item, resolved_tool_path)
            if directory is None:
                continue
            recursive = _tool_dir_recursive(item)
            for candidate in _walk_tool_dir(directory, recursive):
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

        tool_path_abs = file_paths.get(i)
        if tool_path_abs is None:
            continue

        if not exists_by_path[tool_path_abs]:
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


def _iter_data_manager_tools(config: "GalaxyAppConfiguration") -> Iterator[DiscoveredTool]:
    """Yield tool files referenced by data manager configs.

    Data manager tools are loaded via ``DataManagers`` -> ``toolbox.load_hidden_tool``
    rather than from a tool_conf, so the normal conf walk misses them.
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
            data_manager_id = dm_elem.get("id")
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
                # relative to the conf file for planemo-managed layouts.
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
                data_manager_id=data_manager_id,
            )


def discover_tools(
    config: "GalaxyAppConfiguration",
    include_bundled: bool = True,
    include_converters: bool = True,
    parallel: int = 1,
    only_confs: Collection[str] | None = None,
) -> Iterator[DiscoveredTool]:
    """
    Discover all tools from Galaxy configuration.

    This reads all tool configuration files and yields information about
    each discovered tool file.

    Args:
        config: Galaxy configuration object.
        include_bundled: Whether to include bundled tools from lib/galaxy/tools/bundled.
        include_converters: Whether to enumerate datatype converters. This needs
            the datatypes registry; it's off for targeted single-store populates,
            which never write the default store that converters route to.
        parallel: Worker count for per-tool existence checks (see
            :func:`discover_tools_from_config`).
        only_confs: When set, walk only these tool conf files. The per-tool
            existence checks are the expensive part of discovery on network
            filesystems, so callers that would drop a conf's tools anyway
            (routed to a read-only or untargeted store) skip its walk
            entirely rather than filter afterwards.

    Yields:
        DiscoveredTool objects for each tool found.
    """
    root_dir = config.root
    seen_paths: set = set()

    # Discover from all tool config files. A file referenced by several conf
    # items — top-level and again inside a section is a common layout in
    # multi-version confs — is a distinct panel placement per reference and
    # the eager walk places each one, so yield them all; the store layer is
    # content-addressed and absorbs the repeats. ``seen_paths`` still keeps
    # the bundled/hidden-lib/converter/data-manager sweeps below from
    # re-discovering conf tools.
    for config_filename in config.all_tool_config_files():
        if only_confs is not None and config_filename not in only_confs:
            continue
        for tool in discover_tools_from_config(
            config_filename, config.tool_path, config.enable_beta_tool_formats, parallel=parallel
        ):
            seen_paths.add(tool.path)
            yield tool

    # Include bundled tools if requested
    if include_bundled and root_dir:
        bundled_dir = Path(root_dir) / "lib" / "galaxy" / "tools" / "bundled"
        if bundled_dir.exists():
            for xml_file in bundled_dir.rglob("*.xml"):
                path_str = str(xml_file)
                relative_path = xml_file.relative_to(bundled_dir)
                configured_aliases = {
                    os.path.normpath(os.path.join(config.tool_path, relative_path)),
                    os.path.normpath(os.path.join(MODEL_TOOLS_PATH, relative_path)),
                }
                if seen_paths.intersection(configured_aliases) or not looks_like_a_tool_xml(path_str):
                    continue
                seen_paths.add(path_str)
                yield DiscoveredTool(
                    path=path_str,
                    tool_conf=BUNDLED_TOOL_CONF,
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
            tool_conf=HIDDEN_LIB_TOOL_CONF,
            tool_path=os.path.dirname(path),
            is_shed_tool=False,
        )

    # Data manager tools are loaded after boot and are not referenced from
    # ordinary tool_conf files.
    for dm_tool in _iter_data_manager_tools(config):
        if dm_tool.path in seen_paths or not os.path.exists(dm_tool.path):
            continue
        seen_paths.add(dm_tool.path)
        yield dm_tool

    # Datatype converters. ``Registry.load_datatype_converters`` calls
    # ``toolbox.load_tool`` per converter after boot, so converters
    # belong in the index. Use the active datatypes registry (populated by
    # ``set_datatypes_registry`` at app boot / CLI startup) as the
    # source of truth — same list that ``load_datatype_converters``
    # iterates, so we never index a converter the registry won't load
    # and vice versa.
    if include_converters:
        try:
            registry = _get_datatypes_registry()
            if registry.converters_path:
                for tool_config, _src_dt, _tgt_dt in registry.converters:
                    path = os.path.normpath(os.path.join(registry.converters_path, tool_config))
                    if path in seen_paths or not os.path.exists(path):
                        continue
                    seen_paths.add(path)
                    yield DiscoveredTool(
                        path=path,
                        tool_conf=CONVERTER_TOOL_CONF,
                        tool_path=registry.converters_path,
                        is_shed_tool=False,
                    )
        except Exception as e:
            log.error("Failed to enumerate datatype converters: %s", e)


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
