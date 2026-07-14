"""Modern pydantic based descriptions of Galaxy tool output objects.

output_objects.py is still used for internals and contain references to the actual tool object
but the goal here is to switch to using these overtime at least for external APIs and in library
code where actual tool objects aren't created.
"""

from typing import (
    Annotated,
    Any,
    Generic,
    Literal,
)

from pydantic import (
    ConfigDict,
    Field,
    model_validator,
)
from typing_extensions import (
    TypeVar,
)

from ._base import ToolSourceBaseModel

IncomingNotRequiredBoolT = TypeVar("IncomingNotRequiredBoolT")
IncomingNotRequiredStringT = TypeVar("IncomingNotRequiredStringT")

# Use IncomingNotRequired when concrete key: Optional[str] = None would be incorrect


class GenericToolOutputBaseModel(ToolSourceBaseModel, Generic[IncomingNotRequiredBoolT, IncomingNotRequiredStringT]):
    name: Annotated[
        IncomingNotRequiredStringT, Field(description="Parameter name. Used when referencing parameter in workflows.")
    ]
    label: Annotated[str | None, Field(description="Output label. Will be used as dataset name in history.")] = None
    hidden: Annotated[
        IncomingNotRequiredBoolT, Field(description="If true, the output will not be shown in the history.")
    ]


DiscoverViaT = Literal["tool_provided_metadata", "pattern"]
SortKeyT = Literal["filename", "name", "designation", "dbkey"]
SortCompT = Literal["lexical", "numeric"]


# Defaults below mirror the XML parser (galaxy.tool_util.parser.output_collection_def):
# every non-essential discovery attribute has a sensible default there, so an author
# (or an LLM) only needs to supply ``pattern``. Requiring all of them in the model is
# the friction that makes ``discover_datasets`` nearly impossible to author by hand.
class DatasetCollectionDescription(ToolSourceBaseModel):
    # extra="forbid" so a typo'd key (e.g. ``patern``) is rejected rather than silently
    # absorbed by the metadata arm below (which would otherwise collect nothing).
    model_config = ConfigDict(extra="forbid")

    discover_via: DiscoverViaT
    format: str | None = None
    visible: bool = False
    assign_primary_output: bool = False
    directory: str | None = None
    recurse: bool = False
    match_relative_path: bool = False


class ToolProvidedMetadataDatasetCollection(DatasetCollectionDescription):
    # ``discover_via`` is required (no default) so an under-specified descriptor
    # ({} / {format: ...} / a typo'd pattern) does NOT silently resolve to
    # tool_provided_metadata -- it must say so explicitly. Pattern discovery (the
    # default in the XML parser) is opt-out only via the ``FilePattern`` arm, which
    # still requires a real ``pattern``.
    discover_via: Literal["tool_provided_metadata"]


class FilePatternDatasetCollectionDescription(DatasetCollectionDescription):
    discover_via: Literal["pattern"] = "pattern"
    sort_key: SortKeyT = "filename"
    sort_comp: SortCompT = "lexical"
    sort_reverse: bool = False
    pattern: str


DatasetCollectionDescriptionT = FilePatternDatasetCollectionDescription | ToolProvidedMetadataDatasetCollection


class GenericToolOutputDataset(
    GenericToolOutputBaseModel[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
    Generic[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
):
    type: Literal["data"]
    format: Annotated[IncomingNotRequiredStringT, Field(description="The short name for the output datatype.")]
    format_source: Annotated[
        str | None,
        Field(
            description="This sets the data type of the output dataset(s) to be the same format as that of the specified tool input."
        ),
    ] = None
    metadata_source: Annotated[
        str | None,
        Field(
            description="This copies the metadata information from the tool’s input dataset to serve as default for information that cannot be detected from the output. One prominent use case is interval data with a non-standard column order that cannot be deduced from a header line, but which is known to be identical in the input and output datasets."
        ),
    ] = None
    discover_datasets: list[DatasetCollectionDescriptionT] | None = None
    from_work_dir: Annotated[
        str | None,
        Field(
            title="from_work_dir",
            description="Relative path to a file produced by the tool in its working directory. Output’s contents are set to this file’s contents.",
        ),
    ] = None
    precreate_directory: bool | None = False


class ToolOutputDataset(GenericToolOutputDataset[bool, str]): ...


class IncomingToolOutputDataset(GenericToolOutputDataset[bool | None, str | None]):
    name: Annotated[str | None, Field(description="Parameter name. Used when referencing parameter in workflows.")] = (
        None
    )
    hidden: Annotated[bool | None, Field(description="If true, the output will not be shown in the history.")] = None
    format: Annotated[str | None, Field(description="The short name for the output datatype.")] = None


def lift_legacy_collection_structure(output_dict: dict[str, Any]) -> dict[str, Any]:
    # Older DynamicTool.value rows nest collection fields under ``structure:``;
    # the current model expects them flat on the output. Inline them so the
    # parser and pydantic model both see the same flat form. Top-level keys
    # win, but only when they carry a value — an explicit top-level ``None``
    # mustn't shadow a real nested value, or a partial-merge writer could
    # silently drop fields. Returns input untouched when there's no wrapper.
    structure = output_dict.get("structure")
    if not isinstance(structure, dict):
        return output_dict
    lifted = {k: v for k, v in output_dict.items() if k != "structure"}
    for key, value in structure.items():
        if lifted.get(key) is None:
            lifted[key] = value
    return lifted


class GenericToolOutputCollection(
    GenericToolOutputBaseModel[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
    Generic[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
):
    type: Literal["collection"]
    collection_type: str | None = None
    collection_type_source: str | None = None
    collection_type_from_rules: str | None = None
    structured_like: str | None = None
    discover_datasets: list[DatasetCollectionDescriptionT] | None = None

    @model_validator(mode="before")
    @classmethod
    def _lift_legacy_structure(cls, values):
        if isinstance(values, dict):
            return lift_legacy_collection_structure(values)
        return values


class ToolOutputCollection(GenericToolOutputCollection[bool, str]): ...


class IncomingToolOutputCollection(GenericToolOutputCollection[bool | None, str | None]):
    name: Annotated[str | None, Field(description="Parameter name. Used when referencing parameter in workflows.")] = (
        None
    )
    hidden: Annotated[bool | None, Field(description="If true, the output will not be shown in the history.")] = None


class GenericToolOutputSimple(
    GenericToolOutputBaseModel[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
    Generic[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
):
    pass


# Internal / parser-facing variants: ``name`` and ``hidden`` are required, matching
# how ``ToolOutput*Model`` instances are constructed in the output parser (which
# always supplies both). Binding the type vars to ``[bool, str]`` mirrors
# ``ToolOutputDataset`` / ``ToolOutputCollection``.
class ToolOutputText(GenericToolOutputSimple[bool, str]):
    type: Literal["text"]


class ToolOutputInteger(GenericToolOutputSimple[bool, str]):
    type: Literal["integer"]


class ToolOutputFloat(GenericToolOutputSimple[bool, str]):
    type: Literal["float"]


class ToolOutputBoolean(GenericToolOutputSimple[bool, str]):
    type: Literal["boolean"]


# Incoming / authoring variants: ``hidden`` is optional (it has a sensible
# default), but ``name`` stays *required* -- unlike datasets/collections, a simple
# value output has no discovery step to supply a name, so an unnamed one can never
# be referenced. Previously these reused the strict types above, whose unbound type
# vars also forced ``hidden`` to be required -- a bug that made the published schema
# demand a ``hidden`` flag on every simple output.
class IncomingToolOutputSimple(GenericToolOutputSimple[bool | None, str]):
    hidden: Annotated[bool | None, Field(description="If true, the output will not be shown in the history.")] = None


class IncomingToolOutputText(IncomingToolOutputSimple):
    type: Literal["text"]


class IncomingToolOutputInteger(IncomingToolOutputSimple):
    type: Literal["integer"]


class IncomingToolOutputFloat(IncomingToolOutputSimple):
    type: Literal["float"]


class IncomingToolOutputBoolean(IncomingToolOutputSimple):
    type: Literal["boolean"]


IncomingToolOutputT = (
    IncomingToolOutputDataset
    | IncomingToolOutputCollection
    | IncomingToolOutputText
    | IncomingToolOutputInteger
    | IncomingToolOutputFloat
    | IncomingToolOutputBoolean
)
IncomingToolOutput = Annotated[IncomingToolOutputT, Field(discriminator="type")]
ToolOutputT = (
    ToolOutputDataset | ToolOutputCollection | ToolOutputText | ToolOutputInteger | ToolOutputFloat | ToolOutputBoolean
)
ToolOutput = Annotated[ToolOutputT, Field(discriminator="type")]
