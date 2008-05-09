
__all__ = [ "to_json_string", "from_json_string", "json_fix"]

import pkg_resources
pkg_resources.require( "simplejson" )

import simplejson

to_json_string = simplejson.dumps
from_json_string = simplejson.loads

def json_fix( val ):
    if isinstance( val, list ):
        return [ json_fix( v ) for v in val ]
    elif isinstance( val, dict ):
        return dict( [ ( json_fix( k ), json_fix( v ) ) for ( k, v ) in val.iteritems() ] )
    elif isinstance( val, unicode ):
        return val.encode( "utf8" )
    else:
        return val