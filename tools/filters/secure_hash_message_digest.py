#!/usr/bin/env python
# Dan Blankenberg
"""
A script for calculating secure hashes / message digests.
"""
import hashlib
import optparse

from galaxy.util.odict import odict

HASH_ALGORITHMS = [ 'md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512' ]
CHUNK_SIZE = 2 ** 20  # 1mb


def __main__():
    # Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-a', '--algorithm', dest='algorithms', action='append', type="string", help='Algorithms to use, eg. (md5, sha1, sha224, sha256, sha384, sha512)' )
    parser.add_option( '-i', '--input', dest='input', action='store', type="string", help='Input filename' )
    parser.add_option( '-o', '--output', dest='output', action='store', type="string", help='Output filename' )
    (options, args) = parser.parse_args()

    algorithms = odict()
    for algorithm in options.algorithms:
        assert algorithm in HASH_ALGORITHMS, "Invalid algorithm specified: %s" % ( algorithm )
        assert algorithm not in algorithms, "Specify each algorithm only once."
        algorithms[ algorithm ] = hashlib.new( algorithm )
    assert options.algorithms, "You must provide at least one algorithm."
    assert options.input, "You must provide an input filename."
    assert options.output, "You must provide an output filename."

    input = open( options.input )
    while True:
        chunk = input.read( CHUNK_SIZE )
        if chunk:
            for algorithm in algorithms.values():
                algorithm.update( chunk )
        else:
            break

    output = open( options.output, 'wb' )
    output.write( '#%s\n' % ( '\t'.join( algorithms.keys() ) ) )
    output.write( '%s\n' % ( '\t'.join( x.hexdigest() for x in algorithms.values() ) ) )
    output.close()


if __name__ == "__main__":
    __main__()
