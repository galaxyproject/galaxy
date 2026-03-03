from datetime import datetime
from typing import (
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)


class GraphNode(BaseModel):
    id: str
    type: Literal["dataset", "collection", "tool_request"]
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    hid: Optional[int] = None
    name: Optional[str] = None
    state: Optional[str] = None
    extension: Optional[str] = None
    deleted: Optional[bool] = None
    visible: Optional[bool] = None
    collection_type: Optional[str] = None
    element_count: Optional[int] = None
    tool_id: Optional[str] = None
    tool_version: Optional[str] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    type: Literal["input", "output"]
    name: Optional[str] = None


class ExternalRef(BaseModel):
    id: str
    type: Literal["dataset", "collection"]
    history_id: Optional[str] = None
    name: Optional[str] = None


class HistoryGraphResponse(BaseModel):
    version: str = Field(default="2")
    history_id: str
    node_count: int
    edge_count: int
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    external_refs: list[ExternalRef]
