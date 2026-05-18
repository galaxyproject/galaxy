"""
Database backend for Tool Source Store.

This module provides a database-backed implementation of the ToolSourceStore
that uses the existing tool_source table and adds a tool_index table for
lightweight metadata.
"""

import gzip
import json
import logging
from collections.abc import Iterator
from datetime import datetime
from typing import (
    cast,
    Optional,
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import Session

from galaxy.model import (
    ToolIndexCache,
    ToolSource as ToolSourceModel,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from . import (
    StoredToolSource,
    ToolSourceStore,
)
from .index import (
    ToolIndex,
    ToolIndexEntry,
)

log = logging.getLogger(__name__)


class DatabaseToolSourceStore(ToolSourceStore):
    """
    Database-backed tool source store.

    Uses the existing tool_source table for storing full tool sources
    and a separate tool_index table for lightweight metadata.
    """

    def __init__(self, sa_session: galaxy_scoped_session):
        """
        Initialize the database tool source store.

        Args:
            sa_session: Galaxy's scoped SQLAlchemy session (``app.model.context``).
        """
        self._sa_session = sa_session
        self._cached_index: Optional[ToolIndex] = None

    def _get_session(self) -> Session:
        """Get a database session."""
        return cast(Session, self._sa_session)

    def store(self, tool_source: StoredToolSource) -> str:
        """Store a tool source in the database."""
        session = self._get_session()

        # Check if already exists
        existing = session.execute(
            select(ToolSourceModel).where(ToolSourceModel.hash == tool_source.hash)
        ).scalar_one_or_none()

        if existing:
            return tool_source.hash

        # Create new record
        source_data = {
            "raw": tool_source.raw_source,
            "tool_source_class": tool_source.tool_source_class,
            "tool_id": tool_source.tool_id,
            "tool_version": tool_source.tool_version,
            "tool_dir": tool_source.tool_dir,
            "stored_at": (tool_source.stored_at.isoformat() if tool_source.stored_at else None),
            "metadata": tool_source.metadata,
        }

        model = ToolSourceModel(
            hash=tool_source.hash,
            source=source_data,
            source_class=tool_source.tool_source_class,
        )
        session.add(model)
        session.flush()

        return tool_source.hash

    def get(self, hash: str) -> Optional[StoredToolSource]:
        """Retrieve a tool source by hash."""
        session = self._get_session()

        model = session.execute(select(ToolSourceModel).where(ToolSourceModel.hash == hash)).scalar_one_or_none()

        if not model:
            return None

        return self._model_to_stored(model)

    def _model_to_stored(self, model: ToolSourceModel) -> StoredToolSource:
        """Convert database model to StoredToolSource."""
        source_data = model.source or {}

        stored_at = source_data.get("stored_at")
        if stored_at and isinstance(stored_at, str):
            stored_at = datetime.fromisoformat(stored_at)

        assert model.hash is not None
        return StoredToolSource(
            hash=model.hash,
            tool_source_class=source_data.get("tool_source_class", "XmlToolSource"),
            raw_source=source_data.get("raw", ""),
            tool_id=source_data.get("tool_id"),
            tool_version=source_data.get("tool_version"),
            tool_dir=source_data.get("tool_dir"),
            stored_at=stored_at,
            metadata=source_data.get("metadata", {}),
        )

    def exists(self, hash: str) -> bool:
        """Check if a tool source exists."""
        session = self._get_session()

        result = session.execute(select(ToolSourceModel.id).where(ToolSourceModel.hash == hash)).scalar_one_or_none()

        return result is not None

    def delete(self, hash: str) -> bool:
        """Delete a tool source by hash."""
        session = self._get_session()

        model = session.execute(select(ToolSourceModel).where(ToolSourceModel.hash == hash)).scalar_one_or_none()

        if not model:
            return False

        session.delete(model)
        session.flush()
        return True

    def list_all(self) -> Iterator[str]:
        """List all stored tool source hashes."""
        session = self._get_session()

        result = session.execute(select(ToolSourceModel.hash))

        for (hash_value,) in result:
            if hash_value:
                yield hash_value

    def get_by_tool_id(self, tool_id: str, version: Optional[str] = None) -> list[StoredToolSource]:
        """Get tool sources by tool ID and optional version."""
        session = self._get_session()

        # Query all and filter in Python since tool_id is in JSON
        result = session.execute(select(ToolSourceModel))
        sources = []

        for (model,) in result:
            source_data = model.source or {}
            if source_data.get("tool_id") == tool_id:
                if version is None or source_data.get("tool_version") == version:
                    sources.append(self._model_to_stored(model))

        return sources

    def count(self) -> int:
        """Return the total number of stored tool sources."""
        session = self._get_session()
        result = session.execute(select(func.count(ToolSourceModel.id)))
        return result.scalar() or 0

    def get_stats(self) -> dict:
        """Return storage statistics."""
        return {
            "count": self.count(),
            "backend": "database",
        }

    # Index operations

    def store_index(self, index: ToolIndex) -> None:
        """
        Store the complete tool index.

        Stores the index as a gzip-compressed JSON blob in the tool_index table.
        Uses versioning for cache invalidation.
        """
        session = self._get_session()

        # Serialize and compress index
        index_data = index.to_dict()
        json_bytes = json.dumps(index_data).encode("utf-8")
        compressed = gzip.compress(json_bytes)

        version = index.compute_version()

        # Singleton-style upsert: keep at most one row, identified by version. We
        # update an existing row in place rather than DELETE+INSERT to avoid a
        # window where the unique-version constraint can be violated by a
        # concurrent writer.
        model = session.execute(select(ToolIndexCache).order_by(ToolIndexCache.id)).scalar_one_or_none()
        if model is None:
            model = ToolIndexCache(
                version=version,
                data=compressed,
                built_at=index.built_at,
            )
            session.add(model)
        else:
            model.version = version
            model.data = compressed
            model.built_at = index.built_at

        session.flush()
        self._cached_index = index

    def load_index(self) -> Optional[ToolIndex]:
        """Load the tool index from the tool_index table.

        ``select`` on the shared scoped session implicitly opens a read
        transaction. Boot and ``reload_toolbox`` paths call this from
        threads (queue worker, embedded test driver) that don't bound
        their work to a request lifecycle, so nothing later closes that
        transaction — on SQLite (integration tests) the open transaction
        retains a lock on the model database, on Postgres (CI) it
        accumulates idle-in-transaction rows that block subsequent
        DELETE/UPDATE for the entire test run. ``rollback()`` after a
        pure read is a no-op for data but closes the transaction.
        """
        if self._cached_index is not None:
            return self._cached_index

        session = self._get_session()

        try:
            # Try to load from new tool_index table first
            model = session.execute(select(ToolIndexCache).order_by(ToolIndexCache.id.desc())).scalar_one_or_none()

            if model and model.data:
                try:
                    json_bytes = gzip.decompress(model.data)
                    index_data = json.loads(json_bytes.decode("utf-8"))
                    self._cached_index = ToolIndex.from_dict(index_data)
                    return self._cached_index
                except Exception as e:
                    log.warning(f"Failed to load index from tool_index table: {e}")

            # Fall back to legacy storage in tool_source table
            legacy = session.execute(
                select(ToolSourceModel).where(ToolSourceModel.hash == "__tool_index__")
            ).scalar_one_or_none()

            if legacy:
                source_data = legacy.source or {}
                index_data = source_data.get("index")
                if index_data:
                    self._cached_index = ToolIndex.from_dict(index_data)
                    return self._cached_index

            return None
        finally:
            # Release the implicit read transaction so other writers
            # don't block on it. Safe because we haven't added/modified
            # anything in the session.
            try:
                session.rollback()
            except Exception as e:
                log.debug(f"load_index rollback raised: {e}")

    def update_index_entry(self, entry: ToolIndexEntry) -> None:
        """Update a single index entry."""
        index = self.load_index()
        if index is None:
            index = ToolIndex()

        index.entries[entry.id] = entry
        index.invalidate_caches()

        # Update section mapping
        if entry.panel_section_id:
            if entry.panel_section_id not in index.by_section:
                index.by_section[entry.panel_section_id] = []
            if entry.id not in index.by_section[entry.panel_section_id]:
                index.by_section[entry.panel_section_id].append(entry.id)

        self.store_index(index)

    def invalidate_index_cache(self) -> None:
        """Invalidate the cached index."""
        self._cached_index = None

    def commit(self) -> None:
        """Commit pending writes on the shared scoped session."""
        if self._sa_session is not None:
            try:
                self._sa_session.commit()
            except Exception as e:
                log.warning(f"DatabaseToolSourceStore.commit raised: {e}")

    def close(self) -> None:
        """Commit pending writes and drop in-memory state at app shutdown.

        ``store`` and ``store_index`` only ``flush()`` — they don't
        ``commit()`` (so Galaxy's request-scoped session stays in
        control of when its work lands on disk). On
        ``IntegrationTestCase.restart()`` the prior Galaxy then disposes
        its engine via ``_shutdown_model``, which forcibly closes
        in-flight transactions; psycopg's abort path rolls them back.
        Result: every shed-installed tool / bootstrapped index entry
        the prior Galaxy wrote is gone when the next Galaxy starts —
        the next boot sees an empty store and re-bootstraps from
        configs (484 tool sources × XML parse + DB insert).

        On CI the second bootstrap consistently stalls a few seconds in
        and never completes, hanging the test (``test_recovery``'s
        post-restart Galaxy is the most obvious victim — its first
        Galaxy bootstrapped fine, the second got stuck part-way through
        ``discover_tools``).

        Commit on close so the next embedded Galaxy sees the
        already-bootstrapped index and skips the second bootstrap
        entirely. Outside the test driver this is a no-op for the
        common case (production Galaxy doesn't restart in-process).
        """
        if self._sa_session is not None:
            try:
                self._sa_session.commit()
            except Exception as e:
                log.debug(f"DatabaseToolSourceStore.close commit raised: {e}")
        self._cached_index = None
        # Don't null out the session — it's a scoped session shared with
        # the rest of Galaxy. Just stop holding a strong reference to the
        # cached index.
