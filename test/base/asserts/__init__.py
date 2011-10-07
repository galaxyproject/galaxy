import inspect
import logging
import sys
log = logging.getLogger( __name__ )

assertion_module_names = ['text', 'tabular', 'xml']

# Code for loading modules containing assertion checking functions, to
# create a new module of assertion functions, create the needed python
# source file "test/base/asserts/<MODULE_NAME>.py" and add
# <MODULE_NAME> to the list of assertion module names defined above. 
assertion_modules = []
for assertion_module_name in assertion_module_names:
    full_assertion_module_name = 'base.asserts.' + assertion_module_name
    log.debug(full_assertion_module_name)
    try:
        #Dynamically import module
        __import__(full_assertion_module_name)
        assertion_module = sys.modules[full_assertion_module_name]
        assertion_modules.append(assertion_module)
    except Exception, e:
        log.exception( 'Failed to load assertion module: %s %s' % (assertion_module_name, str(e))) 

def verify_assertions(data, assertion_description_list):
    """ This function takes a list of assertions and a string to check
    these assertions against. """
    for assertion_description in assertion_description_list:
        verify_assertion(data, assertion_description)

def verify_assertion(data, assertion_description):
    tag = assertion_description["tag"]
    assert_function_name = "assert_" + tag
    assert_function = None
    for assertion_module in assertion_modules:
        if hasattr(assertion_module, assert_function_name):
            assert_function = getattr(assertion_module, assert_function_name)

    if assert_function is None:
        errmsg = "Unable to find test function associated with XML tag '%s'. Check your tool file syntax." % tag
        raise AssertionError(errmsg)
    
    assert_function_args = inspect.getargspec(assert_function).args
    args = {}
    for attribute, value in assertion_description["attributes"].iteritems():
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
        args["output"] = data

    if "verify_assertions_function" in assert_function_args:
        args["verify_assertions_function"] = verify_assertions

    if "children" in assert_function_args:
        args["children"] = assertion_description["children"]
        
    # TODO: Verify all needed function arguments are specified.
    assert_function(**args)
    
