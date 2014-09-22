from __future__ import absolute_import

__all__ = [ "dumps", "loads", "safe_dumps", "json_fix", "validate_jsonrpc_request", "validate_jsonrpc_response", "jsonrpc_request", "jsonrpc_response" ]

import copy
import collections
import json
import logging
import math
import random
import string

dumps = json.dumps
loads = json.loads

log = logging.getLogger( __name__ )


def to_json_string(*args, **kwargs):
    log.warning("Using deprecated function to_json_string.")
    return json.dumps(*args, **kwargs)


def from_json_string(*args, **kwargs):
    log.warning("Using deprecated function from_json_string.")
    return json.loads(*args, **kwargs)


def json_fix( val ):
    if isinstance( val, list ):
        return [ json_fix( v ) for v in val ]
    elif isinstance( val, dict ):
        return dict( [ ( json_fix( k ), json_fix( v ) ) for ( k, v ) in val.iteritems() ] )
    elif isinstance( val, unicode ):
        return val.encode( "utf8" )
    else:
        return val


def swap_inf_nan( val ):
    """
    This takes an arbitrary object and preps it for jsonifying safely, templating Inf/NaN.
    """
    if isinstance(val, basestring):
        # basestring first, because it's a sequence and would otherwise get caught below.
        return val
    elif isinstance( val, collections.Sequence ):
        return [ swap_inf_nan( v ) for v in val ]
    elif isinstance( val, collections.Mapping ):
        return dict( [ ( swap_inf_nan( k ), swap_inf_nan( v ) ) for ( k, v ) in val.iteritems() ] )
    elif isinstance(val, float):
        if math.isnan(val):
            return "__NaN__"
        elif val == float("inf"):
            return "__Infinity__"
        elif val == float("-inf"):
            return "__-Infinity__"
    else:
        return val


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
        obj = swap_inf_nan(copy.deepcopy(args[0]))
        dumped = json.dumps(obj, allow_nan=False, **kwargs)
    return dumped


# Methods for handling JSON-RPC

def validate_jsonrpc_request( request, regular_methods, notification_methods ):
    try:
        request = loads( request )
    except Exception, e:
        return False, request, jsonrpc_response( id=None,
                                                 error=dict( code=-32700,
                                                             message='Parse error',
                                                             data=str( e ) ) )
    try:
        assert 'jsonrpc' in request, \
            'This server requires JSON-RPC 2.0 and no "jsonrpc" member was sent with the Request object as per the JSON-RPC 2.0 Specification.'
        assert request['jsonrpc'] == '2.0', \
            'Requested JSON-RPC version "%s" != required version "2.0".' % request['jsonrpc']
        assert 'method' in request, 'No "method" member was sent with the Request object'
    except AssertionError, e:
        return False, request, jsonrpc_response( request=request,
                                                 error=dict( code=-32600,
                                                             message='Invalid Request',
                                                             data=str( e ) ) )
    try:
        assert request['method'] in ( regular_methods + notification_methods )
    except AssertionError, e:
        return False, request, jsonrpc_response( request=request,
                                                 error=dict( code=-32601,
                                                             message='Method not found',
                                                             data='Valid methods are: %s' % ', '.join( regular_methods + notification_methods ) ) )
    try:
        if request['method'] in regular_methods:
            assert 'id' in request, 'No "id" member was sent with the Request object and the requested method "%s" is not a notification method' % request['method']
    except AssertionError, e:
        return False, request, jsonrpc_response( request=request,
                                                 error=dict( code=-32600,
                                                             message='Invalid Request',
                                                             data=str( e ) ) )
    return True, request, None


def validate_jsonrpc_response( response, id=None ):
    try:
        response = loads( response )
    except Exception, e:
        log.error( 'Response was not valid JSON: %s' % str( e ) )
        log.debug( 'Response was: %s' % response )
        return False, response
    try:
        assert 'jsonrpc' in response, \
            'This server requires JSON-RPC 2.0 and no "jsonrpc" member was sent with the Response object as per the JSON-RPC 2.0 Specification.'
        assert ( 'result' in response or 'error' in response ), \
            'Neither of "result" or "error" members were sent with the Response object.'
        if 'error' in response:
            assert int( response['error']['code'] ), \
                'The "code" member of the "error" object in the Response is missing or not an integer.'
            assert 'message' in response, \
                'The "message" member of the "error" object in the Response is missing.'
    except Exception, e:
        log.error( 'Response was not valid JSON-RPC: %s' % str( e ) )
        log.debug( 'Response was: %s' % response )
        return False, response
    if id is not None:
        try:
            assert 'id' in response and response['id'] == id
        except Exception, e:
            log.error( 'The response id "%s" does not match the request id "%s"' % ( response['id'], id ) )
            return False, response
    return True, response


def jsonrpc_request( method, params=None, id=None, jsonrpc='2.0' ):
    if method is None:
        log.error( 'jsonrpc_request(): "method" parameter cannot be None' )
        return None
    request = dict( jsonrpc=jsonrpc, method=method )
    if params:
        request['params'] = params
    if id is not None and id is True:
        request['id'] = ''.join( [ random.choice( string.hexdigits ) for i in range( 16 ) ] )
    elif id is not None:
        request['id'] = id
    return request


def jsonrpc_response( request=None, id=None, result=None, error=None, jsonrpc='2.0' ):
    if result:
        rval = dict( jsonrpc=jsonrpc, result=result )
    elif error:
        rval = dict( jsonrpc=jsonrpc, error=error )
    else:
        msg = 'jsonrpc_response() called with out a "result" or "error" parameter'
        log.error( msg )
        rval = dict( jsonrpc=jsonrpc, error=msg )
    if id is not None:
        rval['id'] = id
    elif request is not None and 'id' in request:
        rval['id'] = request['id']
    return rval
