"""Modern pydantic based descriptions of Galaxy tool output objects.

output_objects.py is still used for internals and contain references to the actual tool object
but the goal here is to switch to using these overtime at least for external APIs and in library
code where actual tool objects aren't created.
"""

from typing import (
    Generic,
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
)
from typing_extensions import (
    Annotated,
    Literal,
    TypeVar,
)

AnyT = TypeVar("AnyT")
NotRequired = Annotated[Optional[AnyT], Field(None)]
IncomingNotRequiredBoolT = TypeVar("IncomingNotRequiredBoolT")
IncomingNotRequiredStringT = TypeVar("IncomingNotRequiredStringT")
IncomingNotRequiredDatasetCollectionDescriptionT = TypeVar("IncomingNotRequiredDatasetCollectionDescriptionT")
IncomingNotRequiredDatasetCollectionDescription = NotRequired[List["DatasetCollectionDescriptionT"]]

# Use IncomingNotRequired when concrete key: Optional[str] = None would be incorrect


class ToolOutputBaseModelG(BaseModel, Generic[IncomingNotRequiredBoolT, IncomingNotRequiredStringT]):
    name: Annotated[
        IncomingNotRequiredStringT, Field(description="Parameter name. Used when referencing parameter in workflows.")
    ]
    label: Optional[Annotated[str, Field(description="Output label. Will be used as dataset name in history.")]] = None
    hidden: IncomingNotRequiredBoolT


IncomingToolOutputBaseModel = ToolOutputBaseModelG[NotRequired[bool], NotRequired[str]]


class ToolOutputDatasetG(
    ToolOutputBaseModelG[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
    Generic[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
):
    type: Literal["data"]
    format: Annotated[IncomingNotRequiredStringT, Field(description="The short name for the output datatype.")]
    format_source: Optional[str] = None
    metadata_source: Optional[str] = None
    discover_datasets: Optional[List["DatasetCollectionDescriptionT"]] = None
    from_work_dir: Optional[
        Annotated[
            str,
            Field(
                title="from_work_dir",
                description="Relative path to a file produced by the tool in its working directory. Output’s contents are set to this file’s contents.",
            ),
        ]
    ] = None


ToolOutputDataset = ToolOutputDatasetG[bool, str]
IncomingToolOutputDataset = ToolOutputDatasetG[
    NotRequired[bool],
    NotRequired[str],
]


class ToolOutputCollectionStructure(BaseModel):
    collection_type: Optional[str] = None
    collection_type_source: Optional[str] = None
    collection_type_from_rules: Optional[str] = None
    structured_like: Optional[str] = None
    discover_datasets: Optional[List["DatasetCollectionDescriptionT"]] = None


class ToolOutputCollectionG(
    ToolOutputBaseModelG[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
    Generic[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
):
    type: Literal["collection"]
    structure: ToolOutputCollectionStructure


ToolOutputCollection = ToolOutputCollectionG[bool, str]
IncomingToolOutputCollection = ToolOutputCollectionG[NotRequired[bool], NotRequired[str]]


class ToolOutputSimple(ToolOutputBaseModelG):
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


IncomingToolOutputT = Union[
    IncomingToolOutputDataset,
    IncomingToolOutputCollection,
    ToolOutputText,
    ToolOutputInteger,
    ToolOutputFloat,
    ToolOutputBoolean,
]
IncomingToolOutput = Annotated[IncomingToolOutputT, Field(discriminator="type")]
ToolOutputT = Union[
    ToolOutputDataset, ToolOutputCollection, ToolOutputText, ToolOutputInteger, ToolOutputFloat, ToolOutputBoolean
]
ToolOutput = Annotated[ToolOutputT, Field(discriminator="type")]
