"""Define the ParsedTool model representing metadata extracted from a tool's source.

This is abstraction exported by newer tool shed APIS (circa 2024) and should be sufficient
for reasoning about tool state externally from Galaxy.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from pydantic import (
    AfterValidator,
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
)
from typing_extensions import (
    Annotated,
    Literal,
    NotRequired,
    TypedDict,
)

from .parameters import (
    input_models_for_tool_source,
    ToolParameterT,
)
from .parser.interface import (
    Citation,
    HelpContent,
    OutputCompareType,
    ToolSource,
    XrefDict,
)
from .parser.output_models import (
    from_tool_source,
    ToolOutput,
)
from .verify.assertion_models import assertions


class ParsedTool(BaseModel):
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


def parse_tool(tool_source: ToolSource) -> ParsedTool:
    return parse_tool_custom(tool_source, ParsedTool)


P = TypeVar("P", bound=ParsedTool)


def parse_tool_custom(tool_source: ToolSource, model_type: Type[P]) -> P:
    id = tool_source.parse_id()
    version = tool_source.parse_version()
    name = tool_source.parse_name()
    description = tool_source.parse_description()
    inputs = input_models_for_tool_source(tool_source).parameters
    outputs = from_tool_source(tool_source)
    citations = tool_source.parse_citations()
    license = tool_source.parse_license()
    profile = tool_source.parse_profile()
    edam_operations = tool_source.parse_edam_operations()
    edam_topics = tool_source.parse_edam_topics()
    xrefs = tool_source.parse_xrefs()
    help = tool_source.parse_help()

    return model_type(
        id=id,
        version=version,
        name=name,
        description=description,
        profile=profile,
        inputs=inputs,
        outputs=outputs,
        license=license,
        citations=citations,
        edam_operations=edam_operations,
        edam_topics=edam_topics,
        xrefs=xrefs,
        help=help,
    )


class StrictModel(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
    )


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
        if collection_level not in ["list", "paired"]:
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


class TestJobDict(TypedDict):
    doc: NotRequired[str]
    job: NotRequired[JobDict]
    expect_failure: NotRequired[bool]
    outputs: OutputsDict


TestDicts = List[TestJobDict]
