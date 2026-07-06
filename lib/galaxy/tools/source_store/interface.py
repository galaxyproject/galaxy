"""Interfaces and exceptions for tool source storage backends."""

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
    from .index import (
        ToolIndex,
        ToolIndexEntry,
    )


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

        The populator records ``source_path`` for every stored entry so
        readers can resolve a config file to the already-parsed source
        without guessing through ``tool_id`` (which can collide across
        directories).

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

    def remove_index_entry(self, tool_id: str) -> None:
        """Remove a tool's entry from the persisted index.

        Counterpart of :meth:`update_index_entry` for uninstalls: a consumer
        pops the entry from its in-memory index, but the persisted singleton
        would hand it right back on the next cache invalidation unless the
        removal is written through.
        """
        index = self.load_index()
        if index is None:
            return
        removed = index.entries.pop(tool_id, None)
        removed_versions = index.entries_by_version.pop(tool_id, None)
        if removed is None and removed_versions is None:
            return
        for section_tool_ids in index.by_section.values():
            if tool_id in section_tool_ids:
                section_tool_ids.remove(tool_id)
        index.invalidate_caches()
        self.store_index(index)

    def invalidate_index_cache(self) -> None:  # noqa: B027 — intentional empty default
        """Drop any in-memory cached index so the next load_index() reads fresh.

        Backends override this when they cache; the default is a no-op.
        """

    def close(self) -> None:  # noqa: B027 — intentional empty default
        """Release any state the store is holding.

        Wired into ``GalaxyUniverseApplication.haltables`` so a Python-side
        ``app.shutdown()`` (e.g. the embedded ``IntegrationTestCase.restart()``
        path) clears references that would otherwise survive into the next
        boot. Default is a no-op; backends holding an engine or cache
        override, and the composite store propagates.
        """


class ConfigurationError(Exception):
    """Raised when there's a configuration error."""


class ReadOnlyStoreError(Exception):
    """Raised when a write is attempted against a read-only tool source store."""
