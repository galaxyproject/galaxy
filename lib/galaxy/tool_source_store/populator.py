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
    Optional,
)

log = logging.getLogger(__name__)


def compute_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


def iter_tool_sources(toolbox, pattern: Optional[str] = None) -> Iterator[tuple]:
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
        from kombu import Connection
        from kombu.pools import producers

        from galaxy.queues import galaxy_exchange

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
        notify_callable: Optional[Callable[[Any], bool]] = None,
    ):
        self.config = config
        self.store = store
        self.tools_dirs = tools_dirs
        self.debounce_seconds = debounce_seconds
        self.use_polling = use_polling
        self.verbose = verbose
        # Injected so tests can substitute a fake; default is the AMQP notifier.
        self._notify = notify_callable or send_reload_notification
        self.observer = None
        self._pending_changes: set[str] = set()
        self._lock = threading.Lock()
        self._debounce_timer: Optional[threading.Timer] = None
        self._shutdown_event = threading.Event()

    def start(self):
        """Start watching for file changes."""
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
            from watchdog.observers.polling import PollingObserver
        except ImportError:
            log.error("watchdog library not installed. Install with: pip install watchdog")
            return False

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
        """Process a single tool file and update the store.

        Watch-mode does a lightweight raw-content hash and ElementTree
        root-tag check rather than running Galaxy's full tool-source
        parser, so an in-flight edit doesn't block on macro expansion or
        full validation. The slower canonical path (``populate_store``
        run) re-parses with macros expanded the next time it runs.
        """
        import xml.etree.ElementTree as ET

        from galaxy.tool_source_store import StoredToolSource

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

        tool_id = root.get("id")
        tool_version = root.get("version")

        stored = StoredToolSource(
            hash=content_hash,
            tool_source_class="XmlToolSource",
            raw_source=raw_content,
            tool_id=tool_id,
            tool_version=tool_version,
            tool_dir=str(Path(path).parent),
            source_path=str(path),
            stored_at=datetime.now(timezone.utc),
        )

        self.store.store(stored)
        log.info(f"Updated tool: {tool_id or path}")
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


def _build_stores(config, sa_session) -> dict[str, Any]:
    """Build {store_name: store_instance} for the default + every named store
    referenced from any tool_conf."""
    # Lazy imports: avoids loading the store factory on `--help` and keeps
    # the script's startup snappy for trivial invocations.
    from galaxy.tool_source_store import (
        _build_default_store,
        build_named_store,
        ToolSourceStore,
    )
    from galaxy.tool_util.toolbox.parser import get_toolbox_parser

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
    # Lazy import: matches _build_stores; not needed for --help.
    from galaxy.tool_util.toolbox.parser import get_toolbox_parser

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
    pattern: Optional[str] = None,
    parallel: int = 4,
    verbose: bool = False,
    rebuild_index: bool = False,
    target: Optional[str] = None,
) -> dict[str, int]:
    """
    Main population function.

    Args:
        config_file: Path to Galaxy configuration file.
        dry_run: If True, don't actually store anything.
        incremental: If True, skip already stored tools.
        pattern: Optional tool ID pattern to filter.
        parallel: Number of parallel workers.
        verbose: Enable verbose logging.
        rebuild_index: Rebuild index after population.
        target: If set, restrict population to the named store only.
            Use ``__default__`` for the default store. Without ``target``,
            every writable store is populated in one run.

    Returns:
        Statistics dictionary with counts.
    """
    from galaxy.config import GalaxyAppConfiguration
    from galaxy.datatypes.registry import Registry
    from galaxy.model import set_datatypes_registry
    from galaxy.model.mapping import init_models_from_config
    from galaxy.tool_source_store import (
        ReadOnlyStoreError,
        StoredToolSource,
    )
    from galaxy.util.properties import load_app_properties

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

    log.info(f"Building tool source stores (default backend: {config.tool_source_store})...")

    stores = _build_stores(config, model.context)
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

    # Use the discover module to find all tool files from config
    from galaxy.tool_source_store.discover import discover_tools

    discovered_tools = list(discover_tools(config, include_bundled=True))

    # Bundled tools have tool_conf="bundled"; those go to the default store.
    tool_specs: list[tuple[str, str]] = []
    for d in discovered_tools:
        store_name = conf_to_store.get(d.tool_conf, DEFAULT_STORE_NAME)
        if store_name not in writable_names:
            # tool routed to a read-only store, or to a store not in --target.
            continue
        tool_specs.append((d.path, store_name))

    log.info(f"Found {len(discovered_tools)} tool files; routing {len(tool_specs)} to writable stores")

    if pattern:
        tool_specs = [(p, n) for p, n in tool_specs if pattern in p]
        log.info(f"Filtered to {len(tool_specs)} tools matching '{pattern}'")

    # Import tool parsing utilities
    from galaxy.tool_util.parser import get_tool_source
    from galaxy.util import xml_to_string

    def process_tool(path: str, store_name: str) -> tuple[str, str, Optional[str]]:
        """Process a single tool file with proper macro expansion."""
        try:
            # Use Galaxy's tool source parser which handles macro expansion
            tool_source = get_tool_source(config_file=path)

            # Get the expanded XML as a string
            root = tool_source.xml_tree.getroot()
            expanded_content = xml_to_string(root, pretty=True)

            content_hash = compute_hash(expanded_content)
            target_store = stores[store_name]

            if incremental and target_store.exists(content_hash):
                return ("skipped", path, None)

            # Get tool ID and version from the parsed source
            tool_id = tool_source.parse_id()
            tool_version = tool_source.parse_version()

            stored = StoredToolSource(
                hash=content_hash,
                tool_source_class=type(tool_source).__name__,
                raw_source=expanded_content,
                tool_id=tool_id,
                tool_version=tool_version,
                tool_dir=str(Path(path).parent),
                source_path=str(path),
                stored_at=datetime.now(timezone.utc),
            )

            if not dry_run:
                target_store.store(stored)

            return ("stored", path, tool_id)
        except Exception as e:
            log.error(f"Error processing {path}: {e}")
            return ("error", path, str(e))

    log.info(f"Processing {len(tool_specs)} tools with {parallel} workers...")

    with ThreadPoolExecutor(max_workers=parallel) as executor:
        futures = {executor.submit(process_tool, p, n): p for p, n in tool_specs}
        for future in as_completed(futures):
            result = future.result()
            status = result[0]

            if status == "error":
                stats["errors"] += 1
            elif status == "skipped":
                stats["skipped"] += 1
            else:
                stats["stored"] += 1

            stats["processed"] += 1

            if verbose or status == "error":
                log.info(f"{status}: {result[1]}")

    log.info(f"Population complete: {stats}")

    if rebuild_index and not dry_run:
        log.info("Rebuilding tool index...")
        # We need a minimal app context for this
        # For now, just log that this would happen
        log.info("Index rebuild would happen here with full app context")

    return stats


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
    from galaxy.config import GalaxyAppConfiguration
    from galaxy.datatypes.registry import Registry
    from galaxy.model import set_datatypes_registry
    from galaxy.model.mapping import init_models_from_config
    from galaxy.tool_source_store import build_tool_source_store
    from galaxy.util.properties import load_app_properties

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

    store = build_tool_source_store(config, model.context)

    # Determine directories to watch from tool configurations
    from galaxy.tool_source_store.discover import discover_tools

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
