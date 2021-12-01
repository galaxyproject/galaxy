"""This module contains a linting functions checking for TODO in attributes and text"""

import re


def _has_todo(txt):
    """
    check if text contains a TODO
    the todo needs to be delimited by a non-alphanumerical character (whitespaces, #, ...)
    or be at the begin/end of txt
    """
    return re.search(r"(^|\W)(todo|TODO)(\W|$)", txt) is not None


def lint_todo(tool_xml, lint_ctx):
    """
    check if any attribute / text contains a TODO
    """
    for el in tool_xml.iter():
        for a in el.attrib:
            if _has_todo(el.attrib[a]):
                lint_ctx.warn(f'{el.tag} attribute "{a}" contains a "TODO"')
        if _has_todo(el.text):
            lint_ctx.warn(f'{el.tag} text contains a "TODO"')
