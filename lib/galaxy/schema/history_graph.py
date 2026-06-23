from typing import (
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    ConfigDict,
)

# Graph-local src vocabulary. Scoped to this context exactly as src is
# scoped elsewhere in Galaxy (DataItemSourceType, src: Literal["job"],
# etc.). "hda"/"hdca" align with the rest of the codebase; "tool_request"
# is the graph's tool-execution node.
NodeSrc = Literal["hda", "hdca", "tool_request"]


class NodeRef(BaseModel):
    """A (src, id) reference to a graph node. Frozen so it is hashable
    and usable directly as an edge endpoint and as an internal key."""

    model_config = ConfigDict(frozen=True)

    src: NodeSrc
    id: str


class GraphNode(BaseModel):
    src: NodeSrc
    id: str
    name: Optional[str] = None
    hid: Optional[int] = None
    state: Optional[str] = None
    extension: Optional[str] = None
    collection_type: Optional[str] = None
    deleted: Optional[bool] = None
    visible: Optional[bool] = None
    tool_id: Optional[str] = None
    tool_name: Optional[str] = None
    job_state_summary: Optional[dict[str, int]] = None

    @property
    def ref(self) -> NodeRef:
        return NodeRef(src=self.src, id=self.id)


class GraphEdge(BaseModel):
    source: NodeRef
    target: NodeRef
    type: Literal[
        "dataset_input",
        "dataset_output",
        "collection_input",
        "collection_output",
        "dataset_element",
    ]


class TruncationInfo(BaseModel):
    item_count_capped: bool = False
    scope_type: Literal["recent", "seed_centered"] = "recent"
    seed_in_scope: Optional[bool] = None


class HistoryGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    truncated: TruncationInfo
