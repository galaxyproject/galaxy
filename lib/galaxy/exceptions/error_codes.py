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

# TODO: Guidelines for error message langauge?
UNKNOWN = ErrorCode(0, UNKNOWN_ERROR_MESSAGE)

USER_CANNOT_RUN_AS = ErrorCode(400001, "User does not have permissions to run jobs as another user.")
USER_INVALID_RUN_AS = ErrorCode(400002, "Invalid run_as request - run_as user does not exist.")
USER_INVALID_JSON = ErrorCode(400003, "Your request did not appear to be valid JSON, please consult the API documentation.")
USER_OBJECT_ATTRIBUTE_INVALID = ErrorCode(400004, "Attempted to create or update object with invalid attribute value.")
USER_OBJECT_ATTRIBUTE_MISSING = ErrorCode(400005, "Attempted to create object without required attribute.")
USER_SLUG_DUPLICATE = ErrorCode(400006, "Slug must be unique per user.")

USER_NO_API_KEY = ErrorCode(403001, "API Authentication Required for this request")
USER_CANNOT_ACCESS_ITEM = ErrorCode(403002, "User cannot access specified item.")
USER_DOES_NOT_OWN_ITEM = ErrorCode(403003, "User does not own specified item.")

USER_OBJECT_NOT_FOUND = ErrorCode(404001, "No such object not found.")
