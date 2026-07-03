Tool Source Storage Architecture
================================

This document describes the architecture of the tool source storage subsystem
and the LazyToolBox. For operator-facing setup and configuration, see
:doc:`/admin/tool_source_storage`.

Goals
-----

The traditional ``ToolBox`` parses every tool XML at startup, builds full
``Tool`` objects, and keeps them all in memory. With thousands of tools that
scales poorly: slow boot, large per-process RSS, and expensive worker reloads.

The tool source storage subsystem moves that work out of the request path:

- A separate process (``populate_store.py``) parses tools once and persists
  the canonical, macro-expanded source plus a lightweight metadata index.
- Galaxy processes load only the index at startup and materialize ``Tool``
  objects on demand, with LRU eviction.
- Batch endpoints (``/api/tools``, ``/api/tools/tests_summary``,
  ``/api/tool_panels`` …) answer from the index instead of iterating the
  full toolbox.

Module Layout
-------------

::

    lib/galaxy/tool_source_store/
      __init__.py        ToolSourceStore ABC, StoredToolSource, build_tool_source_store()
      database.py        DatabaseToolSourceStore (uses tool_source + tool_index tables)
      sqlalchemy.py      SqlAlchemyToolSourceStore (any SA URL; sqlite shortcut)
      composite.py       CompositeToolSourceStore (per-conf routing, merged index)
      index.py           ToolIndex, ToolIndexEntry (the lightweight metadata)
      models.py          Pydantic response models for the API layer

    lib/galaxy/tools/lazy_toolbox.py     LazyToolBox (subclass of ToolBox)
    lib/galaxy/tool_util/toolbox/
      base.py            (small hook to support lazy mode)
    lib/galaxy/tool_util/id_util.py      Cheap tool-ID extraction (regex, no XML parser)

    lib/galaxy/webapps/galaxy/services/tools.py          Batch endpoints (index-aware)

    scripts/tool_source/populate_store.py                Population & watch script
    scripts/tool_source/_discover.py                     Tool-file discovery (used by populate_store)

Data Model
----------

Two persistence concepts:

**StoredToolSource** — the canonical macro-expanded XML/YAML for a tool,
keyed by SHA-256 of the expanded content. Multiple versions of the same
``tool_id`` coexist as separate hashes. The DB backend persists these in the
store-owned ``tool_source_record`` table (the ``tool_source`` table belongs
to the job-request path and has a different payload contract); the Redis and
disk backends use their own layout.

**ToolIndex** — a single dataclass containing one ``ToolIndexEntry`` per tool,
holding everything the batch APIs need (id, name, description, panel section,
labels, EDAM, requirements, container info, test counts, hidden/disabled,
shed metadata). The index is serialized and gzip-compressed as a blob.

The DB backend gets the ``tool_index`` and ``tool_source_record`` tables
(migration ``f5a73c8b9d12``); ``tool_index`` holds a single row per index
version.
Redis stores the blob under a known key; disk stores it as a file.

Backend Abstraction
-------------------

``ToolSourceStore`` (in ``tool_source_store/__init__.py``) is an ABC defining:

- ``store/get/exists/delete/list_all/get_by_tool_id/count`` — per-tool source
  operations, all keyed by content hash.
- ``store_index/load_index/update_index_entry`` — index operations.
- ``get_stats()`` — backend-specific stats (count, size, backend name).

``build_tool_source_store(app)`` is the only entry point used by Galaxy. It
inspects ``config.tool_source_store`` and lazily imports the chosen backend
so deployments only pay for the dependencies they use (no SQLAlchemy import
on a Redis-only deploy, no ``redis`` client on a DB-only deploy).
``ConfigurationError`` is raised for unknown backends or missing required
settings; it is allowed to propagate up so misconfiguration fails fast at
startup.

The ABC defines a ``read_only: bool`` class attribute (default ``False``).
``ReadOnlyStoreError`` is raised by mutating methods of stores that opted
in. The populator, watch reload, and composite all consult this flag to
route around read-only members rather than crashing.

Per-conf composition
^^^^^^^^^^^^^^^^^^^^

If any tool_conf carries a top-level ``store="..."`` attribute (XML root)
or ``store: ...`` key (YAML), ``build_tool_source_store`` instantiates
the referenced named stores from ``config.tool_source_stores`` and wraps
them with the writable default in a :class:`CompositeToolSourceStore`.

The composite implements the same ``ToolSourceStore`` interface, so the
LazyToolBox, services, and queue worker stay completely unaware of the
multi-store layout:

- **Reads** iterate ``[per-conf members..., default]`` in order; first
  hit wins. ``count`` and ``list_all`` dedupe across members.
- **Writes** always land on the designated default. The default may not
  itself be ``read_only``; that's enforced at construction.
- ``load_index()`` calls each member's ``load_index()`` and folds the
  entries into a single :class:`ToolIndex`. Earlier members shadow later
  ones on tool-id collisions; ``by_section`` is unioned; ``built_at``
  takes the most recent value.
- ``invalidate_index_cache()`` fans out so a single Kombu reload hits
  every member.
- ``store_to(name, ...)`` lets the populator address a specific member by
  name without going through composite write routing.

When no tool_conf opts in, ``build_tool_source_store`` returns the
default store directly — the composite path is zero-cost for the common
case.

The ``sqlalchemy`` backend (``sqlalchemy.py``) was added to make this
useful for CVMFS: a single self-contained ``.sqlite`` file, opened with
its own SQLAlchemy ``MetaData`` (independent of ``galaxy.model``) so the
file is portable, and openable with ``mode=ro&uri=true`` for read-only
mounts. Despite the name, the backend is not sqlite-specific — pass any
SQLAlchemy ``url`` (Postgres, MySQL, …) instead of ``path``. Auto schema
creation runs on first open; on remote backends operators may prefer to
manage migrations explicitly.

Per-conf populator routing
^^^^^^^^^^^^^^^^^^^^^^^^^^

``scripts/tool_source/populate_store.py`` is per-conf aware. It reads
``parse_store_name()`` for each tool_conf, builds every named store plus
the default, and routes each ``DiscoveredTool.path`` to the store its
conf points at. By default it populates *every* writable store in one
run; ``--target NAME`` restricts to a single store and raises
``ReadOnlyStoreError`` if that store is read-only. Tools whose target is
read-only in default mode are silently skipped (the bundle is treated as
authoritative for those entries).

LazyToolBox
-----------

``LazyToolBox`` extends ``ToolBox`` rather than reimplementing it, so the rest
of Galaxy can keep using the same ``trans.app.toolbox`` interface. The key
override is ``__init__``: instead of calling ``_init_tools_from_configs`` and
loading every tool, it calls ``_init_lazy_toolbox`` which:

1. Sets up the same internal dicts (``_tools_by_id``, ``_tools_by_uuid``,
   etc.) that ``AbstractToolBox.__init__`` would.
2. Walks the tool conf files just enough to build the panel structure
   (sections, labels) and a ``tool_id → (section_id, section_name)`` map.
3. Loads the ``ToolIndex`` from the store. If the store has tool sources but
   no index, the index is rebuilt from the stored sources.
4. Populates ``_tools_by_id`` with stub entries from the index so
   ``has_tool()`` and similar lookups work without touching the store.

Full ``Tool`` objects are built on demand and kept in an ``LRUCache`` of
``lazy_toolbox_cache_size`` entries (default 500). Cache hits and misses are
guarded by an ``RLock`` for thread safety.

The toolbox auto-enables: if the operator hasn't set ``use_lazy_toolbox``,
``galaxy.app._use_lazy_toolbox()`` enables the lazy implementation when the
configured store contains at least one tool. This means a fresh deploy
without the populator run keeps the eager behavior, and only switches once
``populate_store.py`` succeeds.

Tool ID extraction
^^^^^^^^^^^^^^^^^^

``galaxy.tool_util.id_util`` provides ``extract_tool_id_from_xml`` and
``extract_tool_id_from_file``: regex-based ID lookup that reads only the
first ~2 KB of the XML. This avoids paying for full XML parsing during
panel-structure discovery, where we just need the ID to map a file entry
back to an index entry.

Discovery
^^^^^^^^^

``scripts.tool_source._discover.discover_tools`` walks tool config files
and yields ``DiscoveredTool`` records. It is used by:

- ``populate_store.py`` to find tools to parse and store.
- ``populate_store.py --watch`` to know which directories to monitor.
- (Indirectly) the LazyToolBox panel-structure code path.

Pulling discovery out of ``ToolBox`` was deliberate: the population script
must run *without* a full app (or even a running Galaxy), and the watch
mode must run in a long-lived loop with no Galaxy process at all.

Population Script
-----------------

``scripts/tool_source/populate_store.py`` runs out of process. It builds a
minimal app context (datatypes registry + SQLAlchemy model + config) and
calls ``build_tool_source_store`` with that context. Tools are parsed in a
``ThreadPoolExecutor`` (``--parallel``, default 4 workers); each tool is
hashed and skipped if an entry with the same hash already exists
(``--incremental``, the default).

Watch mode (``--watch``) uses ``watchdog`` to monitor every directory yielded
by ``discover_tools``. File events are debounced (default 2 s), the changed
files are re-parsed, the store is updated, and a single
``reload_tool_source_cache`` Kombu control task is published on the Galaxy
exchange. ``--watch-polling`` switches to ``PollingObserver`` for
NFS/CVMFS/network filesystems where inotify is unreliable.

The control task handler lives in ``galaxy.queue_worker.reload_tool_source_cache``
and is wired into the ``control_message_to_task`` map. Each Galaxy process
that receives the message:

1. Calls ``LazyToolBox.invalidate_index_cache()`` (drops the in-memory
   index reference so the next access reloads from the store).
2. Calls ``ToolSourceStore.invalidate_index_cache()`` on the store itself.

Note that the LRU cache of fully constructed ``Tool`` objects is not
flushed by reload — only the index is invalidated. Stale ``Tool`` instances
are evicted naturally as new ones are loaded.

Batch Endpoint Integration
--------------------------

``ToolsService`` (``services/tools.py``) checks at runtime whether
``trans.app.toolbox`` is a ``LazyToolBox`` (via ``_get_lazy_toolbox``) and
routes accordingly:

- ``list_tools(in_panel=False)`` → ``index.list_all()`` mapped to API dicts.
- ``search_tools`` → ``index.search()`` returning IDs.
- ``get_tests_summary`` → ``index.get_tests_summary()``.
- ``get_all_requirements`` → ``index.get_all_requirements()``.
- ``get_panel_views`` → ``index.get_panel_views()`` for views, plus the
  toolbox's own ``default_panel_view``.

In every case there is a fallback path that iterates the eager toolbox, so
the same code works on deployments that have not opted into lazy mode.

``ToolAPICache`` (``api_cache.py``) sits in front of the gzip-compressed JSON
representations of these batch responses, keyed by the canonical request
URL and TTL'd by ``tool_api_cache_ttl`` (default 300 s, ``0`` disables).

API Layer
---------

``api/tool_sources.py`` exposes three FastAPI ``Router.cbv`` controllers:

- ``ToolSourcesAPI`` — store inspection (admin-only).
- ``ToolIndexAPI`` — index browsing (mostly public, ``/stats`` is admin).
- ``ToolCacheAPI`` — LazyToolBox cache stats and clear (admin-only).

Static suffix routes (``/stats``, ``/search``) deliberately precede the
``/{id}`` and ``/{hash}`` parameterized routes to avoid path shadowing —
this is enforced by route declaration order, not by FastAPI itself.

``services/tool_sources.py`` is the thin service layer over the store and
the index. It depends on ``trans.app.tool_source_store``; the LazyToolBox
is only consulted for cache stats/clear.

App Wiring
----------

``galaxy.app.UniverseApplication.__init__`` calls
``_init_tool_source_store`` early and registers the result as a singleton
under ``ToolSourceStore``. The toolbox is then chosen based on
``_use_lazy_toolbox()`` (explicit config override, otherwise auto-detect).
The store is exposed as ``app.tool_source_store`` and is ``Optional`` only
to satisfy type checkers — in practice the build either succeeds or raises
``ConfigurationError``.

Design Notes
------------

**Why a separate index instead of always-querying-the-store?** Batch
endpoints need O(N) access to N entries; doing that against Redis or the
disk is a latency hit on every request. Keeping the index in-process and
only paying for invalidation on reload is the better tradeoff.

**Why an out-of-process populator?** Parsing tools and computing macro
expansions is expensive and shouldn't block worker startup. Keeping the
populator separate also lets it run on a single host while many web workers
share the resulting store (especially with the Redis backend).

**Why subclass ToolBox instead of building a parallel hierarchy?**
``trans.app.toolbox`` is referenced from hundreds of call sites that expect
the full ToolBox interface. Subclassing keeps the Liskov-substitution
property and lets unmodified callers benefit from lazy loading transparently.

**Why hash-keyed storage?** Content-addressed storage gives us cheap
deduplication across versions and shed installations, and idempotent
incremental updates: re-running the populator over an unchanged tree is
effectively a no-op.

Testing
-------

- Unit tests: ``test/unit/tool_source_store/test_stores.py`` exercises each
  backend through the ``ToolSourceStore`` interface.
- Integration tests: ``test/integration/test_tool_source_storage.py`` spins
  up Galaxy with each backend and verifies end-to-end behavior.
- Populator tests: ``test/unit/scripts/tool_source/test_populate_store.py``
  uses fakes (not mocks) of ``ToolSourceStore`` so behavior is verified
  against the real interface.
- API tests: ``lib/galaxy_test/api/test_tool_sources.py``.
- Benchmarks: ``python -m galaxy.tool_source_store.benchmarks --iterations 100``.
