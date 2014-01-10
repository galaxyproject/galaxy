from pkg_resources import resource_string
from json import loads

# Error codes are provided as a convience to Galaxy API clients, but at this
# time they do represent part of the more stable interface. They can change
# without warning between releases.
UNKNOWN_ERROR_MESSAGE = "Unknown error occurred while processing request."


class ErrorCode( object ):

    def __init__( self, code, default_error_message ):
        self.code = code
        self.default_error_message = default_error_message or UNKNOWN_ERROR_MESSAGE

    def __str__( self ):
        return str( self.default_error_message )

    def __int__( self ):
        return int( self.code )

    @staticmethod
    def from_dict( entry ):
        name = entry.get("name")
        code = entry.get("code")
        message = entry.get("message")
        return ( name, ErrorCode( code, message ) )

error_codes_json = resource_string( __name__, 'error_codes.json' )
for entry in loads( error_codes_json ):
    name, error_code_obj = ErrorCode.from_dict( entry )
    globals()[ name ] = error_code_obj
