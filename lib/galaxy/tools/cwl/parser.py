""" This module provides proxy objects around objects from the common
workflow language reference implementation library cwltool. These proxies
adapt cwltool to Galaxy features and abstract the library away from the rest
of the framework.
"""
from __future__ import absolute_import

import base64
import json
import logging
import os
import pickle
from abc import ABCMeta, abstractmethod

import six

from galaxy.exceptions import MessageException
from galaxy.util import listify, safe_makedirs
from galaxy.util.bunch import Bunch
from galaxy.util.odict import odict
from .cwltool_deps import (
    ensure_cwltool_available,
    pathmapper,
    process,
)
from .representation import (
    field_to_field_type,
    FIELD_TYPE_REPRESENTATION,
    INPUT_TYPE,
    type_descriptions_for_field_types,
    USE_FIELD_TYPES,
    USE_STEP_PARAMETERS,
)
from .schema import non_strict_schema_loader, schema_loader
from .util import SECONDARY_FILES_EXTRA_PREFIX

log = logging.getLogger(__name__)

JOB_JSON_FILE = ".cwl_job.json"

DOCKER_REQUIREMENT = "DockerRequirement"
SUPPORTED_TOOL_REQUIREMENTS = [
    "CreateFileRequirement",
    "DockerRequirement",
    "EnvVarRequirement",
    "InitialWorkDirRequirement",
    "InlineJavascriptRequirement",
    "ShellCommandRequirement",
    "ScatterFeatureRequirement",
    "SubworkflowFeatureRequirement",
    "StepInputExpressionRequirement",
    "MultipleInputFeatureRequirement",
]


SUPPORTED_WORKFLOW_REQUIREMENTS = SUPPORTED_TOOL_REQUIREMENTS + [
]


def tool_proxy(tool_path=None, tool_object=None, strict_cwl_validation=True):
    """ Provide a proxy object to cwltool data structures to just
    grab relevant data.
    """
    ensure_cwltool_available()
    tool = to_cwl_tool_object(
        tool_path=tool_path,
        tool_object=tool_object,
        strict_cwl_validation=strict_cwl_validation
    )
    return tool


def tool_proxy_from_persistent_representation(persisted_tool, strict_cwl_validation=True):
    ensure_cwltool_available()
    tool = to_cwl_tool_object(persisted_tool=persisted_tool, strict_cwl_validation=strict_cwl_validation)
    return tool


def workflow_proxy(workflow_path, strict_cwl_validation=True):
    ensure_cwltool_available()
    workflow = to_cwl_workflow_object(workflow_path, strict_cwl_validation=strict_cwl_validation)
    return workflow


def load_job_proxy(job_directory, strict_cwl_validation=True):
    ensure_cwltool_available()
    job_objects_path = os.path.join(job_directory, JOB_JSON_FILE)
    job_objects = json.load(open(job_objects_path, "r"))
    job_inputs = job_objects["job_inputs"]
    output_dict = job_objects["output_dict"]
    # Any reason to retain older tool_path variant of this? Probably not?
    if "tool_path" in job_objects:
        tool_path = job_objects["tool_path"]
        cwl_tool = tool_proxy(tool_path, strict_cwl_validation=strict_cwl_validation)
    else:
        persisted_tool = job_objects["tool_representation"]
        cwl_tool = tool_proxy_from_persistent_representation(persisted_tool, strict_cwl_validation=strict_cwl_validation)
    cwl_job = cwl_tool.job_proxy(job_inputs, output_dict, job_directory=job_directory)
    return cwl_job


def to_cwl_tool_object(tool_path=None, tool_object=None, persisted_tool=None, strict_cwl_validation=True):
    schema_loader = _schema_loader(strict_cwl_validation)
    if tool_path is not None:
        cwl_tool = schema_loader.tool(
            path=tool_path
        )
    elif tool_object is not None:
        # Allow loading tools from YAML...
        from ruamel import yaml as ryaml
        import json
        as_str = json.dumps(tool_object)
        tool_object = ryaml.round_trip_load(as_str)
        from schema_salad import sourceline
        from schema_salad.ref_resolver import file_uri
        uri = file_uri(os.getcwd()) + "/"
        sourceline.add_lc_filename(tool_object, uri)
        tool_object, _ = schema_loader.raw_document_loader.resolve_all(tool_object, uri)
        raw_process_reference = schema_loader.raw_process_reference_for_object(
            tool_object,
            uri=uri
        )
        cwl_tool = schema_loader.tool(
            raw_process_reference=raw_process_reference,
        )
    else:
        cwl_tool = ToolProxy.from_persistent_representation(persisted_tool)

    if isinstance(cwl_tool, int):
        raise Exception("Failed to load tool.")

    raw_tool = cwl_tool.tool
    # Apply Galaxy hacks to CWL tool representation to bridge semantic differences
    # between Galaxy and cwltool.
    _hack_cwl_requirements(cwl_tool)
    check_requirements(raw_tool)
    return cwl_tool_object_to_proxy(cwl_tool, tool_path=tool_path)


def cwl_tool_object_to_proxy(cwl_tool, tool_path=None):
    raw_tool = cwl_tool.tool
    if "class" not in raw_tool:
        raise Exception("File does not declare a class, not a valid Draft 3+ CWL tool.")

    process_class = raw_tool["class"]
    if process_class == "CommandLineTool":
        proxy_class = CommandLineToolProxy
    elif process_class == "ExpressionTool":
        proxy_class = ExpressionToolProxy
    else:
        raise Exception("File not a CWL CommandLineTool.")
    top_level_object = tool_path is not None
    if top_level_object and ("cwlVersion" not in raw_tool):
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


def _hack_cwl_requirements(cwl_tool):
    move_to_hints = []
    for i, requirement in enumerate(cwl_tool.requirements):
        if requirement["class"] == DOCKER_REQUIREMENT:
            move_to_hints.insert(0, i)

    for i in move_to_hints:
        del cwl_tool.requirements[i]
        cwl_tool.hints.append(requirement)


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
class ToolProxy(object):

    def __init__(self, tool, tool_path=None):
        self._tool = tool
        self._tool_path = tool_path

    def job_proxy(self, input_dict, output_dict, job_directory="."):
        """ Build a cwltool.job.Job describing computation using a input_json
        Galaxy will generate mapping the Galaxy description of the inputs into
        a cwltool compatible variant.
        """
        return JobProxy(self, input_dict, output_dict, job_directory=job_directory)

    @property
    def id(self):
        raw_id = self._tool.tool.get("id", None)
        return raw_id

    def galaxy_id(self):
        raw_id = self.id
        tool_id = None
        # don't reduce "search.cwl#index" to search
        if raw_id and "#" not in raw_id:
            tool_id = os.path.splitext(os.path.basename(raw_id))[0]
        if not tool_id:
            from galaxy.tools.hash import build_tool_hash
            tool_id = build_tool_hash(self.to_persistent_representation())
        assert tool_id
        return tool_id

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

    def to_persistent_representation(self):
        """Return a JSON representation of this tool. Not for serialization
        over the wire, but serialization in a database."""
        # TODO: Replace this with some more readable serialization,
        # I really don't like using pickle here.
        return {
            "class": self._class,
            "pickle": base64.b64encode(pickle.dumps(remove_pickle_problems(self._tool), -1)),
        }

    @staticmethod
    def from_persistent_representation(as_object):
        """Recover an object serialized with to_persistent_representation."""
        if "class" not in as_object:
            raise Exception("Failed to deserialize tool proxy from JSON object - no class found.")
        if "pickle" not in as_object:
            raise Exception("Failed to deserialize tool proxy from JSON object - no pickle representation found.")
        return pickle.loads(base64.b64decode(as_object["pickle"]))


class CommandLineToolProxy(ToolProxy):
    _class = "CommandLineTool"

    def description(self):
        return self._tool.tool.get('doc')

    def label(self):
        return self._tool.tool.get('label')

    def input_fields(self):
        input_records_schema = self._tool.inputs_record_schema
        schema_type = input_records_schema["type"]
        if schema_type in self._tool.schemaDefs:
            input_records_schema = self._tool.schemaDefs[schema_type]

        if input_records_schema["type"] != "record":
            raise Exception("Unhandled CWL tool input structure")

        return input_records_schema["fields"]

    def input_instances(self):
        return [_outer_field_to_input_instance(_) for _ in self.input_fields()]

    def output_instances(self):
        outputs_schema = self._tool.outputs_record_schema
        schema_type = outputs_schema["type"]
        if schema_type in self._tool.schemaDefs:
            outputs_schema = self._tool.schemaDefs[schema_type]

        if outputs_schema["type"] != "record":
            raise Exception("Unhandled CWL tool output structure")

        rval = []
        for output in outputs_schema["fields"]:
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

    def software_requirements(self):
        # Roughest imaginable pass at parsing requirements, really need to take in specs, handle
        # multiple versions, etc...
        tool = self._tool.tool
        reqs_and_hints = tool.get("requirements", []) + tool.get("hints", [])
        requirements = []
        for hint in reqs_and_hints:
            if hint["class"] == "SoftwareRequirement":
                packages = hint.get("packages", [])
                for package in packages:
                    versions = package.get("version", [])
                    first_version = None if not versions else versions[0]
                    requirements.append((package["package"], first_version))
        return requirements

    @property
    def requirements(self):
        return getattr(self._tool, "requirements", [])


class ExpressionToolProxy(CommandLineToolProxy):
    _class = "ExpressionTool"


class JobProxy(object):

    def __init__(self, tool_proxy, input_dict, output_dict, job_directory):
        self._tool_proxy = tool_proxy
        self._input_dict = input_dict
        self._output_dict = output_dict
        self._job_directory = job_directory

        self._final_output = None
        self._ok = True
        self._cwl_job = None
        self._is_command_line_job = None

        self._normalize_job()

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
                outdir=os.path.join(self._job_directory, "working"),
                tmpdir=os.path.join(self._job_directory, "cwltmp"),
                stagedir=os.path.join(self._job_directory, "cwlstagedir"),
                use_container=False,
            ))
            self._is_command_line_job = hasattr(self._cwl_job, "command_line")

    def _normalize_job(self):
        # Somehow reuse whatever causes validate in cwltool... maybe?
        def pathToLoc(p):
            if "location" not in p and "path" in p:
                p["location"] = p["path"]
                del p["path"]
        process.fillInDefaults(self._tool_proxy._tool.tool["inputs"], self._input_dict)
        process.visit_class(self._input_dict, ("File", "Directory"), pathToLoc)
        # TODO: Why doesn't fillInDefault fill in locations instead of paths?
        process.normalizeFilesDirs(self._input_dict)
        # TODO: validate like cwltool process _init_job.
        #    validate.validate_ex(self.names.get_name("input_record_schema", ""), builder.job,
        #                         strict=False, logger=_logger_validation_warnings)

    def rewrite_inputs_for_staging(self):
        if hasattr(self._cwl_job, "pathmapper"):
            pass
            # DO SOMETHING LIKE THE FOLLOWING?
            # path_rewrites = {}
            # for f, p in self._cwl_job.pathmapper.items():
            #     if not p.staged:
            #         continue
            #     if p.type in ("File", "Directory"):
            #         path_rewrites[p.resolved] = p.target
            # for key, value in self._input_dict.items():
            #     if key in path_rewrites:
            #         self._input_dict[key]["location"] = path_rewrites[value]
        else:
            stagedir = os.path.join(self._job_directory, "cwlstagedir")
            safe_makedirs(stagedir)

            def stage_recursive(value):
                is_list = isinstance(value, list)
                is_dict = isinstance(value, dict)
                log.info("handling value %s, is_list %s, is_dict %s" % (value, is_list, is_dict))
                if is_list:
                    for val in value:
                        stage_recursive(val)
                elif is_dict:
                    if "location" in value and "basename" in value:
                        location = value["location"]
                        basename = value["basename"]
                        if not location.endswith(basename):  # TODO: sep()[-1]
                            staged_loc = os.path.join(stagedir, basename)
                            if not os.path.exists(staged_loc):
                                os.symlink(location, staged_loc)
                            value["location"] = staged_loc
                    for key, dict_value in value.items():
                        stage_recursive(dict_value)
                else:
                    log.info("skipping simple value...")
            stage_recursive(self._input_dict)

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
        self._process_status = process_status
        if process_status == "success":
            self._final_output = out
        else:
            self._ok = False

        log.info("Output are %s, status is %s" % (out, process_status))

    def collect_outputs(self, tool_working_directory):
        if not self.is_command_line_job:
            cwl_job = self.cwl_job()
            cwl_job.run(
            )
            if not self._ok:
                raise Exception("Final process state not ok, [%s]" % self._process_status)
            return self._final_output
        else:
            return self.cwl_job().collect_outputs(tool_working_directory)

    def save_job(self):
        job_file = JobProxy._job_file(self._job_directory)
        job_objects = {
            # "tool_path": os.path.abspath(self._tool_proxy._tool_path),
            "tool_representation": self._tool_proxy.to_persistent_representation(),
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

    def output_directory_contents_dir(self, output_name, create=False):
        extra_files_dir = self._output_extra_files_dir(output_name)
        return extra_files_dir

    def output_secondary_files_dir(self, output_name, create=False):
        extra_files_dir = self._output_extra_files_dir(output_name)
        secondary_files_dir = os.path.join(extra_files_dir, SECONDARY_FILES_EXTRA_PREFIX)
        if create and not os.path.exists(secondary_files_dir):
            safe_makedirs(secondary_files_dir)
        return secondary_files_dir

    def stage_files(self):
        cwl_job = self.cwl_job()

        def stageFunc(resolved_path, target_path):
            log.info("resolving %s to %s" % (resolved_path, target_path))
            try:
                os.symlink(resolved_path, target_path)
            except OSError:
                pass

        if hasattr(cwl_job, "pathmapper"):
            process.stageFiles(cwl_job.pathmapper, stageFunc, ignoreWritable=True, symLink=False)

        if hasattr(cwl_job, "generatefiles"):
            outdir = os.path.join(self._job_directory, "working")
            # TODO: Why doesn't cwl_job.generatemapper work?
            generate_mapper = pathmapper.PathMapper(cwl_job.generatefiles["listing"],
                                                    outdir, outdir, separateDirs=False)
            # TODO: figure out what inplace_update should be.
            inplace_update = getattr(cwl_job, "inplace_update")
            process.stageFiles(generate_mapper, stageFunc, ignoreWritable=inplace_update, symLink=False)
            from cwltool import job
            job.relink_initialworkdir(generate_mapper, outdir, outdir, inplace_update=inplace_update)
        # else: expression tools do not have a path mapper.

    @staticmethod
    def _job_file(job_directory):
        return os.path.join(job_directory, JOB_JSON_FILE)


class WorkflowProxy(object):

    def __init__(self, workflow, workflow_path=None):
        self._workflow = workflow
        self._workflow_path = workflow_path

    @property
    def cwl_id(self):
        return self._workflow.tool["id"]

    def tool_references(self):
        """Fetch tool source definitions for all referenced tools."""
        references = []
        for step in self.step_proxies():
            references.extend(step.tool_references())
        return references

    def tool_reference_proxies(self):
        return map(lambda tool_object: cwl_tool_object_to_proxy(tool_object), self.tool_references())

    def step_proxies(self):
        proxies = []
        num_input_steps = len(self._workflow.tool['inputs'])
        for i, step in enumerate(self._workflow.steps):
            proxies.append(build_step_proxy(self, step, i + num_input_steps))
        return proxies

    @property
    def runnables(self):
        runnables = []
        for step in self._workflow.steps:
            if "run" in step.tool:
                runnables.append(step.tool["run"])
        return runnables

    def cwl_ids_to_index(self, step_proxies):
        index = 0
        cwl_ids_to_index = {}
        for i, input_dict in enumerate(self._workflow.tool['inputs']):
            cwl_ids_to_index[input_dict["id"]] = index
            index += 1

        for step_proxy in step_proxies:
            cwl_ids_to_index[step_proxy.cwl_id] = index
            index += 1

        return cwl_ids_to_index

    @property
    def output_labels(self):
        return [self.jsonld_id_to_label(o['id']) for o in self._workflow.tool['outputs']]

    def input_connections_by_step(self, step_proxies):
        cwl_ids_to_index = self.cwl_ids_to_index(step_proxies)
        input_connections_by_step = []
        for step_proxy in step_proxies:
            input_connections_step = {}
            for input_proxy in step_proxy.input_proxies:
                cwl_source_id = input_proxy.cwl_source_id
                input_name = input_proxy.input_name
                # Consider only allow multiple if MultipleInputFeatureRequirement is enabled
                for (output_step_name, output_name) in split_step_references(cwl_source_id, workflow_id=self.cwl_id):
                    if "#" in self.cwl_id:
                        sep_on = "/"
                    else:
                        sep_on = "#"
                    output_step_id = self.cwl_id + sep_on + output_step_name

                    if output_step_id not in cwl_ids_to_index:
                        template = "Output [%s] does not appear in ID-to-index map [%s]."
                        msg = template % (output_step_id, cwl_ids_to_index.keys())
                        raise AssertionError(msg)

                    if input_name not in input_connections_step:
                        input_connections_step[input_name] = []

                    input_connections_step[input_name].append({
                        "id": cwl_ids_to_index[output_step_id],
                        "output_name": output_name,
                        "input_type": "dataset"
                    })

            input_connections_by_step.append(input_connections_step)

        return input_connections_by_step

    def to_dict(self):
        name = os.path.basename(self._workflow_path or 'TODO - derive a name from ID')
        steps = {}

        step_proxies = self.step_proxies()
        input_connections_by_step = self.input_connections_by_step(step_proxies)
        index = 0
        for i, input_dict in enumerate(self._workflow.tool['inputs']):
            steps[index] = self.cwl_input_to_galaxy_step(input_dict, i)
            index += 1

        for i, step_proxy in enumerate(step_proxies):
            input_connections = input_connections_by_step[i]
            steps[index] = step_proxy.to_dict(input_connections)
            index += 1

        return {
            'name': name,
            'steps': steps,
            'annotation': self.cwl_object_to_annotation(self._workflow.tool),
        }

    def find_inputs_step_index(self, label):
        for i, input in enumerate(self._workflow.tool['inputs']):
            if self.jsonld_id_to_label(input["id"]) == label:
                return i

        raise Exception("Failed to find index for label %s" % label)

    def jsonld_id_to_label(self, id):
        if "#" in self.cwl_id:
            return id.rsplit("/", 1)[-1]
        else:
            return id.rsplit("#", 1)[-1]

    def cwl_input_to_galaxy_step(self, input, i):
        input_type = input["type"]
        input_as_dict = {
            "id": i,
            "label": self.jsonld_id_to_label(input["id"]),
            "position": {"left": 0, "top": 0},
            "annotation": self.cwl_object_to_annotation(input),
            "input_connections": {},  # Should the Galaxy API really require this? - Seems to.
        }

        if input_type == "File" and "default" not in input:
            input_as_dict["type"] = "data_input"
        elif isinstance(input_type, dict) and input_type.get("type") == "array":
            input_as_dict["type"] = "data_collection_input"
            input_as_dict["collection_type"] = "list"
        elif isinstance(input_type, dict) and input_type.get("type") == "record":
            input_as_dict["type"] = "data_collection_input"
            input_as_dict["collection_type"] = "record"
        else:
            if USE_STEP_PARAMETERS:
                input_as_dict["type"] = "parameter_input"
                # TODO: dispatch on actual type so this doesn't always need
                # to be field - simpler types could be simpler inputs.
                tool_state = {}
                tool_state["parameter_type"] = "field"
                default_value = input.get("default")
                optional = False
                if isinstance(input_type, list) and "null" in input_type:
                    optional = True
                if not optional and isinstance(input_type, dict) and "type" in input_type:
                    assert False
                tool_state["default_value"] = {"src": "json", "value": default_value}
                tool_state["optional"] = optional
                input_as_dict["tool_state"] = tool_state
            else:
                input_as_dict["type"] = "data_input"
                # TODO: format = expression.json

        return input_as_dict

    def cwl_object_to_annotation(self, cwl_obj):
        return cwl_obj.get("doc", None)


def split_step_references(step_references, workflow_id=None, multiple=True):
    """Split a CWL step input or output reference into step id and name."""
    # Trim off the workflow id part of the reference.
    step_references = listify(step_references)
    split_references = []

    for step_reference in step_references:
        if workflow_id is None:
            # This path works fine for some simple workflows - but not so much
            # for subworkflows (maybe same for $graph workflows?)
            assert "#" in step_reference
            _, step_reference = step_reference.split("#", 1)
        else:
            if "#" in workflow_id:
                sep_on = "/"
            else:
                sep_on = "#"
            assert step_reference.startswith(workflow_id + sep_on)
            step_reference = step_reference[len(workflow_id + sep_on):]

        # Now just grab the step name and input/output name.
        assert "#" not in step_reference
        if "/" in step_reference:
            step_name, io_name = step_reference.split("/", 1)
        else:
            # Referencing an input, not a step.
            # In Galaxy workflows input steps have an implicit output named
            # "output" for consistency with tools - in cwl land
            # just the input name is referenced.
            step_name = step_reference
            io_name = "output"
        split_references.append((step_name, io_name))

    if multiple:
        return split_references
    else:
        assert len(split_references) == 1
        return split_references[0]


def build_step_proxy(workflow_proxy, step, index):
    step_type = step.embedded_tool.tool["class"]
    if step_type == "Workflow":
        return SubworkflowStepProxy(workflow_proxy, step, index)
    else:
        return ToolStepProxy(workflow_proxy, step, index)


class BaseStepProxy(object):

    def __init__(self, workflow_proxy, step, index):
        self._workflow_proxy = workflow_proxy
        self._step = step
        self._index = index

    @property
    def step_class(self):
        return self.cwl_tool_object.tool["class"]

    @property
    def cwl_id(self):
        return self._step.id

    @property
    def cwl_workflow_id(self):
        return self._workflow_proxy.cwl_id

    @property
    def requirements(self):
        return self._step.requirements

    @property
    def hints(self):
        return self._step.hints

    @property
    def label(self):
        label = self._workflow_proxy.jsonld_id_to_label(self._step.id)
        return label

    def galaxy_workflow_outputs_list(self):
        outputs = []
        for output in self._workflow_proxy._workflow.tool['outputs']:
            step, output_name = split_step_references(
                output["outputSource"],
                multiple=False,
                workflow_id=self._workflow_proxy.cwl_id,
            )
            if step == self.label:
                output_id = output["id"]
                if "#" not in self._workflow_proxy.cwl_id:
                    _, output_label = output_id.rsplit("#", 1)
                else:
                    _, output_label = output_id.rsplit("/", 1)

                outputs.append({
                    "output_name": output_name,
                    "label": output_label,
                })
        return outputs

    @property
    def cwl_tool_object(self):
        return self._step.embedded_tool

    @property
    def input_proxies(self):
        cwl_inputs = self._step.tool["inputs"]
        for cwl_input in cwl_inputs:
            yield InputProxy(self, cwl_input)

    def inputs_to_dicts(self):
        inputs_as_dicts = []
        for input_proxy in self.input_proxies:
            inputs_as_dicts.append(input_proxy.to_dict())
        return inputs_as_dicts


class InputProxy(object):

    def __init__(self, step_proxy, cwl_input):
        self._cwl_input = cwl_input
        self.step_proxy = step_proxy
        self.workflow_proxy = step_proxy._workflow_proxy

        cwl_input_id = cwl_input["id"]
        cwl_source_id = cwl_input.get("source", None)
        if cwl_source_id is None:
            if "valueFrom" not in cwl_input and "default" not in cwl_input:
                msg = "Workflow step input must define a source, a valueFrom, or a default value. Obtained [%s]." % cwl_input
                raise MessageException(msg)

        assert cwl_input_id
        step_name, input_name = split_step_references(
            cwl_input_id,
            multiple=False,
            workflow_id=step_proxy.cwl_workflow_id
        )
        self.step_name = step_name
        self.input_name = input_name

        self.cwl_input_id = cwl_input_id
        self.cwl_source_id = cwl_source_id

        scatter_inputs = [split_step_references(
            i, multiple=False, workflow_id=step_proxy.cwl_workflow_id
        )[1] for i in listify(step_proxy._step.tool.get("scatter", []))]
        scatter = self.input_name in scatter_inputs
        self.scatter = scatter

    def to_dict(self):
        as_dict = {
            "name": self.input_name,
        }
        if "linkMerge" in self._cwl_input:
            as_dict["merge_type"] = self._cwl_input["linkMerge"]
        if "scatterMethod" in self.step_proxy._step.tool:
            as_dict["scatter_type"] = self.step_proxy._step.tool.get("scatterMethod", "dotproduct")
        else:
            as_dict["scatter_type"] = "dotproduct" if self.scatter else "disabled"
        if "valueFrom" in self._cwl_input:
            # TODO: Add a table for expressions - mark the type as CWL 1.0 JavaScript.
            as_dict["value_from"] = self._cwl_input["valueFrom"]
        if "default" in self._cwl_input:
            as_dict["default"] = self._cwl_input["default"]
        return as_dict


class ToolStepProxy(BaseStepProxy):

    @property
    def tool_proxy(self):
        return cwl_tool_object_to_proxy(self.cwl_tool_object)

    def tool_references(self):
        # Return a list so we can handle subworkflows recursively in the future.
        return [self._step.embedded_tool]

    def to_dict(self, input_connections):
        # We are to the point where we need a content id for this. We got
        # figure that out - short term we can load everything up as an
        # in-memory tool and reference by the JSONLD ID I think. So workflow
        # proxy should force the loading of a tool.
        tool_proxy = cwl_tool_object_to_proxy(self.tool_references()[0])
        from galaxy.tools.hash import build_tool_hash
        tool_hash = build_tool_hash(tool_proxy.to_persistent_representation())

        # We need to stub out null entries for things getting replaced by
        # connections. This doesn't seem ideal - consider just making Galaxy
        # handle this.
        tool_state = {}
        for input_name in input_connections.keys():
            tool_state[input_name] = None

        outputs = self.galaxy_workflow_outputs_list()
        return {
            "id": self._index,
            "tool_hash": tool_hash,
            "label": self.label,
            "position": {"left": 0, "top": 0},
            "type": "tool",
            "annotation": self._workflow_proxy.cwl_object_to_annotation(self._step.tool),
            "input_connections": input_connections,
            "inputs": self.inputs_to_dicts(),
            "workflow_outputs": outputs,
        }


class SubworkflowStepProxy(BaseStepProxy):

    def to_dict(self, input_connections):
        outputs = self.galaxy_workflow_outputs_list()
        for key, input_connection_list in input_connections.items():
            input_subworkflow_step_id = self.workflow_proxy.find_inputs_step_index(
                key
            )
            for input_connection in input_connection_list:
                input_connection["input_subworkflow_step_id"] = input_subworkflow_step_id

        return {
            "id": self._index,
            "label": self.label,
            "position": {"left": 0, "top": 0},
            "type": "subworkflow",
            "subworkflow": self.workflow_proxy.to_dict(),
            "annotation": self._workflow_proxy.cwl_object_to_annotation(self._step.tool),
            "input_connections": input_connections,
            "inputs": self.inputs_to_dicts(),
            "workflow_outputs": outputs,
        }

    def tool_references(self):
        return self.workflow_proxy.tool_references()

    @property
    def workflow_proxy(self):
        return WorkflowProxy(self.cwl_tool_object)


def remove_pickle_problems(obj):
    """doc_loader does not pickle correctly"""
    if hasattr(obj, "doc_loader"):
        obj.doc_loader = None
    if hasattr(obj, "embedded_tool"):
        obj.embedded_tool = remove_pickle_problems(obj.embedded_tool)
    if hasattr(obj, "steps"):
        obj.steps = [remove_pickle_problems(s) for s in obj.steps]
    return obj


@six.add_metaclass(ABCMeta)
class WorkflowToolReference(object):
    pass


class EmbeddedWorkflowToolReference(WorkflowToolReference):
    pass


class ExternalWorkflowToolReference(WorkflowToolReference):
    pass


def _outer_field_to_input_instance(field):
    field_type = field_to_field_type(field)  # Must be a list if in here?
    if not isinstance(field_type, list):
        field_type = [field_type]

    name, label, description = _field_metadata(field)

    case_name = "_cwl__type_"
    case_label = "Specify Parameter %s As" % label

    def value_input(type_description):
        value_name = "_cwl__value_"
        value_label = label
        value_description = description
        return InputInstance(
            value_name,
            value_label,
            value_description,
            input_type=type_description.galaxy_param_type,
            collection_type=type_description.collection_type,
        )

    select_options = []
    case_options = []
    type_descriptions = type_descriptions_for_field_types(field_type)
    for type_description in type_descriptions:
        select_options.append({"value": type_description.name, "label": type_description.label})
        input_instances = []
        if type_description.uses_param():
            input_instances.append(value_input(type_description))
        case_options.append((type_description.name, input_instances))

    # If there is more than one way to represent this parameter - produce a conditional
    # requesting user to ask for what form they want to submit the data in, else just map
    # a simple Galaxy parameter.
    if len(case_options) > 1 and not USE_FIELD_TYPES:
        case_input = SelectInputInstance(
            name=case_name,
            label=case_label,
            description=False,
            options=select_options,
        )

        return ConditionalInstance(name, case_input, case_options)
    else:
        if len(case_options) > 1:
            only_type_description = FIELD_TYPE_REPRESENTATION
        else:
            only_type_description = type_descriptions[0]

        return InputInstance(
            name, label, description, input_type=only_type_description.galaxy_param_type, collection_type=only_type_description.collection_type
        )

    # Older array to repeat handling, now we are just representing arrays as
    # dataset collections - we should offer a blended approach in the future.
    # if field_type in simple_map_type_map.keys():
    #     input_type = simple_map_type_map[field_type]
    #     return {"input_type": input_type, "array": False}
    # elif field_type == "array":
    #     if isinstance(field["type"], dict):
    #         array_type = field["type"]["items"]
    #     else:
    #         array_type = field["items"]
    #     if array_type in simple_map_type_map.keys():
    #         input_type = simple_map_type_map[array_type]
    #     return {"input_type": input_type, "array": True}
    # else:
    #     raise Exception("Unhandled simple field type encountered - [%s]." % field_type)


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

    def __init__(self, name, label, description, input_type, array=False, area=False, collection_type=None):
        self.input_type = input_type
        self.collection_type = collection_type
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
            elif self.input_type == INPUT_TYPE.DATA_COLLECTON:
                as_dict["collection_type"] = self.collection_type

        return as_dict


OUTPUT_TYPE = Bunch(
    GLOB="glob",
    STDOUT="stdout",
)


# TODO: Different subclasses - this is representing different types of things.
class OutputInstance(object):

    def __init__(self, name, output_data_type, output_type, path=None, fields=None):
        self.name = name
        self.output_data_type = output_data_type
        self.output_type = output_type
        self.path = path
        self.fields = fields


__all__ = (
    'tool_proxy',
    'load_job_proxy',
)
