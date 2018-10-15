import inspect
import logging
from functools import wraps
from json import loads
from traceback import format_exc

import paste.httpexceptions
from six import string_types

from galaxy.exceptions import error_codes, MessageException
from galaxy.util import (
    parse_non_hex_float,
    unicodify
)
from galaxy.util.json import safe_dumps
from galaxy.web.framework import url_for

log = logging.getLogger(__name__)

JSON_CONTENT_TYPE = "application/json"
JSONP_CONTENT_TYPE = "application/javascript"
JSONP_CALLBACK_KEY = 'callback'


def error(message):
    raise MessageException(message, type='error')


# ----------------------------------------------------------------------------- web controller decorators
def _save_orig_fn(wrapped, orig):
    if not hasattr(orig, '_orig'):
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
        return _format_return_as_json(rval, jsonp_callback, pretty=(pretty or trans.debug))

    if not hasattr(func, '_orig'):
        call_and_format._orig = func
    return expose(_save_orig_fn(call_and_format, func))


def json_pretty(func):
    """
    Indent and sort returned JSON.
    """
    return json(func, pretty=True)


def require_login(verb="perform this action", use_panels=False, webapp='galaxy'):
    def argcatcher(func):
        @wraps(func)
        def decorator(self, trans, *args, **kwargs):
            if trans.get_user():
                return func(self, trans, *args, **kwargs)
            else:
                return trans.show_error_message(
                    'You must be <a target="galaxy_main" href="%s">logged in</a> to %s.'
                    % (url_for(controller='user', action='login', webapp=webapp), verb), use_panels=use_panels)
        return decorator
    return argcatcher


def require_admin(func):
    @wraps(func)
    def decorator(self, trans, *args, **kwargs):
        if not trans.user_is_admin:
            msg = "You must be an administrator to access this feature."
            user = trans.get_user()
            if not trans.app.config.admin_users_list:
                msg = "You must be logged in as an administrator to access this feature, but no administrators are set in the Galaxy configuration."
            elif not user:
                msg = "You must be logged in as an administrator to access this feature."
            trans.response.status = 403
            if trans.response.get_content_type() == 'application/json':
                return msg
            else:
                return trans.show_error_message(msg)
        return func(self, trans, *args, **kwargs)
    return decorator


# ----------------------------------------------------------------------------- (original) api decorators
def expose_api(func, to_json=True, user_required=True):
    """
    Expose this function via the API.
    """
    @wraps(func)
    def decorator(self, trans, *args, **kwargs):
        def error(environ, start_response):
            start_response(error_status, [('Content-type', 'text/plain')])
            return error_message
        error_status = '403 Forbidden'
        if trans.error_message:
            return trans.error_message
        if user_required and trans.anonymous:
            error_message = "API Authentication Required for this request"
            return error
        if trans.request.body:
            try:
                kwargs['payload'] = __extract_payload_from_request(trans, func, kwargs)
            except ValueError:
                error_status = '400 Bad Request'
                error_message = 'Your request did not appear to be valid JSON, please consult the API documentation'
                return error

        # pull out any callback argument to the api endpoint and set the content type to json or javascript
        jsonp_callback = kwargs.pop(JSONP_CALLBACK_KEY, None)
        if jsonp_callback:
            trans.response.set_content_type(JSONP_CONTENT_TYPE)
        else:
            trans.response.set_content_type(JSON_CONTENT_TYPE)

        # send 'do not cache' headers to handle IE's caching of ajax get responses
        trans.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        # Perform api_run_as processing, possibly changing identity
        if 'payload' in kwargs and isinstance(kwargs['payload'], dict) and 'run_as' in kwargs['payload']:
            if not trans.user_can_do_run_as:
                error_message = 'User does not have permissions to run jobs as another user'
                return error
            try:
                decoded_user_id = trans.security.decode_id(kwargs['payload']['run_as'])
            except TypeError:
                trans.response.status = 400
                return "Malformed user id ( %s ) specified, unable to decode." % str(kwargs['payload']['run_as'])
            try:
                user = trans.sa_session.query(trans.app.model.User).get(decoded_user_id)
                trans.api_inherit_admin = trans.user_is_admin
                trans.set_user(user)
            except Exception:
                trans.response.status = 400
                return "That user does not exist."
        try:
            rval = func(self, trans, *args, **kwargs)
            if to_json:
                rval = _format_return_as_json(rval, jsonp_callback, pretty=trans.debug)
            return rval
        except paste.httpexceptions.HTTPException:
            raise  # handled
        except Exception:
            log.exception('Uncaught exception in exposed API method:')
            raise paste.httpexceptions.HTTPServerError()
    return expose(_save_orig_fn(decorator, func))


def __extract_payload_from_request(trans, func, kwargs):
    content_type = trans.request.headers.get('content-type', '')
    if content_type.startswith('application/x-www-form-urlencoded') or content_type.startswith('multipart/form-data'):
        # If the content type is a standard type such as multipart/form-data, the wsgi framework parses the request body
        # and loads all field values into kwargs. However, kwargs also contains formal method parameters etc. which
        # are not a part of the request body. This is a problem because it's not possible to differentiate between values
        # which are a part of the request body, and therefore should be a part of the payload, and values which should not be
        # in the payload. Therefore, the decorated method's formal arguments are discovered through reflection and removed from
        # the payload dictionary. This helps to prevent duplicate argument conflicts in downstream methods.
        payload = kwargs.copy()
        named_args, _, _, _ = inspect.getargspec(func)
        for arg in named_args:
            payload.pop(arg, None)
        for k, v in payload.items():
            if isinstance(v, string_types):
                try:
                    # note: parse_non_hex_float only needed here for single string values where something like
                    # 40000000000000e5 will be parsed as a scientific notation float. This is as opposed to hex strings
                    # in larger JSON structures where quoting prevents this (further below)
                    payload[k] = loads(v, parse_float=parse_non_hex_float)
                except Exception:
                    # may not actually be json, just continue
                    pass
    else:
        # Assume application/json content type and parse request body manually, since wsgi won't do it. However, the order of this check
        # should ideally be in reverse, with the if clause being a check for application/json and the else clause assuming a standard encoding
        # such as multipart/form-data. Leaving it as is for backward compatibility, just in case.
        payload = loads(unicodify(trans.request.body))
    return payload


def expose_api_raw(func):
    """
    Expose this function via the API but don't dump the results
    to JSON.
    """
    return expose_api(func, to_json=False)


def expose_api_raw_anonymous(func):
    """
    Expose this function via the API but don't dump the results
    to JSON.
    """
    return expose_api(func, to_json=False, user_required=False)


def expose_api_anonymous(func, to_json=True):
    """
    Expose this function via the API but don't require a set user.
    """
    return expose_api(func, to_json=to_json, user_required=False)


# ----------------------------------------------------------------------------- (new) api decorators
# TODO: rename as expose_api and make default.
def _future_expose_api(func, to_json=True, user_required=True, user_or_session_required=True, handle_jsonp=True):
    """
    Expose this function via the API.
    """
    @wraps(func)
    def decorator(self, trans, *args, **kwargs):
        # errors passed in from trans._authenicate_api
        if trans.error_message:
            return __api_error_response(trans, status_code=403, err_code=error_codes.USER_NO_API_KEY,
                                        err_msg=trans.error_message)
        if trans.anonymous:
            # error if anon and user required
            if user_required:
                return __api_error_response(trans, status_code=403, err_code=error_codes.USER_NO_API_KEY,
                                            err_msg="API authentication required for this request")
            # error if anon and no session
            if not trans.galaxy_session and user_or_session_required:
                return __api_error_response(trans, status_code=403, err_code=error_codes.USER_NO_API_KEY,
                                            err_msg="API authentication required for this request")

        if trans.request.body:
            try:
                kwargs['payload'] = __extract_payload_from_request(trans, func, kwargs)
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
        trans.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        # TODO: Refactor next block out into a helper procedure.
        # Perform api_run_as processing, possibly changing identity
        if 'payload' in kwargs and 'run_as' in kwargs['payload']:
            if not trans.user_can_do_run_as:
                error_code = error_codes.USER_CANNOT_RUN_AS
                return __api_error_response(trans, err_code=error_code, status_code=403)
            try:
                decoded_user_id = trans.security.decode_id(kwargs['payload']['run_as'])
            except (TypeError, ValueError):
                error_message = "Malformed user id ( %s ) specified, unable to decode." % str(kwargs['payload']['run_as'])
                error_code = error_codes.USER_INVALID_RUN_AS
                return __api_error_response(trans, err_code=error_code, err_msg=error_message, status_code=400)
            try:
                user = trans.sa_session.query(trans.app.model.User).get(decoded_user_id)
                trans.api_inherit_admin = trans.user_is_admin
                trans.set_user(user)
            except Exception:
                error_code = error_codes.USER_INVALID_RUN_AS
                return __api_error_response(trans, err_code=error_code, status_code=400)
        try:
            rval = func(self, trans, *args, **kwargs)
            if to_json:
                rval = _format_return_as_json(rval, jsonp_callback, pretty=trans.debug)
            return rval
        except MessageException as e:
            traceback_string = format_exc()
            return __api_error_response(trans, exception=e, traceback=traceback_string)
        except paste.httpexceptions.HTTPException:
            # TODO: Allow to pass or format for the API???
            raise  # handled
        except Exception as e:
            traceback_string = format_exc()
            error_message = 'Uncaught exception in exposed API method:'
            log.exception(error_message)
            return __api_error_response(
                trans,
                status_code=500,
                exception=e,
                traceback=traceback_string,
                err_msg=error_message,
                err_code=error_codes.UNKNOWN
            )
    if not hasattr(func, '_orig'):
        decorator._orig = func
    decorator.exposed = True
    return decorator


def _format_return_as_json(rval, jsonp_callback=None, pretty=False):
    """
    Formats a return value as JSON or JSONP if `jsonp_callback` is present.

    Use `pretty=True` to return pretty printed json.
    """
    dumps_kwargs = dict(indent=4, sort_keys=True) if pretty else {}
    json = safe_dumps(rval, **dumps_kwargs)
    if jsonp_callback:
        json = "{}({});".format(jsonp_callback, json)
    return json


def __api_error_message(trans, **kwds):
    exception = kwds.get("exception", None)
    if exception:
        # If we are passed a MessageException use err_msg.
        default_error_code = getattr(exception, "err_code", error_codes.UNKNOWN)
        default_error_message = getattr(exception, "err_msg", default_error_code.default_error_message)
        extra_error_info = getattr(exception, 'extra_error_info', {})
        if not isinstance(extra_error_info, dict):
            extra_error_info = {}
    else:
        default_error_message = "Error processing API request."
        default_error_code = error_codes.UNKNOWN
        extra_error_info = {}
    traceback_string = kwds.get("traceback", "No traceback available.")
    err_msg = kwds.get("err_msg", default_error_message)
    error_code_object = kwds.get("err_code", default_error_code)
    try:
        error_code = error_code_object.code
    except AttributeError:
        # Some sort of bad error code sent in, logic failure on part of
        # Galaxy developer.
        error_code = error_codes.UNKNOWN.code
    # Would prefer the terminology of error_code and error_message, but
    # err_msg used a good number of places already. Might as well not change
    # it?
    error_response = dict(err_msg=err_msg, err_code=error_code, **extra_error_info)
    if trans.debug:  # TODO: Should admins get to see traceback as well?
        error_response["traceback"] = traceback_string
    return error_response


def __api_error_response(trans, **kwds):
    error_dict = __api_error_message(trans, **kwds)
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
    return safe_dumps(error_dict)


def _future_expose_api_anonymous(func, to_json=True):
    """
    Expose this function via the API but don't require a set user.
    """
    return _future_expose_api(func, to_json=to_json, user_required=False)


def _future_expose_api_anonymous_and_sessionless(func, to_json=True):
    """
    Expose this function via the API but don't require a user or a galaxy_session.
    """
    return _future_expose_api(func, to_json=to_json, user_required=False, user_or_session_required=False)


def _future_expose_api_raw(func):
    return _future_expose_api(func, to_json=False, user_required=True)


def _future_expose_api_raw_anonymous(func):
    return _future_expose_api(func, to_json=False, user_required=False)


def _future_expose_api_raw_anonymous_and_sessionless(func):
    # TODO: tool_shed api implemented JSONP first on a method-by-method basis, don't overwrite that for now
    return _future_expose_api(
        func,
        to_json=False,
        user_required=False,
        user_or_session_required=False,
        handle_jsonp=False
    )
