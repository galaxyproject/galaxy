"""
Unit test utilities.
"""

import os
import sys
import logging
import textwrap

def set_up_filelogger( logname, level=logging.DEBUG ):
    """
    Sets up logging to a file named `logname`
    (removing it first if it already exists).

    Usable with 'nosetests' to get logging msgs from failed tests
    (no logfile created).
    Usable with 'nosetests --nologcapture' to get logging msgs for all tests
    (in logfile).
    """
    if os.path.exists( logname ): os.unlink( logname )
    logging.basicConfig( filename=logname, level=logging.DEBUG )
    return logging

def add_galaxy_lib_to_path( this_dir_relative_to_root ):
    """
    Adds `<galaxy>/lib` to `sys.path` given the scripts directory relative
    to `<galaxy>`.
    .. example::
        utility.add_galaxy_lib_to_path( '/test/unit/datatypes/dataproviders' )
    """
    glx_lib = os.path.join( os.getcwd().replace( this_dir_relative_to_root, '' ), 'lib' )
    sys.path.append( glx_lib )

def clean_multiline_string( multiline_string, sep='\n' ):
    """
    Dedent, split, remove first and last empty lines, rejoin.
    """
    multiline_string = textwrap.dedent( multiline_string )
    string_list = multiline_string.split( sep )
    if not string_list[0]:
        string_list = string_list[1:]
    if not string_list[-1]:
        string_list = string_list[:-1]
    #return '\n'.join( docstrings )
    return ''.join([ ( s + '\n' ) for s in  string_list ])
