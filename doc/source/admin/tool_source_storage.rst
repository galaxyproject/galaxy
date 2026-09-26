Tool Source Storage
===================

Overview
--------

By default, Galaxy parses every tool at startup and keeps all of them in
memory. For installations with many tools this:

- Slows down Galaxy startup significantly
- Consumes large amounts of memory in every Galaxy process

Tool source storage addresses this by doing the parsing work once, ahead of
time:

1. Tool sources are pre-parsed (with macros expanded) and stored in a
   configurable database backend
2. A lightweight index over the stored tools supports fast tool listings and
   search without touching tool files

The ``CachedToolBox`` consumes this store to load full ``Tool`` objects on
demand with LRU caching. It is opt-in via ``use_cached_toolbox``; this document
covers the store, the populator, the index, and the toolbox configuration.

Configuration
-------------

Tool source storage is configured in ``galaxy.yml``. The following options are available:

Default Store
^^^^^^^^^^^^^

.. code-block:: yaml

    galaxy:
      # SQLAlchemy URI for storing tool sources.
      tool_source_database_connection: sqlite:////srv/galaxy/tool_sources.sqlite

The store lives in a standalone database - a SQLite file under
``<data_dir>/tool_sources.sqlite`` by default - separate from Galaxy's main
database. It is a rebuildable cache: it can be deleted at any time and
recreated by re-running the population script.

Multi-host deployments must point every Galaxy process (web workers *and*
job handlers) at the same store — typically a SQLite file on a shared
filesystem:

.. code-block:: yaml

    galaxy:
      tool_source_database_connection: sqlite:////shared/galaxy/tool_sources.sqlite

Any other SQLAlchemy-supported database (e.g. PostgreSQL) works as well.

Toolbox Selection
^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    galaxy:
      # Opt in to the CachedToolBox. Off by default; setting this to true is
      # required to activate per-conf store="..." routing.
      use_cached_toolbox: true

The CachedToolBox is opt-in: leave ``use_cached_toolbox`` unset (or false) and
Galaxy uses the traditional eager ToolBox even when the store is populated
or when a tool_conf carries a ``store="..."`` attribute. The store is only
initialized when the CachedToolBox is enabled.

Cache Configuration
^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    galaxy:
      # Maximum Tool objects in the CachedToolBox LRU cache (default: 500)
      cached_toolbox_cache_size: 500

The ``cached_toolbox_cache_size`` determines how many fully-loaded Tool objects
are kept in memory by the CachedToolBox. If your users frequently work with
many different tools, increase this value.

Per-conf Store Routing (CVMFS Recipe)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Individual ``tool_conf`` files can opt into a *named* tool source store,
distinct from the global default. The typical use case is shipping a
read-only SQLite bundle on CVMFS alongside a tool_conf, so worker
processes can resolve every tool in that conf with local-cached lookups
instead of one network round-trip per JSON file.

Declare the named stores under the top-level ``tool_source_stores`` key in
``galaxy.yml``. Each entry takes either a normal SQLAlchemy ``url`` or a
published ``external_store_directory``. Manifests are ignored for normal URL
stores. SQLite is the typical choice for CVMFS bundles (single self-contained
file), but any SQLAlchemy-supported database works for an explicit URL:

.. code-block:: yaml

    galaxy:
      tool_source_database_connection: sqlite:////srv/galaxy/tool_sources.sqlite
      tool_source_stores:
        cvmfs_main:
          url: sqlite:///file:/cvmfs/example.org/tools/sources.sqlite?mode=ro&uri=true
          read_only: true
        site_shared:
          url: sqlite:///file:/shared/galaxy/tool_sources.sqlite?mode=ro&uri=true
          read_only: true

Then point the tool_conf at it via the root element's ``store`` attribute
(XML) or top-level key (YAML):

.. code-block:: xml

    <?xml version="1.0"?>
    <toolbox store="cvmfs_main">
      <section id="cvmfs_tools" name="CVMFS Tools">
        <tool file="bwa/bwa.xml"/>
        ...
      </section>
    </toolbox>

At startup, Galaxy inspects every ``tool_conf`` for the attribute, builds
the referenced stores, and wraps them with the writable default in a
composite store. Reads are tried in declared order (first hit wins) and
writes always go to the default store. If no tool_conf opts in, the
default store is used directly with zero overhead.

**Building the bundle**

Build the SQLite file from a writable host before shipping it:

.. code-block:: console

    $ python scripts/tool_source/populate_store.py -c galaxy.yml --target cvmfs_main

For a file-backed SQLite target, the standalone populator also writes a
sidecar named after the database, for example
``sources.sqlite.manifest.json``. External-store consumers use it to select a
compatible bundle. Failure to write the sidecar fails the command. ``--dry-run``
and in-process Galaxy population do not produce manifests.

Use ``--target`` to restrict population to a single named store; without
it, ``populate_store.py`` populates **every writable store** referenced
from a tool_conf in the same run.

Once the bundle is in place on CVMFS (or any read-only mount), restart
Galaxy. The ``read_only: true`` flag prevents Galaxy from writing through that
store. For SQLite connection-level read-only, use ``mode=ro&uri=true`` in the
SQLite URI as shown above.

Cross-version CVMFS bundles
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``external_store_directory`` to let Galaxy select a compatible bundle from
a published cohort directory:

.. code-block:: yaml

    galaxy:
      tool_source_stores:
        cvmfs_main:
          external_store_directory: /cvmfs/example.org/config/tool_source_store

External stores are read-only. If no compatible bundle is available, Galaxy
logs a warning and parses the tools normally. Galaxy versions predating
automatic selection should configure a specific bundle with ``url`` instead.

Populating the Tool Source Store
--------------------------------

After configuring tool source storage, you need to populate it with your tools.
Use the ``populate_store.py`` script:

Basic Usage
^^^^^^^^^^^

.. code-block:: console

    $ python scripts/tool_source/populate_store.py --config /path/to/galaxy.yml

Deployments that install Galaxy from packages get the same command as the
``galaxy-populate-tool-source-store`` console script (shipped with the
``galaxy-app`` package), so no Galaxy source checkout is needed:

.. code-block:: console

    $ galaxy-populate-tool-source-store --config /path/to/galaxy.yml

This will:

1. Discover tools from your tool configs (uses the same logic as Galaxy startup)
2. Parse each tool (with macro expansion) and compute a content hash
3. Store the tool sources in the configured backend (skipping unchanged tools)

Note: ``--config`` is required; the script does not assume a default path.

Command Line Options
^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

    $ python scripts/tool_source/populate_store.py --help

    Options:
      --config, -c PATH      Galaxy configuration file (required)
      --dry-run              Show what would be stored without storing
      --incremental          Only store new/changed tools (default)
      --full                 Force re-store of all tools
      --tool-id PATTERN      Only process tools whose ID contains PATTERN
      --parallel, -j N       Number of parallel workers (default: 4)
      --rebuild-index        Rebuild the tool index after population
      --target NAME          Restrict to a single named store from
                             tool_source_stores (or '__default__'). Without
                             this, every writable store is populated.
      --verbose, -v          Verbose output
      --watch, -w            Watch tool directories and send reload notifications
      --watch-polling        Use polling observer (for NFS/CVMFS/network FS)

Every non-dry-run invocation of the standalone command, including watch mode,
refreshes the manifest beside each writable file-backed SQLite store it
updates. Non-SQLite and in-memory stores have no sidecar and are skipped.

Examples
^^^^^^^^

**Initial population:**

.. code-block:: console

    $ python scripts/tool_source/populate_store.py -c /path/to/galaxy.yml

**Force re-store everything (e.g., after a parser change):**

.. code-block:: console

    $ python scripts/tool_source/populate_store.py -c galaxy.yml --full

**Process only a subset of tools:**

.. code-block:: console

    $ python scripts/tool_source/populate_store.py -c galaxy.yml --tool-id samtools

Automation with Cron
^^^^^^^^^^^^^^^^^^^^

For installations where tools are frequently updated, you can run the population
script on a schedule:

.. code-block:: cron

    # Update tool source store every hour (incremental is the default)
    0 * * * * /path/to/galaxy/.venv/bin/python /path/to/galaxy/scripts/tool_source/populate_store.py -c /path/to/galaxy.yml >> /var/log/galaxy/tool_source_update.log 2>&1

Watch Mode (Live Updates)
^^^^^^^^^^^^^^^^^^^^^^^^^

As an alternative to cron, you can run the population script in watch mode to
keep the store continuously up to date. This uses ``watchdog`` to monitor tool
directories for changes and automatically updates the store, then sends a
notification via Kombu to trigger cache reloads in all Galaxy processes.

.. code-block:: console

    $ python scripts/tool_source/populate_store.py --config galaxy.yml --watch

Watch mode options:

- ``--watch, -w`` - Enable watch mode
- ``--watch-polling`` - Use polling observer (required for network filesystems like NFS/CVMFS)

Example with polling for network filesystem:

.. code-block:: console

    $ python scripts/tool_source/populate_store.py -c galaxy.yml --watch --watch-polling

**Requirements:**

- The ``watchdog`` library must be installed: ``pip install watchdog``
- Galaxy must have ``amqp_internal_connection`` configured for Kombu notifications
- All Galaxy processes must be connected to the same AMQP broker

When a tool XML file changes, watch mode will:

1. Detect the file change (with debouncing to handle rapid edits)
2. Re-parse the tool and update the store
3. Send a ``reload_tool_source_cache`` control message via Kombu
4. All Galaxy processes will invalidate their local caches

This is useful for:

- Installations using shared storage where tools may be updated externally
- CI/CD pipelines that deploy tool updates
- Development environments where tools are being actively edited

Troubleshooting
---------------

Tools not appearing in the index
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Re-run the population script with verbose output:

   .. code-block:: console

       $ python scripts/tool_source/populate_store.py -c galaxy.yml -v

2. Check for parsing errors in the Galaxy log

High memory usage
^^^^^^^^^^^^^^^^^

1. Reduce ``cached_toolbox_cache_size`` to cache fewer Tool objects
2. Ensure ``use_cached_toolbox: true`` is set in ``galaxy.yml``

Populating an existing installation
-----------------------------------

To set up tool source storage on an existing Galaxy installation:

1. Add the configuration to ``galaxy.yml``:

   .. code-block:: yaml

       galaxy:
         use_cached_toolbox: true
         tool_source_database_connection: sqlite:////srv/galaxy/tool_sources.sqlite

2. Run the population script:

   .. code-block:: console

       $ python scripts/tool_source/populate_store.py -c /path/to/galaxy.yml

3. Restart Galaxy

If the store is not populated, or a specific tool is missing from it, the
CachedToolBox self-heals by populating the missing entries in-process, so the
traditional toolbox behavior is preserved as a fallback.
