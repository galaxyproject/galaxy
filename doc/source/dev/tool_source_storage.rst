Tool Source Storage Architecture
================================

This document describes the architecture of the tool source storage subsystem:
the store backends, the populator, and the index they build. For operator-facing
setup and configuration, see :doc:`/admin/tool_source_storage`.

The ``CachedToolBox`` consumes this store to load tools on demand; it is
documented below alongside the storage layer it builds on.

Goals
-----

The traditional ``ToolBox`` parses every tool XML at startup, builds full
``Tool`` objects, and keeps them all in memory. With thousands of tools that
scales poorly: slow boot, large per-process RSS, and expensive worker reloads.

The tool source storage subsystem moves that parsing work out of the request
path:

- A separate process (``populate_store.py``) parses tools once and persists
  the canonical, macro-expanded source plus a lightweight metadata index.
- The store and index are laid out so a consumer can load only the index at
  startup and materialize ``Tool`` objects on demand, instead of parsing the
  full tree in-process. That consumer is the ``CachedToolBox``.
- Batch endpoints (``/api/tools``, ``/api/tools/tests_summary``,
  ``/api/tool_panels`` …) answer from the index instead of iterating the
  full toolbox.

Module Layout
-------------

::

    lib/galaxy/tools/source_store/
      __init__.py        Public re-exports
      interface.py       ToolSourceStore ABC and StoredToolSource
      factory.py         Store construction from Galaxy configuration
      sqlalchemy.py      SqlAlchemyToolSourceStore (any SQLAlchemy URL)
      composite.py       CompositeToolSourceStore (per-conf routing, merged index)
      index.py           ToolIndex, ToolIndexEntry (the lightweight metadata)
      search.py          ToolWhooshIndex (Whoosh search index built from a ToolIndex)
      discover.py        discover_tools() — conf walk without booting a ToolBox
      populator.py       Population + watch logic (parse, store, index, broadcast)
      freshness.py       Optional external freshness probes
      watcher.py         Filesystem watch support
      benchmarks.py      Store/index micro-benchmarks

    lib/galaxy/tools/cached_toolbox.py     CachedToolBox (subclass of ToolBox), CachedTool
    lib/galaxy/tools/search/__init__.py  CachedToolboxSearch (queries every store's index)

    scripts/tool_source/populate_store.py    Thin CLI wrapper over populator.main

The same ``populator.main`` is registered as the
``galaxy-populate-tool-source-store`` console script in the ``galaxy-app``
package metadata (``packages/app/pyproject.toml``).

Data Model
----------

Two persistence concepts:

**StoredToolSource** — the canonical macro-expanded XML/YAML for a tool,
keyed by SHA-256 of the expanded content. Multiple versions of the same
``tool_id`` coexist as separate hashes. The store keeps its own schema in a
standalone database (a SQLite file by default, any SQLAlchemy URL for shared
deployments) — deliberately outside Galaxy's database: the store is a
rebuildable cache and does not participate in Galaxy's migrations or session
lifecycle.

**ToolIndex** — a Pydantic model containing one default ``ToolIndexEntry`` per tool
plus its versioned and panel-placement projections,
holding everything a store consumer needs (id, name, description, panel section,
labels, EDAM, requirements, container info, test counts, hidden/disabled,
shed metadata). The index is serialized and gzip-compressed as a blob.

The schema is auto-created on first open; ``tool_index`` holds a single
row per index version.

Backend Abstraction
-------------------

``ToolSourceStore`` (in ``tools/source_store/interface.py``) is an ABC defining:

- ``store/get/exists/delete/list_all/get_by_tool_id/count`` — per-tool source
  operations, all keyed by content hash.
- ``store_index/load_index/update_index_entry`` — index operations.
- ``get_stats()`` — backend-specific stats (count, size, backend name).

``build_tool_source_store(config)`` is the only entry point used
by Galaxy. It builds the default store from
``config.tool_source_database_connection`` and uses the same SQLAlchemy-backed
store implementation for all configured URIs. The store is only built when
``use_cached_toolbox`` is enabled — default deployments never initialize it.
``ConfigurationError`` is raised for missing required settings and is allowed
to propagate up so misconfiguration fails fast at startup.

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

The composite implements the same ``ToolSourceStore`` interface, so store
consumers stay completely unaware of the multi-store layout:

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
file is portable, and openable with a SQLite URI such as
``sqlite:///file:/cvmfs/example.org/tools/sources.sqlite?mode=ro&uri=true``
for read-only mounts. Despite the name, the backend is not sqlite-specific -
pass any SQLAlchemy URL (Postgres, MySQL, ...). Auto schema creation runs on
first open; on remote backends operators may prefer to manage migrations
explicitly.

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

CachedToolBox
-----------

``CachedToolBox`` extends ``ToolBox`` rather than reimplementing it, so the rest
of Galaxy can keep using the same ``trans.app.toolbox`` interface. The key
override is ``_init_tools_from_configs``:

1. It loads the persistent ``ToolIndex`` from the store. If the index does
   not cover every tool the configs reference (fresh checkout, new conf
   entry, wiped store), the populator runs in-process to fill the gap —
   it is content-addressed and idempotent, so re-runs on a warm store only
   touch new rows.
2. It then delegates to the eager conf walk. Every ``<tool>`` the walk
   loads lands in ``create_tool``, where indexed sources short-circuit to a
   ``CachedTool`` stub instead of parsing; the panel, ``_tools_by_id``, and
   lineage bookkeeping are all built by the unmodified upstream pipeline
   operating on stubs.

Full ``Tool`` objects are built on demand and kept in an ``LRUCache`` of
``cached_toolbox_cache_size`` entries (default 500). Cache hits and misses are
guarded by an ``RLock`` for thread safety.

Opting in is explicit: only ``use_cached_toolbox: true`` activates the cached
toolbox. A populated store on its own (e.g. brought in by a per-conf
``store="..."`` attribute) does not flip a default deployment to cached-toolbox mode.

Discovery
---------

``galaxy.tools.source_store.discover.discover_tools`` walks tool config files
and yields ``DiscoveredTool`` records without booting a full ``ToolBox``. It is
used by:

- the populator to find tools to parse and store.
- watch mode to know which directories to monitor.
- callers that compare on-disk confs against the indexed tool set.

It also walks ``data_manager_conf``/``shed_data_manager_conf`` and the
datatype converters so data-manager and converter tools — loaded post-boot
outside any tool_conf — still land in the index.

Pulling discovery out of ``ToolBox`` was deliberate: the populator must run
*without* a full app (or even a running Galaxy), and the watch mode must run in
a long-lived loop with no Galaxy process at all.

Population Script
-----------------

``scripts/tool_source/populate_store.py`` is a thin CLI wrapper over
``galaxy.tools.source_store.populator.main``. It loads only the Galaxy
config and calls ``build_tool_source_store(config)``. Converter discovery builds
the datatypes registry, but the standalone process does not initialize the Galaxy
model. Tools are parsed in a
``ThreadPoolExecutor`` (``--parallel``, default 4 workers); each tool is
matched to its source path and carried forward when its raw file hash is unchanged
(``--incremental``, the default). Once the JSON index is committed the
populator rebuilds the Whoosh search index (``search.py``) so ranked tool
search stays in sync with the stored sources.

Watch mode (``--watch``) uses ``watchdog`` to monitor every directory yielded
by ``discover_tools``. File events are debounced (default 2 s), the changed
files are re-parsed, the store is updated, and a single
``reload_tool_source_cache`` Kombu control task is published on the Galaxy
exchange. ``--watch-polling`` switches to ``PollingObserver`` for
NFS/CVMFS/network filesystems where inotify is unreliable.

The broadcast is the populator's half of the contract: it publishes
``reload_tool_source_cache`` so peer processes can drop their stale index
view. The control task handler lives in
``galaxy.queue_worker.reload_tool_source_cache`` and is wired into the
``control_message_to_task`` map. Each Galaxy process that receives the
message:

1. Calls ``CachedToolBox.invalidate_index_cache()`` (drops the in-memory
   index reference so the next access reloads from the store).
2. Calls ``ToolSourceStore.invalidate_index_cache()`` on the store itself.

Reload also refreshes already-materialised tools: entries whose source hash
changed have their LRU entries, stubs, and registered ``Tool`` objects
purged, so the next access re-materialises from the new source. Unchanged
entries keep their cached ``Tool`` objects.

Batch Endpoint Integration
--------------------------

``ToolsService`` (``services/tools.py``) serves the batch endpoints without
materialising tools:

- ``list_tools`` (flat and panel) goes through ``AbstractToolBox.to_dict``
  in both modes — the per-user ``FilterFactory`` pass runs as in eager mode,
  and ``get_tool_to_dict`` serves ``CachedTool`` stubs from their index
  entries.
- ``search_tools`` queries the ``app.toolbox_search`` singleton
  (``CachedToolboxSearch`` in cached-toolbox mode); hits are resolved against registered
  stubs via ``CachedToolBox.resolve_search_hit`` with a per-hit access check.
- ``get_tests_summary`` and ``get_all_requirements`` answer from
  ``ToolIndex`` entries when the cached toolbox is active, and iterate the toolbox
  otherwise.

The integration suite pins this: ``_cached_materialize_count`` (bumped in the
single materialise chokepoint) must not move across any of these endpoints.

``CachedToolboxSearch`` (``tools/search/__init__.py``) queries the whoosh index
of *every* configured store — the default plus each named per-conf store —
via ``ToolWhooshIndex.search_scored``, then merges the per-store hit lists by
BM25 score and post-filters them to the requested panel view. A tool served
from a named store is therefore reachable through ``/api/tools?q=`` even
though its source lives outside the default store.

App Wiring
----------

``galaxy.app.UniverseApplication.__init__`` calls
``_init_tool_source_store`` early and registers the result as a singleton
under ``ToolSourceStore``. The toolbox is then chosen based on
``use_cached_toolbox``. The store is exposed as ``app.tool_source_store`` and is
``Optional`` only to satisfy type checkers — in practice the build either
succeeds or raises ``ConfigurationError``.

Design Notes
------------

**Why a separate index instead of always querying the store?** A consumer
needs O(N) access to N entries; doing that against the backing store on every
request is a latency hit. Keeping the index in-process and only paying for
invalidation on reload is the better tradeoff.

**Why an out-of-process populator?** Parsing tools and computing macro
expansions is expensive and shouldn't block worker startup. Keeping the
populator separate also lets it run on a single host while many web workers
share the resulting store.

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

- Store unit tests: ``test/unit/app/tools/source_store/`` exercises each backend
  through the ``ToolSourceStore`` interface (``test_stores.py``,
  ``test_sqlite_store.py``, ``test_composite_store.py``,
  ``test_index_versions.py``, ``test_multi_store_search.py``).
- Populator/discovery unit tests: ``test/unit/scripts/tool_source/``
  (``test_populate_store.py``, ``test_discover.py``,
  ``test_build_index_entry.py``, ``test_whoosh_dir.py``). These use fakes
  (not mocks) of ``ToolSourceStore`` so behavior is verified against the real
  interface.
- Integration tests: ``test/integration/test_tool_source_storage.py`` spins
  up Galaxy against the store and verifies end-to-end behavior.
- Benchmarks: ``python -m galaxy.tools.source_store.benchmarks --iterations 100``.
