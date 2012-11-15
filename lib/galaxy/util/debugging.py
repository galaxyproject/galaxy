
import inspect
import pprint

import logging
log = logging.getLogger( __name__ )

def stack_trace_string( max_depth=None, line_format="{index}:{file}:{function}:{line}" ):
    """
    Returns a string representation of the current stack.

    :param depth: positive integer to control how many levels of the stack are
    returned. max_depth=None returns the entire stack (default).
    """
    stack_list = []
    for index, caller in enumerate( inspect.stack() ):
        # don't include this function
        if index == 0: continue
        if max_depth and index > max_depth: break

        caller_data = {
            'index'     : str( index ),
            'file'      : caller[1],
            'function'  : caller[3],
            'line'      : caller[2]
        }
        stack_list.append( line_format.format( **caller_data ) )

    return '\n'.join( stack_list )
