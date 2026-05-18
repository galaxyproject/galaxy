"""
Lazy ToolBox - On-demand tool loading with LRU caching.

This module provides a LazyToolBox that extends ToolBox but keeps only a
lightweight index in memory and loads full Tool objects on-demand with
LRU eviction.
"""

import hashlib
import logging
import os
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
from galaxy.tool_util.id_util import extract_short_id_from_guid
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.toolbox.lineages.interface import ToolLineage
from galaxy.tool_util.toolbox.panel import (
    panel_item_types,
    ToolSection,
)
from galaxy.tool_util.toolbox.views.edam import EdamToolPanelView
from . import (
    create_tool_from_source,
    ToolBox,
)

if TYPE_CHECKING:
    from galaxy.app import UniverseApplication
    from galaxy.model import User
    from galaxy.tools import Tool

log = logging.getLogger(__name__)


# Set LAZY_TOOL_PERMISSIVE=1 to downgrade unknown-attribute ``NotImplementedError``s
# on a ``LazyTool`` to a warning + on-demand materialisation. Off by default so
# accidental materialisation paths show up in CI / dev as clear failures.
_LAZY_TOOL_PERMISSIVE = os.environ.get("LAZY_TOOL_PERMISSIVE") == "1"


def _entry_attr(name: str, entry_attr: Optional[str] = None, mutable: bool = False):
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
    a narrow attribute surface (audited at plan time — see
    ``.claude/plans/witty-drifting-clock.md``); ``LazyTool`` forwards every
    read off ``ToolIndexEntry`` and stores writes in ``_overrides`` so they
    are re-applied if the stub is later materialised.

    **Strict by default.** Any attribute outside the explicit surface raises
    :class:`NotImplementedError` so accidental materialisations show up at
    test time as clear failures rather than silent multi-second parse stalls.
    Set ``LAZY_TOOL_PERMISSIVE=1`` to downgrade to warn + materialise while
    debugging.
    """

    __slots__ = ("_entry", "_materialize_cb", "_is_admin_user", "_overrides", "_real", "_lineage")

    # ``watch_tool`` iterates ``tool._macro_paths`` for file-watching; lazy
    # entries are content-addressed in the store, file-watching is a no-op.
    # Class-level so it isn't writable on the instance.
    _macro_paths: tuple = ()

    # Methods we accept will materialise a real Tool. Add to this set only
    # when the parse cost is genuinely warranted at the call site.
    _MATERIALIZE_OK = frozenset(
        {
            "to_archive",  # tool packaging endpoint
            "build_dependency_cache",  # explicit cache-warming
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
        self._real: Optional[Tool] = None
        # Assigned by AbstractToolBox.__add_tool via _lineage_map.register(tool).
        self._lineage: Optional[Any] = None

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
    def config_file(self) -> Optional[str]:
        # ``StoredToolSource.source_path`` was added on this branch precisely
        # so the lazy path can resolve a tool back to its on-disk conf without
        # parsing. Older entries serialised before that field exists return
        # ``None`` — callers that need a real path (``_write_integrated_tool_panel_config_file``,
        # ``get_externally_referenced_paths``) fall through to ``__getattr__``
        # and materialise.
        return getattr(self._entry, "source_path", None)

    @property
    def lineage(self):
        return self._lineage

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
        if self.tool_type == "data_manager":
            if user is None or not bool(self._is_admin_user(user)):
                if attempting_access:
                    log.debug(
                        "User (%s) attempted to access a data manager tool (%s), but is not an admin.",
                        getattr(user, "id", None),
                        self.id,
                    )
                return False
        return True

    def to_dict(self, trans=None, link_details: bool = False, tool_help: bool = False, **kw) -> dict[str, Any]:
        """API serialisation. ``link_details=False`` stays on the entry fast path.

        ``link_details=True`` (used by ``/api/tools/<id>/build``) needs the full
        :meth:`Tool.to_dict` payload (parameters, citations, ...). That triggers
        materialise. The default and EDAM panel listings call with
        ``link_details=False`` and stay cheap.
        """
        if link_details:
            return self._materialize().to_dict(trans, link_details=True, tool_help=tool_help, **kw)
        entry = self._entry
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "labels": self.labels if self.labels else [],
            "edam_operations": entry.edam_operations or [],
            "edam_topics": entry.edam_topics or [],
            "hidden": self.hidden,
            "model_class": "Tool",
            "panel_section_id": entry.panel_section_id,
            "panel_section_name": entry.panel_section_name,
            "link": f"/api/tools/{self.id}",
            "min_width": -1,
            "target": "galaxy_main",
        }

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
        # Private/dunder attrs are never materialise triggers — surface as
        # ``AttributeError`` so e.g. ``hasattr(tool, "__something__")`` stays cheap.
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._MATERIALIZE_OK:
            return getattr(self._materialize(), name)
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
        # Lazy-only state set BEFORE ``super().__init__`` because the
        # eager ``_init_tools_from_configs`` (which super invokes mid-init)
        # is overridden below to consult ``self._store`` and populate
        # ``self._tool_index``.
        self._store = tool_source_store
        self._tool_object_cache: LRUCache = LRUCache(maxsize=cache_size)
        self._cache_lock = threading.RLock()
        # Whoosh search infrastructure — built lazily on first ``search_tools``
        # call and re-built whenever the underlying ``ToolIndex`` version changes.
        self._whoosh_search_index: Optional[ToolWhooshIndex] = None
        self._whoosh_search_index_version: Optional[str] = None
        # ``_tool_index`` is filled by our ``_init_tools_from_configs`` override
        # before the eager walk runs.
        self._tool_index: Optional[ToolIndex] = None
        # Mirror the eager toolbox's short-id → Tool mapping so
        # ``GET /api/tools/<short_id>`` resolves shed installs even when
        # only the guid landed in the panel. Filled after the eager walk
        # via ``_rebuild_shed_short_id_map``.
        self._shed_short_id_to_guids: dict[str, set[str]] = {}

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
        # the panel pass registered.
        self._rebuild_shed_short_id_map()

        # Stamp panel-section metadata from the now-populated ``_tool_panel``
        # back onto the ``ToolIndexEntry`` for each tool. The eager walk
        # records ``(tool_id, section_id, section_name)`` via
        # ``ToolPanelElements.record_section_for_tool_id``, but doesn't
        # touch the persisted index — and the ``to_panel_view`` / ``to_dict``
        # fast paths key off ``entry.panel_section_id`` to group by section.
        self._stamp_panel_sections_onto_index()

        # Sync post-create mutations the eager pipeline applied to each Tool
        # back onto the index entries. ``_load_tool_tag_set`` sets
        # ``tool.hidden = True`` (from conf-level ``hidden="true"``) and
        # ``tool.labels = …`` *after* our ``create_tool`` seam returned,
        # so ``_persist_tool_source`` had no way to see them. Without this
        # sync, materialising a re-loaded tool resurrects the un-flagged
        # version (``test_show_lists_every_indexed_version`` fails because
        # the conf-level hidden of v0.1 is lost on materialise).
        self._sync_tool_mutations_to_index()

        # Commit anything ``create_tool`` persisted during the eager walk.
        # No-op when the store didn't see any new content. When the
        # constructor runs in the queue-worker thread (``reload_toolbox``
        # control task), nothing later closes that transaction — on SQLite
        # the open writer lock blocks the test driver's subsequent
        # ``DELETE FROM repository_repository_dependency_association`` in
        # ``reset_shed_tools`` (``test_repository_*`` teardown), on
        # Postgres it leaves an idle-in-transaction row blocking those
        # same ``DELETE``s for the rest of the shard run.
        if self._store is not None:
            try:
                self._store.commit()
            except Exception as e:
                log.warning(f"LazyToolBox: post-init commit raised: {e}")

        log.info(
            "LazyToolBox initialized with %d tools (cache_size=%d, parsed=%d, from_store=%d)",
            len(self._tools_by_id),
            cache_size,
            self._tools_parsed_from_file,
            self._tools_loaded_from_store,
        )
        self._warn_if_index_misses_panel_tools()

    def _init_tools_from_configs(self, config_filenames: list[str]) -> None:
        """Load the persistent ``ToolIndex`` before delegating to the eager walk.

        After this returns, the eager pipeline calls into ``create_tool`` for
        every ``<tool>`` it walks. The seam short-circuits indexed sources to a
        :class:`LazyTool` stub; misses fall through to the parent's full
        ``ToolBox.create_tool`` and ``_persist_tool_source`` writes them to
        the store, so the next boot sees them as hits.
        """
        if self._store is not None:
            loaded = self._store.load_index()
            self._tool_index = loaded if loaded is not None else ToolIndex()
        else:
            self._tool_index = ToolIndex()
        super()._init_tools_from_configs(config_filenames)

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
        # ``_tool_section_map`` is built by the (Phase-2-doomed)
        # ``_init_panel_structure_from_configs``; in the seam-driven boot
        # path the eager walk populates ``_tool_panel`` directly, so derive
        # the panel-id set from that instead. Falls back to whatever
        # the legacy code path left behind.
        if hasattr(self, "_tool_section_map") and self._tool_section_map:
            panel_ids: set[str] = set(self._tool_section_map.keys())
        else:
            panel_ids = set()
            for _key, item in self._tool_panel.items():
                if isinstance(item, ToolSection):
                    for _sub_key, sub_type, sub_item in item.elems.panel_items_iter():
                        if sub_type == panel_item_types.TOOL and sub_item is not None:
                            tool_id = getattr(sub_item, "id", None)
                            if tool_id:
                                panel_ids.add(tool_id)
                elif _key.startswith("tool_") and item is not None:
                    tool_id = getattr(item, "id", None)
                    if tool_id:
                        panel_ids.add(tool_id)
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

    def _stamp_panel_sections_onto_index(self) -> None:
        """Mirror ``_tool_panel``'s section assignments onto ``_tool_index`` entries.

        The eager walk records section membership inside ``_tool_panel``
        (via ``record_section_for_tool_id``), but the ``ToolIndex`` entries
        — the source of truth for ``to_panel_view`` / ``to_dict`` fast
        paths and for the next boot's warm load — don't know about the
        section. Walk the panel once after the eager init finishes and
        copy that information across; persist if anything changed.
        """
        if self._tool_index is None:
            return
        dirty = False
        for _key, item in self._tool_panel.items():
            if not isinstance(item, ToolSection):
                continue
            section_id = item.id
            section_name = item.name or section_id
            for _sub_key, sub_type, sub_item in item.elems.panel_items_iter():
                if sub_type != panel_item_types.TOOL or sub_item is None:
                    continue
                tool_id = getattr(sub_item, "id", None)
                if not tool_id:
                    continue
                # Stamp every indexed version of this tool — multi-version
                # tools live in the same panel slot in the eager world.
                for entry in self._tool_index.entries_by_version.get(tool_id, {}).values():
                    if entry.panel_section_id != section_id or entry.panel_section_name != section_name:
                        entry.panel_section_id = section_id
                        entry.panel_section_name = section_name
                        dirty = True
                default_entry = self._tool_index.entries.get(tool_id)
                if default_entry is not None and (
                    default_entry.panel_section_id != section_id or default_entry.panel_section_name != section_name
                ):
                    default_entry.panel_section_id = section_id
                    default_entry.panel_section_name = section_name
                    dirty = True
        if dirty and self._store is not None:
            try:
                self._store.store_index(self._tool_index)
            except Exception as e:
                log.debug("store_index after section stamping raised: %s", e)

    def _sync_tool_mutations_to_index(self) -> None:
        """Copy post-``create_tool`` Tool mutations back to ``ToolIndexEntry``.

        Specifically: ``tool.hidden`` and ``tool.labels`` get set by the
        eager ``_load_tool_tag_set`` *after* our seam returned, so
        ``_persist_tool_source`` couldn't capture them. Walk
        ``_tool_versions_by_id`` (which has every (id, version) → Tool
        the eager walk registered) and stamp those attributes onto the
        matching entry. Persists if anything changed.
        """
        if self._tool_index is None:
            return
        dirty = False
        for tool_id, versions in list(self._tool_versions_by_id.items()):
            entries_for_id = self._tool_index.entries_by_version.get(tool_id, {})
            for version, tool in versions.items():
                entry = entries_for_id.get(version or "")
                if entry is None:
                    continue
                tool_hidden = bool(getattr(tool, "hidden", False))
                if tool_hidden and not entry.hidden:
                    entry.hidden = True
                    dirty = True
                tool_labels = getattr(tool, "labels", None) or []
                if tool_labels and list(entry.labels) != list(tool_labels):
                    entry.labels = list(tool_labels)
                    dirty = True
        if dirty and self._store is not None:
            try:
                self._store.store_index(self._tool_index)
            except Exception as e:
                log.debug("store_index after mutation sync raised: %s", e)

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

    # === create_tool seam: return LazyTool stub when the index already has the source ===

    def create_tool(self, config_file, tool_shed_repository=None, guid=None, **kwds) -> "Tool":
        """Return a :class:`LazyTool` whenever the source is already in the store.

        Fallthrough to the eager ``ToolBox.create_tool`` only when the index has no
        entry — the parsed Tool is then persisted via :meth:`_persist_tool_source`
        so the next boot sees it as a hit. The eager pipeline's downstream
        mutations (``tool.hidden = True``, shed metadata, ``tool.labels = …``)
        land in the stub's ``_overrides`` and survive any later materialisation.
        """
        entry = self._resolve_index_entry(config_file, guid)
        if entry is not None:
            # LazyTool is duck-typed against Tool — the eager pipeline (audited
            # in plans/witty-drifting-clock.md) only consults attributes the
            # stub forwards from ToolIndexEntry, with mutations stored on
            # ``_overrides``.
            return LazyTool(  # type: ignore[return-value]
                entry,
                materialize_callback=self._materialize_for_lazy_tool,
                is_admin_user=self.app.config.is_admin_user,
            )
        tool = super().create_tool(config_file, tool_shed_repository=tool_shed_repository, guid=guid, **kwds)
        self._persist_tool_source(tool, config_file, guid=guid)
        return tool

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

    def _resolve_index_entry(self, config_file, guid: Optional[str]) -> Optional[ToolIndexEntry]:
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
        config_file_str = str(config_file)
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
        # No entry: fall through. The id-from-file last-resort that lived
        # here previously is unsafe for multi-version tools — two conf entries
        # carrying the same ``<tool id=foo>`` at different ``<tool version=...>``
        # would both resolve to whatever version happened to be in
        # ``entries[id]`` first, collapsing both panel slots onto the same
        # LazyTool. The store's ``source_path`` index is the authoritative
        # key; a miss here means the source genuinely isn't persisted yet,
        # so let ``create_tool``'s fallthrough parse and ``_persist_tool_source``
        # write it.
        return None

    def _materialize_for_lazy_tool(self, entry: ToolIndexEntry) -> "Tool":
        """Promote a stub to a real ``Tool`` via the existing store-backed loader.

        Routed through :meth:`_register_loaded_tool` so ``_tools_by_id`` /
        ``_tool_versions_by_id`` / ``_tools_by_old_id`` / lineage all agree
        with the eager toolbox bookkeeping.
        """
        if self._store is None:
            raise RuntimeError(f"LazyTool materialise needs a tool source store (id={entry.id!r})")
        stored = self._store.get(entry.source_hash)
        if stored is None:
            raise RuntimeError(
                f"LazyTool materialise: source missing from store (id={entry.id!r}, hash={entry.source_hash!r})"
            )
        tool = self._create_tool_from_stored_source(stored, entry=entry)
        self._register_loaded_tool(tool)
        return tool

    def _persist_tool_source(self, tool: "Tool", config_file, guid: Optional[str]) -> None:
        """Write a freshly-parsed tool's source to the store and add an index entry.

        Called from :meth:`create_tool` whenever the eager fallthrough actually
        parsed the XML. Idempotent on ``content_hash`` (the store dedupes). After
        a successful write, broadcasts ``reload_tool_source_cache`` so peer
        Galaxy processes refresh their index.
        """
        if self._store is None or self._tool_index is None:
            return
        try:
            tool_source = tool.tool_source
            xml_tree = getattr(tool_source, "xml_tree", None)
            if xml_tree is not None:
                from galaxy.util import xml_to_string

                raw_source = xml_to_string(xml_tree.getroot(), pretty=True)
            elif config_file is not None and os.path.exists(str(config_file)):
                with open(str(config_file), encoding="utf-8") as fh:
                    raw_source = fh.read()
            else:
                log.debug("Cannot persist tool source for %s: no xml_tree and no readable config_file", tool.id)
                return
        except Exception as e:
            log.warning("Failed to serialise tool source for persistence (id=%s): %s", tool.id, e)
            return

        content_hash = hashlib.sha256(raw_source.encode("utf-8")).hexdigest()
        tool_id = guid or tool.id
        if not tool_id:
            return
        source_path = str(config_file) if config_file is not None else None
        tool_dir = os.path.dirname(str(config_file)) if source_path else None
        stored = StoredToolSource(
            hash=content_hash,
            tool_source_class=type(tool_source).__name__,
            raw_source=raw_source,
            tool_id=tool_id,
            tool_version=tool.version,
            tool_dir=tool_dir,
            source_path=source_path,
            stored_at=datetime.utcnow(),
        )
        try:
            self._store.store(stored)
        except Exception as e:
            log.warning("Failed to persist tool source (id=%s): %s", tool_id, e)
            return

        entry = self._build_index_entry_from_stored(stored)
        if entry is None:
            return
        # Mirror the shed-metadata stamps the eager pipeline applies to the Tool
        # after create_tool returns. We capture them here so a subsequent
        # lookup off the index agrees with the in-memory Tool.
        if guid:
            entry.id = guid
            entry.is_local = False
            entry.tool_shed = getattr(tool, "tool_shed", None) or entry.tool_shed
            entry.repository_name = getattr(tool, "repository_name", None) or entry.repository_name
            entry.repository_owner = getattr(tool, "repository_owner", None) or entry.repository_owner
            entry.changeset_revision = getattr(tool, "installed_changeset_revision", None) or entry.changeset_revision
        self._tool_index.add_entry(entry)
        self._tool_index.invalidate_caches()
        try:
            self._store.store_index(self._tool_index)
        except Exception as e:
            log.debug("store_index after persist raised: %s", e)
        # Fan out to peer processes — same broadcast the prior shed-install
        # path used to fire from ``_lazy_register_tool_item``.
        try:
            from galaxy.queue_worker import send_control_task

            send_control_task(self.app, "reload_tool_source_cache", noop_self=True)
        except Exception as e:
            log.debug("send_control_task(reload_tool_source_cache) failed: %s", e)

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
        # The default panel view is whatever ``AbstractToolBox.__init__`` (or our
        # legacy override) registered for the "full tool panel" slot — it
        # isn't an Edam view and isn't a configured StaticToolPanelView.
        # ``DefaultToolPanelView`` is a *locally-defined* class inside
        # ``AbstractToolBox.__init__`` now that we call ``super().__init__()``,
        # so we can't ``isinstance``-check it; negate the two known
        # specialisations instead.
        from galaxy.tool_util.toolbox.views.static import StaticToolPanelView

        is_default_view = view_def is not None and not isinstance(view_def, (EdamToolPanelView, StaticToolPanelView))
        if view_def is None or is_default_view:
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

        # Non-default view (EDAM, static): defer to the parent. With the
        # eager pipeline filling ``_integrated_tool_panel`` with ``LazyTool``
        # stubs, EDAM's ``walk_loaded_tools`` reads ``tool.edam_operations``
        # / ``edam_topics`` from the entry surface (no parse) and
        # ``_load_tool_panel_views`` (run by ``super().__init__``) has
        # already cached the rendered panel in ``_tool_panel_view_rendered``.
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
