import sys, logging
using_24 = sys.version_info[:2] < ( 2, 5 )
if using_24:
    import sha
else:
    import hashlib
import hmac

log = logging.getLogger( __name__ )

"""
Utility functions for bi-directional Python version compatibility.  Python 2.5
introduced hashlib which replaced sha in Python 2.4 and previous versions.
"""
def new_secure_hash( text_type=None ):
    if using_24:
        if text_type:
            return sha.new( text_type ).hexdigest()
        return sha.new()
    else:
        if text_type:
            return hashlib.sha1( text_type ).hexdigest()
        return hashlib.sha1()
def hmac_new( key, value ):
    if using_24:
        return hmac.new( key, value, sha ).hexdigest()
    else:
        return hmac.new( key, value, hashlib.sha1 ).hexdigest()
