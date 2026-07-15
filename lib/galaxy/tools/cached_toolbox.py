"""
CachedToolBox - on-demand tool loading with LRU caching.

This module provides a CachedToolBox that extends ToolBox but keeps only a
lightweight index in memory and loads full Tool objects on-demand with
LRU eviction.
"""

import errno
import logging
import os
import threading
from collections.abc import Callable
from enum import Enum
from typing import (
    Any,
    cast,
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
from galaxy.tool_util.deps.requirements import (
    ContainerDescription,
    ToolRequirements,
)
from galaxy.tool_util.ontologies.ontology_data import curated_tool_tags
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.toolbox.base import (
    MaterializationReasonName,
    resolve_tool_path,
    SHED_TOOL_CONF_XML,
    ToolConfRepository,
    ToolLike,
)
from galaxy.tool_util.toolbox.lineages.factory import CachedLineageMap
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
    conf_to_store_map,
    populate_for_paths,
    populate_store_inline,
)
from galaxy.util import listify
from galaxy.util.tool_version import (
    is_shed_guid,
    remove_version_from_guid,
    short_tool_id,
)
from . import (
    create_tool_from_source,
    DataManagerTool,
    parse_tool_version_for_comparison,
    tool_requires_galaxy_python_environment,
    ToolBox,
)

if TYPE_CHECKING:
    from galaxy.app import UniverseApplication
    from galaxy.model import User
    from galaxy.tools import Tool

log = logging.getLogger(__name__)


class MaterializationReason(str, Enum):
    DETAIL = "detail"
    DEPENDENCY = "dependency"
    EXECUTION = "execution"
    JOB_SETUP = "job_setup"
    PACKAGING = "packaging"
    SERIALIZATION = "serialization"
    TESTS = "tests"
    VALIDATION = "validation"


class ToolMaterializationError(RuntimeError):
    """A stored tool could not be promoted to a real ``Tool``."""

    def __init__(self, tool_id: str, message: str) -> None:
        super().__init__(f"Failed to materialize tool {tool_id!r}: {message}")
        self.tool_id = tool_id


MaterializeCallback = Callable[["ToolIndexEntry", MaterializationReason], "Tool"]


def _entry_attr(name: str, entry_attr: str | None = None, mutable: bool = False):
    """Build a ``CachedTool`` property forwarding ``name`` to ``ToolIndexEntry``.

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


class CachedTool:
    """Lightweight stand-in for ``galaxy.tools.Tool`` backed by a ``ToolIndexEntry``.

    It forwards indexed attributes and reapplies pipeline mutations after
    materialisation. Unknown attributes raise so accidental eager paths are
    found and classified explicitly.
    """

    __slots__ = (
        "_containers",
        "_entry",
        "_is_admin_user",
        "_lineage",
        "_materialize_cb",
        "_overrides",
        "_preserve_python_environment",
        "_requirements",
    )

    # Cached sources are content-addressed, so file watching is a no-op.
    _macro_paths: tuple = ()

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
    is_datatype_converter = _entry_attr("is_datatype_converter")

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

    def __init__(
        self,
        entry: "ToolIndexEntry",
        materialize_callback: MaterializeCallback,
        is_admin_user,
        *,
        preserve_python_environment: str = "legacy_only",
    ) -> None:
        self._entry = entry
        self._materialize_cb = materialize_callback
        self._is_admin_user = is_admin_user
        self._preserve_python_environment = preserve_python_environment
        self._overrides: dict[str, Any] = {}
        self._requirements: ToolRequirements | None = None
        self._containers: list[ContainerDescription] | None = None
        # Assigned by AbstractToolBox.__add_tool via _lineage_map.register(tool).
        self._lineage: Any | None = None

    def replace_entry(self, entry: "ToolIndexEntry") -> None:
        self._entry = entry
        self._requirements = None
        self._containers = None

    # --- derived properties ---
    @property
    def guid(self):
        return self._overrides.get("guid") or (self._entry.id if is_shed_guid(self._entry.id) else None)

    @guid.setter
    def guid(self, value):
        self._overrides["guid"] = value

    @property
    def old_id(self) -> str:
        if "old_id" in self._overrides:
            return self._overrides["old_id"]
        return short_tool_id(self._entry.id)

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
        return parse_tool_version_for_comparison(self._entry.version or "")

    @property
    def tool_shed_repository(self):
        # The eager pipeline sets this on the real ``Tool`` for shed-installed
        # tools (passing ``tool_shed_repository=<repo>`` to ``create_tool``);
        # the CachedTool stub doesn't carry the repo object. Default to None —
        # callers that need a real ``ToolShedRepository`` go through
        # materialisation via ``_materialize_for_cached_tool``, which routes the
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

    @property
    def requirements(self) -> ToolRequirements:
        if self._requirements is None:
            self._requirements = ToolRequirements.from_list(cast(Any, self._entry.requirements))
        return self._requirements

    @property
    def tool_requirements(self) -> ToolRequirements:
        return self.requirements.packages

    @property
    def containers(self) -> list[ContainerDescription]:
        if self._containers is None:
            self._containers = [
                ContainerDescription.from_dict(container) for container in self._entry.container_requirements
            ]
        return self._containers

    @property
    def installed_tool_dependencies(self):
        # Standalone population has no install-database session. This matches
        # the ToolConfRepository used when a cached shed tool materializes.
        return None

    produces_real_jobs = _entry_attr("produces_real_jobs")

    @property
    def requires_galaxy_python_environment(self) -> bool:
        return tool_requires_galaxy_python_environment(
            tool_type=self.tool_type,
            profile=self._entry.profile,
            preserve_python_environment=self._preserve_python_environment,
            tool_shed=self.tool_shed,
            old_id=self.old_id,
            version=self.version,
        )

    # --- entry-only methods (no materialise) ---
    def allow_user_access(self, user, attempting_access: bool = True) -> bool:
        """Mirror of :meth:`Tool.allow_user_access` derived from index metadata.

        ``DataManagerTool`` overrides ``allow_user_access`` to require admin
        (lib/galaxy/tools/__init__.py:3893). On the stub we can't dispatch
        polymorphically on subclass, so branch on ``tool_type`` instead.
        Dynamic tools are materialized before unprivileged access checks.
        """
        if self.require_login and user is None:
            return False
        if self.tool_type == DataManagerTool.tool_type:
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
        """Delegate detail serialization, falling back if the stored source cannot load."""
        try:
            materialized = self.materialize(MaterializationReason.DETAIL)
        except ToolMaterializationError:
            log.exception("CachedTool.to_dict could not materialize %s; falling back to indexed metadata", self.id)
            return self.to_panel_entry(trans)
        return materialized.to_dict(trans, link_details=link_details, tool_help=tool_help, **kw)

    # --- materialisation ---
    def materialize(self, reason: MaterializationReason) -> "Tool":
        real = self._materialize_cb(self._entry, reason)
        try:
            for name, value in self._overrides.items():
                setattr(real, name, value)
            if self.hidden:
                real.hidden = True
            if self._lineage is not None:
                real._lineage = self._lineage
        except Exception as exc:
            raise ToolMaterializationError(self.id, "could not apply cached metadata") from exc
        return real


class CachedToolBox(ToolBox):
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
        # Needed by the overridden initialization invoked from ``super()``.
        self._store = tool_source_store
        self._tool_object_cache: LRUCache = LRUCache(maxsize=cache_size)
        self._cache_lock = threading.RLock()
        self._materialization_locks = tuple(threading.Lock() for _ in range(64))
        self._cached_tools: dict[tuple[str, str], CachedTool] = {}
        # Batch endpoints must not increment this test-visible counter.
        self._cached_materialize_count = 0
        self._tool_index: ToolIndex | None = None
        # Rebuilt after the eager walk for shed short-id lookups.
        self._shed_short_id_to_guids: dict[str, set[str]] = {}
        self._index_source_paths_cache: tuple[ToolIndex, set[str]] | None = None
        self._guid_sibling_versions_cache: tuple[ToolIndex, int, dict[str, list[tuple[str, str]]]] | None = None

        super().__init__(
            config_filenames=config_filenames,
            tool_root_dir=tool_root_dir,
            app=app,
            save_integrated_tool_panel=save_integrated_tool_panel,
        )

        self._rebuild_shed_short_id_map()

        log.info(
            "CachedToolBox initialized with %d tools (cache_size=%d, parsed=%d, from_store=%d)",
            len(self._tools_by_id),
            cache_size,
            self._tools_parsed_from_file,
            self._tools_loaded_from_store,
        )

    def _init_tools_from_configs(self, config_filenames: list[str]) -> None:
        """Load or populate the index, then let the eager walk register stubs."""
        # Index-backed lineages reflect reloads and all known versions.
        self._lineage_map = CachedLineageMap(self.app, versions_for=self._index_versions_for)
        self._tool_panel_loaded_from_index = False
        if self._store is not None:
            self._tool_index = self._store.load_index() or ToolIndex()
            if self._index_needs_population():
                self._run_inline_populator()
                # The inline populator uses a separate store instance.
                self._store.invalidate_index_cache()
                self._tool_index = self._store.load_index() or ToolIndex()
        else:
            self._tool_index = ToolIndex()
        if self._init_tools_from_index(config_filenames):
            return
        super()._init_tools_from_configs(config_filenames)

    def _init_tools_from_index(self, config_filenames: list[str]) -> bool:
        """Register stubs directly from a fresh index.

        The generic toolbox walk still parses every tool-conf item and routes
        each tool through ``load_item``. In cached-toolbox mode, a populated source-store
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
                "CachedToolBox fast panel init found %d panel ids missing from index; running populator",
                len(missing),
            )
            self._run_inline_populator()
            if self._store is not None:
                self._store.invalidate_index_cache()
                self._tool_index = self._store.load_index() or ToolIndex()
            placements = self._index_panel_items()
            missing = {p.tool_id for p in placements if p.tool_id not in self._tool_index.entries}
            if missing or not placements:
                log.debug("CachedToolBox fast panel init disabled; %d panel ids still missing from index", len(missing))
                return False
        assert self._tool_index is not None
        self._init_dynamic_tool_confs_without_loading(config_filenames)
        stubs_by_id: dict[str, CachedTool] = {}
        for entry in self._tool_index.entries.values():
            stubs_by_id[entry.id] = self._register_cached_entry(entry, place_in_panel=False)
        placed = 0
        for placement in placements:
            stub = stubs_by_id.get(placement.tool_id)
            if stub is None:
                continue
            self._place_stub(stub, placement.section_id, placement.section_name, hidden=placement.hidden)
            placed += 1
        log.debug(
            "CachedToolBox registered %d indexed tools (%d panel placements) without walking tool conf items",
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
        """Collapse each lineage's placements to its newest version's id.

        Hidden and visible entries collapse independently (the lineage key
        carries ``entry.hidden``): :meth:`_place_stub` mirrors every
        placement into the integrated panel — hidden included — but only
        visible ones into the live panel. Dropping hidden entries here (as an
        earlier revision did) kept their placements from ever reaching
        ``_place_stub``, so a fast-path boot persisted
        ``integrated_tool_panel.xml`` without hidden tools, losing their
        positions. Keeping the latest hidden lineage member routes its
        placement to the integrated projection while a visible sibling in the
        same lineage still reaches the live panel.
        """
        if self._tool_index is None:
            return tool_ids
        ordered_lineages: list[tuple[str | None, str, bool]] = []
        latest_by_lineage: dict[tuple[str | None, str, bool], ToolIndexEntry] = {}
        for tool_id in tool_ids:
            entry = self._tool_index.entries.get(tool_id)
            if entry is None:
                continue
            lineage_id = remove_version_from_guid(entry.id) or entry.id
            lineage_key = (entry.panel_section_id, lineage_id, entry.hidden)
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
        log.info("CachedToolBox: running populator inline to backfill the index")
        populate_store_inline(
            self.app.config,
            rebuild_whoosh=True,
        )

    def _index_versions_for(self, tool_id: str) -> list[str]:
        """Return every version present in the index for ``tool_id``.

        Hooked into ``CachedLineageMap.versions_for`` so a lineage lookup
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
        ``_tools_by_old_id``; the store index needs to walk sibling
        entries that share the versionless prefix.
        """
        if self._tool_index is None:
            return []
        versions = list(self._tool_index.entries_by_version.get(tool_id, {}).keys())
        result = [v for v in versions if v]
        if is_shed_guid(tool_id):
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
            short_id = short_tool_id(entry_id)
            if short_id != entry_id:
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
    ) -> ToolLike | None: ...

    @overload
    def get_tool(
        self,
        tool_id: str | None = None,
        tool_version: str | None = None,
        tool_uuid: UUID | str | None = None,
        get_all_versions: Literal[True] = True,
        exact: bool | None = False,
        user: Optional["User"] = None,
    ) -> list[ToolLike]: ...

    def get_tool(
        self,
        tool_id: str | None = None,
        tool_version: str | None = None,
        tool_uuid: UUID | str | None = None,
        get_all_versions: bool | None = False,
        exact: bool | None = False,
        user: Optional["User"] = None,
    ) -> ToolLike | None | list[ToolLike]:
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
                tools: list[ToolLike] = []
                for ver in versions:
                    entry = self._tool_index.get(tool_id, ver)
                    if entry is not None:
                        tools.append(self._cached_tool_for_entry(entry))
                if tools:
                    return tools
            else:
                entry = self._tool_index.get(tool_id, tool_version)
                if entry is not None:
                    return self._cached_tool_for_entry(entry)
                # Match eager behavior: inexact version misses use the default
                # tool so workflow safe-version migration can run; exact
                # requests must still report the requested version missing.
                if tool_version and not exact:
                    default_entry = self._tool_index.entries.get(tool_id)
                    if default_entry is not None:
                        return self._cached_tool_for_entry(default_entry)

        # Cached shed installs need their own short-id lookup and version sort.
        if self._tool_index and self._shed_short_id_to_guids and tool_id in self._shed_short_id_to_guids:
            candidates: list[tuple[tuple[int, Any], ToolLike]] = []
            for guid in sorted(self._shed_short_id_to_guids[tool_id]):
                entry = self._tool_index.get(guid, tool_version)
                if entry is None and tool_version and not exact:
                    # Inexact requests may use this guid's default version.
                    entry = self._tool_index.entries.get(guid)
                if entry is not None:
                    cached = self._cached_tool_for_entry(entry)
                    ver_key: tuple[int, Any]
                    try:
                        ver_key = (0, parse_version(cached.version or "0"))
                    except Exception:
                        ver_key = (1, cached.version or "")
                    candidates.append((ver_key, cached))
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

    # === create_tool seam: return CachedTool stub when the index already has the source ===

    def create_tool(self, config_file, tool_shed_repository=None, guid=None, **kwds) -> "Tool":
        """Return a :class:`CachedTool` for every indexed tool source.

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
                    "CachedToolBox.create_tool: no index entry for %s after ad-hoc populate; parsing eagerly",
                    config_file,
                )
                return super().create_tool(config_file, tool_shed_repository=tool_shed_repository, guid=guid, **kwds)
            raise RuntimeError(
                "CachedToolBox.create_tool: no index entry for "
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
        # The eager initialization pipeline is typed around Tool, but only
        # consumes the indexed ToolLike surface before registering the entry.
        return cast("Tool", self._cached_tool_for_entry(entry))

    def _cached_tool_for_entry(self, entry: ToolIndexEntry) -> CachedTool:
        key = (entry.id, entry.version or "")
        cached = self._cached_tools.get(key)
        if cached is not None:
            if cached._entry is not entry:
                cached.replace_entry(entry)
            return cached
        cached = CachedTool(
            entry,
            materialize_callback=self._materialize_for_cached_tool,
            is_admin_user=self.app.config.is_admin_user,
            preserve_python_environment=self.app.config.preserve_python_environment,
        )
        if hasattr(self, "_lineage_map"):
            cached._lineage = self._lineage_map.get(entry.id) or self._lineage_map.register(cached)  # type: ignore[arg-type]
        self._cached_tools[key] = cached
        return cached

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
        log.info("CachedToolBox: index miss for existing file %s — populating ad hoc (guid=%s)", path, guid)
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
                # latest and both files would collapse to one CachedTool.
                entry = self._tool_index.get(stored.tool_id, stored.tool_version)
                if entry is not None:
                    return entry
        # No entry: do NOT fall back to parsing the id out of the file —
        # ``entries[id]`` holds only the latest version, which would collapse
        # multi-version conf entries onto one CachedTool. The store's
        # ``source_path`` index is the authoritative key; a miss means the
        # source genuinely isn't persisted yet, so let ``create_tool``'s
        # fallthrough parse and ``_persist_tool_source`` write it.
        return None

    def _materialize_for_cached_tool(self, entry: ToolIndexEntry, reason: MaterializationReason) -> "Tool":
        if self._tool_index is not None:
            versions = self._tool_versions_by_id.setdefault(entry.id, {})
            for version, sibling_entry in self._tool_index.entries_by_version.get(entry.id, {}).items():
                versions[version] = self._cached_tool_for_entry(sibling_entry)  # type: ignore[assignment]
        return self._load_tool_on_demand(entry, reason)

    def materialize_tool(self, tool: ToolLike, *, reason: MaterializationReasonName) -> "Tool":
        if isinstance(tool, CachedTool):
            return tool.materialize(MaterializationReason(reason))
        return cast("Tool", tool)

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

    def _load_tool_on_demand(self, entry: ToolIndexEntry, reason: MaterializationReason) -> "Tool":
        """Return one materialized tool through the bounded, single-flight LRU."""
        cache_key = (entry.id, entry.version or "", entry.source_hash)
        with self._cache_lock:
            cached = self._tool_object_cache.get(cache_key)
            if cached is not None:
                return cached

        materialization_lock = self._materialization_locks[hash(cache_key) % len(self._materialization_locks)]
        with materialization_lock:
            with self._cache_lock:
                cached = self._tool_object_cache.get(cache_key)
                if cached is not None:
                    return cached
            if self._store is None:
                raise ToolMaterializationError(entry.id, "tool source store is unavailable")
            try:
                stored = self._stored_source_for_entry(entry)
            except Exception as exc:
                raise ToolMaterializationError(entry.id, "stored source lookup failed") from exc
            if stored is None:
                raise ToolMaterializationError(
                    entry.id,
                    f"indexed source is missing (path={entry.source_path!r}, hash={entry.source_hash!r})",
                )
            try:
                tool = self._create_tool_from_stored_source(stored, entry=entry)
            except Exception as exc:
                raise ToolMaterializationError(entry.id, "stored source could not be parsed") from exc
            log.debug("Materialized tool %s for %s", entry.id, reason.value)
            with self._cache_lock:
                current = self._tool_index.get(entry.id, entry.version) if self._tool_index is not None else None
                if current is not None and current.source_hash == entry.source_hash:
                    self._tool_object_cache[cache_key] = tool
            return tool

    def _create_tool_from_stored_source(self, stored: StoredToolSource, entry: ToolIndexEntry | None = None) -> "Tool":
        """Create a Tool object from stored source.

        The single chokepoint for promoting a stub to a real ``Tool`` at runtime.
        """
        self._cached_materialize_count += 1
        tool_source = get_tool_source(
            raw_tool_source=stored.raw_source,
            tool_source_class=stored.tool_source_class,
        )
        # When the stored source's ``tool_id`` is a toolshed guid (set by
        # the cached-toolbox shed install path), pass it as ``guid`` to the Tool
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
        if stored.tool_id and is_shed_guid(stored.tool_id):
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
            previous_hashes = self._index_entry_hashes()
            loaded = self._store.load_index()
            self._tool_index = loaded if loaded is not None else ToolIndex()
            # Index just changed under us — refresh the short-id map so
            # peer-process installs (which only update the persisted index)
            # are reachable via short-id lookups in this process.
            self._rebuild_shed_short_id_map()
            # Wire newly-indexed entries (e.g. shed-install partial updates
            # from a peer process) into this process's in-memory registries
            # as ``CachedTool`` stubs. Without this, ``/api/tools`` would
            # return the new ids only after the next full toolbox boot.
            self._register_new_index_entries_as_stubs()
            # Reconcile content edits: an id present in both indexes but with
            # a different ``source_hash`` under the same version was edited in
            # place and re-indexed by the ``populate_store.py --watch``
            # populator. Content-addressed sources can't stale a *hash*, but
            # the per-process LRU and ``_tools_by_id`` are keyed by
            # id/version, so a warm cache would keep serving the pre-edit
            # ``Tool``. Evict the cached/materialised objects for those ids so
            # the next access re-materialises from the new source. Internal
            # and dynamic tools never enter the index, so they are untouched.
            for tool_id, versions in self._tool_index.entries_by_version.items():
                old_hashes = previous_hashes.get(tool_id)
                if not old_hashes:
                    continue
                if not any(v in old_hashes and old_hashes[v] != entry.source_hash for v, entry in versions.items()):
                    continue
                default_entry = self._tool_index.entries.get(tool_id)
                if default_entry is not None:
                    try:
                        self._refresh_changed_entry(tool_id, default_entry)
                    except Exception as e:
                        log.warning("Refreshing content-changed index entry %s raised: %s", tool_id, e)
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
        ``CachedTool`` stub, slot it into the toolbox registries, and place it
        under its declared panel section.

        Mirrors what the eager walk does at boot for each ``<tool>`` element,
        but for a single entry already fully described by the populator.
        """
        if self._tool_index is None:
            return
        for tool_id, entry in self._tool_index.entries.items():
            # ``Any``: the registry is typed for real Tools but holds
            # CachedTool stubs on this toolbox (same duck-typing as create_tool).
            existing: Any = self._tools_by_id.get(tool_id)
            if existing is not None:
                if isinstance(existing, CachedTool) and existing._entry is not entry:
                    # Refresh the stub in place — the panel and registries
                    # hold this object, and the reloaded index may carry an
                    # enriched entry (e.g. the conf-driven populate after a
                    # shed install adds repository metadata the install-time
                    # ad-hoc entry lacked). ``_overrides`` survive.
                    existing.replace_entry(entry)
                continue
            try:
                self._register_cached_entry(entry)
            except Exception as e:
                log.warning("Failed to register new index entry %s: %s", tool_id, e)

    def _index_entry_hashes(self) -> dict[str, dict[str, str]]:
        """Snapshot ``{tool_id: {version: source_hash}}`` of the current index.

        Captured before an :meth:`invalidate_index_cache` reload so the reload
        can spot ids whose source changed under a stable id+version — the
        signal a content-addressed source can't carry on its own once it is
        cached under an id/version key.
        """
        result: dict[str, dict[str, str]] = {}
        if self._tool_index is None:
            return result
        for tool_id, versions in self._tool_index.entries_by_version.items():
            result[tool_id] = {version: entry.source_hash for version, entry in versions.items()}
        return result

    def _refresh_changed_entry(self, tool_id: str, entry: ToolIndexEntry) -> None:
        """Evict parsed state and update the stable proxy for ``tool_id``."""
        self._purge_tool_object_cache(tool_id)
        proxy = self._cached_tool_for_entry(entry)
        proxy.replace_entry(entry)
        self._tools_by_id[tool_id] = proxy  # type: ignore[assignment]
        self._tool_versions_by_id.setdefault(tool_id, {})[entry.version or ""] = proxy  # type: ignore[assignment]

    def _register_cached_entry(self, entry: ToolIndexEntry, place_in_panel: bool = True) -> "CachedTool":
        """Slot the stable metadata proxy for ``entry`` into toolbox registries."""
        stub = self._cached_tool_for_entry(entry)
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
        # Lineage: CachedLineageMap builds it from entries_by_version, which the
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
        stub: "CachedTool",
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
        self._cached_tools.clear()
        self._tool_index = None
        self._store = None
        # ``ToolLineage.lineages_by_id`` is a *class*-level dict, so a
        # ``ToolLineage`` from a prior process / embedded restart would
        # otherwise carry its ``tool_versions`` SortedSet across boots and
        # shadow the new boot's index versions. Reset on shutdown so the
        # next ``CachedLineageMap.get`` rebuilds from the freshly-loaded
        # index.
        ToolLineage.reset()
        # ``_tools_by_id`` and friends still get GC'd when the surrounding
        # app object drops. We don't clear them here because the eager
        # parent's shutdown sequence may still iterate them.

    def remove_tool_by_id(self, tool_id: str, remove_from_panel: bool = True):
        """Also drop the tool from the store index + LRU cache.

        ``AbstractToolBox.remove_tool_by_id`` only deletes from
        ``_tools_by_id``. In the cached-toolbox path that's not enough — ``get_tool``
        re-loads the tool from ``_tool_index`` on the next request, so the
        tool effectively comes back. The eager toolbox doesn't have this
        problem because the tool object isn't created from a serialised
        store. Mirror the deletion across the two backing stores.

        Wrapped in ``app._toolbox_lock`` so registry and persisted-index
        removal remain atomic with toolbox reloads.
        """
        with self.app._toolbox_lock:
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
                # imports CachedToolBox at module level.
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
            if current is not self and isinstance(current, CachedToolBox):
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
        # Drop the complete old-id bucket for this removed index entry.
        self._tools_by_old_id.pop(tool_id, None)
        # The short-id bucket is keyed by ``old_id`` — for a shed guid
        # that's the short tool id, not ``tool_id``. ``super()`` removes
        # from it by object identity only, which misses when the bucket
        # holds an earlier registration (stub or materialised instance)
        # while ``_tools_by_id`` held a fresher one; the leftover then
        # resurrects the uninstalled tool via the eager get_tool
        # fall-through. Scrub every object belonging to this guid, but
        # leave sibling installs (other guids, other versions) alone.
        short_id = short_tool_id(tool_id)
        if short_id != tool_id:
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
        self._purge_tool_object_cache(tool_id)
        for key in [key for key in self._cached_tools if key[0] == tool_id]:
            del self._cached_tools[key]
        return result

    def _purge_tool_object_cache(self, tool_id: str) -> None:
        """Drop every parsed-tool LRU entry for ``tool_id``."""
        with self._cache_lock:
            for key, cached in list(self._tool_object_cache.items()):
                if (
                    key[0] == tool_id
                    or getattr(cached, "id", None) == tool_id
                    or getattr(cached, "guid", None) == tool_id
                ):
                    self._tool_object_cache.pop(key, None)

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

    def resolve_search_hit(self, tool_id: str) -> Optional["Tool"]:
        """Return a registered search hit without materialising it."""
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

    # The inherited ``to_dict`` keeps filtering while serving index-backed stubs.
