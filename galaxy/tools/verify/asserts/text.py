import re


def assert_has_text(output, text):
    """ Asserts specified output contains the substring specified by
    the argument text."""
    assert output.find(text) >= 0, "Output file did not contain expected text '%s' (ouptut '%s')" % (text, output)


def assert_not_has_text(output, text):
    """ Asserts specified output does not contain the substring
    specified the argument text."""
    assert output.find(text) < 0, "Output file contains unexpected text '%s'" % text


def assert_has_line(output, line):
    """ Asserts the specified output contains the line specified the
    argument line."""
    match = re.search("^%s$" % re.escape(line), output, flags=re.MULTILINE)
    assert match is not None, "No line of output file was '%s' (output was '%s') " % (line, output)


def assert_has_text_matching(output, expression):
    """ Asserts the specified output contains text matching the
    regular expression specified by the argument expression."""
    match = re.search(expression, output)
    assert match is not None, "No text matching expression '%s' was found in output file." % expression


def assert_has_line_matching(output, expression):
    """ Asserts the specified output contains a line matching the
    regular expression specified by the argument expression."""
    match = re.search("^%s$" % expression, output, flags=re.MULTILINE)
    assert match is not None, "No line matching expression '%s' was found in output file." % expression
