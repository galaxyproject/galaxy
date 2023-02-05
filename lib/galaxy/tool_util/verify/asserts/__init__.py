import logging
import sys
from inspect import (
    getfullargspec,
    getmembers,
)

from galaxy.util import unicodify

log = logging.getLogger(__name__)

assertion_module_names = ["text", "tabular", "xml", "json", "hdf5", "archive", "size"]

# Code for loading modules containing assertion checking functions, to
# create a new module of assertion functions, create the needed python
# source file "test/base/asserts/<MODULE_NAME>.py" and add
# <MODULE_NAME> to the list of assertion module names defined above.
assertion_functions = {}
for assertion_module_name in assertion_module_names:
    full_assertion_module_name = f"galaxy.tool_util.verify.asserts.{assertion_module_name}"
    try:
        # Dynamically import module
        __import__(full_assertion_module_name)
        assertion_module = sys.modules[full_assertion_module_name]
    except Exception:
        log.exception("Failed to load assertion module: %s", assertion_module_name)
        continue
    for member, value in getmembers(assertion_module):
        if member.startswith("assert_"):
            assertion_functions[member] = value


def verify_assertions(data: bytes, assertion_description_list):
    """This function takes a list of assertions and a string to check
    these assertions against."""
    for assertion_description in assertion_description_list:
        verify_assertion(data, assertion_description)


def verify_assertion(data: bytes, assertion_description):
    tag = assertion_description["tag"]
    assert_function_name = "assert_" + tag
    assert_function = assertion_functions.get(assert_function_name)

    if assert_function is None:
        errmsg = f"Unable to find test function associated with XML tag {tag}. Check your tool file syntax."
        raise AssertionError(errmsg)

    assert_function_args = getfullargspec(assert_function).args
    args = {}
    for attribute, value in assertion_description["attributes"].items():
        if attribute in assert_function_args:
            args[attribute] = value

    # Three special arguments automatically populated independently of
    # tool XML attributes. output is passed in as the contents of the
    # output file. verify_assertions_function is passed in as the
    # verify_assertions function defined above, this allows
    # recursively checking assertions on subsections of
    # output. children is the parsed version of the child elements of
    # the XML element describing this assertion. See
    # assert_element_text in test/base/asserts/xml.py as an example of
    # how to use verify_assertions_function and children in conjuction
    # to apply assertion checking to a subset of the input. The parsed
    # version of an elements child elements do not need to just define
    # assertions, developers of assertion functions can also use the
    # child elements in novel ways to define inputs the assertion
    # checking function (for instance consider the following fictional
    # assertion function for checking column titles of tabular output
    # - <has_column_titles><with_name name="sequence"><with_name
    # name="probability"></has_column_titles>.)
    if "output" in assert_function_args:
        # If the assert_function will have an attribute called "output"
        # the data passed from the test to the function will be unicodified.
        # This is because most of the assert functions are working on pure
        # text files.
        args["output"] = unicodify(data)
    if "output_bytes" in assert_function_args:
        # This will read in data as bytes and will not change it prior passing
        # it to the assert_function
        args["output_bytes"] = data

    if "verify_assertions_function" in assert_function_args:
        args["verify_assertions_function"] = verify_assertions

    if "children" in assert_function_args:
        args["children"] = assertion_description["children"]

    # TODO: Verify all needed function arguments are specified.
    assert_function(**args)
