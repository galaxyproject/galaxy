import re


def is_datasource(tool_xml):
    """Returns true if the tool is a datasource tool"""
    return tool_xml.getroot().attrib.get("tool_type", "") == "data_source"


def is_valid_cheetah_placeholder(name):
    """Returns true if name is a valid Cheetah placeholder"""
    return not re.match(r"^[a-zA-Z_]\w*$", name) is None
