from .interface import ToolSource
from .interface import PagesSource
from .interface import PageSource
from .interface import InputSource

from galaxy.tools.deps import requirements
from galaxy.tools.parameters import output_collect
import galaxy.tools


class YamlToolSource(ToolSource):

    def __init__(self, root_dict):
        self.root_dict = root_dict

    def parse_id(self):
        return self.root_dict.get("id")

    def parse_version(self):
        return self.root_dict.get("version")

    def parse_name(self):
        return self.root_dict.get("name")

    def parse_description(self):
        return self.root_dict.get("description")

    def parse_is_multi_byte(self):
        return self.root_dict.get("is_multi_byte", self.default_is_multi_byte)

    def parse_display_interface(self, default):
        return self.root_dict.get('display_interface', default)

    def parse_require_login(self, default):
        return self.root_dict.get('require_login', default)

    def parse_command(self):
        return self.root_dict.get("command")

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

    def parse_stdio(self):
        from galaxy.jobs.error_level import StdioErrorLevel

        # New format - starting out just using exit code.
        exit_code_lower = galaxy.tools.ToolStdioExitCode()
        exit_code_lower.range_start = float("-inf")
        exit_code_lower.range_end = -1
        exit_code_lower.error_level = StdioErrorLevel.FATAL
        exit_code_high = galaxy.tools.ToolStdioExitCode()
        exit_code_high.range_start = 1
        exit_code_high.range_end = float("inf")
        exit_code_lower.error_level = StdioErrorLevel.FATAL
        return [exit_code_lower, exit_code_high], []

    def parse_outputs(self, tool):
        outputs = self.root_dict.get("outputs", {})
        output_defs = []
        for name, output_dict in outputs.items():
            output_defs.append(self._parse_output(tool, name, output_dict))
        return output_defs

    def _parse_output(self, tool, name, output_dict):
        # TODO: handle filters, actions, change_format
        output = galaxy.tools.ToolOutput( name )
        output.format = output_dict.get("format", "data")
        output.change_format = []
        output.format_source = output_dict.get("format_source", None)
        output.metadata_source = output_dict.get("metadata_source", "")
        output.parent = output_dict.get("parent", None)
        output.label = output_dict.get( "label", None )
        output.count = output_dict.get("count", 1)
        output.filters = []
        output.tool = tool
        output.from_work_dir = output_dict.get("from_work_dir", None)
        output.hidden = output_dict.get("hidden", "")
        output.actions = galaxy.tools.ToolOutputActionGroup( output, None )
        discover_datasets_dicts = output_dict.get( "discover_datasets", [] )
        if isinstance( discover_datasets_dicts, dict ):
            discover_datasets_dicts = [ discover_datasets_dicts ]
        output.dataset_collectors = output_collect.dataset_collectors_from_list( discover_datasets_dicts )
        return output

    def parse_tests_to_dict(self):
        tests = []
        rval = dict(
            tests=tests
        )

        for i, test_dict in enumerate(self.root_dict.get("tests", [])):
            tests.append(_parse_test(i, test_dict))

        return rval


def _parse_test(i, test_dict):
    inputs = test_dict["inputs"]
    if isinstance(inputs, dict):
        new_inputs = []
        for key, value in inputs.iteritems():
            new_inputs.append((key, value, {}))
        test_dict["inputs"] = new_inputs

    outputs = test_dict["outputs"]

    new_outputs = []
    if isinstance(outputs, dict):
        for key, value in outputs.iteritems():
            if isinstance(value, dict):
                attributes = value
                file = attributes.get("file")
            else:
                file = value
                attributes = {}
            new_outputs.append((key, file, attributes))
    else:
        for output in outputs:
            name = output["name"]
            value = output.get("file", None)
            attributes = output
            new_outputs.append((name, value, attributes))

    for output in new_outputs:
        attributes = output[2]
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
        for key, assertion in attributes.get("asserts", {}).iteritems():
            # TODO: not handling nested assertions correctly,
            # not sure these are used though.
            children = []
            if "children" in assertion:
                children = assertion["children"]
                del assertion["children"]
            assert_dict = dict(
                tag=key,
                attributes=assertion,
                children=children,
            )
            assert_list.append(assert_dict)
        attributes["assert_list"] = assert_list

        _ensure_has(attributes, defaults)

    test_dict["outputs"] = new_outputs
    return test_dict


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
        test_dict = self.input_dict.get( "test", None )
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

            # str here to loose type information like XML, needed?
            if not isinstance(block, list):
                block = [block]
            case_page_source = YamlPageSource(block)
            sources.append((value, case_page_source))
        return sources


def _ensure_has(dict, defaults):
    for key, value in defaults.iteritems():
        if key not in dict:
            dict[key] = value
