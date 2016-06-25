import binascii
import json
import logging

from galaxy.util.hash_util import hmac_new

log = logging.getLogger( __name__ )

encoding_sep = '__esep__'
encoding_sep2 = '__esepii__'


def tool_shed_decode( value ):
    # Extract and verify hash
    a, b = value.split( ":" )
    value = binascii.unhexlify( b )
    test = hmac_new( 'ToolShedAndGalaxyMustHaveThisSameKey', value )
    assert a == test
    # Restore from string
    values = None
    try:
        values = json.loads( value )
    except Exception:
        pass
    if values is None:
        values = value
    return values


def tool_shed_encode( val ):
    if isinstance( val, dict ) or isinstance( val, list ):
        value = json.dumps( val )
    else:
        value = val
    a = hmac_new( 'ToolShedAndGalaxyMustHaveThisSameKey', value )
    b = binascii.hexlify( value )
    return "%s:%s" % ( a, b )
