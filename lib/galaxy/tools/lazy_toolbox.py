"""
Lazy ToolBox - On-demand tool loading with LRU caching.

This module provides a LazyToolBox that extends ToolBox but keeps only a
lightweight index in memory and loads full Tool objects on-demand with
LRU eviction.
"""

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
from galaxy.tool_source_store import (
    StoredToolSource,
    ToolSourceStore,
)
from galaxy.tool_source_store.discover import discover_tools
from galaxy.tool_source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tool_source_store.populator import populate_store_inline
from galaxy.tool_util.id_util import extract_short_id_from_guid
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.toolbox.base import ToolConfRepository
from galaxy.tool_util.toolbox.lineages.interface import ToolLineage
from galaxy.tool_util.toolbox.panel import ToolSection
from galaxy.tool_util.version import parse_version
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
    def config_file(self) -> str | None:
        # ``source_path`` is stamped by the populator; entries serialized
        # before the field existed deserialize as ``None`` and callers that
        # need a real path fall through to ``__getattr__`` and materialise.
        return self._entry.source_path

    @property
    def lineage(self):
        return self._lineage

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

    def to_panel_entry(self, trans=None) -> dict[str, Any]:
        """Cheap entry-shape dict for the panel-view walk.

        Returned by :meth:`AbstractToolBox.get_tool_to_dict` when no help
        payload was requested. Stays off the materialise path entirely so
        ``/api/tool_panels/{view}`` and ``/api/tools?in_panel=true`` don't
        parse every tool on the first request.
        """
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
            "link": f"/tool_runner?tool_id={self.id}",
        }

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
        # ``_tool_index`` is filled by our ``_init_tools_from_configs`` override
        # before the eager walk runs.
        self._tool_index: ToolIndex | None = None
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
        # the panel pass registered. Section metadata, conf-level hidden,
        # and labels are already on the index entries (the populator stamps
        # them at discovery time), so no post-walk sync is needed.
        self._rebuild_shed_short_id_map()

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
        if self._store is not None:
            self._tool_index = self._store.load_index() or ToolIndex()
            if self._index_needs_population():
                self._run_inline_populator()
                self._tool_index = self._store.load_index() or ToolIndex()
        else:
            self._tool_index = ToolIndex()
        super()._init_tools_from_configs(config_filenames)

    def _index_needs_population(self) -> bool:
        """Return True when at least one config-discovered tool path is absent
        from the store. The first miss short-circuits the scan — we don't need
        an exhaustive answer, just a decision to run the populator.
        """
        if self._store is None:
            return False
        if not self._tool_index or not self._tool_index.entries:
            return True
        # The discover walker reads tool confs only; no DB round-trip per file.
        try:
            for d in discover_tools(self.app.config):
                if self._store.get_by_source_path(d.path) is None:
                    return True
        except Exception as e:
            log.warning("Index coverage check raised; running populator defensively: %s", e)
            return True
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
            self.app.model.context,
            rebuild_whoosh=True,
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
        too. Any miss is therefore a contract failure — operator added a
        tool to a conf without re-running the populator, or a code path
        introduced a new ad-hoc tool load without adding it to the
        hidden-lib list.
        """
        entry = self._resolve_index_entry(config_file, guid)
        if entry is None:
            raise RuntimeError(
                "LazyToolBox.create_tool: no index entry for "
                f"(config_file={config_file!r}, guid={guid!r}). The populator "
                "owns the index — run scripts/tool_source/populate_store.py "
                "or, for a new Galaxy-internal lib tool, add it to "
                "galaxy.tools.special_tools.hidden_lib_tool_paths()."
            )
        # LazyTool is duck-typed against Tool — the eager pipeline (audited
        # in plans/witty-drifting-clock.md) only consults attributes the
        # stub forwards from ToolIndexEntry, with mutations stored on
        # ``_overrides``.
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

    def _create_tool_from_stored_source(self, stored: StoredToolSource, entry: ToolIndexEntry | None = None) -> "Tool":
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
        try:
            self._store.invalidate_index_cache()
        except Exception as e:
            log.debug(f"Store invalidate_index_cache raised: {e}")
        loaded = self._store.load_index()
        self._tool_index = loaded if loaded is not None else ToolIndex()
        # Index just changed under us — refresh the short-id map so
        # peer-process installs (which only update the persisted index)
        # are reachable via short-id lookups in this process.
        self._rebuild_shed_short_id_map()
        # Wire newly-indexed entries (e.g. shed-install partial updates from
        # a peer process) into this process's in-memory registries as
        # ``LazyTool`` stubs. Without this, ``/api/tools`` would return the
        # new ids only after the next full toolbox boot.
        self._register_new_index_entries_as_stubs()

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
            if tool_id in self._tools_by_id:
                continue
            try:
                self._register_lazy_entry(entry)
            except Exception as e:
                log.warning("Failed to register new index entry %s: %s", tool_id, e)

    def _register_lazy_entry(self, entry: ToolIndexEntry) -> "LazyTool":
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
        if old_id and old_id != tool_id:
            bucket = self._tools_by_old_id.setdefault(old_id, [])
            if not any(getattr(t, "id", None) == tool_id for t in bucket):
                bucket.append(stub)  # type: ignore[arg-type]
        if entry.uuid:
            self._tools_by_uuid[UUID(entry.uuid)] = stub  # type: ignore[assignment]
        # Lineage: LazyLineageMap builds it from entries_by_version, which the
        # populator wrote on the previous step, so .get() returns the right
        # ToolLineage; register() is the fallback for an as-yet-unseen id.
        stub._lineage = self._lineage_map.get(tool_id) or self._lineage_map.register(stub)  # type: ignore[arg-type]
        # Place into the panel. The populator stamped panel_section_id /
        # panel_section_name onto the entry; create the ToolSection if it
        # doesn't already exist (peer-process install of the first tool in
        # a new section).
        section_id = entry.panel_section_id
        if section_id:
            section_key = f"section_{section_id}"
            section = self._tool_panel.get(section_key)
            if not isinstance(section, ToolSection):
                section = ToolSection({"id": section_id, "name": entry.panel_section_name or section_id})
                self._tool_panel[section_key] = section
            section.elems.append_tool(stub)
        else:
            self._tool_panel[f"tool_{tool_id}"] = stub
        return stub

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
