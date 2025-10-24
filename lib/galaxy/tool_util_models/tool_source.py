from enum import Enum
from typing import (
    List,
    Optional,
    Union,
)

from pydantic import (
    Field,
)
from typing_extensions import (
    Annotated,
    Literal,
    NotRequired,
    TypedDict,
)

from ._base import ToolSourceBaseModel


class Container(ToolSourceBaseModel):
    type: Literal["docker", "singularity"]
    container_id: str


class Requirement(ToolSourceBaseModel):
    type: Literal["package", "set_environment"]


class ContainerRequirement(ToolSourceBaseModel):
    type: Literal["container"]
    container: Container


class PackageRequirement(Requirement):
    type: Literal["package"]
    name: str
    version: Optional[str]


class SetEnvironmentRequirement(Requirement):
    type: Literal["set_environment"]
    environment: str


cores_min_description = "Minimum reserved number of CPU cores."
cores_max_description = "Maximum reserved number of CPU cores."
cores_description = """May be a fractional value to indicate to a scheduling algorithm that one core can be allocated to multiple jobs. For example, a value of 0.25 indicates that up to 4 jobs may run in parallel on 1 core. A value of 1.25 means that up to 3 jobs can run on a 4 core system (4/1.25 ≈ 3).
The reported number of CPU cores reserved for the process is a non-zero integer calculated by rounding up the cores request to the next whole number.
"""
ram_min_description = "Minimum reserved RAM in mebibytes (2**20)."
ram_max_description = "Maximum reserved RAM in mebibytes (2**20)."
ram_description = """May be a fractional value. If so, the actual RAM request is rounded up to the next whole number. The reported amount of RAM reserved for the process is a non-zero integer."""


class ResourceRequirement(ToolSourceBaseModel):
    type: Literal["resource"]
    cores_min: Annotated[
        Union[int, float, None], Field(description=f"{cores_min_description}\n{cores_description}")
    ] = 1
    cores_max: Annotated[
        Union[int, float, None], Field(description=f"{cores_max_description}\n{cores_description}")
    ] = None
    ram_min: Annotated[Union[int, float, None], Field(description=f"{ram_min_description}\n{ram_description}")] = 256
    ram_max: Annotated[Union[int, float, None], Field(description=f"{ram_max_description}\n{ram_description}")] = None
    tmpdir_min: Optional[Union[int, float]] = None
    tmpdir_max: Optional[Union[int, float]] = None
    cuda_version_min: Optional[Union[int, float]] = None
    cuda_compute_capability: Optional[Union[int, float]] = None
    gpu_memory_min: Optional[Union[int, float]] = None
    cuda_device_count_min: Optional[Union[int, float]] = None
    cuda_device_count_max: Optional[Union[int, float]] = None
    shm_size: Optional[Union[int, float]] = None


class JavascriptRequirement(ToolSourceBaseModel):
    type: Literal["javascript"]
    expression_lib: Optional[
        List[
            Annotated[
                str,
                Field(
                    title="expression_lib",
                    description="Provide Javascript/ECMAScript 5.1 code here that will be available for expressions inside the `shell_command` field.",
                    examples=[
                        r"""function pickValue() {
    if (inputs.conditional_parameter.test_parameter == "a") {
        return inputs.conditional_parameter.integer_parameter
    } else {
        return inputs.conditional_parameter.boolean_parameter
    }
}"""
                    ],
                ),
            ]
        ]
    ]


class XrefDict(TypedDict):
    value: str
    type: str


class TemplateConfigFile(ToolSourceBaseModel):
    content: str
    name: Optional[str] = None
    filename: Optional[str] = None


class InputConfigFileContent(ToolSourceBaseModel):
    format: Literal["json"] = "json"
    handle_files: Optional[Literal["paths", "staging_path_and_source_path"]] = None
    type: Literal["inputs"] = "inputs"


class InputConfigFile(ToolSourceBaseModel):
    name: Optional[str] = None
    content: InputConfigFileContent
    filename: Optional[str] = None


class FileSourceConfigFileContent(ToolSourceBaseModel):
    type: Literal["files"] = "files"


class FileSourceConfigFile(ToolSourceBaseModel):
    name: Optional[str]
    filename: Optional[str] = None
    content: FileSourceConfigFileContent


class XmlTemplateConfigFile(TemplateConfigFile):
    eval_engine: Literal["cheetah"] = "cheetah"


class YamlTemplateConfigFile(TemplateConfigFile):
    eval_engine: Literal["ecmascript"] = "ecmascript"


class Citation(ToolSourceBaseModel):
    type: str
    content: str


class HelpContent(ToolSourceBaseModel):
    format: Literal["restructuredtext", "plain_text", "markdown"]
    content: str


class OutputCompareType(str, Enum):
    diff = "diff"
    re_match = "re_match"
    sim_size = "sim_size"
    re_match_multiline = "re_match_multiline"
    contains = "contains"
    image_diff = "image_diff"


class DrillDownOptionsDict(TypedDict):
    name: Optional[str]
    value: str
    options: List["DrillDownOptionsDict"]
    selected: bool


# For fields... just implementing a subset of CWL for Galaxy flavors of these objects
# so far.
CwlType = Literal["File", "null", "boolean", "int", "float", "string"]
FieldType = Union[CwlType, List[CwlType]]


# type ignore because mypy can't handle closed TypedDicts yet
class FieldDict(TypedDict, closed=True):  # type: ignore[call-arg]
    name: str
    type: FieldType
    format: NotRequired[Optional[str]]


JsonTestDatasetDefDict = TypedDict(
    "JsonTestDatasetDefDict",
    {
        "class": Literal["File"],
        "path": NotRequired[Optional[str]],
        "location": NotRequired[Optional[str]],
        "name": NotRequired[Optional[str]],
        "dbkey": NotRequired[Optional[str]],
        "filetype": NotRequired[Optional[str]],
        "composite_data": NotRequired[Optional[List[str]]],
        "tags": NotRequired[Optional[List[str]]],
    },
)

JsonTestCollectionDefElementDict = Union[
    "JsonTestCollectionDefDatasetElementDict", "JsonTestCollectionDefCollectionElementDict"
]

JsonTestCollectionDefDatasetElementDict = TypedDict(
    "JsonTestCollectionDefDatasetElementDict",
    {
        "identifier": str,
        "class": Literal["File"],
        "path": NotRequired[Optional[str]],
        "location": NotRequired[Optional[str]],
        "name": NotRequired[Optional[str]],
        "dbkey": NotRequired[Optional[str]],
        "filetype": NotRequired[Optional[str]],
        "composite_data": NotRequired[Optional[List[str]]],
        "tags": NotRequired[Optional[List[str]]],
    },
)

BaseJsonTestCollectionDefCollectionElementDict = TypedDict(
    "BaseJsonTestCollectionDefCollectionElementDict",
    {
        "class": Literal["Collection"],
        "collection_type": Optional[str],
        "elements": NotRequired[Optional[List[JsonTestCollectionDefElementDict]]],
    },
)

JsonTestCollectionDefCollectionElementDict = TypedDict(
    "JsonTestCollectionDefCollectionElementDict",
    {
        "identifier": str,
        "class": Literal["Collection"],
        "collection_type": Optional[str],
        "elements": NotRequired[Optional[List[JsonTestCollectionDefElementDict]]],
    },
)

JsonTestCollectionDefDict = TypedDict(
    "JsonTestCollectionDefDict",
    {
        "class": Literal["Collection"],
        "collection_type": Optional[str],
        "elements": NotRequired[Optional[List[JsonTestCollectionDefElementDict]]],
        "name": NotRequired[Optional[str]],
    },
)
