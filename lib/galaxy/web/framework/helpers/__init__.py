import pkg_resources

pkg_resources.require( "WebHelpers" )
from webhelpers import *

from galaxy.util.json import to_json_string
from galaxy.util import hash_util
from datetime import datetime, timedelta

from cgi import escape

# If the date is more than one week ago, then display the actual date instead of in words
def time_ago( x ):
    delta = timedelta(weeks=1)
    
    if (datetime.utcnow() - x) > delta: # Greater than a week difference
        return x.strftime("%b %d, %Y")
    else:   
        return date.distance_of_time_in_words( x, datetime.utcnow() ).replace("about", "~") + " ago"
    
def iff( a, b, c ):
    if a:
        return b
    else:
        return c
    
# Quick helpers for static content

def css( *args ):
    """
    Take a list of stylesheet names (no extension) and return appropriate string
    of link tags.
    
    TODO: This has a hardcoded "?v=X" to defeat caching. This should be done
          in a better way.
    """
    return "\n".join( [ stylesheet_link_tag( "/static/style/" + name + ".css?v=3" ) for name in args ] )
        
def js( *args ):
    """
    Take a list of javascript names (no extension) and return appropriate
    string of script tags.

    TODO: This has a hardcoded "?v=X" to defeat caching. This should be done
          in a better way.
    """
    return "\n".join( [ javascript_include_tag( "/static/scripts/" + name + ".js?v=8" ) for name in args ] )
    
# Hashes

def md5( s ):
    """
    Return hex encoded md5 hash of string s
    """
    m = hash_util.md5()
    m.update( s )
    return m.hexdigest()
    
# Unicode help

def to_unicode( a_string ):
    """ 
    Convert a string to unicode in utf-8 format; if string is already unicode,
    does nothing because string's encoding cannot be determined by introspection.
    """
    a_string_type = type ( a_string )
    if a_string_type is str:
        return unicode( a_string, 'utf-8' )
    elif a_string_type is unicode:
        return a_string
    