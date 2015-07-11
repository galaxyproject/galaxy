"""
Utility functions for bi-directional Python version compatibility.  Python 2.5
introduced hashlib which replaced sha in Python 2.4 and previous versions.
"""

import sys, logging

# Use hashlib module if for Python 2.5+, fall back on old sha and md5 modules
# sha1 requires explicit calls to new if also being passed to hmac (!)
try:
    import hashlib
    sha1 = hashlib.sha1
    sha = sha1
    md5 = hashlib.md5
except ImportError, e:
    from sha import new as sha1
    import sha
    from md5 import new as md5
import hmac

log = logging.getLogger( __name__ )

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
