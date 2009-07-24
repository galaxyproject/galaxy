import pkg_resources

pkg_resources.require( "WebHelpers" )
from webhelpers import *

from datetime import datetime

def time_ago( x ):
    return date.distance_of_time_in_words( x, datetime.utcnow() )
    
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
    """
    return "\n".join( [ stylesheet_link_tag( "/static/style/" + name + ".css" ) for name in args ] )
        
def js( *args ):
    """
    Take a list of javascript names (no extension) and return appropriate
    string of script tags.
    """
    return "\n".join( [ javascript_include_tag( "/static/scripts/" + name + ".js" ) for name in args ] )