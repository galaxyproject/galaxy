from __future__ import absolute_import

import re
import xml.etree


# Helper functions used to work with XML output.
def to_xml(output):
    return xml.etree.ElementTree.fromstring(output)


def xml_find_text(output, path):
    xml = to_xml(output)
    text = xml.findtext(path)
    return text


def xml_find(output, path):
    xml = to_xml(output)
    return xml.find(path)


def assert_is_valid_xml(output):
    """ Simple assertion that just verifies the specified output
    is valid XML."""
    try:
        to_xml(output)
    except Exception as e:
        # TODO: Narrow caught exception to just parsing failure
        raise AssertionError("Expected valid XML, but could not parse output. %s" % str(e))


def assert_has_element_with_path(output, path):
    """ Asserts the specified output has at least one XML element with a
    path matching the specified path argument. Valid paths are the
    simplified subsets of XPath implemented by xml.etree;
    http://effbot.org/zone/element-xpath.htm for more information."""
    if xml_find(output, path) is None:
        errmsg = "Expected to find XML element matching expression %s, not such match was found." % path
        raise AssertionError(errmsg)


def assert_has_n_elements_with_path(output, path, n):
    """ Asserts the specified output has exactly n elements matching the
    path specified."""
    xml = to_xml(output)
    n = int(n)
    num_elements = len(xml.findall(path))
    if num_elements != n:
        errmsg = "Expected to find %d elements with path %s, but %d were found." % (n, path, num_elements)
        raise AssertionError(errmsg)


def assert_element_text_matches(output, path, expression):
    """ Asserts the text of the first element matching the specified
    path matches the specified regular expression."""
    text = xml_find_text(output, path)
    if re.match(expression, text) is None:
        errmsg = "Expected element with path '%s' to contain text matching '%s', instead text '%s' was found." % (path, expression, text)
        raise AssertionError(errmsg)


def assert_element_text_is(output, path, text):
    """ Asserts the text of the first element matching the specified
    path matches exactly the specified text. """
    assert_element_text_matches(output, path, re.escape(text))


def assert_attribute_matches(output, path, attribute, expression):
    """ Asserts the specified attribute of the first element matching
    the specified path matches the specified regular expression."""
    xml = xml_find(output, path)
    attribute_value = xml.attrib[attribute]
    if re.match(expression, attribute_value) is None:
        errmsg = "Expected attribute '%s' on element with path '%s' to match '%s', instead attribute value was '%s'." % (attribute, path, expression, attribute_value)
        raise AssertionError(errmsg)


def assert_attribute_is(output, path, attribute, text):
    """ Asserts the specified attribute of the first element matching
    the specified path matches exactly the specified text."""
    assert_attribute_matches(output, path, attribute, re.escape(text))


def assert_element_text(output, path, verify_assertions_function, children):
    """ Recursively checks the specified assertions against the text of
    the first element matching the specified path."""
    text = xml_find_text(output, path)
    verify_assertions_function(text, children)
