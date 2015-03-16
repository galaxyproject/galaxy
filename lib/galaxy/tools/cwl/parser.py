""" This module provides proxy objects around objects from the common
workflow language reference implementation library cwltool. These proxies
adapt cwltool to Galaxy features and abstract the library away from the rest
of the framework.
"""
from __future__ import absolute_import
from abc import ABCMeta, abstractmethod
import json
import os

from .cwltool_deps import (
    draft1tool,
    draft2tool,
    ref_resolver,
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
    if ref_resolver is None:
        raise Exception("Using CWL tools requires cwltool module.")
    proxy_class = None
    cwl_tool = None
    toolpath_object = ref_resolver.from_url(tool_path)
    if "schema" in toolpath_object:
        proxy_class = Draft1ToolProxy
        cwl_tool = draft1tool.Tool(toolpath_object)
    if "class" in toolpath_object:
        if toolpath_object["class"] == "CommandLineTool":
            proxy_class = Draft2ToolProxy
            cwl_tool = draft2tool.CommandLineTool(toolpath_object)
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


class Draft1ToolProxy(ToolProxy):

    def input_instances(self):
        # TODO
        return self._tool.tool["inputs"]

    def output_instances(self):
        # TODO
        return []

    def docker_identifier(self):
        tool = self._tool
        requirements = tool.get("requirements", {})
        environment = requirements.get("environment", {})
        container = environment.get("container", {})
        container_type = container.get("type", "docker")
        if container_type != "docker":
            return None
        else:
            return container.get("uri", None)


class Draft2ToolProxy(ToolProxy):

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
                output_type = output.get("type", None)
                if output_type != "File":
                    raise Exception("Unhandled output type [%s] encountered.")
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
            basedir=self._job_directory,
            use_container=False
        )

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


def _simple_field_to_input(field):
    print field
    name = field["name"]
    field_type = field["type"]
    if isinstance(field_type, dict):
        field_type = field_type["type"]

    if isinstance(field_type, list):
        if len(field_type) > 1:
            raise Exception("Union types not yet implemented.")
        else:
            field_type = field_type[0]

    if field_type in ("File", "int"):
        if field_type == "File":
            input_type = INPUT_TYPE.DATA
        else:
            input_type = INPUT_TYPE.INTEGER
        return InputInstance(name, input_type)
    elif field_type == "array":
        if isinstance(field["type"], dict):
            array_type = field["type"]["items"]
        else:
            array_type = field["items"]
        if array_type in ("File", "int"):
            if array_type == "File":
                input_type = INPUT_TYPE.DATA
            elif array_type == "int":
                input_type = INPUT_TYPE.INTEGER
            else:
                raise Exception("Unhandled array type encountered - [%s]." % array_type)
        return InputInstance(name, input_type, array=True)
    else:
        raise Exception("Unhandled field type encountered - [%s]." % field_type)


def _simple_field_to_output(field):
    name = field["name"]
    output_instance = OutputInstance(name, output_type=OUTPUT_TYPE.GLOB)
    return output_instance


INPUT_TYPE = Bunch(
    DATA="data",
    INTEGER="integer",
)


class InputInstance(object):

    def __init__(self, name, input_type, array=False):
        self.input_type = input_type
        self.name = name
        self.required = True
        self.array = array

    def to_dict(self):
        as_dict = dict(
            name=self.name,
            label=self.name,
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
