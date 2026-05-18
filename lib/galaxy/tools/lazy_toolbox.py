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
import weakref
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
from packaging.version import parse as parse_version

from galaxy.tool_source_store import (
    StoredToolSource,
    ToolSourceStore,
)
from galaxy.tool_source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tool_source_store.search import (
    ToolSearchTuning,
    ToolWhooshIndex,
)
from galaxy.tool_util.id_util import (
    extract_short_id_from_guid,
    extract_tool_id_from_file,
)
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.toolbox.base import (
    DynamicToolConfDict,
    SHED_TOOL_CONF_XML,
)
from galaxy.tool_util.toolbox.filters import FilterFactory
from galaxy.tool_util.toolbox.lineages.factory import LazyLineageMap
from galaxy.tool_util.toolbox.lineages.interface import ToolLineage
from galaxy.tool_util.toolbox.panel import (
    panel_item_types,
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
        # Return the configured panel structure as-is. Tools that are
        # explicitly loaded (via shed install or first ``get_tool`` use)
        # land in this panel via the eager ``__add_tool_to_tool_panel``;
        # *eagerly* materialising every indexed tool here would defeat
        # LazyToolBox's purpose, take 30+ seconds at boot, and surface
        # any per-tool parse error as a startup failure.
        # /api/tool_panels/default is served by an override on
        # ``LazyToolBox.to_panel_view`` that builds the response straight
        # from the index entries instead — see that method.
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


class LazyIntegratedToolPanelElements(ToolPanelElements):
    """``_integrated_tool_panel`` that materialises sections on demand.

    Static panel views (``StaticToolPanelView.apply_view``,
    ``lib/galaxy/tool_util/toolbox/views/static.py``) walk this panel via
    ``closest_section`` and then call ``ToolSection.copy(merge_tools=True)``
    which reads ``tool.lineage`` for every tool in ``section.elems`` —
    so the section needs *real* Tool objects, not stubs. The eager
    toolbox populates these as a side effect of loading every tool at
    boot. The lazy toolbox can't afford that (~30s + per-tool parse
    errors that stalled CI's ``test_job_recovery::test_recovery``), so
    we materialise sections lazily: only when a panel-view request
    actually consults one.

    ``walk_sections`` and ``apply_filter`` are bulk operations
    (e.g. global filters); they trigger materialisation of every
    section. ``closest_section`` triggers materialisation of just the
    matching section.
    """

    def __init__(self, toolbox_ref: "weakref.ReferenceType") -> None:
        super().__init__()
        self._toolbox_ref = toolbox_ref
        self._materialised_sections: set[str] = set()
        self._fully_materialised = False

    # --- materialisation helpers ---

    def _toolbox(self) -> Optional["LazyToolBox"]:
        return self._toolbox_ref()

    def _materialise_section(self, section_id: Optional[str]) -> None:
        if not section_id or section_id in self._materialised_sections:
            return
        section = self.get(section_id)
        if not isinstance(section, ToolSection):
            return
        toolbox = self._toolbox()
        if toolbox is None or toolbox._tool_index is None:
            return
        # Order: shed-installed entries (``is_local=False``) before
        # local entries. The eager toolbox achieves this implicitly via
        # the install path's ``__add_tool_to_tool_panel`` insert/replace
        # logic + the integrated panel rebuild; tests like
        # ``test_only_latest_version_in_panel_fastp`` assert
        # ``tools[0]`` is the just-installed shed tool, so the lazy
        # materialiser needs to mirror that ordering. Insert shed
        # tools at the section head (preserving sibling shed-tool
        # order), append local tools at the tail. ``has_tool_with_id``
        # skips tools already in the section so a re-materialise
        # after install is idempotent for prior entries.
        shed_count = 0
        loaded = 0
        for entry in toolbox._tool_index.entries.values():
            if entry.panel_section_id != section_id or entry.hidden:
                continue
            if section.elems.has_tool_with_id(entry.id):
                continue
            tool = toolbox.get_tool(tool_id=entry.id)
            if tool is None:
                continue
            if entry.is_local:
                section.elems.append_tool(tool)
            else:
                section.elems.insert_tool(shed_count, tool)
                shed_count += 1
            loaded += 1
        self._materialised_sections.add(section_id)
        log.debug("LazyIntegratedToolPanelElements: materialised section id=%r (%d tools)", section_id, loaded)

    def _materialise_all(self) -> None:
        if self._fully_materialised:
            return
        toolbox = self._toolbox()
        if toolbox is None or toolbox._tool_index is None:
            return
        # Materialise every section first.
        for section_id, value in list(self.items()):
            if isinstance(value, ToolSection):
                self._materialise_section(section_id)
        # Then add tools that aren't in any section as top-level entries.
        # Tools at the conf's root (no parent ``<section>``) carry
        # ``entry.panel_section_id is None``; ``walk_loaded_tools`` (used
        # by EDAM and toolbox search) yields top-level entries from
        # ``tool_panel.panel_items_iter()`` directly. Without this they're
        # invisible — EDAM can't tag e.g. ``mapper`` with its
        # ``operation_3198`` because the tool never gets walked.
        for entry in toolbox._tool_index.entries.values():
            if entry.panel_section_id or entry.hidden:
                continue
            key = f"tool_{entry.id}"
            if key in self:
                continue
            tool = toolbox.get_tool(tool_id=entry.id)
            if tool is None:
                continue
            self.append_tool(tool)
        self._fully_materialised = True

    # --- overrides ---

    def closest_section(self, target_section_id, target_section_name):
        # Materialise just the section we'll return (if any) before delegating.
        if target_section_id and isinstance(self.get(target_section_id), ToolSection):
            self._materialise_section(target_section_id)
        elif target_section_name:
            for sid, sec in list(self.items()):
                if isinstance(sec, ToolSection) and sec.name == target_section_name:
                    self._materialise_section(sid)
                    break
        return super().closest_section(target_section_id, target_section_name)

    def walk_sections(self):
        self._materialise_all()
        return super().walk_sections()

    def apply_filter(self, f):
        self._materialise_all()
        return super().apply_filter(f)

    # ``panel_items_iter`` is intentionally NOT overridden. It's called by
    # ``ManagesIntegratedToolPanelMixin._write_integrated_tool_panel_config_file``
    # at boot to flush the panel to disk; auto-materialising there would
    # eagerly load every indexed tool — defeating lazy mode and surfacing
    # per-tool parse errors (interactive tools, ``filter_data_table`` etc.)
    # that should stay deferred. Consumers that really need the full panel
    # (EDAM ``apply_view``, search index) get materialisation via the
    # explicit ``LazyToolBox._materialise_integrated_panel_for_views`` call
    # in ``_load_tool_panel_views``.


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


class _IndexEntryFilterAdapter:
    """Wraps a :class:`ToolIndexEntry` so it satisfies ``ToolFilterContext``.

    ``Tool.allow_user_access`` consults ``self.app`` to do per-subclass admin
    checks (``DataManagerTool`` is admin-only). ``ToolIndexEntry`` is a lightweight
    record with no app reference; instead of dragging one onto every entry,
    the adapter takes the admin-check callable at construction time. Filter
    functions call ``tool.allow_user_access(user)`` polymorphically and never
    reach through ``context.trans.app.config``.
    """

    __slots__ = ("entry", "_is_admin_user")

    def __init__(self, entry: "ToolIndexEntry", is_admin_user):
        self.entry = entry
        self._is_admin_user = is_admin_user

    def __getattr__(self, name):
        return getattr(self.entry, name)

    def allow_user_access(self, user, attempting_access: bool = True) -> bool:
        if self.entry.require_login and user is None:
            return False
        if self.entry.tool_type == "data_manager":
            return user is not None and bool(self._is_admin_user(user))
        return True


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
        # Whoosh search infrastructure — built lazily on first ``search_tools``
        # call and re-built whenever the underlying ``ToolIndex`` version changes.
        self._whoosh_search_index: Optional[ToolWhooshIndex] = None
        self._whoosh_search_index_version: Optional[str] = None

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

        # Drop persisted shed-install entries that no current shed_tool_conf
        # references. Without this the persistent tool source store leaks
        # shed installs across reloads (e.g. ``reset_shed_tools`` writes an
        # empty shed conf and triggers a reload, but the previous test's
        # install survives in the index and the next test sees the tool as
        # already installed).
        self._prune_orphaned_shed_entries()

        # Populate _tools_by_id with stub entries from index
        # This allows has_tool() and similar checks to work without loading
        self._populate_tool_registry_from_index()

        # Rebuild the short-id → guid map from the just-loaded index so
        # short-id lookups for shed installs persisted across restarts
        # resolve immediately, before any new install happens.
        self._rebuild_shed_short_id_map()

        # Render static panel views now that the index is populated. Before
        # this point ``apply_view`` would have ``has_tool`` return False for
        # every indexed-but-unloaded tool and the resulting view would be
        # missing every entry. See the deferred-render comment in
        # ``_init_lazy_toolbox``.
        if self.app.name == "galaxy":
            # EDAM's ``apply_view`` walks the full integrated panel via
            # ``walk_loaded_tools`` -> ``panel_items_iter``, none of which
            # trigger ``LazyIntegratedToolPanelElements`` materialisation.
            # Only force a bulk materialisation when EDAM views are
            # explicitly configured — for the typical lazy-mode deployment
            # we keep the per-section deferral behaviour.
            self._load_tool_panel_views()

        # Commit any pending writes the constructor accumulated
        # (``_bootstrap_store_from_configs`` already commits, but
        # ``_prune_orphaned_shed_entries`` / ``_rebuild_index_from_store``
        # ``flush()`` without committing). When the constructor runs in
        # the queue-worker thread (``reload_toolbox`` control task),
        # nothing later closes that transaction — on SQLite the open
        # writer lock blocks the test driver's subsequent ``DELETE FROM
        # repository_repository_dependency_association`` in
        # ``reset_shed_tools`` (``test_repository_*`` teardown), on
        # Postgres it leaves an idle-in-transaction row that blocks
        # those same ``DELETE``s for the rest of the shard run. The
        # commit is also a no-op when nothing was written.
        if self._store is not None:
            try:
                self._store.commit()
            except Exception as e:
                log.warning(f"LazyToolBox: post-init commit raised: {e}")

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

    def _rebuild_shed_short_id_map(self) -> None:
        """Walk the index and rebuild short-id → guid mappings for shed installs.

        Called from ``__init__`` (after the index is loaded from the store)
        and from ``_prune_orphaned_shed_entries`` (after pruning), so the
        map stays consistent with whatever is currently in
        ``self._tool_index.entries``.
        """
        self._shed_short_id_to_guids.clear()
        if self._tool_index is None:
            return
        for entry_id in self._tool_index.entries.keys():
            short_id = extract_short_id_from_guid(entry_id)
            if short_id and short_id != entry_id:
                self._shed_short_id_to_guids.setdefault(short_id, set()).add(entry_id)

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
        # Short-id → set of full guids for shed installs. The eager toolbox
        # populates ``_tools_by_old_id[tool.old_id]`` when a Tool is
        # registered, so ``get_tool("collection_column_join")`` resolves to
        # the installed ``toolshed.../collection_column_join/.../0.0.2``
        # Tool object. The lazy install path stores only the index entry
        # (no Tool instantiation), so ``_tools_by_old_id`` stays empty for
        # shed tools and short-id lookups (the form used by
        # ``GET /api/tools/{tool_id}`` and ``test_repository_installation``)
        # 404. Mirror the eager mapping at the index level so ``get_tool``
        # and ``has_tool`` can resolve short-id → guid → entry without
        # materialising the Tool first.
        self._shed_short_id_to_guids: dict[str, set[str]] = {}
        self._workflows_by_id: dict[str, Any] = {}
        self._tool_to_dict_cache: dict[str, dict[str, Any]] = {}
        self._tool_to_dict_cache_admin: dict[str, dict[str, Any]] = {}
        self._tool_panel = ToolPanelElements()
        self._index = 0
        self.data_manager_tools: dict[str, Tool] = {}
        # ``LazyLineageMap`` defers building each tool's ``ToolLineage``
        # until first access, sourcing versions from the index on demand.
        # That replaces a boot-time ``_seed_lineage_for_tool`` pass that
        # walked every entry; the data is the same since
        # ``ToolIndex.entries_by_version`` is already serialised in the
        # tool source store.
        self._lineage_map = LazyLineageMap(
            app,
            versions_for=self._index_versions_for,
        )

        # Tool root dir handling from ToolBox
        if tool_root_dir == "./tools":
            tool_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "bundled"))
        self._tool_root_dir = tool_root_dir
        self.app = app

        # Initialize integrated tool panel (from ManagesIntegratedToolPanelMixin),
        # then swap the empty ``ToolPanelElements`` it creates for our lazy
        # subclass. ``StaticToolPanelView.apply_view`` walks this panel and
        # calls ``ToolSection.copy(merge_tools=True)`` which reads
        # ``tool.lineage`` for every tool — so the section needs real
        # Tool objects when a panel view is rendered. ``LazyIntegratedToolPanelElements``
        # materialises only the sections actually consulted, instead of
        # eagerly loading every indexed tool at boot.
        self._init_integrated_tool_panel(app.config)
        self._integrated_tool_panel = LazyIntegratedToolPanelElements(weakref.ref(self))

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

        # ``_load_tool_panel_views`` materialises every static panel view by
        # walking ``apply_view``, which calls ``toolbox_registry.has_tool``.
        # In the lazy path the index isn't populated until ``_load_index_from_store``
        # runs (right after this method returns), so calling it here would
        # see an empty toolbox and drop every tool from the static views with
        # a "Failed to find tool_id ... cannot load into panel view" warning.
        # Defer the rendering until after the index is loaded — see the
        # follow-up call in ``__init__``.

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

    def _load_tool_panel_views(self) -> None:
        """Render panel views, deferring EDAM views.

        EDAM views call ``walk_loaded_tools(base_tool_panel, registry)``
        which iterates the *integrated* panel via ``panel_items_iter``.
        ``LazyIntegratedToolPanelElements`` doesn't auto-materialise on
        that iteration (per the comment on
        ``LazyIntegratedToolPanelElements`` — auto-materialisation here
        would defeat lazy mode), so for EDAM we'd have to manually
        ``_materialise_all()`` first. That's hundreds of sequential
        lazy-loads against the database-backed source store, repeated on
        every restart — which silently hangs ``test_job_recovery`` for
        hours under workflow_dispatch + ``use_lazy_toolbox=true``.
        Default and static views are cheap (``DefaultToolPanelView``
        returns the live ``_tool_panel`` and ``StaticToolPanelView``
        lazy-materialises only the few sections it names via
        ``closest_section``); render those at boot. EDAM gets an empty
        placeholder so callers that index ``_tool_panel_view_rendered``
        (e.g. ``panel_has_tool`` from the search-index build) don't
        ``KeyError``. The real EDAM render happens on first
        ``to_panel_view`` request and is cached.
        """
        from galaxy.tool_util.toolbox.base import ToolBoxRegistryImpl
        from galaxy.tool_util.toolbox.panel import ToolPanelElements

        self._tool_panel_view_rendered = {}
        # Tracks EDAM views that have actually been rendered (vs. seeded
        # with the empty placeholder). ``to_panel_view`` consults this
        # to decide whether to do the deferred render — checking
        # ``_tool_panel_view_rendered`` membership wouldn't distinguish
        # the placeholder from a real render.
        self._edam_views_rendered: set[str] = set()
        registry = ToolBoxRegistryImpl(self)
        for key, view in self._tool_panel_views.items():
            if isinstance(view, EdamToolPanelView):
                self._tool_panel_view_rendered[key] = ToolPanelElements()
                continue
            self._tool_panel_view_rendered[key] = view.apply_view(self._integrated_tool_panel, registry)

    def panel_has_tool(self, tool: "Tool", panel_view_id: str) -> bool:
        """Return True if ``tool`` is reachable from the given panel view.

        For EDAM views the boot-time placeholder in
        ``_tool_panel_view_rendered`` is empty (the real render is
        deferred — see ``_load_tool_panel_views``), so the parent's
        ``has_item_recursive`` would always answer ``False`` and the
        search-index build at boot would skip every tool for that view.
        Every tool in the index lands in some EDAM section (an
        ``edam_operations`` term, an ``edam_topics`` term, or
        ``uncategorized``) once ``apply_view`` actually runs, so for
        index-known tools we answer ``True`` directly.
        """
        if panel_view_id in self._tool_panel_view_rendered:
            view = self._tool_panel_views.get(panel_view_id)
            if isinstance(view, EdamToolPanelView):
                tool_id = getattr(tool, "id", None)
                if tool_id and self._tool_index is not None and tool_id in self._tool_index.entries:
                    return True
                return False
        return super().panel_has_tool(tool, panel_view_id)

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
        # Configured shed/migrated tool confs are allowed to be absent at
        # boot — the eager toolbox creates them on demand on first install.
        # Mirror that behaviour so ``install_repository`` (and anything else
        # going through ``default_shed_tool_conf_dict()``) doesn't fail with
        # ``ConfigurationError("No shed_tool_conf file active")`` when the
        # placeholder file hasn't been written yet.
        on_demand_confs = {self.app.config.shed_tool_config_file, self.app.config.migrated_tools_config}
        # Track every shed guid currently referenced by a shed_tool_conf so
        # ``_prune_orphaned_shed_entries`` can drop persisted index entries
        # whose backing conf no longer mentions them. The eager toolbox
        # rebuilds from scratch on reload, so a ``reset_shed_tools`` that
        # blanks the shed conf naturally drops the tool. The lazy toolbox's
        # persistent store outlives reloads — without explicit pruning, a
        # shed install installed in one test leaks into the next.
        self._shed_conf_referenced_ids: set[str] = set()
        self._has_shed_conf = False

        def _register_on_demand_shed_conf(config_filename: str) -> None:
            self._dynamic_tool_confs.append(
                {
                    "config_filename": config_filename,
                    "tool_path": self.app.config.shed_tools_dir,
                    "config_elems": [],
                    "create": SHED_TOOL_CONF_XML.format(shed_tools_dir=self.app.config.shed_tools_dir),
                }
            )

        for config_filename in config_filenames:
            if not self.can_load_config_file(config_filename):
                continue
            if not os.path.exists(config_filename) and config_filename in on_demand_confs:
                _register_on_demand_shed_conf(config_filename)
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
                if parsing_shed_tool_conf:
                    self._has_shed_conf = True

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
                                self._extract_tools_from_section(
                                    item, section_id, section_name, tool_path, in_shed_conf=parsing_shed_tool_conf
                                )

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
                            if parsing_shed_tool_conf:
                                shed_guid = item.get("guid")
                                if shed_guid:
                                    self._shed_conf_referenced_ids.add(shed_guid)

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

    def _extract_tools_from_section(
        self,
        section_item,
        section_id: str,
        section_name: str,
        tool_path: str,
        in_shed_conf: bool = False,
    ) -> None:
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
                    if in_shed_conf:
                        shed_guid = sub_item.get("guid")
                        if shed_guid:
                            self._shed_conf_referenced_ids.add(shed_guid)
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

    def _index_versions_for(self, tool_id: str) -> list[str]:
        """Return every version present in the index for ``tool_id``.

        Hooked into ``LazyLineageMap.versions_for`` so a lineage lookup
        sources its data straight from ``_tool_index.entries_by_version``.
        Empty list (no versions) tells the lineage map to fall through to
        the standard ``LineageMap.get`` toolbox path.

        For shed-installed tools the index keys each entry on the full
        toolshed guid (e.g. ``toolshed.../fastp/0.20.1+galaxy0``), so a
        single id maps to a single version. Lineage merging in
        ``ToolSection.copy(merge_tools=True)`` needs *every* version with
        the same versionless guid to deduplicate older revisions out of
        a panel view (e.g. ``test_only_latest_version_in_panel_fastp``
        expects two installed fastp revisions to render as one
        latest-version entry). Eager achieves this via
        ``_tools_by_old_id``; the lazy index needs to walk sibling
        entries that share the versionless prefix.
        """
        if self._tool_index is None:
            return []
        versions = list(self._tool_index.entries_by_version.get(tool_id, {}).keys())
        result = [v for v in versions if v]
        if "/repos/" in tool_id:
            from galaxy.util.tool_version import remove_version_from_guid

            versionless = remove_version_from_guid(tool_id)
            if versionless:
                prefix = f"{versionless}/"
                for entry_id, entry in self._tool_index.entries.items():
                    if entry_id == tool_id:
                        continue
                    if entry_id.startswith(prefix) and entry.version and entry.version not in result:
                        result.append(entry.version)
        return result

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

    def _prune_orphaned_shed_entries(self) -> None:
        """Drop indexed shed installs whose backing shed_tool_conf is gone.

        Shed installs land in the persistent tool source store via
        ``_lazy_register_tool_item`` (called from
        ``ToolPanelManager.add_to_tool_panel`` → ``self.app.toolbox.load_item``).
        The eager toolbox keeps no persistent state across reloads, so
        rewriting ``shed_tool_conf.xml`` to empty (e.g. via
        ``reset_shed_tools`` in the test driver) and reloading is enough
        to drop every shed-installed tool. The lazy toolbox would
        otherwise treat the persisted entry as still active and answer
        ``has_tool``/``get_tool`` for it, which makes the next install
        attempt see the tool as already installed.

        This method is conservative: it only acts when at least one
        shed_tool_conf was discovered during ``_init_panel_structure_from_configs``
        (so a one-off boot with no shed conf at all doesn't accidentally
        nuke local tools that happen to share the shed-style ``id`` shape).
        """
        if not getattr(self, "_has_shed_conf", False):
            return
        if self._tool_index is None or not self._tool_index.entries:
            return
        referenced = self._shed_conf_referenced_ids
        # ``id`` values that ``ToolPanelManager`` writes to a shed_tool_conf
        # are toolshed guids of the form
        # ``<toolshed-host>/repos/<owner>/<repo>/<tool>/<version>``. We
        # treat any indexed entry whose id contains ``/repos/`` as a
        # shed install candidate.
        to_drop = [
            tool_id
            for tool_id in list(self._tool_index.entries.keys())
            if "/repos/" in tool_id and tool_id not in referenced
        ]
        if not to_drop:
            return
        for tool_id in to_drop:
            self._tool_index.entries.pop(tool_id, None)
            self._tool_index.entries_by_version.pop(tool_id, None)
        self._tool_index.invalidate_caches()
        # Drop any short-id entries that no longer point at a guid in the
        # index. ``_rebuild_shed_short_id_map`` would also work but is
        # quadratic in the number of entries; this is targeted.
        for guid in to_drop:
            short_id = extract_short_id_from_guid(guid)
            if short_id and short_id in self._shed_short_id_to_guids:
                self._shed_short_id_to_guids[short_id].discard(guid)
                if not self._shed_short_id_to_guids[short_id]:
                    del self._shed_short_id_to_guids[short_id]
        log.info(
            "LazyToolBox pruned %s orphaned shed entries from the index "
            "(no shed_tool_conf currently references them)",
            len(to_drop),
        )
        if self._store is not None:
            try:
                self._store.store_index(self._tool_index)
            except Exception as e:
                log.debug(f"_prune_orphaned_shed_entries: store_index raised: {e}")

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
                source_path=str(tool_path),
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

        # Commit the freshly-bootstrapped sources + index. Without an
        # explicit commit here every bootstrapped row is just ``flush()``-ed
        # into the request-scoped session; on
        # ``IntegrationTestCase.restart()`` the prior Galaxy disposes its
        # engine without committing and every bootstrap insert rolls back.
        # The next Galaxy boot then sees an empty store and runs the same
        # bootstrap again — a per-restart cost that hangs ``test_recovery``
        # (and others) on CI. Committing here is also a one-shot: bootstrap
        # only runs when the store is genuinely empty, so we're not
        # interfering with a long-running Galaxy's request-scoped commit
        # boundaries. ``commit()`` is polymorphic over backends — composite
        # propagates to its members, ``DatabaseToolSourceStore`` commits its
        # shared scoped session, file-backed stores are a no-op.
        self._store.commit()

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

            # ``parse_require_login`` is what ``Tool.parse`` calls to set
            # ``tool.require_login``. Default False matches ``Tool.__init__``.
            require_login = False
            if hasattr(tool_source, "parse_require_login"):
                try:
                    require_login = bool(tool_source.parse_require_login(False))
                except Exception:
                    pass

            # ``tool_type`` is the Tool subclass key (``data_manager``,
            # ``interactive_tool``, etc.). Stock filters branch on this for the
            # admin-only check on ``DataManagerTool``; custom filters use it
            # to categorize.
            tool_type = "default"
            if hasattr(tool_source, "parse_tool_type"):
                try:
                    tool_type = tool_source.parse_tool_type() or "default"
                except Exception:
                    pass

            # ``tags`` are currently not exposed via the ToolSource parser API.
            # The field on ``ToolIndexEntry`` is here so admin/user filters that
            # bucket tools by tag have a place to read from when the populator
            # learns to fill it.
            tags: list[str] = []

            return ToolIndexEntry(
                id=tool_id,
                uuid=uuid_val,
                version=tool_source.parse_version(),
                name=tool_source.parse_name() or "",
                description=tool_source.parse_description() or "",
                source_hash=source_hash,
                source_class=source_class,
                hidden=hidden,
                require_login=require_login,
                tool_type=tool_type,
                tags=tags,
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
        with the lazy-equivalent work; for ``section`` items we walk the
        children ourselves so their section context survives (the eager
        ``_load_section_tag_set`` post-walks ``integrated_elems`` to call
        ``record_section_for_tool_id``, which finds nothing because the
        lazy path never put a Tool object into ``integrated_elems``).
        """
        from galaxy.tool_util.toolbox.parser import ensure_tool_conf_item

        item = ensure_tool_conf_item(item)
        item_type = getattr(item, "type", None)

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

        if item_type == "tool":
            with self.app._toolbox_lock:
                self._lazy_register_tool_item(item, tool_path, guid=guid)
            return

        if item_type == "section":
            with self.app._toolbox_lock:
                self._lazy_register_section_item(item, tool_path, index=index)
            return

        super().load_item(
            item,
            tool_path=tool_path,
            panel_dict=panel_dict,
            integrated_panel_dict=integrated_panel_dict,
            load_panel_dict=load_panel_dict,
            guid=guid,
            index=index,
        )

    def _lazy_register_section_item(self, item, tool_path: str, index: Optional[int] = None) -> None:
        """Lazy equivalent of ``_load_section_tag_set`` for shed installs.

        The eager path materializes each child ``Tool`` and walks
        ``integrated_elems.panel_items_iter()`` to call
        ``record_section_for_tool_id``. Without a Tool object the walk
        finds nothing, so panel views (e.g. ``custom_13`` referencing
        ``test_section_multi``) render the freshly-installed tool at root
        instead of inside the requested section. We store the source +
        index entry as for a bare tool, then explicitly stamp the
        section onto the entry and the section/tool maps so subsequent
        panel renders place it correctly.
        """
        section_id = item.get("id")
        section_name = item.get("name", section_id) or ""
        if section_id:
            section_dict = {"id": section_id, "name": section_name, "version": item.get("version", "")}
            if section_id not in self._tool_panel:
                self._tool_panel.append_section(section_id, ToolSection(section_dict))
            # Mirror into ``_integrated_tool_panel`` so static panel views
            # (``apply_view`` walks the integrated panel via
            # ``ToolPanelElements.closest_section`` / ``walk_sections``)
            # can find the section. Without this, e.g. ``custom_13.yml``
            # which references ``test_section_multi`` renders the
            # freshly-installed shed tool at the panel root because the
            # view doesn't see the section it was placed under.
            if section_id not in self._integrated_tool_panel:
                self._integrated_tool_panel[section_id] = ToolSection(section_dict)
            # Drop the section from the materialised-set so the next view
            # render pulls in the newly-installed tool. The lazy panel
            # otherwise short-circuits on the already-materialised flag and
            # keeps serving the pre-install snapshot.
            if isinstance(self._integrated_tool_panel, LazyIntegratedToolPanelElements):
                self._integrated_tool_panel._materialised_sections.discard(section_id)
                self._integrated_tool_panel._fully_materialised = False
        if not hasattr(item, "items"):
            return
        for sub_item in item.items:
            sub_type = getattr(sub_item, "type", None)
            if sub_type == "tool":
                self._lazy_register_tool_item(
                    sub_item,
                    tool_path,
                    guid=sub_item.get("guid"),
                    section_id=section_id,
                    section_name=section_name,
                )
            else:
                # labels, workflows, nested sections — let the eager
                # implementation handle them; they don't need lazy treatment.
                super().load_item(sub_item, tool_path=tool_path, index=index)
        # Re-render static panel views so newly-installed tools land in
        # ``_tool_panel_view_rendered`` immediately. The view dict is
        # otherwise frozen at boot — ``apply_view`` calls
        # ``closest_section.copy(merge_tools=True)`` which snapshots the
        # section's elems at render time, so a post-boot install is
        # invisible to ``tools?in_panel=True&view=...`` until the next
        # reload. Skip if ``app.name != "galaxy"`` (mirrors the eager
        # ``_load_tool_panel_views`` guard in
        # ``ToolBox._load_built_in_converters``).
        if getattr(self.app, "name", None) == "galaxy":
            try:
                self._load_tool_panel_views()
            except Exception as e:
                log.warning(f"Lazy section install: panel view re-render failed: {e}")

    def _lazy_register_tool_item(
        self,
        item,
        tool_path: str,
        guid: Optional[str] = None,
        section_id: Optional[str] = None,
        section_name: Optional[str] = None,
    ) -> None:
        """Persist a single tool item's source to the store and add an index entry.

        Reused by the shed-install ``load_item`` override. Does *not*
        instantiate a ``Tool`` object — the next ``get_tool`` call
        lazy-loads it. ``section_id`` / ``section_name`` are propagated
        from the enclosing ``<section>`` (when called from
        ``_lazy_register_section_item``) so the index entry, the tool
        section map, and the panel structure all agree on the tool's
        section.
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
        # ``<tool guid="...">`` overrides the XML body's ``<tool id="...">``
        # for shed installs — ``Tool.id`` becomes the guid in the eager path.
        # Workflow / API lookups by full guid (e.g. ``toolshed.../pick_value/0.2.0``)
        # consult ``has_tool``/``get_tool`` against that guid; without keying
        # the index by guid the lookup returns ``None`` and downstream
        # callers report "required tools are not installed".
        installed_guid = guid or item.get("guid")
        tool_id = installed_guid or tool_source.parse_id()
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
            source_path=tool_full_path,
            stored_at=datetime.utcnow(),
        )
        try:
            self._store.store(stored)
        except Exception as e:
            log.warning(f"Lazy load_item could not store {tool_full_path}: {e}")
            return

        entry = self._build_index_entry_from_stored(stored)
        if entry:
            # ``_build_index_entry_from_stored`` keys the entry on
            # ``tool_source.parse_id()`` (the XML's ``<tool id="...">``,
            # i.e. the short id like ``map_param_value``). For shed
            # installs the tool's *external* id is the guid — that's what
            # ``Tool.id`` becomes in the eager path and what
            # workflow / API callers consult via ``has_tool(guid)``.
            # Override the entry id (and any tool-shed metadata) so the
            # lazy index agrees with that contract.
            if installed_guid:
                entry.id = installed_guid
                entry.is_local = False
                # Pull tool_shed metadata from the install elem so the
                # entry — and the lazy-loaded Tool — agrees with the
                # eager toolbox's ``populate_tool_shed_info`` contract.
                # The install path generates ``<tool guid="..."><tool_shed>...</tool_shed>...</tool>``
                # via ``ToolPanelManager.generate_tool_elem``; ``ToolConfItem``
                # exposes the underlying XML via ``.elem`` (and ``has_elem``
                # tells us when that's safe). For dict-typed items there's
                # no XML — skip silently.
                xml_elem = item.elem if getattr(item, "has_elem", False) else None
                if xml_elem is not None:
                    shed_url = xml_elem.findtext("tool_shed")
                    if shed_url:
                        entry.tool_shed = shed_url
                    repo_name = xml_elem.findtext("repository_name")
                    if repo_name:
                        entry.repository_name = repo_name
                    repo_owner = xml_elem.findtext("repository_owner")
                    if repo_owner:
                        entry.repository_owner = repo_owner
                    changeset = xml_elem.findtext("installed_changeset_revision")
                    if changeset:
                        entry.changeset_revision = changeset
            if section_id:
                entry.panel_section_id = section_id
                entry.panel_section_name = section_name or section_id
            # ``add_entry`` populates both the default-per-id ``entries``
            # map and ``entries_by_version`` (keyed on the tool's version),
            # which is what version-aware ``get_tool`` lookups consult.
            # Direct assignment to ``entries`` would leave
            # ``entries_by_version`` stale and break per-version routing.
            self._tool_index.add_entry(entry)
            self._tool_index.invalidate_caches()
            # Mirror the eager toolbox's short-id → Tool mapping so
            # ``GET /api/tools/<short_id>`` resolves immediately after
            # install. Without this, ``test_repository_installation``'s
            # ``self._get("/api/tools/collection_column_join")`` hits 404
            # because the index entry is keyed on the full guid.
            if installed_guid:
                short_id = extract_short_id_from_guid(installed_guid)
                if short_id and short_id != installed_guid:
                    self._shed_short_id_to_guids.setdefault(short_id, set()).add(installed_guid)
            if section_id:
                self._tool_section_map[entry.id] = (section_id, section_name)
                if section_id in self._tool_panel:
                    self._tool_panel.record_section_for_tool_id(entry.id, section_id, section_name or "")
            try:
                self._store.store_index(self._tool_index)
            except Exception as e:
                log.warning(f"Lazy load_item could not persist index: {e}")

        # Fan out to peer Galaxy processes so they reload the index. Skip
        # ourselves — our in-memory ``_cached_index`` already reflects the
        # just-added entry, but the local queue-worker handler would
        # ``invalidate_index_cache`` and re-read the DB, where the WSGI
        # thread's session has only flushed (not committed) the new row.
        # That race used to clobber the live cache with the pre-write
        # state, so the next install on this process saw an empty index
        # and persisted only its own entry — losing the prior install's
        # tool entirely (``test_only_latest_version_in_panel_fastp``
        # surfaces this when ``fastp/0.19.5+galaxy1`` vanishes between
        # install-1 and install-2).
        try:
            from galaxy.queue_worker import send_control_task

            send_control_task(self.app, "reload_tool_source_cache", noop_self=True)
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

            # Lineage is built lazily by ``LazyLineageMap`` from
            # ``_tool_index.entries_by_version`` on first ``get()``; no
            # boot-time seeding pass is needed.

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

        # Mirror ``_tool_panel``'s section/label structure into
        # ``_integrated_tool_panel`` so static panel views can resolve
        # sections via ``closest_section`` (which searches the integrated
        # panel). Tools stay deferred — the lazy panel materialises each
        # section's elems on first access. Without this seed, static views
        # for the test-tool sections (e.g. ``test``, ``filter``,
        # ``test_section_multi``) fail to find any section and render
        # empty.
        for key, value in list(self._tool_panel.items()):
            if key in self._integrated_tool_panel:
                continue
            if isinstance(value, ToolSection):
                self._integrated_tool_panel[key] = ToolSection(
                    {"id": value.id, "name": value.name, "version": value.version or ""}
                )
            else:
                # Labels and other non-tool elements copy by reference.
                self._integrated_tool_panel[key] = value

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
                def _ver_key(v: str):
                    # ``packaging.version.parse`` matches what the
                    # eager ToolLineage uses to order versions and
                    # tolerates non-numeric segments (e.g. ``"1.0.0+galaxy0"``).
                    try:
                        return (0, parse_version(v))
                    except Exception:
                        return (1, v)

                versions = sorted(
                    self._tool_index.entries_by_version.get(tool_id, {}).keys(),
                    key=_ver_key,
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
                # Version not in the index. Fall back to the default (latest)
                # entry's Tool — not the requested version, but a Tool for the
                # same id. The eager toolbox does this after a
                # ``_tool_versions_by_id`` miss when ``tool_id`` is in
                # ``_tools_by_id`` and ``exact`` is False: the for-loop in
                # ``AbstractToolBox.get_tool`` ``continue``s for ``exact``
                # when the version doesn't match. Without this fallback,
                # ``ToolModule.__init__`` invoked at workflow-upload time
                # gets ``None`` for any workflow pinned to a tool_version we
                # no longer ship — eager would have returned the
                # lineage-newest Tool, then ``get_safe_version`` would have
                # downgraded it to the safe-upgrade version
                # (e.g. ``__BUILD_LIST__`` 1.0.0 → 1.1.0 via
                # ``WORKFLOW_SAFE_TOOL_VERSION_UPDATES``). Returning ``None``
                # here breaks that path and the workflow ends up bound to
                # the latest version with state shaped for the old version,
                # producing spurious upgrade-message 400s on invoke.
                #
                # Honor ``exact`` though: callers like the workflow
                # missing-tool check pass ``exact=True`` specifically to
                # ask "is THIS exact version installed", and silently
                # substituting the latest makes the missing-tools list
                # under-report (``test_run_workflow_with_missing_tool``
                # asserts both ``nonexistent_tool`` and a known-absent
                # ``compose_text_param 0.0.1`` show up as missing).
                if tool_version and not exact:
                    default_entry = self._tool_index.entries.get(tool_id)
                    if default_entry is not None:
                        default_version = default_entry.version or None
                        tool = self._load_tool_on_demand(tool_id, default_version)
                        if tool:
                            return tool

        # Short-id fallback for shed installs. The eager toolbox resolves
        # ``get_tool("collection_column_join")`` via ``_tools_by_old_id``,
        # which is populated at tool-registration time. The lazy install
        # path doesn't materialise the Tool, so we maintain
        # ``_shed_short_id_to_guids`` separately and consult it here. Each
        # shed install lives under a distinct guid in the index, so we
        # walk every guid mapped to the short id and sort the
        # successfully-loaded Tools by version — matching the eager path's
        # ``rval.sort(key=lambda t: t.version_object)`` over
        # ``_tools_by_old_id[tool_id]``.
        if self._tool_index and self._shed_short_id_to_guids and tool_id in self._shed_short_id_to_guids:
            candidates: list[tuple[tuple[int, Any], Tool]] = []
            for guid in sorted(self._shed_short_id_to_guids[tool_id]):
                loaded = self._load_tool_on_demand(guid, tool_version)
                if loaded is None and tool_version:
                    # Unknown version on this guid — try its default.
                    default_entry = self._tool_index.entries.get(guid)
                    if default_entry is not None:
                        loaded = self._load_tool_on_demand(guid, default_entry.version or None)
                if loaded is not None:
                    ver_key: tuple[int, Any]
                    try:
                        ver_key = (0, parse_version(loaded.version or "0"))
                    except Exception:
                        ver_key = (1, loaded.version or "")
                    candidates.append((ver_key, loaded))
            if candidates:
                candidates.sort(key=lambda pair: pair[0])
                if get_all_versions:
                    return [t for _, t in candidates]
                return candidates[-1][1]

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
            tool = self._create_tool_from_stored_source(stored, entry=entry)
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

    def _create_tool_from_stored_source(
        self, stored: StoredToolSource, entry: Optional[ToolIndexEntry] = None
    ) -> "Tool":
        """Create a Tool object from stored source."""
        tool_source = get_tool_source(
            raw_tool_source=stored.raw_source,
            tool_source_class=stored.tool_source_class,
        )
        # When the stored source's ``tool_id`` is a toolshed guid (set by
        # the lazy shed install path), pass it as ``guid`` to the Tool
        # constructor so ``Tool.id`` becomes the guid — matching what the
        # eager toolbox does and what callers consult via ``has_tool``
        # / ``get_tool`` and the ``_tools_by_id`` registry.
        kwds: dict[str, Any] = {"tool_dir": stored.tool_dir}
        if stored.tool_id and "/repos/" in stored.tool_id:
            kwds["guid"] = stored.tool_id
            # Hand the matching ToolShedRepository to the Tool ctor so
            # ``populate_tool_shed_info`` can stamp ``tool_shed`` /
            # ``repository_name`` / ``changeset_revision`` /
            # ``installed_changeset_revision`` onto the Tool. Without
            # them, ``Tool.to_dict`` skips the ``tool_shed_repository``
            # block (gated on ``self.tool_shed`` being truthy) and tests
            # like ``test_only_latest_version_in_panel_fastp`` raise
            # ``KeyError: 'tool_shed_repository'`` on the rendered
            # response.
            shed_repo = self._lookup_tool_shed_repository(stored, entry)
            if shed_repo is not None:
                kwds["tool_shed_repository"] = shed_repo
        return create_tool_from_source(self.app, tool_source, **kwds)

    def _lookup_tool_shed_repository(self, stored: StoredToolSource, entry: Optional[ToolIndexEntry]) -> Optional[Any]:
        """Resolve the installed ToolShedRepository for a stored shed tool.

        Mirrors ``AbstractToolBox.get_tool_repository_from_xml_item`` but
        sources the tool_shed / repository_name / repository_owner /
        installed_changeset_revision from the index entry (stamped by
        ``_lazy_register_tool_item`` from the install elem) instead of
        re-parsing the conf XML.
        """
        if entry is None or entry.is_local:
            return None
        tool_shed = entry.tool_shed
        repo_name = entry.repository_name
        repo_owner = entry.repository_owner
        installed_changeset = entry.changeset_revision
        if not (tool_shed and repo_name and repo_owner and installed_changeset):
            return None
        try:
            from galaxy.tool_shed.util.repository_util import get_installed_repository

            return get_installed_repository(
                self.app,
                tool_shed=tool_shed,
                name=repo_name,
                owner=repo_owner,
                installed_changeset_revision=installed_changeset,
                from_cache=True,
            )
        except Exception as e:
            log.debug(f"Lazy lookup of tool_shed_repository for {stored.tool_id} failed: {e}")
            return None

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
        # Index just changed under us — refresh the short-id map so
        # peer-process installs (which only update the persisted index)
        # are reachable via short-id lookups in this process.
        self._rebuild_shed_short_id_map()

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

        # The eager ``__add_tool`` also tracks tools by their pre-shed
        # ``old_id`` so callers like ``remove_tool_by_id``
        # (``self._tools_by_old_id[tool.old_id].remove(tool)``) can find
        # them. Without this, removing a lazy-loaded shed tool raises
        # ``KeyError`` on ``_tools_by_old_id``.
        old_id = getattr(tool, "old_id", None)
        if old_id:
            bucket = self._tools_by_old_id.setdefault(old_id, [])
            if tool not in bucket:
                bucket.append(tool)

        # Tool uses 'guid' not 'uuid'
        if hasattr(tool, "uuid") and tool.uuid:
            self._tools_by_uuid[tool.uuid] = tool

        # Update lineage. ``LazyLineageMap.get`` builds the lineage from
        # ``entries_by_version`` (cached after first call); for a shed tool
        # that arrived after boot and isn't in the index yet,
        # ``LineageMap.register`` is the right fallback. Either way the
        # eager ToolBox assigns it to ``tool._lineage`` (see
        # AbstractToolBox.__add_tool) — without that assignment,
        # ``tool.lineage`` is ``None`` and ``tool.tool_versions`` returns
        # ``[]``, breaking /api/tools/{id}'s ``versions`` /
        # ``hidden_versions`` fields.
        tool._lineage = self._lineage_map.get(tool_id) or self._lineage_map.register(tool)

        # Conf-level ``hidden="true"`` (from the ``<tool>`` directive in the
        # tool conf) is applied here. The eager toolbox does this in
        # ``_load_tool_tag_set``; the lazy path's ``_create_tool_from_stored_source``
        # only sees the parsed XML body, so we lift the flag from the index
        # entry. Note: never *clear* an XML-body hidden flag — only set it.
        if self._tool_index is not None:
            entry = self._tool_index.get(tool_id, version)
            if entry and entry.hidden:
                tool.hidden = True

    def close(self) -> None:
        """Drop in-memory state at app shutdown.

        Wired into ``GalaxyUniverseApplication.haltables`` so an embedded
        restart (``IntegrationTestCase.restart``) releases the LRU cache,
        the ``ToolIndex`` reference, and the link back to the
        ``tool_source_store`` before the next boot wires up a fresh
        toolbox. Idempotent; safe to call more than once.
        """
        with self._cache_lock:
            self._tool_object_cache.clear()
        self._tool_index = None
        self._store = None
        # ``ToolLineage.lineages_by_id`` is a *class*-level dict, so a
        # ``ToolLineage`` from a prior process / embedded restart would
        # otherwise carry its ``tool_versions`` SortedSet across boots and
        # shadow the new boot's index versions. Reset on shutdown so the
        # next ``LazyLineageMap.get`` rebuilds from the freshly-loaded
        # index.
        ToolLineage.reset()
        # ``_tools_by_id`` and friends still get GC'd when the surrounding
        # app object drops. We don't clear them here because the eager
        # parent's shutdown sequence may still iterate them.

    def remove_tool_by_id(self, tool_id: str, remove_from_panel: bool = True):
        """Also drop the tool from the lazy index + LRU cache.

        ``AbstractToolBox.remove_tool_by_id`` only deletes from
        ``_tools_by_id``. In the lazy path that's not enough — ``get_tool``
        re-loads the tool from ``_tool_index`` on the next request, so the
        tool effectively comes back. The eager toolbox doesn't have this
        problem because the tool object isn't created from a serialised
        store. Mirror the deletion across the two backing stores.

        Wrapped in ``app._toolbox_lock`` so the cleanup is atomic
        against concurrent ``_load_tool_on_demand`` calls — without
        the lock, an in-flight HTTP request thread that's mid-way
        through ``_register_loaded_tool`` can re-populate
        ``_tool_versions_by_id`` / ``_lineage_map.lineage_map`` /
        ``_tools_by_id`` after this method has already cleared them,
        leaving the tool resurrectable via the eager super().get_tool
        fall-through path that walks lineage versions via
        ``_tool_from_lineage_version``.
        """
        with self.app._toolbox_lock:
            # Force-materialise so the eager parent's bookkeeping (``_tools_by_old_id``,
            # panel removal, lineage, tool cache expiry) gets a real Tool to work
            # against.
            if self._tools_by_id.get(tool_id) is None:
                self.get_tool(tool_id=tool_id)
            result = super().remove_tool_by_id(tool_id, remove_from_panel=remove_from_panel)
            if self._tool_index is not None:
                self._tool_index.entries.pop(tool_id, None)
                self._tool_index.entries_by_version.pop(tool_id, None)
            # ``super().remove_tool_by_id`` clears ``_tools_by_id`` but leaves
            # ``_tool_versions_by_id`` and the lineage map intact. ``get_tool``'s
            # fall-through walks lineage versions via ``_tool_from_lineage_version``
            # which reads ``_tool_versions_by_id``, so the tool would otherwise
            # come back from there even after removal.
            self._tool_versions_by_id.pop(tool_id, None)
            if hasattr(self, "_lineage_map"):
                from galaxy.util.tool_version import remove_version_from_guid

                self._lineage_map.lineage_map.pop(tool_id, None)
                versionless = remove_version_from_guid(tool_id)
                if versionless:
                    self._lineage_map.lineage_map.pop(versionless, None)
            # ``super().remove_tool_by_id`` removes a single Tool object
            # from ``_tools_by_old_id[old_id]``, but if a concurrent
            # ``_register_loaded_tool`` (e.g. an in-flight HTTP request
            # that beat us to the lock) appended a sibling Tool to the
            # same bucket, the sibling survives and the eager
            # super().get_tool fall-through returns it via
            # ``rval.extend(self._tools_by_old_id[tool_id])``. Drop the
            # whole bucket for this tool_id to match the index removal.
            self._tools_by_old_id.pop(tool_id, None)
            # Mirror the cleanup in our short-id → guid map so a
            # subsequent ``has_tool``/``get_tool`` for the short id
            # doesn't resurrect a removed shed install. Both directions
            # need cleanup: ``tool_id`` may itself be a short id (drop
            # the entry), or it may be a guid (drop it from any short
            # id's set, and remove that short id if its set becomes
            # empty).
            self._shed_short_id_to_guids.pop(tool_id, None)
            for _short, _guids in list(self._shed_short_id_to_guids.items()):
                _guids.discard(tool_id)
                if not _guids:
                    del self._shed_short_id_to_guids[_short]
            with self._cache_lock:
                for key in [k for k in self._tool_object_cache.keys() if k.startswith(f"{tool_id}:")]:
                    self._tool_object_cache.pop(key, None)
        return result

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
        """Check if tool exists, using index for fast lookup.

        Honors ``tool_version`` + ``exact`` the same way the eager
        ``AbstractToolBox.has_tool`` does — without that, the workflow
        missing-tools check (``services/workflows.py``: ``has_tool(...,
        exact=require_exact_tool_versions)``) silently passes any tool
        whose id is in the index regardless of which version was
        requested. ``test_run_workflow_with_missing_tool`` exercises
        that surface by installing ``compose_text_param 0.1.0`` from
        the toolshed and then asking the workflow runner to invoke a
        workflow pinned to ``compose_text_param 0.0.1``: with the
        version-blind lookup, ``has_tool`` answers ``True`` for 0.0.1,
        the tool drops out of the missing-tools list, and the assertion
        on the error message under-reports.
        """
        if tool_id and self._tool_index:
            entries = self._tool_index.entries_by_version.get(tool_id)
            if entries is not None:
                if tool_version is None:
                    return bool(entries) or tool_id in self._tool_index.entries
                if str(tool_version) in entries:
                    return True
                if exact:
                    # Exact version requested and not present — say so.
                    # Don't fall through to the parent which would walk
                    # lineage and return ``True`` for any version.
                    return False
                # Non-exact: fall through to parent for lineage walk.
            elif tool_version is None and tool_id in self._tool_index.entries:
                return True
        # Short-id alias for shed installs (see ``get_tool``'s short-id
        # fallback for the rationale).
        if tool_id and tool_id in self._shed_short_id_to_guids:
            if tool_version is None:
                return True
            # For version-specific short-id lookups, check if any guid
            # mapped to this short id has the requested version.
            if self._tool_index is not None:
                for guid in self._shed_short_id_to_guids[tool_id]:
                    versions = self._tool_index.entries_by_version.get(guid, {})
                    if str(tool_version) in versions:
                        return True
            if exact:
                return False
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

    def _get_search_index(self) -> Optional[ToolWhooshIndex]:
        """Return the cached :class:`ToolWhooshIndex` or build one on demand.

        Resolves the index path under ``tool_search_index_dir`` (the same
        root the eager ``ToolBoxSearch`` uses), in a sub-folder so neither
        path stomps the other. ``ToolSearchTuning`` is built from
        ``self.app.config`` once and passed in — the search index code
        doesn't need a god-object reference.
        """
        if self._whoosh_search_index is not None:
            return self._whoosh_search_index
        base = self.app.config.tool_search_index_dir
        if not base:
            return None
        index_dir = os.path.join(base, "_lazy_default")
        tuning = ToolSearchTuning.from_config(self.app.config)
        self._whoosh_search_index = ToolWhooshIndex(index_dir=index_dir, tuning=tuning)
        return self._whoosh_search_index

    def search_tools(self, query: str, limit: int = 50) -> list[ToolIndexEntry]:
        """Rank index entries against ``query`` using Whoosh (BM25F).

        Builds the on-disk Whoosh index lazily on first call (or after a
        ``ToolIndex`` version change) so the populator does not need to know
        about search infrastructure. Falls back to ``ToolIndex.search``'s
        in-process scorer when Whoosh setup fails (e.g. read-only directory).
        """
        if self._tool_index is None:
            return []
        searcher = self._get_search_index()
        if searcher is None:
            return self._tool_index.search(query, limit=limit)
        current_version = self._tool_index.compute_version()
        if self._whoosh_search_index_version != current_version:
            try:
                searcher.build(self._tool_index)
                self._whoosh_search_index_version = current_version
            except Exception as e:
                log.warning("Falling back to in-process scorer; Whoosh build failed: %s", e)
                return self._tool_index.search(query, limit=limit)
        try:
            ids = searcher.search(query, limit=limit)
        except Exception as e:
            log.warning("Falling back to in-process scorer; Whoosh search failed: %s", e)
            return self._tool_index.search(query, limit=limit)
        return [entry for entry in (self._tool_index.entries.get(tool_id) for tool_id in ids) if entry is not None]

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
        the index — no Tool loading needed — but still run every entry
        through ``FilterFactory`` so admin / user toolbox filters apply
        identically to the eager path. Filters take ``ToolFilterContext``,
        which both ``Tool`` and ``ToolIndexEntry`` satisfy. For the panel
        listing (``in_panel=True``, e.g. ``tools?in_panel=True&view=custom_13``)
        we defer to the parent: it walks ``_tool_panel_view_rendered``
        which is built by ``apply_view`` against
        ``_integrated_tool_panel`` and produces the section-aware
        response shape (interleaved Tools and ToolSections) that the UI
        and tests expect. ``ToolBoxRegistry.get_tool`` lazy-loads the
        per-section tools as ``apply_view`` walks them, so this stays
        cheap as long as the requested view scopes to a small section.
        """
        if self._tool_index is None:
            return []

        if in_panel:
            return super().to_dict(trans, in_panel=True, tool_help=tool_help, view=view, **kwds)

        filter_method = self._build_filter_method(trans)
        # The adapter exposes ``allow_user_access`` so the stock
        # ``_handle_authorization`` filter is polymorphic across
        # ``Tool`` (eager) and the index view (lazy) — see
        # ``_IndexEntryFilterAdapter``.
        is_admin_user = self.app.config.is_admin_user
        rval = []
        for _tool_id, entry in self._tool_index.entries.items():
            candidate = _IndexEntryFilterAdapter(entry, is_admin_user)
            if not filter_method(candidate, panel_item_types.TOOL):
                continue
            rval.append(self._index_entry_to_api_dict(entry))

        log.debug(f"LazyToolBox.to_dict: returning {len(rval)} tools from index (no loading)")
        return rval

    def to_panel_view(self, trans, view="default_panel_view", **kwds) -> dict[str, dict]:
        """Render a panel view's API response.

        For the default view we build the response straight from
        ``_tool_index.entries`` — no Tool instantiation, no per-tool
        re-parse. Going through the parent's ``tool_panel_contents`` ->
        ``apply_view`` -> ``get_tool_to_dict`` path would lazy-load every
        indexed tool at request time, which is exactly what defeated
        startup in the prior commit (``test_job_recovery::test_recovery``
        spent ~14 minutes lazy-loading 500+ tools per restart and never
        reached "ready").

        Static panel views (configured via ``panel_views`` /
        ``panel_views_dir``) are scoped to a specific small set of
        ``<tool>`` entries; for those we let the parent walk
        ``apply_view`` so its ``ToolBoxRegistry.get_tool`` lazy-loads
        only the requested few.
        """
        resolved_view = view
        if resolved_view == "default_panel_view":
            resolved_view = self._default_panel_view(trans)

        view_def = (self._tool_panel_views or {}).get(resolved_view) if hasattr(self, "_tool_panel_views") else None
        if view_def is None or isinstance(view_def, DefaultToolPanelView):
            # Default view — render from index entries cheaply.
            view_contents: dict[str, dict] = {}
            sections: dict[str, dict[str, Any]] = {}
            uncategorized: list[dict[str, Any]] = []
            if self._tool_index is None:
                return {}
            include_hidden = bool(kwds.get("include_hidden", False))
            for entry in self._tool_index.entries.values():
                if entry.hidden and not include_hidden:
                    continue
                tool_dict = self._index_entry_to_api_dict(entry)
                section_id = entry.panel_section_id
                if section_id:
                    section = sections.get(section_id)
                    if section is None:
                        # Mirror ``ToolSection.to_dict(only_ids=True)`` which
                        # the eager toolbox calls for the default view: a
                        # ``"tools"`` key with the list of tool ids (not
                        # ``"elems"`` with full dicts). Tests like
                        # ``test_tools::test_index`` walk
                        # ``tool_or_section["tools"]`` to flatten sections;
                        # an ``"elems"`` payload makes ``upload1`` (a
                        # sectioned tool) invisible to the flatten loop.
                        section = {
                            "id": section_id,
                            "name": entry.panel_section_name or section_id,
                            "model_class": "ToolSection",
                            "tools": [],
                        }
                        sections[section_id] = section
                    section["tools"].append(tool_dict["id"])
                else:
                    uncategorized.append(tool_dict)
            for section_id, section_dict in sections.items():
                view_contents[section_id] = section_dict
            for tool_dict in uncategorized:
                view_contents[tool_dict["id"]] = tool_dict
            return view_contents

        # EDAM views walk every tool in the integrated panel, so they need
        # the panel materialised before ``apply_view``. Boot defers this
        # work — render the EDAM view on first request and cache the
        # result in ``_tool_panel_view_rendered`` so subsequent reads are
        # instant. Without this, every restart re-runs ~500 sequential
        # lazy-loads at boot just so EDAM is ready, even when the test
        # never asks for an EDAM view (the regression that caused
        # ``test_job_recovery::test_recovery`` to silently hang shard 3
        # for hours under workflow_dispatch + ``use_lazy_toolbox=true``).
        if isinstance(view_def, EdamToolPanelView):
            from galaxy.tool_util.toolbox.base import ToolBoxRegistryImpl

            if resolved_view not in self._edam_views_rendered:
                if isinstance(self._integrated_tool_panel, LazyIntegratedToolPanelElements):
                    self._integrated_tool_panel._materialise_all()
                registry = ToolBoxRegistryImpl(self)
                self._tool_panel_view_rendered[resolved_view] = view_def.apply_view(
                    self._integrated_tool_panel, registry
                )
                self._edam_views_rendered.add(resolved_view)

        # Static (non-default) view: defer to parent so apply_view runs
        # against the registered ToolPanelView. Only the small set of
        # tools the static view names will be lazy-loaded.
        return super().to_panel_view(trans, view=view, **kwds)

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
