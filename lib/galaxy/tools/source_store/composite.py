"""
Composite tool source store.

Lets a single Galaxy process serve tools from multiple per-tool-conf
stores. Reads are tried in declared order (first hit wins), writes go to
a designated *default* store. Used to layer e.g. a CVMFS-resident
read-only sqlite bundle on top of the local writable store.

The composite is invisible to the rest of Galaxy: it implements the same
:class:`ToolSourceStore` interface, and ``LazyToolBox`` / the populator
keep working unchanged.
"""

import logging
from collections.abc import Iterator
from typing import (
    Any,
)

from . import (
    StoredToolSource,
    ToolSourceStore,
)
from .index import (
    ToolIndex,
    ToolIndexEntry,
)

log = logging.getLogger(__name__)


class CompositeToolSourceStore(ToolSourceStore):
    """A read-priority store that fans out across several backends.

    Args:
        members: Ordered list of ``(name, store)`` pairs consulted for
            reads in order. Earlier entries shadow later ones on id/hash
            collisions.
        default: The store that receives all writes. Must be present in
            ``members`` (its name is the value used for write routing).
            Must not be ``read_only``.
    """

    def __init__(
        self,
        members: list[tuple[str, ToolSourceStore]],
        default: str,
    ) -> None:
        if not members:
            raise ValueError("CompositeToolSourceStore requires at least one member")
        names = [n for n, _ in members]
        if default not in names:
            raise ValueError(f"default store {default!r} not in members {names!r}")
        self._members: list[tuple[str, ToolSourceStore]] = list(members)
        self._default_name = default
        self._default_store = dict(members)[default]
        if self._default_store.read_only:
            raise ValueError(f"default store {default!r} is read-only")
        # Composite as a whole is writable iff its default store is writable.
        self.read_only = False

    # --- write ops: always default ------------------------------------

    def store(self, tool_source: StoredToolSource) -> str:
        return self._default_store.store(tool_source)

    def delete(self, hash: str) -> bool:
        return self._default_store.delete(hash)

    def store_index(self, index: ToolIndex) -> None:
        self._default_store.store_index(index)

    def update_index_entry(self, entry: ToolIndexEntry) -> None:
        self._default_store.update_index_entry(entry)

    def remove_index_entry(self, tool_id: str) -> None:
        self._default_store.remove_index_entry(tool_id)

    # --- read ops: priority order --------------------------------------

    def get(self, hash: str) -> StoredToolSource | None:
        for _name, member in self._members:
            found = member.get(hash)
            if found is not None:
                return found
        return None

    def exists(self, hash: str) -> bool:
        return any(m.exists(hash) for _, m in self._members)

    def get_by_tool_id(self, tool_id: str, version: str | None = None) -> list[StoredToolSource]:
        # Union across members, deduped by hash, preserving member order.
        seen: set[str] = set()
        out: list[StoredToolSource] = []
        for _name, member in self._members:
            for src in member.get_by_tool_id(tool_id, version):
                if src.hash in seen:
                    continue
                seen.add(src.hash)
                out.append(src)
        return out

    def get_by_source_path(self, source_path: str) -> StoredToolSource | None:
        for _name, member in self._members:
            found = member.get_by_source_path(source_path)
            if found is not None:
                return found
        return None

    def list_all(self) -> Iterator[str]:
        seen: set[str] = set()
        for _name, member in self._members:
            for h in member.list_all():
                if h in seen:
                    continue
                seen.add(h)
                yield h

    def list_source_paths(self) -> set[str]:
        paths: set[str] = set()
        for _name, member in self._members:
            paths |= member.list_source_paths()
        return paths

    @property
    def members(self) -> list[tuple[str, ToolSourceStore]]:
        """The ``(name, store)`` pairs, in read-priority order."""
        return list(self._members)

    @property
    def read_only_member_names(self) -> set[str]:
        """Names of member stores no populator can write to.

        The boot coverage check treats paths routed to these differently:
        a miss there can never be healed by running the populator, so it
        must not trigger one.
        """
        return {name for name, member in self._members if member.read_only}

    def count(self) -> int:
        # Distinct hashes across the composite.
        return sum(1 for _ in self.list_all())

    def get_stats(self) -> dict[str, Any]:
        return {
            "backend": "composite",
            "count": self.count(),
            "default": self._default_name,
            "members": [{"name": name, **member.get_stats()} for name, member in self._members],
        }

    # --- index ---------------------------------------------------------

    def load_index(self) -> ToolIndex | None:
        merged = ToolIndex()
        any_loaded = False
        for name, member in self._members:
            try:
                idx = member.load_index()
            except Exception as e:
                log.warning(f"Failed to load index from store {name!r}: {e}")
                continue
            if idx is None:
                continue
            any_loaded = True
            for tool_id, entry in idx.entries.items():
                # Earlier members win on collision.
                if tool_id in merged.entries:
                    continue
                merged.entries[tool_id] = entry
            for section_id, ids in idx.by_section.items():
                bucket = merged.by_section.setdefault(section_id, [])
                for tid in ids:
                    if tid not in bucket:
                        bucket.append(tid)
            # Same collision rule per (tool id, section): earlier members'
            # placements win, later members append theirs after.
            seen_placements = {(item.tool_id, item.section_id) for item in merged.panel_items}
            for item in idx.panel_items:
                placement_key = (item.tool_id, item.section_id)
                if placement_key in seen_placements:
                    continue
                seen_placements.add(placement_key)
                merged.panel_items.append(item)
            for view_name, view in idx.panel_views.items():
                merged.panel_views.setdefault(view_name, view)
            if idx.built_at and (merged.built_at is None or idx.built_at > merged.built_at):
                merged.built_at = idx.built_at
        if not any_loaded:
            return None
        merged.version = merged.compute_version()
        return merged

    def invalidate_index_cache(self) -> None:
        for _name, member in self._members:
            member.invalidate_index_cache()

    def index_is_fresh(self) -> bool | None:
        """Aggregate the member verdicts.

        A stale *writable* member makes the composite stale — the populator
        can heal it, so report ``False`` and let boot run it. A read-only
        member is trusted whenever its index loads under the current schema
        (see the SQLAlchemy backend): ``False`` there means no loadable
        index at all, which can't be healed locally — warn and continue,
        the publisher owns repopulation. A member without a probe
        downgrades an otherwise-fresh verdict to ``None`` so the caller
        still runs its coverage scan.
        """
        verdict: bool | None = True
        for name, member in self._members:
            fresh = member.index_is_fresh()
            if fresh is False:
                if member.read_only:
                    log.warning(
                        "Read-only tool source store %r has no loadable index; "
                        "its tools will parse eagerly until it is repopulated upstream",
                        name,
                    )
                else:
                    return False
            elif fresh is None:
                verdict = None
        return verdict

    def commit(self) -> None:
        """Propagate commit() to every writable member store."""
        for _name, member in self._members:
            try:
                member.commit()
            except Exception as e:
                log.warning(f"Composite store commit failed for member '{_name}': {e}")

    def close(self) -> None:
        """Propagate close() to every member store."""
        for _name, member in self._members:
            try:
                member.close()
            except Exception as e:
                log.warning(f"Composite store close failed for member '{_name}': {e}")
