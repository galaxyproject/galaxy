import logging
import re
import sys
import traceback
import uuid
from math import isinf

from galaxy.tools.deps import requirements
from galaxy.util import string_as_bool, xml_text, xml_to_string
from galaxy.util.odict import odict
from .error_level import StdioErrorLevel
from .interface import (
    InputSource,
    PageSource,
    PagesSource,
    TestCollectionDef,
    TestCollectionOutputDef,
    ToolSource,
    ToolStdioExitCode,
    ToolStdioRegex,
)
from .output_actions import ToolOutputActionGroup
from .output_collection_def import dataset_collector_descriptions_from_elem
from .output_objects import (
    ToolOutput,
    ToolOutputCollection,
    ToolOutputCollectionStructure
)
from .util import (
    aggressive_error_checks,
    error_on_exit_code,
)


log = logging.getLogger(__name__)


class XmlToolSource(ToolSource):
    """ Responsible for parsing a tool from classic Galaxy representation.
    """

    def __init__(self, xml_tree, source_path=None, macro_paths=None):
        self.xml_tree = xml_tree
        self.root = xml_tree.getroot()
        self._source_path = source_path
        self._macro_paths = macro_paths or []
        self.legacy_defaults = self.parse_profile() == "16.01"

    def parse_version(self):
        return self.root.get("version", None)

    def parse_id(self):
        return self.root.get("id")

    def parse_tool_module(self):
        root = self.root
        if root.find("type") is not None:
            type_elem = root.find("type")
            module = type_elem.get('module', 'galaxy.tools')
            cls = type_elem.get('class')
            return module, cls

        return None

    def parse_action_module(self):
        root = self.root
        action_elem = root.find("action")
        if action_elem is not None:
            module = action_elem.get('module')
            cls = action_elem.get('class')
            return module, cls
        else:
            return None

    def parse_tool_type(self):
        root = self.root
        if root.get('tool_type', None) is not None:
            return root.get('tool_type')

    def parse_name(self):
        return self.root.get("name")

    def parse_edam_operations(self):
        edam_ops = self.root.find("edam_operations")
        if edam_ops is None:
            return []
        return [edam_op.text for edam_op in edam_ops.findall("edam_operation")]

    def parse_edam_topics(self):
        edam_topics = self.root.find("edam_topics")
        if edam_topics is None:
            return []
        return [edam_topic.text for edam_topic in edam_topics.findall("edam_topic")]

    def parse_description(self):
        return xml_text(self.root, "description")

    def parse_is_multi_byte(self):
        return self._get_attribute_as_bool("is_multi_byte", self.default_is_multi_byte)

    def parse_display_interface(self, default):
        return self._get_attribute_as_bool("display_interface", default)

    def parse_require_login(self, default):
        return self._get_attribute_as_bool("require_login", default)

    def parse_request_param_translation_elem(self):
        return self.root.find("request_param_translation")

    def parse_command(self):
        command_el = self._command_el
        return ((command_el is not None) and command_el.text) or None

    def parse_environment_variables(self):
        environment_variables_el = self.root.find("environment_variables")
        if environment_variables_el is None:
            return []

        environment_variables = []
        for environment_variable_el in environment_variables_el.findall("environment_variable"):
            definition = {
                "name": environment_variable_el.get("name"),
                "template": environment_variable_el.text,
            }
            environment_variables.append(
                definition
            )
        return environment_variables

    def parse_home_target(self):
        target = "job_home" if self.parse_profile() >= "18.01" else "shared_home"
        command_el = self._command_el
        command_legacy = (command_el is not None) and command_el.get("use_shared_home", None)
        if command_legacy is not None:
            target = "shared_home" if string_as_bool(command_legacy) else "job_home"
        return target

    def parse_tmp_target(self):
        # Default to not touching TMPDIR et. al. but if job_tmp is set
        # in job_conf then do. This is a very conservative approach that shouldn't
        # break or modify any configurations by default.
        return "job_tmp_if_explicit"

    def parse_docker_env_pass_through(self):
        if self.parse_profile() < "18.01":
            return ["GALAXY_SLOTS"]
        else:
            # Pass home, etc...
            return super(XmlToolSource, self).parse_docker_env_pass_through()

    def parse_interpreter(self):
        interpreter = None
        command_el = self._command_el
        if command_el is not None:
            interpreter = command_el.get("interpreter", None)
        if interpreter and not self.legacy_defaults:
            log.warning("Deprecated interpreter attribute on command element is now ignored.")
            interpreter = None
        return interpreter

    def parse_version_command(self):
        version_cmd = self.root.find("version_command")
        if version_cmd is not None:
            return version_cmd.text
        else:
            return None

    def parse_version_command_interpreter(self):
        if self.parse_version_command() is not None:
            version_cmd = self.root.find("version_command")
            version_cmd_interpreter = version_cmd.get("interpreter", None)
            if version_cmd_interpreter:
                return version_cmd_interpreter
        return None

    def parse_parallelism(self):
        parallelism = self.root.find("parallelism")
        parallelism_info = None
        if parallelism is not None and parallelism.get("method"):
            from galaxy.jobs import ParallelismInfo
            return ParallelismInfo(parallelism)
        return parallelism_info

    def parse_hidden(self):
        hidden = xml_text(self.root, "hidden")
        if hidden:
            hidden = string_as_bool(hidden)
        return hidden

    def parse_redirect_url_params_elem(self):
        return self.root.find("redirect_url_params")

    def parse_sanitize(self):
        return self._get_option_value("sanitize", True)

    def parse_refresh(self):
        return self._get_option_value("refresh", False)

    def _get_option_value(self, key, default):
        root = self.root
        for option_elem in root.findall("options"):
            if key in option_elem.attrib:
                return string_as_bool(option_elem.get(key))

        return default

    @property
    def _command_el(self):
        return self.root.find("command")

    def _get_attribute_as_bool(self, attribute, default, elem=None):
        if elem is None:
            elem = self.root
        return string_as_bool(elem.get(attribute, default))

    def parse_requirements_and_containers(self):
        return requirements.parse_requirements_from_xml(self.root)

    def parse_input_pages(self):
        return XmlPagesSource(self.root)

    def parse_provided_metadata_style(self):
        style = None
        out_elem = self.root.find("outputs")
        if out_elem is not None and "provided_metadata_style" in out_elem.attrib:
            style = out_elem.attrib["provided_metadata_style"]

        if style is None:
            style = "legacy" if self.parse_profile() < "17.09" else "default"

        assert style in ["legacy", "default"]
        return style

    def parse_provided_metadata_file(self):
        provided_metadata_file = "galaxy.json"
        out_elem = self.root.find("outputs")
        if out_elem is not None and "provided_metadata_file" in out_elem.attrib:
            provided_metadata_file = out_elem.attrib["provided_metadata_file"]

        return provided_metadata_file

    def parse_outputs(self, tool):
        out_elem = self.root.find("outputs")
        outputs = odict()
        output_collections = odict()
        if out_elem is None:
            return outputs, output_collections

        data_dict = odict()

        def _parse(data_elem, **kwds):
            output_def = self._parse_output(data_elem, tool, **kwds)
            data_dict[output_def.name] = output_def
            return output_def

        for _ in out_elem.findall("data"):
            _parse(_)

        for collection_elem in out_elem.findall("collection"):
            name = collection_elem.get("name")
            label = xml_text(collection_elem, "label")
            default_format = collection_elem.get("format", "data")
            collection_type = collection_elem.get("type", None)
            collection_type_source = collection_elem.get("type_source", None)
            collection_type_from_rules = collection_elem.get("type_from_rules", None)
            structured_like = collection_elem.get("structured_like", None)
            inherit_format = False
            inherit_metadata = False
            if structured_like:
                inherit_format = string_as_bool(collection_elem.get("inherit_format", None))
                inherit_metadata = string_as_bool(collection_elem.get("inherit_metadata", None))
            default_format_source = collection_elem.get("format_source", None)
            default_metadata_source = collection_elem.get("metadata_source", "")
            filters = collection_elem.findall('filter')

            dataset_collector_descriptions = None
            if collection_elem.find("discover_datasets") is not None:
                dataset_collector_descriptions = dataset_collector_descriptions_from_elem(collection_elem, legacy=False)
            structure = ToolOutputCollectionStructure(
                collection_type=collection_type,
                collection_type_source=collection_type_source,
                collection_type_from_rules=collection_type_from_rules,
                structured_like=structured_like,
                dataset_collector_descriptions=dataset_collector_descriptions,
            )
            output_collection = ToolOutputCollection(
                name,
                structure,
                label=label,
                filters=filters,
                default_format=default_format,
                inherit_format=inherit_format,
                inherit_metadata=inherit_metadata,
                default_format_source=default_format_source,
                default_metadata_source=default_metadata_source,
            )
            outputs[output_collection.name] = output_collection

            for data_elem in collection_elem.findall("data"):
                _parse(
                    data_elem,
                    default_format=default_format,
                    default_format_source=default_format_source,
                    default_metadata_source=default_metadata_source,
                )

            for data_elem in collection_elem.findall("data"):
                output_name = data_elem.get("name")
                data = data_dict[output_name]
                assert data
                del data_dict[output_name]
                output_collection.outputs[output_name] = data
            output_collections[name] = output_collection

        for output_def in data_dict.values():
            outputs[output_def.name] = output_def
        return outputs, output_collections

    def _parse_output(
        self,
        data_elem,
        tool,
        default_format="data",
        default_format_source=None,
        default_metadata_source="",
    ):
        output = ToolOutput(data_elem.get("name"))
        output_format = data_elem.get("format", default_format)
        auto_format = string_as_bool(data_elem.get("auto_format", "false"))
        if auto_format and output_format != "data":
            raise ValueError("Setting format and auto_format is not supported at this time.")
        elif auto_format:
            output_format = "_sniff_"
        output.format = output_format
        output.change_format = data_elem.findall("change_format")
        output.format_source = data_elem.get("format_source", default_format_source)
        output.default_identifier_source = data_elem.get("default_identifier_source", 'None')
        output.metadata_source = data_elem.get("metadata_source", default_metadata_source)
        output.parent = data_elem.get("parent", None)
        output.label = xml_text(data_elem, "label")
        output.count = int(data_elem.get("count", 1))
        output.filters = data_elem.findall('filter')
        output.tool = tool
        output.from_work_dir = data_elem.get("from_work_dir", None)
        output.hidden = string_as_bool(data_elem.get("hidden", ""))
        output.actions = ToolOutputActionGroup(output, data_elem.find('actions'))
        output.dataset_collector_descriptions = dataset_collector_descriptions_from_elem(data_elem, legacy=self.legacy_defaults)
        return output

    def parse_stdio(self):
        """
        parse error handling from command and stdio tag

        returns list of exit codes, list of regexes
        - exit_codes contain all non-zero exit codes (:-1 and 1:) if
          detect_errors is default (if not legacy), exit_code, or aggressive
        - the oom_exit_code if given and detect_errors is exit_code
        - exit codes and regexes from the stdio tag
          these are prepended to the list, i.e. are evaluated prior to regexes
          and exit codes derived from the properties of the command tag.
          thus more specific regexes of the same or more severe error level
          are triggered first.
        """

        command_el = self._command_el
        detect_errors = None
        if command_el is not None:
            detect_errors = command_el.get("detect_errors")

        if detect_errors and detect_errors != "default":
            if detect_errors == "exit_code":
                oom_exit_code = None
                if command_el is not None:
                    oom_exit_code = command_el.get("oom_exit_code", None)
                if oom_exit_code is not None:
                    int(oom_exit_code)
                exit_codes, regexes = error_on_exit_code(out_of_memory_exit_code=oom_exit_code)
            elif detect_errors == "aggressive":
                exit_codes, regexes = aggressive_error_checks()
            else:
                raise ValueError("Unknown detect_errors value encountered [%s]" % detect_errors)
        elif len(self.root.findall('stdio')) == 0 and not self.legacy_defaults:
            exit_codes, regexes = error_on_exit_code()
        else:
            exit_codes = []
            regexes = []

        if len(self.root.findall('stdio')) > 0:
            parser = StdioParser(self.root)
            exit_codes = parser.stdio_exit_codes + exit_codes
            regexes = parser.stdio_regexes + regexes

        return exit_codes, regexes

    def parse_strict_shell(self):
        command_el = self._command_el
        if command_el is not None:
            return string_as_bool(command_el.get("strict", "False"))
        elif self.legacy_defaults:
            return False
        else:
            return True

    def parse_help(self):
        help_elem = self.root.find('help')
        return help_elem.text if help_elem is not None else None

    def macro_paths(self):
        return self._macro_paths

    def parse_tests_to_dict(self):
        tests_elem = self.root.find("tests")
        tests = []
        rval = dict(
            tests=tests
        )

        if tests_elem is not None:
            for i, test_elem in enumerate(tests_elem.findall("test")):
                tests.append(_test_elem_to_dict(test_elem, i))

        return rval

    def parse_profile(self):
        # Pre-16.04 or default XML defaults
        # - Use standard error for error detection.
        # - Don't run shells with -e
        # - Auto-check for implicit multiple outputs.
        # - Auto-check for $param_file.
        # - Enable buggy interpreter attribute.
        return self.root.get("profile", "16.01")


def _test_elem_to_dict(test_elem, i):
    rval = dict(
        outputs=__parse_output_elems(test_elem),
        output_collections=__parse_output_collection_elems(test_elem),
        inputs=__parse_input_elems(test_elem, i),
        expect_num_outputs=test_elem.get("expect_num_outputs"),
        command=__parse_assert_list_from_elem(test_elem.find("assert_command")),
        stdout=__parse_assert_list_from_elem(test_elem.find("assert_stdout")),
        stderr=__parse_assert_list_from_elem(test_elem.find("assert_stderr")),
        expect_exit_code=test_elem.get("expect_exit_code"),
        expect_failure=string_as_bool(test_elem.get("expect_failure", False)),
        maxseconds=test_elem.get("maxseconds", None),
    )
    _copy_to_dict_if_present(test_elem, rval, ["num_outputs"])
    return rval


def __parse_input_elems(test_elem, i):
    __expand_input_elems(test_elem)
    return __parse_inputs_elems(test_elem, i)


def __parse_output_elems(test_elem):
    outputs = []
    for output_elem in test_elem.findall("output"):
        name, file, attributes = __parse_output_elem(output_elem)
        outputs.append({"name": name, "value": file, "attributes": attributes})
    return outputs


def __parse_output_elem(output_elem):
    attrib = dict(output_elem.attrib)
    name = attrib.pop('name', None)
    if name is None:
        raise Exception("Test output does not have a 'name'")

    file, attributes = __parse_test_attributes(output_elem, attrib, parse_discovered_datasets=True)
    return name, file, attributes


def __parse_command_elem(test_elem):
    assert_elem = test_elem.find("command")
    return __parse_assert_list_from_elem(assert_elem)


def __parse_output_collection_elems(test_elem):
    output_collections = []
    for output_collection_elem in test_elem.findall("output_collection"):
        output_collection_def = __parse_output_collection_elem(output_collection_elem)
        output_collections.append(output_collection_def)
    return output_collections


def __parse_output_collection_elem(output_collection_elem):
    attrib = dict(output_collection_elem.attrib)
    name = attrib.pop('name', None)
    if name is None:
        raise Exception("Test output collection does not have a 'name'")
    element_tests = __parse_element_tests(output_collection_elem)
    return TestCollectionOutputDef(name, attrib, element_tests).to_dict()


def __parse_element_tests(parent_element):
    element_tests = {}
    for element in parent_element.findall("element"):
        element_attrib = dict(element.attrib)
        identifier = element_attrib.pop('name', None)
        if identifier is None:
            raise Exception("Test primary dataset does not have a 'identifier'")
        element_tests[identifier] = __parse_test_attributes(element, element_attrib, parse_elements=True)
    return element_tests


def __parse_test_attributes(output_elem, attrib, parse_elements=False, parse_discovered_datasets=False):
    assert_list = __parse_assert_list(output_elem)

    # Allow either file or value to specify a target file to compare result with
    # file was traditionally used by outputs and value by extra files.
    file = attrib.pop('file', attrib.pop('value', None))

    # File no longer required if an list of assertions was present.
    attributes = {}
    # Method of comparison
    attributes['compare'] = attrib.pop('compare', 'diff').lower()
    # Number of lines to allow to vary in logs (for dates, etc)
    attributes['lines_diff'] = int(attrib.pop('lines_diff', '0'))
    # Allow a file size to vary if sim_size compare
    attributes['delta'] = int(attrib.pop('delta', '10000'))
    attributes['sort'] = string_as_bool(attrib.pop('sort', False))
    attributes['decompress'] = string_as_bool(attrib.pop('decompress', False))
    extra_files = []
    if 'ftype' in attrib:
        attributes['ftype'] = attrib['ftype']
    for extra in output_elem.findall('extra_files'):
        extra_files.append(__parse_extra_files_elem(extra))
    metadata = {}
    for metadata_elem in output_elem.findall('metadata'):
        metadata[metadata_elem.get('name')] = metadata_elem.get('value')
    md5sum = attrib.get("md5", None)
    checksum = attrib.get("checksum", None)
    element_tests = {}
    if parse_elements:
        element_tests = __parse_element_tests(output_elem)

    primary_datasets = {}
    if parse_discovered_datasets:
        for primary_elem in (output_elem.findall("discovered_dataset") or []):
            primary_attrib = dict(primary_elem.attrib)
            designation = primary_attrib.pop('designation', None)
            if designation is None:
                raise Exception("Test primary dataset does not have a 'designation'")
            primary_datasets[designation] = __parse_test_attributes(primary_elem, primary_attrib)

    has_checksum = md5sum or checksum
    has_nested_tests = extra_files or element_tests or primary_datasets
    if not (assert_list or file or metadata or has_checksum or has_nested_tests):
        raise Exception("Test output defines nothing to check (e.g. must have a 'file' check against, assertions to check, metadata or checksum tests, etc...)")
    attributes['assert_list'] = assert_list
    attributes['extra_files'] = extra_files
    attributes['metadata'] = metadata
    attributes['md5'] = md5sum
    attributes['checksum'] = checksum
    attributes['elements'] = element_tests
    attributes['primary_datasets'] = primary_datasets
    return file, attributes


def __parse_assert_list(output_elem):
    assert_elem = output_elem.find("assert_contents")
    return __parse_assert_list_from_elem(assert_elem)


def __parse_assert_list_from_elem(assert_elem):
    assert_list = None

    def convert_elem(elem):
        """ Converts and XML element to a dictionary format, used by assertion checking code. """
        tag = elem.tag
        attributes = dict(elem.attrib)
        converted_children = []
        for child_elem in elem:
            converted_children.append(convert_elem(child_elem))
        return {"tag": tag, "attributes": attributes, "children": converted_children}
    if assert_elem is not None:
        assert_list = []
        for assert_child in list(assert_elem):
            assert_list.append(convert_elem(assert_child))

    return assert_list


def __parse_extra_files_elem(extra):
    # File or directory, when directory, compare basename
    # by basename
    attrib = dict(extra.attrib)
    extra_type = attrib.pop('type', 'file')
    extra_name = attrib.pop('name', None)
    assert extra_type == 'directory' or extra_name is not None, \
        'extra_files type (%s) requires a name attribute' % extra_type
    extra_value, extra_attributes = __parse_test_attributes(extra, attrib)
    return {
        "value": extra_value,
        "name": extra_name,
        "type": extra_type,
        "attributes": extra_attributes
    }


def __expand_input_elems(root_elem, prefix=""):
    __append_prefix_to_params(root_elem, prefix)

    repeat_elems = root_elem.findall('repeat')
    indices = {}
    for repeat_elem in repeat_elems:
        name = repeat_elem.get("name")
        if name not in indices:
            indices[name] = 0
            index = 0
        else:
            index = indices[name] + 1
            indices[name] = index

        new_prefix = __prefix_join(prefix, name, index=index)
        __expand_input_elems(repeat_elem, new_prefix)
        __pull_up_params(root_elem, repeat_elem)
        root_elem.remove(repeat_elem)

    cond_elems = root_elem.findall('conditional')
    for cond_elem in cond_elems:
        new_prefix = __prefix_join(prefix, cond_elem.get("name"))
        __expand_input_elems(cond_elem, new_prefix)
        __pull_up_params(root_elem, cond_elem)
        root_elem.remove(cond_elem)

    section_elems = root_elem.findall('section')
    for section_elem in section_elems:
        new_prefix = __prefix_join(prefix, section_elem.get("name"))
        __expand_input_elems(section_elem, new_prefix)
        __pull_up_params(root_elem, section_elem)
        root_elem.remove(section_elem)


def __append_prefix_to_params(elem, prefix):
    for param_elem in elem.findall('param'):
        param_elem.set("name", __prefix_join(prefix, param_elem.get("name")))


def __pull_up_params(parent_elem, child_elem):
    for param_elem in child_elem.findall('param'):
        parent_elem.append(param_elem)
        child_elem.remove(param_elem)


def __prefix_join(prefix, name, index=None):
    name = name if index is None else "%s_%d" % (name, index)
    return name if not prefix else "%s|%s" % (prefix, name)


def _copy_to_dict_if_present(elem, rval, attributes):
    for attribute in attributes:
        if attribute in elem.attrib:
            rval[attribute] = elem.get(attribute)
    return rval


def __parse_inputs_elems(test_elem, i):
    raw_inputs = []
    for param_elem in test_elem.findall("param"):
        raw_inputs.append(__parse_param_elem(param_elem, i))

    return raw_inputs


def __parse_param_elem(param_elem, i=0):
    attrib = dict(param_elem.attrib)
    if 'values' in attrib:
        value = attrib['values'].split(',')
    elif 'value' in attrib:
        value = attrib['value']
    else:
        value = None
    children_elem = param_elem
    if children_elem is not None:
        # At this time, we can assume having children only
        # occurs on DataToolParameter test items but this could
        # change and would cause the below parsing to change
        # based upon differences in children items
        attrib['metadata'] = {}
        attrib['composite_data'] = []
        attrib['edit_attributes'] = []
        # Composite datasets need to be renamed uniquely
        composite_data_name = None
        for child in children_elem:
            if child.tag == 'composite_data':
                file_name = child.get("value")
                attrib['composite_data'].append(file_name)
                if composite_data_name is None:
                    # Generate a unique name; each test uses a
                    # fresh history.
                    composite_data_name = '_COMPOSITE_RENAMED_t%d_%s' \
                        % (i, uuid.uuid1().hex)
            elif child.tag == 'metadata':
                attrib['metadata'][child.get("name")] = child.get("value")
            elif child.tag == 'edit_attributes':
                attrib['edit_attributes'].append(child)
            elif child.tag == 'collection':
                attrib['collection'] = TestCollectionDef.from_xml(child, __parse_param_elem)
        if composite_data_name:
            # Composite datasets need implicit renaming;
            # inserted at front of list so explicit declarations
            # take precedence
            attrib['edit_attributes'].insert(0, {'type': 'name', 'value': composite_data_name})
    name = attrib.pop('name')
    return {
        "name": name,
        "value": value,
        "attributes": attrib
    }


class StdioParser(object):

    def __init__(self, root):
        try:
            self.stdio_exit_codes = list()
            self.stdio_regexes = list()

            # We should have a single <stdio> element, but handle the case for
            # multiples.
            # For every stdio element, add all of the exit_code and regex
            # subelements that we find:
            for stdio_elem in (root.findall('stdio')):
                self.parse_stdio_exit_codes(stdio_elem)
                self.parse_stdio_regexes(stdio_elem)
        except Exception:
            log.error("Exception in parse_stdio! " + str(sys.exc_info()))

    def parse_stdio_exit_codes(self, stdio_elem):
        """
        Parse the tool's <stdio> element's <exit_code> subelements.
        This will add all of those elements, if any, to self.stdio_exit_codes.
        """
        try:
            # Look for all <exit_code> elements. Each exit_code element must
            # have a range/value.
            # Exit-code ranges have precedence over a single exit code.
            # So if there are value and range attributes, we use the range
            # attribute. If there is neither a range nor a value, then print
            # a warning and skip to the next.
            for exit_code_elem in (stdio_elem.findall("exit_code")):
                exit_code = ToolStdioExitCode()
                # Each exit code has an optional description that can be
                # part of the "desc" or "description" attributes:
                exit_code.desc = exit_code_elem.get("desc")
                if exit_code.desc is None:
                    exit_code.desc = exit_code_elem.get("description")
                # Parse the error level:
                exit_code.error_level = (
                    self.parse_error_level(exit_code_elem.get("level")))
                code_range = exit_code_elem.get("range", "")
                if code_range is None:
                    code_range = exit_code_elem.get("value", "")
                if code_range is None:
                    log.warning("Tool stdio exit codes must have " +
                                "a range or value")
                    continue
                # Parse the range. We look for:
                #   :Y
                #  X:
                #  X:Y   - Split on the colon. We do not allow a colon
                #          without a beginning or end, though we could.
                # Also note that whitespace is eliminated.
                # TODO: Turn this into a single match - it should be
                # more efficient.
                code_range = re.sub(r"\s", "", code_range)
                code_ranges = re.split(r":", code_range)
                if (len(code_ranges) == 2):
                    if (code_ranges[0] is None or '' == code_ranges[0]):
                        exit_code.range_start = float("-inf")
                    else:
                        exit_code.range_start = int(code_ranges[0])
                    if (code_ranges[1] is None or '' == code_ranges[1]):
                        exit_code.range_end = float("inf")
                    else:
                        exit_code.range_end = int(code_ranges[1])
                # If we got more than one colon, then ignore the exit code.
                elif (len(code_ranges) > 2):
                    log.warning("Invalid tool exit_code range %s - ignored"
                                % code_range)
                    continue
                # Else we have a singular value. If it's not an integer, then
                # we'll just write a log message and skip this exit_code.
                else:
                    try:
                        exit_code.range_start = int(code_range)
                    except Exception:
                        log.error(code_range)
                        log.warning("Invalid range start for tool's exit_code %s: exit_code ignored" % code_range)
                        continue
                    exit_code.range_end = exit_code.range_start
                # TODO: Check if we got ">", ">=", "<", or "<=":
                # Check that the range, regardless of how we got it,
                # isn't bogus. If we have two infinite values, then
                # the start must be -inf and the end must be +inf.
                # So at least warn about this situation:
                if (isinf(exit_code.range_start) and
                        isinf(exit_code.range_end)):
                    log.warning("Tool exit_code range %s will match on " +
                                "all exit codes" % code_range)
                self.stdio_exit_codes.append(exit_code)
        except Exception:
            log.error("Exception in parse_stdio_exit_codes! " +
                      str(sys.exc_info()))
            trace = sys.exc_info()[2]
            if trace is not None:
                trace_msg = repr(traceback.format_tb(trace))
                log.error("Traceback: %s" % trace_msg)

    def parse_stdio_regexes(self, stdio_elem):
        """
        Look in the tool's <stdio> elem for all <regex> subelements
        that define how to look for warnings and fatal errors in
        stdout and stderr. This will add all such regex elements
        to the Tols's stdio_regexes list.
        """
        try:
            # Look for every <regex> subelement. The regular expression
            # will have "match" and "source" (or "src") attributes.
            for regex_elem in (stdio_elem.findall("regex")):
                # TODO: Fill in ToolStdioRegex
                regex = ToolStdioRegex()
                # Each regex has an optional description that can be
                # part of the "desc" or "description" attributes:
                regex.desc = regex_elem.get("desc")
                if regex.desc is None:
                    regex.desc = regex_elem.get("description")
                # Parse the error level
                regex.error_level = (
                    self.parse_error_level(regex_elem.get("level")))
                regex.match = regex_elem.get("match", "")
                if regex.match is None:
                    # TODO: Convert the offending XML element to a string
                    log.warning("Ignoring tool's stdio regex element %s - "
                                "the 'match' attribute must exist")
                    continue
                # Parse the output sources. We look for the "src", "source",
                # and "sources" attributes, in that order. If there is no
                # such source, then the source defaults to stderr & stdout.
                # Look for a comma and then look for "err", "error", "out",
                # and "output":
                output_srcs = regex_elem.get("src")
                if output_srcs is None:
                    output_srcs = regex_elem.get("source")
                if output_srcs is None:
                    output_srcs = regex_elem.get("sources")
                if output_srcs is None:
                    output_srcs = "output,error"
                output_srcs = re.sub(r"\s", "", output_srcs)
                src_list = re.split(r",", output_srcs)
                # Just put together anything to do with "out", including
                # "stdout", "output", etc. Repeat for "stderr", "error",
                # and anything to do with "err". If neither stdout nor
                # stderr were specified, then raise a warning and scan both.
                for src in src_list:
                    if re.search("both", src, re.IGNORECASE):
                        regex.stdout_match = True
                        regex.stderr_match = True
                    if re.search("out", src, re.IGNORECASE):
                        regex.stdout_match = True
                    if re.search("err", src, re.IGNORECASE):
                        regex.stderr_match = True
                    if (not regex.stdout_match and not regex.stderr_match):
                        log.warning("Tool id %s: unable to determine if tool "
                                    "stream source scanning is output, error, "
                                    "or both. Defaulting to use both." % self.id)
                        regex.stdout_match = True
                        regex.stderr_match = True
                self.stdio_regexes.append(regex)
        except Exception:
            log.error("Exception in parse_stdio_exit_codes! " +
                      str(sys.exc_info()))
            trace = sys.exc_info()[2]
            if trace is not None:
                trace_msg = repr(traceback.format_tb(trace))
                log.error("Traceback: %s" % trace_msg)

    # TODO: This method doesn't have to be part of the Tool class.
    def parse_error_level(self, err_level):
        """
        Parses error level and returns error level enumeration. If
        unparsable, returns 'fatal'
        """
        return_level = StdioErrorLevel.FATAL
        try:
            if err_level:
                if (re.search("log", err_level, re.IGNORECASE)):
                    return_level = StdioErrorLevel.LOG
                elif (re.search("warning", err_level, re.IGNORECASE)):
                    return_level = StdioErrorLevel.WARNING
                elif (re.search("fatal_oom", err_level, re.IGNORECASE)):
                    return_level = StdioErrorLevel.FATAL_OOM
                elif (re.search("fatal", err_level, re.IGNORECASE)):
                    return_level = StdioErrorLevel.FATAL
                else:
                    log.debug("Tool %s: error level %s did not match log/warning/fatal" %
                              (self.id, err_level))
        except Exception:
            log.error("Exception in parse_error_level " +
                      str(sys.exc_info()))
            trace = sys.exc_info()[2]
            if trace is not None:
                trace_msg = repr(traceback.format_tb(trace))
                log.error("Traceback: %s" % trace_msg)
        return return_level


class XmlPagesSource(PagesSource):

    def __init__(self, root):
        self.input_elem = root.find("inputs")
        page_sources = []
        if self.input_elem is not None:
            pages_elem = self.input_elem.findall("page")
            for page in (pages_elem or [self.input_elem]):
                page_sources.append(XmlPageSource(page))
        super(XmlPagesSource, self).__init__(page_sources)

    @property
    def inputs_defined(self):
        return self.input_elem is not None


class XmlPageSource(PageSource):

    def __init__(self, parent_elem):
        self.parent_elem = parent_elem

    def parse_display(self):
        display_elem = self.parent_elem.find("display")
        if display_elem is not None:
            display = xml_to_string(display_elem)
        else:
            display = None
        return display

    def parse_input_sources(self):
        return map(XmlInputSource, self.parent_elem)


class XmlInputSource(InputSource):

    def __init__(self, input_elem):
        self.input_elem = input_elem
        self.input_type = self.input_elem.tag

    def parse_input_type(self):
        return self.input_type

    def elem(self):
        return self.input_elem

    def get(self, key, value=None):
        return self.input_elem.get(key, value)

    def get_bool(self, key, default):
        return string_as_bool(self.get(key, default))

    def parse_label(self):
        return xml_text(self.input_elem, "label")

    def parse_help(self):
        return xml_text(self.input_elem, "help")

    def parse_sanitizer_elem(self):
        return self.input_elem.find("sanitizer")

    def parse_validator_elems(self):
        return self.input_elem.findall("validator")

    def parse_dynamic_options_elem(self):
        """ Return a galaxy.tools.parameters.dynamic_options.DynamicOptions
        if appropriate.
        """
        options_elem = self.input_elem.find('options')
        return options_elem

    def parse_static_options(self):
        static_options = list()
        elem = self.input_elem
        for index, option in enumerate(elem.findall("option")):
            value = option.get("value")
            selected = string_as_bool(option.get("selected", False))
            static_options.append((option.text or value, value, selected))
        return static_options

    def parse_optional(self, default=None):
        """ Return boolean indicating wheter parameter is optional. """
        elem = self.input_elem
        if self.get('type') == "data_column":
            # Allow specifing force_select for backward compat., but probably
            # should use optional going forward for consistency with other
            # parameters.
            if "force_select" in elem.attrib:
                force_select = string_as_bool(elem.get("force_select"))
            else:
                force_select = not string_as_bool(elem.get("optional", False))
            return not force_select

        if default is None:
            default = self.default_optional
        return self.get_bool("optional", default)

    def parse_conversion_tuples(self):
        elem = self.input_elem
        conversions = []
        for conv_elem in elem.findall("conversion"):
            name = conv_elem.get("name")  # name for commandline substitution
            conv_extensions = conv_elem.get("type")  # target datatype extension
            conversions.append((name, conv_extensions))
        return conversions

    def parse_nested_inputs_source(self):
        elem = self.input_elem
        return XmlPageSource(elem)

    def parse_test_input_source(self):
        elem = self.input_elem
        input_elem = elem.find("param")
        assert input_elem is not None, "<conditional> must have a child <param>"
        return XmlInputSource(input_elem)

    def parse_when_input_sources(self):
        elem = self.input_elem

        sources = []
        for case_elem in elem.findall("when"):
            value = case_elem.get("value")
            case_page_source = XmlPageSource(case_elem)
            sources.append((value, case_page_source))
        return sources
