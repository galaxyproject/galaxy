import pkg_resources

pkg_resources.require( "WebHelpers" )
from webhelpers import *

from galaxy.util.json import to_json_string
from galaxy.util import hash_util
from datetime import datetime, timedelta
import time

from cgi import escape

server_starttime = int(time.time())

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
    
# Smart string truncation
def truncate(content, length=100, suffix='...'):
    if len(content) <= length:
        return content
    else:
        return content[:length].rsplit(' ', 1)[0] + suffix
    
# Quick helpers for static content

def css( *args ):
    """
    Take a list of stylesheet names (no extension) and return appropriate string
    of link tags.
    
    Cache-bust with time that server started running on
    """
    return "\n".join( [ stylesheet_link_tag( "/static/style/" + name + ".css?v=%s" % server_starttime ) for name in args ] )
        
def js_helper( prefix, *args ):
    """
    Take a prefix and list of javascript names and return appropriate
    string of script tags.

    Cache-bust with time that server started running on
    """
    return "\n".join( [ javascript_include_tag( prefix + name + ".js?v=%s" % server_starttime ) for name in args ] )
    
def js( *args ):
    """
    Take a prefix and list of javascript names and return appropriate
    string of script tags.
    """
    return js_helper( '/static/scripts/', *args )
    
def templates( *args ):
    """
    Take a list of template names (no extension) and return appropriate
    string of script tags.
    """
    return js_helper( '/static/scripts/templates/compiled/', *args )
    
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
    