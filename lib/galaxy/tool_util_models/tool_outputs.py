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

from pydantic import Field
from typing_extensions import (
    Annotated,
    Literal,
    TypeVar,
)

from ._base import ToolSourceBaseModel

AnyT = TypeVar("AnyT")
NotRequired = Annotated[Optional[AnyT], Field(None)]
IncomingNotRequiredBoolT = TypeVar("IncomingNotRequiredBoolT")
IncomingNotRequiredStringT = TypeVar("IncomingNotRequiredStringT")

# Use IncomingNotRequired when concrete key: Optional[str] = None would be incorrect


class GenericToolOutputBaseModel(ToolSourceBaseModel, Generic[IncomingNotRequiredBoolT, IncomingNotRequiredStringT]):
    name: Annotated[
        IncomingNotRequiredStringT, Field(description="Parameter name. Used when referencing parameter in workflows.")
    ]
    label: Annotated[Optional[str], Field(description="Output label. Will be used as dataset name in history.")] = None
    hidden: Annotated[
        IncomingNotRequiredBoolT, Field(description="If true, the output will not be shown in the history.")
    ]


DiscoverViaT = Literal["tool_provided_metadata", "pattern"]
SortKeyT = Literal["filename", "name", "designation", "dbkey"]
SortCompT = Literal["lexical", "numeric"]


class DatasetCollectionDescription(ToolSourceBaseModel):
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
    sort_reverse: bool = False
    pattern: str


DatasetCollectionDescriptionT = Union[FilePatternDatasetCollectionDescription, ToolProvidedMetadataDatasetCollection]


class GenericToolOutputDataset(
    GenericToolOutputBaseModel[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
    Generic[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
):
    type: Literal["data"]
    format: Annotated[IncomingNotRequiredStringT, Field(description="The short name for the output datatype.")]
    format_source: Annotated[
        Optional[str],
        Field(
            description="This sets the data type of the output dataset(s) to be the same format as that of the specified tool input."
        ),
    ] = None
    metadata_source: Annotated[
        Optional[str],
        Field(
            description="This copies the metadata information from the tool’s input dataset to serve as default for information that cannot be detected from the output. One prominent use case is interval data with a non-standard column order that cannot be deduced from a header line, but which is known to be identical in the input and output datasets."
        ),
    ] = None
    discover_datasets: Optional[List[DatasetCollectionDescriptionT]] = None
    from_work_dir: Annotated[
        Optional[str],
        Field(
            title="from_work_dir",
            description="Relative path to a file produced by the tool in its working directory. Output’s contents are set to this file’s contents.",
        ),
    ] = None


class ToolOutputDataset(GenericToolOutputDataset[bool, str]): ...


class IncomingToolOutputDataset(
    GenericToolOutputDataset[
        NotRequired[bool],
        NotRequired[str],
    ]
): ...


class ToolOutputCollectionStructure(ToolSourceBaseModel):
    collection_type: Optional[str] = None
    collection_type_source: Optional[str] = None
    collection_type_from_rules: Optional[str] = None
    structured_like: Optional[str] = None
    discover_datasets: Optional[List[DatasetCollectionDescriptionT]] = None


class GenericToolOutputCollection(
    GenericToolOutputBaseModel[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
    Generic[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
):
    type: Literal["collection"]
    structure: ToolOutputCollectionStructure


class ToolOutputCollection(GenericToolOutputCollection[bool, str]): ...


class IncomingToolOutputCollection(GenericToolOutputCollection[NotRequired[bool], NotRequired[str]]): ...


class ToolOutputSimple(GenericToolOutputBaseModel):
    pass


class ToolOutputText(ToolOutputSimple):
    type: Literal["text"]


class ToolOutputInteger(ToolOutputSimple):
    type: Literal["integer"]


class ToolOutputFloat(ToolOutputSimple):
    type: Literal["float"]


class ToolOutputBoolean(ToolOutputSimple):
    type: Literal["boolean"]


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
