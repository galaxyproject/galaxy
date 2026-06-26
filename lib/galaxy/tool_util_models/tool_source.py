import re
from enum import Enum
from typing import (
    Annotated,
    Literal,
    Union,
)

from pydantic import (
    ConfigDict,
    Field,
    model_validator,
    with_config,
)
from pydantic_core import PydanticCustomError
from typing_extensions import (
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
    version: str | None = None


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


ResourceRequirementValue = int | float | str | None


class ResourceRequirement(ToolSourceBaseModel):
    type: Literal["resource"]
    cores_min: Annotated[
        ResourceRequirementValue, Field(description=f"{cores_min_description}\n{cores_description}")
    ] = 1
    cores_max: Annotated[
        ResourceRequirementValue, Field(description=f"{cores_max_description}\n{cores_description}")
    ] = None
    ram_min: Annotated[ResourceRequirementValue, Field(description=f"{ram_min_description}\n{ram_description}")] = 256
    ram_max: Annotated[ResourceRequirementValue, Field(description=f"{ram_max_description}\n{ram_description}")] = None
    tmpdir_min: ResourceRequirementValue = None
    tmpdir_max: ResourceRequirementValue = None
    cuda_version_min: ResourceRequirementValue = None
    cuda_compute_capability: ResourceRequirementValue = None
    gpu_memory_min: ResourceRequirementValue = None
    cuda_device_count_min: ResourceRequirementValue = None
    cuda_device_count_max: ResourceRequirementValue = None
    shm_size: ResourceRequirementValue = None
    timelimit: Annotated[
        ResourceRequirementValue,
        Field(description="Maximum time in seconds the tool is allowed to run. Job will be terminated if exceeded."),
    ] = None


class JavascriptRequirement(ToolSourceBaseModel):
    type: Literal["javascript"]
    expression_lib: None | (
        list[
            Annotated[
                str,
                Field(
                    title="expression_lib",
                    description="Provide Javascript/ECMAScript 5.1 code here that will be available for expressions inside the `shell_command` field.",
                    examples=[r"""function pickValue() {
    if (inputs.conditional_parameter.test_parameter == "a") {
        return inputs.conditional_parameter.integer_parameter
    } else {
        return inputs.conditional_parameter.boolean_parameter
    }
}"""],
                ),
            ]
        ]
    )


class XrefDict(TypedDict):
    value: str
    type: str


class TemplateConfigFile(ToolSourceBaseModel):
    content: str
    name: str | None = None
    filename: str | None = None


class InputConfigFileContent(ToolSourceBaseModel):
    format: Literal["json"] = "json"
    handle_files: Literal["paths", "staging_path_and_source_path"] | None = None
    type: Literal["inputs"] = "inputs"


class InputConfigFile(ToolSourceBaseModel):
    name: str | None = None
    content: InputConfigFileContent
    filename: str | None = None


class FileSourceConfigFileContent(ToolSourceBaseModel):
    type: Literal["files"] = "files"


class FileSourceConfigFile(ToolSourceBaseModel):
    name: str | None
    filename: str | None = None
    content: FileSourceConfigFileContent


class XmlTemplateConfigFile(TemplateConfigFile):
    eval_engine: Literal["cheetah"] = "cheetah"


class YamlTemplateConfigFile(TemplateConfigFile):
    eval_engine: Literal["ecmascript"] = "ecmascript"


# DOI: '10.<registrant>/<suffix>' per Crossref's published shape.
DOI_RE = re.compile(r"^10\.\d{4,9}/.+$")
# Legacy W3C/RFC form prefixes a bare DOI with 'doi:' (optionally with whitespace
# after the colon). Tools written before 26.1 routinely used this form, so we
# normalize it away to the bare DOI rather than rejecting it.
DOI_PREFIX_RE = re.compile(r"^doi:\s*", re.IGNORECASE)
# BibTeX entries open with '@<type>{' -- e.g. '@article{', '@inproceedings{'.
BIBTEX_RE = re.compile(r"^@[a-zA-Z]+\s*\{", re.MULTILINE)


class Citation(ToolSourceBaseModel):
    type: str
    content: str

    @model_validator(mode="after")
    def _check_citation_shape(self) -> "Citation":
        content = (self.content or "").strip()
        if not content:
            raise PydanticCustomError(
                "dynamic_tool.citation_empty",
                "citation content must not be empty",
            )
        # Normalize the legacy 'doi:' prefix to a bare DOI so older tools load and
        # so downstream DOI resolution (https://doi.org/<doi>) gets a clean value.
        normalized = DOI_PREFIX_RE.sub("", content, count=1)
        if normalized != content:
            content = normalized
            self.content = normalized
        citation_type = (self.type or "").strip().lower()
        if citation_type == "doi":
            if not DOI_RE.match(content):
                raise PydanticCustomError(
                    "dynamic_tool.citation_doi_invalid",
                    "declared as DOI but '{content}' does not match DOI shape (^10\\.\\d{{4,9}}/.+$)",
                    {"content": content},
                )
            return self
        if citation_type == "bibtex":
            if not BIBTEX_RE.search(content):
                raise PydanticCustomError(
                    "dynamic_tool.citation_bibtex_invalid",
                    "declared as bibtex but content does not start with '@<type>{{'",
                )
            return self
        # Type wasn't explicitly doi/bibtex -- accept if the content shape is
        # one of the two known forms. Lets a slightly mis-typed entry through
        # instead of fighting models that emit type='reference' or similar.
        if DOI_RE.match(content) or BIBTEX_RE.search(content):
            return self
        raise PydanticCustomError(
            "dynamic_tool.citation_unrecognized",
            "citation (type={ctype}) is neither a recognizable DOI nor a BibTeX entry",
            {"ctype": repr(self.type)},
        )


class HelpContent(ToolSourceBaseModel):
    format: Literal["restructuredtext", "plain_text", "markdown"]
    content: str


StdioExitCodeRangeValue = int | float | Literal["-inf", "inf"]


class StdioExitCode(ToolSourceBaseModel):
    range_start: StdioExitCodeRangeValue
    range_end: StdioExitCodeRangeValue
    error_level: int | float
    desc: str | None = None


class StdioRegex(ToolSourceBaseModel):
    match: str
    stdout_match: bool
    stderr_match: bool
    error_level: int | float
    desc: str | None = None


class Stdio(ToolSourceBaseModel):
    exit_codes: list[StdioExitCode] = Field(default_factory=list)
    regexes: list[StdioRegex] = Field(default_factory=list)


class OutputCompareType(str, Enum):
    diff = "diff"
    re_match = "re_match"
    sim_size = "sim_size"
    re_match_multiline = "re_match_multiline"
    contains = "contains"
    image_diff = "image_diff"


class DrillDownOptionsDict(TypedDict):
    name: str | None
    value: str
    options: list["DrillDownOptionsDict"]
    selected: bool


# For fields... just implementing a subset of CWL for Galaxy flavors of these objects
# so far.
CwlType = Literal["File", "null", "boolean", "int", "float", "string"]
FieldType = CwlType | list[CwlType]


# type ignore because mypy can't handle closed TypedDicts yet
@with_config(ConfigDict(extra="forbid"))
class FieldDict(TypedDict, closed=True):  # type: ignore[call-arg]
    name: str
    type: FieldType
    format: NotRequired[str | None]


JsonTestDatasetDefDict = TypedDict(
    "JsonTestDatasetDefDict",
    {
        "class": Literal["File"],
        "path": NotRequired[str | None],
        "location": NotRequired[str | None],
        "name": NotRequired[str | None],
        "dbkey": NotRequired[str | None],
        "filetype": NotRequired[str | None],
        "composite_data": NotRequired[list[str] | None],
        "tags": NotRequired[list[str] | None],
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
        "path": NotRequired[str | None],
        "location": NotRequired[str | None],
        "name": NotRequired[str | None],
        "dbkey": NotRequired[str | None],
        "filetype": NotRequired[str | None],
        "composite_data": NotRequired[list[str] | None],
        "tags": NotRequired[list[str] | None],
    },
)

BaseJsonTestCollectionDefCollectionElementDict = TypedDict(
    "BaseJsonTestCollectionDefCollectionElementDict",
    {
        "class": Literal["Collection"],
        "collection_type": str | None,
        "elements": NotRequired[list[JsonTestCollectionDefElementDict] | None],
    },
)

JsonTestCollectionDefCollectionElementDict = TypedDict(
    "JsonTestCollectionDefCollectionElementDict",
    {
        "identifier": str,
        "class": Literal["Collection"],
        "collection_type": str | None,
        "elements": NotRequired[list[JsonTestCollectionDefElementDict] | None],
    },
)

JsonTestCollectionDefDict = TypedDict(
    "JsonTestCollectionDefDict",
    {
        "class": Literal["Collection"],
        "collection_type": str | None,
        "elements": NotRequired[list[JsonTestCollectionDefElementDict] | None],
        "name": NotRequired[str | None],
        "fields": NotRequired[list[FieldDict] | None],
    },
)
