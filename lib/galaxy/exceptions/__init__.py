"""
Custom exceptions for Galaxy
"""

class MessageException( Exception ):
    """
    Exception to make throwing errors from deep in controllers easier
    """
    def __init__( self, err_msg, type="info" ):
        self.err_msg = err_msg
        self.type = type

class ItemDeletionException( MessageException ):
    pass

class ItemAccessibilityException( MessageException ):
    pass

class ItemOwnershipException( MessageException ):
    pass

class ObjectNotFound( Exception ):
    """ Accessed object was not found """
    pass

class ObjectInvalid( Exception ):
    """ Accessed object store ID is invalid """
    pass
