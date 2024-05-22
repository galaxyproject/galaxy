"""This module contains a linter for tool XML block order.

For more information on the IUC standard for XML block order see -
https://github.com/galaxy-iuc/standards.
"""

from typing import (
    Optional,
    TYPE_CHECKING,
)

from galaxy.tool_util.lint import Linter
from ._util import is_datasource

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser.interface import ToolSource

# https://github.com/galaxy-iuc/standards
# https://github.com/galaxy-iuc/standards/pull/7/files
TAG_ORDER = [
    "description",
    "macros",
    "options",
    "edam_topics",
    "edam_operations",
    "xrefs",
    "parallelism",
    "requirements",
    "required_files",
    "code",
    "stdio",
    "version_command",
    "command",
    "environment_variables",
    "configfiles",
    "inputs",
    "outputs",
    "tests",
    "help",
    "citations",
]

DATASOURCE_TAG_ORDER = [
    "description",
    "macros",
    "requirements",
    "command",
    "configfiles",
    "inputs",
    "request_param_translation",
    "uihints",
    "outputs",
    "options",
    "help",
    "citations",
]


class XMLOrder(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tool_root = tool_xml.getroot()

        if is_datasource(tool_xml):
            tag_ordering = DATASOURCE_TAG_ORDER
        else:
            tag_ordering = TAG_ORDER
        last_tag = None
        last_key: Optional[int] = None
        for elem in tool_root:
            tag = elem.tag
            if tag not in tag_ordering:
                continue
            key = tag_ordering.index(tag)
            if last_key:
                if last_key > key:
                    lint_ctx.warn(
                        f"Best practice violation [{tag}] elements should come before [{last_tag}]",
                        linter=cls.name(),
                        node=elem,
                    )
            last_tag = tag
            last_key = key
