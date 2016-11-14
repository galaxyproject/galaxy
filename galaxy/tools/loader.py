from galaxy.util.xml_macros import (
    imported_macro_paths,
    load,
    raw_tool_xml_tree,
    template_macro_params,
)

load_tool = load

__all__ = ("load_tool", "raw_tool_xml_tree", "imported_macro_paths", "template_macro_params")
