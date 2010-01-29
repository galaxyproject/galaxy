import pkg_resources

pkg_resources.require( "WebHelpers" )
from webhelpers import *

from galaxy.util.json import to_json_string
from datetime import datetime, timedelta
import hashlib

# If the date is more than one week ago, then display the actual date instead of in words
def time_ago( x ):
    delta = timedelta(weeks=1)
    
    if (datetime.utcnow() - x) > delta: # Greater than a week difference
        return x.strftime("%b %d, %Y")
    else:   
        return date.distance_of_time_in_words( x, datetime.utcnow() ) + " ago"
    
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
    
    TODO: This has a hardcoded "?v=2" to defeat caching. This should be done
          in a better way.
    """
    return "\n".join( [ stylesheet_link_tag( "/static/style/" + name + ".css?v=2" ) for name in args ] )
        
def js( *args ):
    """
    Take a list of javascript names (no extension) and return appropriate
    string of script tags.

    TODO: This has a hardcoded "?v=2" to defeat caching. This should be done
          in a better way.
    """
    return "\n".join( [ javascript_include_tag( "/static/scripts/" + name + ".js?v=2" ) for name in args ] )
    
# Hashes

def md5( s ):
    """
    Return hex encoded md5 hash of string s
    """
    m = hashlib.md5()
    m.update( s )
    return m.hexdigest()