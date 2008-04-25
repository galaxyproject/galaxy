#!/usr/bin/env python
#Reads a LAV file and writes two BED files.

import sys
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )
import bx.align.lav

assert sys.version_info[:2] >= ( 2, 4 )

def main():

    try:
        lav_file = open(sys.argv[1],'r')
        bed_file1 = open(sys.argv[2],'w')
        bed_file2 = open(sys.argv[3],'w')
    except:
        print >>sys.stderr,"Error with provided arguments"
        print >>sys.stderr,"Usage: python %s input_lav output_bed1 output_bed2" % sys.argv[0]
        sys.exit(0)
        
    lavsRead = bedsWritten = 0
    species = {}
    for lavBlock in bx.align.lav.Reader(lav_file):
        lavsRead += 1
        
        for c in lavBlock.components:
            spec,chrom = bx.align.lav.src_split( c.src )
            if bedsWritten < 1:
                if len(species)==0:
                    species[spec]=bed_file1
                elif len(species)==1:
                    species[spec]=bed_file2
                else:
                    continue #this is a pairwise alignment...
            if spec in species:
                species[spec].write("%s\t%i\t%i\t%s\t%i\t%s\n" % (chrom,c.start,c.end,spec+"_"+str(bedsWritten),0,c.strand))
        bedsWritten += 1


    for spec,file in species.items():
        print "#FILE\t%s\t%s" % (file.name, spec)
    
    lav_file.close()
    bed_file1.close()
    bed_file2.close()
    
    print "%d lav blocks read, %d regions written\n" % (lavsRead,bedsWritten)



if __name__ == "__main__": main()