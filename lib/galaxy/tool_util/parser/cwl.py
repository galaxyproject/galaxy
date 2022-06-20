import logging
import math
import os

from galaxy.tool_util.cwl.parser import tool_proxy
from galaxy.tool_util.deps import requirements
from .interface import (
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

log = logging.getLogger(__name__)


class CwlToolSource(ToolSource):

    language = "yaml"

    def __init__(self, tool_file, strict_cwl_validation=True, tool_id=None, tool_proxy=None):
        self._cwl_tool_file = tool_file
        self._id = tool_id or os.path.splitext(os.path.basename(tool_file))[0]
        self._tool_proxy = tool_proxy
        self._source_path = tool_file
        self._strict_cwl_validation = strict_cwl_validation

    @property
    def source_path(self):
        return self._source_path

    @property
    def tool_proxy(self):
        if self._tool_proxy is None:
            self._tool_proxy = tool_proxy(self._source_path, strict_cwl_validation=self._strict_cwl_validation)
        return self._tool_proxy

    def parse_tool_type(self):
        return "cwl"

    def parse_id(self):
        return self._id

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
        return self.tool_proxy.doc()

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

    def parse_input_pages(self):
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

    def _parse_output(self, tool, output_instance):
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
        output.hidden = ""
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
        return requirements.parse_requirements_from_dict(
            dict(
                requirements=list(
                    map(lambda r: {"name": r[0], "version": r[1], "type": "package"}, software_requirements)
                ),
                containers=containers,
                resource_requirements=resource_requirements,
            )
        )

    def parse_profile(self):
        return "16.04"

    def parse_license(self):
        return None

    def parse_python_template_version(self):
        return "3.5"


class CwlPageSource(PageSource):
    def __init__(self, tool_proxy):
        cwl_instances = tool_proxy.input_instances()
        self._input_list = list(map(self._to_input_source, cwl_instances))

    def _to_input_source(self, input_instance):
        as_dict = input_instance.to_dict()
        return YamlInputSource(as_dict)

    def parse_input_sources(self):
        return self._input_list


__all__ = (
    "CwlToolSource",
    "tool_proxy",
)
