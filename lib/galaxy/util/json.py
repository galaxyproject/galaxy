import copy
import json
import logging
import math
import random
import string
from collections.abc import (
    Iterable,
    Mapping,
    Sequence,
)


from ..util import unicodify

__all__ = ("safe_dumps", "validate_jsonrpc_request", "validate_jsonrpc_response", "jsonrpc_request", "jsonrpc_response")

log = logging.getLogger(__name__)

to_json_string = json.dumps
from_json_string = json.loads


def swap_inf_nan(val):
    """
    This takes an arbitrary object and preps it for jsonifying safely, templating Inf/NaN.
    """
    if isinstance(val, str):
        # basestring first, because it's a sequence and would otherwise get caught below.
        return val
    elif isinstance(val, Sequence):
        return [swap_inf_nan(v) for v in val]
    elif isinstance(val, Mapping):
        return {swap_inf_nan(k): swap_inf_nan(v) for (k, v) in val.items()}
    elif isinstance(val, float):
        if math.isnan(val):
            return "__NaN__"
        elif val == float("inf"):
            return "__Infinity__"
        elif val == float("-inf"):
            return "__-Infinity__"
        else:
            return val
    else:
        return val


def safe_loads(arg):
    """
    This is a wrapper around loads that returns the parsed value instead of
    raising a value error. It also avoids autoconversion of non-iterables
    i.e numeric and boolean values.
    """
    try:
        loaded = json.loads(arg)
        if loaded is not None and not isinstance(loaded, Iterable):
            loaded = arg
    except (TypeError, ValueError):
        loaded = copy.deepcopy(arg)
    return loaded


def safe_dumps(*args, **kwargs):
    """
    This is a wrapper around dumps that encodes Infinity and NaN values.  It's a
    fairly rare case (which will be low in request volume).  Basically, we tell
    json.dumps to blow up if it encounters Infinity/NaN, and we 'fix' it before
    re-encoding.
    """
    try:
        dumped = json.dumps(*args, allow_nan=False, **kwargs)
    except ValueError:
        obj = swap_inf_nan(args[0])
        dumped = json.dumps(obj, allow_nan=False, **kwargs)
    if kwargs.get('escape_closing_tags', True):
        return dumped.replace('</', '<\\/')
    return dumped


def safe_dumps_formatted(obj):
    """Attempt to format an object for display.

    If serialization fails, the object's string representation will be returned instead.
    """
    try:
        return safe_dumps(obj, sort_keys=True, indent=4, separators=(',', ': '))
    except TypeError:
        log.warning("JSON serialization failed for object: %s", str(obj))
        return str(obj)


# Methods for handling JSON-RPC

def validate_jsonrpc_request(request, regular_methods, notification_methods):
    try:
        request = json.loads(request)
    except Exception as e:
        return False, request, jsonrpc_response(id=None,
                                                error=dict(code=-32700,
                                                           message='Parse error',
                                                           data=unicodify(e)))
    try:
        assert 'jsonrpc' in request, \
            'This server requires JSON-RPC 2.0 and no "jsonrpc" member was sent with the Request object as per the JSON-RPC 2.0 Specification.'
        assert request['jsonrpc'] == '2.0', \
            f"Requested JSON-RPC version \"{request['jsonrpc']}\" != required version \"2.0\"."
        assert 'method' in request, 'No "method" member was sent with the Request object'
    except AssertionError as e:
        return False, request, jsonrpc_response(request=request,
                                                error=dict(code=-32600,
                                                           message='Invalid Request',
                                                           data=unicodify(e)))
    try:
        assert request['method'] in (regular_methods + notification_methods)
    except AssertionError:
        return False, request, jsonrpc_response(request=request,
                                                error=dict(code=-32601,
                                                           message='Method not found',
                                                           data=f"Valid methods are: {', '.join(regular_methods + notification_methods)}"))
    try:
        if request['method'] in regular_methods:
            assert 'id' in request, f"No \"id\" member was sent with the Request object and the requested method \"{request['method']}\" is not a notification method"
    except AssertionError as e:
        return False, request, jsonrpc_response(request=request,
                                                error=dict(code=-32600,
                                                           message='Invalid Request',
                                                           data=unicodify(e)))
    return True, request, None


def validate_jsonrpc_response(response, id=None):
    try:
        response = json.loads(response)
    except Exception as e:
        log.error('Response was not valid JSON: %s', unicodify(e))
        log.debug('Response was: %s', response)
        return False, response
    try:
        assert 'jsonrpc' in response, \
            'This server requires JSON-RPC 2.0 and no "jsonrpc" member was sent with the Response object as per the JSON-RPC 2.0 Specification.'
        assert ('result' in response or 'error' in response), \
            'Neither of "result" or "error" members were sent with the Response object.'
        if 'error' in response:
            assert int(response['error']['code']), \
                'The "code" member of the "error" object in the Response is missing or not an integer.'
            assert 'message' in response, \
                'The "message" member of the "error" object in the Response is missing.'
    except Exception:
        log.exception('Response was not valid JSON-RPC')
        log.debug(f'Response was: {response}')
        return False, response
    if id is not None:
        try:
            assert 'id' in response and response['id'] == id
        except Exception:
            log.error(f"The response id \"{response['id']}\" does not match the request id \"{id}\"")
            return False, response
    return True, response


def jsonrpc_request(method, params=None, id=None, jsonrpc='2.0'):
    if method is None:
        log.error('jsonrpc_request(): "method" parameter cannot be None')
        return None
    request = dict(jsonrpc=jsonrpc, method=method)
    if params:
        request['params'] = params
    if id is not None and id is True:
        request['id'] = ''.join(random.choice(string.hexdigits) for i in range(16))
    elif id is not None:
        request['id'] = id
    return request


def jsonrpc_response(request=None, id=None, result=None, error=None, jsonrpc='2.0'):
    if result:
        rval = dict(jsonrpc=jsonrpc, result=result)
    elif error:
        rval = dict(jsonrpc=jsonrpc, error=error)
    else:
        msg = 'jsonrpc_response() called with out a "result" or "error" parameter'
        log.error(msg)
        rval = dict(jsonrpc=jsonrpc, error=msg)
    if id is not None:
        rval['id'] = id
    elif request is not None and 'id' in request:
        rval['id'] = request['id']
    return rval
