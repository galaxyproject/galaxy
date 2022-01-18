import re


def node_props(node, tool_xml):
    if node is None:
        return {"line": 0, "fname": None, "xpath": None}
    else:
        return {"line": node.sourceline,
                "fname": node.base,
                "xpath": tool_xml.getpath(node)}


def is_datasource(tool_xml):
    """Returns true if the tool is a datasource tool"""
    return tool_xml.getroot().attrib.get('tool_type', '') == 'data_source'


def is_valid_cheetah_placeholder(name):
    """Returns true if name is a valid Cheetah placeholder"""
    return not re.match(r"^[a-zA-Z_]\w*$", name) is None
