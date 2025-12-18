import logging
from typing import (
    Optional,
)

log = logging.getLogger(__name__)


def _check_uri_support(target_object, supported_protocols: list[str]) -> bool:
    """Test if the target object is deferred and has a supported protocol."""

    if getattr(target_object, "state", None) != "deferred":
        return True  # not deferred, so no uri to check

    if not supported_protocols:
        return False  # no protocols defined, means no support for deferred objects

    if "*" in supported_protocols:
        return True  # wildcard support for all protocols

    if deferred_source_uri := _deferred_source_uri(target_object):
        protocol = deferred_source_uri.split("://")[0]
        return protocol in supported_protocols
    return False


def _deferred_source_uri(target_object) -> Optional[str]:
    """Get the source uri from a deferred object."""
    sources = getattr(target_object, "sources", None)
    if sources and sources[0]:
        return sources[0].source_uri
    return None


def is_object_applicable(trans, target_object, data_source_tests):
    """
    Run a visualization's data_source tests to find out if
    it can be applied to the target_object.
    """
    for test in data_source_tests:
        test_attr = test["attr"]
        test_type = test["type"]
        test_result = test["result"]
        supported_protocols = test.get("allow_uri_if_protocol", [])
        if test_attr == "ext" and test_type == "eq":
            if target_object.state in ["deferred", "ok"]:
                test_result = trans.app.datatypes_registry.get_datatype_by_extension(test_result)
                if isinstance(target_object.datatype, type(test_result)) and _check_uri_support(
                    target_object, supported_protocols
                ):
                    return True
    return False
