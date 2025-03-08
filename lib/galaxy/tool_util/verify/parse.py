import logging
import os
import traceback
from typing import (
    Any,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)

from packaging.version import Version

from galaxy.tool_util.parameters import (
    input_models_for_tool_source,
    test_case_state as case_state,
)
from galaxy.tool_util.parser.interface import (
    InputSource,
    TestCollectionDef,
    ToolSource,
    ToolSourceTest,
    ToolSourceTestInputs,
    ToolSourceTests,
)
from galaxy.tool_util.parser.util import (
    boolean_is_checked,
    boolean_true_and_false_values,
    parse_tool_version_with_defaults,
)
from galaxy.tool_util.parser.xml import __parse_assert_list_from_elem
from galaxy.tool_util.verify.assertion_models import relaxed_assertion_list
from galaxy.tool_util.verify.interactor import (
    InvalidToolTestDict,
    ToolTestDescription,
    ValidToolTestDict,
)
from galaxy.util import (
    string_as_bool,
    string_as_bool_or_none,
    unicodify,
)
from ._types import (
    ExpandedToolInputs,
    ExtraFileInfoDictT,
    RequiredDataTablesT,
    RequiredFilesT,
    RequiredLocFileT,
)

log = logging.getLogger(__name__)

AnyParamContext = Union["ParamContext", "RootParamContext"]


def parse_tool_test_descriptions(
    tool_source: ToolSource, tool_guid: Optional[str] = None
) -> Iterable[ToolTestDescription]:
    """
    Build ToolTestDescription objects for each test description.
    """
    validate_on_load = Version(tool_source.parse_profile()) >= Version("24.2")
    raw_tests_dict: ToolSourceTests = tool_source.parse_tests_to_dict()
    tests: List[ToolTestDescription] = []

    profile = tool_source.parse_profile()
    for i, raw_test_dict in enumerate(raw_tests_dict.get("tests", [])):
        validation_exception: Optional[Exception] = None
        if validate_on_load:
            tool_parameter_bundle = input_models_for_tool_source(tool_source)
            try:
                case_state(raw_test_dict, tool_parameter_bundle.parameters, profile, validate=True)
            except Exception as e:
                # TOOD: restrict types of validation exceptions a bit probably?
                validation_exception = e

        if validation_exception:
            tool_id, tool_version = _tool_id_and_version(tool_source, tool_guid)
            test = ToolTestDescription.from_tool_source_dict(
                InvalidToolTestDict(
                    {
                        "tool_id": tool_id,
                        "tool_version": tool_version,
                        "test_index": i,
                        "inputs": {},
                        "error": True,
                        "exception": unicodify(validation_exception),
                        "maxseconds": None,
                    }
                )
            )
        else:
            test = _description_from_tool_source(tool_source, raw_test_dict, i, tool_guid)
        tests.append(test)
    return tests


def _description_from_tool_source(
    tool_source: ToolSource, raw_test_dict: ToolSourceTest, test_index: int, tool_guid: Optional[str]
) -> ToolTestDescription:
    required_files: RequiredFilesT = []
    required_data_tables: RequiredDataTablesT = []
    required_loc_files: RequiredLocFileT = []

    num_outputs = raw_test_dict.get("expect_num_outputs", None)
    if num_outputs:
        num_outputs = int(num_outputs)
    maxseconds = raw_test_dict.get("maxseconds", None)
    if maxseconds is not None:
        maxseconds = int(maxseconds)

    tool_id, tool_version = _tool_id_and_version(tool_source, tool_guid)
    processed_test_dict: Union[ValidToolTestDict, InvalidToolTestDict]
    try:
        processed_inputs = _process_raw_inputs(
            tool_source,
            input_sources(tool_source),
            raw_test_dict["inputs"],
            required_files,
            required_data_tables,
            required_loc_files,
        )
        processed_test_dict = ValidToolTestDict(
            {
                "inputs": processed_inputs,
                "outputs": raw_test_dict["outputs"],
                "output_collections": raw_test_dict["output_collections"],
                "num_outputs": num_outputs,
                "command_line": raw_test_dict.get("command", None),
                "command_version": raw_test_dict.get("command_version", None),
                "stdout": raw_test_dict.get("stdout", None),
                "stderr": raw_test_dict.get("stderr", None),
                "expect_exit_code": raw_test_dict.get("expect_exit_code", None),
                "expect_failure": raw_test_dict.get("expect_failure", False),
                "expect_test_failure": raw_test_dict.get("expect_test_failure", False),
                "required_files": required_files,
                "required_data_tables": required_data_tables,
                "required_loc_files": required_loc_files,
                "tool_id": tool_id,
                "tool_version": tool_version,
                "test_index": test_index,
                "maxseconds": maxseconds,
                "error": False,
            }
        )
    except Exception:
        processed_test_dict = InvalidToolTestDict(
            {
                "tool_id": tool_id,
                "tool_version": tool_version,
                "test_index": test_index,
                "inputs": {},
                "error": True,
                "exception": unicodify(traceback.format_exc()),
                "maxseconds": maxseconds,
            }
        )

    return ToolTestDescription.from_tool_source_dict(processed_test_dict)


def _tool_id_and_version(tool_source: ToolSource, tool_guid: Optional[str]) -> Tuple[str, str]:
    tool_id = tool_guid or tool_source.parse_id()
    assert tool_id
    tool_version = parse_tool_version_with_defaults(tool_id, tool_source)
    return tool_id, tool_version


def _process_raw_inputs(
    tool_source: ToolSource,
    input_sources: List[InputSource],
    raw_inputs: ToolSourceTestInputs,
    required_files: RequiredFilesT,
    required_data_tables: RequiredDataTablesT,
    required_loc_files: RequiredLocFileT,
    parent_context: Optional[AnyParamContext] = None,
) -> ExpandedToolInputs:
    """
    Recursively expand flat list of inputs into "tree" form of flat list
    (| using to nest to new levels) structure and expand dataset
    information as proceeding to populate self.required_files.
    """
    profile = tool_source.parse_profile()
    allow_legacy_test_case_parameters = Version(profile) <= Version("24.1")
    parent_context = parent_context or RootParamContext(allow_unqualified_access=allow_legacy_test_case_parameters)
    expanded_inputs: ExpandedToolInputs = {}
    for input_source in input_sources:
        input_type = input_source.parse_input_type()
        name = input_source.parse_name()
        if input_type == "conditional":
            cond_context = ParamContext(name=name, parent_context=parent_context)
            test_param_input_source = input_source.parse_test_input_source()
            case_name = test_param_input_source.parse_name()
            case_context = ParamContext(name=case_name, parent_context=cond_context)
            raw_input_dict = case_context.extract_value(raw_inputs)
            case_value = raw_input_dict["value"] if raw_input_dict else None
            case_when, case_input_sources = _matching_case_for_value(
                tool_source, input_source, test_param_input_source, case_value, allow_legacy_test_case_parameters
            )
            if case_input_sources:
                for case_input_source in case_input_sources.parse_input_sources():
                    case_inputs = _process_raw_inputs(
                        tool_source,
                        [case_input_source],
                        raw_inputs,
                        required_files,
                        required_data_tables,
                        required_loc_files,
                        parent_context=cond_context,
                    )
                    expanded_inputs.update(case_inputs)
                expanded_case_value = split_if_str(case_when)
                if case_value is not None:
                    # A bit tricky here - we are growing inputs with value
                    # that may be implicit (i.e. not defined by user just
                    # a default defined in tool). So we do not want to grow
                    # expanded_inputs and risk repeat block viewing this
                    # as a new instance with value defined and hence enter
                    # an infinite loop - hence the "case_value is not None"
                    # check.
                    processed_value = _process_simple_value(
                        test_param_input_source,
                        expanded_case_value,
                        required_data_tables,
                        required_loc_files,
                        allow_legacy_test_case_parameters,
                    )
                    expanded_inputs[case_context.for_state()] = processed_value
        elif input_type == "section":
            context = ParamContext(name=name, parent_context=parent_context)
            page_source = input_source.parse_nested_inputs_source()
            for section_input_source in page_source.parse_input_sources():
                expanded_input = _process_raw_inputs(
                    tool_source,
                    [section_input_source],
                    raw_inputs,
                    required_files,
                    required_data_tables,
                    required_loc_files,
                    parent_context=context,
                )
                if expanded_input:
                    expanded_inputs.update(expanded_input)
        elif input_type == "repeat":
            repeat_index = 0
            while True:
                context = ParamContext(name=name, parent_context=parent_context, index=repeat_index)
                updated = False
                page_source = input_source.parse_nested_inputs_source()
                for r_value in page_source.parse_input_sources():
                    expanded_input = _process_raw_inputs(
                        tool_source,
                        [r_value],
                        raw_inputs,
                        required_files,
                        required_data_tables,
                        required_loc_files,
                        parent_context=context,
                    )
                    if expanded_input:
                        expanded_inputs.update(expanded_input)
                        updated = True
                if not updated:
                    break
                repeat_index += 1
        else:
            context = ParamContext(name=name, parent_context=parent_context)
            raw_input_dict = context.extract_value(raw_inputs)
            param_type = input_source.get("type")
            if raw_input_dict:
                name = raw_input_dict["name"]
                param_value = raw_input_dict["value"]
                param_extra = raw_input_dict["attributes"]
                location = param_extra.get("location")
                if param_type != "text":
                    param_value = split_if_str(param_value)
                if param_type == "data":
                    if location and input_source.get_bool("multiple", False):
                        # We get the input/s from the location which can be a list of urls separated by commas
                        locations = split_if_str(location)
                        param_value = []
                        for location in locations:
                            v = os.path.basename(location)
                            param_value.append(v)
                            # param_extra should contain only the corresponding location
                            extra = dict(param_extra)
                            extra["location"] = location
                            _add_uploaded_dataset(context.for_state(), v, extra, input_source, required_files)
                    else:
                        if not isinstance(param_value, list):
                            param_value = [param_value]
                        for v in param_value:
                            _add_uploaded_dataset(context.for_state(), v, param_extra, input_source, required_files)
                    processed_value = param_value
                elif param_type == "data_collection":
                    assert "collection" in param_extra
                    collection_dict = param_extra["collection"]
                    collection_def = TestCollectionDef.from_dict(collection_dict)
                    for input_dict in collection_def.collect_inputs():
                        name = input_dict["name"]
                        value = input_dict["value"]
                        attributes = input_dict["attributes"]
                        require_file(name, value, attributes, required_files)
                    processed_value = collection_def
                else:
                    processed_value = _process_simple_value(
                        input_source,
                        param_value,
                        required_data_tables,
                        required_loc_files,
                        allow_legacy_test_case_parameters,
                    )
                expanded_inputs[context.for_state()] = processed_value
    return expanded_inputs


def input_sources(tool_source: ToolSource) -> List[InputSource]:
    input_sources = []
    pages_source = tool_source.parse_input_pages()
    if pages_source.inputs_defined:
        for page_source in pages_source.page_sources:
            for input_source in page_source.parse_input_sources():
                input_sources.append(input_source)
    return input_sources


class ParamContext:
    """Capture the context of a parameter's position within the inputs tree of a tool."""

    parent_context: AnyParamContext
    name: str
    # if in a repeat - what position in the repeat
    index: Optional[int]
    # we've encouraged the use of repeat/conditional tags to capture fully qualified paths
    # to parameters in tools. This brings the parameters closer to the API and prevents a
    # variety of possible ambiguities. Disable this for newer tools.
    allow_unqualified_access: bool

    def __init__(self, name: str, parent_context: AnyParamContext, index: Optional[int] = None):
        self.parent_context = parent_context
        self.name = name
        self.index = None if index is None else int(index)
        self.allow_unqualified_access = parent_context.allow_unqualified_access

    def for_state(self) -> str:
        name = self.name if self.index is None else "%s_%d" % (self.name, self.index)
        parent_for_state = self.parent_context.for_state()
        if parent_for_state:
            return f"{parent_for_state}|{name}"
        else:
            return name

    def __str__(self) -> str:
        return f"Context[for_state={self.for_state()}]"

    def param_names(self):
        if not self.allow_unqualified_access:
            yield self.for_state()
        else:
            for parent_context_param in self.parent_context.param_names():
                if self.index is not None:
                    yield "%s|%s_%d" % (parent_context_param, self.name, self.index)
                else:
                    yield f"{parent_context_param}|{self.name}"
            if self.index is not None:
                yield "%s_%d" % (self.name, self.index)
            else:
                yield self.name

    def extract_value(self, raw_inputs: ToolSourceTestInputs):
        for param_name in self.param_names():
            value = self.__raw_param_found(param_name, raw_inputs)
            if value:
                return value
        return None

    def __raw_param_found(self, param_name: str, raw_inputs: ToolSourceTestInputs):
        index = None
        for i, raw_input_dict in enumerate(raw_inputs):
            if raw_input_dict["name"] == param_name:
                index = i
        if index is not None:
            raw_input_dict = raw_inputs[index]
            del raw_inputs[index]
            return raw_input_dict
        else:
            return None


class RootParamContext:
    allow_unqualified_access: bool

    def __init__(self, allow_unqualified_access: bool):
        self.allow_unqualified_access = allow_unqualified_access

    def for_state(self):
        return ""

    def param_names(self):
        return []

    def get_index(self):
        return 0


def _process_simple_value(
    param: InputSource,
    param_value: Any,
    required_data_tables: RequiredDataTablesT,
    required_loc_files: RequiredLocFileT,
    allow_legacy_test_case_parameters: bool,
):
    input_type = param.get("type")
    if input_type == "select":
        # Tests may specify values as either raw value or the value
        # as they appear in the list - the API doesn't and shouldn't
        # accept the text value - so we need to convert the text
        # into the form value.
        def process_param_value(param_value):
            found_value = False
            value_for_text = None
            if allow_legacy_test_case_parameters:
                # we used to allow selections based on text - this
                # should really be only based on key
                static_options = param.parse_static_options()
                for text, opt_value, _ in static_options:
                    if param_value == opt_value:
                        found_value = True
                    if value_for_text is None and param_value == text:
                        value_for_text = opt_value
            dynamic_options = param.parse_dynamic_options()
            if dynamic_options:
                data_table_name = dynamic_options.get_data_table_name()
                index_file_name = dynamic_options.get_index_file_name()
                if data_table_name:
                    required_data_tables.append(data_table_name)
                elif index_file_name:
                    required_loc_files.append(index_file_name)
            if not found_value and value_for_text is not None:
                processed_value = value_for_text
            else:
                processed_value = param_value
            return processed_value

        # Do replacement described above for lists or singleton
        # values.
        if isinstance(param_value, list):
            processed_value = list(map(process_param_value, param_value))
        else:
            processed_value = process_param_value(param_value)
    elif input_type == "boolean":
        # Like above, tests may use the tool define values of simply
        # true/false.
        processed_value = _process_bool_param_value(param, param_value, allow_legacy_test_case_parameters)
    else:
        processed_value = param_value
    return processed_value


def _matching_case_for_value(
    tool_source: ToolSource,
    cond: InputSource,
    test_param: InputSource,
    declared_value: Any,
    allow_legacy_test_case_parameters: bool,
):
    tool_id = tool_source.parse_id()
    cond_name = cond.parse_name()

    assert test_param.parse_input_type() == "param"
    test_param_type = test_param.get("type")

    if test_param_type == "boolean":
        if declared_value is None:
            # No explicit value for param in test case, determine from default
            query_value = boolean_is_checked(test_param)
        else:
            query_value = _process_bool_param_value(test_param, declared_value, allow_legacy_test_case_parameters)

        def matches_declared_value(case_value):
            return _process_bool_param_value(test_param, case_value, allow_legacy_test_case_parameters) == query_value

    elif test_param_type == "select":
        static_options = test_param.parse_static_options()
        if declared_value is not None:
            # Test case supplied explicit value to check against.

            def matches_declared_value(case_value):
                return case_value == declared_value

        elif static_options:
            # No explicit value in test case, not much to do if options are dynamic but
            # if static options are available can find the one specified as default or
            # fallback on top most option (like GUI).

            for name, _, selected in static_options:
                if selected:
                    default_option = name
            else:
                first_option = static_options[0]
                first_option_value = first_option[1]
                default_option = first_option_value

            def matches_declared_value(case_value):
                return case_value == default_option

        else:
            # No explicit value for this param and cannot determine a
            # default - give up. Previously this would just result in a key
            # error exception.
            msg = f"Failed to find test parameter value specification required for conditional {cond_name}"
            raise Exception(msg)
    else:
        msg = f"Invalid conditional test type found {test_param_type}"
        raise Exception(msg)

    # Check the tool's defined cases against predicate to determine
    # selected or default.
    for case_when, case_input_sources in cond.parse_when_input_sources():
        if matches_declared_value(case_when):
            return case_when, case_input_sources
    else:
        msg_template = "%s - Failed to find case matching value (%s) for test parameter specification for conditional %s. Remainder of test behavior is unspecified."
        msg = msg_template % (tool_id, declared_value, cond_name)
        log.info(msg)
    return None


def _add_uploaded_dataset(
    name: str,
    value: Optional[str],
    extra: ExtraFileInfoDictT,
    input_parameter: InputSource,
    required_files: RequiredFilesT,
) -> Optional[str]:
    if value is None:
        assert (
            input_parameter.parse_optional() or "composite_data" in extra
        ), f"{name} is not optional. You must provide a valid filename."
        return value
    return require_file(name, value, extra, required_files)


def require_file(name: str, value: str, extra: ExtraFileInfoDictT, required_files: RequiredFilesT) -> str:
    if (value, extra) not in required_files:
        required_files.append((value, extra))  # these files will be uploaded
    name_changes = [att for att in extra.get("edit_attributes", []) if att.get("type") == "name"]
    if name_changes:
        name_change = name_changes[-1].get("value")  # only the last name change really matters
        value = str(name_change)  # change value for select to renamed uploaded file for e.g. composite dataset
    else:
        for end in [".zip", ".gz"]:
            if value.endswith(end):
                value = value[: -len(end)]
                break
        value = os.path.basename(value)  # if uploading a file in a path other than root of test-data
    return value


def _process_bool_param_value(
    input_source: InputSource, param_value: Any, allow_legacy_test_case_parameters: bool
) -> Any:
    truevalue, falsevalue = boolean_true_and_false_values(input_source)
    optional = input_source.parse_optional()
    return process_bool_param_value(truevalue, falsevalue, optional, param_value, allow_legacy_test_case_parameters)


def process_bool_param_value(
    truevalue: str, falsevalue: str, optional: bool, param_value: Any, allow_legacy_test_case_parameters: bool
) -> Any:
    was_list = False
    if isinstance(param_value, list):
        was_list = True
        param_value = param_value[0]

    if allow_legacy_test_case_parameters and truevalue == param_value:
        processed_value = True
    elif allow_legacy_test_case_parameters and falsevalue == param_value:
        processed_value = False
    else:
        if optional:
            processed_value = string_as_bool_or_none(param_value)
        else:
            processed_value = string_as_bool(param_value)
    return [processed_value] if was_list else processed_value


def split_if_str(value):
    split = isinstance(value, str)
    if split:
        value = value.split(",")
    return value


# convert the sort internal structure used by the tool library {tag: string, attributes: dict, children: []}
# into the YAML structure consumed by the test framework {that: string, **atributes}
def tag_structure_to_that_structure(raw_assert):
    as_json = {"that": raw_assert["tag"], **raw_assert.get("attributes", {})}
    children = raw_assert.get("children")
    if children:
        as_json["children"] = list(map(tag_structure_to_that_structure, children))
    return as_json


def assertion_xml_els_to_models(asserts_raw) -> relaxed_assertion_list:
    asserts_raw = __parse_assert_list_from_elem(asserts_raw)

    to_yaml_assertions = []
    for raw_assert in asserts_raw or []:
        to_yaml_assertions.append(tag_structure_to_that_structure(raw_assert))
    return relaxed_assertion_list.model_validate(to_yaml_assertions)
