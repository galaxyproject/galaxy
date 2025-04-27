import logging
from typing import (
    List,
    Optional,
)

ATTRIBUTE_SPLIT_CHAR = "."

log = logging.getLogger(__name__)


def _build_getattr_lambda(attr_name_list):
    """
    Recursively builds a compound lambda function of getattr's
    from the attribute names given in `attr_name_list`.
    """
    if len(attr_name_list) == 0:
        # identity - if list is empty, return object itself
        return lambda o: o

    next_attr_name = attr_name_list[-1]
    if len(attr_name_list) == 1:
        # recursive base case
        return lambda o: getattr(o, next_attr_name)

    # recursive case
    return lambda o: getattr(_build_getattr_lambda(attr_name_list[:-1])(o), next_attr_name)


def _check_uri_support(target_object, supported_protocols: List[str]) -> bool:
    """Test if the target object is deferred and has a supported protocol."""

    if not _is_deferred(target_object):
        return True  # not deferred, so no uri to check

    if not supported_protocols:
        return False  # no protocols defined, means no support for deferred objects

    if "*" in supported_protocols:
        return True  # wildcard support for all protocols

    deferred_source_uri = _deferred_source_uri(target_object)
    if deferred_source_uri:
        protocol = deferred_source_uri.split("://")[0]
        return protocol in supported_protocols
    return False


def _deferred_source_uri(target_object) -> Optional[str]:
    """Get the source uri from a deferred object."""
    sources = getattr(target_object, "sources", None)
    if sources and sources[0]:
        return sources[0].source_uri
    return None


def _get_test_function(test_attr, test_type):
    test_attr_array = test_attr.split(ATTRIBUTE_SPLIT_CHAR) if isinstance(test_attr, str) else []
    # log.debug( 'test_type: %s, test_attr: %s, test_result: %s', test_type, test_attr, test_result )

    # build a lambda function that gets the desired attribute to test
    getter = _build_getattr_lambda(test_attr_array)
    # test_attr can be a dot separated chain of object attributes (e.g. dataset.datatype) - convert to list
    # TODO: too dangerous - constrain these to some allowed list
    # TODO: does this err if no test_attr - it should...

    # test functions should be sent an object to test, and the parsed result expected from the test
    if test_type == "isinstance":
        # is test_attr attribute an instance of result
        # TODO: wish we could take this further but it would mean passing in the datatypes_registry
        def test_fn(o, result, getter=getter):
            return isinstance(getter(o), result)

    elif test_type == "has_dataprovider":
        # does the object itself have a datatype attr and does that datatype have the given dataprovider
        def test_fn(o, result, getter=getter):
            return hasattr(getter(o), "has_dataprovider") and getter(o).has_dataprovider(result)

    elif test_type == "has_attribute":
        # does the object itself have attr in 'result' (no equivalence checking)
        def test_fn(o, result, getter=getter):
            return hasattr(getter(o), result)

    elif test_type == "not_eq":

        def test_fn(o, result, getter=getter):
            return str(getter(o)) != result

    else:
        # default to simple (string) equilavance (coercing the test_attr to a string)
        def test_fn(o, result, getter=getter):
            return str(getter(o)) == result

    return test_fn


def _is_deferred(target_object) -> bool:
    """Whether the target object is a deferred object."""
    return getattr(target_object, "state", None) == "deferred"


def is_object_applicable(trans, target_object, data_source_tests):
    """
    Run a visualization's data_source tests to find out if
    it can be applied to the target_object.
    """
    # log.debug( 'is_object_applicable( self, trans, %s, %s )', target_object, data_source_tests )
    for test in data_source_tests:
        test_attr = test["attr"]
        test_type = test["type"]
        result_type = test["result_type"]
        test_result = test["result"]
        test_fn = _get_test_function(test_attr, test_type)

        supported_protocols = test.get("allow_uri_if_protocol", [])
        # log.debug( '%s %s: %s, %s, %s, %s', str( target_object ), 'is_object_applicable',
        #           test_type, result_type, test_result, test_fn )
        if test_type == "isinstance":
            # parse test_result based on result_type (curr: only datatype has to do this)
            if result_type == "datatype":
                # convert datatypes to their actual classes (for use with isinstance)
                datatype_class_name = test_result
                test_result = trans.app.datatypes_registry.get_datatype_class_by_name(datatype_class_name)
                if not test_result:
                    # but continue (with other tests) if can't find class by that name
                    # if debug:
                    #    log.warning( 'visualizations_registry cannot find class (%s)' +
                    #              ' for applicability test on: %s, id: %s', datatype_class_name,
                    #              target_object, getattr( target_object, 'id', '' ) )
                    continue
        elif test_attr == "ext" and test_type == "eq":
            if target_object.state == "ok":
                test_result = trans.app.datatypes_registry.get_datatype_by_extension(test_result)
                if isinstance(target_object.datatype, type(test_result)) and _check_uri_support(
                    target_object, supported_protocols
                ):
                    return True
            continue
        # NOTE: tests are OR'd, if any test passes - the visualization can be applied
        if test_fn(target_object, test_result) and _check_uri_support(target_object, supported_protocols):
            # log.debug( '\t test passed' )
            return True

    return False
