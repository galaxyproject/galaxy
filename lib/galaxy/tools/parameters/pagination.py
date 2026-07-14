"""Helpers shared by data/data_collection tool parameters when paginating
their option lists in ``to_dict``.
"""

from collections.abc import (
    Callable,
    Mapping,
)
from typing import (
    Any,
    TypeVar,
)

DEFAULT_OPTIONS_PAGE_SIZE = 50
MAX_OPTIONS_PAGE_SIZE = 500

#: Pagination spec for a single parameter, keyed by source (``hda``/``hdca``/
#: ``dce``/...) → ``{"offset": int, "limit": int}``.
ParameterPaginationT = Mapping[str, Mapping[str, Any]]

#: Full pagination map keyed by full ``|``-separated parameter name to a
#: per-parameter spec.
OptionsPaginationT = Mapping[str, ParameterPaginationT]

T = TypeVar("T")


def normalize_pagination(pagination: ParameterPaginationT | None, src: str) -> tuple[int, int, str | None]:
    """Return a clamped ``(offset, limit, search)`` for ``src``.

    Falls back to ``(0, DEFAULT_OPTIONS_PAGE_SIZE, None)`` when no spec is
    provided. Always clamps ``limit`` to the inclusive range
    ``[1, MAX_OPTIONS_PAGE_SIZE]`` and ``offset`` to ``>= 0`` — this is the
    server-side guarantee that no single request can pull an unbounded slice.
    ``search`` is coerced to ``None`` when empty/whitespace so a cleared search
    box behaves like no search at all.
    """
    if not pagination:
        return 0, DEFAULT_OPTIONS_PAGE_SIZE, None
    spec = pagination.get(src) or {}
    offset = max(int(spec.get("offset", 0)), 0)
    limit = int(spec.get("limit", DEFAULT_OPTIONS_PAGE_SIZE))
    limit = min(max(limit, 1), MAX_OPTIONS_PAGE_SIZE)
    raw_search = spec.get("search")
    search: str | None = None
    if isinstance(raw_search, str) and raw_search.strip():
        search = raw_search.strip()
    return offset, limit, search


def accumulate_with_filter(
    query_fn: Callable[..., tuple[list, int]],
    filter_fn: Callable[[Any], None | T | list[T]],
    post_filter_offset: int,
    limit: int,
    chunk_size: int | None = None,
) -> tuple[list[T], int, bool]:
    """Walk DB chunks via ``query_fn(offset=, limit=)`` and apply ``filter_fn``.

    ``filter_fn`` returns falsy to drop a row, a single truthy value (typically
    a tuple) to emit one match, or a ``list`` of values to emit multiple
    matches for the same row. Multi-match supports the case where a single
    HDCA satisfies both ``direct_match`` AND ``can_map_over`` for a parameter
    that accepts multiple collection types (e.g., ``list,list:list`` with a
    ``list:list`` HDCA), in which case both entries are emitted.
    Returns ``(matches, pre_filter_total, has_more)`` where:

    - ``matches`` is up to ``limit`` filter results starting from the
      ``post_filter_offset``-th match;
    - ``pre_filter_total`` is the count reported by the underlying query (the
      best estimate available without scanning the full filtered space);
    - ``has_more`` is true if more DB rows exist past the consumed window — it
      may over-estimate when the trailing rows would all be filtered out, but
      a follow-up page request returning empty matches resolves that.

    Used by data-tool-parameter ``to_dict`` for the chunked path that
    accommodates Python-only predicates (``options_filter_attribute``,
    ``data_destination`` public-role checks, collection subcollection mapping).
    """
    chunk_size = chunk_size or max(limit, 50)
    matches: list[T] = []
    skipped = 0
    db_offset = 0
    pre_filter_total = 0
    initialized = False
    while len(matches) < limit:
        rows, total = query_fn(offset=db_offset, limit=chunk_size)
        if not initialized:
            pre_filter_total = total
            initialized = True
        if not rows:
            return matches, pre_filter_total, False
        rows_consumed = 0
        hit_limit = False
        for row in rows:
            rows_consumed += 1
            result = filter_fn(row)
            if not result:
                continue
            # A ``list`` filter result emits multiple matches per row (kept
            # adjacent so a multi-emitting row never straddles a page boundary
            # in a half-emitted state). Anything else truthy is a single
            # match — we deliberately do NOT unpack tuples here, because
            # existing callers return tuples as a single composite match.
            if isinstance(result, list):
                emitted: list[T] = result
            else:
                emitted = [result]
            for entry in emitted:
                if skipped < post_filter_offset:
                    skipped += 1
                    continue
                matches.append(entry)
                if len(matches) >= limit:
                    hit_limit = True
                    break
            if hit_limit:
                break
        # ``rows_consumed`` (not ``len(rows)``) is the right cursor advance:
        # when we break out of the inner loop at the limit, the trailing rows
        # in this chunk are unseen and may still be matches, so leaving them
        # past ``db_offset`` preserves the deliberate over-estimate of
        # ``has_more`` documented above.
        db_offset += rows_consumed
        if len(matches) >= limit:
            break
        if db_offset >= pre_filter_total:
            return matches, pre_filter_total, False
    has_more = db_offset < pre_filter_total
    return matches, pre_filter_total, has_more


def _tag_strings(obj) -> list[str]:
    return [t.user_tname if not t.value else f"{t.user_tname}:{t.value}" for t in obj.tags]


def make_hda_entry(
    security,
    hda,
    name: str,
    *,
    keep: bool = False,
) -> dict[str, Any]:
    """Build an ``options.hda`` / ``pinned.hda`` entry.

    ``hid`` falls back to -1 when the HDA has none — e.g. a rerun input that
    no longer lives in the active history.
    """
    entry: dict[str, Any] = {
        "id": security.encode_id(hda.id),
        "hid": hda.hid if hda.hid is not None else -1,
        "name": name,
        "tags": _tag_strings(hda),
        "src": "hda",
        "keep": keep,
    }
    return entry


def make_hdca_entry(
    security,
    hdca,
    name: str,
    *,
    keep: bool | None = None,
    subcollection_type: str | None = None,
    include_column_definitions: bool = False,
) -> dict[str, Any]:
    """Build an ``options.hdca`` / ``pinned.hdca`` entry.

    ``keep`` is emitted only when explicitly passed; ``DataToolParameter``
    entries carry it, ``DataCollectionToolParameter`` entries do not.
    ``subcollection_type`` flags multirun (map-over) matches.
    ``include_column_definitions`` adds ``column_definitions`` for the
    ``DataCollectionToolParameter`` form, where the client gates
    sample-sheet-aware UI on it.
    """
    entry: dict[str, Any] = {
        "id": security.encode_id(hdca.id),
        "hid": hdca.hid if hdca.hid is not None else -1,
        "name": name,
        "src": "hdca",
        "tags": _tag_strings(hdca),
    }
    if keep is not None:
        entry["keep"] = keep
    if subcollection_type:
        entry["map_over_type"] = subcollection_type
    if include_column_definitions:
        entry["column_definitions"] = hdca.collection.column_definitions
    return entry


def make_dce_entry(security, dce) -> dict[str, Any]:
    return {
        "id": security.encode_id(dce.id),
        "name": dce.element_identifier,
        "is_dataset": dce.hda is not None,
        "src": "dce",
        "tags": [],
        "keep": True,
    }


def make_ldda_entry(security, ldda) -> dict[str, Any]:
    return {
        "id": security.encode_id(ldda.id),
        "name": ldda.name,
        "src": "ldda",
        "tags": [],
        "keep": True,
    }


class DataOptionsBuilder:
    """Owns the ``options`` / ``options_meta`` / ``pinned`` shape returned by
    ``DataToolParameter.to_dict`` and ``DataCollectionToolParameter.to_dict``.

    A single instance covers one ``to_dict`` response. The per-source
    pagination plumbing — ``normalize_pagination``, ``accumulate_with_filter``,
    and the ``options_meta`` record — collapses into one ``paginate`` call so
    the parameter classes can focus on classification (which HDCAs are
    direct-match vs multirun) instead of cursor bookkeeping.

    Callers emit entries via the public ``options`` / ``pinned`` dicts using
    the ``make_*_entry`` factories above, and finalize with ``sort_by_hid``
    and ``write_into``.
    """

    SOURCES: tuple[str, ...] = ("dce", "ldda", "hda", "hdca")

    def __init__(
        self,
        security,
        pagination: ParameterPaginationT | None = None,
        sources: tuple[str, ...] | None = None,
    ):
        """``sources`` overrides which keys appear in ``options``/``pinned`` —
        ``DataCollectionToolParameter`` historically omits ``ldda``, so its
        response dict must match. Defaults to all four standard sources.
        """
        self.security = security
        self._pagination = pagination
        self._sources = sources or self.SOURCES
        self.options: dict[str, list[dict[str, Any]]] = {s: [] for s in self._sources}
        self.pinned: dict[str, list[dict[str, Any]]] = {s: [] for s in self._sources}
        self.options_meta: dict[str, dict[str, Any]] = {}
        self._page_cache: dict[str, tuple[int, int, str | None]] = {}

    def page(self, src: str) -> tuple[int, int, str | None]:
        """Return the ``(offset, limit, search)`` triple for ``src`` per the
        request's pagination spec (clamped + defaulted). Memoized so callers
        and ``paginate()`` see the same normalized values even if
        ``normalize_pagination`` ever becomes non-pure.
        """
        if (cached := self._page_cache.get(src)) is not None:
            return cached
        triple = normalize_pagination(self._pagination, src)
        self._page_cache[src] = triple
        return triple

    def paginate(
        self,
        src: str,
        *,
        query: Callable[..., tuple[list[Any], int]],
        filter: Callable[[Any], None | T | list[T]],
        chunked: bool = True,
    ) -> tuple[list[T], int, bool]:
        """Run a paginated query+filter for ``src`` and record its
        ``options_meta`` entry. Returns ``(matches, total, has_more)`` so the
        caller can convert matches into option dicts (including any
        cross-row dedup logic that does not belong in the per-row filter).

        ``chunked=True`` uses :func:`accumulate_with_filter` — the right
        choice when the filter is a Python predicate that may drop rows.
        ``chunked=False`` issues a single SQL slice and lets the filter act
        as a one-row classifier; the caller is responsible for any
        side-effects of unfiltered totals (e.g. ``has_more`` accuracy when
        almost everything filters out).
        """
        offset, limit, _search = self.page(src)
        if chunked:
            matches, total, has_more = accumulate_with_filter(query, filter, offset, limit)
        else:
            rows, total = query(offset=offset, limit=limit)
            matches = []
            for row in rows:
                result = filter(row)
                if not result:
                    continue
                if isinstance(result, list):
                    matches.extend(result)
                else:
                    matches.append(result)
            has_more = (offset + len(rows)) < total
        self.options_meta[src] = {
            "offset": offset,
            "limit": limit,
            "total_estimate": total,
            "has_more": has_more,
        }
        return matches, total, has_more

    def sort_by_hid(self, *srcs: str) -> None:
        """Sort ``options[src]`` and ``pinned[src]`` by HID descending.

        Defaults to sorting every source that carries an ``hid`` field
        (``hda``, ``hdca``). Pass explicit ``srcs`` to override.
        """
        srcs = srcs or ("hda", "hdca")
        for src in srcs:
            if src in self.options:
                self.options[src].sort(key=lambda k: k.get("hid", -1), reverse=True)
            if src in self.pinned:
                self.pinned[src].sort(key=lambda k: k.get("hid", -1), reverse=True)

    def write_into(self, d: dict[str, Any]) -> None:
        """Install the builder's containers onto a response dict."""
        d["options"] = self.options
        d["pinned"] = self.pinned
        d["options_meta"] = self.options_meta
