""" This module provides proxy objects around objects from the common
workflow language reference implementation library cwltool. These proxies
adapt cwltool to Galaxy features and abstract the library away from the rest
of the framework.
"""
from __future__ import absolute_import

import json
import logging
import os
from abc import ABCMeta, abstractmethod

import six

from galaxy.util import safe_makedirs
from galaxy.util.bunch import Bunch
from galaxy.util.odict import odict

from .cwltool_deps import (
    ensure_cwltool_available,
    process,
)

from .schema import non_strict_schema_loader, schema_loader

log = logging.getLogger(__name__)

JOB_JSON_FILE = ".cwl_job.json"
SECONDARY_FILES_EXTRA_PREFIX = "__secondary_files__"


SUPPORTED_TOOL_REQUIREMENTS = [
    "CreateFileRequirement",
    "DockerRequirement",
    "EnvVarRequirement",
    "InlineJavascriptRequirement",
]


SUPPORTED_WORKFLOW_REQUIREMENTS = SUPPORTED_TOOL_REQUIREMENTS + [
]


def tool_proxy(tool_path, strict_cwl_validation=True):
    """ Provide a proxy object to cwltool data structures to just
    grab relevant data.
    """
    ensure_cwltool_available()
    tool = to_cwl_tool_object(tool_path, strict_cwl_validation=strict_cwl_validation)
    return tool


def workflow_proxy(workflow_path, strict_cwl_validation=True):
    ensure_cwltool_available()
    workflow = to_cwl_workflow_object(workflow_path, strict_cwl_validation=strict_cwl_validation)
    return workflow


def load_job_proxy(job_directory, strict_cwl_validation=True):
    ensure_cwltool_available()
    job_objects_path = os.path.join(job_directory, JOB_JSON_FILE)
    job_objects = json.load(open(job_objects_path, "r"))
    tool_path = job_objects["tool_path"]
    job_inputs = job_objects["job_inputs"]
    output_dict = job_objects["output_dict"]
    cwl_tool = tool_proxy(tool_path, strict_cwl_validation=strict_cwl_validation)
    cwl_job = cwl_tool.job_proxy(job_inputs, output_dict, job_directory=job_directory)
    return cwl_job


def to_cwl_tool_object(tool_path, strict_cwl_validation=True):
    proxy_class = None
    cwl_tool = _schema_loader(strict_cwl_validation).tool(path=tool_path)
    if isinstance(cwl_tool, int):
        raise Exception("Failed to load tool.")

    raw_tool = cwl_tool.tool
    check_requirements(raw_tool)
    if "class" not in raw_tool:
        raise Exception("File does not declare a class, not a valid Draft 3+ CWL tool.")
    process_class = raw_tool["class"]
    if process_class == "CommandLineTool":
        proxy_class = CommandLineToolProxy
    elif process_class == "ExpressionTool":
        proxy_class = ExpressionToolProxy
    else:
        raise Exception("File not a CWL CommandLineTool.")
    if "cwlVersion" not in raw_tool:
        raise Exception("File does not declare a CWL version, pre-draft 3 CWL tools are not supported.")

    proxy = proxy_class(cwl_tool, tool_path)
    return proxy


def to_cwl_workflow_object(workflow_path, strict_cwl_validation=None):
    proxy_class = WorkflowProxy
    cwl_workflow = _schema_loader(strict_cwl_validation).tool(path=workflow_path)
    raw_workflow = cwl_workflow.tool
    check_requirements(raw_workflow, tool=False)

    proxy = proxy_class(cwl_workflow, workflow_path)
    return proxy


def _schema_loader(strict_cwl_validation):
    target_schema_loader = schema_loader if strict_cwl_validation else non_strict_schema_loader
    return target_schema_loader


def check_requirements(rec, tool=True):
    if isinstance(rec, dict):
        if "requirements" in rec:
            for r in rec["requirements"]:
                if tool:
                    possible = SUPPORTED_TOOL_REQUIREMENTS
                else:
                    possible = SUPPORTED_WORKFLOW_REQUIREMENTS
                if r["class"] not in possible:
                    raise Exception("Unsupported requirement %s" % r["class"])
        for d in rec:
            check_requirements(rec[d], tool=tool)
    if isinstance(rec, list):
        for d in rec:
            check_requirements(d, tool=tool)


@six.add_metaclass(ABCMeta)
class ToolProxy( object ):

    def __init__(self, tool, tool_path):
        self._tool = tool
        self._tool_path = tool_path

    def job_proxy(self, input_dict, output_dict, job_directory="."):
        """ Build a cwltool.job.Job describing computation using a input_json
        Galaxy will generate mapping the Galaxy description of the inputs into
        a cwltool compatible variant.
        """
        return JobProxy(self, input_dict, output_dict, job_directory=job_directory)

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

    @abstractmethod
    def label(self):
        """ Return label for tool. """


class CommandLineToolProxy(ToolProxy):

    def description(self):
        return self._tool.tool.get('doc')

    def label(self):
        return self._tool.tool.get('label')

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
                return [_simple_field_to_input(_) for _ in schema["fields"]]

    def output_instances(self):
        outputs_schema = self._tool.outputs_record_schema
        return self._find_outputs(outputs_schema)

    def _find_outputs(self, schema):
        rval = []
        if not rval and schema["type"] == "record":
            for output in schema["fields"]:
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


class ExpressionToolProxy(CommandLineToolProxy):
    pass


class JobProxy(object):

    def __init__(self, tool_proxy, input_dict, output_dict, job_directory):
        self._tool_proxy = tool_proxy
        self._input_dict = input_dict
        self._output_dict = output_dict
        self._job_directory = job_directory

        self._final_output = []
        self._ok = True
        self._cwl_job = None
        self._is_command_line_job = None

    def cwl_job(self):
        self._ensure_cwl_job_initialized()
        return self._cwl_job

    @property
    def is_command_line_job(self):
        self._ensure_cwl_job_initialized()
        assert self._is_command_line_job is not None
        return self._is_command_line_job

    def _ensure_cwl_job_initialized(self):
        if self._cwl_job is None:

            self._cwl_job = next(self._tool_proxy._tool.job(
                self._input_dict,
                self._output_callback,
                basedir=self._job_directory,
                select_resources=self._select_resources,
                use_container=False
            ))
            self._is_command_line_job = hasattr(self._cwl_job, "command_line")

    def _select_resources(self, request):
        new_request = request.copy()
        new_request["cores"] = "$GALAXY_SLOTS"
        return new_request

    @property
    def command_line(self):
        if self.is_command_line_job:
            return self.cwl_job().command_line
        else:
            return ["true"]

    @property
    def stdin(self):
        if self.is_command_line_job:
            return self.cwl_job().stdin
        else:
            return None

    @property
    def stdout(self):
        if self.is_command_line_job:
            return self.cwl_job().stdout
        else:
            return None

    @property
    def environment(self):
        if self.is_command_line_job:
            return self.cwl_job().environment
        else:
            return {}

    @property
    def generate_files(self):
        if self.is_command_line_job:
            return self.cwl_job().generatefiles
        else:
            return {}

    def _output_callback(self, out, process_status):
        if process_status == "success":
            self._final_output = out
        else:
            self._ok = False

        log.info("Output are %s, status is %s" % (out, process_status))

    def collect_outputs(self, tool_working_directory):
        if not self.is_command_line_job:
            self.cwl_job().run(
            )
            return self._final_output
        else:
            return self.cwl_job().collect_outputs(tool_working_directory)

    def save_job(self):
        job_file = JobProxy._job_file(self._job_directory)
        job_objects = {
            "tool_path": os.path.abspath(self._tool_proxy._tool_path),
            "job_inputs": self._input_dict,
            "output_dict": self._output_dict,
        }
        json.dump(job_objects, open(job_file, "w"))

    def _output_extra_files_dir(self, output_name):
        output_id = self.output_id(output_name)
        return os.path.join(self._job_directory, "dataset_%s_files" % output_id)

    def output_id(self, output_name):
        output_id = self._output_dict[output_name]["id"]
        return output_id

    def output_path(self, output_name):
        output_id = self._output_dict[output_name]["path"]
        return output_id

    def output_secondary_files_dir(self, output_name, create=False):
        extra_files_dir = self._output_extra_files_dir(output_name)
        secondary_files_dir = os.path.join(extra_files_dir, SECONDARY_FILES_EXTRA_PREFIX)
        if create and not os.path.exists(secondary_files_dir):
            safe_makedirs(secondary_files_dir)
        return secondary_files_dir

    def stage_files(self):
        cwl_job = self.cwl_job()
        if hasattr(cwl_job, "pathmapper"):
            process.stageFiles(self.cwl_job().pathmapper, os.symlink, ignoreWritable=True)
        # else: expression tools do not have a path mapper.

    @staticmethod
    def _job_file(job_directory):
        return os.path.join(job_directory, JOB_JSON_FILE)


class WorkflowProxy(object):

    def __init__(self, workflow, workflow_path):
        self._workflow = workflow
        self._workflow_path = workflow_path

    def step_proxies(self):
        proxies = []
        for step in self._workflow.steps:
            proxies.append(StepProxy(self, step))
        return proxies

    @property
    def runnables(self):
        runnables = []
        for step in self._workflow.steps:
            if "run" in step.tool:
                runnables.append(step.tool["run"])
        return runnables

    def to_dict(self):
        name = os.path.basename(self._workflow_path)
        steps = {}

        index = 0
        for i, input_dict in self._workflow.tool['inputs']:
            index += 1
            steps[index] = input_dict

        for i, step_proxy in enumerate(self.step_proxies()):
            index += 1
            steps[index] = step_proxy.to_dict()

        return {
            'name': name,
            'steps': steps,
        }


class StepProxy(object):

    def __init__(self, workflow_proxy, step):
        self._workflow_proxy = workflow_proxy
        self._step = step

    def to_dict(self):
        return {}


def _simple_field_union(field):
    field_type = _field_to_field_type(field)  # Must be a list if in here?

    def any_of_in_field_type(types):
        return any([t in field_type for t in types])

    name, label, description = _field_metadata(field)

    case_name = "_cwl__type_"
    case_label = "Specify Parameter %s As" % label

    def value_input(**kwds):
        value_name = "_cwl__value_"
        value_label = label
        value_description = description
        return InputInstance(
            value_name,
            value_label,
            value_description,
            **kwds
        )

    select_options = []
    case_options = []
    if "null" in field_type:
        select_options.append({"value": "null", "label": "None", "selected": True})
        case_options.append(("null", []))
    if any_of_in_field_type(["Any", "string"]):
        select_options.append({"value": "string", "label": "Simple String"})
        case_options.append(("string", [value_input(input_type=INPUT_TYPE.TEXT)]))
    if any_of_in_field_type(["Any", "boolean"]):
        select_options.append({"value": "boolean", "label": "Boolean"})
        case_options.append(("boolean", [value_input(input_type=INPUT_TYPE.BOOLEAN)]))
    if any_of_in_field_type(["Any", "int"]):
        select_options.append({"value": "int", "label": "Integer"})
        case_options.append(("int", [value_input(input_type=INPUT_TYPE.INTEGER)]))
    if any_of_in_field_type(["Any", "float"]):
        select_options.append({"value": "float", "label": "Floating Point Number"})
        case_options.append(("float", [value_input(input_type=INPUT_TYPE.FLOAT)]))
    if any_of_in_field_type(["Any", "File"]):
        select_options.append({"value": "data", "label": "Dataset"})
        case_options.append(("data", [value_input(input_type=INPUT_TYPE.DATA)]))
    if "Any" in field_type:
        select_options.append({"value": "json", "label": "JSON Data Structure"})
        case_options.append(("json", [value_input(input_type=INPUT_TYPE.TEXT, area=True)]))

    case_input = SelectInputInstance(
        name=case_name,
        label=case_label,
        description=False,
        options=select_options,
    )

    return ConditionalInstance(name, case_input, case_options)


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
        "long": INPUT_TYPE.INTEGER,
        "float": INPUT_TYPE.INTEGER,
        "double": INPUT_TYPE.INTEGER,
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

    if field_type == "Any":
        field_type = ["Any"]

    return field_type


def _field_metadata(field):
    name = field["name"]
    label = field.get("label", None)
    description = field.get("doc", None)
    return name, label, description


def _simple_field_to_output(field):
    name = field["name"]
    output_data_class = field["type"]
    output_instance = OutputInstance(
        name,
        output_data_type=output_data_class,
        output_type=OUTPUT_TYPE.GLOB
    )
    return output_instance


INPUT_TYPE = Bunch(
    DATA="data",
    INTEGER="integer",
    FLOAT="float",
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
            as_dict["when"][value] = [i.to_dict() for i in block]

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

    def __init__(self, name, label, description, input_type, array=False, area=False):
        self.input_type = input_type
        self.name = name
        self.label = label
        self.description = description
        self.required = True
        self.array = array
        self.area = area

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
            if self.area:
                as_dict["area"] = True

            if self.input_type == INPUT_TYPE.INTEGER:
                as_dict["value"] = "0"
            if self.input_type == INPUT_TYPE.FLOAT:
                as_dict["value"] = "0.0"
        return as_dict


OUTPUT_TYPE = Bunch(
    GLOB="glob",
    STDOUT="stdout",
)


class OutputInstance(object):

    def __init__(self, name, output_data_type, output_type, path=None):
        self.name = name
        self.output_data_type = output_data_type
        self.output_type = output_type
        self.path = path


__all__ = (
    'tool_proxy',
    'load_job_proxy',
)
