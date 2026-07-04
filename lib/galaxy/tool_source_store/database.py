"""
Database backend for Tool Source Store.

This module provides a database-backed implementation of the ToolSourceStore
backed by the store-owned ``tool_source_record`` table (content-addressed
sources) and the ``tool_index`` table (serialized ToolIndex). The unrelated
``tool_source`` table belongs to the job-request path and is never touched.
"""

import gzip
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import (
    cast,
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import Session

from galaxy.model import (
    ToolIndexCache,
    ToolSourceRecord,
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

    Uses the ``tool_source_record`` table for full tool sources and the
    ``tool_index`` table for the serialized index.
    """

    def __init__(self, sa_session: galaxy_scoped_session):
        """
        Initialize the database tool source store.

        Args:
            sa_session: Galaxy's scoped SQLAlchemy session (``app.model.context``).
        """
        self._sa_session = sa_session
        self._cached_index: ToolIndex | None = None

    def _get_session(self) -> Session:
        """Get the shared scoped session — used for writes that must commit
        in the caller's context (request, queue worker, populator)."""
        return cast(Session, self._sa_session)

    @contextmanager
    def _read_session(self) -> Iterator[Session]:
        """Yield a private Session for reads.

        Reads must not run on the shared scoped session: this code can
        be called mid-request (``LazyTool`` materialise during workflow
        ``inject_all``), and the ``rollback()`` we issue afterwards to
        release the implicit read transaction would expire the caller's
        request-scoped objects (e.g. ``workflow.steps``). A private
        ``Session`` bound to the same engine sees the same committed
        data but its lifecycle is isolated from the caller's.
        """
        bind = self._sa_session.get_bind()
        session = Session(bind=bind, autoflush=False, expire_on_commit=False)
        try:
            yield session
        finally:
            try:
                session.close()
            except Exception as e:
                log.debug("read session close raised: %s", e)

    def store(self, tool_source: StoredToolSource) -> str:
        """Store a tool source in the database.

        One row per ``source_path``: distinct files can expand to identical
        content (same ``hash``), and each path must stay resolvable through
        :meth:`get_by_source_path` — deduplicating on hash alone would leave
        the second file's path pointing at nothing. A row whose path already
        exists is updated in place when its content changed. Path-less
        sources deduplicate on content hash.
        """
        session = self._get_session()

        if tool_source.source_path:
            existing = (
                session.execute(
                    select(ToolSourceRecord).where(ToolSourceRecord.source_path == tool_source.source_path).limit(1)
                )
                .scalars()
                .first()
            )
            if existing is not None:
                if existing.hash != tool_source.hash:
                    existing.hash = tool_source.hash
                    existing.source = tool_source.raw_source
                    existing.source_class = tool_source.tool_source_class
                    existing.tool_id = tool_source.tool_id
                    existing.tool_version = tool_source.tool_version
                    existing.tool_dir = tool_source.tool_dir
                    existing.stored_at = tool_source.stored_at
                    existing.source_metadata = tool_source.metadata or None
                    session.flush()
                return tool_source.hash
        else:
            existing_id = (
                session.execute(select(ToolSourceRecord.id).where(ToolSourceRecord.hash == tool_source.hash).limit(1))
                .scalars()
                .first()
            )
            if existing_id:
                return tool_source.hash

        model = ToolSourceRecord(
            hash=tool_source.hash,
            source=tool_source.raw_source,
            source_class=tool_source.tool_source_class,
            tool_id=tool_source.tool_id,
            tool_version=tool_source.tool_version,
            tool_dir=tool_source.tool_dir,
            source_path=tool_source.source_path,
            stored_at=tool_source.stored_at,
            source_metadata=tool_source.metadata or None,
        )
        session.add(model)
        session.flush()

        return tool_source.hash

    def get(self, hash: str) -> StoredToolSource | None:
        """Retrieve a tool source by hash.

        Several rows can share a hash (one per source path with identical
        expanded content); any of them carries the same source.
        """
        with self._read_session() as session:
            model = (
                session.execute(select(ToolSourceRecord).where(ToolSourceRecord.hash == hash).limit(1))
                .scalars()
                .first()
            )
            if not model:
                return None
            return self._model_to_stored(model)

    def _model_to_stored(self, model: ToolSourceRecord) -> StoredToolSource:
        """Convert database model to StoredToolSource."""
        return StoredToolSource(
            hash=model.hash,
            tool_source_class=model.source_class or "XmlToolSource",
            raw_source=model.source or "",
            tool_id=model.tool_id,
            tool_version=model.tool_version,
            tool_dir=model.tool_dir,
            source_path=model.source_path,
            stored_at=model.stored_at,
            metadata=model.source_metadata or {},
        )

    def exists(self, hash: str) -> bool:
        """Check if a tool source exists."""
        with self._read_session() as session:
            result = (
                session.execute(select(ToolSourceRecord.id).where(ToolSourceRecord.hash == hash).limit(1))
                .scalars()
                .first()
            )
            return result is not None

    def delete(self, hash: str) -> bool:
        """Delete all rows carrying this hash (one per source path)."""
        session = self._get_session()

        models = session.execute(select(ToolSourceRecord).where(ToolSourceRecord.hash == hash)).scalars().all()

        if not models:
            return False

        for model in models:
            session.delete(model)
        session.flush()
        return True

    def list_all(self) -> Iterator[str]:
        """List all stored tool source hashes."""
        # Materialise eagerly so the private session can close before we
        # yield — otherwise an outer caller could keep the session open
        # indefinitely while iterating.
        with self._read_session() as session:
            result = session.execute(select(ToolSourceRecord.hash)).all()
        for (hash_value,) in result:
            if hash_value:
                yield hash_value

    def get_by_tool_id(self, tool_id: str, version: str | None = None) -> list[StoredToolSource]:
        """Get tool sources by tool ID and optional version."""
        with self._read_session() as session:
            stmt = select(ToolSourceRecord).where(ToolSourceRecord.tool_id == tool_id)
            if version is not None:
                stmt = stmt.where(ToolSourceRecord.tool_version == version)
            return [self._model_to_stored(model) for model in session.scalars(stmt)]

    def get_by_source_path(self, source_path: str) -> StoredToolSource | None:
        """Get the stored source for a given on-disk file path.

        The populator writes one entry per file, so there is at most one match.
        """
        with self._read_session() as session:
            model = session.execute(
                select(ToolSourceRecord).where(ToolSourceRecord.source_path == source_path).limit(1)
            ).scalar_one_or_none()
            if not model:
                return None
            return self._model_to_stored(model)

    def count(self) -> int:
        """Return the total number of stored tool sources."""
        with self._read_session() as session:
            result = session.execute(select(func.count(ToolSourceRecord.id)))
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

    def load_index(self) -> ToolIndex | None:
        """Load the tool index from the tool_index table.

        Uses a private session so the implicit read transaction is
        scoped to this call — the shared scoped session (which may be
        request-bound or driving the cold-start populator) keeps its
        own transaction state.
        """
        if self._cached_index is not None:
            return self._cached_index

        with self._read_session() as session:
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

            return None

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
