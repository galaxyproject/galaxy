from galaxy.util.xml_macros import (
    imported_macro_paths,
    load,
    load_with_references,
    raw_xml_tree,
    template_macro_params,
)

load_tool = load
load_tool_with_refereces = load_with_references
raw_tool_xml_tree = raw_xml_tree

__all__ = (
    "imported_macro_paths",
    "load_tool",
    "load_tool_with_refereces",
    "raw_tool_xml_tree",
    "template_macro_params",
)
