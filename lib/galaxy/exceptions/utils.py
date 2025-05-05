from typing import (
    TYPE_CHECKING,
    Union,
)

from galaxy.exceptions import (
    error_codes,
    MessageException,
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.util.json import safe_dumps

if TYPE_CHECKING:
    from fastapi.exceptions import RequestValidationError
    from pydantic import ValidationError


def validation_error_to_message_exception(e: Union["ValidationError", "RequestValidationError"]) -> MessageException:
    invalid_found = False
    missing_found = False
    messages = []
    clean_validation_errors = []
    for error in e.errors():
        messages.append(f"{error['msg']} in {error['loc']}")
        if error["type"] == "message_exception" and "ctx" in error:
            return error["ctx"]["exception"]
        if error["type"] == "missing" or error["type"] == "type_error.none.not_allowed":
            missing_found = True
        elif error["type"].startswith("type_error"):
            invalid_found = True
        # ctx contains data that can't be serialized, like exception instances
        error.pop("ctx", None)
        try:
            clean_validation_errors.append(safe_dumps(error))
        except TypeError:
            pass
    if missing_found and not invalid_found:
        return RequestParameterMissingException("\n".join(messages), validation_errors=clean_validation_errors)
    else:
        return RequestParameterInvalidException("\n".join(messages), validation_errors=clean_validation_errors)


def api_error_to_dict(**kwds):
    UNKNOWN_ERROR_CODE = error_codes.error_codes_by_name["UNKNOWN"]
    exception = kwds.get("exception", None)
    if exception:
        # If we are passed a MessageException use err_msg.
        default_error_code = getattr(exception, "err_code", UNKNOWN_ERROR_CODE)
        default_error_message = getattr(exception, "err_msg", default_error_code.default_error_message)
        extra_error_info = getattr(exception, "extra_error_info", {})
        if not isinstance(extra_error_info, dict):
            extra_error_info = {}
    else:
        default_error_message = "Error processing API request."
        default_error_code = UNKNOWN_ERROR_CODE
        extra_error_info = {}
    traceback_string = kwds.get("traceback", "No traceback available.")
    err_msg = kwds.get("err_msg", default_error_message)
    error_code_object = kwds.get("err_code", default_error_code)
    try:
        error_code = error_code_object.code
    except AttributeError:
        # Some sort of bad error code sent in, logic failure on part of
        # Galaxy developer.
        error_code = UNKNOWN_ERROR_CODE.code
    # Would prefer the terminology of error_code and error_message, but
    # err_msg used a good number of places already. Might as well not change
    # it?
    error_response = dict(err_msg=err_msg, err_code=error_code, **extra_error_info)
    if kwds.get("debug"):  # TODO: Should admins get to see traceback as well?
        error_response["traceback"] = traceback_string
    return error_response
