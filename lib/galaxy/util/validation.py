""" Module for validation of incoming inputs.

TODO: Refactor BaseController references to similar methods to use this module.
"""
from galaxy import exceptions
from galaxy.util.sanitize_html import sanitize_html


def validate_and_sanitize_basestring( key, val ):
    if not isinstance( val, basestring ):
            raise exceptions.RequestParameterInvalidException( '%s must be a string or unicode: %s'
                                                               % ( key, str( type( val ) ) ) )
    return unicode( sanitize_html( val, 'utf-8', 'text/html' ), 'utf-8' )


def validate_and_sanitize_basestring_list( key, val ):
    try:
        assert isinstance( val, list )
        return [ unicode( sanitize_html( t, 'utf-8', 'text/html' ), 'utf-8' ) for t in val ]
    except ( AssertionError, TypeError ):
        raise exceptions.RequestParameterInvalidException( '%s must be a list of strings: %s'
                                                           % ( key, str( type( val ) ) ) )


def validate_boolean( key, val ):
    if not isinstance( val, bool ):
        raise exceptions.RequestParameterInvalidException( '%s must be a boolean: %s'
                                                           % ( key, str( type( val ) ) ) )
    return val


#TODO:
#def validate_integer( self, key, val, min, max ):
#def validate_float( self, key, val, min, max ):
#def validate_number( self, key, val, min, max ):
#def validate_genome_build( self, key, val ):
