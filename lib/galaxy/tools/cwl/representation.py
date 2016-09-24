""" This module is responsible for converting between Galaxy's tool
input description and the CWL description for a job json. """

import json
import logging
import os

from six import string_types

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.util import safe_makedirs, string_as_bool

log = logging.getLogger(__name__)

NOT_PRESENT = object()

GALAXY_TO_CWL_TYPES = {
    'integer': 'integer',
    'float': 'float',
    'data': 'File',
    'boolean': 'boolean',
}


def to_cwl_job(tool, param_dict, local_working_directory):
    """ tool is Galaxy's representation of the tool and param_dict is the
    parameter dictionary with wrapped values.
    """
    inputs = tool.inputs
    input_json = {}

    inputs_dir = os.path.join(local_working_directory, "_inputs")

    def simple_value(input, param_dict_value, cwl_type=None):
        # Hmm... cwl_type isn't really the cwl type in every case,
        # like in the case of json for instance.
        if cwl_type is None:
            input_type = input.type
            cwl_type = GALAXY_TO_CWL_TYPES[input_type]

        if cwl_type == "null":
            assert param_dict_value is None
            return None
        if cwl_type == "File":
            dataset_wrapper = param_dict_value
            extra_files_path = dataset_wrapper.extra_files_path
            secondary_files_path = os.path.join(extra_files_path, "__secondary_files__")
            path = str(dataset_wrapper)
            if os.path.exists(secondary_files_path):
                safe_makedirs(inputs_dir)
                name = os.path.basename(path)
                new_input_path = os.path.join(inputs_dir, name)
                os.symlink(path, new_input_path)
                for secondary_file_name in os.listdir(secondary_files_path):
                    secondary_file_path = os.path.join(secondary_files_path, secondary_file_name)
                    os.symlink(secondary_file_path, new_input_path + secondary_file_name)
                path = new_input_path

            return {"path": path, "class": "File"}
        elif cwl_type == "integer":
            return int(str(param_dict_value))
        elif cwl_type == "long":
            return int(str(param_dict_value))
        elif cwl_type == "float":
            return float(str(param_dict_value))
        elif cwl_type == "double":
            return float(str(param_dict_value))
        elif cwl_type == "boolean":
            return string_as_bool(param_dict_value)
        elif cwl_type == "string":
            return str(param_dict_value)
        elif cwl_type == "json":
            raw_value = param_dict_value.value
            log.info("raw_value is %s (%s)" % (raw_value, type(raw_value)))
            return json.loads(raw_value)
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
            if str(current_case) != "null":  # str because it is a wrapped...
                case_index = input.get_current_case( current_case )
                case_input = input.cases[ case_index ].inputs["_cwl__value_"]
                case_value = param_dict[input_name]["_cwl__value_"]
                input_json[input_name] = simple_value(case_input, case_value, cwl_type=current_case)
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

    def from_simple_value(input, param_dict_value, cwl_type=None):
        if cwl_type == "json":
            return json.dumps(param_dict_value)
        else:
            return param_dict_value

    for input_name, input in inputs.iteritems():
        as_dict_value = as_dict.get(input_name, NOT_PRESENT)
        galaxy_input_type = input.type

        if galaxy_input_type == "repeat":
            if input_name not in as_dict:
                continue

            only_input = input.inputs.values()[0]
            for index, value in enumerate(as_dict_value):
                key = "%s_repeat_0|%s" % (input_name, only_input.name)
                galaxy_value = from_simple_value(only_input, value)
                galaxy_request[key] = galaxy_value
        elif galaxy_input_type == "conditional":
            case_strings = input.case_strings
            # TODO: less crazy handling of defaults...
            if (as_dict_value is NOT_PRESENT or as_dict_value is None) and "null" in case_strings:
                cwl_type = "null"
            elif (as_dict_value is NOT_PRESENT or as_dict_value is None):
                raise RequestParameterInvalidException(
                    "Cannot translate CWL datatype - value [%s] of type [%s] with case_strings [%s]. Non-null property must be set." % (
                        as_dict_value, type(as_dict_value), case_strings
                    )
                )
            elif isinstance(as_dict_value, bool) and "boolean" in case_strings:
                cwl_type = "boolean"
            elif isinstance(as_dict_value, int) and "integer" in case_strings:
                cwl_type = "integer"
            elif isinstance(as_dict_value, int) and "long" in case_strings:
                cwl_type = "long"
            elif isinstance(as_dict_value, (int, float)) and "float" in case_strings:
                cwl_type = "float"
            elif isinstance(as_dict_value, (int, float)) and "double" in case_strings:
                cwl_type = "double"
            elif isinstance(as_dict_value, string_types) and "string" in case_strings:
                cwl_type = "string"
            elif isinstance(as_dict_value, dict) and "src" in as_dict_value and "id" in as_dict_value:
                # Bit problematic...
                cwl_type = "File"
            elif "json" in case_strings and as_dict_value is not None:
                cwl_type = "json"
            else:
                raise RequestParameterInvalidException(
                    "Cannot translate CWL datatype - value [%s] of type [%s] with case_strings [%s]." % (
                        as_dict_value, type(as_dict_value), case_strings
                    )
                )
            galaxy_request["%s|_cwl__type_" % input_name] = cwl_type
            if cwl_type != "null":
                current_case_index = input.get_current_case(cwl_type)
                current_case_inputs = input.cases[ current_case_index ].inputs
                current_case_input = current_case_inputs[ "_cwl__value_" ]
                galaxy_value = from_simple_value(current_case_input, as_dict_value, cwl_type)
                galaxy_request["%s|_cwl__value_" % input_name] = galaxy_value
        elif as_dict_value is NOT_PRESENT:
            continue
        else:
            galaxy_value = from_simple_value(input, as_dict_value)
            galaxy_request[input_name] = galaxy_value

    log.info("Converted galaxy_request is %s" % galaxy_request)
    return galaxy_request
