"""
Utility functions for bi-directional Python version compatibility.  Python 2.5
introduced hashlib which replaced sha in Python 2.4 and previous versions.
"""
import hashlib
import hmac
import logging

log = logging.getLogger( __name__ )

sha1 = hashlib.sha1
sha = sha1
md5 = hashlib.md5


def md5_hash_file(path):
    """
    Return a md5 hashdigest for a file.
    """
    hasher = hashlib.md5()
    with open(path, 'rb') as afile:
        buf = afile.read()
        hasher.update(buf)
        return hasher.hexdigest()


def new_secure_hash( text_type=None ):
    """
    Returns either a sha1 hash object (if called with no arguments), or a
    hexdigest of the sha1 hash of the argument `text_type`.
    """
    if text_type:
        return sha1( text_type ).hexdigest()
    else:
        return sha1()


def hmac_new( key, value ):
    return hmac.new( key, value, sha ).hexdigest()


def is_hashable( value ):
    try:
        hash( value )
    except:
        return False
    return True


__all__ = ('md5', 'hashlib', 'sha1', 'sha', 'new_secure_hash', 'hmac_new', 'is_hashable')
