"""This module contains a linting functions for tool inputs."""
import re

from galaxy.util import string_as_bool
from ._util import (
    is_datasource,
    is_valid_cheetah_placeholder,
)
from ..parser.util import _parse_name

FILTER_TYPES = [
    "data_meta",
    "param_value",
    "static_value",
    "regexp",
    "unique_value",
    "multiple_splitter",
    "attribute_value_splitter",
    "add_value",
    "remove_value",
    "sort_by",
]

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
}

PARAMETER_VALIDATOR_TYPE_COMPATIBILITY = {
    "integer": ["in_range", "expression"],
    "float": ["in_range", "expression"],
    "data": [
        "metadata",
        "no_options",
        "unspecified_build",
        "dataset_ok_validator",
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
        "dataset_metadata_in_range",
        "dataset_metadata_in_file",
        "dataset_metadata_in_data_table",
        "dataset_metadata_not_in_data_table",
        "expression",
    ],
    "text": ["regex", "length", "empty_field", "value_in_data_table", "value_not_in_data_table", "expression"],
    "select": [
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
    ("./column", ["data_column"]),
]


def lint_inputs(tool_xml, lint_ctx):
    """Lint parameters in a tool's inputs block."""
    datasource = is_datasource(tool_xml)
    input_names = set()
    inputs = tool_xml.findall("./inputs//param")
    # determine node to report for general problems with outputs
    tool_node = tool_xml.find("./inputs")
    if tool_node is None:
        tool_node = tool_xml.getroot()
    num_inputs = 0
    for param in inputs:
        num_inputs += 1
        param_attrib = param.attrib
        if "name" not in param_attrib and "argument" not in param_attrib:
            lint_ctx.error("Found param input with no name specified.", node=param)
            continue
        param_name = _parse_name(param_attrib.get("name"), param_attrib.get("argument"))
        if "name" in param_attrib and "argument" in param_attrib:
            if param_attrib.get("name") == _parse_name(None, param_attrib.get("argument")):
                lint_ctx.warn(
                    f"Param input [{param_name}] 'name' attribute is redundant if argument implies the same name.",
                    node=param,
                )
        if param_name.strip() == "":
            lint_ctx.error("Param input with empty name.", node=param)
        elif not is_valid_cheetah_placeholder(param_name):
            lint_ctx.warn(f"Param input [{param_name}] is not a valid Cheetah placeholder.", node=param)

        # check for parameters with duplicate names
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
        path_str = ".".join(reversed(path))
        if path_str in input_names:
            lint_ctx.error(f"Tool defines multiple parameters with the same name: '{path_str}'", node=param)
        input_names.add(path_str)

        if "type" not in param_attrib:
            lint_ctx.error(f"Param input [{param_name}] input with no type specified.", node=param)
            continue
        elif param_attrib["type"].strip() == "":
            lint_ctx.error(f"Param input [{param_name}] with empty type specified.", node=param)
            continue
        param_type = param_attrib["type"]

        # TODO lint for valid param type - attribute combinations

        # lint for valid param type - child node combinations
        for ptcc in PARAM_TYPE_CHILD_COMBINATIONS:
            if param.find(ptcc[0]) is not None and param_type not in ptcc[1]:
                lint_ctx.error(
                    f"Parameter [{param_name}] '{ptcc[0]}' tags are only allowed for parameters of type {ptcc[1]}",
                    node=param,
                )

        # param type specific linting
        if param_type == "data":
            if "format" not in param_attrib:
                lint_ctx.warn(
                    f"Param input [{param_name}] with no format specified - 'data' format will be assumed.", node=param
                )
            options = param.findall("./options")
            has_options_filter_attribute = False
            if len(options) == 1:
                for oa in options[0].attrib:
                    if oa == "options_filter_attribute":
                        has_options_filter_attribute = True
                    else:
                        lint_ctx.error(f"Data parameter [{param_name}] uses invalid attribute: {oa}", node=param)
            elif len(options) > 1:
                lint_ctx.error(f"Data parameter [{param_name}] contains multiple options elements.", node=options[1])
            # for data params only filters with key='build' of type='data_meta' are allowed
            filters = param.findall("./options/filter")
            for f in filters:
                if not f.get("ref"):
                    lint_ctx.error(
                        f"Data parameter [{param_name}] filter needs to define a ref attribute",
                        node=f,
                    )
                if has_options_filter_attribute:
                    if f.get("type") != "data_meta":
                        lint_ctx.error(
                            f'Data parameter [{param_name}] for filters only type="data_meta" is allowed, found type="{f.get("type")}"',
                            node=f,
                        )
                else:
                    if f.get("key") != "dbkey" or f.get("type") != "data_meta":
                        lint_ctx.error(
                            f'Data parameter [{param_name}] for filters only type="data_meta" and key="dbkey" are allowed, found type="{f.get("type")}" and key="{f.get("key")}"',
                            node=f,
                        )

        elif param_type == "select":
            # get dynamic/statically defined options
            dynamic_options = param.get("dynamic_options", None)
            options = param.findall("./options")
            filters = param.findall("./options/filter")
            select_options = param.findall("./option")

            if dynamic_options is not None:
                lint_ctx.warn(
                    f"Select parameter [{param_name}] uses deprecated 'dynamic_options' attribute.", node=param
                )

            # check if options are defined by exactly one possibility
            if param.getparent().tag != "conditional":
                if (dynamic_options is not None) + (len(options) > 0) + (len(select_options) > 0) != 1:
                    lint_ctx.error(
                        f"Select parameter [{param_name}] options have to be defined by either 'option' children elements, a 'options' element or the 'dynamic_options' attribute.",
                        node=param,
                    )
            else:
                if len(select_options) == 0:
                    lint_ctx.error(
                        f"Select parameter of a conditional [{param_name}] options have to be defined by 'option' children elements.",
                        node=param,
                    )

            # lint dynamic options
            if len(options) == 1:
                filters = options[0].findall("./filter")
                # lint filters
                # TODO check if dataset is available for filters referring other datasets
                filter_adds_options = False
                for f in filters:
                    ftype = f.get("type", None)
                    if ftype is None:
                        lint_ctx.error(f"Select parameter [{param_name}] contains filter without type.", node=f)
                        continue
                    if ftype not in FILTER_TYPES:
                        lint_ctx.error(
                            f"Select parameter [{param_name}] contains filter with unknown type '{ftype}'.", node=f
                        )
                        continue
                    if ftype in ["add_value", "data_meta"]:
                        filter_adds_options = True
                    # TODO more linting of filters

                from_file = options[0].get("from_file", None)
                from_parameter = options[0].get("from_parameter", None)
                from_dataset = options[0].get("from_dataset", None)
                from_data_table = options[0].get("from_data_table", None)
                # TODO check if input param is present for from_dataset

                if (
                    from_file is None
                    and from_parameter is None
                    and from_dataset is None
                    and from_data_table is None
                    and not filter_adds_options
                ):
                    lint_ctx.error(
                        f"Select parameter [{param_name}] options tag defines no options. Use 'from_dataset', 'from_data_table', or a filter that adds values.",
                        node=options[0],
                    )

                for deprecated_attr in ["from_file", "from_parameter", "options_filter_attribute", "transform_lines"]:
                    if options[0].get(deprecated_attr) is not None:
                        lint_ctx.warn(
                            f"Select parameter [{param_name}] options uses deprecated '{deprecated_attr}' attribute.",
                            node=options[0],
                        )

                if from_dataset is not None and from_data_table is not None:
                    lint_ctx.error(
                        f"Select parameter [{param_name}] options uses 'from_dataset' and 'from_data_table' attribute.",
                        node=options[0],
                    )

                if options[0].get("meta_file_key", None) is not None and from_dataset is None:
                    lint_ctx.error(
                        f"Select parameter [{param_name}] 'meta_file_key' is only compatible with 'from_dataset'.",
                        node=options[0],
                    )

            elif len(options) > 1:
                lint_ctx.error(f"Select parameter [{param_name}] contains multiple options elements.", node=options[1])

            # lint statically defined options
            if any("value" not in option.attrib for option in select_options):
                lint_ctx.error(f"Select parameter [{param_name}] has option without value", node=param)
            if any(option.text is None for option in select_options):
                lint_ctx.warn(f"Select parameter [{param_name}] has option without text", node=param)

            select_options_texts = list()
            select_options_values = list()
            for option in select_options:
                value = option.attrib.get("value", "")
                if option.text is None:
                    text = value.capitalize()
                else:
                    text = option.text
                select_options_texts.append((text, option.attrib.get("selected", "false")))
                select_options_values.append((value, option.attrib.get("selected", "false")))
            if len(set(select_options_texts)) != len(select_options_texts):
                lint_ctx.error(
                    f"Select parameter [{param_name}] has multiple options with the same text content", node=param
                )
            if len(set(select_options_values)) != len(select_options_values):
                lint_ctx.error(f"Select parameter [{param_name}] has multiple options with the same value", node=param)

        if param_type in ["select", "data_column", "drill_down"]:
            multiple = string_as_bool(param_attrib.get("multiple", "false"))
            optional = string_as_bool(param_attrib.get("optional", multiple))
            if param_attrib.get("display") == "checkboxes":
                if not multiple:
                    lint_ctx.error(
                        f'Select [{param_name}] `display="checkboxes"` is incompatible with `multiple="false"`, remove the `display` attribute',
                        node=param,
                    )
                if not optional:
                    lint_ctx.error(
                        f'Select [{param_name}] `display="checkboxes"` is incompatible with `optional="false"`, remove the `display` attribute',
                        node=param,
                    )
            if param_attrib.get("display") == "radio":
                if multiple:
                    lint_ctx.error(
                        f'Select [{param_name}] display="radio" is incompatible with multiple="true"', node=param
                    )
                if optional:
                    lint_ctx.error(
                        f'Select [{param_name}] display="radio" is incompatible with optional="true"', node=param
                    )
        # TODO: Validate type, much more...

        # lint validators
        # TODO check if dataset is available for validators referring other datasets
        validators = param.findall("./validator")
        for validator in validators:
            vtype = validator.attrib["type"]
            if param_type in PARAMETER_VALIDATOR_TYPE_COMPATIBILITY:
                if vtype not in PARAMETER_VALIDATOR_TYPE_COMPATIBILITY[param_type]:
                    lint_ctx.error(
                        f"Parameter [{param_name}]: validator with an incompatible type '{vtype}'", node=validator
                    )
            for attrib in ATTRIB_VALIDATOR_COMPATIBILITY:
                if attrib in validator.attrib and vtype not in ATTRIB_VALIDATOR_COMPATIBILITY[attrib]:
                    lint_ctx.error(
                        f"Parameter [{param_name}]: attribute '{attrib}' is incompatible with validator of type '{vtype}'",
                        node=validator,
                    )
            if vtype == "expression":
                if validator.text is None:
                    lint_ctx.error(
                        f"Parameter [{param_name}]: expression validators are expected to contain text", node=validator
                    )
                else:
                    try:
                        re.compile(validator.text)
                    except Exception as e:
                        lint_ctx.error(
                            f"Parameter [{param_name}]: '{validator.text}' is no valid regular expression: {str(e)}",
                            node=validator,
                        )
            if vtype not in ["expression", "regex"] and validator.text is not None:
                lint_ctx.warn(
                    f"Parameter [{param_name}]: '{vtype}' validators are not expected to contain text (found '{validator.text}')",
                    node=validator,
                )
            if vtype in ["in_range", "length", "dataset_metadata_in_range"] and (
                "min" not in validator.attrib and "max" not in validator.attrib
            ):
                lint_ctx.error(
                    f"Parameter [{param_name}]: '{vtype}' validators need to define the 'min' or 'max' attribute(s)",
                    node=validator,
                )
            if vtype in ["metadata"] and ("check" not in validator.attrib and "skip" not in validator.attrib):
                lint_ctx.error(
                    f"Parameter [{param_name}]: '{vtype}' validators need to define the 'check' or 'skip' attribute(s)",
                    node=validator,
                )
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
                    node=validator,
                )
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
                    node=validator,
                )

    conditional_selects = tool_xml.findall("./inputs//conditional")
    for conditional in conditional_selects:
        conditional_name = conditional.get("name")
        if not conditional_name:
            lint_ctx.error("Conditional without a name", node=conditional)
        if conditional.get("value_from"):
            # Probably only the upload tool use this, no children elements
            continue
        first_param = conditional.findall("param")
        if len(first_param) != 1:
            lint_ctx.error(
                f"Conditional [{conditional_name}] needs exactly one child <param> found {len(first_param)}",
                node=conditional,
            )
            continue
        first_param = first_param[0]
        first_param_type = first_param.get("type")
        if first_param_type == "boolean":
            lint_ctx.warn(
                f'Conditional [{conditional_name}] first param of type="boolean" is discouraged, use a select',
                node=first_param,
            )
        elif first_param_type != "select":
            lint_ctx.error(f'Conditional [{conditional_name}] first param should have type="select"', node=first_param)
            continue

        if first_param_type == "select":
            select_options = _find_with_attribute(first_param, "option", "value")
            option_ids = [option.get("value") for option in select_options]
        else:  # boolean
            option_ids = [first_param.get("truevalue", "true"), first_param.get("falsevalue", "false")]

        for incomp in ["optional", "multiple"]:
            if string_as_bool(first_param.get(incomp, False)):
                lint_ctx.warn(
                    f'Conditional [{conditional_name}] test parameter cannot be {incomp}="true"', node=first_param
                )

        whens = conditional.findall("./when")
        if any("value" not in when.attrib for when in whens):
            lint_ctx.error(f"Conditional [{conditional_name}] when without value", node=conditional)

        when_ids = [w.get("value") for w in whens if w.get("value") is not None]

        for option_id in option_ids:
            if option_id not in when_ids:
                lint_ctx.warn(
                    f"Conditional [{conditional_name}] no <when /> block found for {first_param_type} option '{option_id}'",
                    node=conditional,
                )

        for when_id in when_ids:
            if when_id not in option_ids:
                if first_param_type == "select":
                    lint_ctx.warn(
                        f"Conditional [{conditional_name}] no <option /> found for when block '{when_id}'",
                        node=conditional,
                    )
                else:
                    lint_ctx.warn(
                        f"Conditional [{conditional_name}] no truevalue/falsevalue found for when block '{when_id}'",
                        node=conditional,
                    )

    if datasource:
        # TODO only display is subtag of inputs, uihints is a separate top level tag (supporting only attrib minwidth)
        for datasource_tag in ("display", "uihints"):
            if not any(param.tag == datasource_tag for param in inputs):
                lint_ctx.info(f"{datasource_tag} tag usually present in data sources", node=tool_node)

    if num_inputs:
        lint_ctx.info(f"Found {num_inputs} input parameters.", node=tool_node)
    else:
        if datasource:
            lint_ctx.info("No input parameters, OK for data sources", node=tool_node)
        else:
            lint_ctx.warn("Found no input parameters.", node=tool_node)

    # check if there is an output with the same name as an input
    outputs = tool_xml.find("./outputs")
    if outputs is not None:
        for output in outputs:
            if output.get("name") in input_names:
                lint_ctx.error(
                    f'Tool defines an output with a name equal to the name of an input: \'{output.get("name")}\'',
                    node=output,
                )


def lint_repeats(tool_xml, lint_ctx):
    """Lint repeat blocks in tool inputs."""
    repeats = tool_xml.findall("./inputs//repeat")
    for repeat in repeats:
        if "name" not in repeat.attrib:
            lint_ctx.error("Repeat does not specify name attribute.", node=repeat)
        if "title" not in repeat.attrib:
            lint_ctx.error("Repeat does not specify title attribute.", node=repeat)


def _find_with_attribute(element, tag, attribute, test_value=None):
    rval = []
    for el in element.findall(f"./{tag}") or []:
        if attribute not in el.attrib:
            continue
        value = el.attrib[attribute]
        if test_value is not None:
            if value == test_value:
                rval.append(el)
        else:
            rval.append(el)
    return rval
