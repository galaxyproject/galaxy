from typing import (
    Annotated,
    Any,
    get_args,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    WithJsonSchema,
)

from galaxy.schema.history_graph import NodeSrc

EncodedId = Annotated[str, Field(pattern="^[0-9a-f]+$")]

NODE_SRC_TITLES = {
    "hda": ("Dataset", "A history dataset."),
    "hdca": ("Collection", "A history dataset collection."),
    "tool_request": ("Tool run", "A tool request, i.e. one tool execution."),
}

SeedSrc = Annotated[
    NodeSrc,
    WithJsonSchema(
        {
            "type": "string",
            "oneOf": [
                {"const": src, "title": NODE_SRC_TITLES[src][0], "description": NODE_SRC_TITLES[src][1]}
                for src in get_args(NodeSrc)
            ],
        }
    ),
]


class HistoryGraphParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"dependentRequired": {"seed_src": ["seed_id"], "seed_id": ["seed_src"]}},
    )

    history_id: EncodedId = Field(title="History", description="Encoded id of the history.")
    seed_src: SeedSrc | None = Field(None, title="Seed type", description="Type of the item to focus the graph on.")
    seed_id: EncodedId | None = Field(None, title="Seed", description="Encoded id of the item to focus the graph on.")


class Widget(BaseModel):
    id: str = Field(title="Identifier", description="Stable identifier of the widget.")
    name: str = Field(title="Name", description="Display name of the widget.")
    description: str = Field(title="Description", description="What the widget shows.")
    path: str = Field(
        title="Path",
        description="Path template relative to `<galaxy root>/widgets/`, with path parameters in braces.",
    )
    parameters_schema: dict[str, Any] = Field(
        title="Parameters Schema",
        description="JSON Schema of the parameters object. Path parameters fill the braces in `path`, all others go in the query.",
    )
