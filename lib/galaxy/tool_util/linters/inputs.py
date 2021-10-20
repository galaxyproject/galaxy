
"""This module contains a linting functions for tool inputs."""
from galaxy.util import string_as_bool
from ._util import is_datasource, is_valid_cheetah_placeholder
from ..parser.util import _parse_name

FILTER_TYPES = [
    'data_meta',
    'param_value',
    'static_value',
    'regexp',
    'unique_value',
    'multiple_splitter',
    'attribute_value_splitter',
    'add_value',
    'remove_value',
    'sort_by',
]

ATTRIB_VALIDATOR_COMPATIBILITY = {
    "check": ["metadata"],
    "expression": ["substitute_value_in_message"],
    "table_name": ["dataset_metadata_in_data_table", "dataset_metadata_not_in_data_table", "value_in_data_table", "value_not_in_data_table"],
    "filename": ["dataset_metadata_in_file"],
    "metadata_name": ["dataset_metadata_in_data_table", "dataset_metadata_not_in_data_table", "dataset_metadata_in_file"],
    "metadata_column": ["dataset_metadata_in_data_table", "dataset_metadata_not_in_data_table", "value_in_data_table", "value_not_in_data_table", "dataset_metadata_in_file"],
    "line_startswith": ["dataset_metadata_in_file"],
    "min": ["in_range", "length", "dataset_metadata_in_range"],
    "max": ["in_range", "length", "dataset_metadata_in_range"],
    "exclude_min": ["in_range", "dataset_metadata_in_range"],
    "exclude_max": ["in_range", "dataset_metadata_in_range"],
    "split": ["dataset_metadata_in_file"],
    "skip": ["metadata"]
}

PARAMETER_VALIDATOR_TYPE_COMPATIBILITY = {
    "integer": ["in_range", "expression"],
    "float": ["in_range", "expression"],
    "data": ["metadata", "unspecified_build", "dataset_ok_validator", "dataset_metadata_in_range", "dataset_metadata_in_file", "dataset_metadata_in_data_table", "dataset_metadata_not_in_data_table", "expression"],
    "data_collection": ["metadata", "unspecified_build", "dataset_ok_validator", "dataset_metadata_in_range", "dataset_metadata_in_file", "dataset_metadata_in_data_table", "dataset_metadata_not_in_data_table", "expression"],
    "text": ["regex", "length", "empty_field", "value_in_data_table", "value_not_in_data_table", "expression"],
    "select": ["no_options", "regex", "length", "empty_field", "value_in_data_table", "value_not_in_data_table", "expression"],
    "drill_down": ["no_options", "regex", "length", "empty_field", "value_in_data_table", "value_not_in_data_table", "expression"],
    "data_column": ["no_options", "regex", "length", "empty_field", "value_in_data_table", "value_not_in_data_table", "expression"]
}


def lint_inputs(tool_xml, lint_ctx):
    """Lint parameters in a tool's inputs block."""
    datasource = is_datasource(tool_xml)
    inputs = tool_xml.findall("./inputs//param")
    num_inputs = 0
    for param in inputs:
        num_inputs += 1
        param_attrib = param.attrib
        if "name" not in param_attrib and "argument" not in param_attrib:
            lint_ctx.error("Found param input with no name specified.")
            continue
        param_name = _parse_name(param_attrib.get("name"), param_attrib.get("argument"))

        if "type" not in param_attrib:
            lint_ctx.error(f"Param input [{param_name}] input with no type specified.")
            continue
        param_type = param_attrib["type"]

        if not is_valid_cheetah_placeholder(param_name):
            lint_ctx.warn(f"Param input [{param_name}] is not a valid Cheetah placeholder.")

        if param_type == "data":
            if "format" not in param_attrib:
                lint_ctx.warn(f"Param input [{param_name}] with no format specified - 'data' format will be assumed.")
        elif param_type == "select":
            # get dynamic/statically defined options
            dynamic_options = param.get("dynamic_options", None)
            options = param.findall("./options")
            filters = param.findall("./options/filter")
            select_options = param.findall('./option')

            if dynamic_options is not None:
                lint_ctx.warn(f"Select parameter [{param_name}] uses deprecated 'dynamic_options' attribute.")

            # check if options are defined by exactly one possibility
            if (dynamic_options is not None) + (len(options) > 0) + (len(select_options) > 0) != 1:
                lint_ctx.error(f"Select parameter [{param_name}] options have to be defined by either 'option' children elements, a 'options' element or the 'dynamic_options' attribute.")

            # lint dynamic options
            if len(options) == 1:
                filters = options[0].findall("./filter")
                # lint filters
                filter_adds_options = False
                for f in filters:
                    ftype = f.get("type", None)
                    if ftype is None:
                        lint_ctx.error(f"Select parameter [{param_name}] contains filter without type.")
                        continue
                    if ftype not in FILTER_TYPES:
                        lint_ctx.error(f"Select parameter [{param_name}] contains filter with unknown type '{ftype}'.")
                        continue
                    if ftype in ['add_value', 'data_meta']:
                        filter_adds_options = True
                    # TODO more linting of filters

                from_file = options[0].get("from_file", None)
                from_parameter = options[0].get("from_parameter", None)
                from_dataset = options[0].get("from_dataset", None)
                from_data_table = options[0].get("from_data_table", None)
                if (from_file is None and from_parameter is None
                        and from_dataset is None and from_data_table is None
                        and not filter_adds_options):
                    lint_ctx.error(f"Select parameter [{param_name}] options tag defines no options. Use 'from_dataset', 'from_data_table', or a filter that adds values.")

                if from_file is not None:
                    lint_ctx.warn(f"Select parameter [{param_name}] options uses deprecated 'from_file' attribute.")
                if from_parameter is not None:
                    lint_ctx.warn(f"Select parameter [{param_name}] options uses deprecated 'from_parameter' attribute.")

                if from_dataset is not None and from_data_table is not None:
                    lint_ctx.error(f"Select parameter [{param_name}] options uses 'from_dataset' and 'from_data_table' attribute.")

                if options[0].get("meta_file_key", None) is not None and from_dataset is None:
                    lint_ctx.error(f"Select parameter [{param_name}] 'meta_file_key' is only compatible with 'from_dataset'.")

                if options[0].get("options_filter_attribute", None) is not None:
                    lint_ctx.warn(f"Select parameter [{param_name}] options uses deprecated 'options_filter_attribute' attribute.")

                if options[0].get("transform_lines", None) is not None:
                    lint_ctx.warn(f"Select parameter [{param_name}] options uses deprecated 'transform_lines' attribute.")

            elif len(options) > 1:
                lint_ctx.error(f"Select parameter [{param_name}] contains multiple options elements")

            # lint statically defined options
            if any(['value' not in option.attrib for option in select_options]):
                lint_ctx.error(f"Select parameter [{param_name}] has option without value")
            if len(set([option.text.strip() for option in select_options if option.text is not None])) != len(select_options):
                lint_ctx.error(f"Select parameter [{param_name}] has multiple options with the same text content")
            if len(set([option.attrib.get("value") for option in select_options])) != len(select_options):
                lint_ctx.error(f"Select parameter [{param_name}] has multiple options with the same value")

            if param_attrib.get("display") == "checkboxes":
                if not string_as_bool(param_attrib.get("multiple", "false")):
                    lint_ctx.error(f'Select [{param_name}] `display="checkboxes"` is incompatible with `multiple="false"`, remove the `display` attribute')
                if not string_as_bool(param_attrib.get("optional", "false")):
                    lint_ctx.error(f'Select [{param_name}] `display="checkboxes"` is incompatible with `optional="false"`, remove the `display` attribute')
            if param_attrib.get("display") == "radio":
                if string_as_bool(param_attrib.get("multiple", "false")):
                    lint_ctx.error(f'Select [{param_name}] display="radio" is incompatible with multiple="true"')
                if string_as_bool(param_attrib.get("optional", "false")):
                    lint_ctx.error(f'Select [{param_name}] display="radio" is incompatible with optional="true"')
        # TODO: Validate type, much more...

        # lint validators
        validators = param.findall("./validator")
        for validator in validators:
            vtype = validator.attrib['type']
            if param_type in PARAMETER_VALIDATOR_TYPE_COMPATIBILITY:
                if vtype not in PARAMETER_VALIDATOR_TYPE_COMPATIBILITY[param_type]:
                    lint_ctx.error(f"Parameter [{param_name}]: validator with an incompatible type '{vtype}'")
            for attrib in ATTRIB_VALIDATOR_COMPATIBILITY:
                if attrib in validator.attrib and vtype not in ATTRIB_VALIDATOR_COMPATIBILITY[attrib]:
                    lint_ctx.error(f"Parameter [{param_name}]: attribute '{attrib}' is incompatible with validator of type '{vtype}'")
            if vtype == "expression" and validator.text is None:
                lint_ctx.error(f"Parameter [{param_name}]: expression validator without content")
            if vtype not in ["expression", "regex"] and validator.text is not None:
                lint_ctx.warn(f"Parameter [{param_name}]: '{vtype}' validators are not expected to contain text (found '{validator.text}')")
            if vtype in ["in_range", "length", "dataset_metadata_in_range"] and ("min" not in validator.attrib and "max" not in validator.attrib):
                lint_ctx.error(f"Parameter [{param_name}]: '{vtype}' validators need to define the 'min' or 'max' attribute(s)")
            if vtype in ["metadata"] and ("check" not in validator.attrib and "skip" not in validator.attrib):
                lint_ctx.error(f"Parameter [{param_name}]: '{vtype}' validators need to define the 'check' or 'skip' attribute(s) {validator.attrib}")
            if vtype in ["value_in_data_table", "value_not_in_data_table", "dataset_metadata_in_data_table", "dataset_metadata_not_in_data_table"] and "table_name" not in validator.attrib:
                lint_ctx.error(f"Parameter [{param_name}]: '{vtype}' validators need to define the 'table_name' attribute")

    conditional_selects = tool_xml.findall("./inputs//conditional")
    for conditional in conditional_selects:
        conditional_name = conditional.get('name')
        if not conditional_name:
            lint_ctx.error("Conditional without a name")
        if conditional.get("value_from"):
            # Probably only the upload tool use this, no children elements
            continue
        first_param = conditional.find("param")
        if first_param is None:
            lint_ctx.error(f"Conditional [{conditional_name}] has no child <param>")
            continue
        first_param_type = first_param.get('type')
        if first_param_type not in ['select', 'boolean']:
            lint_ctx.warn(f'Conditional [{conditional_name}] first param should have type="select" /> or type="boolean"')
            continue

        if first_param_type == 'select':
            select_options = _find_with_attribute(first_param, 'option', 'value')
            option_ids = [option.get('value') for option in select_options]
        else:  # boolean
            option_ids = [
                first_param.get('truevalue', 'true'),
                first_param.get('falsevalue', 'false')
            ]

        if string_as_bool(first_param.get('optional', False)):
            lint_ctx.warn(f"Conditional [{conditional_name}] test parameter cannot be optional")

        whens = conditional.findall('./when')
        if any('value' not in when.attrib for when in whens):
            lint_ctx.error(f"Conditional [{conditional_name}] when without value")

        when_ids = [w.get('value') for w in whens]

        for option_id in option_ids:
            if option_id not in when_ids:
                lint_ctx.warn(f"Conditional [{conditional_name}] no <when /> block found for {first_param_type} option '{option_id}'")

        for when_id in when_ids:
            if when_id not in option_ids:
                if first_param_type == 'select':
                    lint_ctx.warn(f"Conditional [{conditional_name}] no <option /> found for when block '{when_id}'")
                else:
                    lint_ctx.warn(f"Conditional [{conditional_name}] no truevalue/falsevalue found for when block '{when_id}'")

    if datasource:
        for datasource_tag in ('display', 'uihints'):
            if not any([param.tag == datasource_tag for param in inputs]):
                lint_ctx.info(f"{datasource_tag} tag usually present in data sources")

    if num_inputs:
        lint_ctx.info(f"Found {num_inputs} input parameters.")
    else:
        if datasource:
            lint_ctx.info("No input parameters, OK for data sources")
        else:
            lint_ctx.warn("Found no input parameters.")


def lint_repeats(tool_xml, lint_ctx):
    """Lint repeat blocks in tool inputs."""
    repeats = tool_xml.findall("./inputs//repeat")
    for repeat in repeats:
        if "name" not in repeat.attrib:
            lint_ctx.error("Repeat does not specify name attribute.")
        if "title" not in repeat.attrib:
            lint_ctx.error("Repeat does not specify title attribute.")


def _find_with_attribute(element, tag, attribute, test_value=None):
    rval = []
    for el in (element.findall(f'./{tag}') or []):
        if attribute not in el.attrib:
            continue
        value = el.attrib[attribute]
        if test_value is not None:
            if value == test_value:
                rval.append(el)
        else:
            rval.append(el)
    return rval
