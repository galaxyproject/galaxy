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
    AnyUrl,
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    model_validator,
    RootModel,
    Tag,
)
from typing_extensions import (
    Annotated,
    Literal,
    NotRequired,
    TypedDict,
)

from ._base import (
    CollectionType,
    StrictModel,
    ToolSourceBaseModel,
)
from .assertions import assertions
from .parameters import ToolParameterT
from .test_job import Job
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


class BaseTestOutputModel(StrictModel):
    model_config = ConfigDict(extra="forbid", title="BaseTestOutputModel")
    file: Annotated[
        Optional[str],
        Field(
            title="File",
            description=(
                "Name of the output file stored in the target `test-data` directory that will be used to "
                "compare against the results of executing the tool via the functional test framework."
            ),
        ),
    ] = None
    path: Annotated[
        Optional[str],
        Field(title="Path", description="Filesystem path to a local output file used for comparison."),
    ] = None
    location: Annotated[
        Optional[AnyUrl],
        Field(
            title="Location",
            description=(
                "URL that points to a remote output file that will be downloaded and used for output "
                "comparison. Use only when the file cannot be included in the `test-data` folder. May be "
                "combined with `file` (downloads when missing on disk) or used alone (filename inferred "
                "from the URL). A `checksum` is also used to verify the download when provided."
            ),
        ),
    ] = None
    ftype: Annotated[
        Optional[str],
        Field(
            title="File Type",
            description=(
                "If specified, this value is checked against the corresponding output's data type. "
                "If these do not match, the test will fail."
            ),
        ),
    ] = None
    sort: Annotated[
        Optional[bool],
        Field(
            title="Sort",
            description=(
                "Applies only if `compare` is `diff`, `re_match` or `re_match_multiline`. Sorts the lines "
                "of the history data set before comparison; for `diff` and `re_match` the local file is "
                "also sorted. Useful for non-deterministic output."
            ),
        ),
    ] = None
    compare: Annotated[
        Optional[OutputCompareType],
        Field(
            title="Compare",
            description="Comparison mode used when matching the output against the reference file.",
        ),
    ] = None
    checksum: Annotated[
        Optional[str],
        Field(
            title="Checksum",
            description=(
                "The target output's checksum should match the value specified here, in the form "
                "`hash_type$hash_value` (e.g. `sha1$8156d7ca0f46ed7abac98f82e36cfaddb2aca041`). Useful "
                "for large static files where uploading the whole file is inconvenient."
            ),
        ),
    ] = None
    metadata: Annotated[
        Optional[Dict[str, Any]],
        Field(
            title="Metadata",
            description="Mapping of metadata keys to expected values for this output.",
        ),
    ] = None
    asserts: Annotated[
        Optional[assertions],
        Field(title="Asserts", description="Assertions about the content of the output."),
    ] = None
    delta: Annotated[
        Optional[int],
        Field(
            title="Delta",
            description=(
                "If `compare` is set to `sim_size`, the maximum allowed absolute size difference (in "
                "bytes) between the generated data set and the reference file in `test-data/`. Default "
                "is 10000 bytes. Can be combined with `delta_frac`."
            ),
        ),
    ] = None
    delta_frac: Annotated[
        Optional[float],
        Field(
            title="Delta Frac",
            description=(
                "If `compare` is set to `sim_size`, the maximum allowed relative size difference between "
                "the generated data set and the reference file in `test-data/`. 0.1 means the generated "
                "file can differ by at most 10%. Default is not to check for relative size difference. "
                "Can be combined with `delta`."
            ),
        ),
    ] = None
    lines_diff: Annotated[
        Optional[int],
        Field(
            title="Lines Diff",
            description=(
                "Applies when `compare` is set to `diff`, `re_match`, or `contains`. For `diff`, the "
                "number of lines of difference to allow (a modified line counts as two: one added, one "
                "removed)."
            ),
        ),
    ] = None
    decompress: Annotated[
        Optional[bool],
        Field(
            title="Decompress",
            description=(
                "If true, decompress files before comparison. Applies to assertions expressed with "
                "`assert_contents` or `compare` set to anything but `sim_size`. Useful for testing "
                "compressed outputs that are non-deterministic despite having deterministic decompressed "
                "contents. By default, only files compressed with bz2, gzip and zip are automatically "
                "decompressed."
            ),
        ),
    ] = None


class TestDataOutputAssertions(BaseTestOutputModel):
    model_config = ConfigDict(extra="forbid", title="TestDataOutputAssertions")
    class_: Optional[Literal["File"]] = Field("File", alias="class", title="Class")


class TestCollectionCollectionElementAssertions(StrictModel):
    model_config = ConfigDict(extra="forbid", title="TestCollectionCollectionElementAssertions")
    class_: Optional[Literal["Collection"]] = Field("Collection", alias="class", title="Class")
    elements: Annotated[
        Optional[Dict[str, "TestCollectionElementAssertion"]],
        Field(title="Elements"),
    ] = None
    element_tests: Annotated[
        Optional[Dict[str, "TestCollectionElementAssertion"]],
        Field(title="Element Tests"),
    ] = None


class TestCollectionDatasetElementAssertions(BaseTestOutputModel):
    model_config = ConfigDict(extra="forbid", title="TestCollectionDatasetElementAssertions")
    class_: Optional[Literal["File"]] = Field("File", alias="class", title="Class")


def _discriminate_collection_element(v):
    if isinstance(v, dict):
        if v.get("class") == "Collection":
            return "Collection"
        return "File"
    if isinstance(v, TestCollectionCollectionElementAssertions):
        return "Collection"
    if isinstance(v, TestCollectionDatasetElementAssertions):
        return "File"
    return None


TestCollectionElementAssertion = Annotated[
    Union[
        Annotated[TestCollectionDatasetElementAssertions, Tag("File")],
        Annotated[TestCollectionCollectionElementAssertions, Tag("Collection")],
    ],
    Discriminator(_discriminate_collection_element),
]
TestCollectionCollectionElementAssertions.model_rebuild()


class CollectionAttributes(StrictModel):
    model_config = ConfigDict(extra="forbid", title="CollectionAttributes")
    collection_type: Annotated[CollectionType, Field(title="Collection Type")] = None


class TestCollectionOutputAssertions(StrictModel):
    model_config = ConfigDict(extra="forbid", title="TestCollectionOutputAssertions")
    class_: Optional[Literal["Collection"]] = Field("Collection", alias="class", title="Class")
    elements: Annotated[
        Optional[Dict[str, TestCollectionElementAssertion]],
        Field(title="Elements"),
    ] = None
    element_tests: Annotated[
        Optional[Dict[str, "TestCollectionElementAssertion"]],
        Field(title="Element Tests"),
    ] = None
    element_count: Annotated[Optional[int], Field(title="Element Count")] = None
    attributes: Annotated[Optional[CollectionAttributes], Field(title="Attributes")] = None
    collection_type: Annotated[CollectionType, Field(title="Collection Type")] = None


TestOutputLiteral = Union[bool, int, float, str]


def _discriminate_output(v):
    if isinstance(v, dict):
        if v.get("class") == "Collection":
            return "Collection"
        return "File"
    if isinstance(v, TestCollectionOutputAssertions):
        return "Collection"
    if isinstance(v, TestDataOutputAssertions):
        return "File"
    if isinstance(v, (bool, int, float, str)):
        return "scalar"
    return None


TestOutputAssertions = Annotated[
    Union[
        Annotated[TestCollectionOutputAssertions, Tag("Collection")],
        Annotated[TestDataOutputAssertions, Tag("File")],
        Annotated[TestOutputLiteral, Tag("scalar")],
    ],
    Discriminator(_discriminate_output),
]


TestInputValue = Union[bool, int, float, str, List[Any], Dict[str, Any]]


class YamlTestCredentialValue(StrictModel):
    model_config = ConfigDict(extra="forbid", title="YamlTestCredentialValue")
    name: Annotated[str, Field(title="Name", description="Name of the credential variable or secret.")]
    value: Annotated[str, Field(title="Value", description="Value of the credential variable or secret.")]


class YamlTestCredential(StrictModel):
    model_config = ConfigDict(extra="forbid", title="YamlTestCredential")
    name: Annotated[str, Field(title="Name", description="Name of the credentials group.")]
    variables: Annotated[
        List[YamlTestCredentialValue],
        Field(title="Variables", description="Variables exposed to the tool environment."),
    ] = []
    secrets: Annotated[
        List[YamlTestCredentialValue],
        Field(title="Secrets", description="Secrets exposed to the tool environment."),
    ] = []
    version: Annotated[
        Optional[str],
        Field(title="Version", description="Version of the credential definition."),
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

# Loose alias retained for TestJobDict / TypedDict consumers where helpers
# still tolerate Dict[str, Any]. The strict, validated shape is `Job` (see
# galaxy.tool_util_models.test_job).
JobDict = Dict[str, Any]


class TestJob(StrictModel):
    model_config = ConfigDict(extra="forbid", title="TestJob")
    doc: Annotated[
        Optional[str],
        Field(title="Doc", description="Describes the purpose of the test."),
    ] = None
    job: Annotated[
        Job,
        Field(
            title="Job",
            description=(
                "Defines the job to execute. Can be a path to a file or an inline dictionary describing "
                "the job inputs."
            ),
        ),
    ]
    outputs: Annotated[
        Dict[str, TestOutputAssertions],
        Field(
            title="Outputs",
            description=(
                "Defines assertions about outputs (datasets, collections or parameters). Each key "
                "corresponds to a labeled output; values are dictionaries describing the expected output."
            ),
        ),
    ]
    expect_failure: Annotated[
        Optional[bool],
        Field(
            title="Expect Failure",
            description="If true, the workflow is expected to produce an error.",
        ),
    ] = False


class Tests(RootModel[List[TestJob]]):
    model_config = ConfigDict(
        title="GalaxyWorkflowTests",
        json_schema_extra={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "description": (
                "Galaxy workflow tests file — a YAML list of test entries asserting the expected "
                "inputs and outputs of a workflow run."
            ),
        },
    )


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
