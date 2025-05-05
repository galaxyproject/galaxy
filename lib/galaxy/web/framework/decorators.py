import logging
from functools import wraps
from inspect import getfullargspec
from json import loads
from traceback import format_exc
from typing import (
    TYPE_CHECKING,
    Union,
)

import paste.httpexceptions
from pydantic import (
    BaseModel,
    ValidationError,
)

from galaxy.exceptions import (
    error_codes,
    MessageException,
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.exceptions.utils import api_error_to_dict
from galaxy.util import (
    parse_non_hex_float,
    unicodify,
)
from galaxy.util.json import safe_dumps
from galaxy.web.framework import url_for

if TYPE_CHECKING:
    from fastapi.exceptions import RequestValidationError

log = logging.getLogger(__name__)

JSON_CONTENT_TYPE = "application/json; charset=UTF-8"
JSONP_CONTENT_TYPE = "application/javascript"
JSONP_CALLBACK_KEY = "callback"


def error(message):
    raise MessageException(message, type="error")


# ----------------------------------------------------------------------------- web controller decorators
def _save_orig_fn(wrapped, orig):
    if not hasattr(orig, "_orig"):
        wrapped._orig = orig
    return wrapped


def expose(func):
    """
    Decorator: mark a function as 'exposed' and thus web accessible
    """
    func.exposed = True
    return func


def json(func, pretty=False):
    """
    Format the response as JSON and set the response content type to
    JSON_CONTENT_TYPE.
    """

    @wraps(func)
    def call_and_format(self, trans, *args, **kwargs):
        # pull out any callback argument to the api endpoint and set the content type to json or javascript
        jsonp_callback = kwargs.pop(JSONP_CALLBACK_KEY, None)
        if jsonp_callback:
            trans.response.set_content_type(JSONP_CONTENT_TYPE)
        else:
            trans.response.set_content_type(JSON_CONTENT_TYPE)
        rval = func(self, trans, *args, **kwargs)
        return format_return_as_json(rval, jsonp_callback, pretty=(pretty or trans.debug))

    if not hasattr(func, "_orig"):
        call_and_format._orig = func
    return expose(_save_orig_fn(call_and_format, func))


def json_pretty(func):
    """
    Indent and sort returned JSON.
    """
    return json(func, pretty=True)


def require_login(verb="perform this action", use_panels=False):
    def argcatcher(func):
        @wraps(func)
        def decorator(self, trans, *args, **kwargs):
            if trans.get_user():
                return func(self, trans, *args, **kwargs)
            else:
                redirect_url = url_for(controller=trans.controller, action=trans.action)
                query_string = trans.environ.get("QUERY_STRING", "")
                if query_string:
                    redirect_url = f"{redirect_url}?{query_string}"
                href = url_for(controller="login", redirect=redirect_url)
                return trans.show_error_message(
                    f'You must be <a target="galaxy_main" href="{href}" class="require-login-link">logged in</a> to {verb}.',
                    use_panels=use_panels,
                )

        return decorator

    return argcatcher


def require_admin(func):
    @wraps(func)
    def decorator(self, trans, *args, **kwargs):
        if not trans.user_is_admin:
            msg = require_admin_message(trans.app.config, trans.get_user())
            trans.response.status = 403
            content_type = trans.response.get_content_type()
            # content_type for instance may be... application/json; charset=UTF-8
            if "application/json" in content_type:
                return __api_error_dict(trans, status_code=403, err_code=error_codes.ADMIN_REQUIRED, err_msg=msg)
            else:
                return trans.show_error_message(msg)
        return func(self, trans, *args, **kwargs)

    return decorator


def require_admin_message(config, user):
    if not config.admin_users_list:
        msg = "You must be logged in as an administrator to access this feature, but no administrators are set in the Galaxy configuration."
    elif not user:
        msg = "You must be logged in as an administrator to access this feature."
    else:
        msg = "You must be an administrator to access this feature."
    return msg


def do_not_cache(func):
    """
    Sets cache-prevention headers for the request.
    """

    @wraps(func)
    def set_nocache_headers(self, trans, *args, **kwargs):
        trans.response.headers["Cache-Control"] = ["no-cache", "no-store", "must-revalidate"]
        trans.response.headers["Pragma"] = "no-cache"
        trans.response.headers["Expires"] = "0"
        return func(self, trans, *args, **kwargs)

    return set_nocache_headers


# ----------------------------------------------------------------------------- (original) api decorators
def legacy_expose_api(func, to_json=True, user_required=True):
    """
    Expose this function via the API.
    """

    @wraps(func)
    def decorator(self, trans, *args, **kwargs):
        def error(environ, start_response):
            start_response(error_status, [("Content-type", "text/plain")])
            return error_message

        error_status = "403 Forbidden"
        if trans.error_message:
            return trans.error_message
        if user_required and trans.anonymous:
            error_message = "API Authentication Required for this request"
            return error
        if trans.request.is_body_readable:
            try:
                kwargs["payload"] = __extract_payload_from_request(trans, func, kwargs)
            except ValueError:
                error_status = "400 Bad Request"
                error_message = "Your request did not appear to be valid JSON, please consult the API documentation"
                return error

        # pull out any callback argument to the api endpoint and set the content type to json or javascript
        jsonp_callback = kwargs.pop(JSONP_CALLBACK_KEY, None)
        if jsonp_callback:
            trans.response.set_content_type(JSONP_CONTENT_TYPE)
        else:
            trans.response.set_content_type(JSON_CONTENT_TYPE)

        # send 'do not cache' headers to handle IE's caching of ajax get responses
        trans.response.headers["Cache-Control"] = "max-age=0,no-cache,no-store"

        # Perform api_run_as processing, possibly changing identity
        if "payload" in kwargs and isinstance(kwargs["payload"], dict) and "run_as" in kwargs["payload"]:
            if not trans.user_can_do_run_as:
                error_message = "User does not have permissions to run jobs as another user"
                return error
            try:
                decoded_user_id = trans.security.decode_id(kwargs["payload"]["run_as"])
            except TypeError:
                trans.response.status = 400
                return f"Malformed user id ( {str(kwargs['payload']['run_as'])} ) specified, unable to decode."
            try:
                user = trans.sa_session.query(trans.app.model.User).get(decoded_user_id)
                trans.set_user(user)
            except Exception:
                trans.response.status = 400
                return "That user does not exist."
        try:
            rval = func(self, trans, *args, **kwargs)
            if to_json:
                rval = format_return_as_json(rval, jsonp_callback, pretty=trans.debug)
            return rval
        except paste.httpexceptions.HTTPException:
            raise  # handled
        except Exception:
            log.exception("Uncaught exception in exposed API method:")
            raise paste.httpexceptions.HTTPServerError()

    return expose(_save_orig_fn(decorator, func))


def __extract_payload_from_request(trans, func, kwargs):
    content_type = trans.request.headers.get("content-type", "")
    if content_type.startswith("application/x-www-form-urlencoded") or content_type.startswith("multipart/form-data"):
        # If the content type is a standard type such as multipart/form-data, the wsgi framework parses the request body
        # and loads all field values into kwargs. However, kwargs also contains formal method parameters etc. which
        # are not a part of the request body. This is a problem because it's not possible to differentiate between values
        # which are a part of the request body, and therefore should be a part of the payload, and values which should not be
        # in the payload. Therefore, the decorated method's formal arguments are discovered through reflection and removed from
        # the payload dictionary. This helps to prevent duplicate argument conflicts in downstream methods.
        payload = kwargs.copy()
        named_args = getfullargspec(func).args
        for arg in named_args:
            payload.pop(arg, None)
        for k, v in payload.items():
            if isinstance(v, str):
                try:
                    # note: parse_non_hex_float only needed here for single string values where something like
                    # 40000000000000e5 will be parsed as a scientific notation float. This is as opposed to hex strings
                    # in larger JSON structures where quoting prevents this (further below)
                    payload[k] = loads(v, parse_float=parse_non_hex_float)
                except Exception:
                    # may not actually be json, just continue
                    pass
    elif content_type == "application/offset+octet-stream":
        return unicodify(trans.request.body)
    else:
        # Assume application/json content type and parse request body manually, since wsgi won't do it. However, the order of this check
        # should ideally be in reverse, with the if clause being a check for application/json and the else clause assuming a standard encoding
        # such as multipart/form-data. Leaving it as is for backward compatibility, just in case.
        payload = loads(unicodify(trans.request.body))
    if run_as := trans.request.headers.get("run-as"):
        payload["run_as"] = run_as
    return payload


def legacy_expose_api_raw(func):
    """
    Expose this function via the API but don't dump the results
    to JSON.
    """
    return legacy_expose_api(func, to_json=False)


def legacy_expose_api_raw_anonymous(func):
    """
    Expose this function via the API but don't dump the results
    to JSON.
    """
    return legacy_expose_api(func, to_json=False, user_required=False)


def legacy_expose_api_anonymous(func, to_json=True):
    """
    Expose this function via the API but don't require a set user.
    """
    return legacy_expose_api(func, to_json=to_json, user_required=False)


# ----------------------------------------------------------------------------- (new) api decorators
def expose_api(func, to_json=True, user_required=True, user_or_session_required=True, handle_jsonp=True):
    """
    Expose this function via the API.
    """

    @wraps(func)
    def decorator(self, trans, *args, **kwargs):
        # errors passed in from trans._authenticate_api
        if trans.error_message:
            return __api_error_response(
                trans, status_code=403, err_code=error_codes.USER_NO_API_KEY, err_msg=trans.error_message
            )
        if trans.anonymous:
            # error if anon and user required
            if user_required:
                return __api_error_response(
                    trans,
                    status_code=403,
                    err_code=error_codes.USER_NO_API_KEY,
                    err_msg="API authentication required for this request",
                )
            # error if anon and no session
            if not trans.galaxy_session and user_or_session_required:
                return __api_error_response(
                    trans,
                    status_code=403,
                    err_code=error_codes.USER_NO_API_KEY,
                    err_msg="API authentication or Galaxy session required for this request",
                )

        if trans.request.is_body_readable:
            try:
                kwargs["payload"] = __extract_payload_from_request(trans, func, kwargs)
            except ValueError:
                error_code = error_codes.USER_INVALID_JSON
                return __api_error_response(trans, status_code=400, err_code=error_code)

        # pull out any callback argument to the api endpoint and set the content type to json or javascript
        # TODO: use handle_jsonp to NOT overwrite existing tool_shed JSONP
        jsonp_callback = kwargs.pop(JSONP_CALLBACK_KEY, None) if handle_jsonp else None
        if jsonp_callback:
            trans.response.set_content_type(JSONP_CONTENT_TYPE)
        else:
            trans.response.set_content_type(JSON_CONTENT_TYPE)

        # send 'do not cache' headers to handle IE's caching of ajax get responses
        trans.response.headers["Cache-Control"] = "max-age=0,no-cache,no-store"

        # TODO: Refactor next block out into a helper procedure.
        # Perform api_run_as processing, possibly changing identity
        if "payload" in kwargs and "run_as" in kwargs["payload"]:
            if not trans.user_can_do_run_as:
                error_code = error_codes.USER_CANNOT_RUN_AS
                return __api_error_response(trans, err_code=error_code, status_code=403)
            try:
                decoded_user_id = trans.security.decode_id(kwargs["payload"]["run_as"])
            except (TypeError, ValueError):
                error_message = f"Malformed user id ( {str(kwargs['payload']['run_as'])} ) specified, unable to decode."
                error_code = error_codes.USER_INVALID_RUN_AS
                return __api_error_response(trans, err_code=error_code, err_msg=error_message, status_code=400)
            try:
                user = trans.sa_session.query(trans.app.model.User).get(decoded_user_id)
                trans.set_user(user)
            except Exception:
                error_code = error_codes.USER_INVALID_RUN_AS
                return __api_error_response(trans, err_code=error_code, status_code=400)
        try:
            try:
                rval = func(self, trans, *args, **kwargs)
            except ValidationError as e:
                raise validation_error_to_message_exception(e)
            if to_json:
                rval = format_return_as_json(rval, jsonp_callback, pretty=trans.debug)
            return rval
        except MessageException as e:
            traceback_string = format_exc()
            return __api_error_response(trans, exception=e, traceback=traceback_string)
        except paste.httpexceptions.HTTPException:
            # TODO: Allow to pass or format for the API???
            raise  # handled
        except Exception as e:
            traceback_string = format_exc()
            error_message = "Uncaught exception in exposed API method:"
            log.exception(error_message)
            return __api_error_response(
                trans,
                status_code=500,
                exception=e,
                traceback=traceback_string,
                err_msg=error_message,
                err_code=error_codes.UNKNOWN,
            )

    if not hasattr(func, "_orig"):
        decorator._orig = func
    decorator.exposed = True
    return decorator


def format_return_as_json(rval, jsonp_callback=None, pretty=False):
    """
    Formats a return value as JSON or JSONP if `jsonp_callback` is present.

    Use `pretty=True` to return pretty printed json.
    """
    dumps_kwargs = dict(indent=4, sort_keys=True) if pretty else {}
    if isinstance(rval, BaseModel):
        json = rval.model_dump_json(indent=4)
    else:
        json = safe_dumps(rval, **dumps_kwargs)
    if jsonp_callback:
        json = f"{jsonp_callback}({json});"
    return json


def validation_error_to_message_exception(e: Union[ValidationError, "RequestValidationError"]) -> MessageException:
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


def __api_error_dict(trans, **kwds):
    error_dict = api_error_to_dict(debug=trans.debug, **kwds)
    exception = kwds.get("exception", None)
    # If we are given an status code directly - use it - otherwise check
    # the exception for a status_code attribute.
    if "status_code" in kwds:
        status_code = int(kwds.get("status_code"))
    elif hasattr(exception, "status_code"):
        status_code = int(exception.status_code)
    else:
        status_code = 500
    response = trans.response
    if not response.status or str(response.status).startswith("20"):
        # Unset status code appears to be string '200 OK', if anything
        # non-success (i.e. not 200 or 201) has been set, do not override
        # underlying controller.
        response.status = status_code
    return error_dict


def __api_error_response(trans, **kwds):
    error_dict = __api_error_dict(trans, **kwds)
    return safe_dumps(error_dict)


def expose_api_anonymous(func, to_json=True):
    """
    Expose this function via the API but don't require a set user.
    """
    return expose_api(func, to_json=to_json, user_required=False)


def expose_api_anonymous_and_sessionless(func, to_json=True):
    """
    Expose this function via the API but don't require a user or a galaxy_session.
    """
    return expose_api(func, to_json=to_json, user_required=False, user_or_session_required=False)


def expose_api_raw(func):
    return expose_api(func, to_json=False, user_required=True)


def expose_api_raw_anonymous(func):
    return expose_api(func, to_json=False, user_required=False)


def expose_api_raw_anonymous_and_sessionless(func):
    # TODO: tool_shed api implemented JSONP first on a method-by-method basis, don't overwrite that for now
    return expose_api(func, to_json=False, user_required=False, user_or_session_required=False, handle_jsonp=False)
