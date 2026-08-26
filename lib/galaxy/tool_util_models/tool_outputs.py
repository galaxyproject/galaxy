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
        IncomingNotRequiredStringT,
        Field(description="Identifier used to connect this output in workflows and address it in tool tests."),
    ]
    label: Annotated[
        Optional[str],
        Field(description="Name shown for the produced dataset or collection in the history."),
    ] = None
    hidden: Annotated[
        IncomingNotRequiredBoolT,
        Field(description="Set true to keep the output available to workflows without showing it in the history."),
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
    type: Annotated[
        Literal["data"],
        Field(description="Creates one history dataset from a file produced by the command."),
    ]
    format: Annotated[
        IncomingNotRequiredStringT,
        Field(
            description=(
                "Galaxy datatype extension assigned when the command always produces a fixed representation. "
                "Use `format_source` instead when the datatype depends on an input."
            )
        ),
    ]
    format_source: Annotated[
        Optional[str],
        Field(
            description=(
                "Data or collection input whose datatype extension this output inherits. Use this when the command "
                "preserves the input representation, such as filtering reads without changing their format."
            ),
        ),
    ] = None
    metadata_source: Annotated[
        Optional[str],
        Field(
            description=(
                "Single dataset input whose datatype-specific metadata this output copies as defaults. Use this when "
                "the command preserves metadata Galaxy cannot infer from the output, such as interval column assignments."
            ),
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
            description=(
                "Relative path, inside the job working directory, that the command writes for this output. "
                "Galaxy claims that file after the command finishes."
            ),
        ),
    ] = None
    precreate_directory: Annotated[
        Optional[bool],
        Field(
            description=(
                "Set true when `from_work_dir` names a produced directory for a composite datatype. Galaxy copies "
                "the directory contents into the output dataset's extra-files area."
            )
        ),
    ] = False


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
                    "label": "Result",
                    "type": "data",
                    "format": "txt",
                    "from_work_dir": "result.txt",
                }
            ]
        }
    )
    name: Annotated[
        Optional[str],
        Field(description="Identifier used to connect this output in workflows and address it in tool tests."),
    ] = None
    hidden: Annotated[
        Optional[bool],
        Field(description="Set true to keep the output available to workflows without showing it in the history."),
    ] = None
    format: Annotated[
        Optional[str],
        Field(
            description=(
                "Galaxy datatype extension assigned when the command always produces a fixed representation. "
                "Use `format_source` instead when the datatype depends on an input."
            )
        ),
    ] = None


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
    type: Annotated[
        Literal["collection"],
        Field(description="Creates one history dataset collection populated from files produced by the command."),
    ]
    collection_type: Annotated[
        Optional[str],
        Field(
            description=(
                "Fixed structure Galaxy creates for this output, such as `list`, `paired`, or a nested type such "
                "as `list:paired`."
            )
        ),
    ] = None
    collection_type_source: Annotated[
        Optional[str],
        Field(
            description=(
                "Declared data-collection input whose runtime structure determines this output's collection type."
            )
        ),
    ] = None
    structured_like: Annotated[
        Optional[str],
        Field(
            description=(
                "Declared input whose element count, identifiers, and nesting this output mirrors. Use this when "
                "each produced element corresponds to an input element."
            )
        ),
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
                    "label": "Results",
                    "type": "collection",
                    "collection_type": "list",
                    "discover_datasets": [{"pattern": "(?P<name>.+)\\.txt", "format": "txt"}],
                }
            ]
        },
    )
    name: Annotated[
        Optional[str],
        Field(description="Identifier used to connect this output in workflows and address it in tool tests."),
    ] = None
    hidden: Annotated[
        Optional[bool],
        Field(description="Set true to keep the output available to workflows without showing it in the history."),
    ] = None


class IncomingUserToolOutputDataset(IncomingToolOutputDataset):
    """A user-defined tool dataset discovered only from files inside the job working directory."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "result",
                    "label": "Result",
                    "type": "data",
                    "format": "txt",
                    "from_work_dir": "result.txt",
                }
            ],
            "x-usage-examples": [
                {
                    "field": "format",
                    "description": (
                        "`format` can be used to assign a fixed Galaxy datatype when every run writes the same "
                        "representation. The value is a datatype extension, not a filename suffix."
                    ),
                    "definition": {
                        "inputs": [],
                        "shell_command": "printf 'gene\\tscore\\nBRCA1\\t0.95\\n' > scores.tsv",
                        "outputs": [
                            {
                                "name": "scores",
                                "type": "data",
                                "format": "tabular",
                                "from_work_dir": "scores.tsv",
                            }
                        ],
                    },
                },
                {
                    "field": "format_source",
                    "description": (
                        "`format_source` can be used to assign an output the selected input dataset's datatype when "
                        "the command preserves its representation."
                    ),
                    "definition": {
                        "inputs": [
                            {
                                "name": "reads",
                                "type": "data",
                                "format": ["fastq", "fastqsanger"],
                            }
                        ],
                        "shell_command": "head -n 400 '$(inputs.reads.path)' > first.fastq",
                        "outputs": [
                            {
                                "name": "first_reads",
                                "type": "data",
                                "format_source": "reads",
                                "from_work_dir": "first.fastq",
                            }
                        ],
                    },
                },
                {
                    "field": "metadata_source",
                    "description": (
                        "`metadata_source` can be used to copy datatype-specific metadata from an input when the command "
                        "preserves information Galaxy cannot infer from the produced file, such as interval column assignments."
                    ),
                    "definition": {
                        "inputs": [
                            {
                                "name": "intervals",
                                "type": "data",
                                "format": ["interval"],
                            }
                        ],
                        "shell_command": "awk '$3 > $2' '$(inputs.intervals.path)' > filtered.interval",
                        "outputs": [
                            {
                                "name": "filtered_intervals",
                                "type": "data",
                                "format": "interval",
                                "metadata_source": "intervals",
                                "from_work_dir": "filtered.interval",
                            }
                        ],
                    },
                },
                {
                    "field": "from_work_dir",
                    "description": (
                        "`from_work_dir` can be used to claim a file written by the command. The relative path must "
                        "match the command's destination and remain inside the job working directory."
                    ),
                    "definition": {
                        "inputs": [
                            {
                                "name": "message",
                                "type": "text",
                                "label": "Message",
                            }
                        ],
                        "shell_command": "printf '%s\\n' '$(inputs.message)' > message.txt",
                        "outputs": [
                            {
                                "name": "message_file",
                                "type": "data",
                                "format": "txt",
                                "from_work_dir": "message.txt",
                            }
                        ],
                    },
                },
                {
                    "field": "precreate_directory",
                    "description": (
                        "`precreate_directory` can be used with a directory-backed composite datatype. The command "
                        "creates the directory named by `from_work_dir`; Galaxy then copies its contents into the "
                        "output dataset's extra-files area."
                    ),
                    "definition": {
                        "inputs": [
                            {
                                "name": "reference",
                                "type": "data",
                                "format": ["fasta"],
                            }
                        ],
                        "shell_command": (
                            "mkdir index && bwa-mem2 index -p index/reference '$(inputs.reference.path)'"
                        ),
                        "outputs": [
                            {
                                "name": "index",
                                "type": "data",
                                "format": "bwa_mem2_index",
                                "from_work_dir": "index",
                                "precreate_directory": True,
                            }
                        ],
                    },
                },
            ],
        }
    )

    # Pydantic intentionally narrows this authoring model's accepted schema.
    discover_datasets: Annotated[
        Optional[List[FilePatternDatasetCollectionDescription]],
        Field(description="Filename pattern used to discover additional datasets produced by the command."),
    ] = None  # type: ignore[assignment]


class IncomingUserToolOutputCollection(IncomingToolOutputCollection):
    """A user-defined tool collection populated only by matching produced filenames."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "results",
                    "label": "Results",
                    "type": "collection",
                    "collection_type": "list",
                    "discover_datasets": [{"pattern": "(?P<name>.+)\\.txt", "format": "txt"}],
                }
            ],
            "x-usage-examples": [
                {
                    "field": "collection_type",
                    "description": (
                        "`collection_type` can be used to declare a fixed output structure. A `list` contains an "
                        "ordered set of discovered elements; `paired` requires `forward` and `reverse` identifiers."
                    ),
                    "definition": {
                        "inputs": [],
                        "shell_command": (
                            "mkdir reports && printf 'sample\\tvalue\\nA\\t1\\n' > reports/A.tsv && "
                            "printf 'sample\\tvalue\\nB\\t2\\n' > reports/B.tsv"
                        ),
                        "outputs": [
                            {
                                "name": "reports",
                                "type": "collection",
                                "collection_type": "list",
                                "discover_datasets": [
                                    {
                                        "pattern": "(?P<name>.+)\\.tsv",
                                        "directory": "reports",
                                        "format": "tabular",
                                    }
                                ],
                            }
                        ],
                    },
                },
                {
                    "field": "collection_type_source",
                    "description": (
                        "`collection_type_source` can be used when the output has the same runtime collection type "
                        "as a declared data-collection input, including when that input accepts more than one structure."
                    ),
                    "definition": {
                        "inputs": [
                            {
                                "name": "reads",
                                "type": "data_collection",
                                "collection_type": "paired",
                                "format": ["fastqsanger"],
                            }
                        ],
                        "shell_command": (
                            "mkdir copied && cp '$(inputs.reads.elements.forward.path)' copied/forward.fastq && "
                            "cp '$(inputs.reads.elements.reverse.path)' copied/reverse.fastq"
                        ),
                        "outputs": [
                            {
                                "name": "copied_reads",
                                "type": "collection",
                                "collection_type_source": "reads",
                                "discover_datasets": [
                                    {
                                        "pattern": "(?P<name>forward|reverse)\\.fastq",
                                        "directory": "copied",
                                        "format": "fastqsanger",
                                    }
                                ],
                            }
                        ],
                    },
                },
                {
                    "field": "structured_like",
                    "description": (
                        "`structured_like` can be used when each produced element corresponds to an element of a "
                        "declared input. Galaxy mirrors that input's element identifiers and nesting in the output."
                    ),
                    "definition": {
                        "inputs": [
                            {
                                "name": "reads",
                                "type": "data_collection",
                                "collection_type": "paired",
                                "format": ["fastqsanger"],
                            }
                        ],
                        "shell_command": (
                            "mkdir trimmed && head -n 400 '$(inputs.reads.elements.forward.path)' > "
                            "trimmed/forward.fastq && head -n 400 '$(inputs.reads.elements.reverse.path)' > "
                            "trimmed/reverse.fastq"
                        ),
                        "outputs": [
                            {
                                "name": "trimmed_reads",
                                "type": "collection",
                                "collection_type": "paired",
                                "structured_like": "reads",
                                "discover_datasets": [
                                    {
                                        "pattern": "(?P<name>forward|reverse)\\.fastq",
                                        "directory": "trimmed",
                                        "format": "fastqsanger",
                                    }
                                ],
                            }
                        ],
                    },
                },
            ],
        }
    )

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
