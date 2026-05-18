"""
Lazy ToolBox - On-demand tool loading with LRU caching.

This module provides a LazyToolBox that extends ToolBox but keeps only a
lightweight index in memory and loads full Tool objects on-demand with
LRU eviction.
"""

import hashlib
import logging
import os
import string
import threading
from datetime import datetime
from typing import (
    Any,
    Literal,
    Optional,
    overload,
    TYPE_CHECKING,
    Union,
)
from uuid import UUID

from cachetools import LRUCache

from galaxy.tool_source_store import (
    StoredToolSource,
    ToolSourceStore,
)
from galaxy.tool_source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tool_util.id_util import (
    extract_short_id_from_guid,
    extract_tool_id_from_file,
)
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.toolbox.base import DynamicToolConfDict
from galaxy.tool_util.toolbox.filters import FilterFactory
from galaxy.tool_util.toolbox.lineages import LineageMap
from galaxy.tool_util.toolbox.panel import (
    ToolPanelElements,
    ToolSection,
)
from galaxy.tool_util.toolbox.views.edam import (
    EdamPanelMode,
    EdamToolPanelView,
)
from galaxy.tool_util.toolbox.views.interface import (
    ToolPanelView,
    ToolPanelViewModel,
    ToolPanelViewModelType,
)
from galaxy.tool_util.toolbox.views.sources import StaticToolBoxViewSources
from galaxy.util import listify
from . import (
    create_tool_from_source,
    ToolBox,
)

if TYPE_CHECKING:
    from galaxy.app import UniverseApplication
    from galaxy.model import User
    from galaxy.tools import Tool

log = logging.getLogger(__name__)


class DefaultToolPanelView(ToolPanelView):
    """Default tool panel view for LazyToolBox."""

    def __init__(self, toolbox: "LazyToolBox"):
        self.toolbox = toolbox

    def apply_view(self, base_tool_panel, toolbox_registry):
        return self.toolbox._tool_panel

    def to_model(self) -> ToolPanelViewModel:
        return ToolPanelViewModel(
            id="default",
            name="Full Tool Panel",
            description="Galaxy's fully configured toolbox panel.",
            model_class="DefaultToolPanelView",
            view_type=ToolPanelViewModelType.default_type,
            searchable=True,
        )


class _LazyToolsByIdView:
    """Mapping wrapper over ``LazyToolBox._tools_by_id`` that lazy-loads on access.

    ``__getitem__`` returns the materialised Tool, calling ``get_tool`` when the
    underlying dict has a ``None`` placeholder. Provides the bare slice of
    ``Mapping`` that callers in the codebase actually use (``in``, ``[]``,
    ``get``, iteration, ``len``).
    """

    def __init__(self, toolbox: "LazyToolBox") -> None:
        self._toolbox = toolbox

    def _materialised(self, tool_id: str) -> Optional["Tool"]:
        tool = self._toolbox._tools_by_id.get(tool_id)
        if tool is not None:
            return tool
        # Placeholder hit — go through ``get_tool`` which honors the index.
        return self._toolbox.get_tool(tool_id=tool_id)

    def __getitem__(self, tool_id: str) -> "Tool":
        tool = self._materialised(tool_id)
        if tool is None:
            raise KeyError(tool_id)
        return tool

    def get(self, tool_id: str, default: Any = None) -> Any:
        try:
            return self.__getitem__(tool_id)
        except KeyError:
            return default

    def __contains__(self, tool_id: object) -> bool:
        return tool_id in self._toolbox._tools_by_id

    def __iter__(self):
        return iter(self._toolbox._tools_by_id)

    def __len__(self) -> int:
        return len(self._toolbox._tools_by_id)

    def keys(self):
        return self._toolbox._tools_by_id.keys()

    def values(self):
        for tool_id in self._toolbox._tools_by_id:
            tool = self._materialised(tool_id)
            if tool is not None:
                yield tool

    def items(self):
        for tool_id in self._toolbox._tools_by_id:
            tool = self._materialised(tool_id)
            if tool is not None:
                yield tool_id, tool

    def copy(self) -> dict:
        """Return a shallow copy as a regular dict.

        Used by ``galaxy.tool_util.deps.containers.ContainerFinder.find_best_container_description``
        (via ``copy.copy`` on the registry) and similar places that expect a
        plain dict. Materialise every entry — callers iterating the copy
        expect real Tool objects, not ``None`` placeholders.
        """
        return dict(self.items())


class LazyToolBox(ToolBox):
    """
    ToolBox that loads tools on-demand from the tool source store.

    Extends ToolBox but overrides initialization to avoid loading all tools
    at startup. Keeps a lightweight index in memory for API responses,
    but only loads full Tool objects when needed for execution or form building.
    """

    def __init__(
        self,
        config_filenames: list[str],
        tool_root_dir: str,
        app: "UniverseApplication",
        tool_source_store: Optional[ToolSourceStore],
        cache_size: int = 500,
        save_integrated_tool_panel: bool = True,
    ) -> None:
        """
        Initialize the lazy toolbox.

        Args:
            config_filenames: Tool configuration files (used for panel structure).
            tool_root_dir: Root directory for tools.
            app: Galaxy application instance.
            tool_source_store: The tool source store to load from.
            cache_size: Maximum number of Tool objects to cache in memory.
            save_integrated_tool_panel: Whether to save integrated tool panel.
        """
        # Store references before any initialization
        self._store = tool_source_store
        self._tool_object_cache: LRUCache = LRUCache(maxsize=cache_size)
        self._cache_lock = threading.RLock()
        self._reload_count = 0

        # Initialize core attributes that AbstractToolBox.__init__ would set
        # We do this manually to avoid loading all tools
        self._init_lazy_toolbox(
            config_filenames=config_filenames,
            tool_root_dir=tool_root_dir,
            app=app,
            save_integrated_tool_panel=save_integrated_tool_panel,
        )

        # Load tool index from store
        self._tool_index: Optional[ToolIndex] = None
        self._load_index_from_store()

        # Populate _tools_by_id with stub entries from index
        # This allows has_tool() and similar checks to work without loading
        self._populate_tool_registry_from_index()

        log.info(f"LazyToolBox initialized with {len(self._tools_by_id)} tools (cache_size={cache_size})")
        self._warn_if_index_misses_panel_tools()

    def _warn_if_index_misses_panel_tools(self) -> None:
        """Warn loudly if the index doesn't cover every tool the operator configured.

        ``_tool_section_map`` is built from the same tool confs that the bootstrap
        walks. When ``/api/tools`` short-circuits to the index, panel-known ids
        that are missing from the index disappear from the API response — the
        regression that caused 316 ``GALAXY_TEST_REQUIRE_ALL_NEEDED_TOOLS`` API
        failures on the lazy-toolbox-atomic branch. Emit a single WARNING with
        a sample so the cause is visible at boot.
        """
        if self._tool_index is None:
            return
        index_ids = set(self._tool_index.entries.keys())
        panel_ids = set(self._tool_section_map.keys())
        missing = panel_ids - index_ids
        if missing:
            sample = sorted(missing)[:20]
            log.warning(
                "LazyToolBox index is missing %d tool id(s) referenced by tool confs "
                "(sample: %s). /api/tools?in_panel=False will under-report. "
                "Check earlier 'Bootstrap skipping' / 'Error building index entry' warnings.",
                len(missing),
                ", ".join(sample),
            )

    def _init_lazy_toolbox(
        self,
        config_filenames: list[str],
        tool_root_dir: str,
        app: "UniverseApplication",
        save_integrated_tool_panel: bool,
    ) -> None:
        """
        Initialize toolbox attributes without loading tools.

        This replicates the essential parts of AbstractToolBox.__init__
        without calling _init_tools_from_configs which loads all tools.
        """
        # From ToolBox.__init__ — imported lazily to avoid circular import via
        # galaxy.tools -> galaxy.tool_util.fetcher -> galaxy.tools.
        from galaxy.tool_util.fetcher import ToolLocationFetcher

        self.tool_location_fetcher = ToolLocationFetcher()
        self._tools_loaded_from_store = 0
        self._tools_parsed_from_file = 0

        # From AbstractToolBox.__init__
        self._dynamic_tool_confs: list[DynamicToolConfDict] = []
        self._tools_by_id: dict[str, Tool] = {}
        self._tools_by_uuid: dict[UUID, Tool] = {}
        self._tool_versions_by_id: dict[str, dict[Union[str, None], Tool]] = {}
        self._tools_by_old_id: dict[str, list[Tool]] = {}
        self._workflows_by_id: dict[str, Any] = {}
        self._tool_to_dict_cache: dict[str, dict[str, Any]] = {}
        self._tool_to_dict_cache_admin: dict[str, dict[str, Any]] = {}
        self._tool_panel = ToolPanelElements()
        self._index = 0
        self.data_manager_tools: dict[str, Tool] = {}
        self._lineage_map = LineageMap(app)

        # Tool root dir handling from ToolBox
        if tool_root_dir == "./tools":
            tool_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "bundled"))
        self._tool_root_dir = tool_root_dir
        self.app = app

        # Initialize integrated tool panel (from ManagesIntegratedToolPanelMixin)
        self._init_integrated_tool_panel(app.config)

        # Watchers and filters
        self._tool_watcher = self.app.watchers.tool_watcher
        self._tool_config_watcher = self.app.watchers.tool_config_watcher
        self._filter_factory = FilterFactory(self)
        self._tool_tag_manager = self.tool_tag_manager()

        # Initialize panel views
        view_sources = StaticToolBoxViewSources(
            view_directories=app.config.panel_views_dir,
            view_dicts=app.config.panel_views,
        )
        # Store default panel view - we override _default_panel_view() method to use this
        self._default_panel_view_name = app.config.default_panel_view
        self._setup_panel_views(view_sources)

        # Initialize dependency manager
        self._init_dependency_manager()

        # Load panel structure from config files (sections, labels)
        # but don't load the actual tools
        self._init_panel_structure_from_configs(config_filenames)

        # Load tool panel views (required for panel_has_tool checks)
        if self.app.name == "galaxy":
            self._load_tool_panel_views()

        if save_integrated_tool_panel:
            self._save_integrated_tool_panel()

    def _default_panel_view(self, trans):
        """
        Override AbstractToolBox._default_panel_view to avoid name-mangled attribute access.

        Returns the default panel view for the given transaction, respecting
        per-host configuration if available.
        """
        config = self.app.config
        if hasattr(config, "config_value_for_host"):
            config_value = config.config_value_for_host("default_panel_view", trans.host)
        else:
            config_value = getattr(config, "default_panel_view", None)
        return config_value or self._default_panel_view_name

    def _setup_panel_views(self, view_sources) -> None:
        """Set up tool panel views."""
        tool_panel_views_list: list[ToolPanelView] = [DefaultToolPanelView(self)]

        for edam_view in listify(self.app.config.edam_panel_views):
            mode = EdamPanelMode[edam_view]
            tool_panel_views_list.append(EdamToolPanelView(self.app.datatypes_registry.edam, mode=mode))

        if view_sources is not None:
            # Lazy import: only needed when there are static panel views to register.
            from galaxy.tool_util.toolbox.views.static import StaticToolPanelView

            for definition in view_sources.get_definitions():
                tool_panel_views_list.append(StaticToolPanelView(definition))

        self._tool_panel_views = {}
        for tool_panel_view in tool_panel_views_list:
            self._tool_panel_views[tool_panel_view.to_model().id] = tool_panel_view

        self._tool_panel_view_rendered: dict[str, ToolPanelElements] = {}

    def _init_panel_structure_from_configs(self, config_filenames: list[str]) -> None:
        """
        Load panel structure (sections, labels) from config files.

        This parses the tool configs to get the panel layout and builds
        a mapping of tool_id -> section info for use with the index.
        """
        # Lazy import: only the panel-loading code path needs this parser.
        from galaxy.tool_util.toolbox.parser import get_toolbox_parser

        # Map tool_id -> (section_id, section_name)
        self._tool_section_map: dict[str, tuple] = {}

        config_filenames = listify(config_filenames)

        for config_filename in config_filenames:
            if not self.can_load_config_file(config_filename):
                continue
            try:
                tool_conf_source = get_toolbox_parser(config_filename)
                tool_path = tool_conf_source.parse_tool_path()
                if not tool_path:
                    tool_path = self._tool_root_dir
                else:
                    tool_conf_dir = os.path.dirname(config_filename)
                    tool_path_vars = {"tool_conf_dir": tool_conf_dir}
                    tool_path = string.Template(tool_path).safe_substitute(tool_path_vars)

                parsing_shed_tool_conf = tool_conf_source.is_shed_tool_conf()

                for item in tool_conf_source.parse_items():
                    try:
                        item_type = getattr(item, "type", None)
                        if item_type == "section":
                            section_id = item.get("id")
                            section_name = item.get("name", section_id)
                            section_dict = {
                                "id": section_id,
                                "name": section_name,
                                "version": item.get("version", ""),
                            }
                            if section_id and section_id not in self._tool_panel:
                                section = ToolSection(section_dict)
                                self._tool_panel.append_section(section_id, section)

                            # Extract tools in this section
                            if section_id:
                                self._extract_tools_from_section(item, section_id, section_name, tool_path)

                        elif item_type == "label":
                            label_id = item.get("id")
                            label_text = item.get("text", "")
                            if label_id and label_id not in self._tool_panel:
                                # Lazy import: only needed when a label element is encountered.
                                from galaxy.tool_util.toolbox.panel import ToolSectionLabel

                                label = ToolSectionLabel({"id": label_id, "text": label_text})
                                self._tool_panel[f"label_{label_id}"] = label

                        elif item_type == "tool":
                            # Tool at root level (no section). sample_tool_conf.xml
                            # ships some tools both inside a ``<section>`` and at
                            # root level; we don't want the root-level pass to
                            # clobber the section assignment we recorded a few
                            # iterations earlier. Only register if we haven't
                            # already seen this tool with a non-empty section.
                            tool_id = self._extract_tool_id_from_item(item, tool_path)
                            if tool_id:
                                existing = self._tool_section_map.get(tool_id)
                                if existing is None or existing[0] is None:
                                    self._tool_section_map[tool_id] = (None, None)

                        elif item_type == "tool_dir":
                            # ``<tool_dir dir="...">`` registers every tool file under
                            # the directory. Mirror what ToolBox._load_tooldir_tag_set
                            # does so the panel map matches the index after bootstrap.
                            self._extract_tools_from_tool_dir(item, tool_path, None, None)
                    except Exception as e:
                        log.debug(f"Error processing item in {config_filename}: {e}")

                if parsing_shed_tool_conf:
                    if os.access(config_filename, os.W_OK):
                        shed_tool_conf_dict = dict(
                            config_filename=config_filename,
                            tool_path=tool_path,
                            config_elems=[],
                        )
                        self._dynamic_tool_confs.append(shed_tool_conf_dict)

            except FileNotFoundError:
                log.debug(f"Tool config file not found: {config_filename}")
            except Exception as e:
                log.warning(f"Error parsing tool config {config_filename}: {e}")

        log.info(f"Built tool section map with {len(self._tool_section_map)} entries")
        # Log some sample entries for debugging
        sample_entries = list(self._tool_section_map.items())[:5]
        for tool_id, (section_id, _section_name) in sample_entries:
            log.debug(f"  Section map sample: {tool_id} -> {section_id}")

    def _extract_tools_from_section(self, section_item, section_id: str, section_name: str, tool_path: str) -> None:
        """Extract tool IDs from a section and add to section map."""
        if not hasattr(section_item, "items"):
            return

        for sub_item in section_item.items:
            try:
                item_type = getattr(sub_item, "type", None)
                if item_type == "tool":
                    tool_id = self._extract_tool_id_from_item(sub_item, tool_path)
                    if tool_id:
                        self._tool_section_map[tool_id] = (section_id, section_name)
                elif item_type == "tool_dir":
                    self._extract_tools_from_tool_dir(sub_item, tool_path, section_id, section_name)
            except Exception as e:
                log.debug(f"Error extracting tool from section {section_id}: {e}")

    def _extract_tools_from_tool_dir(
        self,
        item,
        tool_path: str,
        section_id: Optional[str],
        section_name: Optional[str],
    ) -> None:
        """Walk a ``<tool_dir>`` directive and add every tool file's id to the panel map.

        Pre-existing logic only handled ``<tool file=...>`` items; tool_conf
        confs that point at a directory (e.g. ``<tool_dir dir="parameters/" />``
        in test/functional/tools/sample_tool_conf.xml) had every tool inside
        invisible to the panel section map — and to ``/api/tools`` once the
        index short-circuit was in play.
        """
        # Lazy import: same script-local helpers the bootstrap walk uses.
        scripts_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "..",
            "..",
            "..",
            "scripts",
            "tool_source",
        )
        scripts_dir = os.path.normpath(scripts_dir)
        import sys as _sys

        if scripts_dir not in _sys.path:
            _sys.path.insert(0, scripts_dir)
        try:
            from _discover import (
                _looks_like_a_tool,
                _walk_tool_dir,
            )
        except ImportError as e:
            log.debug(f"_extract_tools_from_tool_dir could not import discovery helpers: {e}")
            return

        dir_attr = item.get("dir")
        if not dir_attr:
            return
        dir_attr = string.Template(dir_attr).safe_substitute(self._file_template_kwds())
        directory = dir_attr if os.path.isabs(dir_attr) else os.path.join(tool_path, dir_attr)
        directory = os.path.normpath(directory)
        recursive = str(item.get("recursive", "true")).lower() != "false"

        for candidate in _walk_tool_dir(directory, recursive):
            if not _looks_like_a_tool(candidate):
                continue
            tool_id = extract_tool_id_from_file(candidate, max_read=2000)
            if not tool_id:
                tool_id = self._extract_yaml_tool_id(candidate)
            if not tool_id:
                tool_id = os.path.splitext(os.path.basename(candidate))[0]
            if tool_id:
                self._tool_section_map[tool_id] = (section_id, section_name)

    def _seed_lineage_for_tool(self, tool_id: str, versions: list[str]) -> None:
        """Register every indexed version on this tool's ToolLineage."""
        from galaxy.tool_util.toolbox.lineages.interface import ToolLineage
        from galaxy.util.tool_version import remove_version_from_guid

        if not versions:
            return
        lineage_map = self._lineage_map.lineage_map
        versionless = remove_version_from_guid(tool_id)
        # Mirror LineageMap.register: a single ToolLineage is shared between
        # the versionless id and the version-bearing id.
        lineage = lineage_map.get(versionless) if versionless else None
        if lineage is None:
            lineage = lineage_map.get(tool_id)
        if lineage is None:
            lineage = ToolLineage(tool_id)
        for version in versions:
            lineage.register_version(version)
        lineage_map[tool_id] = lineage
        if versionless and versionless not in lineage_map:
            lineage_map[versionless] = lineage

    @staticmethod
    def _extract_yaml_tool_id(path: str) -> Optional[str]:
        """Cheap YAML ``id:`` extractor — avoids importing yaml just for this.

        ``extract_tool_id_from_file`` only handles XML; without a YAML reader
        the panel section map ends up with the *filename* for YAML tools,
        which mismatches the actual ``id:`` field in the YAML body
        (e.g. ``gx_data_collection_any.yml`` has ``id: gx_data_collection_any_y``)
        and produces spurious "missing from index" warnings.
        """
        ext = os.path.splitext(path)[1].lower()
        if ext not in (".yml", ".yaml"):
            return None
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("id:"):
                        value = line.split(":", 1)[1].strip()
                        # Strip surrounding quotes if present.
                        if value and value[0] in ("'", '"') and value[-1] == value[0]:
                            value = value[1:-1]
                        return value or None
                    if line.startswith(("inputs:", "outputs:", "command:", "shell_command:")):
                        # Past the header section without finding an id.
                        return None
        except OSError:
            return None
        return None

    def _extract_tool_id_from_item(self, item, tool_path: str) -> Optional[str]:
        """Extract tool ID from a tool item - either from guid or by parsing the file."""
        # For shed tools, use the guid directly
        guid = item.get("guid")
        if guid:
            return guid

        # For regular tools, we need to get the ID from the file attribute
        # and optionally parse the tool XML to get the actual ID
        tool_file = item.get("file")
        if not tool_file:
            return None

        # Tool confs ship with template variables in ``file=...`` (see
        # tool_conf.xml.sample which uses ``${model_tools_path}``). Without
        # expansion the path doesn't exist, ``extract_tool_id_from_file``
        # silently fails, and we fall back to the filename as the panel id —
        # which is wrong for tools whose actual XML id starts with
        # ``__INTERNAL__`` (e.g. ``build_list.xml`` parses to ``__BUILD_LIST__``).
        tool_file = string.Template(tool_file).safe_substitute(self._file_template_kwds())

        # Try to extract tool ID from file
        if os.path.isabs(tool_file):
            tool_path_full = tool_file
        else:
            tool_path_full = os.path.join(tool_path, tool_file)
        tool_id = extract_tool_id_from_file(tool_path_full, max_read=2000)
        if tool_id:
            return tool_id

        # YAML tools (``class: GalaxyUserTool`` / ``class: GalaxyTool``) have an
        # ``id:`` field that ``extract_tool_id_from_file`` doesn't recognize —
        # fall through to the YAML reader before the filename fallback so the
        # panel section map agrees with the index.
        tool_id = self._extract_yaml_tool_id(tool_path_full)
        if tool_id:
            return tool_id

        # Fall back to using filename without extension as ID hint
        return os.path.splitext(os.path.basename(tool_file))[0]

    def _file_template_kwds(self) -> dict[str, str]:
        """Template variables for substituting into ``<tool file=...>`` paths.

        Mirrors :py:meth:`galaxy.tools.ToolBox._path_template_kwds`.
        """
        # Lazy import: avoids pulling galaxy.tools at module load time.
        from galaxy.tools import MODEL_TOOLS_PATH

        return {"model_tools_path": MODEL_TOOLS_PATH}

    def _load_index_from_store(self) -> None:
        """Load the tool index from store."""
        log.debug("Loading tool index from store...")
        if self._store is None:
            log.info("No tool source store configured")
            self._tool_index = ToolIndex()
            return
        self._tool_index = self._store.load_index()

        if self._tool_index is None or len(self._tool_index.entries) == 0:
            # Check if store has tools but index is missing/empty
            stored_hashes = list(self._store.list_all())
            if stored_hashes:
                log.info(f"Index empty but store has {len(stored_hashes)} tools - rebuilding index...")
                self._rebuild_index_from_store(stored_hashes)
            else:
                # Empty store + empty index — first lazy boot. Walk every
                # configured tool conf and populate the default store so the
                # toolbox is non-empty without requiring an explicit
                # populate_store.py run.
                log.info("Empty tool source store; bootstrapping from tool configs...")
                self._bootstrap_store_from_configs()
        else:
            log.info(f"Loaded tool index with {len(self._tool_index.entries)} entries")

    def _bootstrap_store_from_configs(self) -> None:
        """One-shot populate: parse every tool conf, write canonical sources, build index.

        Runs only when the active store is empty. Idempotent — if a hash
        already exists in the store the per-source `store()` call is a
        no-op. Composite layering means writes land on the writable
        default member; read-only members (CVMFS bundles) are skipped by
        the composite itself.
        """
        # Lazy imports — only the bootstrap path needs these.
        import sys as _sys
        from pathlib import Path as _Path

        from galaxy.tool_source_store import StoredToolSource as _StoredToolSource
        from galaxy.util import xml_to_string

        if self._store is None:
            self._tool_index = ToolIndex()
            return

        # scripts/tool_source/_discover.py is a script-local helper; expose it on
        # sys.path the same way scripts/tool_source/populate_store.py does.
        scripts_dir = _Path(__file__).resolve().parents[3] / "scripts" / "tool_source"
        if str(scripts_dir) not in _sys.path:
            _sys.path.insert(0, str(scripts_dir))
        try:
            from _discover import discover_tools
        except ImportError as e:
            log.warning(f"Could not import discover_tools for bootstrap: {e}")
            self._tool_index = ToolIndex()
            return

        config = self.app.config
        # Build the index incrementally. ``add_entry`` keeps both
        # ``entries`` (default version per id) and ``entries_by_version``
        # (every version) in sync so multi-version tools survive bootstrap.
        index = ToolIndex(by_section={})
        stored_count = 0

        for discovered in discover_tools(config, include_bundled=True):
            tool_path = discovered.path
            try:
                tool_source = get_tool_source(config_file=tool_path)
                # XML tools: serialize the parsed (macro-expanded) tree so the
                # stored source matches what the parser would produce. YAML /
                # CWL / other tool sources have no ``xml_tree`` attribute —
                # store their raw file bytes instead so they show up in the
                # index without forcing them through an XML round-trip.
                xml_tree = getattr(tool_source, "xml_tree", None)
                if xml_tree is not None:
                    expanded_content = xml_to_string(xml_tree.getroot(), pretty=True)
                else:
                    with open(tool_path, encoding="utf-8") as _src_fh:
                        expanded_content = _src_fh.read()
            except Exception as e:
                log.warning(f"Bootstrap skipping {tool_path}: {e}")
                continue
            content_hash = hashlib.sha256(expanded_content.encode("utf-8")).hexdigest()
            tool_id = tool_source.parse_id() or discovered.guid
            if not tool_id:
                log.warning(f"Bootstrap skipping {tool_path}: no parseable tool id")
                continue
            stored = _StoredToolSource(
                hash=content_hash,
                tool_source_class=type(tool_source).__name__,
                raw_source=expanded_content,
                tool_id=tool_id,
                tool_version=tool_source.parse_version(),
                tool_dir=str(_Path(tool_path).parent),
                stored_at=datetime.utcnow(),
            )
            try:
                self._store.store(stored)
                stored_count += 1
            except Exception as e:
                log.warning(f"Bootstrap could not store {tool_path}: {e}")
                continue
            # Build the index entry directly from the tool_source we already
            # parsed — avoid round-tripping through xml_to_string + re-parse,
            # which has historically dropped ~third of stored sources silently.
            entry = self._make_index_entry(
                tool_source=tool_source,
                source_hash=content_hash,
                source_class=type(tool_source).__name__,
                fallback_tool_id=tool_id,
            )
            if entry is None:
                log.warning(f"Bootstrap could not build index entry for {tool_path} (id={tool_id})")
                continue
            # Conf-level ``hidden="true"`` on the ``<tool>`` directive forces
            # ``tool.hidden = True`` in the eager toolbox (see
            # AbstractToolBox._load_tool_tag_set). The XML body's own hidden
            # flag is already captured by ``parse_hidden()`` in
            # ``_make_index_entry``; OR them together so either source wins.
            if discovered.hidden:
                entry.hidden = True
            # ``add_entry`` records every version under entries_by_version and
            # keeps the highest version as the default in entries. Same-id
            # different-source-hash collisions at the same version are still
            # last-write-wins (a single tool conf shouldn't ship two of those).
            same_version = index.entries_by_version.get(entry.id, {}).get(entry.version or "")
            if same_version is not None and same_version.source_hash != entry.source_hash:
                log.warning(
                    f"Bootstrap index collision at same version: {entry.id} v={entry.version!r} "
                    f"from {tool_path} (hash={entry.source_hash}) replaces previous "
                    f"(hash={same_version.source_hash})"
                )
            index.add_entry(entry)

        self._tool_index = ToolIndex(
            entries=index.entries,
            entries_by_version=index.entries_by_version,
            by_section={},
            version=hashlib.md5(str(sorted(index.entries.keys())).encode()).hexdigest()[:8],
            built_at=datetime.utcnow(),
        )
        try:
            self._store.store_index(self._tool_index)
        except Exception as e:
            log.warning(f"Bootstrap could not persist index: {e}")
        # ``stored_count`` counts every accepted source (per-hash); index
        # ``entries`` only counts unique tool ids. The interesting ratio for
        # operators is ids-vs-versions: an index with N ids covering V total
        # versions where V == stored_count means nothing was dropped.
        total_versions = sum(len(v) for v in self._tool_index.entries_by_version.values())
        dropped = stored_count - total_versions
        if dropped:
            log.warning(
                f"Bootstrap complete: stored {stored_count} sources, index has {len(self._tool_index.entries)} "
                f"ids covering {total_versions} versions (dropped {dropped} during indexing — see prior warnings)"
            )
        else:
            log.info(
                f"Bootstrap complete: stored {stored_count} sources, index has {len(self._tool_index.entries)} "
                f"ids covering {total_versions} versions"
            )

    def _rebuild_index_from_store(self, stored_hashes: list[str]) -> None:
        """Rebuild the index from stored tool sources."""
        assert self._store is not None
        index = ToolIndex(by_section={})

        for source_hash in stored_hashes:
            stored = self._store.get(source_hash)
            if stored:
                try:
                    entry = self._build_index_entry_from_stored(stored)
                    if entry and entry.id:
                        index.add_entry(entry)
                except Exception as e:
                    log.warning(f"Error building index entry for {source_hash}: {e}")

        self._tool_index = ToolIndex(
            entries=index.entries,
            entries_by_version=index.entries_by_version,
            by_section={},
            version=hashlib.md5(str(sorted(index.entries.keys())).encode()).hexdigest()[:8],
            built_at=datetime.utcnow(),
        )

        # Save the rebuilt index
        try:
            self._store.store_index(self._tool_index)
            log.info(f"Rebuilt and saved tool index with {len(index.entries)} entries")
        except Exception as e:
            log.warning(f"Could not save rebuilt index: {e}")

    def _make_index_entry(
        self,
        tool_source: Any,
        source_hash: str,
        source_class: str,
        fallback_tool_id: Optional[str] = None,
    ) -> Optional[ToolIndexEntry]:
        """Build an index entry from an already-parsed tool source.

        Used by both the bootstrap path (parsing fresh from a file) and the
        rebuild path (parsing from raw stored bytes). Returning ``None`` means
        the source did not yield a usable id — callers should log and skip.
        """
        try:
            tool_id = tool_source.parse_id() or fallback_tool_id
            if not tool_id:
                return None

            uuid_val = None
            if hasattr(tool_source, "parse_uuid"):
                try:
                    parsed_uuid = tool_source.parse_uuid()
                    uuid_val = str(parsed_uuid) if parsed_uuid else None
                except Exception:
                    pass

            hidden = False
            if hasattr(tool_source, "parse_hidden"):
                try:
                    hidden = tool_source.parse_hidden()
                except Exception:
                    pass

            return ToolIndexEntry(
                id=tool_id,
                uuid=uuid_val,
                version=tool_source.parse_version(),
                name=tool_source.parse_name() or "",
                description=tool_source.parse_description() or "",
                source_hash=source_hash,
                source_class=source_class,
                hidden=hidden,
                indexed_at=datetime.utcnow(),
            )
        except Exception as e:
            log.warning(f"Error building index entry (id={fallback_tool_id}, hash={source_hash}): {e}")
            return None

    def _build_index_entry_from_stored(self, stored: StoredToolSource) -> Optional[ToolIndexEntry]:
        """Build an index entry from a stored tool source by re-parsing its raw bytes.

        Used by the rebuild path (`_rebuild_index_from_store`) where the only
        thing we have is the persisted ``StoredToolSource``.
        """
        try:
            tool_source = get_tool_source(
                raw_tool_source=stored.raw_source,
                tool_source_class=stored.tool_source_class,
            )
        except Exception as e:
            log.warning(f"Error re-parsing stored tool source (id={stored.tool_id}, hash={stored.hash}): {e}")
            return None
        return self._make_index_entry(
            tool_source=tool_source,
            source_hash=stored.hash,
            source_class=stored.tool_source_class,
            fallback_tool_id=stored.tool_id,
        )

    def load_item(
        self,
        item,
        tool_path,
        panel_dict=None,
        integrated_panel_dict=None,
        load_panel_dict: bool = True,
        guid=None,
        index: Optional[int] = None,
    ) -> None:
        """Persist newly installed tools to the store + index without pinning a Tool object.

        Called at runtime by the shed-install path
        (``tool_panel_manager.add_to_tool_panel`` →
        ``self.app.toolbox.load_item(...)``). The eager ``ToolBox.load_item``
        materializes a fully parsed ``Tool`` and registers it in
        ``_tools_by_id`` for the lifetime of the process — defeating the
        whole point of the lazy path. We replace it for ``tool`` items
        with the lazy-equivalent work; section/label/workflow/tool_dir
        items still go through super since they only mutate panel
        structure.
        """
        from galaxy.tool_util.toolbox.parser import ensure_tool_conf_item

        item = ensure_tool_conf_item(item)
        if getattr(item, "type", None) != "tool":
            super().load_item(
                item,
                tool_path=tool_path,
                panel_dict=panel_dict,
                integrated_panel_dict=integrated_panel_dict,
                load_panel_dict=load_panel_dict,
                guid=guid,
                index=index,
            )
            return

        if self._store is None or self._tool_index is None:
            # No lazy infra wired — fall back to eager load so the install still works.
            super().load_item(
                item,
                tool_path=tool_path,
                panel_dict=panel_dict,
                integrated_panel_dict=integrated_panel_dict,
                load_panel_dict=load_panel_dict,
                guid=guid,
                index=index,
            )
            return

        with self.app._toolbox_lock:
            self._lazy_register_tool_item(item, tool_path, guid=guid)

    def _lazy_register_tool_item(self, item, tool_path: str, guid: Optional[str] = None) -> None:
        """Persist a single tool item's source to the store and add an index entry.

        Reused by the shed-install ``load_item`` override. Does *not*
        instantiate a ``Tool`` object — the next ``get_tool`` call
        lazy-loads it.
        """
        from galaxy.tool_source_store import StoredToolSource as _StoredToolSource
        from galaxy.util import xml_to_string

        assert self._store is not None
        assert self._tool_index is not None

        tool_file = item.get("file")
        if not tool_file:
            log.debug("Lazy load_item skipped: tool item has no 'file' attribute")
            return
        tool_full_path = os.path.join(tool_path, tool_file)
        try:
            tool_source = get_tool_source(config_file=tool_full_path)
            root = tool_source.xml_tree.getroot()  # type: ignore[attr-defined]
            expanded_content = xml_to_string(root, pretty=True)
        except Exception as e:
            log.warning(f"Lazy load_item could not parse {tool_full_path}: {e}")
            return

        content_hash = hashlib.sha256(expanded_content.encode("utf-8")).hexdigest()
        tool_id = tool_source.parse_id() or guid or item.get("guid")
        if not tool_id:
            log.debug(f"Lazy load_item: no tool_id resolvable for {tool_full_path}")
            return

        stored = _StoredToolSource(
            hash=content_hash,
            tool_source_class=type(tool_source).__name__,
            raw_source=expanded_content,
            tool_id=tool_id,
            tool_version=tool_source.parse_version(),
            tool_dir=os.path.dirname(tool_full_path),
            stored_at=datetime.utcnow(),
        )
        try:
            self._store.store(stored)
        except Exception as e:
            log.warning(f"Lazy load_item could not store {tool_full_path}: {e}")
            return

        entry = self._build_index_entry_from_stored(stored)
        if entry and entry.id:
            self._tool_index.entries[entry.id] = entry
            self._tool_index.invalidate_caches()
            try:
                self._store.store_index(self._tool_index)
            except Exception as e:
                log.warning(f"Lazy load_item could not persist index: {e}")

        # Fan out to peer Galaxy processes so they reload the index.
        try:
            from galaxy.queue_worker import send_control_task

            send_control_task(self.app, "reload_tool_source_cache")
        except Exception as e:
            log.debug(f"Lazy load_item could not broadcast reload_tool_source_cache: {e}")

    def _populate_tool_registry_from_index(self) -> None:
        """
        Populate _tools_by_id with None placeholders from index.

        This allows has_tool() checks to work without loading Tool objects.
        The actual Tool objects are loaded on-demand in get_tool().
        """
        if self._tool_index is None:
            return

        # Update index entries with section info from tool_conf.xml
        # Build reverse map: short_id -> section_info for faster lookup
        if hasattr(self, "_tool_section_map"):
            short_id_to_section: dict[str, tuple] = {}
            for map_tool_id, mapped_section in self._tool_section_map.items():
                # Store exact ID
                short_id_to_section[map_tool_id] = mapped_section
                # For guids, also store the short tool ID
                short_id = extract_short_id_from_guid(map_tool_id)
                if short_id and short_id != map_tool_id and short_id not in short_id_to_section:
                    short_id_to_section[short_id] = mapped_section
        else:
            short_id_to_section = {}

        section_updates = 0
        section_info: Optional[tuple]
        for tool_id, entry in self._tool_index.entries.items():
            section_info = None

            # Try exact match first
            if tool_id in short_id_to_section:
                section_info = short_id_to_section[tool_id]

            if section_info:
                section_id, section_name = section_info
                if section_id and not entry.panel_section_id:
                    entry.panel_section_id = section_id
                    entry.panel_section_name = section_name
                    section_updates += 1

            # Store None as placeholder - actual Tool loaded on demand
            self._tools_by_id[tool_id] = None  # type: ignore[assignment]

            # Initialize version tracking. Walk every version we indexed so
            # ``has_tool(tool_id, exact=True)`` and version-aware lookups
            # behave the same as the eager toolbox (which registers each
            # ``Tool`` instance per version).
            self._tool_versions_by_id.setdefault(tool_id, {})
            versions = self._tool_index.entries_by_version.get(tool_id, {entry.version or "": entry})
            for version_key in versions.keys():
                if version_key:
                    self._tool_versions_by_id[tool_id][version_key] = None  # type: ignore[assignment]

            # Pre-seed the lineage map with every indexed version. The eager
            # ToolBox builds lineage as a side effect of loading each Tool,
            # but the lazy path only loads one version on demand — without
            # this, ``tool.lineage.tool_versions`` would only ever contain
            # the version that happened to be loaded first, breaking
            # /api/tools/{id}'s ``versions`` and ``hidden_versions`` fields.
            self._seed_lineage_for_tool(tool_id, [v for v in versions.keys() if v])

            # Add to panel if section info available
            if entry.panel_section_id and entry.panel_section_id in self._tool_panel:
                section = self._tool_panel[entry.panel_section_id]
                if isinstance(section, ToolSection):
                    self._tool_panel.record_section_for_tool_id(tool_id, entry.panel_section_id, section.name or "")

        # Debug: check for mismatches
        index_ids = set(self._tool_index.entries.keys()) if self._tool_index else set()
        map_ids = set(self._tool_section_map.keys()) if hasattr(self, "_tool_section_map") else set()
        matched = index_ids & map_ids
        log.info(
            f"Section map has {len(map_ids)} entries, index has {len(index_ids)} entries, {len(matched)} matched, {section_updates} updated"
        )
        if map_ids and index_ids:
            # Show sample IDs from each for comparison
            log.info(f"  Sample index IDs: {list(index_ids)[:3]}")
            log.info(f"  Sample map IDs: {list(map_ids)[:3]}")

    # === Override get_tool for lazy loading ===

    @overload
    def get_tool(
        self,
        tool_id: Optional[str] = None,
        tool_version: Optional[str] = None,
        tool_uuid: Optional[Union[UUID, str]] = None,
        get_all_versions: Literal[False] = False,
        exact: Optional[bool] = False,
        user: Optional["User"] = None,
    ) -> Optional["Tool"]: ...

    @overload
    def get_tool(
        self,
        tool_id: Optional[str] = None,
        tool_version: Optional[str] = None,
        tool_uuid: Optional[Union[UUID, str]] = None,
        get_all_versions: Literal[True] = True,
        exact: Optional[bool] = False,
        user: Optional["User"] = None,
    ) -> list["Tool"]: ...

    def get_tool(
        self,
        tool_id: Optional[str] = None,
        tool_version: Optional[str] = None,
        tool_uuid: Optional[Union[UUID, str]] = None,
        get_all_versions: Optional[bool] = False,
        exact: Optional[bool] = False,
        user: Optional["User"] = None,
    ) -> Union[Optional["Tool"], list["Tool"]]:
        """
        Get a tool, loading from store on-demand if needed.

        Overrides ToolBox.get_tool to implement lazy loading.
        """
        # Lazy import: galaxy.exceptions pulls in webapp framework deps.
        from galaxy.exceptions import (
            ObjectNotFound,
            RequestParameterInvalidException,
        )

        if tool_id is None and tool_uuid is None:
            raise RequestParameterInvalidException("get_tool cannot be called with both tool_id and tool_uuid as None")

        # Handle UUID lookup
        if tool_uuid:
            if user:
                unprivileged_tool = self.get_unprivileged_tool_or_none(user, tool_uuid=tool_uuid)
                if unprivileged_tool:
                    return unprivileged_tool
            tool_uuid = tool_uuid if isinstance(tool_uuid, UUID) else UUID(tool_uuid)
            tool_from_uuid = self._get_tool_by_uuid(tool_uuid)
            if tool_from_uuid is None:
                raise ObjectNotFound(f"Failed to find a tool with uuid [{tool_uuid}]")
            tool_id = tool_from_uuid.id

        assert tool_id

        if tool_version:
            tool_version = str(tool_version)

        if get_all_versions and exact:
            raise RequestParameterInvalidException(
                "get_tool cannot be called with both get_all_versions and exact as True"
            )

        # Check if we have this tool in our index
        if self._tool_index and tool_id in self._tool_index.entries:
            if get_all_versions:
                # Lazy-load every indexed version. Callers (e.g. workflow
                # refactor's ``upgrade_all_steps``) need every version to
                # determine the latest; returning only the requested version
                # makes upgrades silently no-op.
                versions = sorted(
                    self._tool_index.entries_by_version.get(tool_id, {}).keys(),
                    key=lambda v: tuple(int(p) if p.isdigit() else p for p in v.split(".") if p),
                )
                tools: list[Tool] = []
                for ver in versions:
                    loaded = self._load_tool_on_demand(tool_id, ver or None)
                    if loaded is not None:
                        tools.append(loaded)
                if tools:
                    return tools
            else:
                tool = self._load_tool_on_demand(tool_id, tool_version)
                if tool:
                    return tool

        # Fall back to parent implementation for tools not in our index
        # (dynamic tools, data manager tools, etc.)
        if get_all_versions:
            return super().get_tool(
                tool_id=tool_id,
                tool_version=tool_version,
                tool_uuid=tool_uuid,
                get_all_versions=True,
                exact=exact,
                user=user,
            )
        return super().get_tool(
            tool_id=tool_id,
            tool_version=tool_version,
            tool_uuid=tool_uuid,
            get_all_versions=False,
            exact=exact,
            user=user,
        )

    def _load_tool_on_demand(self, tool_id: str, tool_version: Optional[str] = None) -> Optional["Tool"]:
        """
        Load a tool from the store on-demand.

        Uses LRU cache to avoid reloading frequently used tools.
        """
        cache_key = f"{tool_id}:{tool_version or 'latest'}"

        # Check cache first
        with self._cache_lock:
            if cache_key in self._tool_object_cache:
                return self._tool_object_cache[cache_key]

        # Check if already loaded in _tools_by_id — only safe when no specific
        # version was requested. ``_tools_by_id`` keys by id and stores the
        # latest-loaded version, so honoring ``tool_version`` requires going
        # through the index to pick the right ``source_hash``.
        if tool_version is None:
            existing = self._tools_by_id.get(tool_id)
            if existing is not None:
                with self._cache_lock:
                    self._tool_object_cache[cache_key] = existing
                return existing

        # Get entry from index
        if self._tool_index is None or self._store is None:
            return None

        entry = self._tool_index.get(tool_id, tool_version)
        if not entry:
            return None

        # Load source from store
        stored = self._store.get(entry.source_hash)
        if not stored:
            log.warning(f"Tool source not found for {tool_id} (hash: {entry.source_hash})")
            return None

        # Create Tool object
        try:
            tool = self._create_tool_from_stored_source(stored)
            log.debug(f"Lazy-loaded tool: {tool_id}")
        except Exception as e:
            log.error(f"Error creating tool {tool_id}: {e}")
            return None

        # Register the tool
        self._register_loaded_tool(tool)

        # Add to cache
        with self._cache_lock:
            self._tool_object_cache[cache_key] = tool

        return tool

    def _create_tool_from_stored_source(self, stored: StoredToolSource) -> "Tool":
        """Create a Tool object from stored source."""
        tool_source = get_tool_source(
            raw_tool_source=stored.raw_source,
            tool_source_class=stored.tool_source_class,
        )
        return create_tool_from_source(
            self.app,
            tool_source,
            tool_dir=stored.tool_dir,
        )

    def invalidate_index_cache(self) -> None:
        """Drop cached tool index so the next read picks up out-of-band updates.

        Wired to the ``reload_tool_source_cache`` queue-worker control
        message: a populator on another host (or another Galaxy process)
        writes new sources/index to the shared store, then publishes
        the message — every process calls this method to re-read the
        index. The per-process LRU of materialized ``Tool`` objects
        stays warm because content-addressed sources can't go stale
        for a given hash.
        """
        if self._store is not None:
            try:
                self._store.invalidate_index_cache()
            except Exception as e:
                log.debug(f"Store invalidate_index_cache raised: {e}")
        self._tool_index = None
        self._load_index_from_store()

    def _register_loaded_tool(self, tool: "Tool") -> None:
        """Register a lazily-loaded tool in the toolbox registries."""
        tool_id = tool.id
        if not tool_id:
            return

        self._tools_by_id[tool_id] = tool

        version = tool.version
        if tool_id not in self._tool_versions_by_id:
            self._tool_versions_by_id[tool_id] = {}
        self._tool_versions_by_id[tool_id][version] = tool

        # Tool uses 'guid' not 'uuid'
        if hasattr(tool, "uuid") and tool.uuid:
            self._tools_by_uuid[tool.uuid] = tool

        # Update lineage. ``LineageMap.register`` returns the shared lineage
        # for this id; the eager ToolBox assigns it to ``tool._lineage`` (see
        # AbstractToolBox.__add_tool) — without that assignment, ``tool.lineage``
        # is ``None`` and ``tool.tool_versions`` returns ``[]``, breaking
        # /api/tools/{id}'s ``versions`` / ``hidden_versions`` fields.
        tool._lineage = self._lineage_map.register(tool)

        # Conf-level ``hidden="true"`` (from the ``<tool>`` directive in the
        # tool conf) is applied here. The eager toolbox does this in
        # ``_load_tool_tag_set``; the lazy path's ``_create_tool_from_stored_source``
        # only sees the parsed XML body, so we lift the flag from the index
        # entry. Note: never *clear* an XML-body hidden flag — only set it.
        if self._tool_index is not None:
            entry = self._tool_index.get(tool_id, version)
            if entry and entry.hidden:
                tool.hidden = True

    @property
    def tools_by_id(self) -> "_LazyToolsByIdView":
        """Lazy-loading view over ``_tools_by_id``.

        ``AbstractToolBox.tools_by_id`` returns the raw dict, but in the lazy
        path that dict holds ``None`` placeholders for tools that haven't been
        materialised yet. Callers that index by id (e.g.
        ``galaxy.tool_util.deps.views.resolve``: ``self._app.toolbox.tools_by_id[tool_id]``)
        otherwise get ``None`` and crash. This view delegates ``__getitem__``
        through ``get_tool`` so a placeholder triggers a lazy load instead of
        being returned as ``None``.
        """
        return _LazyToolsByIdView(self)

    # === Override has_tool to check index ===

    def has_tool(
        self,
        tool_id: Optional[str],
        tool_version: Optional[str] = None,
        tool_uuid: Optional[Union[UUID, str]] = None,
        exact: bool = False,
        user: Optional["User"] = None,
    ) -> bool:
        """Check if tool exists, using index for fast lookup."""
        if tool_id and self._tool_index and tool_id in self._tool_index.entries:
            return True
        # Fall back to parent for UUID lookups and edge cases
        return super().has_tool(
            tool_id=tool_id,
            tool_version=tool_version,
            tool_uuid=tool_uuid,
            exact=exact,
            user=user,
        )

    # === Override tools() to iterate loaded tools ===

    def tools(self):
        """
        Return loaded tools.

        Note: This only returns tools that have been loaded on-demand.
        For a full list, use the index.
        """
        return {k: v for k, v in self._tools_by_id.items() if v is not None}.items()

    # === Index access methods ===

    @property
    def tool_index(self) -> Optional[ToolIndex]:
        """Get the tool index."""
        return self._tool_index

    def get_tool_ids(self) -> list[str]:
        """Get all tool IDs from index."""
        if self._tool_index:
            return list(self._tool_index.entries.keys())
        return []

    def get_index_entry(self, tool_id: str) -> Optional[ToolIndexEntry]:
        """Get index entry for a tool without loading it."""
        if self._tool_index:
            return self._tool_index.get(tool_id)
        return None

    # === Required property overrides ===

    @property
    def all_requirements(self):
        """Get all tool requirements from index (no tool loading needed)."""
        if self._tool_index:
            requirements = set()
            for entry in self._tool_index.entries.values():
                for req in entry.requirements:
                    # Convert dict to hashable tuple
                    req_tuple = (req.get("name"), req.get("version"), req.get("type"))
                    requirements.add(req_tuple)
            return [
                {"name": r[0], "version": r[1], "type": r[2]} for r in requirements if r[0]  # Filter out empty names
            ]
        return []

    # === Override to_dict for API responses ===

    def to_dict(
        self, trans, in_panel: bool = True, tool_help: bool = False, view: Optional[str] = None, **kwds
    ) -> list[dict[str, Any]]:
        """
        Create a dictionary representation of the toolbox.

        For the *flat* listing (``in_panel=False``) we serve straight from
        the index — no Tool loading needed. The panel listing
        (``in_panel=True``) defers to the parent so the section-aware
        response shape the UI expects is preserved.

        Note: tool_help is ignored since we don't load the full tool.
        """
        if self._tool_index is None:
            return []

        if in_panel:
            return super().to_dict(trans, in_panel=True, tool_help=tool_help, view=view, **kwds)

        rval = []

        # Return data directly from index - no tool loading needed!
        for _tool_id, entry in self._tool_index.entries.items():
            # Skip hidden tools unless requested
            if entry.hidden and not kwds.get("include_hidden", False):
                continue

            # Convert index entry to API dict format
            tool_dict = self._index_entry_to_api_dict(entry)
            rval.append(tool_dict)

        log.debug(f"LazyToolBox.to_dict: returning {len(rval)} tools from index (no loading)")
        return rval

    def _index_entry_to_api_dict(self, entry: ToolIndexEntry) -> dict[str, Any]:
        """Convert an index entry to the format expected by /api/tools."""
        return {
            "id": entry.id,
            "name": entry.name,
            "version": entry.version,
            "description": entry.description,
            "labels": entry.labels if entry.labels else [],
            "edam_operations": entry.edam_operations if entry.edam_operations else [],
            "edam_topics": entry.edam_topics if entry.edam_topics else [],
            "hidden": entry.hidden,
            "model_class": "Tool",
            "panel_section_id": entry.panel_section_id,
            "panel_section_name": entry.panel_section_name,
            # Minimal fields that indicate this is from index
            "link": f"/api/tools/{entry.id}",
            "min_width": -1,
            "target": "galaxy_main",
        }

    def to_panel_view(self, trans, view="default_panel_view", **kwds) -> dict[str, dict]:
        """
        Create a panel view representation of the toolbox.

        For LazyToolBox, returns tools from index organized by section.
        """
        if self._tool_index is None:
            return {}

        view_contents: dict[str, dict] = {}

        # Group tools by section from index
        sections: dict[str, dict[str, Any]] = {}
        uncategorized_tools: list[dict[str, Any]] = []

        for _tool_id, entry in self._tool_index.entries.items():
            if entry.hidden and not kwds.get("include_hidden", False):
                continue

            tool_dict = self._index_entry_to_api_dict(entry)

            section_id = entry.panel_section_id
            if section_id:
                if section_id not in sections:
                    sections[section_id] = {
                        "id": section_id,
                        "name": entry.panel_section_name or section_id,
                        "model_class": "ToolSection",
                        "elems": [],
                    }
                sections[section_id]["elems"].append(tool_dict)
            else:
                uncategorized_tools.append(tool_dict)

        # Add sections to view_contents
        for section_id, section_dict in sections.items():
            view_contents[section_id] = section_dict

        # Add uncategorized tools directly
        for tool_dict in uncategorized_tools:
            view_contents[tool_dict["id"]] = tool_dict

        return view_contents
