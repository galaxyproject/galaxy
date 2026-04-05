"""Define the ParsedTool model representing metadata extracted from a tool's source.

This is abstraction exported by newer tool shed APIS (circa 2024) and should be sufficient
for reasoning about tool state externally from Galaxy.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import (
    AfterValidator,
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
    RootModel,
)
from typing_extensions import (
    Annotated,
    Literal,
    NotRequired,
    TypedDict,
)

from ._base import ToolSourceBaseModel
from .assertions import assertions
from .parameters import ToolParameterT
from .tool_outputs import (
    IncomingToolOutput,
    ToolOutput,
)
from .tool_source import (
    Citation,
    ContainerRequirement,
    HelpContent,
    JavascriptRequirement,
    OutputCompareType,
    ResourceRequirement,
    XrefDict,
    YamlTemplateConfigFile,
)
from .yaml_parameters import YamlGalaxyToolParameter


def normalize_dict(values, keys: List[str]):
    for key in keys:
        items = values.get(key)
        if isinstance(items, dict):  # dict-of-dicts format
            # Transform dict-of-dicts to list-of-dicts
            values[key] = [{"name": k, **v} for k, v in items.items()]


class _DynamicToolSourceBase(ToolSourceBaseModel):
    # extra="forbid" rejects unknown top-level keys (e.g. a stray `argument:` at
    # the tool level), matching the strict-narrow stance on `inputs`.
    model_config = ConfigDict(
        extra="forbid",
        field_title_generator=lambda field_name, field_info: field_name.lower(),
    )

    id: Annotated[
        Optional[str],
        Field(
            description="Unique identifier for the tool. Should be all lower-case and should not include whitespace.",
            examples=["my-cool-tool"],
            min_length=3,
            max_length=255,
        ),
    ] = None
    version: Annotated[Optional[str], Field(description="Version for the tool.", examples=["0.1.0"])] = None
    name: Annotated[
        str,
        Field(
            description="The name of the tool, displayed in the tool menu. This is not the same as the tool id, which is a unique identifier for the tool."
        ),
    ]
    description: Annotated[
        Optional[str],
        Field(
            description="The description is displayed in the tool menu immediately following the hyperlink for the tool."
        ),
    ] = None
    configfiles: Annotated[
        Optional[List[YamlTemplateConfigFile]], Field(description="A list of config files for this tool.")
    ] = None
    requirements: Annotated[
        Optional[List[Union[JavascriptRequirement, ResourceRequirement, ContainerRequirement]]],
        Field(
            description="A list of requirements needed to execute this tool. These can be javascript expressions, resource requirements or container images."
        ),
    ] = []
    shell_command: Annotated[
        str,
        Field(
            title="shell_command",
            description="A string that contains the command to be executed. Parameters can be referenced inside $().",
            examples=["head -n '$(inputs.n_lines)' '$(inputs.data_input.path)'"],
        ),
    ]
    inputs: List[YamlGalaxyToolParameter] = []
    outputs: List[IncomingToolOutput] = []
    citations: Optional[List[Citation]] = None
    license: Annotated[
        Optional[str],
        Field(
            description="A full URI or a a short [SPDX](https://spdx.org/licenses/) identifier for a license for this tool wrapper. The tool wrapper license can be independent of the underlying tool license. This license covers the tool yaml and associated scripts shipped with the tool.",
            examples=["MIT"],
        ),
    ] = None
    edam_operations: Optional[List[str]] = None
    edam_topics: Optional[List[str]] = None
    xrefs: Optional[List[XrefDict]] = None
    profile: Optional[float] = None
    help: Annotated[Optional[HelpContent], Field(description="Help text shown below the tool interface.")] = None
    tests: Optional[List["YamlToolTest"]] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_items(cls, values):
        if isinstance(values, dict):
            normalize_dict(values, ["inputs", "outputs"])
        return values


class UserToolSource(_DynamicToolSourceBase):
    class_: Annotated[Literal["GalaxyUserTool"], Field(alias="class")]
    container: Annotated[
        str, Field(description="Container image to use for this tool.", examples=["quay.io/biocontainers/python:3.13"])
    ]


class YamlToolSource(_DynamicToolSourceBase):
    class_: Annotated[Literal["GalaxyTool"], Field(alias="class")]
    container: Annotated[
        Optional[str],
        Field(
            description="Container image to use for this tool.",
            examples=["quay.io/biocontainers/python:3.13"],
        ),
    ] = None


DynamicToolSources = Annotated[Union[UserToolSource, YamlToolSource], Field(discriminator="class_")]


class ParsedTool(ToolSourceBaseModel):
    id: str
    version: Optional[str]
    name: str
    description: Optional[str]
    inputs: List[ToolParameterT]
    outputs: List[ToolOutput]
    citations: List[Citation]
    license: Optional[str]
    profile: Optional[str]
    edam_operations: List[str]
    edam_topics: List[str]
    xrefs: List[XrefDict]
    help: Optional[HelpContent]


class StrictModel(BaseModel):

    model_config = ConfigDict(extra="forbid", field_title_generator=lambda field_name, field_info: field_name.lower())


class BaseTestOutputModel(StrictModel):
    file: Optional[str] = None
    path: Optional[str] = None
    location: Optional[AnyUrl] = None
    ftype: Optional[str] = None
    sort: Optional[bool] = None
    compare: Optional[OutputCompareType] = None
    checksum: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    asserts: Optional[assertions] = None
    delta: Optional[int] = None
    delta_frac: Optional[float] = None
    lines_diff: Optional[int] = None
    decompress: Optional[bool] = None


class TestDataOutputAssertions(BaseTestOutputModel):
    class_: Optional[Literal["File"]] = Field("File", alias="class")


class TestCollectionCollectionElementAssertions(StrictModel):
    elements: Optional[Dict[str, "TestCollectionElementAssertion"]] = None
    element_tests: Optional[Dict[str, "TestCollectionElementAssertion"]] = None


class TestCollectionDatasetElementAssertions(BaseTestOutputModel):
    pass


TestCollectionElementAssertion = Union[
    TestCollectionDatasetElementAssertions, TestCollectionCollectionElementAssertions
]
TestCollectionCollectionElementAssertions.model_rebuild()


def _check_collection_type(v: str) -> str:
    if len(v) == 0:
        raise ValueError("Invalid empty collection_type specified.")
    collection_levels = v.split(":")
    for collection_level in collection_levels:
        if collection_level not in ["list", "paired", "paired_or_unpaired", "record", "sample_sheet"]:
            raise ValueError(f"Invalid collection_type specified [{v}]")
    return v


CollectionType = Annotated[Optional[str], AfterValidator(_check_collection_type)]


class CollectionAttributes(StrictModel):
    collection_type: CollectionType = None


class TestCollectionOutputAssertions(StrictModel):
    class_: Optional[Literal["Collection"]] = Field("Collection", alias="class")
    elements: Optional[Dict[str, TestCollectionElementAssertion]] = None
    element_tests: Optional[Dict[str, "TestCollectionElementAssertion"]] = None
    element_count: Optional[int] = None
    attributes: Optional[CollectionAttributes] = None
    collection_type: CollectionType = None


TestOutputLiteral = Union[bool, int, float, str]

TestOutputAssertions = Union[TestCollectionOutputAssertions, TestDataOutputAssertions, TestOutputLiteral]


TestInputValue = Union[bool, int, float, str, List[Any], Dict[str, Any]]


class YamlTestCredentialValue(StrictModel):
    name: Annotated[str, Field(description="Name of the credential variable or secret.")]
    value: Annotated[str, Field(description="Value of the credential variable or secret.")]


class YamlTestCredential(StrictModel):
    name: Annotated[str, Field(description="Name of the credentials group.")]
    variables: Annotated[
        List[YamlTestCredentialValue],
        Field(description="Variables exposed to the tool environment."),
    ] = []
    secrets: Annotated[
        List[YamlTestCredentialValue],
        Field(description="Secrets exposed to the tool environment."),
    ] = []
    version: Annotated[
        Optional[str],
        Field(description="Version of the credential definition."),
    ] = None


class YamlToolTest(BaseModel):
    """In-tool test case as authored in YAML tool fixtures."""

    model_config = ConfigDict(extra="forbid")

    doc: Annotated[Optional[str], Field(description="Human-readable description of this test case.")] = None
    inputs: Annotated[
        Optional[Dict[str, TestInputValue]],
        Field(description="Mapping of input parameter names to test values."),
    ] = None
    outputs: Annotated[
        Dict[str, TestOutputAssertions],
        Field(description="Mapping of output names to expected values or assertions."),
    ] = {}
    assert_stdout: Annotated[
        Optional[assertions],
        Field(description="Assertions to apply against the tool's standard output."),
    ] = None
    assert_stderr: Annotated[
        Optional[assertions],
        Field(description="Assertions to apply against the tool's standard error."),
    ] = None
    command: Annotated[
        Optional[assertions],
        Field(description="Assertions to apply against the executed command line."),
    ] = None
    expect_exit_code: Annotated[
        Optional[int],
        Field(description="Expected process exit code."),
    ] = None
    expect_failure: Annotated[
        Optional[bool],
        Field(description="If true, the tool is expected to produce an error."),
    ] = None
    expect_test_failure: Annotated[
        Optional[bool],
        Field(description="If true, the test itself is expected to fail."),
    ] = None
    credentials: Annotated[
        Optional[List[YamlTestCredential]],
        Field(description="Credentials to inject for this test case."),
    ] = None


UserToolSource.model_rebuild()
YamlToolSource.model_rebuild()

JobDict = Dict[str, Any]


class TestJob(StrictModel):
    doc: Optional[str]
    job: JobDict
    outputs: Dict[str, TestOutputAssertions]
    expect_failure: Optional[bool] = False


Tests = RootModel[List[TestJob]]

# TODO: typed dict versions of all thee above for verify code - make this Dict[str, Any] here more
# specific.
OutputChecks = Union[TestOutputLiteral, Dict[str, Any]]
OutputsDict = Dict[str, OutputChecks]


class JobTestDict(TypedDict):
    doc: NotRequired[str]
    job: NotRequired[JobDict]
    expect_failure: NotRequired[bool]
    outputs: OutputsDict


TestDicts = List[JobTestDict]
