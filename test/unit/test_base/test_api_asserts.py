from galaxy.exceptions import error_codes
from galaxy_test.base.api_asserts import assert_error_code_is


def test_assert_error_code_is():
    response = {"err_code": 400007}
    assert_error_code_is(response, error_codes.error_codes_by_name["USER_REQUEST_MISSING_PARAMETER"])
