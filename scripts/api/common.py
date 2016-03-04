"""
Common methods used by the API sample scripts.
"""
from __future__ import print_function

import json
import logging
import sys

from Crypto.Cipher import Blowfish
from six.moves.urllib.error import HTTPError
from six.moves.urllib.request import Request, urlopen

log = logging.getLogger( __name__ )


def make_url( api_key, url, args=None ):
    """
    Adds the API Key to the URL if it's not already there.
    """
    if args is None:
        args = []
    argsep = '&'
    if '?' not in url:
        argsep = '?'
    if '?key=' not in url and '&key=' not in url:
        args.insert( 0, ( 'key', api_key ) )
    return url + argsep + '&'.join( [ '='.join( t ) for t in args ] )


def get( api_key, url ):
    """
    Do the actual GET.
    """
    url = make_url( api_key, url )
    try:
        return json.loads( urlopen( url ).read() )
    except ValueError as e:
        print("URL did not return JSON data: %s" % e)
        sys.exit(1)


def post( api_key, url, data ):
    """
    Do the actual POST.
    """
    url = make_url( api_key, url )
    req = Request( url, headers={ 'Content-Type': 'application/json' }, data=json.dumps( data ) )
    return json.loads( urlopen( req ).read() )


def put( api_key, url, data ):
    """
    Do the actual PUT
    """
    url = make_url( api_key, url )
    req = Request( url, headers={ 'Content-Type': 'application/json' }, data=json.dumps( data ))
    req.get_method = lambda: 'PUT'
    return json.loads( urlopen( req ).read() )


def __del( api_key, url, data ):
    """
    Do the actual DELETE
    """
    url = make_url( api_key, url )
    req = Request( url, headers={ 'Content-Type': 'application/json' }, data=json.dumps( data ))
    req.get_method = lambda: 'DELETE'
    return json.loads( urlopen( req ).read() )


def display( api_key, url, return_formatted=True ):
    """
    Sends an API GET request and acts as a generic formatter for the JSON response.
    """
    try:
        r = get( api_key, url )
    except HTTPError as e:
        print(e)
        print(e.read( 1024 ))  # Only return the first 1K of errors.
        sys.exit( 1 )
    if not return_formatted:
        return r
    elif type( r ) == list:
        # Response is a collection as defined in the REST style.
        print('Collection Members')
        print('------------------')
        for n, i in enumerate(r):
            # All collection members should have a name in the response.
            # url is optional
            if 'url' in i:
                print('#%d: %s' % (n + 1, i.pop( 'url' ) ))
            if 'name' in i:
                print('  name: %s' % i.pop( 'name' ))
            for k, v in i.items():
                print('  %s: %s' % ( k, v ))
        print('')
        print('%d element(s) in collection' % len( r ))
    elif type( r ) == dict:
        # Response is an element as defined in the REST style.
        print('Member Information')
        print('------------------')
        for k, v in r.items():
            print('%s: %s' % ( k, v ))
    elif type( r ) == str:
        print(r)
    else:
        print('response is unknown type: %s' % type( r ))


def submit( api_key, url, data, return_formatted=True ):
    """
    Sends an API POST request and acts as a generic formatter for the JSON response.
    'data' will become the JSON payload read by Galaxy.
    """
    try:
        r = post( api_key, url, data )
    except HTTPError as e:
        if return_formatted:
            print(e)
            print(e.read( 1024 ))
            sys.exit( 1 )
        else:
            return 'Error. ' + str( e.read( 1024 ) )
    if not return_formatted:
        return r
    print('Response')
    print('--------')
    if type( r ) == list:
        # Currently the only implemented responses are lists of dicts, because
        # submission creates some number of collection elements.
        for i in r:
            if type( i ) == dict:
                if 'url' in i:
                    print(i.pop( 'url' ))
                else:
                    print('----')
                if 'name' in i:
                    print('  name: %s' % i.pop( 'name' ))
                for k, v in i.items():
                    print('  %s: %s' % ( k, v ))
            else:
                print(i)
    else:
        print(r)


def update( api_key, url, data, return_formatted=True ):
    """
    Sends an API PUT request and acts as a generic formatter for the JSON response.
    'data' will become the JSON payload read by Galaxy.
    """
    try:
        r = put( api_key, url, data )
    except HTTPError as e:
        if return_formatted:
            print(e)
            print(e.read( 1024 ))
            sys.exit( 1 )
        else:
            return 'Error. ' + str( e.read( 1024 ) )
    if not return_formatted:
        return r
    print('Response')
    print('--------')
    print(r)


def delete( api_key, url, data, return_formatted=True ):
    """
    Sends an API DELETE request and acts as a generic formatter for the JSON response.
    'data' will become the JSON payload read by Galaxy.
    """
    try:
        r = __del( api_key, url, data )
    except HTTPError as e:
        if return_formatted:
            print(e)
            print(e.read( 1024 ))
            sys.exit( 1 )
        else:
            return 'Error. ' + str( e.read( 1024 ) )
    if not return_formatted:
        return r
    print('Response')
    print('--------')
    print(r)


def encode_id( config_id_secret, obj_id ):
    """
    utility method to encode ID's
    """
    id_cipher = Blowfish.new( config_id_secret )
    # Convert to string
    s = str( obj_id )
    # Pad to a multiple of 8 with leading "!"
    s = ( "!" * ( 8 - len(s) % 8 ) ) + s
    # Encrypt
    return id_cipher.encrypt( s ).encode( 'hex' )
