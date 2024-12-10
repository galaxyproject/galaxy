"""This module contains a linting functions for tool inputs."""

import ast
import re
import warnings
from typing import (
    Iterator,
    Optional,
    Tuple,
    TYPE_CHECKING,
)

from packaging.version import Version

from galaxy.tool_util.lint import Linter
from galaxy.util import string_as_bool
from ._util import (
    is_datasource,
    is_valid_cheetah_placeholder,
)
from ..parser.util import _parse_name

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser import ToolSource
    from galaxy.util.etree import (
        Element,
        ElementTree,
    )

lint_tool_types = ["*"]

ATTRIB_VALIDATOR_COMPATIBILITY = {
    "check": ["metadata"],
    "expression": ["substitute_value_in_message"],
    "table_name": [
        "dataset_metadata_in_data_table",
        "dataset_metadata_not_in_data_table",
        "value_in_data_table",
        "value_not_in_data_table",
    ],
    "filename": ["dataset_metadata_in_file"],
    "metadata_name": [
        "dataset_metadata_equal",
        "dataset_metadata_in_data_table",
        "dataset_metadata_not_in_data_table",
        "dataset_metadata_in_file",
        "dataset_metadata_in_range",
    ],
    "metadata_column": [
        "dataset_metadata_in_data_table",
        "dataset_metadata_not_in_data_table",
        "value_in_data_table",
        "value_not_in_data_table",
        "dataset_metadata_in_file",
    ],
    "line_startswith": ["dataset_metadata_in_file"],
    "min": ["in_range", "length", "dataset_metadata_in_range"],
    "max": ["in_range", "length", "dataset_metadata_in_range"],
    "exclude_min": ["in_range", "dataset_metadata_in_range"],
    "exclude_max": ["in_range", "dataset_metadata_in_range"],
    "split": ["dataset_metadata_in_file"],
    "skip": ["metadata"],
    "value": ["dataset_metadata_equal"],
    "value_json": ["dataset_metadata_equal"],
}

PARAMETER_VALIDATOR_TYPE_COMPATIBILITY = {
    "integer": ["in_range", "expression"],
    "float": ["in_range", "expression"],
    "data": [
        "metadata",
        "no_options",
        "unspecified_build",
        "dataset_ok_validator",
        "dataset_metadata_equal",
        "dataset_metadata_in_range",
        "dataset_metadata_in_file",
        "dataset_metadata_in_data_table",
        "dataset_metadata_not_in_data_table",
        "expression",
    ],
    "data_collection": [
        "metadata",
        "no_options",
        "unspecified_build",
        "dataset_ok_validator",
        "dataset_metadata_equal",
        "dataset_metadata_in_range",
        "dataset_metadata_in_file",
        "dataset_metadata_in_data_table",
        "dataset_metadata_not_in_data_table",
        "expression",
    ],
    "text": ["regex", "length", "empty_field", "value_in_data_table", "value_not_in_data_table", "expression"],
    "select": [
        "in_range",
        "no_options",
        "regex",
        "length",
        "empty_field",
        "value_in_data_table",
        "value_not_in_data_table",
        "expression",
    ],
    "drill_down": [
        "no_options",
        "regex",
        "length",
        "empty_field",
        "value_in_data_table",
        "value_not_in_data_table",
        "expression",
    ],
    "data_column": [
        "no_options",
        "regex",
        "length",
        "empty_field",
        "value_in_data_table",
        "value_not_in_data_table",
        "expression",
    ],
}

PARAM_TYPE_CHILD_COMBINATIONS = [
    ("./options", ["data", "select", "drill_down"]),
    ("./options/option", ["drill_down"]),
    ("./options/column", ["data", "select"]),
]

# TODO lint for valid param type - attribute combinations
# TODO check if dataset is available for filters referring other datasets
# TODO check if ref input param is present for from_dataset


class InputsNum(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tool_node = tool_xml.find("./inputs")
        if tool_node is None:
            tool_node = tool_xml.getroot()
        num_inputs = len(tool_xml.findall("./inputs//param"))
        if num_inputs:
            lint_ctx.info(f"Found {num_inputs} input parameters.", linter=cls.name(), node=tool_node)


class InputsMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tool_node = tool_xml.find("./inputs")
        if tool_node is None:
            tool_node = tool_xml.getroot()
        num_inputs = len(tool_xml.findall("./inputs//param"))
        if num_inputs == 0 and not is_datasource(tool_xml):
            lint_ctx.warn("Found no input parameters.", linter=cls.name(), node=tool_node)


class InputsMissingDataSource(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tool_node = tool_xml.find("./inputs")
        if tool_node is None:
            tool_node = tool_xml.getroot()
        num_inputs = len(tool_xml.findall("./inputs//param"))
        if num_inputs == 0 and is_datasource(tool_xml):
            lint_ctx.info("No input parameters, OK for data sources", linter=cls.name(), node=tool_node)


class InputsDatasourceTags(Linter):
    """
    Lint that datasource tools have display and uihints tags
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tool_node = tool_xml.find("./inputs")
        if tool_node is None:
            tool_node = tool_xml.getroot()
        inputs = tool_xml.findall("./inputs//param")
        if is_datasource(tool_xml):
            # TODO only display is subtag of inputs, uihints is a separate top level tag (supporting only attrib minwidth)
            for datasource_tag in ("display", "uihints"):
                if not any(param.tag == datasource_tag for param in inputs):
                    lint_ctx.info(
                        f"{datasource_tag} tag usually present in data sources", linter=cls.name(), node=tool_node
                    )


def _iter_param(tool_xml: "ElementTree") -> Iterator[Tuple["Element", str]]:
    for param in tool_xml.findall("./inputs//param"):
        if "name" not in param.attrib and "argument" not in param.attrib:
            continue
        param_name = _parse_name(param.attrib.get("name"), param.attrib.get("argument"))
        yield param, param_name


def _iter_param_type(tool_xml: "ElementTree") -> Iterator[Tuple["Element", str, str]]:
    for param, param_name in _iter_param(tool_xml):
        if "type" not in param.attrib:
            continue
        param_type = param.attrib["type"]
        if param_type == "":
            continue
        yield param, param_name, param_type


class InputsName(Linter):
    """
    Lint params define a name
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param in tool_xml.findall("./inputs//param"):
            if "name" not in param.attrib and "argument" not in param.attrib:
                lint_ctx.error("Found param input with no name specified.", linter=cls.name(), node=param)


class InputsNameRedundantArgument(Linter):
    """
    Lint params define a name
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param in tool_xml.findall("./inputs//param"):
            if "name" in param.attrib and "argument" in param.attrib:
                param_name = _parse_name(param.attrib.get("name"), param.attrib.get("argument"))
                if param.attrib.get("name") == _parse_name(None, param.attrib.get("argument")):
                    lint_ctx.warn(
                        f"Param input [{param_name}] 'name' attribute is redundant if argument implies the same name.",
                        linter=cls.name(),
                        node=param,
                    )


# TODO redundant with InputsNameValid
class InputsNameEmpty(Linter):
    """
    Lint params define a non-empty name
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name in _iter_param(tool_xml):
            if param_name.strip() == "":
                lint_ctx.error("Param input with empty name.", linter=cls.name(), node=param)


class InputsNameValid(Linter):
    """
    Lint params define valid cheetah placeholder
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name in _iter_param(tool_xml):
            if param_name != "" and not is_valid_cheetah_placeholder(param_name):
                lint_ctx.warn(
                    f"Param input [{param_name}] is not a valid Cheetah placeholder.", linter=cls.name(), node=param
                )


def _param_path(param: "Element", param_name: str) -> str:
    path = [param_name]
    parent = param
    while True:
        parent = parent.getparent()
        if parent.tag == "inputs":
            break
        # parameters of the same name in different when branches are allowed
        # just add the value of the when branch to the path (this also allows
        # that the conditional select has the same name as params in the whens)
        if parent.tag == "when":
            path.append(str(parent.attrib.get("value")))
        else:
            path.append(str(parent.attrib.get("name")))
    return ".".join(reversed(path))


class InputsNameDuplicate(Linter):
    """
    Lint params with duplicate names
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        input_names = set()
        for param, param_name in _iter_param(tool_xml):
            # check for parameters with duplicate names
            path = _param_path(param, param_name)
            if path in input_names:
                lint_ctx.error(
                    f"Tool defines multiple parameters with the same name: '{path}'", linter=cls.name(), node=param
                )
            input_names.add(path)


class InputsNameDuplicateOutput(Linter):
    """
    Lint params names that are also used in outputs
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        input_names = set()
        for param, param_name in _iter_param(tool_xml):
            input_names.add(_param_path(param, param_name))

        # check if there is an output with the same name as an input
        outputs = tool_xml.findall("./outputs/*")
        for output in outputs:
            if output.get("name") in input_names:
                lint_ctx.error(
                    f'Tool defines an output with a name equal to the name of an input: \'{output.get("name")}\'',
                    linter=cls.name(),
                    node=output,
                )


class InputsTypeChildCombination(Linter):
    """
    Lint for invalid parameter type child combinations
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            # lint for valid param type - child node combinations
            for ptcc in PARAM_TYPE_CHILD_COMBINATIONS:
                if param.find(ptcc[0]) is not None and param_type not in ptcc[1]:
                    lint_ctx.error(
                        f"Parameter [{param_name}] '{ptcc[0]}' tags are only allowed for parameters of type {ptcc[1]}",
                        linter=cls.name(),
                        node=param,
                    )


class InputsDataFormat(Linter):
    """
    Lint for data params wo format
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "data":
                continue
            if "format" not in param.attrib:
                lint_ctx.warn(
                    f"Param input [{param_name}] with no format specified - 'data' format will be assumed.",
                    linter=cls.name(),
                    node=param,
                )


class InputsDataOptionsMultiple(Linter):
    """
    Lint for data params with multiple options tags
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "data":
                continue
            options = param.findall("./options")
            if len(options) > 1:
                lint_ctx.error(
                    f"Data parameter [{param_name}] contains multiple options elements.",
                    linter=cls.name(),
                    node=options[1],
                )


class InputsDataOptionsAttrib(Linter):
    """
    Lint for data params with options that have invalid attributes
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "data":
                continue
            options = param.find("./options")
            if options is None:
                continue
            for oa in options.attrib:
                if oa != "options_filter_attribute":
                    lint_ctx.error(
                        f"Data parameter [{param_name}] uses invalid attribute: {oa}", linter=cls.name(), node=param
                    )


class InputsDataOptionsFilterAttribFiltersType(Linter):
    """
    Lint for valid filter types for data parameters
    if options set options_filter_attribute
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "data":
                continue
            options = param.find("./options")
            if options is None:
                continue
            for filter in param.findall("./options/filter"):
                if "options_filter_attribute" in options.attrib:
                    if filter.get("type") != "data_meta":
                        lint_ctx.error(
                            f'Data parameter [{param_name}] for filters only type="data_meta" is allowed, found type="{filter.get("type")}"',
                            linter=cls.name(),
                            node=filter,
                        )


class InputsDataOptionsFiltersType(Linter):
    """
    Lint for valid filter types for data parameters
    if options do not set options_filter_attribute
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "data":
                continue
            options = param.find("./options")
            if options is None:
                continue
            for filter in param.findall("./options/filter"):
                if "options_filter_attribute" not in options.attrib:
                    if filter.get("key") != "dbkey" or filter.get("type") != "data_meta":
                        lint_ctx.error(
                            f'Data parameter [{param_name}] for filters only type="data_meta" and key="dbkey" are allowed, found type="{filter.get("type")}" and key="{filter.get("key")}"',
                            linter=cls.name(),
                            node=filter,
                        )


class InputsDataOptionsFiltersRef(Linter):
    """
    Lint for set ref for filters of data parameters
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "data":
                continue
            options = param.find("./options")
            if options is None:
                continue
            for filter in param.findall("./options/filter"):
                if not filter.get("ref"):
                    lint_ctx.error(
                        f"Data parameter [{param_name}] filter needs to define a ref attribute",
                        linter=cls.name(),
                        node=filter,
                    )


class InputsSelectDynamicOptions(Linter):
    """
    Lint for select with deprecated dynamic_options attribute
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "select":
                continue
            dynamic_options = param.get("dynamic_options", None)
            if dynamic_options is not None:
                lint_ctx.warn(
                    f"Select parameter [{param_name}] uses deprecated 'dynamic_options' attribute.",
                    linter=cls.name(),
                    node=param,
                )


class InputsSelectOptionsDef(Linter):
    """
    Lint for valid ways to define select options
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "select":
                continue
            dynamic_options = param.get("dynamic_options", None)
            options = param.findall("./options")
            select_options = param.findall("./option")
            if param.getparent().tag != "conditional":
                if (dynamic_options is not None) + (len(options) > 0) + (len(select_options) > 0) != 1:
                    lint_ctx.error(
                        f"Select parameter [{param_name}] options have to be defined by either 'option' children elements, a 'options' element or the 'dynamic_options' attribute.",
                        linter=cls.name(),
                        node=param,
                    )


class InputsSelectOptionsDefConditional(Linter):
    """
    Lint for valid ways to define select options
    (for a select in a conditional)
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "select":
                continue
            dynamic_options = param.get("dynamic_options", None)
            options = param.findall("./options")
            select_options = param.findall("./option")
            if param.getparent().tag == "conditional":
                if len(select_options) == 0 or dynamic_options is not None or len(options) > 0:
                    lint_ctx.error(
                        f"Select parameter of a conditional [{param_name}] options have to be defined by 'option' children elements.",
                        linter=cls.name(),
                        node=param,
                    )


# TODO xsd
class InputsSelectOptionValueMissing(Linter):
    """
    Lint for select option tags without value
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "select":
                continue
            select_options = param.findall("./option")
            if any("value" not in option.attrib for option in select_options):
                lint_ctx.error(
                    f"Select parameter [{param_name}] has option without value", linter=cls.name(), node=param
                )


class InputsSelectOptionDuplicateValue(Linter):
    """
    Lint for select option with same value
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "select":
                continue
            select_options = param.findall("./option")
            select_options_values = []
            for option in select_options:
                value = option.attrib.get("value", "")
                select_options_values.append((value, option.attrib.get("selected", "false")))
            if len(set(select_options_values)) != len(select_options_values):
                lint_ctx.error(
                    f"Select parameter [{param_name}] has multiple options with the same value",
                    linter=cls.name(),
                    node=param,
                )


class InputsSelectOptionDuplicateText(Linter):
    """
    Lint for select option with same text
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "select":
                continue
            select_options = param.findall("./option")
            select_options_texts = []
            for option in select_options:
                if option.text is None:
                    text = option.attrib.get("value", "").capitalize()
                else:
                    text = option.text
                select_options_texts.append((text, option.attrib.get("selected", "false")))
            if len(set(select_options_texts)) != len(select_options_texts):
                lint_ctx.error(
                    f"Select parameter [{param_name}] has multiple options with the same text content",
                    linter=cls.name(),
                    node=param,
                )


class InputsSelectOptionsMultiple(Linter):
    """
    Lint dynamic options select for multiple options tags
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "select":
                continue
            options = param.findall("./options")
            if len(options) > 1:
                lint_ctx.error(
                    f"Select parameter [{param_name}] contains multiple options elements.",
                    linter=cls.name(),
                    node=options[1],
                )


class InputsSelectOptionsDefinesOptions(Linter):
    """
    Lint dynamic options select for the potential to define options
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "select":
                continue
            options = param.find("./options")
            if options is None:
                continue
            filter_adds_options = any(
                f.get("type", None) in ["add_value", "data_meta"] for f in param.findall("./options/filter")
            )
            from_file = options.get("from_file", None)
            from_parameter = options.get("from_parameter", None)
            # TODO check if input param is present for from_dataset
            from_dataset = options.get("from_dataset", None)
            from_data_table = options.get("from_data_table", None)
            from_url = options.get("from_url", None)

            if (
                from_file is None
                and from_parameter is None
                and from_dataset is None
                and from_data_table is None
                and from_url is None
                and not filter_adds_options
            ):
                lint_ctx.error(
                    f"Select parameter [{param_name}] options tag defines no options. Use 'from_dataset', 'from_data_table', or a filter that adds values.",
                    linter=cls.name(),
                    node=options,
                )


class InputsSelectOptionsDeprecatedAttr(Linter):
    """
    Lint dynamic options select deprecated attributes
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "select":
                continue
            options = param.find("./options")
            if options is None:
                continue
            for deprecated_attr in ["from_file", "from_parameter", "options_filter_attribute", "transform_lines"]:
                if options.get(deprecated_attr) is not None:
                    lint_ctx.warn(
                        f"Select parameter [{param_name}] options uses deprecated '{deprecated_attr}' attribute.",
                        linter=cls.name(),
                        node=options,
                    )


class InputsSelectOptionsFromDatasetAndDatatable(Linter):
    """
    Lint dynamic options select for from_dataset and from_data_table
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "select":
                continue
            options = param.find("./options")
            if options is None:
                continue
            from_dataset = options.get("from_dataset", None)
            from_data_table = options.get("from_data_table", None)
            if from_dataset is not None and from_data_table is not None:
                lint_ctx.error(
                    f"Select parameter [{param_name}] options uses 'from_dataset' and 'from_data_table' attribute.",
                    linter=cls.name(),
                    node=options,
                )


class InputsSelectOptionsMetaFileKey(Linter):
    """
    Lint dynamic options select: meta_file_key attribute can only be used with from_dataset
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "select":
                continue
            options = param.find("./options")
            if options is None:
                continue
            from_dataset = options.get("from_dataset", None)
            if options.get("meta_file_key", None) is not None and from_dataset is None:
                lint_ctx.error(
                    f"Select parameter [{param_name}] 'meta_file_key' is only compatible with 'from_dataset'.",
                    linter=cls.name(),
                    node=options,
                )


class InputsBoolDistinctValues(Linter):
    """
    Lint booleans for distinct true/false value
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "boolean":
                continue
            profile = tool_source.parse_profile()
            truevalue = param.attrib.get("truevalue", "true")
            falsevalue = param.attrib.get("falsevalue", "false")
            problematic_booleans_allowed = Version(profile) < Version("23.1")
            lint_level = lint_ctx.warn if problematic_booleans_allowed else lint_ctx.error
            if truevalue == falsevalue:
                lint_level(
                    f"Boolean parameter [{param_name}] needs distinct 'truevalue' and 'falsevalue' values.",
                    linter=cls.name(),
                    node=param,
                )


class InputsBoolProblematic(Linter):
    """
    Lint booleans for problematic values, i.e. truevalue being false and vice versa
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type != "boolean":
                continue
            profile = tool_source.parse_profile()
            truevalue = param.attrib.get("truevalue", "true")
            falsevalue = param.attrib.get("falsevalue", "false")
            problematic_booleans_allowed = Version(profile) < Version("23.1")
            lint_level = lint_ctx.warn if problematic_booleans_allowed else lint_ctx.error
            if truevalue.lower() == "false":
                lint_level(
                    f"Boolean parameter [{param_name}] has invalid truevalue [{truevalue}].",
                    linter=cls.name(),
                    node=param,
                )
            if falsevalue.lower() == "true":
                lint_level(
                    f"Boolean parameter [{param_name}] has invalid falsevalue [{falsevalue}].",
                    linter=cls.name(),
                    node=param,
                )


class InputsSelectSingleCheckboxes(Linter):
    """
    Lint selects that allow only a single selection but display as checkboxes
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type not in ["select", "data_column", "drill_down"]:
                continue
            multiple = string_as_bool(param.attrib.get("multiple", "false"))
            if param.attrib.get("display") == "checkboxes":
                if not multiple:
                    lint_ctx.error(
                        f'Select [{param_name}] `display="checkboxes"` is incompatible with `multiple="false"`, remove the `display` attribute',
                        linter=cls.name(),
                        node=param,
                    )


class InputsSelectMandatoryCheckboxes(Linter):
    """
    Lint selects that are mandatory but display as checkboxes
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type not in ["select", "data_column", "drill_down"]:
                continue
            multiple = string_as_bool(param.attrib.get("multiple", "false"))
            optional = string_as_bool(param.attrib.get("optional", multiple))
            if param.attrib.get("display") == "checkboxes":
                if not optional:
                    lint_ctx.error(
                        f'Select [{param_name}] `display="checkboxes"` is incompatible with `optional="false"`, remove the `display` attribute',
                        linter=cls.name(),
                        node=param,
                    )


class InputsSelectMultipleRadio(Linter):
    """
    Lint selects that allow only multiple selections but display as radio
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type not in ["select", "data_column", "drill_down"]:
                continue
            multiple = string_as_bool(param.attrib.get("multiple", "false"))
            if param.attrib.get("display") == "radio":
                if multiple:
                    lint_ctx.error(
                        f'Select [{param_name}] display="radio" is incompatible with multiple="true"',
                        linter=cls.name(),
                        node=param,
                    )


class InputsSelectOptionalRadio(Linter):
    """
    Lint selects that are optional but display as radio
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param, param_name, param_type in _iter_param_type(tool_xml):
            if param_type not in ["select", "data_column", "drill_down"]:
                continue
            multiple = string_as_bool(param.attrib.get("multiple", "false"))
            optional = string_as_bool(param.attrib.get("optional", multiple))
            if param.attrib.get("display") == "radio":
                if optional:
                    lint_ctx.error(
                        f'Select [{param_name}] display="radio" is incompatible with optional="true"',
                        linter=cls.name(),
                        node=param,
                    )


def _iter_param_validator(tool_xml: "ElementTree") -> Iterator[Tuple[str, str, "Element", str]]:
    input_params = tool_xml.findall("./inputs//param[@type]")
    for param in input_params:
        try:
            param_name = _parse_name(param.attrib.get("name"), param.attrib.get("argument"))
        except ValueError:
            continue
        param_type = param.attrib["type"]
        validators = param.findall("./validator[@type]")
        for validator in validators:
            vtype = validator.attrib["type"]
            yield (param_name, param_type, validator, vtype)


class ValidatorParamIncompatible(Linter):
    """
    Lint for validator type - parameter type incompatibilities
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param_name, param_type, validator, vtype in _iter_param_validator(tool_xml):
            if param_type in PARAMETER_VALIDATOR_TYPE_COMPATIBILITY:
                if vtype not in PARAMETER_VALIDATOR_TYPE_COMPATIBILITY[param_type]:
                    lint_ctx.error(
                        f"Parameter [{param_name}]: validator with an incompatible type '{vtype}'",
                        linter=cls.name(),
                        node=validator,
                    )


class ValidatorAttribIncompatible(Linter):
    """
    Lint for incompatibilities between validator type and given attributes
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param_name, _, validator, vtype in _iter_param_validator(tool_xml):
            for attrib in ATTRIB_VALIDATOR_COMPATIBILITY:
                if attrib in validator.attrib and vtype not in ATTRIB_VALIDATOR_COMPATIBILITY[attrib]:
                    lint_ctx.error(
                        f"Parameter [{param_name}]: attribute '{attrib}' is incompatible with validator of type '{vtype}'",
                        linter=cls.name(),
                        node=validator,
                    )


class ValidatorHasText(Linter):
    """
    Lint that parameters that need text have text
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param_name, _, validator, vtype in _iter_param_validator(tool_xml):
            if vtype in ["expression", "regex"]:
                if validator.text is None:
                    lint_ctx.error(
                        f"Parameter [{param_name}]: {vtype} validators are expected to contain text",
                        linter=cls.name(),
                        node=validator,
                    )


class ValidatorHasNoText(Linter):
    """
    Lint that parameters that need no text have no text
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param_name, _, validator, vtype in _iter_param_validator(tool_xml):
            if vtype not in ["expression", "regex"] and validator.text is not None:
                lint_ctx.warn(
                    f"Parameter [{param_name}]: '{vtype}' validators are not expected to contain text (found '{validator.text}')",
                    linter=cls.name(),
                    node=validator,
                )


class ValidatorExpression(Linter):
    """
    Lint that checks expressions / regexp (ignoring FutureWarning)
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        with warnings.catch_warnings():
            warnings.simplefilter("error", FutureWarning)
            for param_name, _, validator, vtype in _iter_param_validator(tool_xml):
                if vtype in ["expression", "regex"] and validator.text is not None:
                    try:
                        if vtype == "regex":
                            re.compile(validator.text)
                        else:
                            ast.parse(validator.text, mode="eval")
                    except FutureWarning:
                        pass
                    except Exception as e:
                        lint_ctx.error(
                            f"Parameter [{param_name}]: '{validator.text}' is no valid {vtype}: {str(e)}",
                            linter=cls.name(),
                            node=validator,
                        )


class ValidatorExpressionFuture(Linter):
    """
    Lint that checks expressions / regexp FutureWarnings
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        with warnings.catch_warnings():
            warnings.simplefilter("error", FutureWarning)
            for param_name, _, validator, vtype in _iter_param_validator(tool_xml):
                if vtype in ["expression", "regex"] and validator.text is not None:
                    try:
                        if vtype == "regex":
                            re.compile(validator.text)
                        else:
                            ast.parse(validator.text, mode="eval")
                    except FutureWarning as e:
                        lint_ctx.warn(
                            f"Parameter [{param_name}]: '{validator.text}' is marked as deprecated {vtype}: {str(e)}",
                            linter=cls.name(),
                            node=validator,
                        )
                    except Exception:
                        pass


class ValidatorMinMax(Linter):
    """
    Lint for min/max for validator that need it
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param_name, _, validator, vtype in _iter_param_validator(tool_xml):
            if vtype in ["in_range", "length", "dataset_metadata_in_range"] and (
                "min" not in validator.attrib and "max" not in validator.attrib
            ):
                lint_ctx.error(
                    f"Parameter [{param_name}]: '{vtype}' validators need to define the 'min' or 'max' attribute(s)",
                    linter=cls.name(),
                    node=validator,
                )


class ValidatorDatasetMetadataEqualValue(Linter):
    """
    Lint dataset_metadata_equal needs value or value_json
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param_name, _, validator, vtype in _iter_param_validator(tool_xml):
            if vtype in ["dataset_metadata_equal"]:
                if (
                    not ("value" in validator.attrib or "value_json" in validator.attrib)
                    or "metadata_name" not in validator.attrib
                ):
                    lint_ctx.error(
                        f"Parameter [{param_name}]: '{vtype}' validators need to define the 'value'/'value_json' and 'metadata_name' attributes",
                        linter=cls.name(),
                        node=validator,
                    )


class ValidatorDatasetMetadataEqualValueOrJson(Linter):
    """
    Lint dataset_metadata_equal needs either value or value_json
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param_name, _, validator, vtype in _iter_param_validator(tool_xml):
            if vtype in ["dataset_metadata_equal"]:
                if "value" in validator.attrib and "value_json" in validator.attrib:
                    lint_ctx.error(
                        f"Parameter [{param_name}]: '{vtype}' validators must not define the 'value' and the 'value_json' attributes",
                        linter=cls.name(),
                        node=validator,
                    )


class ValidatorMetadataCheckSkip(Linter):
    """
    Lint metadata needs check or skip
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param_name, _, validator, vtype in _iter_param_validator(tool_xml):
            if vtype in ["metadata"] and ("check" not in validator.attrib and "skip" not in validator.attrib):
                lint_ctx.error(
                    f"Parameter [{param_name}]: '{vtype}' validators need to define the 'check' or 'skip' attribute(s)",
                    linter=cls.name(),
                    node=validator,
                )


class ValidatorTableName(Linter):
    """
    Lint table_name is present if needed
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param_name, _, validator, vtype in _iter_param_validator(tool_xml):
            if (
                vtype
                in [
                    "value_in_data_table",
                    "value_not_in_data_table",
                    "dataset_metadata_in_data_table",
                    "dataset_metadata_not_in_data_table",
                ]
                and "table_name" not in validator.attrib
            ):
                lint_ctx.error(
                    f"Parameter [{param_name}]: '{vtype}' validators need to define the 'table_name' attribute",
                    linter=cls.name(),
                    node=validator,
                )


class ValidatorMetadataName(Linter):
    """
    Lint metadata_name is present if needed
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for param_name, _, validator, vtype in _iter_param_validator(tool_xml):
            if (
                vtype
                in [
                    "dataset_metadata_in_data_table",
                    "dataset_metadata_not_in_data_table",
                    "dataset_metadata_in_file",
                    "dataset_metadata_in_range",
                ]
                and "metadata_name" not in validator.attrib
            ):
                lint_ctx.error(
                    f"Parameter [{param_name}]: '{vtype}' validators need to define the 'metadata_name' attribute",
                    linter=cls.name(),
                    node=validator,
                )


def _iter_conditional(tool_xml: "ElementTree") -> Iterator[Tuple["Element", Optional[str], "Element", Optional[str]]]:
    conditionals = tool_xml.findall("./inputs//conditional")
    for conditional in conditionals:
        conditional_name = conditional.get("name")
        if conditional.get("value_from"):  # Probably only the upload tool use this, no children elements
            continue
        first_param = conditional.find("param")
        if first_param is None:
            continue
        first_param_type = first_param.get("type")
        yield conditional, conditional_name, first_param, first_param_type


class ConditionalParamTypeBool(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for _, conditional_name, first_param, first_param_type in _iter_conditional(tool_xml):
            if first_param_type == "boolean":
                lint_ctx.warn(
                    f'Conditional [{conditional_name}] first param of type="boolean" is discouraged, use a select',
                    linter=cls.name(),
                    node=first_param,
                )


class ConditionalParamType(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for _, conditional_name, first_param, first_param_type in _iter_conditional(tool_xml):
            if first_param_type not in ["boolean", "select"]:
                lint_ctx.error(
                    f'Conditional [{conditional_name}] first param should have type="select"',
                    linter=cls.name(),
                    node=first_param,
                )


class ConditionalParamIncompatibleAttributes(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for _, conditional_name, first_param, first_param_type in _iter_conditional(tool_xml):
            if first_param_type not in ["boolean", "select"]:
                continue
            for incomp in ["optional", "multiple"]:
                if string_as_bool(first_param.get(incomp, False)):
                    lint_ctx.warn(
                        f'Conditional [{conditional_name}] test parameter cannot be {incomp}="true"',
                        linter=cls.name(),
                        node=first_param,
                    )


class ConditionalWhenMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for conditional, conditional_name, first_param, first_param_type in _iter_conditional(tool_xml):
            if first_param_type not in ["boolean", "select"]:
                continue
            if first_param_type == "select":
                options = first_param.findall("./option[@value]")
                option_ids = {option.get("value") for option in options}
            else:  # boolean
                option_ids = {first_param.get("truevalue", "true"), first_param.get("falsevalue", "false")}
            whens = conditional.findall("./when[@value]")
            when_ids = {w.get("value") for w in whens if w.get("value") is not None}
            for option_id in option_ids - when_ids:
                lint_ctx.warn(
                    f"Conditional [{conditional_name}] no <when /> block found for {first_param_type} option '{option_id}'",
                    linter=cls.name(),
                    node=conditional,
                )


class ConditionalOptionMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for conditional, conditional_name, first_param, first_param_type in _iter_conditional(tool_xml):
            if first_param_type != "select":
                continue
            options = first_param.findall("./option[@value]")
            option_ids = {option.get("value") for option in options}
            whens = conditional.findall("./when[@value]")
            when_ids = {w.get("value") for w in whens if w.get("value") is not None}
            for when_id in when_ids - option_ids:
                lint_ctx.warn(
                    f"Conditional [{conditional_name}] no <option /> found for when block '{when_id}'",
                    linter=cls.name(),
                    node=conditional,
                )


class ConditionalOptionMissingBoolean(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for conditional, conditional_name, first_param, first_param_type in _iter_conditional(tool_xml):
            if first_param_type != "boolean":
                continue
            option_ids = {first_param.get("truevalue", "true"), first_param.get("falsevalue", "false")}
            whens = conditional.findall("./when[@value]")
            when_ids = {w.get("value") for w in whens if w.get("value")}
            for when_id in when_ids - option_ids:
                lint_ctx.warn(
                    f"Conditional [{conditional_name}] no truevalue/falsevalue found for when block '{when_id}'",
                    linter=cls.name(),
                    node=conditional,
                )
