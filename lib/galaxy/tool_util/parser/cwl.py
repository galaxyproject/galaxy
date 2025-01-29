import json
import logging
import math
from typing import (
    Optional,
    TYPE_CHECKING,
)

import packaging.version

from galaxy.tool_util.cwl.parser import tool_proxy
from galaxy.tool_util.deps import requirements
from .interface import (
    HelpContent,
    PageSource,
    PagesSource,
    ToolSource,
)
from .output_actions import ToolOutputActionGroup
from .output_objects import ToolOutput
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
    from galaxy.tools import Tool

log = logging.getLogger(__name__)


class CwlToolSource(ToolSource):
    language = "yaml"

    def __init__(
        self,
        tool_file: Optional[str] = None,
        strict_cwl_validation: bool = True,
        tool_proxy: Optional["ToolProxy"] = None,
    ):
        self._tool_proxy = tool_proxy
        self._source_path = tool_file
        self._strict_cwl_validation = strict_cwl_validation

    @property
    def source_path(self):
        return self._source_path

    @property
    def tool_proxy(self) -> "ToolProxy":
        if self._tool_proxy is None:
            self._tool_proxy = tool_proxy(self._source_path, strict_cwl_validation=self._strict_cwl_validation)
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
        # New format - starting out just using exit code.
        exit_code_lower = ToolStdioExitCode()
        exit_code_lower.range_start = -math.inf
        exit_code_lower.range_end = -1
        exit_code_lower.error_level = StdioErrorLevel.FATAL
        exit_code_high = ToolStdioExitCode()
        exit_code_high.range_start = 1
        exit_code_high.range_end = math.inf
        exit_code_lower.error_level = StdioErrorLevel.FATAL
        return [exit_code_lower, exit_code_high], []

    def parse_interpreter(self):
        return None

    def parse_version(self):
        return "0.0.1"

    def parse_description(self):
        return self.tool_proxy.description()

    def parse_interactivetool(self):
        return []

    def parse_input_pages(self) -> PagesSource:
        page_source = CwlPageSource(self.tool_proxy)
        return PagesSource([page_source])

    def parse_outputs(self, tool):
        output_instances = self.tool_proxy.output_instances()
        outputs = {}
        output_defs = []
        for output_instance in output_instances:
            output_defs.append(self._parse_output(tool, output_instance))
        # TODO: parse outputs collections
        for output_def in output_defs:
            outputs[output_def.name] = output_def
        return outputs, {}

    def _parse_output(self, tool: Optional["Tool"], output_instance: "OutputInstance"):
        name = output_instance.name
        # TODO: handle filters, actions, change_format
        output = ToolOutput(name)
        if "File" in output_instance.output_data_type:
            output.format = "_sniff_"
        else:
            output.format = "expression.json"
        output.change_format = []
        output.format_source = None
        output.metadata_source = ""
        output.parent = None
        output.label = None
        output.count = None
        output.filters = []
        output.tool = tool
        output.hidden = False
        output.dataset_collector_descriptions = []
        output.actions = ToolOutputActionGroup(output, None)
        return output

    def parse_requirements_and_containers(self):
        containers = []
        docker_identifier = self.tool_proxy.docker_identifier()
        if docker_identifier:
            containers.append({"type": "docker", "identifier": docker_identifier})

        software_requirements = self.tool_proxy.software_requirements()
        resource_requirements = self.tool_proxy.resource_requirements()
        return requirements.parse_requirements_from_lists(
            software_requirements=[{"name": r[0], "version": r[1], "type": "package"} for r in software_requirements],
            containers=containers,
            resource_requirements=resource_requirements,
        )

    def parse_profile(self):
        return "17.09"

    def parse_xrefs(self):
        return []

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
