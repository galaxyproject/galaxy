"""Modern pydantic based descriptions of Galaxy tool output objects.

output_objects.py is still used for internals and contain references to the actual tool object
but the goal here is to switch to using these overtime at least for external APIs and in library
code where actual tool objects aren't created.
"""

from typing import (
    List,
    Optional,
    Sequence,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
)
from typing_extensions import (
    Annotated,
    Literal,
)

from .interface import ToolSource


class ToolOutputBaseModel(BaseModel):
    name: str
    label: Optional[str]
    hidden: bool


class ToolOutputDataset(ToolOutputBaseModel):
    type: Literal["data"]
    format: str
    format_source: Optional[str]
    metadata_source: Optional[str]
    discover_datasets: Optional[List["DatasetCollectionDescriptionT"]]


class ToolOutputCollectionStructure(BaseModel):
    collection_type: Optional[str]
    collection_type_source: Optional[str]
    collection_type_from_rules: Optional[str]
    structured_like: Optional[str]
    discover_datasets: Optional[List["DatasetCollectionDescriptionT"]]


class ToolOutputCollection(ToolOutputBaseModel):
    type: Literal["collection"]
    structure: ToolOutputCollectionStructure


class ToolOutputSimple(ToolOutputBaseModel):
    pass


class ToolOutputText(ToolOutputSimple):
    type: Literal["text"]


class ToolOutputInteger(ToolOutputSimple):
    type: Literal["integer"]


class ToolOutputFloat(ToolOutputSimple):
    type: Literal["float"]


class ToolOutputBoolean(ToolOutputSimple):
    type: Literal["boolean"]


DiscoverViaT = Literal["tool_provided_metadata", "pattern"]
SortKeyT = Literal["filename", "name", "designation", "dbkey"]
SortCompT = Literal["lexical", "numeric"]


class DatasetCollectionDescription(BaseModel):
    discover_via: DiscoverViaT
    format: Optional[str]
    visible: bool
    assign_primary_output: bool
    directory: Optional[str]
    recurse: bool
    match_relative_path: bool


class ToolProvidedMetadataDatasetCollection(DatasetCollectionDescription):
    discover_via: Literal["tool_provided_metadata"]


class FilePatternDatasetCollectionDescription(DatasetCollectionDescription):
    discover_via: Literal["pattern"]
    sort_key: SortKeyT
    sort_comp: SortCompT
    pattern: str


DatasetCollectionDescriptionT = Union[FilePatternDatasetCollectionDescription, ToolProvidedMetadataDatasetCollection]


ToolOutputT = Union[
    ToolOutputDataset, ToolOutputCollection, ToolOutputText, ToolOutputInteger, ToolOutputFloat, ToolOutputBoolean
]
ToolOutput = Annotated[ToolOutputT, Field(discriminator="type")]


def from_tool_source(tool_source: ToolSource) -> Sequence[ToolOutput]:
    tool_outputs, tool_output_collections = tool_source.parse_outputs(None)
    outputs = []
    for tool_output in tool_outputs.values():
        outputs.append(tool_output.to_model())
    # for tool_output_collection in tool_output_collections.values():
    #    outputs.append(tool_output_collection.to_model())
    return outputs
