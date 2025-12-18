"""Types used by interactor and test case processor."""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from typing_extensions import (
    NotRequired,
    TypedDict,
)

from galaxy.tool_util.parser.interface import (
    AssertionList,
    TestSourceTestOutputColllection,
    ToolSourceTestOutputs,
)

# legacy inputs for working with POST /api/tools
# + inputs that have been processed with parse.py and expanded out
ExpandedToolInputs = Dict[str, Any]
# + ExpandedToolInputs where any model objects have been json-ified with to_dict()
ExpandedToolInputsJsonified = Dict[str, Any]

# modern inputs for working with POST /api/jobs*
RawTestToolRequest = Dict[str, Any]

ExtraFileInfoDictT = Dict[str, Any]
RequiredFileTuple = Tuple[str, ExtraFileInfoDictT]
RequiredFilesT = List[RequiredFileTuple]
RequiredDataTablesT = List[str]
RequiredLocFileT = List[str]


class ToolTestDescriptionDict(TypedDict):
    tool_id: str
    tool_version: Optional[str]
    name: str
    test_index: int
    inputs: ExpandedToolInputsJsonified
    request: NotRequired[Optional[Dict[str, Any]]]
    request_schema: NotRequired[Optional[Dict[str, Any]]]
    outputs: ToolSourceTestOutputs
    output_collections: List[TestSourceTestOutputColllection]
    stdout: Optional[AssertionList]
    stderr: Optional[AssertionList]
    expect_exit_code: Optional[int]
    expect_failure: bool
    expect_test_failure: bool
    num_outputs: Optional[int]
    command_line: Optional[AssertionList]
    command_version: Optional[AssertionList]
    required_files: List[Any]
    required_data_tables: List[Any]
    required_loc_files: List[str]
    error: bool
    exception: Optional[str]
    maxseconds: NotRequired[Optional[int]]
