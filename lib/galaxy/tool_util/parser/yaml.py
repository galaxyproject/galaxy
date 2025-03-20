import json
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import packaging.version

from galaxy.tool_util.deps import requirements
from galaxy.tool_util.parser.util import (
    DEFAULT_DECOMPRESS,
    DEFAULT_DELTA,
    DEFAULT_DELTA_FRAC,
    DEFAULT_SORT,
)
from .interface import (
    AssertionDict,
    AssertionList,
    HelpContent,
    InputSource,
    PageSource,
    PagesSource,
    ToolSource,
    ToolSourceTest,
    ToolSourceTests,
    XrefDict,
)
from .output_collection_def import dataset_collector_descriptions_from_output_dict
from .output_objects import (
    ToolOutput,
    ToolOutputCollection,
    ToolOutputCollectionStructure,
)
from .parameter_validators import (
    AnyValidatorModel,
    parse_dict_validators,
)
from .stdio import error_on_exit_code
from .util import is_dict


class YamlToolSource(ToolSource):
    language = "yaml"

    def __init__(self, root_dict: Dict, source_path=None):
        self.root_dict = root_dict
        self._source_path = source_path
        self._macro_paths: List[str] = []

    @property
    def source_path(self):
        return self._source_path

    def parse_tool_type(self):
        return self.root_dict.get("tool_type")

    def parse_id(self):
        return self.root_dict.get("id")

    def parse_version(self) -> Optional[str]:
        version_raw = self.root_dict.get("version")
        return str(version_raw) if version_raw is not None else None

    def parse_name(self) -> str:
        rval = self.root_dict.get("name") or self.parse_id()
        assert rval
        return str(rval)

    def parse_description(self) -> str:
        return self.root_dict.get("description", "")

    def parse_edam_operations(self) -> List[str]:
        return self.root_dict.get("edam_operations", [])

    def parse_edam_topics(self) -> List[str]:
        return self.root_dict.get("edam_topics", [])

    def parse_xrefs(self) -> List[XrefDict]:
        xrefs = self.root_dict.get("xrefs", [])
        return [XrefDict(value=xref["value"], reftype=xref["type"]) for xref in xrefs if xref["type"]]

    def parse_sanitize(self):
        return self.root_dict.get("sanitize", True)

    def parse_display_interface(self, default):
        return self.root_dict.get("display_interface", default)

    def parse_require_login(self, default):
        return self.root_dict.get("require_login", default)

    def parse_command(self):
        return self.root_dict.get("command")

    def parse_expression(self):
        return self.root_dict.get("expression")

    def parse_environment_variables(self):
        return []

    def parse_interpreter(self):
        return self.root_dict.get("interpreter")

    def parse_version_command(self):
        return self.root_dict.get("runtime_version", {}).get("command", None)

    def parse_version_command_interpreter(self):
        return self.root_dict.get("runtime_version", {}).get("interpreter", None)

    def parse_requirements_and_containers(self):
        mixed_requirements = self.root_dict.get("requirements", [])
        return requirements.parse_requirements_from_lists(
            software_requirements=[r for r in mixed_requirements if r.get("type") != "resource"],
            containers=self.root_dict.get("containers", []),
            resource_requirements=[r for r in mixed_requirements if r.get("type") == "resource"],
        )

    def parse_input_pages(self) -> PagesSource:
        # All YAML tools have only one page (feature is deprecated)
        page_source = YamlPageSource(self.root_dict.get("inputs", {}))
        return PagesSource([page_source])

    def parse_strict_shell(self):
        # TODO: Add ability to disable this.
        return True

    def parse_stdio(self):
        return error_on_exit_code()

    def parse_help(self) -> Optional[HelpContent]:
        content = self.root_dict.get("help", None)
        if content:
            return HelpContent(format="markdown", content=content)
        else:
            return None

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
                message = f"Unknown output_type [{output_type}] encountered."
                raise Exception(message)
        outputs = {}
        for output in output_defs:
            outputs[output.name] = output
        output_collections = {}
        for output in output_collection_defs:
            output_collections[output.name] = output

        return outputs, output_collections

    def _parse_output(self, tool, name, output_dict):
        output = ToolOutput.from_dict(name, output_dict, tool=tool)
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

    def parse_tests_to_dict(self) -> ToolSourceTests:
        tests: List[ToolSourceTest] = []
        rval: ToolSourceTests = dict(tests=tests)

        for i, test_dict in enumerate(self.root_dict.get("tests", [])):
            tests.append(_parse_test(i, test_dict))

        return rval

    def parse_profile(self) -> str:
        return self.root_dict.get("profile", "16.04")

    def parse_license(self) -> Optional[str]:
        return self.root_dict.get("license")

    def parse_interactivetool(self):
        return self.root_dict.get("entry_points", [])

    def parse_python_template_version(self):
        python_template_version = self.root_dict.get("python_template_version")
        if python_template_version is not None:
            python_template_version = packaging.version.Version(python_template_version)
        return python_template_version

    def to_string(self):
        # TODO: Unit test for dumping/restoring
        return json.dumps(self.root_dict)


def _parse_test(i, test_dict) -> ToolSourceTest:
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
            new_outputs.append({"name": key, "value": file, "attributes": attributes})
    else:
        for output in outputs:
            name = output["name"]
            value = output.get("file", None)
            attributes = output
            new_outputs.append({"name": name, "value": value, "attributes": attributes})

    for output in new_outputs:
        attributes = output["attributes"]
        defaults = {
            "compare": "diff",
            "lines_diff": 0,
            "delta": DEFAULT_DELTA,
            "delta_frac": DEFAULT_DELTA_FRAC,
            "sort": DEFAULT_SORT,
            "decompress": DEFAULT_DECOMPRESS,
        }
        # TODO
        attributes["extra_files"] = []
        # TODO
        attributes["metadata"] = {}
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
    test_dict["expect_failure"] = test_dict.get("expect_failure", False)
    test_dict["expect_test_failure"] = test_dict.get("expect_test_failure", False)
    return test_dict


def to_test_assert_list(assertions) -> AssertionList:
    def expand_dict_form(item):
        key, value = item
        new_value = value.copy()
        new_value["that"] = key
        return new_value

    if is_dict(assertions):
        assertions = map(expand_dict_form, assertions.items())

    assert_list: List[AssertionDict] = []
    for assertion in assertions:
        # TODO: not handling nested assertions correctly,
        # not sure these are used though.
        if "that" not in assertion:
            new_assertion = {}
            for assertion_key, assertion_value in assertion.items():
                new_assertion["that"] = assertion_key
                new_assertion.update(assertion_value)
            assertion = new_assertion
        children = assertion.pop("asserts", assertion.pop("children", []))
        # if there are no nested assertions then children should be []
        # but to_test_assert_list would return None
        if children:
            children = to_test_assert_list(children)
        assert_dict: AssertionDict = dict(
            tag=assertion["that"],
            attributes=assertion,
            children=children,
        )
        assert_list.append(assert_dict)

    return assert_list or None  # XML variant is None if no assertions made


# Planemo depends on this and was never updated unfortunately.
# https://github.com/galaxyproject/planemo/blob/master/planemo/test/_check_output.py
__to_test_assert_list = to_test_assert_list


class YamlPageSource(PageSource):
    def __init__(self, inputs_list):
        self.inputs_list = inputs_list

    def parse_input_sources(self):
        return list(map(YamlInputSource, self.inputs_list))


class YamlInputSource(InputSource):
    def __init__(self, input_dict, trusted: bool = True):
        self.input_dict = input_dict
        self.trusted = trusted

    def get(self, key, default=None):
        return self.input_dict.get(key, default)

    def get_bool(self, key, default):
        return self.input_dict.get(key, default)

    def get_bool_or_none(self, key, default):
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

    def parse_validators(self) -> List[AnyValidatorModel]:
        return parse_dict_validators(self.input_dict.get("validators", []), trusted=self.trusted)

    def parse_static_options(self) -> List[Tuple[str, str, bool]]:
        static_options = []
        input_dict = self.input_dict
        for option in input_dict.get("options", {}):
            value = option.get("value")
            label = option.get("label", value)
            selected = option.get("selected", False)
            static_options.append((label, value, selected))
        return static_options

    def parse_default(self) -> Optional[Dict[str, Any]]:
        input_dict = self.input_dict
        default_def = input_dict.get("default", None)
        return default_def


def _ensure_has(dict, defaults):
    for key, value in defaults.items():
        if key not in dict:
            dict[key] = value
