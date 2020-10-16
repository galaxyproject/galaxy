from galaxy.tools.deps import requirements
from galaxy.util.odict import odict
from .interface import InputSource
from .interface import PageSource
from .interface import PagesSource
from .interface import ToolSource
from .output_actions import ToolOutputActionGroup
from .output_collection_def import dataset_collector_descriptions_from_output_dict
from .output_objects import (
    ToolOutput,
    ToolOutputCollection,
    ToolOutputCollectionStructure,
)
from .util import error_on_exit_code, is_dict


class YamlToolSource(ToolSource):

    def __init__(self, root_dict, source_path=None):
        self.root_dict = root_dict
        self._source_path = source_path
        self._macro_paths = []

    def parse_id(self):
        return self.root_dict.get("id")

    def parse_version(self):
        return self.root_dict.get("version")

    def parse_name(self):
        return self.root_dict.get("name")

    def parse_description(self):
        return self.root_dict.get("description", "")

    def parse_edam_operations(self):
        return self.root_dict.get("edam_operations", [])

    def parse_edam_topics(self):
        return self.root_dict.get("edam_topics", [])

    def parse_is_multi_byte(self):
        return self.root_dict.get("is_multi_byte", self.default_is_multi_byte)

    def parse_sanitize(self):
        return self.root_dict.get("sanitize", True)

    def parse_display_interface(self, default):
        return self.root_dict.get('display_interface', default)

    def parse_require_login(self, default):
        return self.root_dict.get('require_login', default)

    def parse_command(self):
        return self.root_dict.get("command")

    def parse_environment_variables(self):
        return []

    def parse_interpreter(self):
        return self.root_dict.get("interpreter")

    def parse_version_command(self):
        return self.root_dict.get("runtime_version", {}).get("command", None)

    def parse_version_command_interpreter(self):
        return self.root_dict.get("runtime_version", {}).get("interpreter", None)

    def parse_requirements_and_containers(self):
        return requirements.parse_requirements_from_dict(self.root_dict)

    def parse_input_pages(self):
        # All YAML tools have only one page (feature is deprecated)
        page_source = YamlPageSource(self.root_dict.get("inputs", {}))
        return PagesSource([page_source])

    def parse_strict_shell(self):
        # TODO: Add ability to disable this.
        return True

    def parse_stdio(self):
        return error_on_exit_code()

    def parse_help(self):
        return self.root_dict.get("help", None)

    def parse_outputs(self, tool):
        outputs = self.root_dict.get("outputs", {})
        output_defs = []
        output_collection_defs = []
        for name, output_dict in outputs.items():
            output_type = output_dict.get("type", "data")
            if output_type == "data":
                output_defs.append(self._parse_output(tool, name, output_dict))
            elif output_type == "collection":
                output_collection_defs.append(self._parse_output_collection(tool, name, output_dict))
            else:
                message = "Unknown output_type [%s] encountered." % output_type
                raise Exception(message)
        outputs = odict()
        for output in output_defs:
            outputs[output.name] = output
        output_collections = odict()
        for output in output_collection_defs:
            output_collections[output.name] = output

        return outputs, output_collections

    def _parse_output(self, tool, name, output_dict):
        # TODO: handle filters, actions, change_format
        output = ToolOutput(name)
        output.format = output_dict.get("format", "data")
        output.change_format = []
        output.format_source = output_dict.get("format_source", None)
        output.default_identifier_source = output_dict.get("default_identifier_source", None)
        output.metadata_source = output_dict.get("metadata_source", "")
        output.parent = output_dict.get("parent", None)
        output.label = output_dict.get("label", None)
        output.count = output_dict.get("count", 1)
        output.filters = []
        output.tool = tool
        output.from_work_dir = output_dict.get("from_work_dir", None)
        output.hidden = output_dict.get("hidden", "")
        # TODO: implement tool output action group fixes
        output.actions = ToolOutputActionGroup(output, None)
        output.dataset_collector_descriptions = dataset_collector_descriptions_from_output_dict(output_dict)
        return output

    def _parse_output_collection(self, tool, name, output_dict):
        name = output_dict.get("name")
        label = output_dict.get("label")
        default_format = output_dict.get("format", "data")
        collection_type = output_dict.get("type", None)
        collection_type_source = output_dict.get("type_source", None)
        structured_like = output_dict.get("structured_like", None)
        inherit_format = False
        inherit_metadata = False
        if structured_like:
            inherit_format = output_dict.get("inherit_format", None)
            inherit_metadata = output_dict.get("inherit_metadata", None)
        default_format_source = output_dict.get("format_source", None)
        default_metadata_source = output_dict.get("metadata_source", "")
        filters = []
        dataset_collector_descriptions = dataset_collector_descriptions_from_output_dict(output_dict)

        structure = ToolOutputCollectionStructure(
            collection_type=collection_type,
            collection_type_source=collection_type_source,
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
        return output_collection

    def parse_tests_to_dict(self):
        tests = []
        rval = dict(
            tests=tests
        )

        for i, test_dict in enumerate(self.root_dict.get("tests", [])):
            tests.append(_parse_test(i, test_dict))

        return rval

    def parse_profile(self):
        return self.root_dict.get("profile", "16.04")


def _parse_test(i, test_dict):
    inputs = test_dict["inputs"]
    if is_dict(inputs):
        new_inputs = []
        for key, value in inputs.items():
            new_inputs.append({"name": key, "value": value, "attributes": {}})
        test_dict["inputs"] = new_inputs

    outputs = test_dict["outputs"]

    new_outputs = []
    if is_dict(outputs):
        for key, value in outputs.items():
            if is_dict(value):
                attributes = value
                file = attributes.get("file")
            else:
                file = value
                attributes = {}
            new_outputs.append({
                "name": key,
                "value": file,
                "attributes": attributes
            })
    else:
        for output in outputs:
            name = output["name"]
            value = output.get("file", None)
            attributes = output
            new_outputs.append((name, value, attributes))

    for output in new_outputs:
        attributes = output["attributes"]
        defaults = {
            'compare': 'diff',
            'lines_diff': 0,
            'delta': 1000,
            'sort': False,
        }
        # TODO
        attributes["extra_files"] = []
        # TODO
        attributes["metadata"] = {}
        # TODO
        assert_list = []
        assert_list = __to_test_assert_list(attributes.get("asserts", []))
        attributes["assert_list"] = assert_list
        _ensure_has(attributes, defaults)

    test_dict["outputs"] = new_outputs
    # TODO: implement output collections for YAML tools.
    test_dict["output_collections"] = []
    test_dict["command"] = __to_test_assert_list(test_dict.get("command", []))
    test_dict["stdout"] = __to_test_assert_list(test_dict.get("stdout", []))
    test_dict["stderr"] = __to_test_assert_list(test_dict.get("stderr", []))
    test_dict["expect_exit_code"] = test_dict.get("expect_exit_code", None)
    test_dict["expect_failure"] = test_dict.get("expect_exit_code", False)
    return test_dict


def __to_test_assert_list(assertions):
    def expand_dict_form(item):
        key, value = item
        new_value = value.copy()
        new_value["that"] = key
        return new_value

    if is_dict(assertions):
        assertions = map(expand_dict_form, assertions.items())

    assert_list = []
    for assertion in assertions:
        # TODO: not handling nested assertions correctly,
        # not sure these are used though.
        children = []
        if "children" in assertion:
            children = assertion["children"]
            del assertion["children"]
        assert_dict = dict(
            tag=assertion["that"],
            attributes=assertion,
            children=children,
        )
        assert_list.append(assert_dict)

    return assert_list or None  # XML variant is None if no assertions made


class YamlPageSource(PageSource):

    def __init__(self, inputs_list):
        self.inputs_list = inputs_list

    def parse_input_sources(self):
        return map(YamlInputSource, self.inputs_list)


class YamlInputSource(InputSource):

    def __init__(self, input_dict):
        self.input_dict = input_dict

    def get(self, key, default=None):
        return self.input_dict.get(key, default)

    def get_bool(self, key, default):
        return self.input_dict.get(key, default)

    def parse_input_type(self):
        input_type = self.input_dict["type"]
        if input_type == "repeat":
            return "repeat"
        elif input_type == "conditional":
            return "conditional"
        else:
            return "param"

    def parse_nested_inputs_source(self):
        assert self.parse_input_type() == "repeat"
        return YamlPageSource(self.input_dict["blocks"])

    def parse_test_input_source(self):
        test_dict = self.input_dict.get("test", None)
        assert test_dict is not None, "conditional must contain a `test` definition"
        return YamlInputSource(test_dict)

    def parse_when_input_sources(self):
        input_dict = self.input_dict

        sources = []
        for value, block in input_dict.get("when", {}).items():
            if value is True:
                value = "true"
            elif value is False:
                value = "false"
            else:
                value = str(value)

            # str here to lose type information like XML, needed?
            if not isinstance(block, list):
                block = [block]
            case_page_source = YamlPageSource(block)
            sources.append((value, case_page_source))
        return sources

    def parse_static_options(self):
        static_options = list()
        input_dict = self.input_dict
        for index, option in enumerate(input_dict.get("options", {})):
            value = option.get("value")
            label = option.get("label", value)
            selected = option.get("selected", False)
            static_options.append((label, value, selected))
        return static_options


def _ensure_has(dict, defaults):
    for key, value in defaults.items():
        if key not in dict:
            dict[key] = value
