import binascii
import json
import logging
from galaxy import eggs
from galaxy.util.hash_util import hmac_new
from galaxy.util.json import json_fix

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
    except Exception, e:
        pass
    if values is not None:
        try:
            return json_fix( values )
        except Exception, e:
            log.debug( "Fixing decoded json values '%s' from tool shed threw exception: %s" % ( str( values ), str( e ) ) )
            fixed_values = values
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
