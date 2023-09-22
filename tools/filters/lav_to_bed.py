#!/usr/bin/env python
# Reads a LAV file and writes two BED files.
from __future__ import print_function

import sys

import bx.align.lav


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def main():
    try:
        lav_file = open(sys.argv[1])
        bed_file1 = open(sys.argv[2], "w")
        bed_file2 = open(sys.argv[3], "w")
    except Exception as e:
        stop_err(str(e))

    lavsRead = 0
    bedsWritten = 0
    species = {}
    # TODO: this is really bad since everything is read into memory.  Can we eliminate this tool?
    for lavBlock in bx.align.lav.Reader(lav_file):
        lavsRead += 1
        for c in lavBlock.components:
            spec, chrom = bx.align.lav.src_split(c.src)
            if bedsWritten < 1:
                if len(species) == 0:
                    species[spec] = bed_file1
                elif len(species) == 1:
                    species[spec] = bed_file2
                else:
                    continue  # this is a pairwise alignment...
            if spec in species:
                species[spec].write(
                    "%s\t%i\t%i\t%s_%s\t%i\t%s\n" % (chrom, c.start, c.end, spec, str(bedsWritten), 0, c.strand)
                )
        bedsWritten += 1

    for spec, file in species.items():
        print("#FILE\t%s\t%s" % (file.name, spec))

    lav_file.close()
    bed_file1.close()
    bed_file2.close()

    print("%d lav blocks read, %d regions written\n" % (lavsRead, bedsWritten))


if __name__ == "__main__":
    main()
