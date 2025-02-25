import re

from Cheetah.Compiler import Compiler
from Cheetah.Template import Template

from galaxy.util import unicodify


def get_code(tool_xml):
    """get code used in the Galaxy tool"""
    # get code from command and configfiles
    code = ""
    for tag in [".//command", ".//configfile"]:
        for cn in tool_xml.findall(tag):
            code += cn.text
    # TODO not sure about this line, I get UnicodeError for some tools otherwise (trinity)
    code = "#encoding utf-8\n" + code
    code = Template.compile(source=code, compilerClass=Compiler, returnAClass=False)
    code = unicodify(code)
    # print(code)

    # template macros
    # note: not necessary (& possible) for macro tokens which are expanded
    # during loading the xml (and removed from the macros tag)
    templatecode = ""
    for cn in tool_xml.findall('.//macros/macro[@type="template"]'):
        templatecode += cn.text
    templatecode = "#encoding utf-8\n" + templatecode
    templatecode = Template.compile(source=templatecode, compilerClass=Compiler, returnAClass=False)
    templatecode = unicodify(templatecode)

    # get code from output filters (which use variables wo $)
    filtercode = ""
    for cn in tool_xml.findall("./outputs/*/filter"):
        filtercode += cn.text + "\n"

    # get output labels which might contain code (which use variables like ${var})
    labelcode = ""
    for cn in tool_xml.findall("./outputs/*[@label]"):
        labelcode += cn.attrib["label"] + "\n"

    actioncode = ""
    for cn in tool_xml.findall("./outputs//conditional[@name]"):
        actioncode += cn.attrib["name"] + "\n"
    for cn in tool_xml.findall('./outputs//action/option[@type="from_param"]'):
        actioncode += cn.attrib.get("name", "") + "\n"
    for cn in tool_xml.findall("./outputs//action/option/filter[@ref]"):
        actioncode += cn.attrib["ref"] + "\n"
    for cn in tool_xml.findall("./outputs//action[@default]"):
        actioncode += cn.attrib["default"] + "\n"

    return code, templatecode, filtercode, labelcode, actioncode


def is_datasource(tool_xml):
    """Returns true if the tool is a datasource tool"""
    return tool_xml.getroot().attrib.get("tool_type", "") in ["data_source", "data_source_async"]


def is_valid_cheetah_placeholder(name):
    """Returns true if name is a valid Cheetah placeholder"""
    return re.match(r"^[a-zA-Z_]\w*$", name) is not None
