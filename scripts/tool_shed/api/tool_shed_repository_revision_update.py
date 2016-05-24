#!/usr/bin/env python
"""
PUT/update script to update appropriate values in a repository_metadata table record in the Tool Shed.

usage: tool_shed_repository_revision_update.py key url key1=value1 key2=value2 ...
"""

import json
import sys

from common import update

data = {}
for key, value in [ kwarg.split( '=', 1 ) for kwarg in sys.argv[ 3: ] ]:
    """
    This example script will properly handle updating the value of one or more of the following RepositoryMetadata attributes:
    tools_functionally_correct, do_not_test, tool_test_results
    """
    if key in [ 'tools_functionally_correct', 'do_not_test' ]:
        if str( value ).lower() in [ 'true', 'yes', 'on' ]:
            new_value = True
        else:
            new_value = False
    elif key in [ 'tool_test_results' ]:
        new_value = json.loads( value )
    else:
        new_value = str( value )
    data[ key ] = new_value

update( sys.argv[ 1 ], sys.argv[ 2 ], data )
