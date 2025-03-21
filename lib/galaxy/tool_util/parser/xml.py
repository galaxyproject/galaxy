import itertools
import json
import logging
import math
import os
import re
import uuid
from typing import (
    Any,
    cast,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
)

from packaging.version import Version

from galaxy.tool_util.deps import requirements
from galaxy.tool_util.parser.util import (
    DEFAULT_DECOMPRESS,
    DEFAULT_DELTA,
    DEFAULT_DELTA_FRAC,
    DEFAULT_EPS,
    DEFAULT_METRIC,
    DEFAULT_PIN_LABELS,
    DEFAULT_SORT,
)
from galaxy.util import (
    Element,
    ElementTree,
    string_as_bool,
    string_as_bool_or_none,
    unicodify,
    XML,
    xml_text,
    xml_to_string,
)
from .interface import (
    AssertionList,
    Citation,
    DrillDownDynamicOptions,
    DrillDownOptionsDict,
    DynamicOptions,
    HelpContent,
    InputSource,
    OutputCompareType,
    PageSource,
    PagesSource,
    RequiredFiles,
    TestCollectionDefElementDict,
    TestCollectionDefElementObject,
    TestCollectionOutputDef,
    ToolSource,
    ToolSourceTest,
    ToolSourceTestInput,
    ToolSourceTestInputAttributes,
    ToolSourceTestInputs,
    ToolSourceTestOutput,
    ToolSourceTestOutputAttributes,
    ToolSourceTestOutputs,
    ToolSourceTests,
    XmlTestCollectionDefDict,
    XrefDict,
)
from .output_actions import (
    ToolOutputActionApp,
    ToolOutputActionGroup,
)
from .output_collection_def import dataset_collector_descriptions_from_elem
from .output_objects import (
    ChangeFormatModel,
    ToolExpressionOutput,
    ToolOutput,
    ToolOutputCollection,
    ToolOutputCollectionStructure,
)
from .parameter_validators import (
    AnyValidatorModel,
    parse_xml_validators,
)
from .stdio import (
    aggressive_error_checks,
    error_on_exit_code,
    StdioErrorLevel,
    ToolStdioExitCode,
    ToolStdioRegex,
)

if TYPE_CHECKING:
    from .output_objects import ToolOutputBase

log = logging.getLogger(__name__)


def inject_validates(inject):
    if inject == "api_key":
        return True
    elif inject == "entry_point_path_for_label":
        return True
    p = re.compile("^oidc_(id|access|refresh)_token_(.*)$")
    match = p.match(inject)
    return match is not None


def destroy_tree(tree):
    root = tree.getroot()

    node_tracker = {root: [0, None]}

    for node in root.iterdescendants():
        parent = node.getparent()
        node_tracker[node] = [node_tracker[parent][0] + 1, parent]

    node_tracker = sorted(
        [(depth, parent, child) for child, (depth, parent) in node_tracker.items()], key=lambda x: x[0], reverse=True
    )

    for _, parent, child in node_tracker:
        if parent is None:
            break
        parent.remove(child)

    del tree


def parse_change_format(change_format: Iterable[Element]) -> List[ChangeFormatModel]:
    change_models: List[ChangeFormatModel] = []
    for change_elem in change_format:
        for when_elem in change_elem.findall("when"):
            when_elem = cast(Element, when_elem)
            value: Optional[str] = when_elem.get("value", None)
            format_: Optional[str] = when_elem.get("format", None)
            check: Optional[str] = when_elem.get("input", None)
            input_dataset: Optional[str] = None
            check_attribute: Optional[str] = None
            if check is not None:
                if "$" not in check:
                    check = f"${check}"
            else:
                input_dataset = when_elem.get("input_dataset", None)
                check_attribute = when_elem.get("attribute", None)
            change_models.append(
                ChangeFormatModel(
                    value=value,
                    format=format_,
                    input=check,
                    input_dataset=input_dataset,
                    check_attribute=check_attribute,
                )
            )
    return change_models


class XmlToolSource(ToolSource):
    """Responsible for parsing a tool from classic Galaxy representation."""

    language = "xml"

    def __init__(self, xml_tree: ElementTree, source_path=None, macro_paths=None):
        self.xml_tree = xml_tree
        self.root = self.xml_tree.getroot()
        self._source_path = source_path
        self._macro_paths = macro_paths or []
        self.legacy_defaults = Version(self.parse_profile()) == Version("16.01")
        self._string = xml_to_string(self.root)

    def to_string(self):
        return self._string

    def mem_optimize(self):
        destroy_tree(self.xml_tree)
        self.root = None
        self._xml_tree = None

    def parse_version(self) -> Optional[str]:
        return self.root.get("version", None)

    def parse_id(self):
        return self.root.get("id")

    def parse_tool_module(self):
        root = self.root
        if root.find("type") is not None:
            type_elem = root.find("type")
            module = type_elem.get("module", "galaxy.tools")
            cls = type_elem.get("class")
            return module, cls

        return None

    def parse_action_module(self):
        root = self.root
        action_elem = root.find("action")
        if action_elem is not None:
            module = action_elem.get("module")
            cls = action_elem.get("class")
            return module, cls
        else:
            return None

    def parse_tool_type(self):
        root = self.root
        return root.get("tool_type")

    def parse_name(self):
        return self.root.get("name") or self.parse_id()

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

    def parse_xrefs(self) -> List[XrefDict]:
        xrefs = self.root.find("xrefs")
        if xrefs is None:
            return []
        return [
            XrefDict(value=xref.text.strip(), reftype=str(xref.attrib["type"]))
            for xref in xrefs.findall("xref")
            if xref.get("type") and xref.text
        ]

    def parse_description(self) -> str:
        return xml_text(self.root, "description")

    def parse_icon(self) -> Optional[str]:
        icon_elem = self.root.find("icon")
        return icon_elem.get("src") if icon_elem is not None else None

    def parse_display_interface(self, default):
        return self._get_attribute_as_bool("display_interface", default)

    def parse_require_login(self, default):
        return self._get_attribute_as_bool("require_login", default)

    def parse_request_param_translation_elem(self):
        return self.root.find("request_param_translation")

    def parse_command(self):
        command_el = self._command_el
        return ((command_el is not None) and command_el.text) or None

    def parse_expression(self):
        """Return string containing command to run."""
        expression_el = self.root.find("expression")
        if expression_el is not None:
            expression_type = expression_el.get("type")
            if expression_type != "ecma5.1":
                raise Exception(f"Unknown expression type [{expression_type}] encountered")
            return expression_el.text
        return None

    def parse_environment_variables(self):
        environment_variables_el = self.root.find("environment_variables")
        if environment_variables_el is None:
            return []

        environment_variables = []
        for environment_variable_el in environment_variables_el.findall("environment_variable"):
            template = environment_variable_el.text
            inject = environment_variable_el.get("inject")
            if inject:
                assert inject_validates(inject)
            if inject == "entry_point_path_for_label":
                assert (
                    template
                ), 'Environment variable value must contain entry point label when inject="entry_point_path_for_label".'
            else:
                assert not (template and inject), "Cannot specify inject and environment variable template."
            definition = {
                "name": environment_variable_el.get("name"),
                "template": template,
                "inject": inject,
                "strip": string_as_bool(environment_variable_el.get("strip", False)),
            }
            environment_variables.append(definition)
        return environment_variables

    def parse_home_target(self):
        target = "job_home" if Version(self.parse_profile()) >= Version("18.01") else "shared_home"
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
            return ParallelismInfo(parallelism)
        return parallelism_info

    def parse_interactivetool(self):
        interactivetool_el = self.root.find("entry_points")
        rtt = []
        if interactivetool_el is None:
            return rtt
        for ep_el in interactivetool_el.findall("entry_point"):
            port = ep_el.find("port")
            assert port is not None, ValueError("A port is required for InteractiveTools")
            port = port.text.strip()
            url = ep_el.find("url")
            if url is not None:
                url = url.text.strip()
            name = ep_el.get("name", None)
            if name:
                name = name.strip()
            label = ep_el.get("label", None)
            if label:
                label = label.strip()
            requires_domain = string_as_bool(ep_el.attrib.get("requires_domain", False))
            requires_path_in_url = string_as_bool(ep_el.attrib.get("requires_path_in_url", False))
            requires_path_in_header_named = ep_el.get("requires_path_in_header_named", None)
            if requires_path_in_header_named:
                requires_path_in_header_named = requires_path_in_header_named.strip()
            rtt.append(
                dict(
                    port=port,
                    url=url,
                    name=name,
                    label=label,
                    requires_domain=requires_domain,
                    requires_path_in_url=requires_path_in_url,
                    requires_path_in_header_named=requires_path_in_header_named,
                )
            )
        return rtt

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

    @property
    def _outputs_el(self):
        return self.root.find("outputs")

    def _get_attribute_as_bool(self, attribute, default, elem=None):
        if elem is None:
            elem = self.root
        return string_as_bool(elem.get(attribute, default))

    def parse_required_files(self) -> Optional[RequiredFiles]:
        required_files = self.root.find("required_files")
        if required_files is None:
            return None

        def parse_include_exclude_list(tag_name):
            as_list = []
            for ref in required_files.findall(tag_name):
                path = ref.get("path")
                assert path is not None, f'"path" must be specified in {tag_name}'
                path_type = ref.get("type", "literal")
                as_list.append({"path": path, "path_type": path_type})
            return as_list

        as_dict = {}
        as_dict["extend_default_excludes"] = self._get_attribute_as_bool(
            "extend_default_excludes", True, elem=required_files
        )
        as_dict["includes"] = parse_include_exclude_list("include")
        as_dict["excludes"] = parse_include_exclude_list("exclude")
        return RequiredFiles.from_dict(as_dict)

    def parse_requirements_and_containers(self):
        return requirements.parse_requirements_from_xml(self.root, parse_resources=True)

    def parse_input_pages(self) -> "XmlPagesSource":
        return XmlPagesSource(self.root)

    def parse_provided_metadata_style(self):
        style = None
        out_elem = self._outputs_el
        if out_elem is not None and "provided_metadata_style" in out_elem.attrib:
            style = out_elem.attrib["provided_metadata_style"]

        if style is None:
            style = "legacy" if Version(self.parse_profile()) < Version("17.09") else "default"

        assert style in ["legacy", "default"]
        return style

    def parse_provided_metadata_file(self):
        provided_metadata_file = "galaxy.json"
        out_elem = self.root.find("outputs")
        if out_elem is not None and "provided_metadata_file" in out_elem.attrib:
            provided_metadata_file = out_elem.attrib["provided_metadata_file"]

        return provided_metadata_file

    def parse_outputs(self, app: Optional[ToolOutputActionApp] = None):
        out_elem = self.root.find("outputs")
        outputs: Dict[str, ToolOutputBase] = {}
        output_collections: Dict[str, ToolOutputCollection] = {}
        if out_elem is None:
            return outputs, output_collections

        data_dict: Dict[str, ToolOutput] = {}
        expression_dict: Dict[str, ToolExpressionOutput] = {}

        def _parse(data_elem, **kwds):
            output_def = self._parse_output(data_elem, app, **kwds)
            data_dict[output_def.name] = output_def
            return output_def

        for _ in out_elem.findall("data"):
            _parse(_)

        def _parse_expression(output_elem, app: Optional[ToolOutputActionApp] = None, **kwds):
            output_def = self._parse_expression_output(output_elem, app, **kwds)
            output_def.filters = output_elem.findall("filter")
            expression_dict[output_def.name] = output_def
            return output_def

        def _parse_collection(collection_elem: Element):
            name = collection_elem.get("name")
            assert name
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
            filters = collection_elem.findall("filter")

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
                assert output_name
                data = data_dict[output_name]
                assert data
                del data_dict[output_name]
                output_collection.outputs[output_name] = data
            output_collections[name] = output_collection

        for out_child in out_elem:
            if out_child.tag == "data":
                _parse(out_child)
            elif out_child.tag == "collection":
                _parse_collection(out_child)
            elif out_child.tag == "output":
                output_type = out_child.get("type")
                if output_type == "data":
                    _parse(out_child)
                elif output_type == "collection":
                    out_child.attrib["type"] = unicodify(out_child.get("collection_type"))
                    out_child.attrib["type_source"] = unicodify(out_child.get("collection_type_source"))
                    _parse_collection(out_child)
                else:
                    _parse_expression(out_child, app)
            else:
                log.warning(f"Unknown output tag encountered [{out_child.tag}]")

        for output_def in itertools.chain(data_dict.values(), expression_dict.values()):
            outputs[output_def.name] = output_def
        return outputs, output_collections

    def _parse_output(
        self,
        data_elem,
        app: Optional[ToolOutputActionApp] = None,
        default_format="data",
        default_format_source=None,
        default_metadata_source="",
        expression_type=None,
    ):
        from_expression = data_elem.get("from")
        output = ToolOutput(data_elem.get("name"), from_expression=from_expression)
        output_format = data_elem.get("format", default_format)
        auto_format = string_as_bool(data_elem.get("auto_format", "false"))
        if auto_format and output_format != "data":
            raise ValueError("Setting format and auto_format is not supported at this time.")
        elif auto_format:
            output_format = "_sniff_"
        output.format = output_format
        output.change_format = parse_change_format(data_elem.findall("change_format"))
        output.format_source = data_elem.get("format_source", default_format_source)
        output.default_identifier_source = data_elem.get("default_identifier_source", "None")
        output.metadata_source = data_elem.get("metadata_source", default_metadata_source)
        output.parent = data_elem.get("parent", None)
        output.label = xml_text(data_elem, "label", None)
        output.count = int(data_elem.get("count", 1))
        output.filters = data_elem.findall("filter")
        output.from_work_dir = data_elem.get("from_work_dir", None)
        profile_version = Version(self.parse_profile())
        if output.from_work_dir and profile_version < Version("21.09"):
            # We started quoting from_work_dir outputs in 21.09.
            # Prior to quoting, trailing spaces had no effect.
            # This ensures that old tools continue to work.
            output.from_work_dir = output.from_work_dir.strip()
        output.hidden = string_as_bool(data_elem.get("hidden", ""))
        if app is not None:
            # poor design here driven entirely by pragmatism in refactoring, ToolOutputActionGroup
            # belongs in galaxy-tool because it uses app heavily. Breaking the output objects
            # into app-aware things and dumb models would be a large project but superior design
            # and decomposition.
            output.actions = ToolOutputActionGroup(app, data_elem.find("actions"))
        output.dataset_collector_descriptions = dataset_collector_descriptions_from_elem(
            data_elem, legacy=self.legacy_defaults
        )
        return output

    def _parse_expression_output(self, output_elem, app: Optional[ToolOutputActionApp] = None, **kwds):
        output_type = output_elem.get("type")
        from_expression = output_elem.get("from")
        output = ToolExpressionOutput(
            output_elem.get("name"),
            output_type,
            from_expression,
        )
        output.path = output_elem.get("value")
        output.label = xml_text(output_elem, "label", None)

        output.hidden = string_as_bool(output_elem.get("hidden", ""))
        if app is not None:
            output.actions = ToolOutputActionGroup(app, output_elem.find("actions"))
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
                raise ValueError(f"Unknown detect_errors value encountered [{detect_errors}]")
        elif len(self.root.findall("stdio")) == 0 and not self.legacy_defaults:
            exit_codes, regexes = error_on_exit_code()
        else:
            exit_codes = []
            regexes = []

        if len(self.root.findall("stdio")) > 0:
            parser = StdioParser(self.root)
            exit_codes = parser.stdio_exit_codes + exit_codes
            regexes = parser.stdio_regexes + regexes

        return exit_codes, regexes

    def parse_strict_shell(self):
        command_el = self._command_el
        if Version(self.parse_profile()) < Version("20.09"):
            default = "False"
        else:
            default = "True"
        if command_el is not None:
            return string_as_bool(command_el.get("strict", default))
        else:
            return string_as_bool(default)

    def parse_help(self) -> Optional[HelpContent]:
        help_elem = self.root.find("help")
        if help_elem is None:
            return None

        help_format = help_elem.get("format", "restructuredtext")
        content = help_elem.text or ""
        return HelpContent(format=help_format, content=content)

    @property
    def macro_paths(self):
        return self._macro_paths

    @property
    def source_path(self):
        return self._source_path

    def parse_tests_to_dict(self) -> ToolSourceTests:
        tests_elem = self.root.find("tests")
        tests: List[ToolSourceTest] = []
        rval: ToolSourceTests = dict(tests=tests)

        if tests_elem is not None:
            for i, test_elem in enumerate(tests_elem.findall("test")):
                profile = self.parse_profile()
                tests.append(_test_elem_to_dict(test_elem, i, profile))

        return rval

    def parse_profile(self) -> str:
        # Pre-16.04 or default XML defaults
        # - Use standard error for error detection.
        # - Don't run shells with -e
        # - Auto-check for implicit multiple outputs.
        # - Auto-check for $param_file.
        # - Enable buggy interpreter attribute.
        return self.root.get("profile", "16.01")

    def parse_license(self) -> Optional[str]:
        return self.root.get("license")

    def parse_citations(self) -> List[Citation]:
        """Return a list of citations."""
        citations: List[Citation] = []
        root = self.root
        citations_elem = root.find("citations")
        if citations_elem is None:
            return citations

        for citation_elem in citations_elem:
            citation = parse_citation_elem(citation_elem)
            if citation:
                citations.append(citation)

        return citations

    def parse_python_template_version(self):
        python_template_version = self.root.get("python_template_version")
        if python_template_version is not None:
            python_template_version = Version(python_template_version)
        return python_template_version

    def parse_creator(self):
        creators_el = self.root.find("creator")
        if creators_el is None:
            return None

        creators = []
        for creator_el in creators_el:
            creator_as_dict = {}
            if creator_el.tag == "person":
                clazz = "Person"
            elif creator_el.tag == "organization":
                clazz = "Organization"
            else:
                continue
            creator_as_dict["class"] = clazz
            creator_as_dict.update(creator_el.attrib)
            creators.append(creator_as_dict)
        return creators


def _test_elem_to_dict(test_elem, i, profile=None) -> ToolSourceTest:
    rval: ToolSourceTest = dict(
        outputs=__parse_output_elems(test_elem),
        output_collections=__parse_output_collection_elems(test_elem, profile=profile),
        inputs=__parse_input_elems(test_elem, i),
        expect_num_outputs=test_elem.get("expect_num_outputs"),
        command=__parse_assert_list_from_elem(test_elem.find("assert_command")),
        command_version=__parse_assert_list_from_elem(test_elem.find("assert_command_version")),
        stdout=__parse_assert_list_from_elem(test_elem.find("assert_stdout")),
        stderr=__parse_assert_list_from_elem(test_elem.find("assert_stderr")),
        expect_exit_code=test_elem.get("expect_exit_code"),
        expect_failure=string_as_bool(test_elem.get("expect_failure", False)),
        expect_test_failure=string_as_bool(test_elem.get("expect_test_failure", False)),
        maxseconds=test_elem.get("maxseconds", None),
    )
    _copy_to_dict_if_present(test_elem, rval, ["num_outputs"])
    return rval


def __parse_input_elems(test_elem, i) -> ToolSourceTestInputs:
    __expand_input_elems(test_elem)
    return __parse_inputs_elems(test_elem, i)


def __parse_output_elems(test_elem) -> ToolSourceTestOutputs:
    outputs: ToolSourceTestOutputs = []
    for output_elem in test_elem.findall("output"):
        name, file, attributes = __parse_output_elem(output_elem)
        outputs.append(ToolSourceTestOutput({"name": name, "value": file, "attributes": attributes}))
    return outputs


def __parse_output_elem(output_elem):
    attrib = _element_to_dict(output_elem)
    name = attrib.pop("name", None)
    if name is None:
        raise Exception("Test output does not have a 'name'")
    file, attributes = __parse_test_attributes(output_elem, attrib, parse_discovered_datasets=True)
    return name, file, attributes


def __parse_command_elem(test_elem):
    assert_elem = test_elem.find("command")
    return __parse_assert_list_from_elem(assert_elem)


def __parse_output_collection_elems(test_elem, profile=None):
    output_collections = []
    for output_collection_elem in test_elem.findall("output_collection"):
        output_collection_def = __parse_output_collection_elem(output_collection_elem, profile=profile)
        output_collections.append(output_collection_def)
    return output_collections


def __parse_output_collection_elem(output_collection_elem, profile=None):
    attrib = _element_to_dict(output_collection_elem)
    name = attrib.pop("name", None)
    if name is None:
        raise Exception("Test output collection does not have a 'name'")
    element_tests = __parse_element_tests(output_collection_elem, profile=profile)
    return TestCollectionOutputDef(name, attrib, element_tests).to_dict()


def __parse_element_tests(parent_element, profile=None):
    element_tests = {}
    for idx, element in enumerate(parent_element.findall("element")):
        element_attrib: dict = _element_to_dict(element)
        identifier = element_attrib.pop("name", None)
        if identifier is None:
            raise Exception("Test primary dataset does not have a 'identifier'")
        element_tests[identifier] = __parse_test_attributes(
            element, element_attrib, parse_elements=True, profile=profile
        )
        if profile and Version(profile) >= Version("20.09"):
            element_tests[identifier][1]["expected_sort_order"] = idx

    return element_tests


VALUE_OBJECT_UNSET = object()


def __parse_test_attributes(
    output_elem, attrib, parse_elements=False, parse_discovered_datasets=False, profile=None
) -> Tuple[Optional[str], ToolSourceTestOutputAttributes]:
    assert_list = __parse_assert_list(output_elem)

    # Allow either file or value to specify a target file to compare result with
    # file was traditionally used by outputs and value by extra files.
    file: Optional[str] = attrib.pop("file", attrib.pop("value", None))

    # File no longer required if an list of assertions was present.

    value_object: Any = VALUE_OBJECT_UNSET
    if "value_json" in attrib:
        value_object = json.loads(attrib.pop("value_json"))

    # Method of comparison
    compare: OutputCompareType = cast(OutputCompareType, attrib.pop("compare", "diff").lower())
    # Number of lines to allow to vary in logs (for dates, etc)
    lines_diff: int = int(attrib.pop("lines_diff", "0"))
    # Allow a file size to vary if sim_size compare
    delta: int = int(attrib.pop("delta", DEFAULT_DELTA))
    delta_frac: Optional[float] = float(attrib["delta_frac"]) if "delta_frac" in attrib else DEFAULT_DELTA_FRAC
    sort: bool = string_as_bool(attrib.pop("sort", DEFAULT_SORT))
    decompress: bool = string_as_bool(attrib.pop("decompress", DEFAULT_DECOMPRESS))
    # `location` may contain an URL to a remote file that will be used to download `file` (if not already present on disk).
    location: Optional[str] = attrib.get("location")
    if location and file is None:
        file = os.path.basename(location)  # If no file specified, try to get filename from URL last component
    # Parameters for "image_diff" comparison
    metric: str = attrib.pop("metric", DEFAULT_METRIC)
    eps: float = float(attrib.pop("eps", DEFAULT_EPS))
    pin_labels: Optional[Any] = attrib.pop("pin_labels", DEFAULT_PIN_LABELS)
    count: Optional[int] = None
    try:
        count = int(attrib.pop("count"))
    except KeyError:
        pass
    extra_files: List[Dict[str, Any]] = []
    ftype: Optional[str] = None
    if "ftype" in attrib:
        ftype = attrib["ftype"]
    for extra in output_elem.findall("extra_files"):
        extra_files.append(__parse_extra_files_elem(extra))
    metadata: Dict[str, Any] = {}
    for metadata_elem in output_elem.findall("metadata"):
        metadata[metadata_elem.get("name")] = metadata_elem.get("value")
    md5sum = attrib.get("md5", None)
    checksum = attrib.get("checksum", None)
    element_tests: Dict[str, Any] = {}
    if parse_elements:
        element_tests = __parse_element_tests(output_elem, profile=profile)

    primary_datasets: Dict[str, Any] = {}
    if parse_discovered_datasets:
        for primary_elem in output_elem.findall("discovered_dataset") or []:
            primary_attrib = _element_to_dict(primary_elem)
            designation = primary_attrib.pop("designation", None)
            if designation is None:
                raise Exception("Test primary dataset does not have a 'designation'")
            primary_datasets[designation] = __parse_test_attributes(primary_elem, primary_attrib)

    has_checksum = md5sum or checksum
    has_nested_tests = extra_files or element_tests or primary_datasets
    has_object = value_object is not VALUE_OBJECT_UNSET
    if not (assert_list or file or metadata or has_checksum or has_nested_tests or has_object):
        raise Exception(
            "Test output defines nothing to check (e.g. must have a 'file' check against, assertions to check, metadata or checksum tests, etc...)"
        )
    attributes = ToolSourceTestOutputAttributes(
        ftype=ftype,
        compare=compare,
        lines_diff=lines_diff,
        delta=delta,
        delta_frac=delta_frac,
        sort=sort,
        decompress=decompress,
        metric=metric,
        eps=eps,
        pin_labels=pin_labels,
        location=location,
        count=count,
        metadata=metadata,
        md5=md5sum,
        checksum=checksum,
        primary_datasets=primary_datasets,
        elements=element_tests,
        assert_list=assert_list,
        extra_files=extra_files,
    )
    if value_object is not VALUE_OBJECT_UNSET:
        attributes["object"] = value_object
    return file, attributes


def __parse_assert_list(output_elem) -> AssertionList:
    assert_elem = output_elem.find("assert_contents")
    return __parse_assert_list_from_elem(assert_elem)


def __parse_assert_list_from_elem(assert_elem) -> AssertionList:
    assert_list = None

    def convert_elem(elem):
        """Converts and XML element to a dictionary format, used by assertion checking code."""
        tag = elem.tag
        attributes = _element_to_dict(elem)
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
    attrib = _element_to_dict(extra)
    extra_type = attrib.pop("type", "file")
    extra_name = attrib.pop("name", None)
    assert (
        extra_type == "directory" or extra_name is not None
    ), f"extra_files type ({extra_type}) requires a name attribute"
    extra_value, extra_attributes = __parse_test_attributes(extra, attrib)
    return {"value": extra_value, "name": extra_name, "type": extra_type, "attributes": extra_attributes}


def __expand_input_elems(root_elem, prefix=""):
    __append_prefix_to_params(root_elem, prefix)

    repeat_elems = root_elem.findall("repeat")
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

    cond_elems = root_elem.findall("conditional")
    for cond_elem in cond_elems:
        new_prefix = __prefix_join(prefix, cond_elem.get("name"))
        __expand_input_elems(cond_elem, new_prefix)
        __pull_up_params(root_elem, cond_elem)

    section_elems = root_elem.findall("section")
    for section_elem in section_elems:
        new_prefix = __prefix_join(prefix, section_elem.get("name"))
        __expand_input_elems(section_elem, new_prefix)
        __pull_up_params(root_elem, section_elem)


def __append_prefix_to_params(elem, prefix):
    for param_elem in elem.findall("param"):
        param_elem.set("name", __prefix_join(prefix, param_elem.get("name")))


def __pull_up_params(parent_elem, child_elem):
    for param_elem in child_elem.findall("param"):
        parent_elem.append(param_elem)


def __prefix_join(prefix, name, index: Optional[int] = None):
    name = name if index is None else f"{name}_{index}"
    return name if not prefix else f"{prefix}|{name}"


def _copy_to_dict_if_present(elem, rval, attributes):
    for attribute in attributes:
        if attribute in elem.attrib:
            rval[attribute] = elem.get(attribute)
    return rval


def __parse_inputs_elems(test_elem, i) -> ToolSourceTestInputs:
    raw_inputs: ToolSourceTestInputs = []
    for param_elem in test_elem.findall("param"):
        raw_inputs.append(__parse_param_elem(param_elem, i))

    return raw_inputs


def _test_collection_def_dict(elem: Element) -> XmlTestCollectionDefDict:
    elements: List[TestCollectionDefElementDict] = []
    attrib: Dict[str, Any] = _element_to_dict(elem)
    collection_type = attrib["type"]
    name = attrib.get("name", "Unnamed Collection")
    for element in elem.findall("element"):
        element_attrib: Dict[str, Any] = _element_to_dict(element)
        element_identifier = element_attrib["name"]
        nested_collection_elem = element.find("collection")
        element_definition: TestCollectionDefElementObject
        if nested_collection_elem is not None:
            element_definition = _test_collection_def_dict(nested_collection_elem)
        else:
            element_definition = __parse_param_elem(element)
        elements.append({"element_identifier": element_identifier, "element_definition": element_definition})

    return XmlTestCollectionDefDict(
        model_class="TestCollectionDef",
        attributes=attrib,
        collection_type=collection_type,
        elements=elements,
        name=name,
    )


def __parse_param_elem(param_elem, i=0) -> ToolSourceTestInput:
    attrib: ToolSourceTestInputAttributes = dict(param_elem.attrib)
    if "values" in attrib:
        value = attrib["values"].split(",")
    elif "value" in attrib:
        value = attrib["value"]
    elif "value_json" in attrib:
        value = json.loads(attrib["value_json"])
    else:
        value = None

    if value is None and attrib.get("location", None) is not None:
        value = os.path.basename(attrib["location"])

    children_elem = param_elem
    if children_elem is not None:
        # At this time, we can assume having children only
        # occurs on DataToolParameter test items but this could
        # change and would cause the below parsing to change
        # based upon differences in children items
        attrib["metadata"] = {}
        attrib["composite_data"] = []
        attrib["edit_attributes"] = []
        # Composite datasets need to be renamed uniquely
        composite_data_name = None
        for child in children_elem:
            if child.tag == "composite_data":
                file_name = child.get("value")
                attrib["composite_data"].append(file_name)
                if composite_data_name is None:
                    # Generate a unique name; each test uses a
                    # fresh history.
                    composite_data_name = f"_COMPOSITE_RENAMED_t{i}_{uuid.uuid1().hex}"
            elif child.tag == "metadata":
                attrib["metadata"][child.get("name")] = child.get("value")
            elif child.tag == "edit_attributes":
                attrib["edit_attributes"].append(child)
            elif child.tag == "collection":
                attrib["collection"] = _test_collection_def_dict(child)
        if composite_data_name:
            # Composite datasets need implicit renaming;
            # inserted at front of list so explicit declarations
            # take precedence
            attrib["edit_attributes"].insert(0, {"type": "name", "value": composite_data_name})
    name = attrib.pop("name")
    return {"name": name, "value": value, "attributes": attrib}


class StdioParser:
    def __init__(self, root):
        try:
            self.stdio_exit_codes = []
            self.stdio_regexes = []

            # We should have a single <stdio> element, but handle the case for
            # multiples.
            # For every stdio element, add all of the exit_code and regex
            # subelements that we find:
            for stdio_elem in root.findall("stdio"):
                self.parse_stdio_exit_codes(stdio_elem)
                self.parse_stdio_regexes(stdio_elem)
        except Exception:
            log.exception("Exception in parse_stdio!")

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
            for exit_code_elem in stdio_elem.findall("exit_code"):
                exit_code = ToolStdioExitCode()
                # Each exit code has an optional description that can be
                # part of the "desc" or "description" attributes:
                exit_code.desc = exit_code_elem.get("desc")
                if exit_code.desc is None:
                    exit_code.desc = exit_code_elem.get("description")
                # Parse the error level:
                exit_code.error_level = self.parse_error_level(exit_code_elem.get("level"))
                code_range = exit_code_elem.get("range")
                if code_range is None:
                    code_range = exit_code_elem.get("value")
                if code_range is None:
                    log.warning("Tool stdio exit codes must have a range or value")
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
                if len(code_ranges) == 2:
                    if code_ranges[0] is None or "" == code_ranges[0]:
                        exit_code.range_start = -math.inf
                    else:
                        exit_code.range_start = int(code_ranges[0])
                    if code_ranges[1] is None or "" == code_ranges[1]:
                        exit_code.range_end = math.inf
                    else:
                        exit_code.range_end = int(code_ranges[1])
                # If we got more than one colon, then ignore the exit code.
                elif len(code_ranges) > 2:
                    log.warning(f"Invalid tool exit_code range {code_range} - ignored")
                    continue
                # Else we have a singular value. If it's not an integer, then
                # we'll just write a log message and skip this exit_code.
                else:
                    try:
                        exit_code.range_start = int(code_range)
                    except Exception:
                        log.error(code_range)
                        log.warning(f"Invalid range start for tool's exit_code {code_range}: exit_code ignored")
                        continue
                    exit_code.range_end = exit_code.range_start
                # TODO: Check if we got ">", ">=", "<", or "<=":
                # Check that the range, regardless of how we got it,
                # isn't bogus. If we have two infinite values, then
                # the start must be -inf and the end must be +inf.
                # So at least warn about this situation:
                if math.isinf(exit_code.range_start) and math.isinf(exit_code.range_end):
                    log.warning(f"Tool exit_code range {code_range} will match on all exit codes")
                self.stdio_exit_codes.append(exit_code)
        except Exception:
            log.exception("Exception in parse_stdio_exit_codes!")

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
            for regex_elem in stdio_elem.findall("regex"):
                # TODO: Fill in ToolStdioRegex
                regex = ToolStdioRegex()
                # Each regex has an optional description that can be
                # part of the "desc" or "description" attributes:
                regex.desc = regex_elem.get("desc")
                if regex.desc is None:
                    regex.desc = regex_elem.get("description")
                # Parse the error level
                regex.error_level = self.parse_error_level(regex_elem.get("level"))
                regex.match = regex_elem.get("match")
                if regex.match is None:
                    log.warning(
                        f"Ignoring tool's stdio regex element with attributes {regex_elem.attrib} - "
                        "the 'match' attribute must exist"
                    )
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
                    if not regex.stdout_match and not regex.stderr_match:
                        log.warning(
                            "Tool id %s: unable to determine if tool "
                            "stream source scanning is output, error, "
                            "or both. Defaulting to use both.",
                            self.id,
                        )
                        regex.stdout_match = True
                        regex.stderr_match = True
                self.stdio_regexes.append(regex)
        except Exception:
            log.exception("Exception in parse_stdio_exit_codes!")

    # TODO: This method doesn't have to be part of the Tool class.
    def parse_error_level(self, err_level):
        """
        Parses error level and returns error level enumeration. If
        unparsable, returns 'fatal'
        """
        return_level = StdioErrorLevel.FATAL
        try:
            if err_level:
                if re.search("log", err_level, re.IGNORECASE):
                    return_level = StdioErrorLevel.LOG
                elif re.search("qc", err_level, re.IGNORECASE):
                    return_level = StdioErrorLevel.QC
                elif re.search("warning", err_level, re.IGNORECASE):
                    return_level = StdioErrorLevel.WARNING
                elif re.search("fatal_oom", err_level, re.IGNORECASE):
                    return_level = StdioErrorLevel.FATAL_OOM
                elif re.search("fatal", err_level, re.IGNORECASE):
                    return_level = StdioErrorLevel.FATAL
                else:
                    log.debug(f"Tool {self.id}: error level {err_level} did not match log/warning/fatal")
        except Exception:
            log.exception("Exception in parse_error_level")
        return return_level


class XmlPagesSource(PagesSource):
    def __init__(self, root):
        self.input_elem = root.find("inputs")
        page_sources = []
        if self.input_elem is not None:
            pages_elem = self.input_elem.findall("page")
            for page in pages_elem or [self.input_elem]:
                page_sources.append(XmlPageSource(page))
        super().__init__(page_sources)

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
        return list(map(XmlInputSource, self.parent_elem))


class XmlDynamicOptions(DynamicOptions):

    def __init__(self, options_elem: Element, dynamic_option_code: Optional[str]):
        self._options_elem = options_elem
        self._dynamic_options_code = dynamic_option_code

    def elem(self) -> Element:
        return self._options_elem

    def get_dynamic_options_code(self) -> Optional[str]:
        """If dynamic options are a piece of code to eval, return it."""
        return self._dynamic_options_code

    def get_data_table_name(self) -> Optional[str]:
        """If dynamic options are loaded from a data table, return the name."""
        return self._options_elem.get("from_data_table") if self._options_elem is not None else None

    def get_index_file_name(self) -> Optional[str]:
        return self._options_elem.get("from_file") if self._options_elem is not None else None


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

    def get_bool_or_none(self, key, default):
        return string_as_bool_or_none(self.get(key, default))

    def parse_label(self):
        return xml_text(self.input_elem, "label")

    def parse_help(self):
        return xml_text(self.input_elem, "help")

    def parse_sanitizer_elem(self):
        return self.input_elem.find("sanitizer")

    def parse_validators(self) -> List[AnyValidatorModel]:
        return parse_xml_validators(self.input_elem)

    def parse_dynamic_options(self) -> Optional[XmlDynamicOptions]:
        """Return a XmlDynamicOptions to describe dynamic options if options elem is available."""
        options_elem = self.input_elem.find("options")
        dynamic_option_code = self.input_elem.get("dynamic_options")
        is_dynamic = options_elem is not None or dynamic_option_code is not None
        if is_dynamic:
            return XmlDynamicOptions(options_elem, dynamic_option_code)
        else:
            return None

    def parse_static_options(self) -> List[Tuple[str, str, bool]]:
        """
        >>> from galaxy.util import parse_xml_string_to_etree
        >>> xml = '<param><option value="a">A</option><option value="b">B</option></param>'
        >>> xis = XmlInputSource(parse_xml_string_to_etree(xml).getroot())
        >>> xis.parse_static_options()
        [('A', 'a', False), ('B', 'b', False)]
        >>> xml = '<param><option value="a"/><option value="b"/><option value="a" selected="true"/></param>'
        >>> xis = XmlInputSource(parse_xml_string_to_etree(xml).getroot())
        >>> xis.parse_static_options()
        [('a', 'a', True), ('b', 'b', False)]
        """

        deduplicated_static_options = {}

        elem = self.input_elem
        for option in elem.findall("option"):
            value = option.get("value")
            text = option.text or value
            selected = string_as_bool(option.get("selected", False))
            deduplicated_static_options[value] = (text, value, selected)
        return list(deduplicated_static_options.values())

    def parse_drill_down_dynamic_options(
        self, tool_data_path: Optional[str] = None
    ) -> Optional[DrillDownDynamicOptions]:
        elem = self.input_elem
        dynamic_options_raw = elem.get("dynamic_options", None)
        dynamic_options: Optional[str] = str(dynamic_options_raw) if dynamic_options_raw else None
        if dynamic_options is None:
            return None
        else:
            return XmlDrillDownDynamicOptions(code_block=dynamic_options)

    def parse_drill_down_static_options(
        self, tool_data_path: Optional[str] = None
    ) -> Optional[List[DrillDownOptionsDict]]:
        from_file = self.input_elem.get("from_file", None)
        if from_file:
            if not os.path.isabs(from_file):
                assert tool_data_path, "This tool cannot be parsed outside of a Galaxy context"
                from_file = os.path.join(tool_data_path, from_file)
            elem = XML(f"<root>{open(from_file).read()}</root>")
        else:
            elem = self.input_elem

        dynamic_options_elem = elem.get("dynamic_options", None)
        filter_elem = elem.get("filter", None)
        if dynamic_options_elem is not None and filter_elem is not None:
            return None

        root_options: List[DrillDownOptionsDict] = []
        options_elem = elem.find("options")
        assert options_elem, "Non-dynamic drilldown parameters must supply an options element"
        _recurse_drill_down_elems(root_options, options_elem.findall("option"))
        return root_options

    def parse_optional(self, default=None):
        """Return boolean indicating whether parameter is optional."""
        elem = self.input_elem
        if self.get("type") == "data_column":
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

    def parse_default(self) -> Optional[Dict[str, Any]]:
        def file_default_from_elem(elem):
            # TODO: hashes, created_from_basename, etc...
            return {"class": "File", "location": elem.get("location")}

        def read_elements(collection_elem):
            element_dicts = []
            elements = collection_elem.findall("element")
            for element in elements:
                identifier = element.get("name")
                subcollection_elem = element.find("collection")
                if subcollection_elem:
                    collection_type = subcollection_elem.get("collection_type")
                    element_dicts.append(
                        {
                            "class": "Collection",
                            "identifier": identifier,
                            "collection_type": collection_type,
                            "elements": read_elements(subcollection_elem),
                        }
                    )
                else:
                    element_dict = file_default_from_elem(element)
                    element_dict["identifier"] = identifier
                    element_dicts.append(element_dict)
            return element_dicts

        elem = self.input_elem
        element_type = self.input_elem.get("type")
        if element_type == "data":
            default_elem = elem.find("default")
            if default_elem is not None:
                return file_default_from_elem(default_elem)
            else:
                return None
        else:
            default_elem = elem.find("default")
            if default_elem is not None:
                default_elem = elem.find("default")
                collection_type = default_elem.get("collection_type")
                name = default_elem.get("name", elem.get("name"))
                return {
                    "class": "Collection",
                    "name": name,
                    "collection_type": collection_type,
                    "elements": read_elements(default_elem),
                }
            else:
                return None


class ParallelismInfo:
    """
    Stores the information (if any) for running multiple instances of the tool in parallel
    on the same set of inputs.
    """

    def __init__(self, tag):
        self.method = tag.get("method")
        if isinstance(tag, dict):
            items = tag.items()
        else:
            items = tag.attrib.items()
        self.attributes = dict([item for item in items if item[0] != "method"])
        if len(self.attributes) == 0:
            # legacy basic mode - provide compatible defaults
            self.attributes["split_size"] = 20
            self.attributes["split_mode"] = "number_of_parts"


def parse_citation_elem(citation_elem: Element) -> Optional[Citation]:
    if citation_elem.tag != "citation":
        return None

    citation_type = citation_elem.attrib.get("type", None)
    citation_raw_text = citation_elem.text
    assert citation_raw_text
    content = citation_raw_text.strip()

    return Citation(
        type=citation_type,
        content=content,
    )


class XmlDrillDownDynamicOptions(DrillDownDynamicOptions):

    def __init__(self, code_block: Optional[str]):
        self._code_block = code_block

    def from_code_block(self) -> Optional[str]:
        """Get a code block to do an eval on."""
        return self._code_block


def _element_to_dict(elem: Element) -> Dict[str, Any]:
    # every call to this function needs to be replaced with something more type safe and with
    # an actual typed dictionary - but centralizing this hack for now.
    return dict(elem.attrib)  # type: ignore [arg-type]


def _recurse_drill_down_elems(options: List[DrillDownOptionsDict], option_elems: List[Element]):
    for option_elem in option_elems:
        selected = string_as_bool(option_elem.get("selected", False))
        nested_options: List[DrillDownOptionsDict] = []
        value = option_elem.get("value")
        assert value
        current_option: DrillDownOptionsDict = DrillDownOptionsDict(
            {
                "name": option_elem.get("name"),
                "value": value,
                "options": nested_options,
                "selected": selected,
            }
        )
        _recurse_drill_down_elems(nested_options, option_elem.findall("option"))
        options.append(current_option)
