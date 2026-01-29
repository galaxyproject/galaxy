from typing import (
    Type,
    TypeVar,
)

from galaxy.tool_util_models import ParsedTool
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

    return model_type(
        id=id,
        version=version,
        name=name,
        description=description,
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
