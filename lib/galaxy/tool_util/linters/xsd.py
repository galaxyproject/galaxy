import os.path
from typing import TYPE_CHECKING

from galaxy import tool_util
from galaxy.tool_util.lint import Linter
from galaxy.util import etree

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser import ToolSource

TOOL_XSD = os.path.join(os.path.dirname(tool_util.__file__), "xsd", "galaxy.xsd")


class XSD(Linter):
    """
    Lint an XML tool against XSD
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        xmlschema = etree.parse(TOOL_XSD)
        xsd = etree.XMLSchema(xmlschema)
        if not xsd.validate(tool_xml):
            for error in xsd.error_log:  # type: ignore[attr-defined] # https://github.com/lxml/lxml-stubs/pull/100
                # the validation error contains the path which allows
                # us to lookup the node that is reported in the lint context
                node = tool_xml.xpath(error.path)
                node = node[0]
                lint_ctx.error(f"Invalid XML: {error.message}", linter=cls.name(), node=node)
