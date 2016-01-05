
from galaxy.util import is_uuid


def directory_hash_id( id ):
    """

    >>> directory_hash_id( 100 )
    ['000']
    >>> directory_hash_id( "90000" )
    ['090']
    >>> directory_hash_id("777777777")
    ['000', '777', '777']
    >>> directory_hash_id("135ee48a-4f51-470c-ae2f-ce8bd78799e6")
    ['1', '3', '5']
    """
    s = str( id )
    l = len( s )
    # Shortcut -- ids 0-999 go under ../000/
    if l < 4:
        return [ "000" ]
    if not is_uuid(s):
        # Pad with zeros until a multiple of three
        padded = ( ( 3 - len( s ) % 3 ) * "0" ) + s
        # Drop the last three digits -- 1000 files per directory
        padded = padded[:-3]
        # Break into chunks of three
        return [ padded[ i * 3 : (i + 1 ) * 3 ] for i in range( len( padded ) // 3 ) ]
    else:
        # assume it is a UUID
        return list(iter(s[0:3]))
