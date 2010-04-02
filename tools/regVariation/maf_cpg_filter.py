#!/usr/bin/env python
#Guruprasad Ananda
#Adapted from bx/scripts/maf_mask_cpg.py
"""
Mask out potential CpG sites from a maf. Restricted or inclusive definition
of CpG sites can be used. The total fraction masked is printed to stderr.

usage: %prog < input > output restricted
    -m, --mask=N: Character to use as mask ('?' is default)
"""

from galaxy import eggs
import pkg_resources 
pkg_resources.require( "bx-python" )
try:
    pkg_resources.require( "numpy" )
except:
    pass
import bx.align
import bx.align.maf
from bx.cookbook import doc_optparse
import sys
import bx.align.sitemask.cpg

assert sys.version_info[:2] >= ( 2, 4 )

def main():
    options, args = doc_optparse.parse( __doc__ )
    try:
        inp_file, out_file, sitetype, definition = args
        if options.mask:
            mask = int(options.mask)
        else:
            mask = 0
    except:
        print >> sys.stderr, "Tool initialization error."
        sys.exit()

    reader = bx.align.maf.Reader( open(inp_file, 'r') )
    writer = bx.align.maf.Writer( open(out_file,'w') )
    
    mask_chr_dict = {0:'#', 1:'$', 2:'^', 3:'*', 4:'?', 5:'N'}
    mask = mask_chr_dict[mask]
    
    if sitetype == "CpG":
        if int(definition) == 1:
            cpgfilter = bx.align.sitemask.cpg.Restricted( mask=mask )
            defn = "CpG-Restricted"
        else:
            cpgfilter = bx.align.sitemask.cpg.Inclusive( mask=mask )
            defn = "CpG-Inclusive"
    else:
        cpgfilter = bx.align.sitemask.cpg.nonCpG( mask=mask )
        defn = "non-CpG"
    cpgfilter.run( reader, writer.write )
    
    print "%2.2f percent bases masked; Mask character = %s, Definition = %s" %(float(cpgfilter.masked)/float(cpgfilter.total) * 100, mask, defn)

if __name__ == "__main__":
    main()
