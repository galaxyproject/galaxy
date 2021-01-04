"""This module contains a linting functions for tool inputs."""
from galaxy.util import string_as_bool
from ._util import is_datasource, is_valid_cheetah_placeholder
from ..parser.util import _parse_name


def lint_inputs(tool_xml, lint_ctx):
    """Lint parameters in a tool's inputs block."""
    datasource = is_datasource(tool_xml)
    inputs = tool_xml.findall("./inputs//param")
    num_inputs = 0
    for param in inputs:
        num_inputs += 1
        param_attrib = param.attrib
        has_errors = False
        if "type" not in param_attrib:
            lint_ctx.error("Found param input with no type specified.")
            has_errors = True
        if "name" not in param_attrib and "argument" not in param_attrib:
            lint_ctx.error("Found param input with no name specified.")
            has_errors = True

        if has_errors:
            continue

        param_type = param_attrib["type"]
        param_name = _parse_name(param_attrib.get("name"), param_attrib.get("argument"))

        if not is_valid_cheetah_placeholder(param_name):
            lint_ctx.warn("Param input [%s] is not a valid Cheetah placeholder.", param_name)

        if param_type == "data":
            if "format" not in param_attrib:
                lint_ctx.warn("Param input [%s] with no format specified - 'data' format will be assumed.", param_name)
        elif param_type == "select":
            dynamic_options = param.get("dynamic_options", None)
            if dynamic_options is None:
                dynamic_options = param.find("options")

            select_options = param.findall('./option')
            if any(['value' not in option.attrib for option in select_options]):
                lint_ctx.error("Select [%s] has option without value", param_name)

            if dynamic_options is None and len(select_options) == 0:
                message = "No options defined for select [%s]" % param_name
                lint_ctx.warn(message)
        # TODO: Validate type, much more...

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
            lint_ctx.error("Conditional '%s' has no child <param>" % conditional_name)
            continue
        first_param_type = first_param.get('type')
        if first_param_type not in ['select', 'boolean']:
            lint_ctx.warn("Conditional '%s' first param should have type=\"select\" /> or type=\"boolean\"" % conditional_name)
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
            lint_ctx.warn("Conditional test parameter cannot be optional")

        whens = conditional.findall('./when')
        if any('value' not in when.attrib for when in whens):
            lint_ctx.error("When without value")

        when_ids = [w.get('value') for w in whens]

        for option_id in option_ids:
            if option_id not in when_ids:
                lint_ctx.warn(f"No <when /> block found for {first_param_type} option '{option_id}' inside conditional '{conditional_name}'")

        for when_id in when_ids:
            if when_id not in option_ids:
                if first_param_type == 'select':
                    lint_ctx.warn(f"No <option /> found for when block '{when_id}' inside conditional '{conditional_name}'")
                else:
                    lint_ctx.warn(f"No truevalue/falsevalue found for when block '{when_id}' inside conditional '{conditional_name}'")

    if datasource:
        for datasource_tag in ('display', 'uihints'):
            if not any([param.tag == datasource_tag for param in inputs]):
                lint_ctx.info("%s tag usually present in data sources" % datasource_tag)

    if num_inputs:
        lint_ctx.info("Found %d input parameters.", num_inputs)
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
    for el in (element.findall('./%s' % tag) or []):
        if attribute not in el.attrib:
            continue
        value = el.attrib[attribute]
        if test_value is not None:
            if value == test_value:
                rval.append(el)
        else:
            rval.append(el)
    return rval
