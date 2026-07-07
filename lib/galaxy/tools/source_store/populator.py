"""
Tool source store populator.

Walks Galaxy's tool configuration files, parses each tool source, and writes
the canonical ``StoredToolSource`` + ``ToolIndex`` rows into every writable
tool source store. The populator is the single writer of the index and the
whoosh search index; store consumers are read-only.

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
import os
import signal
import sys
import threading
import time
import xml.etree.ElementTree as ET
from collections.abc import (
    Callable,
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
from typing import Any

from kombu import Connection
from kombu.pools import producers
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from galaxy.config import GalaxyAppConfiguration
from galaxy.queues import (
    control_queues_for_session,
    galaxy_exchange,
)
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.parser.interface import ToolSource
from galaxy.tool_util.parser.util import parse_tool_version_with_defaults
from galaxy.tool_util.toolbox.parser import get_toolbox_parser
from galaxy.tools.source_store.discover import (
    discover_tools,
    DiscoveredTool,
)
from galaxy.tools.source_store.factory import (
    _build_default_store,
    build_named_store,
    build_tool_source_store,
)
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.interface import (
    ReadOnlyStoreError,
    StoredToolSource,
    ToolSourceStore,
)
from galaxy.tools.source_store.search import (
    ToolSearchTuning,
    ToolWhooshIndex,
)
from galaxy.util.properties import load_app_properties
from galaxy.util.watcher import (
    EventHandler,
    get_observer_class,
    Watcher,
)

log = logging.getLogger(__name__)


def compute_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


def _cli_control_queues(config) -> list:
    """Active per-process control queues, read straight from the main Galaxy DB.

    The standalone populator CLI has no ``ApplicationStack``; on the kombu
    sqlalchemy transport a producer must declare every live consumer's queue
    or the message is silently dropped. Build the same routing table
    :func:`galaxy.queues.all_control_queues_for_declare` builds, from a bare
    session on ``config.database_connection``.
    """
    try:
        engine = create_engine(config.database_connection)
        try:
            with Session(engine) as session:
                return control_queues_for_session(session)
        finally:
            engine.dispose()
    except Exception as e:
        log.error("Could not build control-queue declare list: %s", e)
        return []


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
                declare=_cli_control_queues(config),
                retry=True,
                headers={"epoch": time.time()},
            )

        log.info("Sent reload_tool_source_cache notification to all Galaxy processes")
        return True

    except Exception as e:
        log.error(f"Failed to send reload notification: {e}")
        return False


class ToolFileWatcher:
    """Watches tool directories and updates the store as files change.

    Filesystem observation and change detection are delegated to
    :class:`galaxy.util.watcher.Watcher` (the plumbing the eager toolbox
    watchers use); this class only supplies the per-file callback that
    re-populates the store and notifies peer Galaxy processes. ``Watcher``
    already suppresses no-op events via an md5 re-check, so there is no
    per-batch timer — each changed ``.xml`` triggers one populate + notify.
    """

    def __init__(
        self,
        config,
        store,
        tools_dirs: list,
        use_polling: bool = False,
        verbose: bool = False,
        notify_callable: Callable[[Any], bool] | None = None,
    ):
        self.config = config
        self.store = store
        self.tools_dirs = tools_dirs
        self.verbose = verbose
        # Injected so tests can substitute a fake; default is the AMQP notifier.
        self._notify = notify_callable or send_reload_notification
        observer_class = get_observer_class(
            "watch_tool_sources",
            "polling" if use_polling else "auto",
            default="auto",
            monitor_what_str="tool sources",
        )
        self._watcher = Watcher(observer_class, EventHandler) if observer_class is not None else None
        self._shutdown_event = threading.Event()

    def start(self):
        """Start watching for file changes."""
        if self._watcher is None:
            raise Exception("watchdog is not installed; --watch mode requires it")
        for tools_dir in self.tools_dirs:
            if tools_dir and tools_dir.exists():
                log.info("Watching directory: %s", tools_dir)
                self._watcher.watch_directory(
                    str(tools_dir),
                    callback=self._on_change,
                    recursive=True,
                    require_extensions=[".xml"],
                )
        self._watcher.start()
        log.info("File watcher started")
        return True

    def _on_change(self, path: str) -> None:
        """``Watcher`` callback: re-populate a changed ``.xml``, notify on success.

        Tool files re-populate themselves; a changed macros file re-expands
        its sibling tools (both in :meth:`_process_tool_file`). Non-tool confs
        parse-and-skip there.
        """
        try:
            if self._process_tool_file(path):
                self._notify(self.config)
        except Exception as e:
            log.error("Error processing %s: %s", path, e)

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
        try:
            with open(path) as f:
                raw_content = f.read()
        except OSError as e:
            log.error(f"Could not read {path}: {e}")
            return False

        try:
            root = ET.fromstring(raw_content)
        except ET.ParseError as e:
            log.error(f"Could not parse {path}: {e}")
            return False

        if root.tag == "macros":
            # A macros file changed: the tools that ``<import>`` it are
            # unchanged on disk but their expanded content is now stale.
            return self._reprocess_macro_dependents(path)
        if root.tag != "tool":
            return False

        content_hash = compute_hash(raw_content)
        if self.store.exists(content_hash):
            if self.verbose:
                log.debug(f"Tool unchanged: {path}")
            return False

        # ``_on_change`` sends the reload notification when this returns True.
        populate_store_inline(self.config, paths=[path], rebuild_whoosh=True)
        log.info("Updated tool: %s", path)
        return True

    def _reprocess_macro_dependents(self, macro_path: str) -> bool:
        """Re-expand the tool files that import a changed macros file.

        The watcher can't know which tools ``<import>`` this macro without
        parsing them, so it conservatively re-populates every ``.xml``
        sibling in the macro's directory — the standard layout keeps a tool
        and its ``macros.xml`` together. Non-tool siblings parse-and-skip in
        the populator. Cross-directory macro imports aren't covered (a
        dev-loop limitation).
        """
        macro_dir = Path(macro_path).parent
        siblings = [str(p) for p in macro_dir.glob("*.xml") if str(p) != macro_path]
        if not siblings:
            return False
        populate_store_inline(self.config, paths=siblings, rebuild_whoosh=True)
        log.info("Macro change in %s — re-expanded %d sibling file(s)", macro_path, len(siblings))
        return True

    def wait(self):
        """Wait for shutdown signal."""
        self._shutdown_event.wait()

    def shutdown(self):
        """Stop the watcher."""
        log.info("Shutting down file watcher...")
        self._shutdown_event.set()
        if self._watcher is not None:
            self._watcher.shutdown()

        log.info("File watcher stopped")


DEFAULT_STORE_NAME = "__default__"

# Sub-directory under ``config.tool_search_index_dir`` where the default
# store's whoosh index lives.
_WHOOSH_DEFAULT_SUBDIR = "_store_default"


def whoosh_dir_for_store(tool_search_index_dir: str | None, store_name: str) -> str | None:
    """Resolve the on-disk whoosh dir for ``store_name``.

    Returns ``None`` if the config doesn't define ``tool_search_index_dir``
    (whoosh search is then disabled). The default store maps to a fixed
    sub-dir; named stores get their own sub-dir.
    """
    if not tool_search_index_dir:
        return None
    sub = _WHOOSH_DEFAULT_SUBDIR if store_name == DEFAULT_STORE_NAME else store_name
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
        log.error("Whoosh build for store %s failed: %s", store_name, e)


def build_index_entry_from_source(
    discovered: DiscoveredTool,
    stored: StoredToolSource,
    tool_source: ToolSource,
) -> ToolIndexEntry | None:
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
        # Shed conf entries carry the tool's guid; the index (like the eager
        # toolbox's ``_tools_by_id``) keys installed shed tools by guid, not
        # by the short id in the XML body.
        tool_id = discovered.guid or tool_source.parse_id() or stored.tool_id
        if not tool_id:
            return None

        uuid_val = None
        if hasattr(tool_source, "parse_uuid"):
            parsed_uuid = tool_source.parse_uuid()
            uuid_val = str(parsed_uuid) if parsed_uuid else None

        # XML-body ``<tool hidden="true">`` from the parsed source OR
        # conf-level ``hidden="true"`` from the ``<tool>`` element — either
        # forces the entry hidden. Mirrors the eager pipeline's
        # ``_load_tool_tag_set`` ordering.
        hidden = bool(tool_source.parse_hidden() or discovered.hidden)

        require_login = bool(tool_source.parse_require_login(False))

        tool_type = tool_source.parse_tool_type() or "default"

        edam_operations = list(tool_source.parse_edam_operations() or ())
        edam_topics = list(tool_source.parse_edam_topics() or ())

        # Honour the same version-default rules as ``Tool.__init__``: empty
        # ``version`` on a pre-16.04-profile tool becomes "1.0.0"; on newer
        # profiles it raises (the outer except drops the entry).
        version = parse_tool_version_with_defaults(tool_id, tool_source)

        return ToolIndexEntry(
            id=tool_id,
            uuid=uuid_val,
            version=version,
            name=tool_source.parse_name() or "",
            description=tool_source.parse_description() or "",
            panel_section_id=discovered.section_id,
            panel_section_name=discovered.section_name,
            labels=list(discovered.labels or ()),
            edam_operations=edam_operations,
            edam_topics=edam_topics,
            source_hash=stored.hash,
            source_class=stored.tool_source_class,
            hidden=hidden,
            require_login=require_login,
            tool_type=tool_type,
            tags=[],
            tool_shed=discovered.tool_shed,
            repository_name=discovered.repository_name,
            repository_owner=discovered.repository_owner,
            changeset_revision=discovered.installed_changeset_revision,
            is_local=discovered.guid is None,
            indexed_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        log.error(
            "Error building index entry (id=%s, hash=%s): %s",
            stored.tool_id,
            stored.hash,
            e,
        )
        return None


def _build_stores(config) -> dict[str, Any]:
    """Build {store_name: store_instance} for the default + every named store
    referenced from any tool_conf."""
    stores: dict[str, ToolSourceStore] = {
        DEFAULT_STORE_NAME: _build_default_store(config),
    }

    catalog = config.tool_source_stores or {}
    referenced: set[str] = set()
    for path in config.tool_configs or []:
        try:
            parser = get_toolbox_parser(path)
        except Exception as e:
            log.error(f"skipping tool conf {path} during store discovery: {e}")
            continue
        name = parser.parse_store_name()
        if name:
            referenced.add(name)

    for name in referenced:
        if name not in catalog:
            raise RuntimeError(f"tool_conf references store {name!r} but no such entry in tool_source_stores")
        stores[name] = build_named_store(name, catalog[name])

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
    properties = load_app_properties(config_file=config_file, config_section="galaxy")
    config = GalaxyAppConfiguration(**properties)
    return populate_store_inline(
        config,
        pattern=pattern,
        parallel=parallel,
        dry_run=dry_run,
        incremental=incremental,
        verbose=verbose,
        target=target,
    )


def populate_store_inline(
    config,
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
    path_guids: dict[str, str | None] | None = None,
) -> dict[str, int]:
    """In-process populator entry.

    Caller supplies an already-built ``GalaxyAppConfiguration``, so
    in-process callers don't pay the config-load cost a second time.

    ``parallel`` defaults to ``1`` for the in-process callers (a boot or
    install populates a handful of files); the CLI overrides via
    ``populate_store(config_file, parallel=...)`` for full-tree scans.

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
    log.info("Building tool source stores...")
    stores = _build_stores(config)
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
        # Requested paths the conf walk can't reach — a freshly cloned shed
        # repository whose conf entry isn't persisted yet (metadata
        # generation loads its tools first), or any other ad-hoc load.
        # Synthesize their DiscoveredTool so partial populates index them
        # before the conf catches up; the next conf-driven populate
        # overwrites these entries with full conf context.
        covered = {d.path for d, _ in tool_specs}
        if DEFAULT_STORE_NAME in writable_names:
            for p in sorted(paths_set - covered):
                if not Path(p).exists():
                    continue
                guid = (path_guids or {}).get(p)
                tool_specs.append(
                    (
                        DiscoveredTool(
                            path=p,
                            tool_conf="adhoc",
                            tool_path=None,
                            guid=guid,
                            is_shed_tool=guid is not None,
                        ),
                        DEFAULT_STORE_NAME,
                    )
                )
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
                # Shed tools are keyed by guid everywhere downstream: the
                # index entry, ``get_by_tool_id``, and the materialise path
                # (``_create_tool_from_stored_source`` passes a guid-shaped
                # ``tool_id`` to the Tool constructor).
                tool_id=d.guid or tool_source.parse_id(),
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
        # off DiscoveredTool).
        full_scan = paths is None or prune
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
                entry = build_index_entry_from_source(d, stored, tool_source)
                if entry is not None:
                    index.add_entry(entry)
            try:
                stores[store_name].store_index(index)
                log.info(
                    "Persisted ToolIndex for store %s (%d entries, mode=%s)",
                    store_name,
                    len(index.entries),
                    "full" if full_scan else "partial",
                )
            except Exception as e:
                log.error("store_index for %s raised: %s", store_name, e)
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
    paths: list[str],
    *,
    rebuild_whoosh: bool = True,
    path_guids: dict[str, str | None] | None = None,
) -> dict[str, int]:
    """Partial-update populator entry for shed installs.

    Restricts the scan to ``paths`` (typically the freshly-written tool
    files of a newly-installed repository), adds/replaces their index
    entries, and broadcasts ``reload_tool_source_cache`` so peer Galaxy
    processes pick up the new tools. ``path_guids`` supplies the guid for
    paths that no persisted conf covers yet (install-time metadata
    generation), so the ad-hoc entries are keyed like their eventual
    conf-driven replacements.
    """
    return populate_store_inline(
        config,
        paths=paths,
        rebuild_whoosh=rebuild_whoosh,
        broadcast=True,
        path_guids=path_guids,
    )


def reconcile_index(
    config,
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
        paths=None,
        prune=True,
        rebuild_whoosh=rebuild_whoosh,
        broadcast=True,
    )


def watch_mode(
    config_file: str,
    use_polling: bool = False,
    verbose: bool = False,
):
    """
    Run in watch mode, monitoring tool directories for changes.

    Args:
        config_file: Path to Galaxy configuration file.
        use_polling: Use polling observer (for network filesystems).
        verbose: Enable verbose logging.
    """
    log.info("Loading Galaxy configuration...")
    properties = load_app_properties(config_file=config_file, config_section="galaxy")
    config = GalaxyAppConfiguration(**properties)

    log.info("Building tool source store...")

    store = build_tool_source_store(config)

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
        tools_dirs=tools_dirs,
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
