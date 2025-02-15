"""This module is responsible for converting between Galaxy's tool
input description and the CWL description for a job json."""

import json
import logging
import os
from enum import Enum
from typing import (
    Any,
    NamedTuple,
    Optional,
)

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.util import (
    safe_makedirs,
    string_as_bool,
)
from .util import set_basename_and_derived_properties

log = logging.getLogger(__name__)

NOT_PRESENT = object()

NO_GALAXY_INPUT = object()


class INPUT_TYPE(str, Enum):
    DATA = "data"
    INTEGER = "integer"
    FLOAT = "float"
    TEXT = "text"
    BOOLEAN = "boolean"
    SELECT = "select"
    FIELD = "field"
    CONDITIONAL = "conditional"
    DATA_COLLECTION = "data_collection"


# There are two approaches to mapping CWL tool state to Galaxy tool state
# one is to map CWL types to compound Galaxy tool parameters combinations
# with conditionals and the other is to use a new Galaxy parameter type that
# allows unions, optional specifications, etc.... The problem with the former
# is that it doesn't work with the workflow parameters for instance and is
# very complex on the backend. The problem with the latter is that the GUI
# for this parameter type is undefined curently.
USE_FIELD_TYPES = True

# There are two approaches to mapping CWL workflow inputs to Galaxy workflow
# steps. The first is to simply map everything to expressions and stick them into
# files and use data inputs - the second is to use parameter_input steps with
# fields types. We are dispatching on USE_FIELD_TYPES for now - to choose but
# may diverge later?
# There are open issues with each approach:
#  - Mapping everything to files makes the GUI harder to imagine but the backend
#     easier to manage in someways.
USE_STEP_PARAMETERS = USE_FIELD_TYPES


class TypeRepresentation(NamedTuple):
    name: str
    galaxy_param_type: Any
    label: str
    collection_type: Optional[str]

    @property
    def uses_param(self):
        return self.galaxy_param_type is not NO_GALAXY_INPUT


TYPE_REPRESENTATIONS = [
    TypeRepresentation("null", NO_GALAXY_INPUT, "no input", None),
    TypeRepresentation("integer", INPUT_TYPE.INTEGER, "an integer", None),
    TypeRepresentation("float", INPUT_TYPE.FLOAT, "a decimal number", None),
    TypeRepresentation("double", INPUT_TYPE.FLOAT, "a decimal number", None),
    TypeRepresentation("file", INPUT_TYPE.DATA, "a dataset", None),
    TypeRepresentation("directory", INPUT_TYPE.DATA, "a directory", None),
    TypeRepresentation("boolean", INPUT_TYPE.BOOLEAN, "a boolean", None),
    TypeRepresentation("text", INPUT_TYPE.TEXT, "a simple text field", None),
    TypeRepresentation("record", INPUT_TYPE.DATA_COLLECTION, "record as a dataset collection", "record"),
    TypeRepresentation("json", INPUT_TYPE.TEXT, "arbitrary JSON structure", None),
    TypeRepresentation("array", INPUT_TYPE.DATA_COLLECTION, "as a dataset list", "list"),
    TypeRepresentation("enum", INPUT_TYPE.TEXT, "enum value", None),  # TODO: make this a select...
    TypeRepresentation("field", INPUT_TYPE.FIELD, "arbitrary JSON structure", None),
]
FIELD_TYPE_REPRESENTATION = TYPE_REPRESENTATIONS[-1]

if not USE_FIELD_TYPES:
    CWL_TYPE_TO_REPRESENTATIONS = {
        "Any": ["integer", "float", "file", "boolean", "text", "record", "json"],
        "org.w3id.cwl.salad.Any": ["integer", "float", "file", "boolean", "text", "record", "json"],
        "array": ["array"],
        "string": ["text"],
        "boolean": ["boolean"],
        "int": ["integer"],
        "float": ["float"],
        "File": ["file"],
        "org.w3id.cwl.cwl.File": ["file"],
        "Directory": ["directory"],
        "org.w3id.cwl.cwl.Directory": ["directory"],
        "null": ["null"],
        "record": ["record"],
    }
else:
    CWL_TYPE_TO_REPRESENTATIONS = {
        "Any": ["field"],
        "org.w3id.cwl.salad.Any": ["field"],
        "array": ["array"],
        "string": ["text"],
        "boolean": ["boolean"],
        "int": ["integer"],
        "float": ["float"],
        "File": ["file"],
        "org.w3id.cwl.cwl.File": ["file"],
        "Directory": ["directory"],
        "org.w3id.cwl.cwl.Directory": ["directory"],
        "null": ["null"],
        "record": ["record"],
        "enum": ["enum"],
        "double": ["double"],
    }


def type_representation_from_name(type_representation_name):
    for type_representation in TYPE_REPRESENTATIONS:
        if type_representation.name == type_representation_name:
            return type_representation
    else:
        raise ValueError(f"No type representation for {type_representation_name}")


def type_descriptions_for_field_types(field_types):
    type_representation_names = set()
    for field_type in field_types:
        if isinstance(field_type, dict) and field_type.get("type"):
            field_type = field_type.get("type")

        try:
            type_representation_names_for_field_type = CWL_TYPE_TO_REPRESENTATIONS.get(field_type)
        except TypeError:
            raise Exception(f"Failed to convert field_type {field_type}")
        if type_representation_names_for_field_type is None:
            raise Exception(f"Failed to convert type {field_type}")
        type_representation_names.update(type_representation_names_for_field_type)
    type_representations = []
    for type_representation in TYPE_REPRESENTATIONS:
        if type_representation.name in type_representation_names:
            type_representations.append(type_representation)
    return type_representations


def dataset_wrapper_to_file_json(inputs_dir, dataset_wrapper):
    if dataset_wrapper.ext == "expression.json":
        with open(dataset_wrapper.get_file_name()) as f:
            return json.load(f)

    if dataset_wrapper.ext == "directory":
        return dataset_wrapper_to_directory_json(inputs_dir, dataset_wrapper)

    extra_files_path = dataset_wrapper.extra_files_path
    secondary_files_path = os.path.join(extra_files_path, "__secondary_files__")
    path = str(dataset_wrapper)
    raw_file_object = {"class": "File"}

    if os.path.exists(secondary_files_path):
        safe_makedirs(inputs_dir)
        name = os.path.basename(path)
        new_input_path = os.path.join(inputs_dir, name)
        os.symlink(path, new_input_path)
        secondary_files = []
        for secondary_file_name in os.listdir(secondary_files_path):
            secondary_file_path = os.path.join(secondary_files_path, secondary_file_name)
            target = os.path.join(inputs_dir, secondary_file_name)
            log.info(f"linking [{secondary_file_path}] to [{target}]")
            os.symlink(secondary_file_path, target)
            is_dir = os.path.isdir(os.path.realpath(secondary_file_path))
            secondary_files.append({"class": "File" if not is_dir else "Directory", "location": target})

        raw_file_object["secondaryFiles"] = secondary_files
        path = new_input_path

    raw_file_object["location"] = path

    # Verify it isn't a NoneDataset
    if dataset_wrapper.unsanitized:
        raw_file_object["size"] = int(dataset_wrapper.get_size())

    set_basename_and_derived_properties(
        raw_file_object, str(dataset_wrapper.created_from_basename or dataset_wrapper.name)
    )
    return raw_file_object


def dataset_wrapper_to_directory_json(inputs_dir, dataset_wrapper):
    assert dataset_wrapper.ext == "directory"

    # get directory name
    archive_name = str(dataset_wrapper.created_from_basename or dataset_wrapper.name)
    nameroot, nameext = os.path.splitext(archive_name)
    directory_name = nameroot  # assume archive file name contains the directory name

    # get archive location
    try:
        archive_location = dataset_wrapper.unsanitized.get_file_name()
    except Exception:
        archive_location = None

    directory_json = {
        "location": dataset_wrapper.extra_files_path,
        "class": "Directory",
        "name": directory_name,
        "archive_location": archive_location,
        "archive_nameext": nameext,
        "archive_nameroot": nameroot,
    }

    return directory_json


def collection_wrapper_to_array(inputs_dir, wrapped_value):
    rval = []
    for value in wrapped_value:
        rval.append(dataset_wrapper_to_file_json(inputs_dir, value))
    return rval


def collection_wrapper_to_record(inputs_dir, wrapped_value):
    rval = {}
    for key, value in wrapped_value.items():
        rval[key] = dataset_wrapper_to_file_json(inputs_dir, value)
    return rval


def to_cwl_job(tool, param_dict, local_working_directory):
    """tool is Galaxy's representation of the tool and param_dict is the
    parameter dictionary with wrapped values.
    """
    tool_proxy = tool._cwl_tool_proxy
    input_fields = tool_proxy.input_fields()
    inputs = tool.inputs
    input_json = {}

    inputs_dir = os.path.join(local_working_directory, "_inputs")

    def simple_value(input, param_dict_value, type_representation_name=None):
        type_representation = type_representation_from_name(type_representation_name)
        # Hmm... cwl_type isn't really the cwl type in every case,
        # like in the case of json for instance.

        if type_representation.galaxy_param_type == NO_GALAXY_INPUT:
            assert param_dict_value is None
            return None

        if type_representation.name == "file":
            dataset_wrapper = param_dict_value
            return dataset_wrapper_to_file_json(inputs_dir, dataset_wrapper)
        elif type_representation.name == "directory":
            dataset_wrapper = param_dict_value
            return dataset_wrapper_to_directory_json(inputs_dir, dataset_wrapper)
        elif type_representation.name == "integer":
            return int(str(param_dict_value))
        elif type_representation.name == "long":
            return int(str(param_dict_value))
        elif type_representation.name in ["float", "double"]:
            return float(str(param_dict_value))
        elif type_representation.name == "boolean":
            return string_as_bool(param_dict_value)
        elif type_representation.name == "text":
            return str(param_dict_value)
        elif type_representation.name == "enum":
            return str(param_dict_value)
        elif type_representation.name == "json":
            raw_value = param_dict_value.value
            return json.loads(raw_value)
        elif type_representation.name == "field":
            if param_dict_value is None:
                return None
            if hasattr(param_dict_value, "value"):
                # Is InputValueWrapper
                rval = param_dict_value.value
                if isinstance(rval, dict) and "src" in rval and rval["src"] == "json":
                    # needed for wf_step_connect_undeclared_param, so non-file defaults?
                    return rval["value"]
                return rval
            elif not param_dict_value.is_collection:
                # Is DatasetFilenameWrapper
                return dataset_wrapper_to_file_json(inputs_dir, param_dict_value)
            else:
                # Is DatasetCollectionWrapper
                hdca_wrapper = param_dict_value
                if hdca_wrapper.collection_type == "list":
                    # TODO: generalize to lists of lists and lists of non-files...
                    return collection_wrapper_to_array(inputs_dir, hdca_wrapper)
                elif hdca_wrapper.collection_type.collection_type == "record":
                    return collection_wrapper_to_record(inputs_dir, hdca_wrapper)

        elif type_representation.name == "array":
            # TODO: generalize to lists of lists and lists of non-files...
            return collection_wrapper_to_array(inputs_dir, param_dict_value)
        elif type_representation.name == "record":
            return collection_wrapper_to_record(inputs_dir, param_dict_value)
        else:
            return str(param_dict_value)

    for input_name, input in inputs.items():
        if input.type == "repeat":
            only_input = next(iter(input.inputs.values()))
            array_value = []
            for instance in param_dict[input_name]:
                array_value.append(simple_value(only_input, instance[input_name[: -len("_repeat")]]))
            input_json[input_name[: -len("_repeat")]] = array_value
        elif input.type == "conditional":
            assert input_name in param_dict, f"No value for {input_name} in {param_dict}"
            current_case = param_dict[input_name]["_cwl__type_"]
            if str(current_case) != "null":  # str because it is a wrapped...
                case_index = input.get_current_case(current_case)
                case_input = input.cases[case_index].inputs["_cwl__value_"]
                case_value = param_dict[input_name]["_cwl__value_"]
                input_json[input_name] = simple_value(case_input, case_value, current_case)
        else:
            matched_field = None
            for field in input_fields:
                if field["name"] == input_name:
                    matched_field = field
            field_type = field_to_field_type(matched_field)
            if isinstance(field_type, list):
                assert USE_FIELD_TYPES
                type_descriptions = [FIELD_TYPE_REPRESENTATION]
            else:
                type_descriptions = type_descriptions_for_field_types([field_type])
            assert len(type_descriptions) == 1
            type_description_name = type_descriptions[0].name
            input_json[input_name] = simple_value(input, param_dict[input_name], type_description_name)

    log.debug(f"Galaxy Tool State is CWL State is {input_json}")
    return input_json


def to_galaxy_parameters(tool, as_dict):
    """Tool is Galaxy's representation of the tool and as_dict is a Galaxified
    representation of the input json (no paths, HDA references for instance).
    """
    inputs = tool.inputs
    galaxy_request = {}

    def from_simple_value(input, param_dict_value, type_representation_name=None):
        if type_representation_name == "json":
            return json.dumps(param_dict_value)
        else:
            return param_dict_value

    for input_name, input in inputs.items():
        as_dict_value = as_dict.get(input_name, NOT_PRESENT)
        galaxy_input_type = input.type

        if galaxy_input_type == "repeat":
            if input_name not in as_dict:
                continue

            only_input = next(iter(input.inputs.values()))
            for value in as_dict_value:
                key = f"{input_name}_repeat_0|{only_input.name}"
                galaxy_value = from_simple_value(only_input, value)
                galaxy_request[key] = galaxy_value
        elif galaxy_input_type == "conditional":
            case_strings = input.case_strings
            # TODO: less crazy handling of defaults...
            if (as_dict_value is NOT_PRESENT or as_dict_value is None) and "null" in case_strings:
                type_representation_name = "null"
            elif as_dict_value is NOT_PRESENT or as_dict_value is None:
                raise RequestParameterInvalidException(
                    f"Cannot translate CWL datatype - value [{as_dict_value}] of type [{type(as_dict_value)}] with case_strings [{case_strings}]. Non-null property must be set."
                )
            elif isinstance(as_dict_value, bool) and "boolean" in case_strings:
                type_representation_name = "boolean"
            elif isinstance(as_dict_value, int) and "integer" in case_strings:
                type_representation_name = "integer"
            elif isinstance(as_dict_value, int) and "long" in case_strings:
                type_representation_name = "long"
            elif isinstance(as_dict_value, (int, float)) and "float" in case_strings:
                type_representation_name = "float"
            elif isinstance(as_dict_value, (int, float)) and "double" in case_strings:
                type_representation_name = "double"
            elif isinstance(as_dict_value, str) and "string" in case_strings:
                type_representation_name = "string"
            elif (
                isinstance(as_dict_value, dict)
                and "src" in as_dict_value
                and "id" in as_dict_value
                and "file" in case_strings
            ):
                type_representation_name = "file"
            elif (
                isinstance(as_dict_value, dict)
                and "src" in as_dict_value
                and "id" in as_dict_value
                and "directory" in case_strings
            ):
                # TODO: can't disambiuate with above if both are available...
                type_representation_name = "directory"
            elif "field" in case_strings:
                type_representation_name = "field"
            elif "json" in case_strings and as_dict_value is not None:
                type_representation_name = "json"
            else:
                raise RequestParameterInvalidException(
                    f"Cannot translate CWL datatype - value [{as_dict_value}] of type [{type(as_dict_value)}] with case_strings [{case_strings}]."
                )
            galaxy_request[f"{input_name}|_cwl__type_"] = type_representation_name
            if type_representation_name != "null":
                current_case_index = input.get_current_case(type_representation_name)
                current_case_inputs = input.cases[current_case_index].inputs
                current_case_input = current_case_inputs["_cwl__value_"]
                galaxy_value = from_simple_value(current_case_input, as_dict_value, type_representation_name)
                galaxy_request[f"{input_name}|_cwl__value_"] = galaxy_value
        elif as_dict_value is NOT_PRESENT:
            continue
        else:
            galaxy_value = from_simple_value(input, as_dict_value)
            galaxy_request[input_name] = galaxy_value

    log.info(f"Converted galaxy_request is {galaxy_request}")
    return galaxy_request


def field_to_field_type(field):
    field_type = field["type"]
    if isinstance(field_type, dict):
        field_type = field_type["type"]
    if isinstance(field_type, list):
        field_type_length = len(field_type)
        if field_type_length == 0:
            raise Exception("Zero-length type list encountered, invalid CWL?")
        elif len(field_type) == 1:
            field_type = field_type[0]

    return field_type
