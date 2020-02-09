#!/usr/bin/env python

from __future__ import division

import sys

from bx.arrays.array_tree import array_tree_dict_from_reader, FileArrayTreeDict
from bx.arrays.wiggle import WiggleReader

BLOCK_SIZE = 100


def main():

    input_fname = sys.argv[1]
    out_fname = sys.argv[2]

    with input(input_fname) as in_fh, open(out_fname, 'w') as out:
        reader = WiggleReader(in_fh)

        # Fill array from reader
        d = array_tree_dict_from_reader(reader, {}, block_size=BLOCK_SIZE)

        for array_tree in d.values():
            array_tree.root.build_summary()

        FileArrayTreeDict.dict_to_file(d, out)


if __name__ == "__main__":
    main()
