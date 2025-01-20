from enum import Enum
from typing import (
    List,
    Optional,
    Union,
)

from pydantic import BaseModel
from typing_extensions import (
    Literal,
    NotRequired,
    TypedDict,
)


class Container(BaseModel):
    type: Literal["docker", "singularity"]
    container_id: str


class Requirement(BaseModel):
    type: Literal["package", "set_environment"]


class ContainerRequirement(BaseModel):
    type: Literal["container"]
    container: Container


class PackageRequirement(Requirement):
    type: Literal["package"]
    name: str
    version: Optional[str]


class SetEnvironmentRequirement(Requirement):
    type: Literal["set_environment"]
    environment: str


class ResourceRequirement(BaseModel):
    type: Literal["resource"]
    cores_min: Optional[Union[int, float]]
    cores_max: Optional[Union[int, float]]
    ram_min: Optional[Union[int, float]]
    ram_max: Optional[Union[int, float]]
    tmpdir_min: Optional[Union[int, float]]
    tmpdir_max: Optional[Union[int, float]]
    cuda_version_min: Optional[Union[int, float]]
    cuda_compute_capability: Optional[Union[int, float]]
    gpu_memory_min: Optional[Union[int, float]]
    cuda_device_count_min: Optional[Union[int, float]]
    cuda_device_count_max: Optional[Union[int, float]]
    shm_size: Optional[Union[int, float]]


class JavascriptRequirement(BaseModel):
    type: Literal["javascript"]
    expression_lib: Optional[List[str]]


class XrefDict(TypedDict):
    value: str
    type: str


class Citation(BaseModel):
    type: str
    content: str


class HelpContent(BaseModel):
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


class FieldDict(TypedDict):
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
