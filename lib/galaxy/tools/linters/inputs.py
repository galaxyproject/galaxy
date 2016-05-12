"""This module contains a linting functions for tool inputs."""
from ..lint_util import is_datasource


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
        param_name = param_attrib.get("name", param_attrib.get("argument"))
        if param_type == "data":
            if "format" not in param_attrib:
                lint_ctx.warn("Param input [%s] with no format specified - 'data' format will be assumed.", param_name)

        if param_type == "select":
            dynamic_options = param.get("dynamic_options", None)
            if dynamic_options is None:
                dynamic_options = param.find("options")

            select_options = _find_with_attribute(param, 'option', 'value')
            if any(['value' not in option.attrib for option in select_options]):
                lint_ctx.error("Option without value")

            select_option_ids = [option.attrib.get('value', None) for option in select_options]

            if dynamic_options is None and len(select_options) == 0:
                message = "No options defined for select [%s]" % param_name
                lint_ctx.warn(message)

        # TODO: Validate type, much more...

    conditional_selects = tool_xml.findall("./inputs//conditional")
    for conditional in conditional_selects:
        booleans = _find_with_attribute(conditional, "param", "type", "boolean")
        selects = _find_with_attribute(conditional, "param", "type", "select")
        # Should conditionals ever not have a select?
        if not len(selects) and not len(booleans):
            lint_ctx.warn("Conditional without <param type=\"select\" /> or <param type=\"boolean\" />")
            continue

        test_param_optional = False
        for select in selects:
            test_param_optional = test_param_optional or (select.attrib.get('optional', None) is not None)
            select_options = _find_with_attribute(select, 'option', 'value')
            select_option_ids = [option.attrib.get('value', None) for option in select_options]

        for boolean in booleans:
            test_param_optional = test_param_optional or (boolean.attrib.get('optional', None) is not None)
            select_option_ids = [
                boolean.attrib.get('truevalue', 'true'),
                boolean.attrib.get('falsevalue', 'false')
            ]

        if test_param_optional:
            lint_ctx.warn("Conditional test parameter declares an invalid optional attribute.")

        whens = conditional.findall('./when')
        if any(['value' not in when.attrib for when in whens]):
            lint_ctx.error("When without value")

        when_ids = [w.attrib.get('value', None) for w in whens]
        when_ids = [i.lower() if i in ["True", "False"] else i for i in when_ids]

        for select_id in select_option_ids:
            if select_id not in when_ids:
                lint_ctx.warn("No <when /> block found for select option '%s'" % select_id)

        for when_id in when_ids:
            if when_id not in select_option_ids:
                lint_ctx.warn("No <option /> block found for when block '%s'" % when_id)

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
