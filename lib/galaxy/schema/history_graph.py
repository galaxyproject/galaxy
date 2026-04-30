from typing import (
    Literal,
    Optional,
)

from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    type: Literal["dataset", "collection", "tool_request"]
    name: Optional[str] = None
    hid: Optional[int] = None
    state: Optional[str] = None
    extension: Optional[str] = None
    collection_type: Optional[str] = None
    deleted: Optional[bool] = None
    visible: Optional[bool] = None
    tool_id: Optional[str] = None
    tool_name: Optional[str] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    type: Literal["dataset_input", "dataset_output", "collection_input", "collection_output"]


class TruncationInfo(BaseModel):
    item_count_capped: bool = False
    scope_type: Literal["recent", "seed_centered"] = "recent"
    seed_in_scope: Optional[bool] = None


class HistoryGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    truncated: TruncationInfo
