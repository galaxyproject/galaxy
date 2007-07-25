#!/usr/bin/env python2.4
#Dan Blankenberg

import sys
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf

def __main__():
    output_name = sys.argv.pop(1)
    input_name = sys.argv.pop(1)
    out = open(output_name,'w')
    count = 0
    for maf in bx.align.maf.Reader( open(input_name, 'r') ):
        for c in maf.components:
            spec, chrom = bx.align.maf.src_split( c.src )
            if not spec or not chrom:
                    spec = chrom = c.src
            out.write(">"+c.src+"("+c.strand+"):"+str(c.start)+"-"+str(c.end)+"|"+spec+"_"+str(count)+"\n")
            out.write(c.text+"\n")
        out.write("\n")
        count += 1
    out.close()
    print "%i MAF blocks converted to FASTA." % (count)


if __name__ == "__main__": __main__()
