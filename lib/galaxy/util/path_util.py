"""This file is here to solve any path mannipulation"""

import os


# TODO: Check if this extracted function from galaxy/config.py and tool_shed/config.py is used somewhere else
def resolve_path( path, root ):
    """If 'path' is relative make absolute by prepending 'root'"""
    if not( os.path.isabs( path ) ):
        path = os.path.join( root, path )
    return path
