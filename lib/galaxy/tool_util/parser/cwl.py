import json
import logging
import math
from typing import (
    Any,
    Dict,
    Optional,
    TYPE_CHECKING,
    Union,
)
from uuid import UUID

import packaging.version

from galaxy.tool_util.cwl.parser import (
    tool_proxy,
    tool_proxy_from_persistent_representation,
)
from galaxy.tool_util.deps import requirements
from galaxy.tool_util_models.tool_source import HelpContent
from .interface import (
    PageSource,
    PagesSource,
    ToolSource,
)
from .output_actions import (
    ToolOutputActionApp,
    ToolOutputActionGroup,
)
from .output_collection_def import dataset_collector_descriptions_from_list
from .output_objects import (
    ToolOutput,
    ToolOutputCollection,
    ToolOutputCollectionStructure,
)
from .stdio import (
    StdioErrorLevel,
    ToolStdioExitCode,
)
from .yaml import YamlInputSource

if TYPE_CHECKING:
    from galaxy.tool_util.cwl.parser import (
        OutputInstance,
        ToolProxy,
    )

CWL_DEFAULT_FILE_OUTPUT = "data"  # set to _sniff_ to sniff output types automatically.

log = logging.getLogger(__name__)


class CwlToolSource(ToolSource):
    language = "yaml"

    def __init__(
        self,
        tool_file: Optional[str] = None,
        tool_object: Optional[Dict[str, Any]] = None,
        strict_cwl_validation: bool = True,
        tool_directory: Optional[str] = None,
        uuid: Optional[Union[UUID, str]] = None,
        tool_proxy: Optional["ToolProxy"] = None,
    ):
        self._source_path = tool_file
        self._source_object = tool_object
        self._strict_cwl_validation = strict_cwl_validation
        self._tool_directory = tool_directory
        self._uuid = uuid
        self._tool_proxy = tool_proxy

    @property
    def source_path(self):
        return self._source_path

    @property
    def tool_proxy(self) -> "ToolProxy":
        if self._tool_proxy is None:
            if self._source_path is not None:
                self._tool_proxy = tool_proxy(
                    self._source_path,
                    strict_cwl_validation=self._strict_cwl_validation,
                    tool_directory=self._tool_directory,
                    uuid=self._uuid,
                )
            else:
                assert self._source_object
                assert "uuid" in self._source_object
                self._tool_proxy = tool_proxy_from_persistent_representation(
                    self._source_object,
                    strict_cwl_validation=self._strict_cwl_validation,
                    tool_directory=self._tool_directory,
                )
        return self._tool_proxy

    def parse_tool_type(self):
        return "cwl"

    def parse_id(self):
        return self.tool_proxy.galaxy_id()

    def parse_name(self):
        return self.tool_proxy.label() or self.parse_id()

    def parse_command(self):
        return "$__cwl_command"

    def parse_environment_variables(self):
        environment_variables = []
        # TODO: Is this even possible from here, should instead this be moved
        # into the job.

        # for environment_variable_el in environment_variables_el.findall("environment_variable"):
        #    definition = {
        #        "name": environment_variable_el.get("name"),
        #        "template": environment_variable_el.text,
        #    }
        #    environment_variables.append(
        #        definition
        #    )

        return environment_variables

    def parse_edam_operations(self):
        return []

    def parse_edam_topics(self):
        return []

    def parse_help(self):
        doc = self.tool_proxy.doc()
        if doc:
            return HelpContent(format="plain_text", content=doc)
        else:
            return None

    def parse_sanitize(self):
        return False

    def parse_strict_shell(self):
        return True

    def parse_stdio(self):
        # TODO: remove duplication with YAML
        exit_codes = []

        success_codes = sorted(set(self.tool_proxy._tool.tool.get("successCodes") or [0]))

        last_success_code = None

        for success_code in success_codes:
            if last_success_code is not None and success_code == last_success_code + 1:
                last_success_code = success_code
                continue

            exit_code = ToolStdioExitCode()
            range_start = -math.inf
            if last_success_code is not None:
                range_start = last_success_code + 1

            exit_code.range_start = range_start
            exit_code.range_end = success_code - 1
            exit_code.error_level = StdioErrorLevel.FATAL
            exit_codes.append(exit_code)

            last_success_code = success_code

        exit_code = ToolStdioExitCode()
        exit_code.range_start = last_success_code + 1
        exit_code.range_end = math.inf
        exit_code.error_level = StdioErrorLevel.FATAL
        exit_codes.append(exit_code)

        return exit_codes, []

    def parse_interpreter(self):
        return None

    def parse_version(self):
        return "0.0.1"

    def parse_description(self):
        return self.tool_proxy.description()

    def parse_icon(self) -> Optional[str]:
        return None  # Not implemented

    def parse_interactivetool(self):
        return []

    def parse_input_pages(self) -> PagesSource:
        page_source = CwlPageSource(self.tool_proxy)
        return PagesSource([page_source])

    def parse_outputs(self, app: Optional[ToolOutputActionApp]):
        output_instances = self.tool_proxy.output_instances()
        outputs = {}
        output_collections = {}
        output_defs = []
        for output_instance in output_instances:
            output_defs.append(self._parse_output(app, output_instance))
        # TODO: parse outputs collections
        for output_def in output_defs:
            if isinstance(output_def, ToolOutput):
                outputs[output_def.name] = output_def
            else:
                outputs[output_def.name] = output_def
                output_collections[output_def.name] = output_def
        return outputs, output_collections

    def _parse_output(self, app: Optional[ToolOutputActionApp], output_instance: "OutputInstance"):
        output_type = output_instance.output_data_type
        if isinstance(output_type, dict) and output_type.get("type") == "record":
            return self._parse_output_record(output_instance)
        elif isinstance(output_type, dict) and output_type.get("type") == "array":
            return self._parse_output_array(output_instance)
        else:
            return self._parse_output_data(app, output_instance)

    def _parse_output_data(self, app: Optional[ToolOutputActionApp], output_instance: "OutputInstance"):
        name = output_instance.name
        # TODO: handle filters, actions, change_format
        output = ToolOutput(name)
        if "File" in output_instance.output_data_type:
            output.format = CWL_DEFAULT_FILE_OUTPUT
        elif "Directory" in output_instance.output_data_type:
            output.format = "directory"
        else:
            output.format = "expression.json"
        output.change_format = []
        output.format_source = None
        output.metadata_source = None
        output.parent = None
        output.label = None
        output.count = None
        output.filters = []
        output.hidden = False
        output.dataset_collector_descriptions = []
        if app is not None:
            output.actions = ToolOutputActionGroup(app, None)
        return output

    def _parse_output_record(self, output_instance: "OutputInstance"):
        name = output_instance.name
        # TODO: clean output bindings and other non-structure information
        # from this.
        fields = output_instance.output_data_type.get("fields")
        output_collection = ToolOutputCollection(
            name,
            ToolOutputCollectionStructure(
                collection_type="record",
                fields=fields,
            ),
        )
        return output_collection

    def _parse_output_array(self, output_instance: "OutputInstance"):
        name = output_instance.name
        # TODO: Handle nested arrays and such...
        dataset_collector_descriptions = dataset_collector_descriptions_from_list(
            [{"from_provided_metadata": True}],
        )
        output_collection = ToolOutputCollection(
            name,
            ToolOutputCollectionStructure(
                collection_type="list",
                dataset_collector_descriptions=dataset_collector_descriptions,
            ),
        )
        return output_collection

    def parse_requirements(self):
        containers = []
        docker_identifier = self.tool_proxy.docker_identifier()
        if docker_identifier:
            containers.append({"type": "docker", "identifier": docker_identifier})

        software_requirements = self.tool_proxy.software_requirements()
        resource_requirements = self.tool_proxy.resource_requirements()
        credentials = self.tool_proxy.credentials_requirements()
        return requirements.parse_requirements_from_lists(
            software_requirements=[{"name": r[0], "version": r[1], "type": "package"} for r in software_requirements],
            containers=containers,
            resource_requirements=resource_requirements,
            javascript_requirements=[],  # TODO, implement in tool proxy?
            credentials=credentials,
        )

    def parse_profile(self):
        return "17.09"

    def parse_xrefs(self):
        return []

    def parse_provided_metadata_style(self):
        return "default"

    def parse_cores_min(self):
        for h in self.tool_proxy.hints_or_requirements_of_class("ResourceRequirement"):
            cores_min = h.get("coresMin")
            if cores_min:
                return cores_min
        return 1

    def parse_license(self):
        return None

    def parse_python_template_version(self):
        return packaging.version.Version("3.5")

    def to_string(self):
        return json.dumps(self.tool_proxy.to_persistent_representation())


class CwlInputSource(YamlInputSource):
    def __init__(self, as_dict, as_field):
        super().__init__(as_dict)
        self._field = as_field

    @property
    def field(self):
        return self._field


class CwlPageSource(PageSource):
    def __init__(self, tool_proxy):
        cwl_instances = tool_proxy.input_instances()
        input_fields = tool_proxy.input_fields()
        input_list = []
        for cwl_instance in cwl_instances:
            name = cwl_instance.name
            input_field = None
            for field in input_fields:
                if field["name"] == name:
                    input_field = field
            input_list.append(CwlInputSource(cwl_instance.to_dict(), input_field))

        self._input_list = input_list

    def _to_input_source(self, input_instance):
        as_dict = input_instance.to_dict()
        return CwlInputSource(as_dict)

    def parse_input_sources(self):
        return self._input_list

    def input_fields(self):
        return self._input_fields


__all__ = (
    "CwlToolSource",
    "tool_proxy",
)
