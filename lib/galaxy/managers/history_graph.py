from datetime import datetime
from typing import (
    Any,
    Optional,
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import Session

from galaxy.model import (
    Dataset,
    DatasetCollection,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    Job,
    JobToOutputDatasetAssociation,
    JobToOutputDatasetCollectionAssociation,
    ToolRequest,
    ToolRequestImplicitCollectionAssociation,
)
from galaxy.schema.history_graph import (
    ExternalRef,
    GraphEdge,
    GraphNode,
    HistoryGraphResponse,
)
from galaxy.security.idencoding import IdEncodingHelper


def _iso(dt: Optional[datetime]) -> Optional[datetime]:
    return dt


class HistoryGraphBuilder:
    def __init__(self, sa_session: Session, security: IdEncodingHelper, history_id: int, encoded_history_id: str):
        self.sa_session = sa_session
        self.security = security
        self.history_id = history_id
        self.encoded_history_id = encoded_history_id

        self.nodes: list[GraphNode] = []
        self.edges: list[GraphEdge] = []
        self.external_refs: list[ExternalRef] = []

        self.referenced_hda_ids: set[int] = set()
        self.referenced_hdca_ids: set[int] = set()

    def build(self) -> HistoryGraphResponse:
        tool_requests = self._query_tool_requests()
        self._derive_input_edges(tool_requests)
        self._query_output_edges(tool_requests)
        self._fetch_hda_metadata()
        self._fetch_hdca_metadata()
        self._deduplicate_edges()
        self._sort()
        return HistoryGraphResponse(
            history_id=self.encoded_history_id,
            node_count=len(self.nodes),
            edge_count=len(self.edges),
            nodes=self.nodes,
            edges=self.edges,
            external_refs=self.external_refs,
        )

    def _query_tool_requests(self) -> list[dict[str, Any]]:
        first_job = (
            select(
                Job.tool_request_id,
                func.min(Job.id).label("first_job_id"),
            )
            .where(Job.tool_request_id.isnot(None))
            .group_by(Job.tool_request_id)
            .subquery()
        )
        stmt = (
            select(
                ToolRequest.id,
                ToolRequest.state,
                ToolRequest.request,
                Job.tool_id,
                Job.tool_version,
            )
            .outerjoin(first_job, ToolRequest.id == first_job.c.tool_request_id)
            .outerjoin(Job, Job.id == first_job.c.first_job_id)
            .where(ToolRequest.history_id == self.history_id)
        )
        tool_requests = []
        for row in self.sa_session.execute(stmt):
            tool_id = row.tool_id
            if tool_id and tool_id.startswith("__"):
                continue
            tool_requests.append(
                {
                    "id": row.id,
                    "state": row.state,
                    "request": row.request,
                    "tool_id": tool_id,
                    "tool_version": row.tool_version,
                }
            )
            self.nodes.append(
                GraphNode(
                    id=f"r{self.security.encode_id(row.id)}",
                    type="tool_request",
                    state=row.state,
                    tool_id=tool_id,
                    tool_version=row.tool_version,
                )
            )
        return tool_requests

    def _derive_input_edges(self, tool_requests: list[dict[str, Any]]):
        for tr in tool_requests:
            request_data = tr["request"]
            if not request_data:
                continue
            encoded_tr_id = f"r{self.security.encode_id(tr['id'])}"
            self._walk_request(request_data, encoded_tr_id, name=None)

    def _walk_request(self, obj: Any, target: str, name: Optional[str]):
        if isinstance(obj, dict):
            src = obj.get("src")
            raw_id = obj.get("id")
            if src in ("hda", "hdca") and isinstance(raw_id, int):
                if src == "hda":
                    self.referenced_hda_ids.add(raw_id)
                    encoded_source = f"d{self.security.encode_id(raw_id)}"
                else:
                    self.referenced_hdca_ids.add(raw_id)
                    encoded_source = f"c{self.security.encode_id(raw_id)}"
                self.edges.append(
                    GraphEdge(
                        source=encoded_source,
                        target=target,
                        type="input",
                        name=name,
                    )
                )
            else:
                for key, value in obj.items():
                    self._walk_request(value, target, name=key)
        elif isinstance(obj, list):
            for item in obj:
                self._walk_request(item, target, name=name)

    def _query_output_edges(self, tool_requests: list[dict[str, Any]]):
        tr_ids = [tr["id"] for tr in tool_requests]
        if not tr_ids:
            return
        self._query_implicit_collection_outputs(tr_ids)
        self._query_hda_outputs(tr_ids)
        self._query_explicit_collection_outputs(tr_ids)

    def _query_implicit_collection_outputs(self, tr_ids: list[int]):
        stmt = (
            select(
                ToolRequestImplicitCollectionAssociation.tool_request_id,
                ToolRequestImplicitCollectionAssociation.dataset_collection_id,
                ToolRequestImplicitCollectionAssociation.output_name,
            )
            .join(
                HistoryDatasetCollectionAssociation,
                ToolRequestImplicitCollectionAssociation.dataset_collection_id
                == HistoryDatasetCollectionAssociation.id,
            )
            .where(
                ToolRequestImplicitCollectionAssociation.tool_request_id.in_(tr_ids),
                HistoryDatasetCollectionAssociation.history_id == self.history_id,
            )
        )
        for row in self.sa_session.execute(stmt):
            self.referenced_hdca_ids.add(row.dataset_collection_id)
            self.edges.append(
                GraphEdge(
                    source=f"r{self.security.encode_id(row.tool_request_id)}",
                    target=f"c{self.security.encode_id(row.dataset_collection_id)}",
                    type="output",
                    name=row.output_name,
                )
            )

    def _query_hda_outputs(self, tr_ids: list[int]):
        stmt = (
            select(
                Job.tool_request_id,
                JobToOutputDatasetAssociation.dataset_id,
                JobToOutputDatasetAssociation.name,
            )
            .distinct()
            .join(Job, JobToOutputDatasetAssociation.job_id == Job.id)
            .join(
                HistoryDatasetAssociation,
                JobToOutputDatasetAssociation.dataset_id == HistoryDatasetAssociation.id,
            )
            .where(
                Job.tool_request_id.in_(tr_ids),
                HistoryDatasetAssociation.history_id == self.history_id,
            )
        )
        for row in self.sa_session.execute(stmt):
            self.referenced_hda_ids.add(row.dataset_id)
            self.edges.append(
                GraphEdge(
                    source=f"r{self.security.encode_id(row.tool_request_id)}",
                    target=f"d{self.security.encode_id(row.dataset_id)}",
                    type="output",
                    name=row.name,
                )
            )

    def _query_explicit_collection_outputs(self, tr_ids: list[int]):
        stmt = (
            select(
                Job.tool_request_id,
                JobToOutputDatasetCollectionAssociation.dataset_collection_id,
                JobToOutputDatasetCollectionAssociation.name,
            )
            .distinct()
            .join(Job, JobToOutputDatasetCollectionAssociation.job_id == Job.id)
            .join(
                HistoryDatasetCollectionAssociation,
                JobToOutputDatasetCollectionAssociation.dataset_collection_id
                == HistoryDatasetCollectionAssociation.id,
            )
            .where(
                Job.tool_request_id.in_(tr_ids),
                HistoryDatasetCollectionAssociation.history_id == self.history_id,
            )
        )
        for row in self.sa_session.execute(stmt):
            self.referenced_hdca_ids.add(row.dataset_collection_id)
            self.edges.append(
                GraphEdge(
                    source=f"r{self.security.encode_id(row.tool_request_id)}",
                    target=f"c{self.security.encode_id(row.dataset_collection_id)}",
                    type="output",
                    name=row.name,
                )
            )

    def _fetch_hda_metadata(self):
        if not self.referenced_hda_ids:
            return
        stmt = (
            select(
                HistoryDatasetAssociation.id,
                HistoryDatasetAssociation.history_id,
                HistoryDatasetAssociation.hid,
                HistoryDatasetAssociation.name,
                HistoryDatasetAssociation._state,
                Dataset.state.label("dataset_state"),
                HistoryDatasetAssociation.extension,
                HistoryDatasetAssociation.deleted,
                HistoryDatasetAssociation.visible,
                HistoryDatasetAssociation.create_time,
                HistoryDatasetAssociation.update_time,
            )
            .join(Dataset, HistoryDatasetAssociation.dataset_id == Dataset.id)
            .where(HistoryDatasetAssociation.id.in_(self.referenced_hda_ids))
        )
        found: set[int] = set()
        for row in self.sa_session.execute(stmt):
            found.add(row.id)
            if row.history_id == self.history_id:
                state = row._state if row._state else row.dataset_state
                self.nodes.append(
                    GraphNode(
                        id=f"d{self.security.encode_id(row.id)}",
                        type="dataset",
                        hid=row.hid,
                        name=row.name,
                        state=state,
                        extension=row.extension,
                        deleted=row.deleted,
                        visible=row.visible,
                        create_time=_iso(row.create_time),
                        update_time=_iso(row.update_time),
                    )
                )
            else:
                self.external_refs.append(
                    ExternalRef(
                        id=f"d{self.security.encode_id(row.id)}",
                        type="dataset",
                        history_id=self.security.encode_id(row.history_id) if row.history_id else None,
                        name=row.name,
                    )
                )
        for missing_id in self.referenced_hda_ids - found:
            self.external_refs.append(
                ExternalRef(
                    id=f"d{self.security.encode_id(missing_id)}",
                    type="dataset",
                    name=None,
                )
            )

    def _fetch_hdca_metadata(self):
        if not self.referenced_hdca_ids:
            return
        stmt = (
            select(
                HistoryDatasetCollectionAssociation.id,
                HistoryDatasetCollectionAssociation.history_id,
                HistoryDatasetCollectionAssociation.hid,
                HistoryDatasetCollectionAssociation.name,
                HistoryDatasetCollectionAssociation.deleted,
                HistoryDatasetCollectionAssociation.visible,
                HistoryDatasetCollectionAssociation.create_time,
                HistoryDatasetCollectionAssociation.update_time,
                DatasetCollection.collection_type,
                DatasetCollection.element_count,
            )
            .join(
                DatasetCollection,
                HistoryDatasetCollectionAssociation.collection_id == DatasetCollection.id,
            )
            .where(HistoryDatasetCollectionAssociation.id.in_(self.referenced_hdca_ids))
        )
        found: set[int] = set()
        for row in self.sa_session.execute(stmt):
            found.add(row.id)
            if row.history_id == self.history_id:
                self.nodes.append(
                    GraphNode(
                        id=f"c{self.security.encode_id(row.id)}",
                        type="collection",
                        hid=row.hid,
                        name=row.name,
                        collection_type=row.collection_type,
                        element_count=row.element_count,
                        deleted=row.deleted,
                        visible=row.visible,
                        create_time=_iso(row.create_time),
                        update_time=_iso(row.update_time),
                    )
                )
            else:
                self.external_refs.append(
                    ExternalRef(
                        id=f"c{self.security.encode_id(row.id)}",
                        type="collection",
                        history_id=self.security.encode_id(row.history_id) if row.history_id else None,
                        name=row.name,
                    )
                )
        for missing_id in self.referenced_hdca_ids - found:
            self.external_refs.append(
                ExternalRef(
                    id=f"c{self.security.encode_id(missing_id)}",
                    type="collection",
                    name=None,
                )
            )

    def _deduplicate_edges(self):
        seen: set[tuple] = set()
        unique: list[GraphEdge] = []
        for edge in self.edges:
            key = (edge.source, edge.target, edge.type, edge.name)
            if key not in seen:
                seen.add(key)
                unique.append(edge)
        self.edges = unique

    def _sort(self):
        type_order = {"dataset": 0, "collection": 1, "tool_request": 2}
        self.nodes.sort(key=lambda n: (type_order.get(n.type, 99), n.hid or 0, n.create_time or "", n.id))

        edge_type_order = {"input": 0, "output": 1}
        self.edges.sort(key=lambda e: (edge_type_order.get(e.type, 99), e.source, e.target))

        ref_type_order = {"dataset": 0, "collection": 1}
        self.external_refs.sort(key=lambda r: (ref_type_order.get(r.type, 99), r.id))
