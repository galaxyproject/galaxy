import os
from galaxy import config

# This silliness is needed for py2.4 compatibility
try:
    from hashlib import sha1 as sha
except:
    from sha import new as sha

class BaseCache( object ):
    """
    Base/Abstract Cache for dataset indices.
    """
    pass
