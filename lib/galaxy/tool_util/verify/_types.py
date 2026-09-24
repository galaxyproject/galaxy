"""Types used by interactor and test case processor."""

from typing import (
    Any,
    Literal,
)

from typing_extensions import (
    NotRequired,
    TypedDict,
)

from galaxy.tool_util.parser.interface import (
    TestSourceTestOutputColllection,
    ToolSourceTestOutputs,
)
from galaxy.tool_util_models.testing_types import (
    AssertionList,
    DirectCredential,
)

# legacy inputs for working with POST /api/tools
# + inputs that have been processed with parse.py and expanded out
ExpandedToolInputs = dict[str, Any]
# + ExpandedToolInputs where any model objects have been json-ified with to_dict()
ExpandedToolInputsJsonified = dict[str, Any]

# modern inputs for working with POST /api/jobs*
RawTestToolRequest = dict[str, Any]

ExtraFileInfoDictT = dict[str, Any]
RequiredFileTuple = tuple[str, ExtraFileInfoDictT]
RequiredFilesT = list[RequiredFileTuple]
RequiredDataTablesT = list[str]
RequiredLocFileT = list[str]
ValueStateRepresentationT = Literal["test_case_xml", "test_case_json"]


class ToolTestDescriptionDict(TypedDict):
    tool_id: str
    tool_version: str | None
    name: str
    test_index: int
    inputs: ExpandedToolInputsJsonified
    request: NotRequired[dict[str, Any] | None]
    request_schema: NotRequired[dict[str, Any] | None]
    outputs: ToolSourceTestOutputs
    output_collections: list[TestSourceTestOutputColllection]
    stdout: AssertionList | None
    stderr: AssertionList | None
    expect_exit_code: int | None
    expect_failure: bool
    expect_test_failure: bool
    num_outputs: int | None
    command_line: AssertionList | None
    command_version: AssertionList | None
    required_files: list[Any]
    required_data_tables: list[Any]
    required_loc_files: list[str]
    error: bool
    exception: str | None
    request_unavailable_reason: NotRequired[str | None]
    maxseconds: NotRequired[int | None]
    value_state_representation: NotRequired[ValueStateRepresentationT]
    credentials: NotRequired[list[DirectCredential] | None]
