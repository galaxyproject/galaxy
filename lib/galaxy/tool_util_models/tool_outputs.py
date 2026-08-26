"""Modern pydantic based descriptions of Galaxy tool output objects.

output_objects.py is still used for internals and contain references to the actual tool object
but the goal here is to switch to using these overtime at least for external APIs and in library
code where actual tool objects aren't created.
"""

from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Union,
)

from pydantic import (
    ConfigDict,
    Field,
    model_validator,
)
from typing_extensions import (
    Annotated,
    Literal,
    TypeVar,
)

from ._base import ToolSourceBaseModel

AnyT = TypeVar("AnyT")
NotRequired = Optional[AnyT]
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


# Defaults below mirror the XML parser (galaxy.tool_util.parser.output_collection_def):
# every non-essential discovery attribute has a sensible default there, so an author
# (or an LLM) only needs to supply ``pattern``. Requiring all of them in the model is
# the friction that makes ``discover_datasets`` nearly impossible to author by hand.
class DatasetCollectionDescription(ToolSourceBaseModel):
    # extra="forbid" so a typo'd key (e.g. ``patern``) is rejected rather than silently
    # absorbed by the metadata arm below (which would otherwise collect nothing).
    model_config = ConfigDict(extra="forbid")

    discover_via: Annotated[
        DiscoverViaT,
        Field(
            description="How Galaxy identifies datasets: by matching filenames or by reading tool-provided metadata."
        ),
    ]
    format: Annotated[
        Optional[str],
        Field(description="Galaxy datatype extension assigned to each discovered dataset."),
    ] = None
    visible: Annotated[
        bool,
        Field(description="Whether discovered datasets are visible in the history."),
    ] = False
    assign_primary_output: Annotated[
        bool,
        Field(description="Whether the first matching file replaces the primary dataset output."),
    ] = False
    directory: Annotated[
        Optional[str],
        Field(description="Directory to search, relative to the job working directory."),
    ] = None
    recurse: Annotated[
        bool,
        Field(description="Whether to search recursively below `directory`."),
    ] = False
    match_relative_path: Annotated[
        bool,
        Field(description="Whether `pattern` matches each file's relative path instead of only its filename."),
    ] = False


class ToolProvidedMetadataDatasetCollection(DatasetCollectionDescription):
    # ``discover_via`` is required (no default) so an under-specified descriptor
    # ({} / {format: ...} / a typo'd pattern) does NOT silently resolve to
    # tool_provided_metadata -- it must say so explicitly. Pattern discovery (the
    # default in the XML parser) is opt-out only via the ``FilePattern`` arm, which
    # still requires a real ``pattern``.
    discover_via: Annotated[
        Literal["tool_provided_metadata"],
        Field(description="Read discovered dataset details from the tool-provided metadata file."),
    ]


class FilePatternDatasetCollectionDescription(DatasetCollectionDescription):
    discover_via: Annotated[
        Literal["pattern"],
        Field(description="Discover datasets by matching files produced by the command."),
    ] = "pattern"
    sort_key: Annotated[
        SortKeyT,
        Field(description="Discovered metadata used to order matching files."),
    ] = "filename"
    sort_comp: Annotated[
        SortCompT,
        Field(description="Whether the sort key is compared as text or as a number."),
    ] = "lexical"
    sort_reverse: Annotated[
        bool,
        Field(description="Whether to reverse the discovered dataset order."),
    ] = False
    pattern: Annotated[
        str,
        Field(
            description=(
                "Regular expression matched against produced filenames. Named groups such as `name`, "
                "`designation`, `ext`, and `dbkey` set discovered dataset metadata."
            )
        ),
    ]


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
    discover_datasets: Annotated[
        Optional[List[DatasetCollectionDescriptionT]],
        Field(description="Rules for discovering additional datasets produced by the command."),
    ] = None
    from_work_dir: Annotated[
        Optional[str],
        Field(
            title="from_work_dir",
            description="Relative path to a file produced by the tool in its working directory. Output’s contents are set to this file’s contents.",
        ),
    ] = None
    precreate_directory: Optional[bool] = False


class ToolOutputDataset(GenericToolOutputDataset[bool, str]): ...


class IncomingToolOutputDataset(
    GenericToolOutputDataset[
        NotRequired[bool],
        NotRequired[str],
    ]
):
    """A dataset collected from a file produced in the job working directory."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "result",
                    "type": "data",
                    "format": "txt",
                    "from_work_dir": "result.txt",
                }
            ]
        }
    )
    name: Annotated[
        Optional[str], Field(description="Parameter name. Used when referencing parameter in workflows.")
    ] = None
    hidden: Annotated[Optional[bool], Field(description="If true, the output will not be shown in the history.")] = None
    format: Annotated[Optional[str], Field(description="The short name for the output datatype.")] = None


def lift_legacy_collection_structure(output_dict: Dict[str, Any]) -> Dict[str, Any]:
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
        # Old serialized collection structures included this XML/rules-only
        # key even when unused. Do not reintroduce a null placeholder into the
        # narrower incoming YAML model.
        if key == "collection_type_from_rules" and value is None:
            continue
        if lifted.get(key) is None:
            lifted[key] = value
    return lifted


class GenericToolOutputCollection(
    GenericToolOutputBaseModel[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
    Generic[IncomingNotRequiredBoolT, IncomingNotRequiredStringT],
):
    type: Literal["collection"]
    collection_type: Annotated[
        Optional[str],
        Field(description="Collection structure, such as `list`, `paired`, or a nested type such as `list:paired`."),
    ] = None
    collection_type_source: Annotated[
        Optional[str],
        Field(description="Input collection whose structure determines this output collection's type."),
    ] = None
    structured_like: Annotated[
        Optional[str],
        Field(description="Input collection whose element identifiers and nesting this output mirrors."),
    ] = None
    discover_datasets: Annotated[
        Optional[List[DatasetCollectionDescriptionT]],
        Field(description="Rules used to discover and populate collection elements from produced files."),
    ] = None

    @model_validator(mode="before")
    @classmethod
    def _lift_legacy_structure(cls, values):
        if isinstance(values, dict):
            return lift_legacy_collection_structure(values)
        return values


class ToolOutputCollection(GenericToolOutputCollection[bool, str]):
    # XML/rules-based tools can derive the collection type from a rules input.
    # Incoming YAML user tools deliberately do not expose this parser-only field.
    collection_type_from_rules: Optional[str] = None


class IncomingToolOutputCollection(GenericToolOutputCollection[NotRequired[bool], NotRequired[str]]):
    """A dataset collection populated by discovering files produced by the command."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "results",
                    "type": "collection",
                    "collection_type": "list",
                    "discover_datasets": [{"pattern": "(?P<name>.+)\\.txt", "format": "txt"}],
                }
            ]
        },
    )
    name: Annotated[
        Optional[str], Field(description="Parameter name. Used when referencing parameter in workflows.")
    ] = None
    hidden: Annotated[Optional[bool], Field(description="If true, the output will not be shown in the history.")] = None


class IncomingUserToolOutputDataset(IncomingToolOutputDataset):
    """A user-defined tool dataset discovered only from files inside the job working directory."""

    # Pydantic intentionally narrows this authoring model's accepted schema.
    discover_datasets: Annotated[
        Optional[List[FilePatternDatasetCollectionDescription]],
        Field(description="Filename pattern used to discover additional datasets produced by the command."),
    ] = None  # type: ignore[assignment]


class IncomingUserToolOutputCollection(IncomingToolOutputCollection):
    """A user-defined tool collection populated only by matching produced filenames."""

    # Pydantic intentionally narrows this authoring model's accepted schema.
    discover_datasets: Annotated[
        Optional[List[FilePatternDatasetCollectionDescription]],
        Field(description="Filename pattern used to discover and populate collection elements."),
    ] = None  # type: ignore[assignment]


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
class IncomingToolOutputSimple(GenericToolOutputSimple[NotRequired[bool], str]):
    hidden: Annotated[Optional[bool], Field(description="If true, the output will not be shown in the history.")] = None


class IncomingToolOutputText(IncomingToolOutputSimple):
    """A text value emitted as a workflow-visible scalar output."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "message", "type": "text"}]})
    type: Literal["text"]


class IncomingToolOutputInteger(IncomingToolOutputSimple):
    """An integer value emitted as a workflow-visible scalar output."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "match_count", "type": "integer"}]})
    type: Literal["integer"]


class IncomingToolOutputFloat(IncomingToolOutputSimple):
    """A floating-point value emitted as a workflow-visible scalar output."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "score", "type": "float"}]})
    type: Literal["float"]


class IncomingToolOutputBoolean(IncomingToolOutputSimple):
    """A boolean value emitted as a workflow-visible scalar output."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "matched", "type": "boolean"}]})
    type: Literal["boolean"]


IncomingToolOutputT = Union[
    IncomingToolOutputDataset,
    IncomingToolOutputCollection,
    IncomingToolOutputText,
    IncomingToolOutputInteger,
    IncomingToolOutputFloat,
    IncomingToolOutputBoolean,
]
IncomingToolOutput = Annotated[IncomingToolOutputT, Field(discriminator="type")]
IncomingUserToolOutputT = Union[IncomingUserToolOutputDataset, IncomingUserToolOutputCollection]
IncomingUserToolOutput = Annotated[IncomingUserToolOutputT, Field(discriminator="type")]
ToolOutputT = Union[
    ToolOutputDataset, ToolOutputCollection, ToolOutputText, ToolOutputInteger, ToolOutputFloat, ToolOutputBoolean
]
ToolOutput = Annotated[ToolOutputT, Field(discriminator="type")]
