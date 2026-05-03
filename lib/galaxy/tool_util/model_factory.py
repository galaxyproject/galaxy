import math
from typing import (
    Any,
    List,
    Type,
    TypeVar,
)

from galaxy.tool_util_models import ParsedTool
from galaxy.tool_util_models.tool_source import (
    Container,
    PackageRequirement,
    ResourceRequirement,
    SetEnvironmentRequirement,
    Stdio,
    StdioExitCode,
    StdioRegex,
)
from .parameters import input_models_for_tool_source
from .parser.interface import (
    ToolSource,
)
from .parser.output_objects import from_tool_source


def parse_tool(tool_source: ToolSource) -> ParsedTool:
    return parse_tool_custom(tool_source, ParsedTool)


P = TypeVar("P", bound=ParsedTool)


def parse_tool_custom(tool_source: ToolSource, model_type: Type[P]) -> P:
    id = tool_source.parse_id()
    version = tool_source.parse_version()
    name = tool_source.parse_name()
    description = tool_source.parse_description()
    inputs = input_models_for_tool_source(tool_source).parameters
    outputs = from_tool_source(tool_source)
    citations = tool_source.parse_citations()
    license = tool_source.parse_license()
    profile = tool_source.parse_profile()
    edam_operations = tool_source.parse_edam_operations()
    edam_topics = tool_source.parse_edam_topics()
    xrefs = tool_source.parse_xrefs()
    help = tool_source.parse_help()
    tool_requirements, container_descriptions, resource_requirements, javascript_requirements, _ = (
        tool_source.parse_requirements()
    )
    requirements = _parsed_requirements(tool_requirements, resource_requirements, javascript_requirements)
    containers = [Container(type=c.type, container_id=c.identifier) for c in container_descriptions]
    stdio = _parsed_stdio(tool_source)

    return model_type(
        id=id,
        version=version,
        name=name,
        description=description,
        requirements=requirements,
        containers=containers,
        stdio=stdio,
        profile=profile,
        inputs=inputs,
        outputs=outputs,
        license=license,
        citations=citations,
        edam_operations=edam_operations,
        edam_topics=edam_topics,
        xrefs=xrefs,
        help=help,
    )


def _parsed_requirements(tool_requirements, resource_requirements, javascript_requirements) -> List[Any]:
    parsed_requirements: List[Any] = []
    for requirement in tool_requirements:
        if requirement.type == "package":
            parsed_requirements.append(
                PackageRequirement(type="package", name=requirement.name, version=requirement.version)
            )
        elif requirement.type == "set_environment":
            parsed_requirements.append(SetEnvironmentRequirement(type="set_environment", environment=requirement.name))

    resource_requirement_kwds = {r.resource_type: r.value_or_expression for r in resource_requirements}
    if resource_requirement_kwds:
        resource_requirement = {"cores_min": None, "ram_min": None, **resource_requirement_kwds}
        parsed_requirements.append(ResourceRequirement(type="resource", **resource_requirement))

    parsed_requirements.extend(javascript_requirements)
    return parsed_requirements


def _parsed_stdio(tool_source: ToolSource) -> Stdio:
    exit_codes, regexes = tool_source.parse_stdio()
    return Stdio(
        exit_codes=[
            StdioExitCode(
                range_start=_stdio_range_value(exit_code.range_start),
                range_end=_stdio_range_value(exit_code.range_end),
                error_level=exit_code.error_level,
                desc=exit_code.desc,
            )
            for exit_code in exit_codes
        ],
        regexes=[
            StdioRegex(
                match=regex.match,
                stdout_match=regex.stdout_match,
                stderr_match=regex.stderr_match,
                error_level=regex.error_level,
                desc=regex.desc,
            )
            for regex in regexes
        ],
    )


def _stdio_range_value(value):
    if isinstance(value, float) and math.isinf(value):
        return "-inf" if value < 0 else "inf"
    return value
