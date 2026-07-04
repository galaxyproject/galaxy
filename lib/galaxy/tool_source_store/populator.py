"""
Tool source store populator.

Walks Galaxy's tool configuration files, parses each tool source, and writes
the canonical ``StoredToolSource`` + ``ToolIndex`` rows into every writable
tool source store. Single writer of the index and (in subsequent commits) the
whoosh search index — :class:`galaxy.tools.lazy_toolbox.LazyToolBox` is a
read-only consumer.

Two execution modes:

- Standalone: ``scripts/tool_source/populate_store.py`` invokes :func:`main`.
- In-process: callers (cold-start auto-populate, shed-install reroute,
  ``reset_shed_tools``) import :func:`populate_store_inline` /
  :func:`populate_for_paths` / :func:`reconcile_index` directly.

The watch mode (:func:`watch_mode`, :class:`ToolFileWatcher`) is a development
loop that updates the store as tool files change on disk and broadcasts a
``reload_tool_source_cache`` control task to every Galaxy process.
"""

import argparse
import hashlib
import logging
import signal
import sys
import threading
import time
from collections.abc import (
    Callable,
    Iterator,
)
from concurrent.futures import (
    as_completed,
    ThreadPoolExecutor,
)
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from typing import (
    Any,
    cast,
)

from kombu import Connection
from kombu.pools import producers

from galaxy.config import GalaxyAppConfiguration
from galaxy.datatypes.registry import Registry
from galaxy.model import set_datatypes_registry
from galaxy.model.mapping import init_models_from_config
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.queues import galaxy_exchange
from galaxy.tool_source_store import (
    _build_default_store,
    build_named_store,
    build_tool_source_store,
    ReadOnlyStoreError,
    StoredToolSource,
    ToolSourceStore,
)
from galaxy.tool_source_store.discover import (
    discover_tools,
    DiscoveredTool,
)
from galaxy.tool_source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tool_source_store.search import (
    ToolSearchTuning,
    ToolWhooshIndex,
)
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.parser.util import parse_tool_version_with_defaults
from galaxy.tool_util.toolbox.parser import get_toolbox_parser
from galaxy.util.properties import load_app_properties

log = logging.getLogger(__name__)


def compute_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


def iter_tool_sources(toolbox, pattern: str | None = None) -> Iterator[tuple]:
    """
    Iterate over all tools in the toolbox.

    Yields:
        Tuples of (tool_id, version, tool_source, tool_dir).
    """
    for tool_id, tool in toolbox._tools_by_id.items():
        if pattern and pattern not in tool_id:
            continue
        if hasattr(tool, "tool_source") and tool.tool_source:
            yield tool_id, tool.version, tool.tool_source, getattr(tool, "tool_dir", None)


def send_reload_notification(config) -> bool:
    """
    Send a reload_tool_source_cache control task via Kombu.

    Args:
        config: Galaxy configuration object.

    Returns:
        True if message was sent successfully, False otherwise.
    """
    try:
        amqp_url = config.amqp_internal_connection
        if not amqp_url:
            log.warning("No amqp_internal_connection configured, cannot send reload notification")
            return False

        connection = Connection(amqp_url)
        payload = {
            "task": "reload_tool_source_cache",
            "kwargs": {},
        }

        with producers[connection].acquire(block=True, timeout=10) as producer:
            producer.publish(
                payload,
                exchange=galaxy_exchange,
                routing_key="control.*",
                retry=True,
                headers={"epoch": time.time()},
            )

        log.info("Sent reload_tool_source_cache notification to all Galaxy processes")
        return True

    except Exception as e:
        log.error(f"Failed to send reload notification: {e}")
        return False


class ToolFileWatcher:
    """
    Watches tool directories for changes and triggers store updates.

    Uses watchdog for filesystem monitoring and sends Kombu notifications
    when tools are updated.
    """

    def __init__(
        self,
        config,
        store,
        tools_dirs: list,
        debounce_seconds: float = 2.0,
        use_polling: bool = False,
        verbose: bool = False,
        notify_callable: Callable[[Any], bool] | None = None,
        sa_session: Any = None,
    ):
        self.config = config
        self.store = store
        # ``sa_session`` is required when the watcher should update the index
        # alongside the store on each file change; passing ``None`` keeps the
        # watcher store-only (used by older callers / tests that mock the
        # session out).
        self.sa_session = sa_session
        self.tools_dirs = tools_dirs
        self.debounce_seconds = debounce_seconds
        self.use_polling = use_polling
        self.verbose = verbose
        # Injected so tests can substitute a fake; default is the AMQP notifier.
        self._notify = notify_callable or send_reload_notification
        # ``watchdog`` observer; typed Any because watchdog is an optional
        # dependency imported inside :meth:`start`.
        self.observer: Any = None
        self._pending_changes: set[str] = set()
        self._lock = threading.Lock()
        self._debounce_timer: threading.Timer | None = None
        self._shutdown_event = threading.Event()

    def start(self):
        """Start watching for file changes."""
        # ``watchdog`` is an optional dependency only needed for --watch mode;
        # keep the import local so plain populate runs (and the galaxy-app
        # package, which doesn't ship watchdog) can import this module.
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
        from watchdog.observers.polling import PollingObserver

        observer_class = PollingObserver if self.use_polling else Observer

        class ToolFileHandler(FileSystemEventHandler):
            def __init__(handler_self, watcher):
                handler_self.watcher = watcher

            def on_any_event(handler_self, event):
                if event.is_directory:
                    return
                path = getattr(event, "dest_path", None) or event.src_path
                if path.endswith(".xml") and "macro" not in path.lower():
                    handler_self.watcher._queue_change(path)

        self.observer = observer_class()
        handler = ToolFileHandler(self)

        for tools_dir in self.tools_dirs:
            if tools_dir and tools_dir.exists():
                log.info(f"Watching directory: {tools_dir}")
                self.observer.schedule(handler, str(tools_dir), recursive=True)

        self.observer.start()
        log.info("File watcher started")
        return True

    def _queue_change(self, path: str):
        """Queue a file change for processing with debouncing."""
        with self._lock:
            self._pending_changes.add(path)

            # Cancel existing timer if any
            if self._debounce_timer:
                self._debounce_timer.cancel()

            # Start new debounce timer
            self._debounce_timer = threading.Timer(
                self.debounce_seconds,
                self._process_pending_changes,
            )
            self._debounce_timer.start()

    def _process_pending_changes(self):
        """Process all pending file changes."""
        with self._lock:
            if not self._pending_changes:
                return

            changes = list(self._pending_changes)
            self._pending_changes.clear()

        log.info(f"Processing {len(changes)} changed tool file(s)")

        updated = 0
        for path in changes:
            try:
                if self._process_tool_file(path):
                    updated += 1
            except Exception as e:
                log.error(f"Error processing {path}: {e}")

        if updated > 0:
            log.info(f"Updated {updated} tool(s), sending reload notification")
            self._notify(self.config)

    def _process_tool_file(self, path: str) -> bool:
        """Process a single tool file and update the store + index.

        First does a lightweight raw-content hash check so the watcher
        can bail on unchanged files without paying for macro expansion.
        If the content is new, delegates to :func:`populate_for_paths`,
        which runs the full parse-and-persist path: ``StoredToolSource``
        write, ``ToolIndexEntry`` build (with section + labels from the
        conf walk), whoosh rebuild, and the ``reload_tool_source_cache``
        broadcast — same machinery a shed install hits.
        """
        import xml.etree.ElementTree as ET

        try:
            with open(path) as f:
                raw_content = f.read()
        except OSError as e:
            log.warning(f"Could not read {path}: {e}")
            return False

        try:
            root = ET.fromstring(raw_content)
        except ET.ParseError as e:
            log.warning(f"Could not parse {path}: {e}")
            return False

        if root.tag != "tool":
            return False

        content_hash = compute_hash(raw_content)
        if self.store.exists(content_hash):
            if self.verbose:
                log.debug(f"Tool unchanged: {path}")
            return False

        if self.sa_session is None:
            # Legacy/no-session caller: degrade to store-only update so the
            # watcher still keeps StoredToolSource current. The next full
            # populator run picks up the index entry.
            stored = StoredToolSource(
                hash=content_hash,
                tool_source_class="XmlToolSource",
                raw_source=raw_content,
                tool_id=root.get("id"),
                tool_version=root.get("version"),
                tool_dir=str(Path(path).parent),
                source_path=str(path),
                stored_at=datetime.now(timezone.utc),
            )
            self.store.store(stored)
            log.info("Updated stored source for %s (index left stale)", path)
            return True

        populate_for_paths(self.config, self.sa_session, [path], rebuild_whoosh=True)
        log.info("Updated tool: %s", path)
        return True

    def wait(self):
        """Wait for shutdown signal."""
        self._shutdown_event.wait()

    def shutdown(self):
        """Stop the watcher."""
        log.info("Shutting down file watcher...")
        self._shutdown_event.set()

        if self._debounce_timer:
            self._debounce_timer.cancel()

        if self.observer:
            self.observer.stop()
            self.observer.join()

        log.info("File watcher stopped")


DEFAULT_STORE_NAME = "__default__"

# Sub-directory under ``config.tool_search_index_dir`` where the default
# store's whoosh index lives. Named for backwards-compat with the LazyToolBox
# ``_get_search_index`` path (which previously built this index in-process).
_WHOOSH_DEFAULT_SUBDIR = "_lazy_default"


def whoosh_dir_for_store(tool_search_index_dir: str | None, store_name: str) -> str | None:
    """Resolve the on-disk whoosh dir for ``store_name``.

    Returns ``None`` if the config doesn't define ``tool_search_index_dir``
    (whoosh search is then disabled). The default store maps to
    ``_lazy_default`` so :class:`galaxy.tools.lazy_toolbox.LazyToolBox` reads
    the same path it always has; named stores get their own sub-dir.
    """
    if not tool_search_index_dir:
        return None
    sub = _WHOOSH_DEFAULT_SUBDIR if store_name == DEFAULT_STORE_NAME else store_name
    import os

    return os.path.join(tool_search_index_dir, sub)


def _build_whoosh_for_store(config, store_name: str, tool_index) -> None:
    """Rebuild the whoosh index for ``store_name`` from ``tool_index``.

    No-ops if ``tool_search_index_dir`` is unset. Logs and swallows whoosh
    failures: the toolbox surfaces them to users at query time (the
    populator's job is to write what it can; an unbuildable index is a
    deploy issue, not a populator-CLI fatal).
    """
    index_dir = whoosh_dir_for_store(config.tool_search_index_dir, store_name)
    if index_dir is None:
        return
    try:
        tuning = ToolSearchTuning.from_config(config)
        searcher = ToolWhooshIndex(index_dir=index_dir, tuning=tuning)
        count = searcher.build(tool_index)
        log.info("Built whoosh index for store %s at %s (%d docs)", store_name, index_dir, count)
    except Exception as e:
        log.warning("Whoosh build for store %s failed: %s", store_name, e)


def build_index_entry_from_source(
    discovered,
    stored,
    tool_source,
    biotools_metadata_source=None,
):
    """Assemble a :class:`ToolIndexEntry` from a populator triple.

    ``discovered`` carries conf-level metadata that isn't visible to the tool
    source parser (section membership, ``labels="a,b"`` on the ``<tool>``
    element, conf-level ``hidden="true"``). ``stored`` carries the
    content-addressed hash and source class. ``tool_source`` is the parsed
    body — we read identity (id, version, name, description), EDAM
    operations / topics, ``require_login``, and ``tool_type`` off it.

    Returns ``None`` if the tool source does not yield a usable id; callers
    log + skip in that case.
    """
    try:
        tool_id = tool_source.parse_id() or stored.tool_id
        if not tool_id:
            return None

        uuid_val = None
        if hasattr(tool_source, "parse_uuid"):
            try:
                parsed_uuid = tool_source.parse_uuid()
                uuid_val = str(parsed_uuid) if parsed_uuid else None
            except Exception:
                pass

        # XML-body ``<tool hidden="true">`` from the parsed source OR
        # conf-level ``hidden="true"`` from the ``<tool>`` element — either
        # forces the entry hidden. Mirrors the eager pipeline's
        # ``_load_tool_tag_set`` ordering.
        body_hidden = False
        if hasattr(tool_source, "parse_hidden"):
            try:
                body_hidden = bool(tool_source.parse_hidden())
            except Exception:
                pass
        hidden = bool(body_hidden or discovered.hidden)

        require_login = False
        if hasattr(tool_source, "parse_require_login"):
            try:
                require_login = bool(tool_source.parse_require_login(False))
            except Exception:
                pass

        tool_type = "default"
        if hasattr(tool_source, "parse_tool_type"):
            try:
                tool_type = tool_source.parse_tool_type() or "default"
            except Exception:
                pass

        lowered = tool_id.lower()
        all_ids = [lowered]
        if "/repos/" in lowered:
            all_ids = [lowered, lowered.rsplit("/", 1)[0], lowered.rsplit("/", 2)[-2]]
        # Same ontology expansion as ``Tool.__init__`` — curated EDAM mapping
        # overrides and legacy bio.tools xrefs included.
        from galaxy.tool_util.ontologies.ontology_data import expand_ontology_data

        ontology_data = expand_ontology_data(tool_source, all_ids, biotools_metadata_source)
        edam_operations = list(ontology_data.edam_operations or ())
        edam_topics = list(ontology_data.edam_topics or ())
        xrefs: list[dict[str, Any]] = [dict(x) for x in ontology_data.xrefs or ()]

        icon = tool_source.parse_icon() if hasattr(tool_source, "parse_icon") else None

        # ``model_class`` / ``form_style`` mirror ``Tool.to_dict``'s ad-hoc
        # class inspection via the same tool_type registry the eager path
        # constructs tools with. Local import: galaxy.tools is the full tool
        # machinery; only the registry mapping is needed.
        from galaxy.tools import (
            DatabaseOperationTool,
            InteractiveTool,
            Tool,
            tool_types,
        )

        tool_class = tool_types.get(tool_type, Tool)
        regular_form = tool_class is Tool or issubclass(tool_class, (DatabaseOperationTool, InteractiveTool))

        # ``Tool.check_workflow_compatible`` equivalents derivable at parse
        # time: multi-page tools and data sources are incompatible; XML tools
        # may opt out via workflow_compatible="false" on the root.
        is_workflow_compatible = not tool_type.startswith("data_source")
        try:
            pages = tool_source.parse_input_pages()
            if pages is not None and len(pages.page_sources) > 1:
                is_workflow_compatible = False
        except Exception:
            pass
        root = getattr(tool_source, "root", None)
        if root is not None and str(root.get("workflow_compatible", "True")).lower() in ("false", "0", "no"):
            is_workflow_compatible = False

        # Honour the same version-default rules as ``Tool.__init__``: empty
        # ``version`` on a pre-16.04-profile tool becomes "1.0.0"; on newer
        # profiles it raises. Without this, ``ToolLineage.register_version``
        # crashes on ``Version(None)`` during the eager walk.
        try:
            version = parse_tool_version_with_defaults(tool_id, tool_source)
        except Exception as e:
            log.warning("parse_tool_version_with_defaults raised for %s: %s", tool_id, e)
            version = tool_source.parse_version() or "0"

        return ToolIndexEntry(
            id=tool_id,
            uuid=uuid_val,
            version=version,
            name=tool_source.parse_name() or "",
            description=tool_source.parse_description() or "",
            panel_section_id=discovered.section_id,
            panel_section_name=discovered.section_name,
            labels=list(discovered.labels or ()),
            icon=icon,
            xrefs=xrefs,
            model_class=tool_class.__name__,
            form_style="regular" if regular_form else "special",
            is_workflow_compatible=is_workflow_compatible,
            edam_operations=edam_operations,
            edam_topics=edam_topics,
            source_hash=stored.hash,
            source_class=stored.tool_source_class,
            source_path=stored.source_path,
            hidden=hidden,
            require_login=require_login,
            tool_type=tool_type,
            tags=[],
            indexed_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        log.warning(
            "Error building index entry (id=%s, hash=%s): %s",
            stored.tool_id,
            stored.hash,
            e,
        )
        return None


def _build_stores(config, sa_session) -> dict[str, Any]:
    """Build {store_name: store_instance} for the default + every named store
    referenced from any tool_conf."""
    stores: dict[str, ToolSourceStore] = {
        DEFAULT_STORE_NAME: _build_default_store(config, sa_session),
    }

    catalog = config.tool_source_stores or {}
    referenced: set[str] = set()
    for path in config.tool_configs or []:
        try:
            parser = get_toolbox_parser(path)
        except Exception as e:
            log.debug(f"skipping tool conf {path} during store discovery: {e}")
            continue
        name = parser.parse_store_name()
        if name:
            referenced.add(name)

    for name in referenced:
        if name not in catalog:
            raise RuntimeError(f"tool_conf references store {name!r} but no such entry in tool_source_stores")
        stores[name] = build_named_store(sa_session, name, catalog[name])

    return stores


def _build_conf_to_store_map(config) -> dict[str, str]:
    """Map each tool_conf path to its declared store name (default if absent)."""
    out: dict[str, str] = {}
    for path in config.tool_configs or []:
        try:
            parser = get_toolbox_parser(path)
        except Exception:
            out[path] = DEFAULT_STORE_NAME
            continue
        out[path] = parser.parse_store_name() or DEFAULT_STORE_NAME
    return out


def populate_store(
    config_file: str,
    dry_run: bool = False,
    incremental: bool = True,
    pattern: str | None = None,
    parallel: int = 4,
    verbose: bool = False,
    rebuild_index: bool = False,
    target: str | None = None,
) -> dict[str, int]:
    """CLI entry: load Galaxy config from disk, then delegate to
    :func:`populate_store_inline` for the actual work.

    ``rebuild_index`` is accepted for backwards compat but has no effect:
    the index is rebuilt on every non-dry-run.
    """
    log.info("Loading Galaxy configuration...")
    registry = Registry()
    registry.load_datatypes()
    set_datatypes_registry(registry)
    properties = load_app_properties(config_file=config_file, config_section="galaxy")
    config = GalaxyAppConfiguration(**properties)
    log.info(f"Connecting to database: {config.database_connection[:50]}...")
    model = init_models_from_config(config)
    return populate_store_inline(
        config,
        model.context,
        pattern=pattern,
        parallel=parallel,
        dry_run=dry_run,
        incremental=incremental,
        verbose=verbose,
        target=target,
    )


def populate_store_inline(
    config,
    sa_session,
    *,
    paths: list[str] | None = None,
    pattern: str | None = None,
    parallel: int = 1,
    dry_run: bool = False,
    incremental: bool = True,
    verbose: bool = False,
    rebuild_whoosh: bool = True,
    broadcast: bool = False,
    target: str | None = None,
    prune: bool = False,
) -> dict[str, int]:
    """In-process populator entry.

    Caller supplies an already-built ``GalaxyAppConfiguration`` and a
    SQLAlchemy session, so cold-start auto-populate (LazyToolBox boot path)
    and shed-install reroute (``tool_panel_manager``) don't pay the config-
    load cost a second time.

    ``parallel`` defaults to ``1`` so the in-process callers don't share
    ``sa_session`` across threads — ``DatabaseToolSourceStore.store()``
    writes through that session, and SQLAlchemy ``Session`` is not thread-
    safe. The CLI overrides via ``populate_store(config_file, parallel=...)``;
    it operates on its own fresh ``model.context`` with no concurrent
    readers and can safely fan out.

    ``paths`` semantics:

    - ``paths=None`` (default): full scan. Every discovered tool gets
      indexed; the index is **replaced** per writable store.
    - ``paths=[...]``: partial scan restricted to the listed paths. The
      existing index for each store is loaded, the entries for the matched
      paths are added/replaces, and the merged result is written back.
      Other entries are untouched.

    ``prune=True`` forces full-scan replacement even when ``paths`` is set,
    matching :func:`reconcile_index`.

    ``broadcast=True`` sends a ``reload_tool_source_cache`` control task
    after every store write succeeds, so peer Galaxy processes refresh
    their cached index. Shed-install and ``reset_shed_tools`` set this.
    """
    log.info(f"Building tool source stores (default backend: {config.tool_source_store})...")
    stores = _build_stores(config, sa_session)
    conf_to_store = _build_conf_to_store_map(config)

    if target is not None:
        if target not in stores:
            raise RuntimeError(f"--target {target!r} not found; available: {sorted(stores.keys())}")
        if stores[target].read_only:
            raise ReadOnlyStoreError(f"--target store {target!r} is read-only")

    writable_names = {n for n, s in stores.items() if not s.read_only}
    if target is not None:
        writable_names &= {target}
    skipped_read_only = [n for n, s in stores.items() if s.read_only]
    if skipped_read_only:
        log.info(f"Skipping read-only stores: {skipped_read_only}")
    log.info(f"Writable target stores: {sorted(writable_names)}")

    log.info("Discovering tools from configuration...")

    stats = {"processed": 0, "stored": 0, "skipped": 0, "errors": 0}

    discovered_tools = list(discover_tools(config, include_bundled=True))

    # Bundled tools have tool_conf="bundled"; those go to the default store.
    tool_specs: list[tuple[DiscoveredTool, str]] = []
    for d in discovered_tools:
        store_name = conf_to_store.get(d.tool_conf, DEFAULT_STORE_NAME)
        if store_name not in writable_names:
            # tool routed to a read-only store, or to a store not in --target.
            continue
        tool_specs.append((d, store_name))

    log.info(f"Found {len(discovered_tools)} tool files; routing {len(tool_specs)} to writable stores")

    if paths is not None:
        paths_set = {str(p) for p in paths}
        tool_specs = [(d, n) for d, n in tool_specs if d.path in paths_set]
        log.info(f"Restricted to {len(tool_specs)} tools matching {len(paths_set)} requested path(s)")

    if pattern:
        tool_specs = [(d, n) for d, n in tool_specs if pattern in d.path]
        log.info(f"Filtered to {len(tool_specs)} tools matching '{pattern}'")

    def process_tool(
        d: DiscoveredTool, store_name: str
    ) -> tuple[str, DiscoveredTool, str, StoredToolSource | None, Any | None, str | None]:
        """Process a single tool file with proper macro expansion.

        Returns ``(status, discovered, store_name, stored, tool_source, err)``.
        ``stored`` and ``tool_source`` are populated on ``stored`` and
        ``skipped`` so the post-walk index build can read them; ``error``
        carries the message in the last slot.
        """
        path = d.path
        try:
            # Galaxy's tool source parser handles macro expansion (XML) and
            # YAML user-tool / CWL parsing transparently; ``to_string`` then
            # serialises whatever the source class needs to round-trip.
            tool_source = get_tool_source(config_file=path)
            expanded_content = tool_source.to_string()
            content_hash = compute_hash(expanded_content)
            target_store = stores[store_name]

            stored = StoredToolSource(
                hash=content_hash,
                tool_source_class=type(tool_source).__name__,
                raw_source=expanded_content,
                tool_id=tool_source.parse_id(),
                tool_version=tool_source.parse_version(),
                tool_dir=str(Path(path).parent),
                source_path=str(path),
                stored_at=datetime.now(timezone.utc),
            )

            if incremental:
                # Skip only when this *path* is already stored with this
                # content. A bare content-hash check is wrong: distinct files
                # can expand to identical content, and skipping the second
                # one would leave its path unresolvable (the row keeps the
                # first writer's ``source_path``).
                prior = target_store.get_by_source_path(str(path))
                if prior is not None and prior.hash == content_hash:
                    return ("skipped", d, store_name, stored, tool_source, None)

            if not dry_run:
                target_store.store(stored)
                # Commit per tool so each write is a short transaction.
                # When the populator runs inside a Galaxy process (cold
                # start, shed install) the shared SQLAlchemy session is
                # under concurrent pressure from request handlers and the
                # queue worker; holding 484 inserts in one open transaction
                # is enough to push SQLite past its 5s busy timeout. The
                # CLI path takes the same hit but on its own model.context
                # with no concurrent readers, so the cost is invisible.
                target_store.commit()
            return ("stored", d, store_name, stored, tool_source, None)
        except Exception as e:
            log.error(f"Error processing {path}: {e}")
            return ("error", d, store_name, None, None, str(e))

    log.info(f"Processing {len(tool_specs)} tools with {parallel} workers...")

    # Collect (discovered, stored, tool_source) per writable store so the
    # post-walk pass can build a fresh ToolIndex from this run's discoveries.
    parsed_per_store: dict[str, list[tuple[DiscoveredTool, StoredToolSource, Any]]] = {
        name: [] for name in writable_names
    }

    with ThreadPoolExecutor(max_workers=parallel) as executor:
        futures = {executor.submit(process_tool, d, n): (d, n) for d, n in tool_specs}
        for future in as_completed(futures):
            status, discovered, store_name, stored, tool_source, err = future.result()

            if status == "error":
                stats["errors"] += 1
            elif status == "skipped":
                stats["skipped"] += 1
                if stored is not None and tool_source is not None:
                    parsed_per_store[store_name].append((discovered, stored, tool_source))
            else:
                stats["stored"] += 1
                if stored is not None and tool_source is not None:
                    parsed_per_store[store_name].append((discovered, stored, tool_source))

            stats["processed"] += 1

            if verbose or status == "error":
                log.info(f"{status}: {discovered.path}{' — ' + err if err else ''}")

    log.info(f"Population complete: {stats}")

    if not dry_run:
        # Build / update the ToolIndex per writable store from this run's
        # parsed sources. Section metadata and conf-level labels/hidden are
        # already on each entry (build_index_entry_from_source threads them
        # off DiscoveredTool) — this is the seam the prior LazyToolBox
        # post-walk syncs (_stamp_panel_sections_onto_index,
        # _sync_tool_mutations_to_index) replaced ad-hoc.
        full_scan = paths is None or prune
        # Local import: galaxy.tools.biotools executes the galaxy.tools
        # package; only the metadata-source factory is needed, once per run.
        from galaxy.tools.biotools import get_galaxy_biotools_metadata_source

        biotools_metadata_source = get_galaxy_biotools_metadata_source(config)
        for store_name in sorted(writable_names):
            triples = parsed_per_store[store_name]
            if full_scan:
                # Replace the index entirely from this run's discoveries.
                index = ToolIndex()
            else:
                # Partial update: load the existing index, then add/replace
                # entries for the paths we just rescanned. Anything else
                # stays as-is (use reconcile_index for full prune).
                index = stores[store_name].load_index() or ToolIndex()
            for d, stored, tool_source in triples:
                entry = build_index_entry_from_source(d, stored, tool_source, biotools_metadata_source)
                if entry is not None:
                    index.add_entry(entry)
            try:
                stores[store_name].store_index(index)
                stores[store_name].commit()
                log.info(
                    "Persisted ToolIndex for store %s (%d entries, mode=%s)",
                    store_name,
                    len(index.entries),
                    "full" if full_scan else "partial",
                )
            except Exception as e:
                log.warning("store_index for %s raised: %s", store_name, e)
                # The flush failed — the session is now in PendingRollback
                # state, which would surface to the very next caller as
                # SQLAlchemyError. Clear it so the rest of the boot path
                # (and the eventual test client) sees a clean session.
                if sa_session is not None:
                    try:
                        sa_session.rollback()
                    except Exception as rb_e:
                        log.debug("session.rollback after store_index failure raised: %s", rb_e)
                continue
            # Rebuild the whoosh search index from the persisted ToolIndex.
            # Single-writer principle: the toolbox stops re-building this in
            # the search hot path.
            if rebuild_whoosh:
                _build_whoosh_for_store(config, store_name, index)

        if broadcast:
            # Tell peer Galaxy processes to drop their cached index so the
            # next request reloads what we just wrote. ``send_reload_notification``
            # tolerates a missing AMQP config (logs WARN, returns False).
            send_reload_notification(config)

    return stats


def populate_for_paths(
    config,
    sa_session,
    paths: list[str],
    *,
    rebuild_whoosh: bool = True,
) -> dict[str, int]:
    """Partial-update populator entry for shed installs.

    Restricts the scan to ``paths`` (typically the freshly-written tool
    files of a newly-installed repository), adds/replaces their index
    entries, and broadcasts ``reload_tool_source_cache`` so peer Galaxy
    processes pick up the new tools.
    """
    return populate_store_inline(
        config,
        sa_session,
        paths=paths,
        rebuild_whoosh=rebuild_whoosh,
        broadcast=True,
    )


def reconcile_index(
    config,
    sa_session,
    *,
    rebuild_whoosh: bool = True,
) -> dict[str, int]:
    """Full prune-enabled scan; used by ``reset_shed_tools``.

    Walks every config-discovered tool and replaces the index per writable
    store with the result. Anything previously indexed that no longer has a
    matching ``<tool>`` entry in any conf is dropped. Broadcasts
    ``reload_tool_source_cache`` so peer processes drop their stale view.
    """
    return populate_store_inline(
        config,
        sa_session,
        paths=None,
        prune=True,
        rebuild_whoosh=rebuild_whoosh,
        broadcast=True,
    )


def watch_mode(
    config_file: str,
    use_polling: bool = False,
    debounce: float = 2.0,
    verbose: bool = False,
):
    """
    Run in watch mode, monitoring tool directories for changes.

    Args:
        config_file: Path to Galaxy configuration file.
        use_polling: Use polling observer (for network filesystems).
        debounce: Debounce time in seconds.
        verbose: Enable verbose logging.
    """
    log.info("Loading Galaxy configuration...")

    # Initialize datatypes registry (required for model)
    registry = Registry()
    registry.load_datatypes()
    set_datatypes_registry(registry)

    # Load app properties from config file, then create config object
    properties = load_app_properties(config_file=config_file, config_section="galaxy")
    config = GalaxyAppConfiguration(**properties)

    log.info(f"Connecting to database: {config.database_connection[:50]}...")

    # Initialize model from config
    model = init_models_from_config(config)

    log.info(f"Building tool source store (backend: {config.tool_source_store})...")

    store = build_tool_source_store(config, cast("galaxy_scoped_session", model.context))

    # Determine directories to watch from tool configurations
    tools_dirs_set: set[Path] = set()
    for discovered in discover_tools(config, include_bundled=True):
        tool_dir = Path(discovered.tool_path) if discovered.tool_path else None
        if tool_dir and tool_dir.exists():
            tools_dirs_set.add(tool_dir)

    tools_dirs = list(tools_dirs_set)

    if not tools_dirs:
        log.error("No tool directories found to watch")
        return 1

    log.info(f"Will watch {len(tools_dirs)} tool directories")

    watcher = ToolFileWatcher(
        config=config,
        store=store,
        sa_session=model.context,
        tools_dirs=tools_dirs,
        debounce_seconds=debounce,
        use_polling=use_polling,
        verbose=verbose,
    )

    # Handle shutdown signals
    def signal_handler(signum, frame):
        log.info(f"Received signal {signum}, shutting down...")
        watcher.shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if not watcher.start():
        return 1

    log.info("Watching for tool file changes. Press Ctrl+C to stop.")
    watcher.wait()

    return 0


def main():
    """CLI entry point. Invoked by ``scripts/tool_source/populate_store.py``."""
    parser = argparse.ArgumentParser(description="Populate tool source store from Galaxy toolbox")
    parser.add_argument("--config", "-c", required=True, help="Galaxy configuration file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be stored")
    parser.add_argument(
        "--incremental",
        action="store_true",
        default=True,
        help="Only store new/changed tools (default)",
    )
    parser.add_argument("--full", action="store_true", help="Force re-store all tools")
    parser.add_argument("--tool-id", help="Tool ID pattern filter")
    parser.add_argument("--parallel", "-j", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild index after population")
    parser.add_argument(
        "--target",
        help=(
            "Restrict population to a single named store from tool_source_stores "
            "(or '__default__' for the default). Without this, every writable "
            "store is populated."
        ),
    )
    parser.add_argument(
        "--watch", "-w", action="store_true", help="Watch for file changes and send reload notifications"
    )
    parser.add_argument(
        "--watch-polling", action="store_true", help="Use polling observer for watch mode (for network filesystems)"
    )
    parser.add_argument(
        "--debounce", type=float, default=2.0, help="Debounce time in seconds for watch mode (default: 2.0)"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.watch:
        sys.exit(
            watch_mode(
                config_file=args.config,
                use_polling=args.watch_polling,
                debounce=args.debounce,
                verbose=args.verbose,
            )
        )
    else:
        stats = populate_store(
            config_file=args.config,
            dry_run=args.dry_run,
            incremental=not args.full,
            pattern=args.tool_id,
            parallel=args.parallel,
            verbose=args.verbose,
            rebuild_index=args.rebuild_index,
            target=args.target,
        )

        sys.exit(1 if stats["errors"] > 0 else 0)
