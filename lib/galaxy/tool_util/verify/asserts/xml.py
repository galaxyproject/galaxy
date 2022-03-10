import re
from typing import Optional

from lxml.etree import XMLSyntaxError

from galaxy.tool_util.verify import asserts
from galaxy.util import (
    asbool,
    parse_xml_string,
    unicodify,
)


def assert_is_valid_xml(output):
    """Simple assertion that just verifies the specified output
    is valid XML."""
    try:
        parse_xml_string(output)
    except XMLSyntaxError as e:
        raise AssertionError(f"Expected valid XML, but could not parse output. {unicodify(e)}")


def assert_has_element_with_path(output, path, negate: bool = False):
    """Asserts the specified output has at least one XML element with a
    path matching the specified path argument. Valid paths are the
    simplified subsets of XPath implemented by lxml.etree;
    https://lxml.de/xpathxslt.html for more information."""
    assert_xml_element(output, path, negate=negate)


def assert_has_n_elements_with_path(
    output,
    path,
    n: Optional[int] = None,
    delta: int = 0,
    min: Optional[int] = None,
    max: Optional[int] = None,
    negate: bool = False,
):
    """Asserts the specified output has exactly n elements matching the
    path specified."""
    assert_xml_element(output, path, n=n, delta=delta, min=min, max=max, negate=negate)


def assert_element_text_matches(output, path, expression, negate: bool = False):
    """Asserts the text of the first element matching the specified
    path matches the specified regular expression."""
    sub = {"tag": "has_text_matching", "attributes": {"expression": expression, "negate": negate}}
    assert_xml_element(output, path, asserts.verify_assertions, [sub])


def assert_element_text_is(output, path, text, negate: bool = False):
    """Asserts the text of the first element matching the specified
    path matches exactly the specified text."""
    assert_element_text_matches(output, path, re.escape(text) + "$", negate=negate)


def assert_attribute_matches(output, path, attribute, expression, negate: bool = False):
    """Asserts the specified attribute of the first element matching
    the specified path matches the specified regular expression."""
    sub = {"tag": "has_text_matching", "attributes": {"expression": expression, "negate": negate}}
    assert_xml_element(output, path, asserts.verify_assertions, [sub], attribute=attribute)


def assert_attribute_is(output, path, attribute, text, negate: bool = False):
    """Asserts the specified attribute of the first element matching
    the specified path matches exactly the specified text."""
    assert_attribute_matches(output, path, attribute, re.escape(text) + "$", negate=negate)


def assert_element_text(output, path, verify_assertions_function, children, negate: bool = False):
    """Recursively checks the specified assertions against the text of
    the first element matching the specified path."""
    assert_xml_element(output, path, verify_assertions_function, children, negate=negate)


def assert_xml_element(
    output,
    path,
    verify_assertions_function=None,
    children=None,
    attribute=None,
    all=False,
    n: Optional[int] = None,
    delta: int = 0,
    min: Optional[int] = None,
    max: Optional[int] = None,
    negate: bool = False,
):
    """
    Check if path occurs in the xml. If n and delta or min and max are given
    also the number of occurences is checked.
    If there are any sub assertions then check them against
    - the element's text if attribute is None
    - the content of the attribute
    If all is True then the sub assertions are checked for all occurences.
    """
    children = children or []
    all = asbool(all)
    # assert that path is in output (the specified number of times)

    xml = parse_xml_string(output)
    asserts._util._assert_presence_number(
        xml,
        path,
        n,
        delta,
        min,
        max,
        negate,
        lambda x, p: x.find(p) is not None,
        lambda x, p: len(x.findall(p)),
        "{expected} path '{text}' in xml",
        "{expected} {n}+-{delta} occurrences of path '{text}' in xml",
        "{expected} that the number of occurences of path '{text}' in xml is in [{min}:{max}]",
    )

    # check sub-assertions
    if len(children) == 0 or verify_assertions_function is None:
        return
    for occ in xml.findall(path):
        if attribute is None or attribute == "":
            content = occ.text
        else:
            content = occ.attrib[attribute]
        try:
            verify_assertions_function(content, children)
        except AssertionError as e:
            if attribute is not None and attribute != "":
                raise AssertionError(f"Attribute '{attribute}' on element with path '{path}': {str(e)}")
            else:
                raise AssertionError(f"Text of element with path '{path}': {str(e)}")
        if not all:
            break
