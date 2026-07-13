"""
Lazy ToolBox - On-demand tool loading with LRU caching.

This module provides a LazyToolBox that extends ToolBox but keeps only a
lightweight index in memory and loads full Tool objects on-demand with
LRU eviction.
"""

import errno
import logging
import os
import threading
from typing import (
    Any,
    Literal,
    Optional,
    overload,
    TYPE_CHECKING,
)
from uuid import UUID

from cachetools import LRUCache

from galaxy.exceptions import (
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.tool_util.id_util import extract_short_id_from_guid
from galaxy.tool_util.ontologies.ontology_data import curated_tool_tags
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.toolbox.base import (
    resolve_tool_path,
    SHED_TOOL_CONF_XML,
    ToolConfRepository,
)
from galaxy.tool_util.toolbox.lineages.factory import LazyLineageMap
from galaxy.tool_util.toolbox.lineages.interface import ToolLineage
from galaxy.tool_util.toolbox.panel import ToolSection
from galaxy.tool_util.toolbox.parser import get_toolbox_parser
from galaxy.tool_util.version import parse_version
from galaxy.tools.source_store import (
    StoredToolSource,
    ToolSourceStore,
)
from galaxy.tools.source_store.composite import CompositeToolSourceStore
from galaxy.tools.source_store.discover import discover_tools
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
    ToolPanelItem,
)
from galaxy.tools.source_store.populator import (
    build_whoosh_for_store,
    conf_to_store_map,
    populate_for_paths,
    populate_store_inline,
)
from galaxy.tools.source_store.watcher import ToolSourceStoreWatcher
from galaxy.util import listify
from galaxy.util.tool_version import remove_version_from_guid
from . import (
    create_tool_from_source,
    ToolBox,
)

if TYPE_CHECKING:
    from galaxy.app import UniverseApplication
    from galaxy.model import User
    from galaxy.tools import Tool

log = logging.getLogger(__name__)


# Whether to be strict about unknown attribute reads on a ``LazyTool``. Default
# is permissive: anything not on the stub surface and not in ``_MATERIALIZE_OK``
# materialises with a WARN log, instead of raising. Set ``LAZY_TOOL_STRICT=1``
# to flip to raise — useful when adding to the stub surface, since unaccounted
# reads then show up loudly. The eager pipeline + the integration suite hit a
# very wide tool surface; permissive is the pragmatic default once the
# explicit ``_MATERIALIZE_OK`` set has stabilised.
_LAZY_TOOL_PERMISSIVE = os.environ.get("LAZY_TOOL_STRICT") != "1"


def _entry_attr(name: str, entry_attr: str | None = None, mutable: bool = False):
    """Build a ``LazyTool`` property forwarding ``name`` to ``ToolIndexEntry``.

    ``_overrides`` shadows the entry so writes from the eager pipeline
    (``tool.hidden = True``, ``tool.tool_shed = ...``) round-trip through
    materialisation.
    """
    src = entry_attr or name

    def getter(self):
        overrides = self._overrides
        if name in overrides:
            return overrides[name]
        return getattr(self._entry, src)

    if mutable:

        def setter(self, value):
            self._overrides[name] = value

        return property(getter, setter)
    return property(getter)


class LazyTool:
    """Lightweight stand-in for ``galaxy.tools.Tool`` backed by a ``ToolIndexEntry``.

    Returned by :meth:`LazyToolBox.create_tool` whenever the tool's source is
    already persisted in the tool source store. The eager
    ``AbstractToolBox._init_tools_from_configs`` pipeline reads and mutates
    only a narrow attribute surface; ``LazyTool`` forwards every read off
    ``ToolIndexEntry`` and stores writes in ``_overrides`` so they are
    re-applied if the stub is later materialised.

    **Permissive by default:** an attribute outside the stub surface and not
    in ``_MATERIALIZE_OK`` materialises a real Tool with a WARN log. Set
    ``LAZY_TOOL_STRICT=1`` to raise :class:`NotImplementedError` instead, so
    unaccounted reads show up as clear failures rather than silent
    multi-second parse stalls.
    """

    __slots__ = ("_entry", "_materialize_cb", "_is_admin_user", "_overrides", "_real", "_lineage")

    # ``watch_tool`` iterates ``tool._macro_paths`` for file-watching; lazy
    # entries are content-addressed in the store, file-watching is a no-op.
    # Class-level so it isn't writable on the instance.
    _macro_paths: tuple = ()

    # Methods / properties we accept will materialise a real Tool. Add to
    # this set only when the parse cost is genuinely warranted at the call
    # site — generally the tool-execution path (``handle_input``, the
    # parameter machinery) and admin/container endpoints that need the
    # fully-parsed Tool.
    _MATERIALIZE_OK = frozenset(
        {
            "to_archive",  # tool packaging endpoint
            "build_dependency_cache",  # explicit cache-warming
            "tool_requirements",  # container_resolvers/toolbox admin endpoint
            "containers",  # container resolution
            "requirements",  # alias used by some callers
            # Tool-execution path. ``/api/tools/{id}`` POST → ``handle_input``
            # → ``inputs`` / ``parameters`` / ``new_state`` / ``input_translator``.
            # Materialising here is right: the caller is about to execute the
            # tool, which fundamentally needs the parsed parameter tree.
            "handle_input",
            "inputs",
            "parameters",
            "new_state",
            "input_translator",
            "check_and_update_param_values",  # validation called from handle_input
            "wants_params_cleaned",  # parameter scrub before execution
            "tool_source",  # raw ToolSource; some callers walk it directly
            "dynamic_tool",  # dynamic-tool linkage on execution
            "produces_entry_points",  # interactive tool entry points
            "execute",  # actual tool execute method
            "expand_incoming",  # parameter expansion for multi-run/map
            "params_to_strings",  # parameter serialisation
            "tool_action",  # execution action dispatch
            "tool_dir",  # on-disk tool directory accessor
            "completed_jobs",  # job-search via tool
            "get_default_history_by_trans",  # default-history lookup on execute
            "regenerate_imported_metadata_if_needed",  # import/export path
            "outputs",  # output spec read by execute / display
            "tests",  # tool test definitions read by /api/tools tests endpoints
            "to_json",  # tool JSON serialisation
            "tool_requirements_status",  # /api/tools requirements_status
            "provided_metadata_file",  # job-runner metadata path
            "test_data_path",  # tool test data lookup
            "get_configured_job_handler",  # job-runner handler routing
            # Job runner reads this on the tool to decide environment setup.
            "requires_galaxy_python_environment",
            # Job-setup dependency/env path: the runner builds the dependency
            # shell commands for the tool it's about to run (including the
            # internal ``__SET_METADATA__`` tool that follows most jobs), which
            # needs the parsed requirements. Materialising here is correct — the
            # tool is executing.
            "build_dependency_shell_commands",
            # Parameter-validation path (data-manager / index-file tools): both
            # walk the parsed parameter tree to check tool params against loaded
            # data tables / index files at job time.
            "params_with_missing_data_table_entry",
            "params_with_missing_index_file",
            # Admin dependency-management endpoints (install_dependencies /
            # uninstall_dependencies) drive the resolver view on the tool.
            "_view",
        }
    )

    # --- forwarded read-only entry surface ---
    id = _entry_attr("id")
    uuid = _entry_attr("uuid")
    name = _entry_attr("name", mutable=True)
    description = _entry_attr("description")
    tool_type = _entry_attr("tool_type")
    tags = _entry_attr("tags")
    require_login = _entry_attr("require_login")
    edam_operations = _entry_attr("edam_operations")
    edam_topics = _entry_attr("edam_topics")
    icon = _entry_attr("icon")
    xrefs = _entry_attr("xrefs")
    is_workflow_compatible = _entry_attr("is_workflow_compatible")

    # --- forwarded mutable entry surface ---
    # Eager ``_load_tool_tag_set`` (base.py:964-987) mutates these post-create.
    version = _entry_attr("version", mutable=True)
    hidden = _entry_attr("hidden", mutable=True)
    labels = _entry_attr("labels", mutable=True)
    tool_shed = _entry_attr("tool_shed", mutable=True)
    repository_name = _entry_attr("repository_name", mutable=True)
    repository_owner = _entry_attr("repository_owner", mutable=True)
    # Eager naming: ``installed_changeset_revision`` (vs entry's ``changeset_revision``).
    installed_changeset_revision = _entry_attr(
        "installed_changeset_revision",
        entry_attr="changeset_revision",
        mutable=True,
    )

    def __init__(self, entry: "ToolIndexEntry", materialize_callback, is_admin_user) -> None:
        self._entry = entry
        self._materialize_cb = materialize_callback
        self._is_admin_user = is_admin_user
        self._overrides: dict[str, Any] = {}
        self._real: Tool | None = None
        # Assigned by AbstractToolBox.__add_tool via _lineage_map.register(tool).
        self._lineage: Any | None = None

    # --- derived properties ---
    @property
    def guid(self):
        return self._overrides.get("guid") or (self._entry.id if "/repos/" in self._entry.id else None)

    @guid.setter
    def guid(self, value):
        self._overrides["guid"] = value

    @property
    def old_id(self) -> str:
        if "old_id" in self._overrides:
            return self._overrides["old_id"]
        short = extract_short_id_from_guid(self._entry.id)
        return short or self._entry.id

    @property
    def tool_tags(self) -> list[str]:
        # Mirror ``Tool.__init__``'s ``all_ids`` construction: the curated
        # tag mapping is keyed purely by tool id, so the stub can answer
        # ``AbstractToolBox.curated_tool_tags``'s full-toolbox sweep without
        # materialising anything.
        if "tool_tags" in self._overrides:
            return self._overrides["tool_tags"]
        tool_id = (self._entry.id or "").lower()
        if not tool_id:
            return []
        all_ids = [tool_id]
        old_id = self.old_id.lower()
        if old_id and old_id != tool_id:
            all_ids = [tool_id, tool_id.rsplit("/", 1)[0], old_id]
        return curated_tool_tags(all_ids)

    @tool_tags.setter
    def tool_tags(self, value):
        self._overrides["tool_tags"] = value

    @property
    def config_file(self) -> str | None:
        # ``source_path`` is stamped by the populator; entries serialized
        # before the field existed deserialize as ``None`` and callers that
        # need a real path fall through to ``__getattr__`` and materialise.
        return self._entry.source_path

    @property
    def lineage(self):
        return self._lineage

    def get_panel_section(self) -> tuple[str, str] | tuple[None, None]:
        """Answer the tool's ``(section_id, section_name)`` off the entry.

        ``Tool.get_panel_section`` resolves this through
        ``toolbox.get_section_for_tool`` (a panel lookup), but the populator
        already stamps the placement onto ``ToolIndexEntry``. Full-toolbox
        sweeps read this — e.g. ``AgentTools.get_tool_categories`` iterates
        ``toolbox.tools()`` and reads ``get_panel_section()[1]`` per tool —
        so forwarding off the entry keeps that O(N) walk from materialising
        every tool.
        """
        entry = self._entry
        if entry.panel_section_id:
            return (entry.panel_section_id, entry.panel_section_name or "")
        return (None, None)

    @property
    def version_object(self):
        # Mirror ``Tool.version_object`` (lib/galaxy/tools/__init__.py:1213).
        # ``to_panel_view`` walks ``_lineage_in_panel`` → ``_newer_tool`` which
        # compares ``tool.version_object``; computing it off the entry's
        # ``version`` string keeps the stub self-sufficient.
        GALAXY_VERSION_SUFFIX = "+galaxy"
        version = self._entry.version or ""
        if GALAXY_VERSION_SUFFIX not in version:
            return parse_version(version)
        base_version, suffix = version.split(GALAXY_VERSION_SUFFIX, 1)
        if suffix:
            # PEP-440 numeric sort hint — keep the eager Tool's behaviour.
            version = f"{base_version}{GALAXY_VERSION_SUFFIX}.{suffix.lstrip('.')}"
        return parse_version(version)

    @property
    def tool_shed_repository(self):
        # The eager pipeline sets this on the real ``Tool`` for shed-installed
        # tools (passing ``tool_shed_repository=<repo>`` to ``create_tool``);
        # the LazyTool stub doesn't carry the repo object. Default to None —
        # callers that need a real ``ToolShedRepository`` go through
        # materialisation via ``_materialize_for_lazy_tool``, which routes the
        # repo lookup via ``_lookup_tool_shed_repository``.
        return self._overrides.get("tool_shed_repository")

    @tool_shed_repository.setter
    def tool_shed_repository(self, value):
        self._overrides["tool_shed_repository"] = value

    @property
    def tool_errors(self):
        return self._overrides.get("tool_errors")

    @tool_errors.setter
    def tool_errors(self, value):
        self._overrides["tool_errors"] = value

    # --- entry-only methods (no materialise) ---
    def allow_user_access(self, user, attempting_access: bool = True) -> bool:
        """Mirror of :meth:`Tool.allow_user_access` derived from index metadata.

        ``DataManagerTool`` overrides ``allow_user_access`` to require admin
        (lib/galaxy/tools/__init__.py:3893). On the stub we can't dispatch
        polymorphically on subclass, so branch on ``tool_type`` instead.
        ``dynamic_tool`` (unprivileged-tool gating) is not in the index — fall
        through to materialise via ``__getattr__`` for that one case if a
        caller passes a dynamic tool. Stock filters never do.
        """
        if self.require_login and user is None:
            return False
        if self.tool_type == "manage_data":
            if user is None or not bool(self._is_admin_user(user)):
                if attempting_access:
                    log.debug(
                        "User (%s) attempted to access a data manager tool (%s), but is not an admin.",
                        getattr(user, "id", None),
                        self.id,
                    )
                return False
        return True

    def to_panel_entry(self, trans=None) -> dict[str, Any]:
        """Cheap entry-shape dict for the panel-view walk.

        Returned by :meth:`AbstractToolBox.get_tool_to_dict` when no help
        payload was requested. Stays off the materialise path entirely so
        ``/api/tool_panels/{view}`` and ``/api/tools?in_panel=true`` don't
        parse every tool on the first request.
        """
        entry = self._entry
        if self._lineage is not None:
            versions = list(self._lineage.tool_versions)
        else:
            versions = [entry.version] if entry.version else []
        payload = {
            "model_class": entry.model_class,
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "labels": self.labels if self.labels else [],
            "icon": entry.icon,
            "edam_operations": entry.edam_operations or [],
            "edam_topics": entry.edam_topics or [],
            "hidden": self.hidden,
            "is_workflow_compatible": entry.is_workflow_compatible,
            "xrefs": entry.xrefs or [],
            "versions": versions,
            "hidden_versions": [],
            "link": f"/tool_runner?tool_id={self.id}",
            "panel_section_id": entry.panel_section_id,
            "panel_section_name": entry.panel_section_name,
            "form_style": entry.form_style,
        }
        if entry.uuid:
            payload["uuid"] = entry.uuid
        if entry.tool_shed:
            payload["tool_shed_repository"] = {
                "name": entry.repository_name,
                "owner": entry.repository_owner,
                "changeset_revision": entry.changeset_revision,
                "tool_shed": entry.tool_shed,
            }
        if trans is not None and getattr(trans, "user_is_admin", False):
            payload["config_file"] = entry.source_path
        return payload

    def to_dict(self, trans=None, link_details: bool = False, tool_help: bool = False, **kw) -> dict[str, Any]:
        """Materialise and delegate — ``/api/tools/{id}`` contract.

        The show endpoint ships ``xrefs`` / ``versions`` /
        ``is_workflow_compatible`` / ``tool_shed_repository`` / ``inputs``
        / ``outputs`` even with ``io_details=False``, so the parsed Tool
        has to do the serialisation. The cheap panel-view path lives in
        :meth:`to_panel_entry`; only ``to_dict`` materialises.

        On materialise failure (tool XML the parameter factory can't
        handle — ``upload_dataset``, ``column="value"`` against an
        unresolvable column-name spec, …) fall back to the entry shape
        so the caller still gets a renderable response; eager mode
        catches the same in ``_load_tool_tag_set`` and drops the tool
        from ``_tools_by_id``.
        """
        try:
            return self._materialize().to_dict(trans, link_details=link_details, tool_help=tool_help, **kw)
        except Exception as e:
            log.warning("LazyTool.to_dict: materialise failed for %s, falling back to entry: %s", self.id, e)
            return self.to_panel_entry(trans)

    # --- materialisation ---
    def _materialize(self) -> "Tool":
        if self._real is None:
            real = self._materialize_cb(self._entry)
            # Re-apply mutations the eager pipeline recorded against the stub
            # before materialise (``hidden``, ``labels``, shed metadata, etc.).
            for name, value in self._overrides.items():
                try:
                    setattr(real, name, value)
                except Exception:
                    log.debug("LazyTool._materialize could not re-apply override %r on %s", name, self.id)
            if self._lineage is not None:
                real._lineage = self._lineage
            self._real = real
        return self._real

    # --- strict fallthrough ---
    def __getattr__(self, name: str):
        if name in self._MATERIALIZE_OK:
            return getattr(self._materialize(), name)
        # Other private/dunder attrs are never materialise triggers — surface
        # as ``AttributeError`` so e.g. ``hasattr(tool, "__something__")``
        # stays cheap.
        if name.startswith("_"):
            raise AttributeError(name)
        if _LAZY_TOOL_PERMISSIVE:
            log.warning(
                "LazyTool.%r forced materialise of tool %r (LAZY_TOOL_PERMISSIVE=1); "
                "add to the stub surface or _MATERIALIZE_OK to make this explicit.",
                name,
                self.id,
            )
            return getattr(self._materialize(), name)
        raise NotImplementedError(
            f"LazyTool.{name!r} is not on the stub surface for tool {self.id!r}. "
            f"If this attribute can be read off ToolIndexEntry, add a forwarded "
            f"property; if it genuinely needs a parsed Tool, add it to "
            f"LazyTool._MATERIALIZE_OK. Set LAZY_TOOL_PERMISSIVE=1 to bypass "
            f"this check while debugging."
        )


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
        tool_source_store: ToolSourceStore | None,
        cache_size: int = 500,
        save_integrated_tool_panel: bool = True,
    ) -> None:
        # Lazy-only state set BEFORE ``super().__init__`` because the
        # eager ``_init_tools_from_configs`` (which super invokes mid-init)
        # is overridden below to consult ``self._store`` and populate
        # ``self._tool_index``.
        self._store = tool_source_store
        self._tool_object_cache: LRUCache = LRUCache(maxsize=cache_size)
        self._cache_lock = threading.RLock()
        # Count of stubs promoted to real ``Tool`` objects since boot — every
        # runtime materialise funnels through ``_create_tool_from_stored_source``.
        # Batch/read endpoints must never move this counter; the integration
        # suite asserts a zero delta across them to catch an accidental
        # whole-toolbox sweep that ``LAZY_TOOL_STRICT`` alone can't (a legit
        # ``_MATERIALIZE_OK`` attr read in a loop, or a tool-filter that parses).
        self._lazy_materialize_count = 0
        # ``_tool_index`` is filled by our ``_init_tools_from_configs`` override
        # before the eager walk runs.
        self._tool_index: ToolIndex | None = None
        # Mirror the eager toolbox's short-id → Tool mapping so
        # ``GET /api/tools/<short_id>`` resolves shed installs even when
        # only the guid landed in the panel. Filled after the eager walk
        # via ``_rebuild_shed_short_id_map``.
        self._shed_short_id_to_guids: dict[str, set[str]] = {}
        self._store_watcher: ToolSourceStoreWatcher | None = None
        # Identity-keyed cache of every indexed ``source_path`` — see
        # ``_index_source_paths``. Set before ``super().__init__`` because
        # the eager walk consults it through ``_tool_file_on_disk``.
        self._index_source_paths_cache: tuple[ToolIndex, set[str]] | None = None
        # Versionless-guid → sibling versions map, keyed on index identity
        # plus entry count — see ``_guid_sibling_versions``. Also consulted
        # during ``super().__init__`` (panel views resolve lineages
        # mid-walk).
        self._guid_sibling_versions_cache: tuple[ToolIndex, int, dict[str, list[tuple[str, str]]]] | None = None

        # Eager init — its ``_init_tools_from_configs`` is overridden so the
        # walk goes through our ``create_tool`` seam and hands back LazyTool
        # stubs for indexed sources.
        super().__init__(
            config_filenames=config_filenames,
            tool_root_dir=tool_root_dir,
            app=app,
            save_integrated_tool_panel=save_integrated_tool_panel,
        )

        # Post-eager-walk: build the short-id lookup from whatever guids
        # the panel pass registered. Section metadata, conf-level hidden,
        # and labels are already on the index entries (the populator stamps
        # them at discovery time), so no post-walk sync is needed.
        self._rebuild_shed_short_id_map()

        log.info(
            "LazyToolBox initialized with %d tools (cache_size=%d, parsed=%d, from_store=%d)",
            len(self._tools_by_id),
            cache_size,
            self._tools_parsed_from_file,
            self._tools_loaded_from_store,
        )

        self._start_store_watcher()

    def _start_store_watcher(self) -> None:
        """Poll externally-published stores for freshness-token changes.

        Only read-only members with a probe are watched: writable stores
        change through this process's own populate paths, which broadcast
        their own reloads, and CVMFS (the read-only publishing model)
        delivers no filesystem events to react to — polling one
        extended-attribute read per store per tick is the whole cost.
        """
        if not self.app.config.watch_tool_source_stores:
            return
        if not isinstance(self._store, CompositeToolSourceStore):
            log.info("watch_tool_source_stores is enabled but no named tool source stores are configured")
            return
        members = [(n, m) for n, m in self._store.members if m.read_only and m.has_freshness_probe]
        if not members:
            log.info("watch_tool_source_stores is enabled but no read-only store declares a freshness probe")
            return
        self._store_watcher = ToolSourceStoreWatcher(
            members=members,
            interval=self.app.config.tool_source_store_watch_interval,
            on_change=self._on_store_freshness_change,
        )
        self._store_watcher.start()
        log.info(
            "Watching tool source store(s) %s for freshness changes every %gs",
            sorted(n for n, _ in members),
            self.app.config.tool_source_store_watch_interval,
        )

    def _on_store_freshness_change(self, changed_names: list[str]) -> None:
        """A watched store was republished: reload index state and search.

        ``invalidate_index_cache`` handles the reload dance (it also
        disposes read-only members' engines — see there). The whoosh
        rebuild runs here rather than in the reload path because only a
        republished store can grow the corpus without a local populate;
        its corpus-signature check makes re-runs no-ops, and concurrent
        rebuilds from peer processes degrade to one winner (whoosh lock,
        errors swallowed and logged by ``build_whoosh_for_store``).
        """
        self.invalidate_index_cache()
        if not isinstance(self._store, CompositeToolSourceStore):
            return
        for name, member in self._store.members:
            if name not in changed_names:
                continue
            index = member.load_index()
            if index is not None:
                build_whoosh_for_store(self.app.config, name, index)

    def _init_tools_from_configs(self, config_filenames: list[str]) -> None:
        """Load the persistent ``ToolIndex`` before delegating to the eager walk.

        Cold-start safety net: if the index doesn't yet cover every tool the
        configs reference (fresh checkout, a new conf entry, a wiped store),
        invoke the populator in-process to fill the gap. The populator is
        content-addressed and idempotent, so re-runs on a warm store only
        touch the new rows.

        After this returns, the eager pipeline calls into ``create_tool`` for
        every ``<tool>`` it walks. The seam short-circuits indexed sources to
        a :class:`LazyTool` stub; misses raise — by contract the cold-start
        populator below guarantees coverage.
        """
        # Replace the plain ``LineageMap`` the base ``__init__`` just
        # assigned: ``LazyLineageMap`` sources each lineage's version set
        # from ``entries_by_version`` at lookup time, so post-boot lookups
        # (peer installs surfaced by ``invalidate_index_cache``, reloads)
        # see every indexed version instead of a memoised single-version
        # lineage built from one Tool object.
        self._lineage_map = LazyLineageMap(self.app, versions_for=self._index_versions_for)
        self._tool_panel_loaded_from_index = False
        if self._store is not None:
            self._tool_index = self._store.load_index() or ToolIndex()
            if self._index_needs_population():
                self._run_inline_populator()
                # The populator writes through its own store instances; drop
                # this store's cached index so the re-load below reads the
                # index the populator just persisted rather than the (possibly
                # foreign, shared-database) index cached two lines up.
                self._store.invalidate_index_cache()
                self._tool_index = self._store.load_index() or ToolIndex()
        else:
            self._tool_index = ToolIndex()
        if self._init_tools_from_index(config_filenames):
            return
        super()._init_tools_from_configs(config_filenames)

    def _init_tools_from_index(self, config_filenames: list[str]) -> bool:
        """Register lazy stubs directly from a fresh index.

        The generic toolbox walk still parses every tool-conf item and routes
        each tool through ``load_item``. In lazy mode, a populated source-store
        index already carries the panel placements (``ToolIndex.panel_items``)
        the walk would produce, so replay those instead. If the index predates
        placement recording, return ``False`` and let the parent
        implementation take the conservative path.
        """
        placements = self._index_panel_items()
        if not placements:
            return False
        # ``_index_panel_items`` only returns placements when the index is
        # populated, so it is non-None here.
        assert self._tool_index is not None
        missing = {p.tool_id for p in placements if p.tool_id not in self._tool_index.entries}
        if missing:
            log.info(
                "LazyToolBox fast panel init found %d panel ids missing from index; running populator",
                len(missing),
            )
            self._run_inline_populator()
            if self._store is not None:
                self._store.invalidate_index_cache()
                self._tool_index = self._store.load_index() or ToolIndex()
            placements = self._index_panel_items()
            missing = {p.tool_id for p in placements if p.tool_id not in self._tool_index.entries}
            if missing or not placements:
                log.debug("LazyToolBox fast panel init disabled; %d panel ids still missing from index", len(missing))
                return False
        assert self._tool_index is not None
        self._init_dynamic_tool_confs_without_loading(config_filenames)
        stubs_by_id: dict[str, LazyTool] = {}
        for entry in self._tool_index.entries.values():
            stubs_by_id[entry.id] = self._register_lazy_entry(entry, place_in_panel=False)
        placed = 0
        for placement in placements:
            stub = stubs_by_id.get(placement.tool_id)
            if stub is None:
                continue
            self._place_stub(stub, placement.section_id, placement.section_name, hidden=placement.hidden)
            placed += 1
        log.debug(
            "LazyToolBox registered %d indexed tools (%d panel placements) without walking tool conf items",
            len(stubs_by_id),
            placed,
        )
        self._tool_panel_loaded_from_index = True
        return True

    def _load_tool_panel(self) -> None:
        if getattr(self, "_tool_panel_loaded_from_index", False):
            return
        super()._load_tool_panel()

    def _index_panel_items(self) -> list[ToolPanelItem]:
        """The index's conf-ordered panel placements, latest version only.

        Placements of non-newest versions of a lineage are dropped the same
        way the old id-based fast path collapsed them — the panel shows the
        latest version, older ones stay reachable through the lineage.
        """
        if self._tool_index is None:
            return []
        placements = self._tool_index.panel_items
        if not placements:
            return []
        ordered_ids: list[str] = []
        seen: set[str] = set()
        for placement in placements:
            if placement.tool_id in seen:
                continue
            seen.add(placement.tool_id)
            ordered_ids.append(placement.tool_id)
        keep = set(self._latest_panel_tool_ids(ordered_ids))
        return [placement for placement in placements if placement.tool_id in keep]

    def _latest_panel_tool_ids(self, tool_ids: list[str]) -> list[str]:
        if self._tool_index is None:
            return tool_ids
        ordered_lineages: list[tuple[str | None, str]] = []
        latest_by_lineage: dict[tuple[str | None, str], ToolIndexEntry] = {}
        for tool_id in tool_ids:
            entry = self._tool_index.entries.get(tool_id)
            if entry is None or entry.hidden:
                continue
            lineage_id = remove_version_from_guid(entry.id) or entry.id
            lineage_key = (entry.panel_section_id, lineage_id)
            current = latest_by_lineage.get(lineage_key)
            if current is None:
                ordered_lineages.append(lineage_key)
                latest_by_lineage[lineage_key] = entry
            elif self._index_entry_newer(entry, current):
                latest_by_lineage[lineage_key] = entry
        return [latest_by_lineage[lineage_key].id for lineage_key in ordered_lineages]

    def _index_entry_newer(self, entry: ToolIndexEntry, other: ToolIndexEntry) -> bool:
        try:
            return parse_version(entry.version or "0") > parse_version(other.version or "0")
        except Exception:
            return (entry.version or "") > (other.version or "")

    def _init_dynamic_tool_confs_without_loading(self, config_filenames: list[str]) -> None:
        config_filenames = listify(config_filenames)
        config_directories = [config_filename for config_filename in config_filenames if os.path.isdir(config_filename)]
        config_filenames = [
            config_filename for config_filename in config_filenames if config_filename not in config_directories
        ]
        for config_directory in config_directories:
            directory_contents = sorted(os.listdir(config_directory))
            directory_config_files = [config_file for config_file in directory_contents if config_file.endswith(".xml")]
            config_filenames.extend(directory_config_files)
        for config_filename in config_filenames:
            if not self.can_load_config_file(config_filename):
                continue
            self._init_dynamic_tool_conf_without_loading(config_filename)

    def _init_dynamic_tool_conf_without_loading(self, config_filename: str) -> None:
        try:
            tool_conf_source = get_toolbox_parser(config_filename)
        except OSError as exc:
            dynamic_confs = (self.app.config.shed_tool_config_file, self.app.config.migrated_tools_config)
            if config_filename in dynamic_confs and exc.errno == errno.ENOENT:
                stcd = dict(
                    config_filename=config_filename,
                    tool_path=self.app.config.shed_tools_dir,
                    config_elems=[],
                    create=SHED_TOOL_CONF_XML.format(shed_tools_dir=self.app.config.shed_tools_dir),
                )
                self._dynamic_tool_confs.append(stcd)
                return
            raise
        if not tool_conf_source.is_shed_tool_conf() or not os.access(config_filename, os.W_OK):
            return
        tool_path = resolve_tool_path(tool_conf_source.parse_tool_path(), config_filename, self._tool_root_dir)
        config_elems = [item.elem for item in tool_conf_source.parse_items() if item.has_elem]
        self._dynamic_tool_confs.append(
            dict(
                config_filename=config_filename,
                tool_path=tool_path,
                config_elems=config_elems,
            )
        )

    def _index_needs_population(self) -> bool:
        """Return True when at least one config-discovered tool path is absent
        from the store.

        The stored paths are fetched as one bulk set up front
        (``list_source_paths``) so the conf walk costs a set lookup per tool
        instead of a store query per tool — on a CVMFS-scale deployment the
        per-tool round trips dominated boot time.

        Confs routed to read-only stores are not walked at all: the
        populator can't write those stores, so a miss there could never be
        healed — their coverage is the trust/schema gate's job
        (``index_is_fresh``), and any genuinely missing tool falls through
        to the eager parse in ``create_tool``.
        """
        if self._store is None:
            return False
        if not self._tool_index or not self._tool_index.entries:
            return True
        # Freshness fast path: read-only members are trusted whenever their
        # index loads (published together with their tools — the CVMFS
        # model); writable members compare their probe against the token
        # the populator stamped. When every member reports fresh, the store
        # provably covers the current tree — skip the conf walk (and its
        # per-file existence stats) entirely. See
        # ``galaxy.tools.source_store.freshness``.
        fresh = self._store.index_is_fresh()
        if fresh is True:
            if self._writable_store_index_needs_population():
                return True
            log.info("Tool source store index is fresh; skipping index coverage scan")
            return False
        if fresh is False:
            log.info("Tool source store index is stale; running populator")
            return True
        try:
            stored_paths = self._store.list_source_paths()
            only_confs = None
            if isinstance(self._store, CompositeToolSourceStore):
                read_only_stores = self._store.read_only_member_names
                if read_only_stores:
                    conf_to_store = conf_to_store_map(self.app.config)
                    only_confs = {c for c, name in conf_to_store.items() if name not in read_only_stores}
            for d in discover_tools(self.app.config, only_confs=only_confs):
                if d.path not in stored_paths:
                    return True
        except Exception as e:
            log.warning("Index coverage check raised; running populator defensively: %s", e)
            return True
        return False

    def _writable_store_index_needs_population(self) -> bool:
        """Return True when an index entry references a source the store lost.

        The invariant that matters is one-directional: every ``source_hash``
        the index references must resolve to a stored row, or materialising
        that tool would fail. The reverse is not staleness — the store is
        append-only (only ``reconcile_index`` prunes), so rows orphaned by a
        content change, an ad-hoc self-heal superseded by conf context, or an
        uninstall accumulate legitimately. A symmetric comparison here turned
        one such orphan into a full inline repopulate on every boot and
        reload, permanently defeating the freshness-token scan skip.
        """
        if self._store is None:
            return False
        stores = (
            self._store.members if isinstance(self._store, CompositeToolSourceStore) else [("__default__", self._store)]
        )
        for store_name, store in stores:
            if store.read_only:
                continue
            source_hashes = set(store.list_all())
            index = store.load_index()
            index_hashes: set[str] = set()
            if index is not None:
                index_hashes.update(entry.source_hash for entry in index.entries.values() if entry.source_hash)
                for versions in index.entries_by_version.values():
                    index_hashes.update(entry.source_hash for entry in versions.values() if entry.source_hash)
            dangling = index_hashes - source_hashes
            if dangling:
                log.info(
                    "Tool source store index for %s references %d source(s) missing from the store "
                    "(%d indexed, %d stored); running populator",
                    store_name,
                    len(dangling),
                    len(index_hashes),
                    len(source_hashes),
                )
                return True
            orphaned = len(source_hashes - index_hashes)
            if orphaned:
                log.debug(
                    "Tool source store %s holds %d source row(s) no index entry references "
                    "(superseded content or ad-hoc rows; reconcile_index prunes them)",
                    store_name,
                    orphaned,
                )
        return False

    def _run_inline_populator(self) -> None:
        """Cold-start hook: write the index + whoosh in this process.

        Wraps ``populator.populate_store_inline`` so boot can use the same
        single-writer machinery as the CLI script and the shed-install
        reroute. Failures here surface to the operator: the eager walk that
        follows calls ``create_tool``, which falls through to the parent
        on miss — a broken populator surfaces immediately on first tool
        load instead of degrading silently.
        """
        log.info("LazyToolBox: running populator inline to backfill the index")
        populate_store_inline(
            self.app.config,
            rebuild_whoosh=True,
        )

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
            versionless = remove_version_from_guid(tool_id)
            if versionless:
                for entry_id, version in self._guid_sibling_versions().get(versionless, ()):
                    if entry_id != tool_id and version not in result:
                        result.append(version)
        return result

    def _guid_sibling_versions(self) -> dict[str, list[tuple[str, str]]]:
        """Versionless guid → ``(entry_id, version)`` of every indexed sibling.

        ``_index_versions_for`` used to prefix-scan all index entries per
        lineage lookup; the EDAM panel views resolve a lineage per shed
        tool, which made boot quadratic in installed-tool count (~11k
        scans over ~9k entries profiled as the single largest toolbox
        cost). Keyed on index identity *and* entry count — reloads swap
        the ``ToolIndex`` object, while registrations and removals mutate
        membership in place; in-place removals additionally reset the
        cache explicitly (a pop-then-add could keep the count stable).
        """
        index = self._tool_index
        if index is None:
            return {}
        cached = self._guid_sibling_versions_cache
        if cached is not None and cached[0] is index and cached[1] == len(index.entries):
            return cached[2]
        siblings: dict[str, list[tuple[str, str]]] = {}
        for entry_id, entry in index.entries.items():
            if "/repos/" not in entry_id or not entry.version:
                continue
            versionless = remove_version_from_guid(entry_id)
            if versionless:
                siblings.setdefault(versionless, []).append((entry_id, entry.version))
        self._guid_sibling_versions_cache = (index, len(index.entries), siblings)
        return siblings

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

    # === Override get_tool for lazy loading ===

    @overload
    def get_tool(
        self,
        tool_id: str | None = None,
        tool_version: str | None = None,
        tool_uuid: UUID | str | None = None,
        get_all_versions: Literal[False] = False,
        exact: bool | None = False,
        user: Optional["User"] = None,
    ) -> Optional["Tool"]: ...

    @overload
    def get_tool(
        self,
        tool_id: str | None = None,
        tool_version: str | None = None,
        tool_uuid: UUID | str | None = None,
        get_all_versions: Literal[True] = True,
        exact: bool | None = False,
        user: Optional["User"] = None,
    ) -> list["Tool"]: ...

    def get_tool(
        self,
        tool_id: str | None = None,
        tool_version: str | None = None,
        tool_uuid: UUID | str | None = None,
        get_all_versions: bool | None = False,
        exact: bool | None = False,
        user: Optional["User"] = None,
    ) -> Optional["Tool"] | list["Tool"]:
        """
        Get a tool, loading from store on-demand if needed.

        Overrides ToolBox.get_tool to implement lazy loading.
        """
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
                    # ``galaxy.tool_util.version.parse_version`` matches what
                    # the eager ToolLineage uses to order versions and
                    # tolerates non-numeric segments (e.g. ``"1.0.0+galaxy0"``)
                    # via ``LegacyVersion`` fallback.
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

    # === create_tool seam: return LazyTool stub when the index already has the source ===

    def create_tool(self, config_file, tool_shed_repository=None, guid=None, **kwds) -> "Tool":
        """Return a :class:`LazyTool` for every indexed tool source.

        The populator (cold-start in :meth:`_init_tools_from_configs`, shed
        installs via ``tool_panel_manager.add_to_tool_panel``) is the single
        writer of the index. Hidden lib tools (``set_metadata_tool.xml``,
        ``data_fetch``, history import/export) are indexed via
        ``galaxy.tools.special_tools.hidden_lib_tool_paths``, so the
        post-boot ``load_hidden_lib_tool`` calls resolve through the seam
        too. A miss for a file that exists on disk self-heals through a
        single-path populate (:meth:`_populate_adhoc_path`) — shed installs
        load cloned tools during metadata generation, before any conf is
        persisted. A miss for anything else is a contract failure and
        raises.
        """
        entry = self._resolve_index_entry(config_file, guid)
        if entry is None and config_file is not None and os.path.exists(str(config_file)):
            # The file is real but the index doesn't know it. The main
            # legitimate path here is a shed install: metadata generation
            # (``installed_repository_metadata_manager.get_repository_tools_tups``)
            # loads the freshly cloned tools *before* ``add_to_tool_panel``
            # persists the conf and populates. Populate this one path —
            # still through the single-writer populator — and retry.
            entry = self._populate_adhoc_path(str(config_file), guid)
        if entry is None:
            if config_file is not None and os.path.exists(str(config_file)):
                log.warning(
                    "LazyToolBox.create_tool: no index entry for %s after ad-hoc populate; parsing eagerly",
                    config_file,
                )
                return super().create_tool(config_file, tool_shed_repository=tool_shed_repository, guid=guid, **kwds)
            raise RuntimeError(
                "LazyToolBox.create_tool: no index entry for "
                f"(config_file={config_file!r}, guid={guid!r}). The populator "
                "owns the index — run scripts/tool_source/populate_store.py "
                "or, for a new Galaxy-internal lib tool, add it to "
                "galaxy.tools.special_tools.hidden_lib_tool_paths()."
            )
        data_manager_id = kwds.get("data_manager_id")
        if data_manager_id and not entry.data_manager_id:
            # ``DataManager._load_tool`` hands the ``<data_manager id>`` conf
            # id through ``load_hidden_tool``. Entries minted before any data
            # manager conf covered this tool (install-time self-heal) don't
            # carry it, and the materialise path must restore it or
            # ``DataManagerTool.exec_after_process`` falls back to the tool
            # id and misses the registry. Persist so job-handler processes
            # materialising from the shared index see it too.
            entry.data_manager_id = data_manager_id
            if self._tool_index is not None:
                # After a from_dict reload the default and per-version maps
                # hold distinct objects; the job-time materialise resolves
                # through the per-version map, so stamp its twin too.
                twin = self._tool_index.entries_by_version.get(entry.id, {}).get(entry.version or "")
                if twin is not None and twin is not entry:
                    twin.data_manager_id = data_manager_id
            if self._store is not None:
                try:
                    self._store.update_index_entry(entry)
                except Exception as e:
                    log.warning("Persisting data_manager_id for %s raised: %s", entry.id, e)
        # LazyTool is duck-typed against Tool — the eager pipeline only
        # consults attributes the stub forwards from ToolIndexEntry, with
        # mutations stored on ``_overrides``.
        return LazyTool(  # type: ignore[return-value]
            entry,
            materialize_callback=self._materialize_for_lazy_tool,
            is_admin_user=self.app.config.is_admin_user,
        )

    def load_tool_from_cache(self, config_file, recover_tool: bool = False):
        """Skip Galaxy's disk-backed ``ToolCache``.

        The index + LRU + content-addressed store already plays that role.
        Returning ``None`` keeps ``load_tool`` honest — every call lands in
        ``create_tool``, where the seam can decide stub vs real.
        """
        return None

    def add_tool_to_cache(self, tool, config_file) -> None:
        """Bypass the disk ``ToolCache`` — see :meth:`load_tool_from_cache`."""
        return None

    def _populate_adhoc_path(self, config_file: str, guid: str | None) -> ToolIndexEntry | None:
        """Index a single on-disk tool file that no conf covers yet.

        Runs the partial populator for the path (threading the guid so the
        entry is keyed like its eventual conf-driven replacement), reloads
        the index, and retries resolution. Returns the entry, or ``None``
        when the populator couldn't index the file either.
        """
        path = os.path.abspath(config_file)
        log.info("LazyToolBox: index miss for existing file %s — populating ad hoc (guid=%s)", path, guid)
        try:
            populate_for_paths(
                self.app.config,
                [path],
                path_guids={path: guid},
                app=self.app,
            )
        except Exception as e:
            log.warning("Ad-hoc populate for %s raised: %s", path, e)
            return None
        if self._store is not None:
            self._store.invalidate_index_cache()
            self._tool_index = self._store.load_index() or ToolIndex()
            self._rebuild_shed_short_id_map()
        return self._resolve_index_entry(config_file, guid)

    def _index_source_paths(self) -> set[str]:
        """Every ``source_path`` the current in-memory index covers.

        Cached against the identity of ``_tool_index``, so any reload
        (which always assigns a fresh ``ToolIndex``) refreshes it without
        reset plumbing. In-place entry removals can leave a stale extra
        path here — that only skips one stat for a tool ``create_tool``
        will then resolve or self-heal, so it is harmless.
        """
        index = self._tool_index
        if index is None:
            return set()
        cached = self._index_source_paths_cache
        if cached is not None and cached[0] is index:
            return cached[1]
        paths: set[str] = set()
        for versions in index.entries_by_version.values():
            for entry in versions.values():
                if entry.source_path:
                    paths.add(entry.source_path)
        for entry in index.entries.values():
            if entry.source_path:
                paths.add(entry.source_path)
        self._index_source_paths_cache = (index, paths)
        return paths

    def _tool_file_on_disk(self, path: str) -> bool:
        """Answer the eager walk's existence gate from the index.

        The populator established existence when it stored the source, and
        materialisation reads the raw source from the store, not the file —
        so for an index-covered tool the per-tool stat proves nothing and,
        on a CVMFS-resident shed conf, costs minutes of boot time.
        """
        if os.path.abspath(path) in self._index_source_paths():
            return True
        return os.path.exists(path)

    def _missing_repository_log_level(self, path: str) -> int:
        """Index-covered shed tools expectedly lack install-DB rows.

        A conf-provided repository (CVMFS shed conf) is never installed
        through the install database, so the eager warning would repeat
        for every one of its tools on every boot.
        """
        if os.path.abspath(path) in self._index_source_paths():
            return logging.DEBUG
        return logging.WARNING

    def _resolve_index_entry(self, config_file, guid: str | None) -> ToolIndexEntry | None:
        """Find a matching index entry for the (config_file, guid) pair, or ``None``."""
        if self._tool_index is None:
            return None
        # Shed install: guid is authoritative — keyed identically in the index.
        if guid:
            entry = self._tool_index.entries.get(guid)
            if entry is not None:
                return entry
        if config_file is None:
            return None
        config_file_str = os.path.abspath(str(config_file))
        # Exact source-path lookup against the store; ``source_path`` is set
        # by the bootstrap and the shed-install persistence hook.
        if self._store is not None:
            try:
                stored = self._store.get_by_source_path(config_file_str)
            except Exception as e:
                log.debug("get_by_source_path raised for %s: %s", config_file_str, e)
                stored = None
            if stored is not None and stored.tool_id:
                # Honor the stored source's *version* — multi-version tools
                # (same ``<tool id=foo>`` across two files at different
                # ``<tool version=...>``) have one StoredToolSource per file,
                # so ``entries.get(tool_id)`` would always hand back the
                # latest and both files would collapse to one LazyTool.
                entry = self._tool_index.get(stored.tool_id, stored.tool_version)
                if entry is not None:
                    return entry
        # No entry: do NOT fall back to parsing the id out of the file —
        # ``entries[id]`` holds only the latest version, which would collapse
        # multi-version conf entries onto one LazyTool. The store's
        # ``source_path`` index is the authoritative key; a miss means the
        # source genuinely isn't persisted yet, so let ``create_tool``'s
        # fallthrough parse and ``_persist_tool_source`` write it.
        return None

    def _materialize_for_lazy_tool(self, entry: ToolIndexEntry) -> "Tool":
        """Promote a stub to a real ``Tool`` via the existing store-backed loader.

        Routed through :meth:`_register_loaded_tool` so ``_tools_by_id`` /
        ``_tool_versions_by_id`` / ``_tools_by_old_id`` / lineage all agree
        with the eager toolbox bookkeeping.
        """
        if self._store is None:
            raise RuntimeError(f"LazyTool materialise needs a tool source store (id={entry.id!r})")
        stored = self._stored_source_for_entry(entry)
        if stored is None:
            raise RuntimeError(
                "LazyTool materialise: indexed source missing from store "
                f"(id={entry.id!r}, path={entry.source_path!r}, hash={entry.source_hash!r})"
            )
        tool = self._create_tool_from_stored_source(stored, entry=entry)
        self._register_loaded_tool(tool)
        return tool

    def _stored_source_for_entry(self, entry: ToolIndexEntry) -> StoredToolSource | None:
        """Resolve path-specific source metadata without ambiguous hash lookup."""
        if self._store is None:
            return None
        if entry.source_path is None:
            return self._store.get(entry.source_hash)
        stored = self._store.get_by_source_path(entry.source_path)
        if stored is None or stored.hash != entry.source_hash:
            return None
        return stored

    def _load_tool_on_demand(self, tool_id: str, tool_version: str | None = None) -> Optional["Tool"]:
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
        stored = self._stored_source_for_entry(entry)
        if not stored:
            log.warning(
                "Indexed tool source not found for %s (path: %s, hash: %s)",
                tool_id,
                entry.source_path,
                entry.source_hash,
            )
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

    def _create_tool_from_stored_source(self, stored: StoredToolSource, entry: ToolIndexEntry | None = None) -> "Tool":
        """Create a Tool object from stored source.

        The single chokepoint for promoting a stub to a real ``Tool`` at
        runtime — bump ``_lazy_materialize_count`` here so the budget test
        can assert batch endpoints don't materialise.
        """
        self._lazy_materialize_count += 1
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
        if entry and entry.data_manager_id:
            # The registry is keyed by the ``<data_manager id>`` conf id,
            # which may differ from the tool XML id.
            # ``DataManagerTool.__init__`` falls back to the tool id when
            # the kwd is missing and ``exec_after_process`` then can't find
            # the manager — eager threads this through ``load_hidden_tool``.
            kwds["data_manager_id"] = entry.data_manager_id
        if stored.tool_id and "/repos/" in stored.tool_id:
            kwds["guid"] = stored.tool_id
            # ``ToolConfRepository`` (lib/galaxy/tool_util/toolbox/base.py:87)
            # is the same namedtuple stub the eager pipeline hands the Tool
            # ctor for shed tools whose install-DB row hasn't materialised
            # yet — see ``AbstractToolBox.get_tool_repository_from_xml_item``.
            # ``Tool.populate_tool_shed_info`` only reads the scalar fields,
            # all of which are on ``ToolIndexEntry``; building the stub
            # directly avoids a per-materialise install-DB round-trip.
            # ``installed_tool_dependencies`` readers get ``[]`` — same
            # shape the eager pre-install code path produces.
            if entry and not entry.is_local and entry.tool_shed:
                kwds["tool_shed_repository"] = ToolConfRepository(
                    tool_shed=entry.tool_shed,
                    name=entry.repository_name,
                    owner=entry.repository_owner,
                    installed_changeset_revision=entry.changeset_revision,
                    changeset_revision=entry.changeset_revision,
                    tool_dependencies_installed_or_in_error=[],
                    repository_path=None,
                    tool_path=stored.tool_dir,
                )
        return create_tool_from_source(self.app, tool_source, **kwds)

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
        if self._store is None:
            return
        # Serialize against ``remove_tool_by_id``: an uninstall pops the
        # tool from every in-memory registry and then persists the index
        # removal. Every populate broadcasts an invalidation, so without
        # the lock a queue-worker invalidation can interleave — it reloads
        # the pre-removal index and re-registers the just-removed tool as
        # a stub (observed as test_repository_uninstall resurrecting the
        # tool right after the install's own broadcast).
        with self.app._toolbox_lock:
            try:
                # Read-only members are published externally (CVMFS); a
                # descriptor opened before the publish keeps serving the old
                # snapshot forever, so dropping pooled connections — not just
                # the cached index — is what makes the re-read below actually
                # see the new file. Writable stores were updated through this
                # process group's own connections and only need the cache drop.
                if isinstance(self._store, CompositeToolSourceStore):
                    for _name, member in self._store.members:
                        if member.read_only:
                            member.dispose()
                self._store.invalidate_index_cache()
            except Exception as e:
                log.debug(f"Store invalidate_index_cache raised: {e}")
            previous_ids = set(self._tool_index.entries) if self._tool_index is not None else set()
            loaded = self._store.load_index()
            self._tool_index = loaded if loaded is not None else ToolIndex()
            # Index just changed under us — refresh the short-id map so
            # peer-process installs (which only update the persisted index)
            # are reachable via short-id lookups in this process.
            self._rebuild_shed_short_id_map()
            # Wire newly-indexed entries (e.g. shed-install partial updates
            # from a peer process) into this process's in-memory registries
            # as ``LazyTool`` stubs. Without this, ``/api/tools`` would
            # return the new ids only after the next full toolbox boot.
            self._register_new_index_entries_as_stubs()
            # Reconcile removals: an id the previous index carried but the
            # reloaded one doesn't was removed by a peer process (uninstall).
            # Registration above is add/update-only, so without this pop the
            # stale stub would keep serving via the eager ``get_tool``
            # fall-through. Diffing the two indexes keeps this scoped to
            # store-backed tools — internal and dynamic tools never enter
            # the index, so they are untouched.
            for tool_id in previous_ids - set(self._tool_index.entries):
                if tool_id not in self._tools_by_id:
                    continue
                try:
                    self._remove_tool_in_memory(tool_id)
                except Exception as e:
                    log.warning("Reconciling peer-removed index entry %s raised: %s", tool_id, e)

    def _register_new_index_entries_as_stubs(self) -> None:
        """For every index entry not yet in ``_tools_by_id``, build a
        ``LazyTool`` stub, slot it into the toolbox registries, and place it
        under its declared panel section.

        Mirrors what the eager walk does at boot for each ``<tool>`` element,
        but for a single entry already fully described by the populator.
        """
        if self._tool_index is None:
            return
        for tool_id, entry in self._tool_index.entries.items():
            # ``Any``: the registry is typed for real Tools but holds
            # LazyTool stubs on this toolbox (same duck-typing as create_tool).
            existing: Any = self._tools_by_id.get(tool_id)
            if existing is not None:
                if isinstance(existing, LazyTool) and existing._entry is not entry:
                    # Refresh the stub in place — the panel and registries
                    # hold this object, and the reloaded index may carry an
                    # enriched entry (e.g. the conf-driven populate after a
                    # shed install adds repository metadata the install-time
                    # ad-hoc entry lacked). ``_overrides`` survive.
                    existing._entry = entry
                continue
            try:
                self._register_lazy_entry(entry)
            except Exception as e:
                log.warning("Failed to register new index entry %s: %s", tool_id, e)

    def _register_lazy_entry(self, entry: ToolIndexEntry, place_in_panel: bool = True) -> "LazyTool":
        """Construct + slot a ``LazyTool`` stub for ``entry``.

        Inverse of :meth:`_register_loaded_tool`: same bookkeeping, but for
        the stub side. Used by :meth:`invalidate_index_cache` when a
        peer-process populator run added new entries that this process should
        surface immediately.
        """
        stub = LazyTool(
            entry,
            materialize_callback=self._materialize_for_lazy_tool,
            is_admin_user=self.app.config.is_admin_user,
        )
        tool_id = entry.id
        self._tools_by_id[tool_id] = stub  # type: ignore[assignment]
        version = entry.version
        self._tool_versions_by_id.setdefault(tool_id, {})[version or ""] = stub  # type: ignore[assignment]
        old_id = stub.old_id
        # Register the old-id bucket even when ``old_id == tool_id`` — the
        # eager ``__add_tool`` does, and ``remove_tool_by_id`` unconditionally
        # removes from the bucket, so skipping it here would KeyError a later
        # removal of this stub.
        if old_id:
            bucket = self._tools_by_old_id.setdefault(old_id, [])
            if not any(getattr(t, "id", None) == tool_id for t in bucket):
                bucket.append(stub)  # type: ignore[arg-type]
        if entry.uuid:
            self._tools_by_uuid[UUID(entry.uuid)] = stub  # type: ignore[assignment]
        # Lineage: LazyLineageMap builds it from entries_by_version, which the
        # populator wrote on the previous step, so .get() returns the right
        # ToolLineage; register() is the fallback for an as-yet-unseen id.
        stub._lineage = self._lineage_map.get(tool_id) or self._lineage_map.register(stub)  # type: ignore[arg-type]
        if not place_in_panel:
            return stub
        # Place into the panel. The populator stamped panel_section_id /
        # panel_section_name onto the entry; create the ToolSection if it
        # doesn't already exist (peer-process install of the first tool in
        # a new section).
        self._place_stub(stub, entry.panel_section_id, entry.panel_section_name, hidden=False)
        return stub

    def _place_stub(
        self,
        stub: "LazyTool",
        section_id: str | None,
        section_name: str | None,
        hidden: bool,
    ) -> None:
        """Slot ``stub`` into the live and integrated tool panels.

        The integrated panel gets every placement, hidden included — the
        eager ``__add_tool`` always records walked conf tools there. It is
        the panel ``_load_tool_panel_views`` renders EDAM/static views from
        and ``_save_integrated_tool_panel`` persists, so a boot that skips
        the conf walk must fill it or every panel view renders empty.
        """
        tool_id = stub.id
        if section_id:
            integrated_section = self._integrated_tool_panel.get(section_id)
            if not isinstance(integrated_section, ToolSection):
                integrated_section = ToolSection({"id": section_id, "name": section_name or section_id})
                self._integrated_tool_panel[section_id] = integrated_section
            integrated_section.elems[f"tool_{tool_id}"] = stub
        else:
            self._integrated_tool_panel[f"tool_{tool_id}"] = stub
        if hidden:
            return
        if section_id:
            section = self._tool_panel.get(section_id)
            if not isinstance(section, ToolSection):
                section = ToolSection({"id": section_id, "name": section_name or section_id})
                self._tool_panel[section_id] = section
            section.elems.append_tool(stub)
            self._tool_panel.record_section_for_tool_id(tool_id, section_id, section.name)
        else:
            self._tool_panel[f"tool_{tool_id}"] = stub

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
            # The eager pipeline registers a LazyTool stub at boot via
            # ``register_tool``; on materialise we drop the stub so the
            # bucket doesn't end up with two entries for the same tool id
            # (``get_tool`` lineage walk would otherwise return both).
            bucket[:] = [t for t in bucket if t is not tool and getattr(t, "id", None) != tool.id]
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
        if self._store_watcher is not None:
            self._store_watcher.shutdown()
            self._store_watcher = None
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
            result = self._remove_tool_in_memory(tool_id, remove_from_panel=remove_from_panel)
            if self._store is not None:
                # The pops above are in-memory. The persisted singleton index
                # still carries the entry, and any later cache invalidation
                # (every populate broadcasts one) would reload it —
                # resurrecting an uninstalled tool.
                try:
                    self._store.remove_index_entry(tool_id)
                except Exception as e:
                    log.warning("Persisting index removal of %s raised: %s", tool_id, e)
                # Installs converge across processes because every populate
                # broadcasts an invalidation; removals must broadcast too or
                # peer web workers keep serving the uninstalled tool until an
                # unrelated populate happens to run.
                # Local import: genuine circularity — galaxy.queue_worker
                # imports LazyToolBox at module level.
                from galaxy.queue_worker import send_control_task

                try:
                    send_control_task(self.app, "reload_tool_source_cache", noop_self=True)
                except Exception as e:
                    log.warning("Broadcasting index removal of %s raised: %s", tool_id, e)
            # A toolbox reload queued before this removal (the conf write of
            # the preceding install) may already have swapped a NEW toolbox
            # into ``app.toolbox``, built from the index as it stood before
            # ``remove_index_entry`` above — with the tool still registered.
            # ``self`` is then the superseded instance and cleaning it alone
            # leaves ``app.toolbox`` serving the uninstalled tool. The swap
            # holds the same lock, so the current object is stable here.
            current = getattr(self.app, "toolbox", None)
            if current is not self and isinstance(current, LazyToolBox):
                current._remove_tool_in_memory(tool_id, remove_from_panel=remove_from_panel)
        return result

    def _remove_tool_in_memory(self, tool_id: str, remove_from_panel: bool = True):
        """Pop ``tool_id`` from every in-memory registry, panel slot and cache.

        Shared by :meth:`remove_tool_by_id` (which additionally persists the
        index removal and notifies peer processes) and by
        :meth:`invalidate_index_cache`'s reconciliation of entries a peer
        process removed from the persisted index. Caller must hold
        ``app._toolbox_lock``.
        """
        result = super().remove_tool_by_id(tool_id, remove_from_panel=remove_from_panel)
        if self._tool_index is not None:
            self._tool_index.remove_entry(tool_id)
            # In-place membership change on the same ToolIndex object: the
            # identity-keyed sibling-versions cache would otherwise keep
            # serving the removed version to lineage lookups.
            self._guid_sibling_versions_cache = None
        # ``super().remove_tool_by_id`` clears ``_tools_by_id`` but leaves
        # ``_tool_versions_by_id`` and the lineage map intact. ``get_tool``'s
        # fall-through walks lineage versions via ``_tool_from_lineage_version``
        # which reads ``_tool_versions_by_id``, so the tool would otherwise
        # come back from there even after removal.
        self._tool_versions_by_id.pop(tool_id, None)
        if hasattr(self, "_lineage_map"):
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
        # The short-id bucket is keyed by ``old_id`` — for a shed guid
        # that's the short tool id, not ``tool_id``. ``super()`` removes
        # from it by object identity only, which misses when the bucket
        # holds an earlier registration (stub or materialised instance)
        # while ``_tools_by_id`` held a fresher one; the leftover then
        # resurrects the uninstalled tool via the eager get_tool
        # fall-through. Scrub every object belonging to this guid, but
        # leave sibling installs (other guids, other versions) alone.
        short_id = extract_short_id_from_guid(tool_id)
        if short_id and short_id != tool_id:
            bucket = self._tools_by_old_id.get(short_id)
            if bucket:
                survivors = [
                    t for t in bucket if getattr(t, "id", None) != tool_id and getattr(t, "guid", None) != tool_id
                ]
                if survivors:
                    self._tools_by_old_id[short_id] = survivors
                else:
                    del self._tools_by_old_id[short_id]
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
            # Purge by cached identity, not by key prefix: the LRU is
            # keyed by whatever id the caller resolved with, so the same
            # tool can sit under both its guid and its short id
            # ("collection_column_join:latest"). A guid-prefix purge
            # leaves the short-id entry behind and get_tool serves the
            # uninstalled tool straight from cache.
            for key, cached in list(self._tool_object_cache.items()):
                if (
                    key.startswith(f"{tool_id}:")
                    or getattr(cached, "id", None) == tool_id
                    or getattr(cached, "guid", None) == tool_id
                ):
                    self._tool_object_cache.pop(key, None)
        return result

    # === Override has_tool to check index ===

    def has_tool(
        self,
        tool_id: str | None,
        tool_version: str | None = None,
        tool_uuid: UUID | str | None = None,
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

    # === Index access methods ===

    @property
    def tool_index(self) -> ToolIndex | None:
        """Get the tool index."""
        return self._tool_index

    def get_tool_ids(self) -> list[str]:
        """Get all tool IDs from index."""
        if self._tool_index:
            return list(self._tool_index.entries.keys())
        return []

    def get_index_entry(self, tool_id: str) -> ToolIndexEntry | None:
        """Get index entry for a tool without loading it."""
        if self._tool_index:
            return self._tool_index.get(tool_id)
        return None

    def resolve_search_hit(self, tool_id: str) -> Optional["Tool"]:
        """Resolve a search hit to a registered stub, never materialising.

        ``ToolsService.search_tools`` only needs the tool id plus an
        ``allow_user_access`` check to filter results — parsing the tool
        would be pure waste. Going through :meth:`get_tool` instead
        materialises every hit, and the populator-owned whoosh index can
        carry ids that were never loaded into this toolbox
        (``tool_conf.xml.sample`` alone lists ~150 legacy tools whose files
        aren't present in most deployments).

        Return the already-registered stub / Tool from ``_tools_by_id`` (or
        via the shed short-id map), or ``None`` for a hit that isn't part of
        this toolbox. That matches eager search, whose ``_tools_by_id``
        lookup returns ``None`` for un-loaded ids so they're skipped — the
        lazy path must not surface (or parse) tools the eager path wouldn't.
        """
        tool = self._tools_by_id.get(tool_id)
        if tool is not None:
            return tool
        if self._shed_short_id_to_guids and tool_id in self._shed_short_id_to_guids:
            for guid in sorted(self._shed_short_id_to_guids[tool_id]):
                candidate = self._tools_by_id.get(guid)
                if candidate is not None:
                    return candidate
        return None

    def latest_search_hits(self, tool_ids: list[str]) -> list[str]:
        if self._tool_index is None:
            return tool_ids
        ordered_lineages: list[str] = []
        latest_by_lineage: dict[str, ToolIndexEntry] = {}
        for tool_id in tool_ids:
            entry = self._tool_index.entries.get(tool_id)
            if entry is None:
                continue
            lineage_id = remove_version_from_guid(entry.id) or entry.id
            current = latest_by_lineage.get(lineage_id)
            if current is None:
                ordered_lineages.append(lineage_id)
                latest_by_lineage[lineage_id] = entry
            elif self._index_entry_newer(entry, current):
                latest_by_lineage[lineage_id] = entry
        return [latest_by_lineage[lineage_id].id for lineage_id in ordered_lineages]

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

    # ``to_dict`` is NOT overridden: ``AbstractToolBox.to_dict`` runs the
    # ``FilterFactory`` pass for both the panel and the flat listing, and
    # its ``get_tool_to_dict`` serves ``LazyTool`` stubs via
    # ``to_panel_entry`` — filtered AND non-materialising.
