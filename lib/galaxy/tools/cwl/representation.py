""" This module is responsible for converting between Galaxy's tool
input description and the CWL description for a job json. """

import logging

from galaxy.util import string_as_bool

log = logging.getLogger(__name__)

NOT_PRESENT = object()


def to_cwl_job(tool, param_dict):
    """ tool is Galaxy's representation of the tool and param_dict is the
    parameter dictionary with wrapped values.
    """
    inputs = tool.inputs
    input_json = {}

    def simple_value(input, param_dict_value):
        if input.type == "data":
            return {"path": str(param_dict_value), "class": "File"}
        elif input.type == "integer":
            return int(str(param_dict_value))
        elif input.type == "boolean":
            return string_as_bool(param_dict_value)
        else:
            return str(param_dict_value)

    for input_name, input in inputs.iteritems():
        if input.type == "repeat":
            only_input = input.inputs.values()[0]
            array_value = []
            for instance in param_dict[input_name]:
                array_value.append(simple_value(only_input, instance[input_name[:-len("_repeat")]]))
            input_json[input_name[:-len("_repeat")]] = array_value
        elif input.type == "conditional":
            assert input_name in param_dict, "No value for %s in %s" % (input_name, param_dict)
            current_case = param_dict[input_name]["_cwl__type_"]
            if current_case != "null":
                # TODO: make sure trans is not needed here...
                case_index = input.get_current_case( current_case, None )
                case_input = input.cases[ case_index ].inputs[ "_cwl__value_"]
                case_value = param_dict[input_name]["_cwl__value_"]
                input_json[input_name] = simple_value(case_input, case_value)
        else:
            input_json[input_name] = simple_value(input, param_dict[input_name])

    input_json["allocatedResources"] = {
        "cpu": "$GALAXY_SLOTS",
    }
    return input_json


def to_galaxy_parameters(tool, as_dict):
    """ Tool is Galaxy's representation of the tool and as_dict is a Galaxified
    representation of the input json (no paths, HDA references for instance).
    """
    inputs = tool.inputs
    galaxy_request = {}

    def from_simple_value(input, param_dict_value):
        return param_dict_value

    for input_name, input in inputs.iteritems():
        as_dict_value = as_dict.get(input_name, NOT_PRESENT)

        if input.type == "repeat":
            if input_name not in as_dict:
                continue

            only_input = input.inputs.values()[0]
            for index, value in enumerate(as_dict_value):
                key = "%s_repeat_0|%s" % (input_name, only_input.name)
                galaxy_value = from_simple_value(only_input, value)
                galaxy_request[key] = galaxy_value
        elif input.type == "conditional":
            # TODO: less crazy handling of defaults...
            if as_dict_value is NOT_PRESENT:
                cwl_type = "null"
            elif isinstance(as_dict_value, bool):
                cwl_type = "boolean"
            elif isinstance(as_dict_value, int):
                cwl_type = "integer"
            else:
                cwl_type = "string"
            galaxy_request["%s|_cwl__type_" % input_name] = cwl_type
            if cwl_type != "null":
                current_case_index = input.get_current_case(cwl_type, None)
                current_case_input = input.cases[ current_case_index ].inputs[ "_cwl__value_" ]
                galaxy_value = from_simple_value(current_case_input, as_dict_value)
                galaxy_request["%s|_cwl__value_" % input_name] = galaxy_value
        elif as_dict_value is NOT_PRESENT:
            continue
        else:
            galaxy_value = from_simple_value(input, as_dict_value)
            galaxy_request[input_name] = galaxy_value

    log.info("Converted galaxy_request is %s" % galaxy_request)
    return galaxy_request
