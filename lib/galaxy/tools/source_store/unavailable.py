"""Read-only placeholder used when no published cohort is compatible."""

from collections.abc import Iterator
from typing import NoReturn

from .index import (
    ToolIndex,
    ToolIndexEntry,
)
from .interface import (
    ReadOnlyStoreError,
    StoredToolSource,
    ToolSourceStore,
)


class UnavailableToolSourceStore(ToolSourceStore):
    """An empty member that leaves its tool conf on the eager parse path."""

    read_only = True

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def _reject_write(self) -> NoReturn:
        raise ReadOnlyStoreError(self.reason)

    def store(self, tool_source: StoredToolSource) -> str:
        self._reject_write()

    def get(self, hash: str) -> StoredToolSource | None:
        return None

    def exists(self, hash: str) -> bool:
        return False

    def delete(self, hash: str) -> bool:
        self._reject_write()

    def list_all(self) -> Iterator[str]:
        return iter(())

    def get_by_tool_id(self, tool_id: str, version: str | None = None) -> list[StoredToolSource]:
        return []

    def get_by_source_path(self, source_path: str) -> StoredToolSource | None:
        return None

    def list_source_paths(self) -> set[str]:
        return set()

    def count(self) -> int:
        return 0

    def get_stats(self) -> dict:
        return {"backend": "unavailable", "count": 0, "reason": self.reason}

    def store_index(self, index: ToolIndex) -> None:
        self._reject_write()

    def load_index(self) -> ToolIndex | None:
        return None

    def update_index_entry(self, entry: ToolIndexEntry) -> None:
        self._reject_write()

    def index_is_fresh(self) -> bool:
        # Nothing local can populate this read-only member. Reporting it as
        # handled avoids re-running the writable populator on every boot;
        # absent entries still fall through to the eager tool parser.
        return True
