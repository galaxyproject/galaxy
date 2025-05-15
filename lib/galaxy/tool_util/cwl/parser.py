"""This module provides proxy objects around objects from the common
workflow language reference implementation library cwltool. These proxies
adapt cwltool to Galaxy features and abstract the library away from the rest
of the framework.
"""

import copy
import json
import logging
import os
from abc import (
    ABCMeta,
    abstractmethod,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
    overload,
    TYPE_CHECKING,
    Union,
)
from uuid import (
    UUID,
    uuid4,
)

from typing_extensions import (
    Literal,
    TypedDict,
)

from galaxy.exceptions import MessageException
from galaxy.util import (
    listify,
    safe_makedirs,
)
from galaxy.util.bunch import Bunch
from .cwltool_deps import (
    beta_relaxed_fmt_check,
    ensure_cwltool_available,
    getdefault,
    normalizeFilesDirs,
    pathmapper,
    process,
    ref_resolver,
    relink_initialworkdir,
    RuntimeContext,
    sourceline,
    StdFsAccess,
    visit_class,
    yaml_no_ts,
)
from .representation import (
    field_to_field_type,
    FIELD_TYPE_REPRESENTATION,
    INPUT_TYPE,
    type_descriptions_for_field_types,
    USE_FIELD_TYPES,
    USE_STEP_PARAMETERS,
)
from .schema import (
    non_strict_non_validating_schema_loader,
    schema_loader,
)
from .util import SECONDARY_FILES_EXTRA_PREFIX

if TYPE_CHECKING:
    from .cwltool_deps import (
        CWLObjectType,
        JobsType,
        workflow,
    )
    from .schema import RawProcessReference

log = logging.getLogger(__name__)

JOB_JSON_FILE = ".cwl_job.json"

DOCKER_REQUIREMENT = "DockerRequirement"
SUPPORTED_TOOL_REQUIREMENTS = [
    "CreateFileRequirement",
    "DockerRequirement",
    "EnvVarRequirement",
    "InitialWorkDirRequirement",
    "InlineJavascriptRequirement",
    "ResourceRequirement",
    "ShellCommandRequirement",
    "ScatterFeatureRequirement",
    "SchemaDefRequirement",
    "SubworkflowFeatureRequirement",
    "StepInputExpressionRequirement",
    "MultipleInputFeatureRequirement",
]


SUPPORTED_WORKFLOW_REQUIREMENTS = SUPPORTED_TOOL_REQUIREMENTS + []

ToolStateType = Dict[str, Union[None, str, bool, Dict[str, str]]]


class InputInstanceDict(TypedDict, total=False):
    type: str
    name: str
    title: str
    label: str
    help: str
    optional: bool
    area: bool
    value: str
    collection_type: str


class InputInstanceArrayDict(TypedDict):
    type: str
    name: str
    title: str
    blocks: List[InputInstanceDict]


class ToolProxy(metaclass=ABCMeta):
    _class: str

    def __init__(
        self,
        tool: process.Process,
        uuid: Union[UUID, str],
        raw_process_reference: Optional["RawProcessReference"] = None,
        tool_path: Optional[str] = None,
    ):
        self._tool = tool
        self.uuid = uuid
        self._tool_path = tool_path
        self._raw_process_reference = raw_process_reference
        # remove input parameter formats from CWL files so that cwltool
        # does not complain they are missing in the input data
        assert isinstance(self._tool.inputs_record_schema, dict)
        for input_field in self._tool.inputs_record_schema["fields"]:
            if "format" in input_field:
                del input_field["format"]

    def job_proxy(self, input_dict: Dict[str, Any], output_dict, job_directory: str = "."):
        """Build a cwltool.job.Job describing computation using a input_json
        Galaxy will generate mapping the Galaxy description of the inputs into
        a cwltool compatible variant.
        """
        return JobProxy(self, input_dict, output_dict, job_directory=job_directory)

    @property
    def id(self):
        raw_id = self._tool.tool.get("id", None)
        return raw_id

    def galaxy_id(self) -> str:
        raw_id = self.id
        tool_id = None
        # don't reduce "search.cwl#index" to search
        if raw_id:
            tool_id = os.path.basename(raw_id)
            # tool_id = os.path.splitext(os.path.basename(raw_id))[0]
        if not tool_id:
            return str(self.uuid)
        if tool_id.startswith("#"):
            tool_id = tool_id[1:]
        return tool_id

    @abstractmethod
    def input_fields(self) -> list:
        """Return InputInstance objects describing mapping to Galaxy inputs."""

    @abstractmethod
    def input_instances(self):
        """Return InputInstance objects describing mapping to Galaxy inputs."""

    @abstractmethod
    def output_instances(self) -> List["OutputInstance"]:
        """Return OutputInstance objects describing mapping to Galaxy inputs."""

    @abstractmethod
    def docker_identifier(self):
        """Return docker identifier for embedding in tool description."""

    @abstractmethod
    def description(self):
        """Return description to tool."""

    @abstractmethod
    def label(self):
        """Return label for tool."""

    def to_persistent_representation(self):
        """Return a JSON representation of this tool. Not for serialization
        over the wire, but serialization in a database."""
        persisted_obj = self._tool.tool
        persisted_obj["requirements"] = self.requirements
        if not persisted_obj.get("cwlVersion"):
            # This happens for any inline process, but getting it from metadata is correct for inline processes at least
            persisted_obj["cwlVersion"] = self._tool.metadata["cwlVersion"]
        return {
            "class": self._class,
            # Should maybe be yaml instead
            "raw_process_reference": persisted_obj,
            "uuid": self.uuid,
        }

    @staticmethod
    def from_persistent_representation(
        as_object: Dict[str, Any], strict_cwl_validation: bool = True, tool_directory: Optional[str] = None
    ) -> "ToolProxy":
        """Recover an object serialized with to_persistent_representation."""
        if "class" not in as_object:
            raise Exception("Failed to deserialize tool proxy from JSON object - no class found.")
        loaded_object = tool_proxy(
            tool_object=as_object["raw_process_reference"],
            strict_cwl_validation=strict_cwl_validation,
            tool_directory=tool_directory,
            uuid=as_object.get("uuid"),
        )
        return loaded_object

    @property
    def requirements(self) -> List:
        return getattr(self._tool, "requirements", [])

    def hints_or_requirements_of_class(self, class_name: str) -> List:
        reqs_and_hints = self.requirements + getattr(self._tool, "hints", [])
        return [hint for hint in reqs_and_hints if hint["class"] == class_name]

    def software_requirements(self) -> List:
        # Roughest imaginable pass at parsing requirements, really need to take in specs, handle
        # multiple versions, etc...
        requirements = []
        for hint in self.hints_or_requirements_of_class("SoftwareRequirement"):
            packages = hint.get("packages", [])
            for package in packages:
                versions = package.get("version", [])
                first_version = None if not versions else versions[0]
                requirements.append((package["package"], first_version))
        return requirements

    def resource_requirements(self) -> List:
        return self.hints_or_requirements_of_class("ResourceRequirement")


class CommandLineToolProxy(ToolProxy):
    _class = "CommandLineTool"

    def description(self):
        # Don't use description - typically too verbose.
        return ""

    def doc(self):
        # TODO: parse multiple lines and merge - valid in cwl-1.1
        doc = self._tool.tool.get("doc")
        return doc

    def label(self):
        label = self._tool.tool.get("label")

        if label is not None:
            return label.partition(":")[0]  # return substring before ':'
        else:
            return ""

    def input_fields(self) -> list:
        input_records_schema = self._eval_schema(self._tool.inputs_record_schema)
        if input_records_schema["type"] != "record":
            raise Exception("Unhandled CWL tool input structure")

        # TODO: handle this somewhere else?
        # schemadef_req_tool_param
        rval = []
        for input in input_records_schema["fields"]:
            input_copy = copy.deepcopy(input)
            input_type = input.get("type")
            if isinstance(input_type, list) or isinstance(input_type, dict):
                rval.append(input_copy)
                continue

            if input_type in self._tool.schemaDefs:
                input_copy["type"] = self._tool.schemaDefs[input_type]

            rval.append(input_copy)
        return rval

    def _eval_schema(self, io_schema):
        schema_type = io_schema.get("type")
        if schema_type in self._tool.schemaDefs:
            io_schema = self._tool.schemaDefs[schema_type]
        return io_schema

    def input_instances(self):
        return [_outer_field_to_input_instance(_) for _ in self.input_fields()]

    def output_instances(self):
        outputs_schema = self._eval_schema(self._tool.outputs_record_schema)
        if outputs_schema["type"] != "record":
            raise Exception("Unhandled CWL tool output structure")

        return [_simple_field_to_output(output) for output in outputs_schema["fields"]]

    def docker_identifier(self):
        for hint in self.hints_or_requirements_of_class("DockerRequirement"):
            if "dockerImageId" in hint:
                return hint["dockerImageId"]
            else:
                return hint["dockerPull"]

        return None


class ExpressionToolProxy(CommandLineToolProxy):
    _class = "ExpressionTool"


class JobProxy:
    _is_command_line_job: bool

    def __init__(self, tool_proxy: ToolProxy, input_dict: Dict[str, Any], output_dict, job_directory: str):
        assert RuntimeContext is not None, "cwltool is not installed, cannot run CWL jobs"
        self._tool_proxy = tool_proxy
        self._input_dict = input_dict
        self._output_dict = output_dict
        self._job_directory = job_directory

        self._final_output: Optional[CWLObjectType] = None
        self._ok = True
        self._cwl_job: Optional[JobsType] = None

        self._normalize_job()

    def cwl_job(self):
        self._ensure_cwl_job_initialized()
        return self._cwl_job

    @property
    def is_command_line_job(self):
        self._ensure_cwl_job_initialized()
        return self._is_command_line_job

    def _ensure_cwl_job_initialized(self):
        if self._cwl_job is None:
            job_args = dict(
                basedir=self._job_directory,
                select_resources=self._select_resources,
                outdir=os.path.join(self._job_directory, "working"),
                tmpdir=os.path.join(self._job_directory, "cwltmp"),
                stagedir=os.path.join(self._job_directory, "cwlstagedir"),
                use_container=False,
                beta_relaxed_fmt_check=beta_relaxed_fmt_check,
            )

            runtimeContext = RuntimeContext(job_args)
            self._cwl_job = next(self._tool_proxy._tool.job(self._input_dict, self._output_callback, runtimeContext))
            self._is_command_line_job = hasattr(self._cwl_job, "command_line")

    def _normalize_job(self):
        # Somehow reuse whatever causes validate in cwltool... maybe?
        def pathToLoc(p):
            if "location" not in p and "path" in p:
                p["location"] = p["path"]
                del p["path"]

        runtime_context = RuntimeContext({})
        make_fs_access = getdefault(runtime_context.make_fs_access, StdFsAccess)
        fs_access = make_fs_access(runtime_context.basedir)
        process.fill_in_defaults(self._tool_proxy._tool.tool["inputs"], self._input_dict, fs_access)
        visit_class(self._input_dict, ("File", "Directory"), pathToLoc)
        # TODO: Why doesn't fillInDefault fill in locations instead of paths?
        normalizeFilesDirs(self._input_dict)
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
                log.info(f"handling value {value}, is_list {is_list}, is_dict {is_dict}")
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
                    for dict_value in value.values():
                        stage_recursive(dict_value)
                else:
                    log.info("skipping simple value...")

            stage_recursive(self._input_dict)

    def _select_resources(self, request, runtime_context=None):
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
    def stderr(self):
        if self.is_command_line_job:
            return self.cwl_job().stderr
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

    def _output_callback(self, out: Optional["CWLObjectType"], process_status: str):
        self._process_status = process_status
        if process_status == "success":
            self._final_output = out
        else:
            self._ok = False

        log.info(f"Output are {out}, status is {process_status}")

    def collect_outputs(self, tool_working_directory: str, rcode: int):
        if not self.is_command_line_job:
            cwl_job = self.cwl_job()
            if RuntimeContext is not None:
                cwl_job.run(RuntimeContext({}))
            else:
                cwl_job.run()
            if not self._ok:
                raise Exception(f"Final process state not ok, [{self._process_status}]")
            return self._final_output
        else:
            return self.cwl_job().collect_outputs(tool_working_directory, rcode)

    def save_job(self) -> None:
        job_file = self._job_file(self._job_directory)
        job_objects = {
            # "tool_path": os.path.abspath(self._tool_proxy._tool_path),
            "tool_representation": self._tool_proxy.to_persistent_representation(),
            "job_inputs": self._input_dict,
            "output_dict": self._output_dict,
        }
        json.dump(job_objects, open(job_file, "w"))

    def _output_extra_files_dir(self, output_name):
        output_id = self.output_id(output_name)
        return os.path.join(self._job_directory, "outputs", f"dataset_{output_id}_files")

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
            log.info(f"resolving {resolved_path} to {target_path}")
            try:
                os.symlink(resolved_path, target_path)
            except OSError:
                pass

        if hasattr(cwl_job, "pathmapper"):
            process.stage_files(cwl_job.pathmapper, stageFunc, ignore_writable=True, symlink=False)

        if hasattr(cwl_job, "generatefiles"):
            outdir = os.path.join(self._job_directory, "working")
            # TODO: Why doesn't cwl_job.generatemapper work?
            generate_mapper = pathmapper.PathMapper(
                cwl_job.generatefiles["listing"], outdir, outdir, separateDirs=False
            )
            # TODO: figure out what inplace_update should be.
            inplace_update = cwl_job.inplace_update
            process.stage_files(generate_mapper, stageFunc, ignore_writable=inplace_update, symlink=False)
            relink_initialworkdir(generate_mapper, outdir, outdir, inplace_update=inplace_update)
        # else: expression tools do not have a path mapper.

    @staticmethod
    def _job_file(job_directory):
        return os.path.join(job_directory, JOB_JSON_FILE)


class WorkflowProxy:
    def __init__(self, workflow: "workflow.Workflow", workflow_path: Optional[str] = None):
        self._workflow = workflow
        self._workflow_path = workflow_path
        self._step_proxies: Optional[List[Union[SubworkflowStepProxy, ToolStepProxy]]] = None

    @property
    def cwl_id(self):
        return self._workflow.tool["id"]

    def get_outputs_for_label(self, label):
        outputs = []
        for output in self._workflow.tool["outputs"]:
            step, output_name = split_step_references(
                output["outputSource"],
                multiple=False,
                workflow_id=self.cwl_id,
            )
            if step == label:
                output_id = output["id"]
                if "#" not in self.cwl_id:
                    _, output_label = output_id.rsplit("#", 1)
                else:
                    _, output_label = output_id.rsplit("/", 1)

                outputs.append(
                    {
                        "output_name": output_name,
                        "label": output_label,
                    }
                )
        return outputs

    def tool_reference_proxies(self):
        """Fetch tool source definitions for all referenced tools."""
        references: List[ToolProxy] = []
        for step in self.step_proxies():
            references.extend(step.tool_reference_proxies())
        return references

    def step_proxies(self):
        if self._step_proxies is None:
            proxies = []
            num_input_steps = len(self._workflow.tool["inputs"])
            for i, step in enumerate(self._workflow.steps):
                proxies.append(build_step_proxy(self, step, i + num_input_steps))
            self._step_proxies = proxies
        return self._step_proxies

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
        for input_dict in self._workflow.tool["inputs"]:
            cwl_ids_to_index[input_dict["id"]] = index
            index += 1

        for step_proxy in step_proxies:
            cwl_ids_to_index[step_proxy.cwl_id] = index
            index += 1

        return cwl_ids_to_index

    @property
    def output_labels(self):
        return [self.jsonld_id_to_label(o["id"]) for o in self._workflow.tool["outputs"]]

    def input_connections_by_step(self, step_proxies):
        cwl_ids_to_index = self.cwl_ids_to_index(step_proxies)
        input_connections_by_step = []
        for step_proxy in step_proxies:
            input_connections_step: Dict[str, List[Dict[str, str]]] = {}
            for input_proxy in step_proxy.input_proxies:
                cwl_source_id = input_proxy.cwl_source_id
                input_name = input_proxy.input_name
                # Consider only allow multiple if MultipleInputFeatureRequirement is enabled
                for output_step_name, output_name in split_step_references(cwl_source_id, workflow_id=self.cwl_id):
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

                    input_connections_step[input_name].append(
                        {"id": cwl_ids_to_index[output_step_id], "output_name": output_name, "input_type": "dataset"}
                    )

            input_connections_by_step.append(input_connections_step)

        return input_connections_by_step

    def to_dict(self):
        name = os.path.basename(
            self._workflow.tool.get("label") or self._workflow_path or "TODO - derive a name from ID"
        )
        steps = {}

        step_proxies = self.step_proxies()
        input_connections_by_step = self.input_connections_by_step(step_proxies)
        index = 0
        for i, input_dict in enumerate(self._workflow.tool["inputs"]):
            steps[index] = self.cwl_input_to_galaxy_step(input_dict, i)
            index += 1

        for i, step_proxy in enumerate(step_proxies):
            input_connections = input_connections_by_step[i]
            steps[index] = step_proxy.to_dict(input_connections)
            index += 1

        return {
            "name": name,
            "steps": steps,
            "annotation": self.cwl_object_to_annotation(self._workflow.tool),
        }

    def find_inputs_step_index(self, label):
        for i, input in enumerate(self._workflow.tool["inputs"]):
            if self.jsonld_id_to_label(input["id"]) == label:
                return i

        raise Exception(f"Failed to find index for label {label}")

    def jsonld_id_to_label(self, id):
        if "#" in self.cwl_id:
            return id.rsplit("/", 1)[-1]
        else:
            return id.rsplit("#", 1)[-1]

    def cwl_input_to_galaxy_step(self, input, i):
        input_type = input["type"]
        label = self.jsonld_id_to_label(input["id"])
        input_as_dict = {
            "id": i,
            "label": label,
            "position": {"left": 0, "top": 0},
            "annotation": self.cwl_object_to_annotation(input),
            "input_connections": {},  # Should the Galaxy API really require this? - Seems to.
            "workflow_outputs": self.get_outputs_for_label(label),
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
                tool_state: ToolStateType = {}
                tool_state["parameter_type"] = "field"
                default_set = "default" in input
                default_value = input.get("default")
                optional = default_set
                if isinstance(input_type, list) and "null" in input_type:
                    optional = True
                if not optional and isinstance(input_type, dict) and "type" in input_type:
                    raise ValueError("'type' detected in non-optional input dictionary.")
                if default_set:
                    tool_state["default"] = {"src": "json", "value": default_value}
                tool_state["optional"] = optional
                input_as_dict["tool_state"] = tool_state
            else:
                input_as_dict["type"] = "data_input"
                # TODO: format = expression.json

        return input_as_dict

    def cwl_object_to_annotation(self, cwl_obj):
        return cwl_obj.get("doc", None)


def tool_proxy(
    tool_path: Optional[str] = None,
    tool_object=None,
    strict_cwl_validation: bool = True,
    tool_directory: Optional[str] = None,
    uuid: Optional[Union[UUID, str]] = None,
) -> ToolProxy:
    """Provide a proxy object to cwltool data structures to just
    grab relevant data.
    """
    ensure_cwltool_available()
    return _to_cwl_tool_object(
        tool_path=tool_path,
        tool_object=tool_object,
        strict_cwl_validation=strict_cwl_validation,
        tool_directory=tool_directory,
        uuid=uuid,
    )


def tool_proxy_from_persistent_representation(
    persisted_tool: Dict[str, Any], strict_cwl_validation: bool = True, tool_directory: Optional[str] = None
) -> ToolProxy:
    """Load a ToolProxy from a previously persisted representation."""
    ensure_cwltool_available()
    return ToolProxy.from_persistent_representation(
        persisted_tool, strict_cwl_validation=strict_cwl_validation, tool_directory=tool_directory
    )


def workflow_proxy(workflow_path: str, strict_cwl_validation: bool = True) -> WorkflowProxy:
    ensure_cwltool_available()
    return _to_cwl_workflow_object(workflow_path, strict_cwl_validation=strict_cwl_validation)


def load_job_proxy(job_directory: str, strict_cwl_validation: bool = True) -> JobProxy:
    ensure_cwltool_available()
    job_objects_path = os.path.join(job_directory, JOB_JSON_FILE)
    job_objects = json.load(open(job_objects_path))
    job_inputs = job_objects["job_inputs"]
    output_dict = job_objects["output_dict"]
    persisted_tool = job_objects["tool_representation"]
    cwl_tool = tool_proxy_from_persistent_representation(
        persisted_tool=persisted_tool, strict_cwl_validation=strict_cwl_validation
    )
    return cwl_tool.job_proxy(job_inputs, output_dict, job_directory=job_directory)


def _to_cwl_tool_object(
    tool_path: Optional[str] = None,
    tool_object=None,
    strict_cwl_validation: bool = False,
    tool_directory: Optional[str] = None,
    uuid: Optional[Union[UUID, str]] = None,
) -> ToolProxy:
    if uuid is None:
        uuid = str(uuid4())
    schema_loader = _schema_loader(strict_cwl_validation)
    if tool_path is not None:
        assert tool_object is None

        raw_process_reference = schema_loader.raw_process_reference(tool_path)
        cwl_tool = schema_loader.tool(
            raw_process_reference=raw_process_reference,
        )
    elif tool_object is not None:
        # Allow loading tools from YAML...
        as_str = json.dumps(tool_object)
        tool_object = yaml_no_ts().load(as_str)
        path = tool_directory
        if path is None:
            path = os.getcwd()
        uri = f"{ref_resolver.file_uri(path)}/"
        sourceline.add_lc_filename(tool_object, uri)
        raw_process_reference = schema_loader.raw_process_reference_for_object(tool_object, uri=uri)
        cwl_tool = schema_loader.tool(
            raw_process_reference=raw_process_reference,
        )
    else:
        raise ValueError("Either tool_path or tool_object should be defined")

    if isinstance(cwl_tool, int):
        raise Exception("Failed to load tool.")

    raw_tool = cwl_tool.tool
    # Apply Galaxy hacks to CWL tool representation to bridge semantic differences
    # between Galaxy and cwltool.
    _hack_cwl_requirements(cwl_tool)
    check_requirements(raw_tool)
    return _cwl_tool_object_to_proxy(cwl_tool, uuid, raw_process_reference=raw_process_reference, tool_path=tool_path)


def _cwl_tool_object_to_proxy(
    cwl_tool: process.Process,
    uuid: Union[UUID, str],
    raw_process_reference: Optional["RawProcessReference"] = None,
    tool_path: Optional[str] = None,
) -> ToolProxy:
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

    return proxy_class(cwl_tool, uuid, raw_process_reference, tool_path)


def _to_cwl_workflow_object(workflow_path: str, strict_cwl_validation: bool = True) -> WorkflowProxy:
    cwl_workflow = _schema_loader(strict_cwl_validation).tool(path=workflow_path)
    raw_workflow = cwl_workflow.tool
    check_requirements(raw_workflow, tool=False)
    return WorkflowProxy(cwl_workflow, workflow_path)


def _schema_loader(strict_cwl_validation: bool):
    return schema_loader if strict_cwl_validation else non_strict_non_validating_schema_loader


def _hack_cwl_requirements(cwl_tool):
    move_to_hints: List[int] = []
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
                    raise Exception(f"Unsupported requirement {r['class']}")
        for d in rec:
            check_requirements(rec[d], tool=tool)
    if isinstance(rec, list):
        for d in rec:
            check_requirements(d, tool=tool)


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
            expected_prefix = workflow_id + sep_on
            if not step_reference.startswith(expected_prefix):
                raise AssertionError(f"step_reference [{step_reference}] doesn't start with {expected_prefix}")
            step_reference = step_reference[len(expected_prefix) :]

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
        assert len(split_references) == 1, split_references
        return split_references[0]


def build_step_proxy(workflow_proxy: WorkflowProxy, step: "workflow.WorkflowStep", index: int):
    step_type = step.embedded_tool.tool["class"]
    if step_type == "Workflow":
        return SubworkflowStepProxy(workflow_proxy, step, index)
    else:
        return ToolStepProxy(workflow_proxy, step, index)


class InputProxy:
    def __init__(self, step_proxy, cwl_input):
        self._cwl_input = cwl_input
        self.step_proxy = step_proxy
        self.workflow_proxy = step_proxy._workflow_proxy

        cwl_input_id = cwl_input["id"]
        cwl_source_id = cwl_input.get("source", None)
        if cwl_source_id is None:
            if "valueFrom" not in cwl_input and "default" not in cwl_input:
                msg = f"Workflow step input must define a source, a valueFrom, or a default value. Obtained [{cwl_input}]."
                raise MessageException(msg)

        assert cwl_input_id
        step_name, input_name = split_step_references(
            cwl_input_id, multiple=False, workflow_id=step_proxy.cwl_workflow_id
        )
        self.step_name = step_name
        self.input_name = input_name

        self.cwl_input_id = cwl_input_id
        self.cwl_source_id = cwl_source_id

        scatter_inputs = [
            split_step_references(i, multiple=False, workflow_id=step_proxy.cwl_workflow_id)[1]
            for i in listify(step_proxy._step.tool.get("scatter", []))
        ]
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


class BaseStepProxy:
    def __init__(self, workflow_proxy: WorkflowProxy, step: "workflow.WorkflowStep", index: int):
        self._workflow_proxy = workflow_proxy
        self._step = step
        self._index = index
        self._uuid = str(uuid4())
        cwl_inputs = self._step.tool["inputs"]
        self.input_proxies = [InputProxy(self, cwl_input) for cwl_input in cwl_inputs]

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
        return self._workflow_proxy.get_outputs_for_label(self.label)

    @property
    def cwl_tool_object(self):
        return self._step.embedded_tool

    def inputs_to_dicts(self):
        inputs_as_dicts = []
        for input_proxy in self.input_proxies:
            inputs_as_dicts.append(input_proxy.to_dict())
        return inputs_as_dicts


class ToolStepProxy(BaseStepProxy):
    def __init__(self, workflow_proxy, step, index):
        super().__init__(workflow_proxy, step, index)
        self._tool_proxy = None

    @property
    def tool_proxy(self):
        # Needs to be cached so UUID that is loaded matches UUID generated with to_dict.
        if self._tool_proxy is None:
            self._tool_proxy = _cwl_tool_object_to_proxy(self.cwl_tool_object, uuid=str(uuid4()))
        return self._tool_proxy

    def tool_reference_proxies(self):
        # Return a list so we can handle subworkflows recursively.
        return [self.tool_proxy]

    def to_dict(self, input_connections):
        # We need to stub out null entries for things getting replaced by
        # connections. This doesn't seem ideal - consider just making Galaxy
        # handle this.
        tool_state: ToolStateType = {}
        for input_name in input_connections.keys():
            tool_state[input_name] = None

        outputs = self.galaxy_workflow_outputs_list()
        when_expression = self._step.tool.get("when")
        rval = {
            "id": self._index,
            "tool_uuid": self.tool_proxy.uuid,  # TODO: make sure this is respected...
            "label": self.label,
            "position": {"left": 0, "top": 0},
            "type": "tool",
            "annotation": self._workflow_proxy.cwl_object_to_annotation(self._step.tool),
            "input_connections": input_connections,
            "inputs": self.inputs_to_dicts(),
            "workflow_outputs": outputs,
        }
        if when_expression:
            rval["when"] = when_expression
        return rval


class SubworkflowStepProxy(BaseStepProxy):
    def __init__(self, workflow_proxy, step, index):
        super().__init__(workflow_proxy, step, index)
        self._subworkflow_proxy = None

    def to_dict(self, input_connections):
        outputs = self.galaxy_workflow_outputs_list()
        for key, input_connection_list in input_connections.items():
            input_subworkflow_step_id = self.subworkflow_proxy.find_inputs_step_index(key)
            for input_connection in input_connection_list:
                input_connection["input_subworkflow_step_id"] = input_subworkflow_step_id

        return {
            "id": self._index,
            "label": self.label,
            "position": {"left": 0, "top": 0},
            "type": "subworkflow",
            "subworkflow": self.subworkflow_proxy.to_dict(),
            "annotation": self.subworkflow_proxy.cwl_object_to_annotation(self._step.tool),
            "input_connections": input_connections,
            "inputs": self.inputs_to_dicts(),
            "workflow_outputs": outputs,
        }

    def tool_reference_proxies(self):
        return self.subworkflow_proxy.tool_reference_proxies()

    @property
    def subworkflow_proxy(self):
        if self._subworkflow_proxy is None:
            self._subworkflow_proxy = WorkflowProxy(self.cwl_tool_object)
        return self._subworkflow_proxy


def _outer_field_to_input_instance(field):
    field_type = field_to_field_type(field)  # Must be a list if in here?
    if not isinstance(field_type, list):
        field_type = [field_type]

    name, label, description = _field_metadata(field)

    case_name = "_cwl__type_"
    case_label = f"Specify Parameter {label} As"

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
        if type_description.uses_param:
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
            name,
            label,
            description,
            input_type=only_type_description.galaxy_param_type,
            collection_type=only_type_description.collection_type,
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
    output_instance = OutputInstance(name, output_data_type=output_data_class, output_type=OUTPUT_TYPE.GLOB)
    return output_instance


class ConditionalInstance:
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
            when={},
        )
        for value, block in self.whens:
            as_dict["when"][value] = [i.to_dict() for i in block]

        return as_dict


class SelectInputInstance:
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


class InputInstance:
    def __init__(self, name, label, description, input_type, array=False, area=False, collection_type=None):
        self.input_type = input_type
        self.collection_type = collection_type
        self.name = name
        self.label = label
        self.description = description
        self.required = True
        self.array = array
        self.area = area

    @overload
    def to_dict(self, itemwise: Literal[False]) -> InputInstanceDict: ...

    @overload
    def to_dict(self, itemwise: Literal[True]) -> Union[InputInstanceDict, InputInstanceArrayDict]: ...

    def to_dict(self, itemwise: bool = True) -> Union[InputInstanceDict, InputInstanceArrayDict]:
        if itemwise and self.array:
            return InputInstanceArrayDict(
                type="repeat", name=f"{self.name}_repeat", title=f"{self.name}", blocks=[self.to_dict(itemwise=False)]
            )
        else:
            as_dict = InputInstanceDict(
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
            elif self.input_type == INPUT_TYPE.DATA_COLLECTION:
                as_dict["collection_type"] = self.collection_type
            return as_dict


OUTPUT_TYPE = Bunch(
    GLOB="glob",
    STDOUT="stdout",
)


# TODO: Different subclasses - this is representing different types of things.
class OutputInstance:
    def __init__(self, name: str, output_data_type, output_type, path=None, fields=None):
        self.name = name
        self.output_data_type = output_data_type
        self.output_type = output_type
        self.path = path
        self.fields = fields


__all__ = (
    "tool_proxy",
    "load_job_proxy",
)
