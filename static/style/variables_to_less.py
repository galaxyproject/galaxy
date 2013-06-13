#!/usr/bin/env python

"""
Read ini-like variable definition and output in less format.
"""

import sys

def main():
    # Read variable definitions from a (sorta) ini file
    context = dict()
    for line in sys.stdin:
        if line.startswith( '#' ):
            continue
        key, value = line.rstrip("\r\n").split( '=' )
        if value.startswith( '"' ) and value.endswith( '"' ):
            value = value[1:-1]
        if value == "-":
            continue
        print "@%s: %s;" % ( key, value ) 

if __name__ == "__main__":
    main()
