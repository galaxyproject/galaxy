"""Utility methods for making assertions about Galaxy API responses, etc..."""

from typing import (
    Any,
    cast,
    Dict,
    Optional,
    Union,
)

from requests import Response

from galaxy.exceptions.error_codes import ErrorCode


def assert_status_code_is(response: Response, expected_status_code: int, failure_message: Optional[str] = None):
    """Assert that the supplied response has the expect status code."""
    response_status_code = response.status_code
    if expected_status_code != response_status_code:
        _report_status_code_error(response, expected_status_code, failure_message)


def assert_status_code_is_ok(response: Response, failure_message: Optional[str] = None):
    """Assert that the supplied response is okay.

    This is an alternative to ``response.raise_for_status()`` with a more detailed
    error message.

    .. seealso:: :py:meth:`requests.Response.raise_for_status()`
    """
    response_status_code = response.status_code
    is_two_hundred_status_code = response_status_code >= 200 and response_status_code <= 300
    if not is_two_hundred_status_code:
        _report_status_code_error(response, "2XX", failure_message)


def assert_status_code_is_not_ok(response: Response, failure_message: Optional[str] = None):
    """Assert that the supplied response is not okay.

    .. seealso:: :py:meth:`assert_status_code_is_ok`
    """
    response_status_code = response.status_code
    is_two_hundred_status_code = response_status_code >= 200 and response_status_code <= 300
    if is_two_hundred_status_code:
        _report_status_code_error(response, "2XX", failure_message)


def _report_status_code_error(
    response: Response, expected_status_code: Union[str, int], failure_message: Optional[str]
):
    try:
        body = response.json()
    except Exception:
        body = f"INVALID JSON RESPONSE <{response.text}>"
    assertion_message = (
        f"Request status code ({response.status_code}) was not expected value {expected_status_code}. Body was {body}"
    )
    if failure_message:
        assertion_message = f"{failure_message}. {assertion_message}"
    raise AssertionError(assertion_message)


def assert_has_keys(response: dict, *keys: str):
    """Assert that the supplied response (dict) has the supplied keys."""
    for key in keys:
        assert key in response, f"Response [{response}] does not contain key [{key}]"


def assert_not_has_keys(response: dict, *keys: str):
    """Assert that the supplied response (dict) does not have the supplied keys."""
    for key in keys:
        assert key not in response, f"Response [{response}] contains invalid key [{key}]"


def assert_error_code_is(response: Union[Response, dict], error_code: Union[int, ErrorCode]):
    """Assert that the supplied response has the supplied Galaxy error code.

    Galaxy error codes can be imported from :py:mod:`galaxy.exceptions.error_codes`
    to test against.
    """
    as_dict = _as_dict(response)
    assert_has_keys(as_dict, "err_code")
    err_code = as_dict["err_code"]
    assert err_code == int(error_code), f"Expected Galaxy error code {error_code}, obtained {err_code}"


def assert_object_id_error(response: Response):
    # for tests that use fake object IDs - API might throw MalformedId (400) or
    # or ObjectNotFound (404) - depending if the ID happens to be parseable with
    # servers API key.
    error_code = response.status_code
    assert error_code in [400, 404]
    if error_code == 400:
        assert_error_code_is(response, 400009)
    else:
        assert_error_code_is(response, 404001)


def assert_error_message_contains(response: Union[Response, dict], expected_contains: str):
    as_dict = _as_dict(response)
    assert_has_keys(as_dict, "err_msg")
    err_msg = as_dict["err_msg"]
    assert expected_contains in err_msg, f"Expected error message [{err_msg}] to contain [{expected_contains}]."


def _as_dict(response: Union[Response, dict]) -> Dict[str, Any]:
    as_dict: Dict[str, Any]
    if isinstance(response, Response):
        as_dict = cast(dict, response.json())
    else:
        as_dict = response
    return as_dict


assert_has_key = assert_has_keys
