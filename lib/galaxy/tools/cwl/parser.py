""" This module provides proxy objects around objects from the common
workflow language reference implementation library cwltool. These proxies
adapt cwltool to Galaxy features and abstract the library away from the rest
of the framework.
"""
from __future__ import absolute_import
from abc import ABCMeta, abstractmethod
from galaxy.util.odict import odict
import json
import os

from .cwltool_deps import (
    main,
    workflow,
    ensure_cwltool_available,
)

from galaxy.util.bunch import Bunch

JOB_JSON_FILE = ".cwl_job.json"


def tool_proxy(tool_path):
    """ Provide a proxy object to cwltool data structures to just
    grab relevant data.
    """
    ensure_cwltool_available()
    tool = to_cwl_tool_object(tool_path)
    return tool


def load_job_proxy(job_directory):
    ensure_cwltool_available()
    job_objects_path = os.path.join(job_directory, JOB_JSON_FILE)
    job_objects = json.load(open(job_objects_path, "r"))
    tool_path = job_objects["tool_path"]
    job_inputs = job_objects["job_inputs"]
    cwl_tool = tool_proxy(tool_path)
    cwl_job = cwl_tool.job_proxy(job_inputs, job_directory=job_directory)
    return cwl_job


def to_cwl_tool_object(tool_path):
    if workflow is None:
        raise Exception("Using CWL tools requires cwltool module.")
    proxy_class = None
    cwl_tool = None
    make_tool = workflow.defaultMakeTool
    cwl_tool = main.load_tool(tool_path, False, False, make_tool, False)
    proxy_class = Draft2ToolProxy
    if proxy_class is None:
        raise Exception("Unsupported CWL object encountered.")
    proxy = proxy_class(cwl_tool, tool_path)
    return proxy


class ToolProxy( object ):
    __metaclass__ = ABCMeta

    def __init__(self, tool, tool_path):
        self._tool = tool
        self._tool_path = tool_path

    def job_proxy(self, input_dict, job_directory="."):
        """ Build a cwltool.job.Job describing computation using a input_json
        Galaxy will generate mapping the Galaxy description of the inputs into
        a cwltool compatible variant.
        """
        return JobProxy(self, input_dict, job_directory=job_directory)

    @abstractmethod
    def input_instances(self):
        """ Return InputInstance objects describing mapping to Galaxy inputs. """

    @abstractmethod
    def output_instances(self):
        """ Return OutputInstance objects describing mapping to Galaxy inputs. """

    @abstractmethod
    def docker_identifier(self):
        """ Return docker identifier for embedding in tool description. """

    @abstractmethod
    def description(self):
        """ Return description to tool. """


class Draft2ToolProxy(ToolProxy):

    def description(self):
        # Feels like I should be getting some abstract namespaced thing
        # not actually description, is this correct?
        return self._tool.tool.get('description')

    def input_instances(self):
        return self._find_inputs(self._tool.inputs_record_schema)

    def _find_inputs(self, schema):
        schema_type = schema["type"]
        if isinstance(schema_type, list):
            raise Exception("Union types not yet implemented.")
        elif isinstance(schema_type, dict):
            return self._find_inputs(schema_type)
        else:
            if schema_type in self._tool.schemaDefs:
                schema = self._tool.schemaDefs[schema_type]

            if schema["type"] == "record":
                return map(_simple_field_to_input, schema["fields"])

    def output_instances(self):
        outputs_schema = self._tool.outputs_record_schema
        return self._find_outputs(outputs_schema)

    def _find_outputs(self, schema):
        rval = []
        if not rval and schema["type"] == "record":
            for output in schema["fields"]:
                # TODO: Handle non-files differently? Make them
                # JSON maybe?.
                # output_type = output.get("type", None)
                # if output_type != "File":
                #     template = "Unhandled output type [%s] encountered."
                #     raise Exception(template % output_type)
                rval.append(_simple_field_to_output(output))

        return rval

    def docker_identifier(self):
        tool = self._tool.tool
        reqs_and_hints = tool.get("requirements", []) + tool.get("hints", [])
        for hint in reqs_and_hints:
            if hint["class"] == "DockerRequirement":
                if "dockerImageId" in hint:
                    return hint["dockerImageId"]
                else:
                    return hint["dockerPull"]
        return None


class JobProxy(object):

    def __init__(self, tool_proxy, input_dict, job_directory):
        self._tool_proxy = tool_proxy
        self._input_dict = input_dict
        self._job_directory = job_directory

    def cwl_job(self):
        return self._tool_proxy._tool.job(
            self._input_dict,
            self._job_directory,
            self._output_callback,
            use_container=False
        ).next()

    def _output_callback(self, out):
        pass

    def save_job(self):
        job_file = JobProxy._job_file(self._job_directory)
        job_objects = {
            "tool_path": os.path.abspath(self._tool_proxy._tool_path),
            "job_inputs": self._input_dict,
        }
        json.dump(job_objects, open(job_file, "w"))

    # @staticmethod
    # def load_job(tool_proxy, job_directory):
    #     job_file = JobProxy._job_file(job_directory)
    #     input_dict = json.load(open(job_file, "r"))
    #     return JobProxy(tool_proxy, input_dict, job_directory)

    @staticmethod
    def _job_file(job_directory):
        return os.path.join(job_directory, JOB_JSON_FILE)


def _simple_field_union(field):
    field_type = _field_to_field_type(field)
    non_null_type = None
    if len(field_type) == 2:
        if "null" == field_type[0]:
            non_null_type = field_type[1]
        elif "null" == field_type[1]:
            non_null_type = field_type[1]

    if non_null_type is None:
        raise Exception("General union types not yet implemented (simple).")

    name, label, description = _field_metadata(field)

    case_name = "_cwl__type_"
    case_label = "Specify %s" % label

    options = [
        {"value": "null", "label": "No", "selected": True},
        {"value": "%s" % non_null_type, "label": "Yes", "selected": False},
    ]

    case_input = SelectInputInstance(
        name=case_name,
        label=case_label,
        description=False,
        options=options,
    )

    non_null_type_kwds = _simple_field_to_input_type_kwds(field, field_type=non_null_type)
    non_null_name = "_cwl__value_"
    non_null_label = label
    non_null_description = description
    non_null_input = InputInstance(
        non_null_name,
        non_null_label,
        non_null_description,
        **non_null_type_kwds
    )
    options = [
        ("null", []),
        (non_null_type, [non_null_input]),
    ]
    return ConditionalInstance(name, case_input, options)


def _simple_field_to_input(field):
    field_type = _field_to_field_type(field)
    if isinstance(field_type, list):
        # Length must be greater than 1...
        return _simple_field_union(field)

    name, label, description = _field_metadata(field)

    type_kwds = _simple_field_to_input_type_kwds(field)
    return InputInstance(name, label, description, **type_kwds)


def _simple_field_to_input_type_kwds(field, field_type=None):
    simple_map_type_map = {
        "File": INPUT_TYPE.DATA,
        "int": INPUT_TYPE.INTEGER,
        "string": INPUT_TYPE.TEXT,
        "boolean": INPUT_TYPE.BOOLEAN,
    }

    if field_type is None:
        field_type = _field_to_field_type(field)

    if field_type in simple_map_type_map.keys():
        input_type = simple_map_type_map[field_type]
        return {"input_type": input_type, "array": False}
    elif field_type == "array":
        if isinstance(field["type"], dict):
            array_type = field["type"]["items"]
        else:
            array_type = field["items"]
        if array_type in simple_map_type_map.keys():
            input_type = simple_map_type_map[array_type]
        return {"input_type": input_type, "array": True}
    else:
        raise Exception("Unhandled simple field type encountered - [%s]." % field_type)


def _field_to_field_type(field):
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


def _field_metadata(field):
    name = field["name"]
    label = field.get("label", None)
    description = field.get("description", None)
    return name, label, description


def _simple_field_to_output(field):
    name = field["name"]
    output_instance = OutputInstance(name, output_type=OUTPUT_TYPE.GLOB)
    return output_instance


INPUT_TYPE = Bunch(
    DATA="data",
    INTEGER="integer",
    TEXT="text",
    BOOLEAN="boolean",
    SELECT="select",
    CONDITIONAL="conditional",
)


class ConditionalInstance(object):

    def __init__(self, name, case, whens):
        self.input_type = INPUT_TYPE.CONDITIONAL
        self.name = name
        self.case = case
        self.whens = whens

    def to_dict(self):

        as_dict = dict(
            name=self.name,
            type=INPUT_TYPE.CONDITIONAL,
            test=self.case.to_dict(),
            when=odict(),
        )
        for value, block in self.whens:
            as_dict["when"][value] = map(lambda i: i.to_dict(), block)

        return as_dict


class SelectInputInstance(object):

    def __init__(self, name, label, description, options):
        self.input_type = INPUT_TYPE.SELECT
        self.name = name
        self.label = label
        self.description = description
        self.options = options

    def to_dict(self):
        # TODO: serialize options...
        as_dict = dict(
            name=self.name,
            label=self.label or self.name,
            help=self.description,
            type=self.input_type,
            options=self.options,
        )
        return as_dict


class InputInstance(object):

    def __init__(self, name, label, description, input_type, array=False):
        self.input_type = input_type
        self.name = name
        self.label = label
        self.description = description
        self.required = True
        self.array = array

    def to_dict(self, itemwise=True):
        if itemwise and self.array:
            as_dict = dict(
                type="repeat",
                name="%s_repeat" % self.name,
                title="%s" % self.name,
                blocks=[
                    self.to_dict(itemwise=False)
                ]
            )
        else:
            as_dict = dict(
                name=self.name,
                label=self.label or self.name,
                help=self.description,
                type=self.input_type,
                optional=not self.required,
            )
            if self.input_type == INPUT_TYPE.INTEGER:
                as_dict["value"] = "0"
        return as_dict


OUTPUT_TYPE = Bunch(
    GLOB="glob",
    STDOUT="stdout",
)


class OutputInstance(object):

    def __init__(self, name, output_type, path=None):
        self.name = name
        self.output_type = output_type
        self.path = path


__all__ = [
    'tool_proxy',
    'load_job_proxy',
]
