import logging
import os

from galaxy.util import unicodify

from galaxy import eggs

eggs.require( 'markupsafe' )
import markupsafe

log = logging.getLogger( __name__ )

MAX_DISPLAY_SIZE = 32768

def remove_dir( dir ):
    """Attempt to remove a directory from disk."""
    if dir:
        if os.path.exists( dir ):
            try:
                shutil.rmtree( dir )
            except:
                pass

def size_string( raw_text, size=MAX_DISPLAY_SIZE ):
    """Return a subset of a string (up to MAX_DISPLAY_SIZE) translated to a safe string for display in a browser."""
    if raw_text and len( raw_text ) >= size:
        large_str = '\nFile contents truncated because file size is larger than maximum viewing size of %s\n' % util.nice_size( size )
        raw_text = '%s%s' % ( raw_text[ 0:size ], large_str )
    return raw_text or ''

def stringify( list ):
    if list:
        return ','.join( list )
    return ''

def strip_path( fpath ):
    """Attempt to strip the path from a file name."""
    if not fpath:
        return fpath
    try:
        file_path, file_name = os.path.split( fpath )
    except:
        file_name = fpath
    return file_name

def to_html_string( text ):
    """Translates the characters in text to an html string"""
    if text:
        try:
            text = unicodify( text )
        except UnicodeDecodeError, e:
            return "Error decoding string: %s" % str( e )
        text = unicode( markupsafe.escape( text ) )
        text = text.replace( '\n', '<br/>' )
        text = text.replace( '    ', '&nbsp;&nbsp;&nbsp;&nbsp;' )
        text = text.replace( ' ', '&nbsp;' )
    return text
