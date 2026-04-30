"""Bounded user-action provenance graph for Galaxy histories.

For each selected top-level history item, resolves its producing
tool_request and that tool_request's declared inputs from the
submission payload, one hop out from the seed.
"""

import json
import logging
from typing import (
    Optional,
    Union,
)

from boltons.iterutils import remap
from sqlalchemy import (
    Select,
    select,
    union_all,
)
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import literal_column

from galaxy.model import (
    Dataset,
    DatasetCollection,
    DatasetCollectionElement,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    Job,
    JobToOutputDatasetAssociation,
    JobToOutputDatasetCollectionAssociation,
    ToolRequest,
)
from galaxy.schema.history_graph import (
    GraphEdge,
    GraphNode,
    HistoryGraphResponse,
    TruncationInfo,
)
from galaxy.security.idencoding import IdEncodingHelper

log = logging.getLogger(__name__)

TYPE_RANK = {"dataset": 0, "collection": 1, "tool_request": 2}
EDGE_TYPE_RANK = {"dataset_input": 0, "dataset_output": 1, "collection_input": 2, "collection_output": 3}
NODE_TYPE_PREFIX = {"dataset": "d", "collection": "c", "tool_request": "r"}
MAX_LIMIT = 1000


class HistoryGraphBuilder:
    """Builds a provenance graph from selected history items.

    Behaviors:
    - HDA producer edges come from JobToOutputDatasetAssociation joined
      to Job.
    - HDCA producer edges come from JobToOutputDatasetCollectionAssociation
      joined to Job.
    - Input edges come from the tool_request.request submission payload.
    - When an item resolves to more than one distinct producing
      tool_request, the item is kept as a node and the producer edge is
      skipped with a debug log.
    - Malformed payloads are logged at debug level and the item becomes
      a node with no input edges.
    - Hidden HDAs that belong to a collection are filtered before
      producer lookup and surfaced via their parent HDCA instead.
    - ``limit`` is clamped to ``MAX_LIMIT`` to keep per-request work
      bounded regardless of caller input.
    """

    def __init__(
        self,
        sa_session: Session,
        security: IdEncodingHelper,
        history_id: int,
        limit: int = 500,
        toolbox=None,
        include_deleted: bool = False,
        seed: Optional[str] = None,
        direction: str = "both",
        depth: int = 5,
        seed_scope: Optional[str] = None,
    ):
        self.sa_session = sa_session
        self.security = security
        self.history_id = history_id
        self.limit = min(limit, MAX_LIMIT)
        self.toolbox = toolbox
        self.include_deleted = include_deleted
        self.seed = seed
        self.direction = direction
        self.depth = depth
        self.seed_scope = seed_scope
        self._older_than_hid: Optional[int] = None
        self._newer_than_hid: Optional[int] = None
        self._sort_keys: dict[str, tuple[int, int]] = {}

    def build(self) -> HistoryGraphResponse:
        truncation = TruncationInfo()
        if self.seed_scope:
            truncation.scope_type = "seed_centered"
            self._resolve_seed_scope(self.seed_scope)

        # 1. Select top-level items in scope.
        dataset_ids, collection_ids, item_capped = self._select_items()
        truncation.item_count_capped = item_capped

        # 2. Remove hidden collection elements.
        dataset_ids = self._remove_hidden_elements(dataset_ids)

        # 3. Producer lookup + payload input resolution.
        edges: list[GraphEdge] = []
        tr_nodes: dict[int, Optional[str]] = {}  # tr_id -> tool_id
        closure_dataset_ids: set[int] = set()
        closure_collection_ids: set[int] = set()

        hda_producers = self._hda_producers(dataset_ids)
        hdca_producers = self._hdca_producers(collection_ids)
        all_producers = {**hda_producers, **hdca_producers}

        # Emit output edges and collect tr_ids.
        for item_key, (tr_id, tool_id) in all_producers.items():
            item_type, item_id = item_key
            tr_nodes[tr_id] = tool_id
            src = self._encode("tool_request", tr_id)
            tgt = self._encode(item_type, item_id)
            etype = "dataset_output" if item_type == "dataset" else "collection_output"
            edges.append(GraphEdge(source=src, target=tgt, type=etype))

        # Batch-fetch all payloads, parse inputs, emit input edges.
        payloads = self._fetch_payloads(set(tr_nodes.keys()))
        for tr_id, payload in payloads.items():
            input_refs = self._extract_inputs(payload)
            for ref_type, ref_id in input_refs:
                src = self._encode(ref_type, ref_id)
                tgt = self._encode("tool_request", tr_id)
                etype = "dataset_input" if ref_type == "dataset" else "collection_input"
                edges.append(GraphEdge(source=src, target=tgt, type=etype))
                if ref_type == "dataset" and ref_id not in dataset_ids:
                    closure_dataset_ids.add(ref_id)
                elif ref_type == "collection" and ref_id not in collection_ids:
                    closure_collection_ids.add(ref_id)

        # 4. Filter closure items by the same deleted policy as seed selection.
        if not self.include_deleted and (closure_dataset_ids or closure_collection_ids):
            closure_dataset_ids = self._filter_deleted_ids(HistoryDatasetAssociation, closure_dataset_ids)
            closure_collection_ids = self._filter_deleted_ids(
                HistoryDatasetCollectionAssociation, closure_collection_ids
            )

        # Build nodes.
        all_dataset_ids = dataset_ids | closure_dataset_ids
        all_collection_ids = collection_ids | closure_collection_ids
        nodes: list[GraphNode] = []
        nodes.extend(self._dataset_nodes(all_dataset_ids))
        nodes.extend(self._collection_nodes(all_collection_ids))
        nodes.extend(self._tr_nodes(tr_nodes))

        # Invariant: every edge endpoint must be a node. Edges were emitted
        # before closure deletion filtering, so drop any that now reference
        # an item that did not survive.
        node_id_set = {n.id for n in nodes}
        edges = [e for e in edges if e.source in node_id_set and e.target in node_id_set]

        # 5. Resolve tool names.
        self._resolve_tool_names(nodes)

        # 6. Optional seed subgraph filter (in-memory only).
        if self.seed:
            node_ids = {n.id for n in nodes}
            truncation.seed_in_scope = self.seed in node_ids
            nodes, edges = self._seed_filter(self.seed, nodes, edges)

        # 7. Sort.
        nodes, edges = self._sort(nodes, edges)
        return HistoryGraphResponse(nodes=nodes, edges=edges, truncated=truncation)

    # ── Item selection ──

    def _resolve_seed_scope(self, seed_scope: str):
        from galaxy.exceptions import RequestParameterInvalidException

        prefix = seed_scope[0]
        try:
            db_id = self.security.decode_id(seed_scope[1:])
        except Exception:
            raise RequestParameterInvalidException(f"Invalid seed_scope encoding: {seed_scope!r}")
        model = HistoryDatasetAssociation if prefix == "d" else HistoryDatasetCollectionAssociation
        row = self.sa_session.execute(
            select(model.hid).where(model.id == db_id, model.history_id == self.history_id)
        ).first()
        if row is None or row.hid is None:
            raise RequestParameterInvalidException(f"seed_scope {seed_scope} not found in history.")
        half = self.limit // 2
        self._older_than_hid = row.hid + half + (self.limit % 2)
        self._newer_than_hid = row.hid - half - 1

    def _select_items(self) -> tuple[set[int], set[int], bool]:
        hda_q: Select = select(
            HistoryDatasetAssociation.id,
            HistoryDatasetAssociation.hid,
            literal_column("'dataset'").label("item_type"),
        ).where(HistoryDatasetAssociation.history_id == self.history_id)
        if not self.include_deleted:
            hda_q = hda_q.where(HistoryDatasetAssociation.deleted == False)  # noqa: E712
        if self._older_than_hid is not None:
            hda_q = hda_q.where(HistoryDatasetAssociation.hid < self._older_than_hid)
        if self._newer_than_hid is not None:
            hda_q = hda_q.where(HistoryDatasetAssociation.hid > self._newer_than_hid)

        hdca_q: Select = select(
            HistoryDatasetCollectionAssociation.id,
            HistoryDatasetCollectionAssociation.hid,
            literal_column("'collection'").label("item_type"),
        ).where(HistoryDatasetCollectionAssociation.history_id == self.history_id)
        if not self.include_deleted:
            hdca_q = hdca_q.where(HistoryDatasetCollectionAssociation.deleted == False)  # noqa: E712
        if self._older_than_hid is not None:
            hdca_q = hdca_q.where(HistoryDatasetCollectionAssociation.hid < self._older_than_hid)
        if self._newer_than_hid is not None:
            hdca_q = hdca_q.where(HistoryDatasetCollectionAssociation.hid > self._newer_than_hid)

        combined = union_all(hda_q, hdca_q).subquery()
        # Deterministic order: hid desc, then id desc as a stable tiebreaker
        # so duplicate hids (theoretically possible across imported data) do
        # not affect internal selection stability.
        stmt = (
            select(combined.c.id, combined.c.hid, combined.c.item_type)
            .order_by(combined.c.hid.desc(), combined.c.id.desc())
            .limit(self.limit + 1)
        )

        dataset_ids: set[int] = set()
        collection_ids: set[int] = set()
        count = 0
        for row in self.sa_session.execute(stmt):
            count += 1
            if count > self.limit:
                break
            if row.item_type == "dataset":
                dataset_ids.add(row.id)
            else:
                collection_ids.add(row.id)
        return dataset_ids, collection_ids, count > self.limit

    def _remove_hidden_elements(self, dataset_ids: set[int]) -> set[int]:
        if not dataset_ids:
            return dataset_ids
        stmt = (
            select(HistoryDatasetAssociation.id)
            .join(DatasetCollectionElement, DatasetCollectionElement.hda_id == HistoryDatasetAssociation.id)
            .where(
                HistoryDatasetAssociation.id.in_(dataset_ids),
                HistoryDatasetAssociation.visible == False,  # noqa: E712
            )
            .distinct()
        )
        to_remove = {row.id for row in self.sa_session.execute(stmt)}
        return dataset_ids - to_remove

    def _filter_deleted_ids(
        self,
        model_cls: Union[type[HistoryDatasetAssociation], type[HistoryDatasetCollectionAssociation]],
        ids: set[int],
    ) -> set[int]:
        """Return the subset of ``ids`` whose rows are not marked deleted.

        Used to apply the seed-side deleted policy to closure items
        pulled in via payload refs."""
        if not ids:
            return ids
        stmt = select(model_cls.id).where(
            model_cls.id.in_(ids),
            model_cls.deleted == False,  # noqa: E712
        )
        return {row.id for row in self.sa_session.execute(stmt)}

    # ── Producer lookup ──

    def _hda_producers(self, dataset_ids: set[int]) -> dict[tuple[str, int], tuple[int, str]]:
        """Resolve each HDA's producing (tool_request_id, tool_id) by
        joining JobToOutputDatasetAssociation to Job. Only HDAs with
        exactly one distinct producing tool_request are returned;
        ambiguous ones are logged at debug level."""
        if not dataset_ids:
            return {}
        stmt = (
            select(
                JobToOutputDatasetAssociation.dataset_id.label("hda_id"),
                Job.tool_request_id,
                Job.tool_id,
            )
            .join(Job, Job.id == JobToOutputDatasetAssociation.job_id)
            .where(
                JobToOutputDatasetAssociation.dataset_id.in_(dataset_ids),
                Job.tool_request_id.isnot(None),
                Job.tool_id.isnot(None),
                Job.tool_id != "__DATA_FETCH__",
            )
        )
        candidates: dict[int, dict[int, str]] = {}  # hda_id -> {tr_id: tool_id}
        for row in self.sa_session.execute(stmt):
            candidates.setdefault(row.hda_id, {})[row.tool_request_id] = row.tool_id

        result: dict[tuple[str, int], tuple[int, str]] = {}
        for hda_id, tr_map in candidates.items():
            if len(tr_map) == 1:
                tr_id, tool_id = next(iter(tr_map.items()))
                result[("dataset", hda_id)] = (tr_id, tool_id)
            else:
                log.debug("history_graph: skipping HDA %d — ambiguous producer (%s)", hda_id, set(tr_map.keys()))
        return result

    def _hdca_producers(self, collection_ids: set[int]) -> dict[tuple[str, int], tuple[int, str]]:
        """Resolve each HDCA's producing (tool_request_id, tool_id) by
        joining JobToOutputDatasetCollectionAssociation to Job. Only
        HDCAs with exactly one distinct producing tool_request are
        returned; ambiguous ones are logged at debug level."""
        if not collection_ids:
            return {}
        stmt = (
            select(
                JobToOutputDatasetCollectionAssociation.dataset_collection_id.label("hdca_id"),
                Job.tool_request_id,
                Job.tool_id,
            )
            .join(Job, Job.id == JobToOutputDatasetCollectionAssociation.job_id)
            .where(
                JobToOutputDatasetCollectionAssociation.dataset_collection_id.in_(collection_ids),
                Job.tool_request_id.isnot(None),
                Job.tool_id.isnot(None),
                Job.tool_id != "__DATA_FETCH__",
            )
        )
        candidates: dict[int, dict[int, str]] = {}
        for row in self.sa_session.execute(stmt):
            candidates.setdefault(row.hdca_id, {})[row.tool_request_id] = row.tool_id

        result: dict[tuple[str, int], tuple[int, str]] = {}
        for hdca_id, tr_map in candidates.items():
            if len(tr_map) == 1:
                tr_id, tool_id = next(iter(tr_map.items()))
                result[("collection", hdca_id)] = (tr_id, tool_id)
            else:
                log.debug("history_graph: skipping HDCA %d — ambiguous producer (%s)", hdca_id, set(tr_map.keys()))
        return result

    # ── Payload input resolution ──

    def _fetch_payloads(self, tr_ids: set[int]) -> dict[int, dict]:
        """Return raw ``tool_request.request`` payloads keyed by tool
        request id. Rows whose ``request`` field is not a dict (after
        decoding a JSON string form) are silently dropped with a debug
        log, on the assumption that a malformed payload contributes no
        usable input refs."""
        if not tr_ids:
            return {}
        stmt = select(ToolRequest.id, ToolRequest.request).where(ToolRequest.id.in_(tr_ids))
        result: dict[int, dict] = {}
        for row in self.sa_session.execute(stmt):
            try:
                payload = json.loads(row.request) if isinstance(row.request, str) else row.request
                if isinstance(payload, dict):
                    result[row.id] = payload
            except (json.JSONDecodeError, TypeError):
                log.debug("history_graph: malformed payload for tool_request %d", row.id)
        return result

    def _extract_inputs(self, payload: dict) -> set[tuple[str, int]]:
        """Sole payload entry point inside the builder. Walks a single
        ``tool_request.request`` payload and returns the deduplicated
        set of input refs the builder will emit edges for.

        Contract, in order:
        1. Extract declared ``{src, id}`` refs from the payload, using
           the same ``boltons.iterutils.remap`` traversal idiom as
           ``jobs.py::populate_input_data_input_id`` — when we hit a
           leaf keyed ``id``, we peek at its sibling ``src`` on the
           parent container to decide whether it is an HDA/HDCA ref.
        2. Normalize refs so that each one points at a top-level
           history item (see ``_normalize_refs``).
        3. Return as a set — the caller does not need to dedupe.

        Payload shape is trusted to be Pydantic-validated upstream when
        the tool_request was accepted; no explicit depth or ref caps are
        applied here by design."""
        refs: set[tuple[str, int]] = set()

        def visit(path, key, value):
            if key == "id" and isinstance(value, int) and not isinstance(value, bool):
                parent = payload
                for step in path:
                    parent = parent[step]
                if isinstance(parent, dict):
                    src = parent.get("src")
                    if src == "hda":
                        refs.add(("dataset", value))
                    elif src == "hdca":
                        refs.add(("collection", value))
            return key, value

        remap(payload, visit=visit)
        return self._normalize_refs(refs)

    def _normalize_refs(self, refs: set[tuple[str, int]]) -> set[tuple[str, int]]:
        """Apply the single normalization rule: a hidden-element HDA
        ref is replaced with its parent HDCA. Single-hop only — the
        replacement is not re-normalized. No other rules apply here
        by design; adding more cases should be weighed against the
        invariant that every emitted ref points at a top-level item."""
        hda_ids = [item_id for t, item_id in refs if t == "dataset"]
        hdca_parents: dict[int, int] = {}
        if hda_ids:
            stmt = (
                select(
                    HistoryDatasetAssociation.id.label("hda_id"),
                    HistoryDatasetCollectionAssociation.id.label("hdca_id"),
                )
                .join(DatasetCollectionElement, DatasetCollectionElement.hda_id == HistoryDatasetAssociation.id)
                .join(
                    HistoryDatasetCollectionAssociation,
                    HistoryDatasetCollectionAssociation.collection_id == DatasetCollectionElement.dataset_collection_id,
                )
                .where(
                    HistoryDatasetAssociation.id.in_(hda_ids),
                    HistoryDatasetAssociation.visible == False,  # noqa: E712
                )
            )
            for row in self.sa_session.execute(stmt):
                hdca_parents[row.hda_id] = row.hdca_id

        result: set[tuple[str, int]] = set()
        for ref_type, ref_id in refs:
            if ref_type == "dataset" and ref_id in hdca_parents:
                result.add(("collection", hdca_parents[ref_id]))
            else:
                result.add((ref_type, ref_id))
        return result

    # ── Node construction ──

    def _dataset_nodes(self, db_ids: set[int]) -> list[GraphNode]:
        if not db_ids:
            return []
        stmt = (
            select(
                HistoryDatasetAssociation.id,
                HistoryDatasetAssociation.name,
                HistoryDatasetAssociation.hid,
                HistoryDatasetAssociation._state,
                Dataset.state.label("dataset_state"),
                HistoryDatasetAssociation.extension,
                HistoryDatasetAssociation.deleted,
                HistoryDatasetAssociation.visible,
            )
            .join(Dataset, HistoryDatasetAssociation.dataset_id == Dataset.id)
            .where(HistoryDatasetAssociation.id.in_(db_ids))
        )
        return [
            GraphNode(
                id=self._encode("dataset", row.id),
                type="dataset",
                name=row.name,
                hid=row.hid,
                state=row._state if row._state else row.dataset_state,
                extension=row.extension,
                deleted=row.deleted,
                visible=row.visible,
            )
            for row in self.sa_session.execute(stmt)
        ]

    def _collection_nodes(self, db_ids: set[int]) -> list[GraphNode]:
        if not db_ids:
            return []
        stmt = (
            select(
                HistoryDatasetCollectionAssociation.id,
                HistoryDatasetCollectionAssociation.name,
                HistoryDatasetCollectionAssociation.hid,
                HistoryDatasetCollectionAssociation.deleted,
                HistoryDatasetCollectionAssociation.visible,
                DatasetCollection.collection_type,
                DatasetCollection.populated_state,
            )
            .join(DatasetCollection, HistoryDatasetCollectionAssociation.collection_id == DatasetCollection.id)
            .where(HistoryDatasetCollectionAssociation.id.in_(db_ids))
        )
        return [
            GraphNode(
                id=self._encode("collection", row.id),
                type="collection",
                name=row.name,
                hid=row.hid,
                state=row.populated_state,
                collection_type=row.collection_type,
                deleted=row.deleted,
                visible=row.visible,
            )
            for row in self.sa_session.execute(stmt)
        ]

    def _tr_nodes(self, tr_map: dict[int, Optional[str]]) -> list[GraphNode]:
        return [
            GraphNode(
                id=self._encode("tool_request", tr_id),
                type="tool_request",
                tool_id=tool_id,
            )
            for tr_id, tool_id in tr_map.items()
        ]

    def _resolve_tool_names(self, nodes: list[GraphNode]):
        toolbox = self.toolbox
        if toolbox is None:
            return
        tool_ids = {n.tool_id for n in nodes if n.type == "tool_request" and n.tool_id}
        name_map: dict[str, str] = {}
        for tool_id in tool_ids:
            try:
                tool = toolbox.get_tool(tool_id)
                if tool and tool.name:
                    name_map[tool_id] = tool.name
            except Exception:
                pass
        for node in nodes:
            if node.type == "tool_request" and node.tool_id and node.tool_id in name_map:
                node.tool_name = name_map[node.tool_id]

    # ── Seed subgraph filter (in-memory only) ──

    def _seed_filter(
        self, seed: str, nodes: list[GraphNode], edges: list[GraphEdge]
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        from galaxy.exceptions import RequestParameterInvalidException

        node_ids = {n.id for n in nodes}
        if seed not in node_ids:
            raise RequestParameterInvalidException(f"Seed {seed} not found in graph.")

        out_map: dict[str, set[str]] = {}
        in_map: dict[str, set[str]] = {}
        for e in edges:
            out_map.setdefault(e.source, set()).add(e.target)
            in_map.setdefault(e.target, set()).add(e.source)

        reachable: set[str] = {seed}
        frontier = {seed}
        for _ in range(self.depth):
            nxt: set[str] = set()
            for nid in frontier:
                if self.direction in ("forward", "both"):
                    nxt |= out_map.get(nid, set()) - reachable
                if self.direction in ("backward", "both"):
                    nxt |= in_map.get(nid, set()) - reachable
            if not nxt:
                break
            reachable |= nxt
            frontier = nxt
        return (
            [n for n in nodes if n.id in reachable],
            [e for e in edges if e.source in reachable and e.target in reachable],
        )

    # ── Sort ──

    def _sort(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> tuple[list[GraphNode], list[GraphEdge]]:
        fallback = (99, 0)
        nodes.sort(key=lambda n: self._sort_keys.get(n.id, fallback))
        edges.sort(
            key=lambda e: (
                self._sort_keys.get(e.source, fallback),
                self._sort_keys.get(e.target, fallback),
                EDGE_TYPE_RANK.get(e.type, 99),
            )
        )
        return nodes, edges

    # ── Utilities ──

    def _encode(self, node_type: str, db_id: int) -> str:
        encoded = f"{NODE_TYPE_PREFIX[node_type]}{self.security.encode_id(db_id)}"
        self._sort_keys[encoded] = (TYPE_RANK[node_type], db_id)
        return encoded
