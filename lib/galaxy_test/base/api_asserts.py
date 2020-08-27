""" Utility methods for making assertions about Galaxy API responses, etc...
"""
ASSERT_FAIL_ERROR_CODE = "Expected Galaxy error code %d, obtained %d"
ASSERT_FAIL_STATUS_CODE = "Request status code (%d) was not expected value %s. Body was %s"


def assert_status_code_is(response, expected_status_code):
    response_status_code = response.status_code
    if expected_status_code != response_status_code:
        _report_status_code_error(response, expected_status_code)


def assert_status_code_is_ok(response):
    response_status_code = response.status_code
    is_two_hundred_status_code = response_status_code >= 200 and response_status_code <= 300
    if not is_two_hundred_status_code:
        _report_status_code_error(response, "2XX")


def _report_status_code_error(response, expected_status_code):
    try:
        body = response.json()
    except Exception:
        body = "INVALID JSON RESPONSE <%s>" % response.content
    assertion_message = ASSERT_FAIL_STATUS_CODE % (response.status_code, expected_status_code, body)
    raise AssertionError(assertion_message)


def assert_has_keys(response, *keys):
    for key in keys:
        assert key in response, "Response [{}] does not contain key [{}]".format(response, key)


def assert_not_has_keys(response, *keys):
    for key in keys:
        assert key not in response, "Response [{}] contains invalid key [{}]".format(response, key)


def assert_error_code_is(response, error_code):
    if hasattr(response, "json"):
        response = response.json()
    assert_has_keys(response, "err_code")
    err_code = response["err_code"]
    assert err_code == int(error_code), ASSERT_FAIL_ERROR_CODE % (err_code, int(error_code))


def assert_object_id_error(response):
    # for tests that use fake object IDs - API might throw MalformedId (400) or
    # or ObjectNotFound (404) - depending if the ID happens to be parseable with
    # servers API key.
    error_code = response.status_code
    assert error_code in [400, 404]
    if error_code == 400:
        assert_error_code_is(response, 400009)
    else:
        assert_error_code_is(response, 404001)


def assert_error_message_contains(response, expected_contains):
    if hasattr(response, "json"):
        response = response.json()
    assert_has_keys(response, "err_msg")
    err_msg = response["err_msg"]
    assert expected_contains in err_msg


assert_has_key = assert_has_keys
