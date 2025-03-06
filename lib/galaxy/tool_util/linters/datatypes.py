import os.path
from typing import (
    Set,
    TYPE_CHECKING,
    Union,
)

# from galaxy import config
from galaxy.tool_util.lint import Linter
from galaxy.util import (
    listify,
    parse_xml,
)
from galaxy.util.resources import resource_path

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser import ToolSource
    from galaxy.util.resources import Traversable

DATATYPES_CONF = resource_path(__package__, "datatypes_conf.xml.sample")


def _parse_datatypes(datatype_conf_path: Union[str, "Traversable"]) -> Set[str]:
    datatypes = set()
    tree = parse_xml(datatype_conf_path)
    root = tree.getroot()
    for elem in root.findall("./registration/datatype"):
        extension = elem.get("extension", "")
        datatypes.add(extension)
        auto_compressed_types = listify(elem.get("auto_compressed_types", ""))
        for act in auto_compressed_types:
            datatypes.add(f"{extension}.{act}")
    return datatypes


class DatatypesCustomConf(Linter):
    """
    Check if a custom datatypes_conf.xml is present
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        if not tool_source.source_path:
            return
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tool_node = tool_xml.getroot()
        tool_dir = os.path.dirname(tool_source.source_path)
        datatypes_conf_path = os.path.join(tool_dir, "datatypes_conf.xml")
        if os.path.exists(datatypes_conf_path):
            lint_ctx.warn(
                "Tool uses a custom datatypes_conf.xml which is discouraged",
                linter=cls.name(),
                node=tool_node,
            )


class ValidDatatypes(Linter):
    """
    Check that used datatypes are available
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        # get Galaxy built-in dataypes
        datatypes = _parse_datatypes(DATATYPES_CONF)
        # add custom tool data types
        if tool_source.source_path:
            tool_dir = os.path.dirname(tool_source.source_path)
            datatypes_conf_path = os.path.join(tool_dir, "datatypes_conf.xml")
            if os.path.exists(datatypes_conf_path):
                datatypes |= _parse_datatypes(datatypes_conf_path)
        for attrib in ["format", "ftype", "ext"]:
            for elem in tool_xml.findall(f".//*[@{attrib}]"):
                formats = elem.get(attrib, "").split(",")
                # Certain elements (e.g. `data`) can only have one format. This
                # is checked separately by linting against the XSD.
                if "auto" in formats:
                    if elem.tag == "param":
                        lint_ctx.error(
                            "Format [auto] can not be used for tool or tool test inputs",
                            linter=cls.name(),
                            node=elem,
                        )
                    continue
                for format in formats:
                    if format not in datatypes:
                        lint_ctx.error(
                            f"Unknown datatype [{format}] used in {elem.tag} element",
                            linter=cls.name(),
                            node=elem,
                        )
