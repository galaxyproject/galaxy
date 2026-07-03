"""
Tool Source Store - Pluggable storage backends for Galaxy tool sources.

This module provides a configurable, pluggable tool source storage system
that enables storing and retrieving tool sources from multiple backends
(currently ``database`` and ``sqlalchemy``).
"""

import logging
from abc import (
    ABC,
    abstractmethod,
)
from collections.abc import Iterator
from dataclasses import (
    dataclass,
    field,
)
from datetime import datetime
from typing import (
    Optional,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from galaxy.config import GalaxyAppConfiguration
    from galaxy.model.scoped_session import galaxy_scoped_session

log = logging.getLogger(__name__)


@dataclass
class StoredToolSource:
    """Representation of a stored tool source."""

    hash: str  # Content hash (SHA256)
    tool_source_class: str  # XmlToolSource, YamlToolSource, etc.
    raw_source: str  # Serialized tool source string
    tool_id: str | None = None  # Tool ID if known
    tool_version: str | None = None  # Tool version if known
    tool_dir: str | None = None  # Original tool directory
    source_path: str | None = None  # Original file path (used as a lookup key)
    stored_at: datetime | None = None
    metadata: dict | None = field(default_factory=dict)


class ToolSourceStore(ABC):
    """Abstract base class for tool source storage backends."""

    # Backends that wrap a read-only target (e.g. CVMFS-resident sqlite)
    # set this to ``True`` so the populator and reload paths can skip them
    # cleanly instead of crashing on a write attempt.
    read_only: bool = False

    @abstractmethod
    def store(self, tool_source: StoredToolSource) -> str:
        """
        Store a tool source.

        Args:
            tool_source: The tool source to store.

        Returns:
            The storage key (hash).
        """

    @abstractmethod
    def get(self, hash: str) -> StoredToolSource | None:
        """
        Retrieve a tool source by hash.

        Args:
            hash: The content hash of the tool source.

        Returns:
            The stored tool source, or None if not found.
        """

    @abstractmethod
    def exists(self, hash: str) -> bool:
        """
        Check if a tool source exists.

        Args:
            hash: The content hash to check.

        Returns:
            True if the tool source exists.
        """

    @abstractmethod
    def delete(self, hash: str) -> bool:
        """
        Delete a tool source by hash.

        Args:
            hash: The content hash of the tool source to delete.

        Returns:
            True if deleted, False if not found.
        """

    @abstractmethod
    def list_all(self) -> Iterator[str]:
        """
        List all stored tool source hashes.

        Yields:
            Content hashes of all stored tool sources.
        """

    @abstractmethod
    def get_by_tool_id(self, tool_id: str, version: str | None = None) -> list[StoredToolSource]:
        """
        Get tool sources by tool ID and optional version.

        Args:
            tool_id: The tool ID to search for.
            version: Optional version filter.

        Returns:
            List of matching tool sources.
        """

    @abstractmethod
    def get_by_source_path(self, source_path: str) -> StoredToolSource | None:
        """
        Get the stored tool source for a given on-disk file path.

        The populator records ``source_path`` for every stored entry so the
        eager / lazy load paths can resolve a config file to the
        already-parsed source without guessing through ``tool_id`` (which can
        collide across directories or be macro-expanded after the regex shortcut).

        Args:
            source_path: Absolute path of the original tool config file.

        Returns:
            Matching stored source, or None if nothing was populated from that file.
        """

    @abstractmethod
    def count(self) -> int:
        """Return the total number of stored tool sources."""

    def get_stats(self) -> dict:
        """Return storage statistics."""
        return {"count": self.count()}

    # Index operations

    @abstractmethod
    def store_index(self, index: "ToolIndex") -> None:
        """
        Store the complete tool index.

        Args:
            index: The tool index to store.
        """

    @abstractmethod
    def load_index(self) -> Optional["ToolIndex"]:
        """
        Load the tool index.

        Returns:
            The tool index, or None if not found.
        """

    @abstractmethod
    def update_index_entry(self, entry: "ToolIndexEntry") -> None:
        """
        Update a single index entry.

        Args:
            entry: The index entry to update.
        """

    def invalidate_index_cache(self) -> None:  # noqa: B027 — intentional empty default
        """Drop any in-memory cached index so the next load_index() reads fresh.

        Backends override this when they cache; the default is a no-op.
        """

    def commit(self) -> None:  # noqa: B027 — intentional empty default
        """Commit any pending writes to durable storage.

        Backends that use a request-scoped session (``DatabaseToolSourceStore``)
        only ``flush()`` inside ``store()`` / ``store_index()`` — the surrounding
        session decides when to ``commit()``. The lazy toolbox bootstrap runs
        *outside* a request, so it must drive the commit itself or every
        bootstrap insert rolls back when the engine is disposed. File-backed
        stores (``SqlAlchemyToolSourceStore``) already commit per write and
        override this as a no-op; ``CompositeToolSourceStore`` propagates.
        """

    def close(self) -> None:  # noqa: B027 — intentional empty default
        """Release any state the store is holding.

        Wired into ``GalaxyUniverseApplication.haltables`` so a Python-side
        ``app.shutdown()`` (e.g. the embedded ``IntegrationTestCase.restart()``
        path) clears references that would otherwise survive into the next
        boot. Default is a no-op; ``DatabaseToolSourceStore`` and the
        composite store override.
        """


class ConfigurationError(Exception):
    """Raised when there's a configuration error."""


class ReadOnlyStoreError(Exception):
    """Raised when a write is attempted against a read-only tool source store."""


def _build_default_store(
    config: "GalaxyAppConfiguration",
    sa_session: Optional["galaxy_scoped_session"],
) -> ToolSourceStore:
    """Build the default store from top-level ``tool_source_*`` config."""
    backend = config.tool_source_store

    if backend == "database":
        from .database import DatabaseToolSourceStore

        if sa_session is None:
            raise ConfigurationError("'database' backend requires a SQLAlchemy session")
        return DatabaseToolSourceStore(sa_session)

    if backend in ("sqlalchemy", "sqlite"):
        from .sqlalchemy import SqlAlchemyToolSourceStore

        url = getattr(config, "tool_source_url", None)
        path = config.tool_source_disk_path
        if url:
            return SqlAlchemyToolSourceStore(url=url, read_only=False)
        if path:
            return SqlAlchemyToolSourceStore(path=path, read_only=False)
        raise ConfigurationError(f"{backend!r} backend requires tool_source_url or tool_source_disk_path")

    raise ConfigurationError(f"Unknown tool source store backend: {backend}")


def build_named_store(
    sa_session: Optional["galaxy_scoped_session"],
    name: str,
    spec: dict,
) -> ToolSourceStore:
    """Build a single named store from a ``tool_source_stores`` entry.

    ``spec`` is the dict from galaxy.yml — a ``backend`` plus its options
    plus an optional ``read_only`` flag. ``sa_session`` is only used for
    the (unusual) ``database`` backend.
    """
    if not isinstance(spec, dict):
        raise ConfigurationError(f"tool_source_stores[{name!r}] must be a mapping")
    backend = spec.get("backend")
    read_only = bool(spec.get("read_only", False))

    if backend in ("sqlalchemy", "sqlite"):
        from .sqlalchemy import SqlAlchemyToolSourceStore

        url = spec.get("url")
        path = spec.get("path")
        if not url and not path:
            raise ConfigurationError(f"tool_source_stores[{name!r}] requires a 'url' or 'path'")
        return SqlAlchemyToolSourceStore(url=url, path=path, read_only=read_only)

    if backend == "database":
        from .database import DatabaseToolSourceStore

        if sa_session is None:
            raise ConfigurationError(
                f"tool_source_stores[{name!r}] uses the 'database' backend which requires a SQLAlchemy session"
            )
        store = DatabaseToolSourceStore(sa_session)
        store.read_only = read_only
        return store

    raise ConfigurationError(f"tool_source_stores[{name!r}] has unknown backend {backend!r}")


def _collect_per_conf_store_names(config: "GalaxyAppConfiguration") -> set[str]:
    """Walk configured tool_confs and collect referenced store names."""
    if not config.tool_configs:
        return set()
    # Lazy import: avoids pulling parser code into deploys that don't need it.
    from galaxy.tool_util.toolbox.parser import get_toolbox_parser

    names: set[str] = set()
    for path in config.tool_configs:
        try:
            parser = get_toolbox_parser(path)
        except Exception as e:
            log.debug(f"skipping tool conf {path}: {e}")
            continue
        store = parser.parse_store_name()
        if store:
            names.add(store)
    return names


def build_tool_source_store(
    config: "GalaxyAppConfiguration",
    sa_session: Optional["galaxy_scoped_session"],
) -> ToolSourceStore:
    """Build the active tool source store, composing per-conf overrides.

    Returns the default store directly when no tool_conf opts into a named
    override (zero overhead for the common case). Otherwise wraps the
    default plus each referenced named store in a
    :class:`CompositeToolSourceStore`, with the default consulted last and
    receiving all writes.

    Args:
        config: The Galaxy application configuration.
        sa_session: Galaxy's scoped SQLAlchemy session, used by the
            ``database`` backend. Other backends ignore it.
    """
    default_store = _build_default_store(config, sa_session)

    # Per-conf store="..." attributes are only meaningful when the LazyToolBox
    # is the active toolbox. Opting in is explicit: anything other than
    # ``use_lazy_toolbox: true`` keeps the traditional ToolBox, in which case
    # nothing would query the named store. Treat such attributes as no-ops
    # rather than failing on a catalog mismatch or doing wasted I/O.
    if not config.use_lazy_toolbox:
        referenced = _collect_per_conf_store_names(config)
        if referenced:
            log.info(
                "use_lazy_toolbox is not enabled; ignoring store=... attributes "
                f"from tool_confs (referenced: {sorted(referenced)})"
            )
        return default_store

    referenced = _collect_per_conf_store_names(config)
    if not referenced:
        return default_store

    catalog = config.tool_source_stores or {}
    members: list[tuple[str, ToolSourceStore]] = []
    for name in referenced:
        if name not in catalog:
            raise ConfigurationError(
                f"tool_conf references store {name!r} but no such entry exists in tool_source_stores"
            )
        members.append((name, build_named_store(sa_session, name, catalog[name])))

    # Default is consulted last so per-conf overrides shadow it on hash collisions.
    members.append(("__default__", default_store))

    # Lazy import to avoid composite always being pulled in.
    from .composite import CompositeToolSourceStore

    return CompositeToolSourceStore(members=members, default="__default__")


# Re-export key classes — placed after the abstract base above to avoid circular
# imports between this module and ``index.py``/``database.py``.
from .index import (  # noqa: E402
    ToolIndex,
    ToolIndexEntry,
)

__all__ = [
    "StoredToolSource",
    "ToolSourceStore",
    "ToolIndex",
    "ToolIndexEntry",
    "build_tool_source_store",
    "build_named_store",
    "ConfigurationError",
    "ReadOnlyStoreError",
]
