"""Define the ParsedTool model representing metadata extracted from a tool's source.

This is abstraction exported by newer tool shed APIS (circa 2024) and should be sufficient
for reasoning about tool state externally from Galaxy.
"""

from typing import (
    List,
    Optional,
)

from pydantic import BaseModel

from .parameters import (
    input_models_for_tool_source,
    ToolParameterT,
)
from .parser.interface import (
    Citation,
    HelpContent,
    ToolSource,
    XrefDict,
)
from .parser.output_models import (
    from_tool_source,
    ToolOutput,
)


class ParsedTool(BaseModel):
    id: str
    version: Optional[str]
    name: str
    description: Optional[str]
    inputs: List[ToolParameterT]
    outputs: List[ToolOutput]
    citations: List[Citation]
    license: Optional[str]
    profile: Optional[str]
    edam_operations: List[str]
    edam_topics: List[str]
    xrefs: List[XrefDict]
    help: Optional[HelpContent]


def parse_tool(tool_source: ToolSource) -> ParsedTool:
    id = tool_source.parse_id()
    version = tool_source.parse_version()
    name = tool_source.parse_name()
    description = tool_source.parse_description()
    inputs = input_models_for_tool_source(tool_source).input_models
    outputs = from_tool_source(tool_source)
    citations = tool_source.parse_citations()
    license = tool_source.parse_license()
    profile = tool_source.parse_profile()
    edam_operations = tool_source.parse_edam_operations()
    edam_topics = tool_source.parse_edam_topics()
    xrefs = tool_source.parse_xrefs()
    help = tool_source.parse_help()

    return ParsedTool(
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
