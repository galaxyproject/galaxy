"""
Unit test utilities.
"""
import textwrap


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
    # return '\n'.join( docstrings )
    return ''.join([ ( s + '\n' ) for s in string_list ])


__all__ = (
    "clean_multiline_string",
)
