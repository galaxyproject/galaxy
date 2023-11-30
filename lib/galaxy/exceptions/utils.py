from galaxy.exceptions import error_codes


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
