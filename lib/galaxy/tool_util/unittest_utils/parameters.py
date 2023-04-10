import os
from typing import List

from galaxy.tool_util.parameters import (
    from_input_source,
    ToolParameterBundle,
    ToolParameterT,
)
from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.util import galaxy_directory


class ParameterBundle(ToolParameterBundle):
    input_models: List[ToolParameterT]

    def __init__(self, parameter: ToolParameterT):
        self.input_models = [parameter]


def parameter_bundle(parameter: ToolParameterT) -> ParameterBundle:
    return ParameterBundle(parameter)


def parameter_bundle_for_file(filename: str) -> ParameterBundle:
    return parameter_bundle(tool_parameter(filename))


def tool_parameter(filename: str) -> ToolParameterT:
    return from_input_source(parameter_source(filename))


def parameter_source(filename: str):
    tool_source = parameter_tool_source(filename)
    input_sources = tool_source.parse_input_pages().page_sources[0].parse_input_sources()
    assert len(input_sources) == 1
    return input_sources[0]


def parameter_tool_source(basename: str):
    path_prefix = os.path.join(galaxy_directory(), "test/functional/tools/parameters", basename)
    if os.path.exists(f"{path_prefix}.xml"):
        path = f"{path_prefix}.xml"
    else:
        path = f"{path_prefix}.cwl"
    tool_source = get_tool_source(path, macro_paths=[])
    return tool_source
