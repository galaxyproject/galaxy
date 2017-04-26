#!/usr/bin/env python

from __future__ import division

import sys

from bx.arrays.array_tree import array_tree_dict_from_reader, FileArrayTreeDict

BLOCK_SIZE = 100


class BedGraphReader:
    def __init__( self, f ):
        self.f = f

    def __iter__( self ):
        return self

    def next( self ):
        while True:
            line = self.f.readline()
            if not line:
                raise StopIteration()
            if line.isspace():
                continue
            if line[0] == "#":
                continue
            if line[0].isalpha():
                if line.startswith( "track" ) or line.startswith( "browser" ):
                    continue

                feature = line.strip().split()
                chrom = feature[0]
                chrom_start = int(feature[1])
                chrom_end = int(feature[2])
                score = float(feature[3])
                return chrom, chrom_start, chrom_end, None, score


def main():
    input_fname = sys.argv[1]
    out_fname = sys.argv[2]

    reader = BedGraphReader( open( input_fname ) )

    # Fill array from reader
    d = array_tree_dict_from_reader( reader, {}, block_size=BLOCK_SIZE )

    for array_tree in d.itervalues():
        array_tree.root.build_summary()

    FileArrayTreeDict.dict_to_file( d, open( out_fname, "w" ) )


if __name__ == "__main__":
    main()
