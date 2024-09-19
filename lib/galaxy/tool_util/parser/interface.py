import fnmatch
import os
import re
from abc import (
    ABCMeta,
    abstractmethod,
)
from os.path import join
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
    Union,
)

import packaging.version
from pydantic import BaseModel
from typing_extensions import (
    Literal,
    NotRequired,
    TypedDict,
)

from galaxy.util import Element
from galaxy.util.path import safe_walk
from .util import _parse_name

if TYPE_CHECKING:
    from galaxy.tool_util.deps.requirements import (
        ContainerDescription,
        ResourceRequirement,
        ToolRequirements,
    )

NOT_IMPLEMENTED_MESSAGE = "Galaxy tool format does not yet support this tool feature."


class AssertionDict(TypedDict):
    tag: str
    attributes: Dict[str, Any]
    children: "AssertionList"


AssertionList = Optional[List[AssertionDict]]
XmlInt = Union[str, int]


class ToolSourceTestOutputAttributes(TypedDict):
    object: NotRequired[Optional[Any]]
    compare: str
    lines_diff: int
    delta: int
    delta_frac: Optional[float]
    sort: bool
    decompress: bool
    location: NotRequired[Optional[str]]
    ftype: NotRequired[Optional[str]]
    eps: float
    metric: str
    pin_labels: Optional[Any]
    count: Optional[int]
    metadata: Dict[str, Any]
    md5: Optional[str]
    checksum: Optional[str]
    primary_datasets: Dict[str, Any]
    elements: Dict[str, Any]
    assert_list: AssertionList
    extra_files: List[Dict[str, Any]]


class ToolSourceTestOutput(TypedDict):
    name: str
    value: Optional[str]
    attributes: ToolSourceTestOutputAttributes


# The unfortunate 'attrib = dict(param_elem.attrib)' makes this difficult to type.
ToolSourceTestInputAttributes = Dict[str, Any]


class ToolSourceTestInput(TypedDict):
    name: str
    value: Optional[Any]
    attributes: ToolSourceTestInputAttributes


ToolSourceTestInputs = List[ToolSourceTestInput]
ToolSourceTestOutputs = List[ToolSourceTestOutput]
TestSourceTestOutputColllection = Any


class ToolSourceTest(TypedDict):
    inputs: ToolSourceTestInputs
    outputs: ToolSourceTestOutputs
    output_collections: List[TestSourceTestOutputColllection]
    stdout: AssertionList
    stderr: AssertionList
    expect_exit_code: Optional[XmlInt]
    expect_failure: bool
    expect_test_failure: bool
    maxseconds: Optional[XmlInt]
    expect_num_outputs: Optional[XmlInt]
    command: AssertionList
    command_version: AssertionList


class ToolSourceTests(TypedDict):
    tests: List[ToolSourceTest]


class XrefDict(TypedDict):
    value: str
    reftype: str


class Citation(BaseModel):
    type: str
    content: str


class HelpContent(BaseModel):
    format: Literal["restructuredtext", "plain_text", "markdown"]
    content: str


class ToolSource(metaclass=ABCMeta):
    """This interface represents an abstract source to parse tool
    information from.
    """

    language: str

    @abstractmethod
    def parse_id(self) -> Optional[str]:
        """Parse an ID describing the abstract tool. This is not the
        GUID tracked by the tool shed but the simple id (there may be
        multiple tools loaded in Galaxy with this same simple id).
        """

    @abstractmethod
    def parse_version(self) -> Optional[str]:
        """Parse a version describing the abstract tool."""

    def parse_tool_module(self):
        """Load Tool class from a custom module. (Optional).

        If not None, return pair containing module and class (as strings).
        """
        return None

    def parse_action_module(self):
        """Load Tool class from a custom module. (Optional).

        If not None, return pair containing module and class (as strings).
        """
        return None

    def parse_tool_type(self):
        """Load simple tool type string (e.g. 'data_source', 'default')."""
        return None

    @abstractmethod
    def parse_name(self) -> str:
        """Parse a short name for tool (required)."""

    @abstractmethod
    def parse_description(self) -> str:
        """Parse a description for tool. Longer than name, shorted than help.

        We parse this out as "" if it isn't explicitly declared.
        """

    def parse_edam_operations(self) -> List[str]:
        """Parse list of edam operation codes."""
        return []

    def parse_edam_topics(self) -> List[str]:
        """Parse list of edam topic codes."""
        return []

    @abstractmethod
    def parse_xrefs(self) -> List[XrefDict]:
        """Parse list of external resource URIs and types."""

    def parse_display_interface(self, default):
        """Parse display_interface - fallback to default for the tool type
        (supplied as default parameter) if not specified.
        """
        return default

    def parse_require_login(self, default):
        """Parse whether the tool requires login (as a bool)."""
        return default

    def parse_request_param_translation_elem(self):
        """Return an XML element describing require parameter translation.

        If we wish to support this feature for non-XML based tools this should
        be converted to return some sort of object interface instead of a RAW
        XML element.
        """
        return None

    @abstractmethod
    def parse_command(self):
        """Return string contianing command to run."""

    def parse_expression(self):
        """Return string contianing command to run."""
        return None

    @abstractmethod
    def parse_environment_variables(self):
        """Return environment variable templates to expose."""

    def parse_home_target(self):
        """Should be "job_home", "shared_home", "job_tmp", "pwd", or None."""
        return "pwd"

    def parse_tmp_target(self):
        """Should be "pwd", "shared_home", "job_tmp", "job_tmp_if_explicit", or None."""
        return "job_tmp"

    def parse_tmp_directory_vars(self):
        """Directories to override if a tmp_target is not None."""
        return ["TMPDIR", "TMP", "TEMP"]

    def parse_docker_env_pass_through(self):
        return [
            "GALAXY_SLOTS",
            "GALAXY_MEMORY_MB",
            "GALAXY_MEMORY_MB_PER_SLOT",
            "HOME",
            "_GALAXY_JOB_HOME_DIR",
            "_GALAXY_JOB_TMP_DIR",
        ] + self.parse_tmp_directory_vars()

    @abstractmethod
    def parse_interpreter(self):
        """Return string containing the interpreter to prepend to the command
        (for instance this might be 'python' to run a Python wrapper located
        adjacent to the tool).
        """

    @abstractmethod
    def parse_interactivetool(self):
        """Return InteractiveTool entry point templates to expose."""

    def parse_redirect_url_params_elem(self):
        """Return an XML element describing redirect_url_params.

        If we wish to support this feature for non-XML based tools this should
        be converted to return some sort of object interface instead of a RAW
        XML element.
        """
        return None

    def parse_version_command(self):
        """Parse command used to determine version of primary application
        driving the tool. Return None to not generate or record such a command.
        """
        return None

    def parse_version_command_interpreter(self):
        """Parse command used to determine version of primary application
        driving the tool. Return None to not generate or record such a command.
        """
        return None

    def parse_parallelism(self):
        """Return a galaxy.jobs.ParallismInfo object describing task splitting
        or None.
        """
        return None

    def parse_hidden(self):
        """Return boolean indicating whether tool should be hidden in the tool menu."""
        return False

    def parse_sanitize(self):
        """Return boolean indicating whether tool should be sanitized or not."""
        return True

    def parse_refresh(self):
        """Return boolean indicating ... I have no clue..."""
        return False

    def parse_required_files(self) -> Optional["RequiredFiles"]:
        """Parse explicit RequiredFiles object or return None to let Galaxy decide implicit logic."""
        return None

    @abstractmethod
    def parse_requirements_and_containers(
        self,
    ) -> Tuple["ToolRequirements", List["ContainerDescription"], List["ResourceRequirement"]]:
        """Return triple of ToolRequirement, ContainerDescription and ResourceRequirement lists."""

    @abstractmethod
    def parse_input_pages(self) -> "PagesSource":
        """Return a PagesSource representing inputs by page for tool."""

    def parse_provided_metadata_style(self):
        """Return style of tool provided metadata file (e.g. galaxy.json).

        A value of of "default" indicates the newer galaxy.json style
        (the default for XML-based tools with profile >= 17.09) and a value
        of "legacy" indicates the older galaxy.json style.

        A short description of these two styles can be found at
        https://github.com/galaxyproject/galaxy/pull/4437.
        """
        return "default"

    def parse_provided_metadata_file(self):
        """Return location of provided metadata file (e.g. galaxy.json)."""
        return "galaxy.json"

    @abstractmethod
    def parse_outputs(self, tool):
        """Return a pair of output and output collections ordered
        dictionaries for use by Tool.
        """

    @abstractmethod
    def parse_strict_shell(self):
        """Return True if tool commands should be executed with
        set -e.
        """

    @abstractmethod
    def parse_stdio(self):
        """Builds lists of ToolStdioExitCode and ToolStdioRegex objects
        to describe tool execution error conditions.
        """
        return [], []

    @abstractmethod
    def parse_help(self) -> Optional[HelpContent]:
        """Return help text for tool or None if the tool doesn't define help text.

        The returned object contains the help text and an indication if it is reStructuredText
        (``restructuredtext``), Markdown (``markdown``), or plain text (``plain_text``).
        """

    @abstractmethod
    def parse_profile(self) -> str:
        """Return tool profile version as Galaxy major e.g. 16.01 or 16.04."""

    @abstractmethod
    def parse_license(self) -> Optional[str]:
        """Return license corresponding to tool wrapper."""

    def parse_citations(self) -> List[Citation]:
        """Return a list of citations."""
        return []

    @abstractmethod
    def parse_python_template_version(self) -> Optional[packaging.version.Version]:
        """
        Return minimum python version that the tool template has been developed against.
        """

    def parse_creator(self):
        """Return list of metadata relating to creator/author of tool.

        Result should be list of schema.org data model Person or Organization objects.
        """
        return []

    @property
    def macro_paths(self):
        return []

    @property
    def source_path(self):
        return None

    def paths_and_modtimes(self):
        paths_and_modtimes = {p: os.path.getmtime(p) for p in self.macro_paths}
        if self.source_path:
            paths_and_modtimes[self.source_path] = os.path.getmtime(self.source_path)
        return paths_and_modtimes

    def parse_tests_to_dict(self) -> ToolSourceTests:
        return {"tests": []}

    def __str__(self):
        source_path = self.source_path
        if source_path:
            as_str = f"{self.__class__.__name__}[{source_path}]"
        else:
            as_str = f"{self.__class__.__name__}[In-memory]"
        return as_str

    @abstractmethod
    def to_string(self) -> str:
        """Return the tool source as a string"""


class PagesSource:
    """Contains a list of Pages - each a list of InputSources -
    each item in the outer list representing a page of inputs.
    Pages are deprecated so ideally this outer list will always
    be exactly a singleton.
    """

    def __init__(self, page_sources):
        self.page_sources = page_sources

    @property
    def inputs_defined(self):
        return True


class DynamicOptions(metaclass=ABCMeta):

    def elem(self) -> Element:
        # For things in transition that still depend on XML - provide a way
        # to grab it and just throw an error if feature is attempted to be
        # used with other tool sources.
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)

    @abstractmethod
    def get_data_table_name(self) -> Optional[str]:
        """If dynamic options are loaded from a data table, return the name."""

    @abstractmethod
    def get_index_file_name(self) -> Optional[str]:
        """If dynamic options are loaded from an index file, return the name."""


DrillDownDynamicFilters = Dict[str, Dict[str, dict]]  # {input key: {metadata_key: metadata values}}


class DrillDownDynamicOptions(metaclass=ABCMeta):

    @abstractmethod
    def from_code_block(self) -> Optional[str]:
        """Get a code block to do an eval on."""

    @abstractmethod
    def from_filters(self) -> Optional[DrillDownDynamicFilters]:
        """Get filters to apply to target datasets."""


class InputSource(metaclass=ABCMeta):
    default_optional = False

    def elem(self):
        # For things in transition that still depend on XML - provide a way
        # to grab it and just throw an error if feature is attempted to be
        # used with other tool sources.
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)

    @abstractmethod
    def get(self, key, value=None):
        """Return simple named properties as string for this input source.
        keys to be supported depend on the parameter type.
        """

    @abstractmethod
    def get_bool(self, key, default):
        """Return simple named properties as boolean for this input source.
        keys to be supported depend on the parameter type.
        """

    def parse_label(self):
        return self.get("label")

    def parse_name(self):
        """Return name of an input source
        returns the name or if absent the argument property
        In the latter case, leading dashes are stripped and
        all remaining dashes are replaced by underscores.
        """
        return _parse_name(self.get("name"), self.get("argument"))

    @abstractmethod
    def parse_input_type(self) -> str:
        """Return the type of this input."""

    def parse_help(self):
        return self.get("help")

    def parse_sanitizer_elem(self):
        """Return an XML description of sanitizers. This is a stop gap
        until we can rework galaxy.tools.parameters.sanitize to not
        explicitly depend on XML.
        """
        return None

    def parse_validator_elems(self):
        """Return an XML description of sanitizers. This is a stop gap
        until we can rework galaxy.tools.parameters.validation to not
        explicitly depend on XML.
        """
        return []

    def parse_optional(self, default=None):
        """Return boolean indicating whether parameter is optional."""
        if default is None:
            default = self.default_optional
        return self.get_bool("optional", default)

    def parse_dynamic_options(self) -> Optional[DynamicOptions]:
        """Return an optional element describing dynamic options.

        These options are still very XML based but as they are adapted to the infrastructure, the return
        type here will evolve.
        """
        return None

    def parse_drill_down_dynamic_options(
        self, tool_data_path: Optional[str] = None
    ) -> Optional["DrillDownDynamicOptions"]:
        return None

    def parse_static_options(self) -> List[Tuple[str, str, bool]]:
        """Return list of static options if this is a select type without
        defining a dynamic options.
        """
        return []

    def parse_drill_down_static_options(
        self, tool_data_path: Optional[str] = None
    ) -> Optional[List["DrillDownOptionsDict"]]:
        return None

    def parse_conversion_tuples(self):
        """Return list of (name, extension) to describe explicit conversions."""
        return []

    def parse_nested_inputs_source(self):
        # For repeats
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)

    def parse_test_input_source(self) -> "InputSource":
        # For conditionals
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)

    def parse_when_input_sources(self):
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)

    def parse_default(self) -> Optional[Dict[str, Any]]:
        return None


class PageSource(metaclass=ABCMeta):
    def parse_display(self):
        return None

    @abstractmethod
    def parse_input_sources(self) -> List[InputSource]:
        """Return a list of InputSource objects."""


AnyTestCollectionDefDict = Union["JsonTestCollectionDefDict", "XmlTestCollectionDefDict"]
TestCollectionDefElementObject = Union[AnyTestCollectionDefDict, "ToolSourceTestInput"]
TestCollectionAttributeDict = Dict[str, Any]
CollectionType = str


class TestCollectionDefElementDict(TypedDict):
    element_identifier: str
    element_definition: TestCollectionDefElementObject


class TestCollectionDefElementInternal(TypedDict):
    element_identifier: str
    element_definition: Union["TestCollectionDef", "ToolSourceTestInput"]


# two versions of collection inputs can be parsed out, XmlTestCollectionDefDict is historically
# used by tools and Galaxy internals and exposed in the API via the test definition endpoints for
# tool execution. JsonTestCollectionDefDict is the format consumed by Planemo that mirrors a CWL
# way of defining inputs.
class XmlTestCollectionDefDict(TypedDict):
    model_class: Literal["TestCollectionDef"]
    attributes: TestCollectionAttributeDict
    collection_type: CollectionType
    elements: List[TestCollectionDefElementDict]
    name: str


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
        "collection_type": str,
        "elements": NotRequired[Optional[List[JsonTestCollectionDefElementDict]]],
    },
)
JsonTestCollectionDefCollectionElementDict = TypedDict(
    "JsonTestCollectionDefCollectionElementDict",
    {
        "identifier": str,
        "class": Literal["Collection"],
        "collection_type": str,
        "elements": NotRequired[Optional[List[JsonTestCollectionDefElementDict]]],
    },
)
JsonTestCollectionDefDict = TypedDict(
    "JsonTestCollectionDefDict",
    {
        "class": Literal["Collection"],
        "collection_type": str,
        "elements": NotRequired[Optional[List[JsonTestCollectionDefElementDict]]],
        "name": NotRequired[Optional[str]],
    },
)


def xml_data_input_to_json(xml_input: ToolSourceTestInput) -> "JsonTestDatasetDefDict":
    attributes = xml_input["attributes"]
    as_dict: JsonTestDatasetDefDict = {
        "class": "File",
    }
    value = xml_input["value"]
    if value:
        as_dict["path"] = value
    _copy_if_exists(attributes, as_dict, "location")
    _copy_if_exists(attributes, as_dict, "dbkey")
    _copy_if_exists(attributes, as_dict, "ftype", "filetype")
    _copy_if_exists(attributes, as_dict, "composite_data", only_if_value=True)
    tags = attributes.get("tags")
    if tags:
        as_dict["tags"] = [t.strip() for t in tags.split(",")]
    return as_dict


def _copy_if_exists(attributes, as_dict, name: str, as_name: Optional[str] = None, only_if_value: bool = False):
    if name in attributes:
        value = attributes[name]
        if not value and only_if_value:
            return
        if as_name is None:
            as_name = name
        as_dict[as_name] = value


class TestCollectionDef:
    __test__ = False  # Prevent pytest from discovering this class (issue #12071)
    elements: List[TestCollectionDefElementInternal]

    def __init__(self, attrib, name, collection_type, elements):
        self.attrib = attrib
        self.collection_type = collection_type
        self.elements = elements
        self.name = name

    def _test_format_to_dict(self) -> "BaseJsonTestCollectionDefCollectionElementDict":

        def to_element(xml_element_dict: "TestCollectionDefElementInternal") -> "JsonTestCollectionDefElementDict":
            identifier = xml_element_dict["element_identifier"]
            element_object = xml_element_dict["element_definition"]
            as_dict: JsonTestCollectionDefElementDict

            if isinstance(element_object, TestCollectionDef):
                as_dict = JsonTestCollectionDefCollectionElementDict(
                    identifier=identifier, **element_object._test_format_to_dict()
                )
            else:
                as_dict = JsonTestCollectionDefDatasetElementDict(
                    identifier=identifier,
                    **xml_data_input_to_json(cast(ToolSourceTestInput, element_object)),
                )
            return as_dict

        test_format_dict = BaseJsonTestCollectionDefCollectionElementDict(
            {
                "class": "Collection",
                "elements": list(map(to_element, self.elements)),
                "collection_type": self.collection_type,
            }
        )
        return test_format_dict

    def test_format_to_dict(self) -> JsonTestCollectionDefDict:
        test_format_dict = JsonTestCollectionDefDict(**self._test_format_to_dict())
        if self.name:
            test_format_dict["name"] = self.name
        return test_format_dict

    def to_dict(self) -> XmlTestCollectionDefDict:
        def element_to_dict(element_dict):
            element_identifier, element_def = element_dict["element_identifier"], element_dict["element_definition"]
            if isinstance(element_def, TestCollectionDef):
                element_def = element_def.to_dict()
            return {
                "element_identifier": element_identifier,
                "element_definition": element_def,
            }

        return {
            "model_class": "TestCollectionDef",
            "attributes": self.attrib,
            "collection_type": self.collection_type,
            "elements": list(map(element_to_dict, self.elements or [])),
            "name": self.name,
        }

    @staticmethod
    def from_dict(
        as_dict: Union[AnyTestCollectionDefDict, JsonTestCollectionDefCollectionElementDict]
    ) -> "TestCollectionDef":
        if "model_class" in as_dict:
            xml_as_dict = cast(XmlTestCollectionDefDict, as_dict)
            assert xml_as_dict["model_class"] == "TestCollectionDef"

            def element_from_dict(element_dict) -> TestCollectionDefElementInternal:
                if "element_definition" not in element_dict:
                    raise Exception(f"Invalid element_dict {element_dict}")
                element_def = element_dict["element_definition"]
                if element_def.get("model_class", None) == "TestCollectionDef":
                    element_def = TestCollectionDef.from_dict(element_def)
                return {"element_identifier": element_dict["element_identifier"], "element_definition": element_def}

            return TestCollectionDef(
                attrib=xml_as_dict["attributes"],
                name=xml_as_dict.get("name", "Unnamed Collection"),
                elements=list(map(element_from_dict, xml_as_dict["elements"] or [])),
                collection_type=xml_as_dict["collection_type"],
            )
        else:
            json_as_dict = cast(JsonTestCollectionDefDict, as_dict)

            def element_from_dict_json(
                element_dict: JsonTestCollectionDefElementDict,
            ) -> TestCollectionDefElementInternal:
                element_class = element_dict.get("class")
                identifier = element_dict["identifier"]
                element_def: Union[TestCollectionDef, ToolSourceTestInput]
                if element_class == "Collection":
                    collection_element_dict = cast(JsonTestCollectionDefCollectionElementDict, element_dict)
                    element_def = TestCollectionDef.from_dict(collection_element_dict)
                else:
                    dataset_element_dict = cast(JsonTestCollectionDefDatasetElementDict, element_dict)
                    value = dataset_element_dict["path"]  # todo handle location
                    name = dataset_element_dict.get("name") or "Unnamed Collection"
                    element_def = {"name": name, "value": value, "attributes": {}}
                return TestCollectionDefElementInternal(element_identifier=identifier, element_definition=element_def)

            elements = list(map(element_from_dict_json, json_as_dict.get("elements") or []))
            return TestCollectionDef(
                attrib={},
                name=json_as_dict.get("name") or "Unnamed Collection",
                elements=elements,
                collection_type=json_as_dict["collection_type"],
            )

    def collect_inputs(self):
        inputs = []
        for element in self.elements:
            value = element["element_definition"]
            if isinstance(value, TestCollectionDef):
                inputs.extend(value.collect_inputs())
            else:
                inputs.append(value)
        return inputs


class RequiredFiles:
    def __init__(self, includes: List[Dict], excludes: List[Dict], extend_default_excludes: bool):
        self.includes = includes
        self.excludes = excludes
        self.extend_default_excludes = extend_default_excludes

    @staticmethod
    def from_dict(as_dict):
        extend_default_excludes: bool = as_dict.get("extend_default_excludes", True)
        includes: List = as_dict.get("includes", [])
        excludes: List = as_dict.get("excludes", [])
        return RequiredFiles(includes, excludes, extend_default_excludes)

    def find_required_files(self, tool_directory: str) -> List[str]:
        def matches(ie_list: List, rel_path: str):
            for ie_item in ie_list:
                ie_item_path = ie_item["path"]
                ie_item_type = ie_item.get("path_type", "literal")
                if ie_item_type == "literal":
                    if rel_path == ie_item_path:
                        return True
                elif ie_item_type == "prefix":
                    if rel_path.startswith(ie_item_path):
                        return True
                elif ie_item_type == "glob":
                    if fnmatch.fnmatch(rel_path, ie_item_path):
                        return True
                else:
                    if re.match(ie_item_path, rel_path) is not None:
                        return True
            return False

        excludes = self.excludes
        if self.extend_default_excludes:
            excludes.append({"path": "tool-data", "path_type": "prefix"})
            excludes.append({"path": "test-data", "path_type": "prefix"})
            excludes.append({"path": ".hg", "path_type": "prefix"})

        files: List[str] = []
        for dirpath, _, filenames in safe_walk(tool_directory):
            for filename in filenames:
                rel_path = join(dirpath, filename).replace(tool_directory + os.path.sep, "")
                if matches(self.includes, rel_path) and not matches(self.excludes, rel_path):
                    files.append(rel_path)
        return files


class TestCollectionOutputDef:
    __test__ = False  # Prevent pytest from discovering this class (issue #12071)

    def __init__(self, name, attrib, element_tests):
        self.name = name
        self.collection_type = attrib.get("type", None)
        count = attrib.get("count", None)
        self.count = int(count) if count is not None else None
        self.attrib = attrib
        self.element_tests = element_tests

    @staticmethod
    def from_dict(as_dict):
        return TestCollectionOutputDef(
            name=as_dict["name"],
            attrib=as_dict.get("attributes", {}),
            element_tests=as_dict["element_tests"],
        )

    def to_dict(self):
        return dict(name=self.name, attributes=self.attrib, element_tests=self.element_tests)


class DrillDownOptionsDict(TypedDict):
    name: Optional[str]
    value: str
    options: List["DrillDownOptionsDict"]
    selected: bool
