""" Utility methods for making assertions about Galaxy API responses, etc...
"""
ASSERT_FAIL_ERROR_CODE = "Expected Galaxy error code %d, obtained %d"
ASSERT_FAIL_STATUS_CODE = "Request status code (%d) was not expected value %d. Body was %s"


def assert_status_code_is( response, expected_status_code ):
    response_status_code = response.status_code
    if expected_status_code != response_status_code:
        try:
            body = response.json()
        except Exception:
            body = "INVALID JSON RESPONSE <%s>" % response.content
        assertion_message = ASSERT_FAIL_STATUS_CODE % ( response_status_code, expected_status_code, body )
        raise AssertionError( assertion_message )


def assert_has_keys( response, *keys ):
    for key in keys:
        assert key in response, "Response [%s] does not contain key [%s]" % ( response, key )


def assert_error_code_is( response, error_code ):
    if hasattr( response, "json" ):
        response = response.json()
    assert_has_keys( response, "err_code" )
    err_code = response[ "err_code" ]
    assert err_code == int( error_code ), ASSERT_FAIL_ERROR_CODE % ( err_code, int( error_code ) )

assert_has_key = assert_has_keys
