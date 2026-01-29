import os

from galaxy.tool_util.parameters import (
    input_models_for_tool_source,
    ToolParameterBundle,
    ToolParameterBundleModel,
    ToolParameterT,
)
from galaxy.tool_util.parser import (
    get_tool_source,
    ToolSource,
)
from galaxy.util import galaxy_directory
from . import functional_test_tool_path


class ParameterBundle(ToolParameterBundle):

    def __init__(self, parameter: ToolParameterT):
        self.parameters = [parameter]


def parameter_bundle(parameter: ToolParameterT) -> ParameterBundle:
    return ParameterBundle(parameter)


def parameter_bundle_for_framework_tool(filename: str) -> ToolParameterBundleModel:
    path = functional_test_tool_path(filename)
    tool_source = get_tool_source(path, macro_paths=[])
    return input_models_for_tool_source(tool_source)


def parameter_bundle_for_file(filename: str) -> ToolParameterBundleModel:
    tool_source = parameter_tool_source(filename)
    return input_models_for_tool_source(tool_source)


def parameter_tool_source(basename: str) -> ToolSource:
    path_prefix = os.path.join(galaxy_directory(), "test/functional/tools/parameters", basename)
    if os.path.exists(f"{path_prefix}.xml"):
        path = f"{path_prefix}.xml"
    else:
        path = f"{path_prefix}.cwl"
    tool_source = get_tool_source(path, macro_paths=[])
    return tool_source
