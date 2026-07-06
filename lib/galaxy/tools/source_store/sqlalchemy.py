"""
SQLAlchemy-backed tool source store.

A self-contained store that owns its own engine + metadata, decoupled
from ``galaxy.model``. Works with any SQLAlchemy URL (sqlite, postgres,
mysql, …); the SQLite single-file path is the typical use case
(shippable on CVMFS) but nothing about the schema is sqlite-specific.
"""

import gzip
import json
import logging
import os
from collections.abc import Iterator
from datetime import datetime
from typing import (
    Any,
)

from sqlalchemy import (
    create_engine,
    LargeBinary,
    MetaData,
    select,
    String,
    Text,
)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    Session,
    sessionmaker,
)

from .index import (
    ToolIndex,
    ToolIndexEntry,
)
from .interface import (
    ReadOnlyStoreError,
    StoredToolSource,
    ToolSourceStore,
)

log = logging.getLogger(__name__)

# Independent SQLAlchemy metadata — a tool source bundle has nothing to
# do with the Galaxy ORM and must be openable without booting Galaxy.
_metadata = MetaData()


class _Base(DeclarativeBase):
    metadata = _metadata


class _ToolSourceRow(_Base):
    __tablename__ = "tool_source"

    # One row per source path; ``hash`` fingerprints the expanded content
    # and is non-unique — distinct files can expand to identical content
    # yet each path must resolve through ``get_by_source_path``.
    id: Mapped[int] = mapped_column(primary_key=True)
    hash: Mapped[str] = mapped_column(String(64), index=True)
    tool_source_class: Mapped[str] = mapped_column(String(64))
    raw_source: Mapped[str] = mapped_column(Text)
    tool_id: Mapped[str | None] = mapped_column(String(255), index=True)
    tool_version: Mapped[str | None] = mapped_column(String(64))
    tool_dir: Mapped[str | None] = mapped_column(Text)
    source_path: Mapped[str | None] = mapped_column(String(1024), index=True)
    stored_at: Mapped[datetime | None] = mapped_column()
    extra_metadata: Mapped[str | None] = mapped_column(Text)  # JSON


class _ToolIndexRow(_Base):
    __tablename__ = "tool_index"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(64), unique=True)
    data: Mapped[bytes] = mapped_column(LargeBinary)  # gzip-compressed JSON
    built_at: Mapped[datetime | None] = mapped_column()


class SqlAlchemyToolSourceStore(ToolSourceStore):
    """A tool source store backed by any SQLAlchemy-compatible database.

    Each instance owns a private engine + metadata, separate from the
    Galaxy ORM, so the schema travels with the data and the store is
    openable without booting Galaxy.

    Args:
        url: SQLAlchemy URL.
        read_only: If True, refuse all mutating operations with
            :class:`ReadOnlyStoreError`. This is enforced at the Python
            level only - make sure the connection user lacks write
            privileges if that matters. For SQLite connection-level
            read-only, use a URI such as
            ``sqlite:///file:/path/to/store.sqlite?mode=ro&uri=true``.
    """

    def __init__(
        self,
        url: str,
        read_only: bool = False,
    ) -> None:
        self.url = url
        self.read_only = read_only
        self._cached_index: ToolIndex | None = None

        self._ensure_sqlite_parent_directory(url)

        self._engine = create_engine(url, future=True)
        if not read_only and not self._is_remote_engine():
            # Only auto-create schema on local/file backends. For shared
            # databases the operator should manage migrations explicitly
            # to avoid surprises.
            _metadata.create_all(self._engine)
        elif not read_only:
            # Best-effort create_all on remote backends - harmless if
            # tables already exist.
            try:
                _metadata.create_all(self._engine)
            except Exception as e:
                log.warning(f"could not auto-create tool source tables on {self._engine.url.drivername!r}: {e}")
        self._Session = sessionmaker(bind=self._engine, future=True)

    def _is_remote_engine(self) -> bool:
        return self._engine.url.drivername.split("+")[0] not in {"sqlite"}

    def _ensure_sqlite_parent_directory(self, url: str) -> None:
        parsed_url = make_url(url)
        if parsed_url.drivername.split("+")[0] != "sqlite":
            return
        if str(parsed_url.query.get("uri", "")).lower() in {"true", "1", "yes"}:
            return
        database = parsed_url.database
        if not database or database == ":memory:":
            return
        os.makedirs(os.path.dirname(os.path.abspath(database)) or ".", exist_ok=True)

    # --- helpers --------------------------------------------------------

    def _session(self) -> Session:
        return self._Session()

    def _ensure_writable(self) -> None:
        if self.read_only:
            raise ReadOnlyStoreError(f"tool source store at {self.url} is read-only")

    # --- ToolSourceStore: per-source ops --------------------------------

    def store(self, tool_source: StoredToolSource) -> str:
        """Store a source; one row per ``source_path``, path-less sources
        deduplicate on content hash (see :class:`_ToolSourceRow`)."""
        self._ensure_writable()
        with self._session() as session:
            if tool_source.source_path:
                existing = (
                    session.execute(
                        select(_ToolSourceRow).where(_ToolSourceRow.source_path == tool_source.source_path).limit(1)
                    )
                    .scalars()
                    .first()
                )
                if existing is not None:
                    if existing.hash != tool_source.hash:
                        existing.hash = tool_source.hash
                        existing.tool_source_class = tool_source.tool_source_class
                        existing.raw_source = tool_source.raw_source
                        existing.tool_id = tool_source.tool_id
                        existing.tool_version = tool_source.tool_version
                        existing.tool_dir = tool_source.tool_dir
                        existing.stored_at = tool_source.stored_at
                        existing.extra_metadata = json.dumps(tool_source.metadata) if tool_source.metadata else None
                        session.commit()
                    return tool_source.hash
            else:
                existing = (
                    session.execute(select(_ToolSourceRow).where(_ToolSourceRow.hash == tool_source.hash).limit(1))
                    .scalars()
                    .first()
                )
                if existing is not None:
                    return tool_source.hash
            row = _ToolSourceRow(
                hash=tool_source.hash,
                tool_source_class=tool_source.tool_source_class,
                raw_source=tool_source.raw_source,
                tool_id=tool_source.tool_id,
                tool_version=tool_source.tool_version,
                tool_dir=tool_source.tool_dir,
                source_path=tool_source.source_path,
                stored_at=tool_source.stored_at,
                extra_metadata=json.dumps(tool_source.metadata) if tool_source.metadata else None,
            )
            session.add(row)
            session.commit()
        return tool_source.hash

    def get(self, hash: str) -> StoredToolSource | None:
        with self._session() as session:
            row = session.execute(select(_ToolSourceRow).where(_ToolSourceRow.hash == hash).limit(1)).scalars().first()
            if row is None:
                return None
            return self._row_to_stored(row)

    def exists(self, hash: str) -> bool:
        with self._session() as session:
            row = (
                session.execute(select(_ToolSourceRow.id).where(_ToolSourceRow.hash == hash).limit(1)).scalars().first()
            )
            return row is not None

    def delete(self, hash: str) -> bool:
        """Delete all rows carrying this hash (one per source path)."""
        self._ensure_writable()
        with self._session() as session:
            rows = session.execute(select(_ToolSourceRow).where(_ToolSourceRow.hash == hash)).scalars().all()
            if not rows:
                return False
            for row in rows:
                session.delete(row)
            session.commit()
        return True

    def list_all(self) -> Iterator[str]:
        # Materialize so the session can close before the caller iterates.
        with self._session() as session:
            hashes = [h for (h,) in session.execute(select(_ToolSourceRow.hash)).all()]
        yield from hashes

    def get_by_tool_id(self, tool_id: str, version: str | None = None) -> list[StoredToolSource]:
        with self._session() as session:
            stmt = select(_ToolSourceRow).where(_ToolSourceRow.tool_id == tool_id)
            if version is not None:
                stmt = stmt.where(_ToolSourceRow.tool_version == version)
            rows = session.execute(stmt).scalars().all()
            return [self._row_to_stored(r) for r in rows]

    def get_by_source_path(self, source_path: str) -> StoredToolSource | None:
        with self._session() as session:
            row = (
                session.execute(select(_ToolSourceRow).where(_ToolSourceRow.source_path == source_path).limit(1))
                .scalars()
                .first()
            )
            return self._row_to_stored(row) if row is not None else None

    def count(self) -> int:
        with self._session() as session:
            return session.query(_ToolSourceRow).count()

    def get_stats(self) -> dict[str, Any]:
        return {
            "count": self.count(),
            "backend": "sqlalchemy",
            "url": str(self._engine.url),
            "read_only": self.read_only,
        }

    # --- ToolSourceStore: index ops -------------------------------------

    def store_index(self, index: ToolIndex) -> None:
        self._ensure_writable()
        compressed = gzip.compress(json.dumps(index.to_dict()).encode("utf-8"))
        version = index.compute_version()
        with self._session() as session:
            # Singleton row, updated in place to avoid the unique-version race.
            row = session.execute(select(_ToolIndexRow).order_by(_ToolIndexRow.id)).scalar_one_or_none()
            if row is None:
                row = _ToolIndexRow(version=version, data=compressed, built_at=index.built_at)
                session.add(row)
            else:
                row.version = version
                row.data = compressed
                row.built_at = index.built_at
            session.commit()
        self._cached_index = index

    def load_index(self) -> ToolIndex | None:
        if self._cached_index is not None:
            return self._cached_index
        with self._session() as session:
            row = session.execute(select(_ToolIndexRow).order_by(_ToolIndexRow.id.desc())).scalar_one_or_none()
        if row is None or not row.data:
            return None
        try:
            payload = json.loads(gzip.decompress(row.data).decode("utf-8"))
            self._cached_index = ToolIndex.from_dict(payload)
            return self._cached_index
        except Exception as e:
            log.warning(f"Failed to decode tool index from store {self.url}: {e}")
            return None

    def update_index_entry(self, entry: ToolIndexEntry) -> None:
        self._ensure_writable()
        index = self.load_index() or ToolIndex()
        # add_entry keeps ``entries_by_version`` in step with ``entries``;
        # versioned lookups read the per-version map (see the database
        # backend's update_index_entry).
        index.add_entry(entry)
        index.invalidate_caches()
        if entry.panel_section_id:
            index.by_section.setdefault(entry.panel_section_id, [])
            if entry.id not in index.by_section[entry.panel_section_id]:
                index.by_section[entry.panel_section_id].append(entry.id)
        self.store_index(index)

    def invalidate_index_cache(self) -> None:
        self._cached_index = None

    # --- internals ------------------------------------------------------

    def _row_to_stored(self, row: _ToolSourceRow) -> StoredToolSource:
        metadata = json.loads(row.extra_metadata) if row.extra_metadata else {}
        return StoredToolSource(
            hash=row.hash,
            tool_source_class=row.tool_source_class,
            raw_source=row.raw_source,
            tool_id=row.tool_id,
            tool_version=row.tool_version,
            tool_dir=row.tool_dir,
            source_path=row.source_path,
            stored_at=row.stored_at,
            metadata=metadata,
        )
