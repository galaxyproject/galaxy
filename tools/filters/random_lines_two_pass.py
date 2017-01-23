#!/usr/bin/env python
# Dan Blankenberg
# Selects N random lines from a file and outputs to another file, maintaining original line order
# allows specifying a seed
# does two passes to determine line offsets/count, and then to output contents
from __future__ import print_function

import optparse
import random


def get_random_by_subtraction( line_offsets, num_lines ):
    while len( line_offsets ) > num_lines:
        del line_offsets[ random.randint( 0, len( line_offsets ) - 1 ) ]
    return line_offsets


def get_random_by_sample( line_offsets, num_lines ):
    line_offsets = random.sample( line_offsets, num_lines )
    line_offsets.sort()
    return line_offsets


def get_random( line_offsets, num_lines ):
    if num_lines > ( len( line_offsets ) / 2 ):
        return get_random_by_subtraction( line_offsets, num_lines )
    else:
        return get_random_by_sample( line_offsets, num_lines )


def __main__():
    parser = optparse.OptionParser()
    parser.add_option( '-s', '--seed', dest='seed', action='store', type="string", default=None, help='Set the random seed.' )
    (options, args) = parser.parse_args()

    assert len( args ) == 3, "Invalid command line specified."

    input = open( args[0], 'rb' )
    output = open( args[1], 'wb' )
    num_lines = int( args[2] )
    assert num_lines > 0, "You must select at least one line."

    if options.seed is not None:
        random.seed( options.seed )

    # get line offsets
    line_offsets = []
    teller = input.tell
    readliner = input.readline
    appender = line_offsets.append
    while True:
        offset = teller()
        if readliner():
            appender( offset )
        else:
            break

    total_lines = len( line_offsets )
    assert num_lines <= total_lines, "Error: asked to select more lines (%i) than there were in the file (%i)." % ( num_lines, total_lines )

    # get random line offsets
    line_offsets = get_random( line_offsets, num_lines )

    # write out random lines
    seeker = input.seek
    writer = output.write
    for line_offset in line_offsets:
        seeker( line_offset )
        writer( readliner() )
    input.close()
    output.close()
    print("Kept %i of %i total lines." % ( num_lines, total_lines ))
    if options.seed is not None:
        print('Used random seed of "%s".' % options.seed)


if __name__ == "__main__":
    __main__()
