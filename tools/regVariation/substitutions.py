#!/usr/bin/env python
#Guruprasad ANanda
"""
Fetches substitutions from pairwise alignments.
"""

from galaxy import eggs

from galaxy.tools.util import maf_utilities

import bx.align.maf
import sys

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


if len(sys.argv) < 3:
    stop_err("Incorrect number of arguments.")

inp_file = sys.argv[1]
out_file = sys.argv[2]
fout = open(out_file, 'w')

def fetchSubs(block):
    src1 = block.components[0].src
    sequence1 = block.components[0].text
    start1 = block.components[0].start
    end1 = block.components[0].end
    len1_withgap = len(sequence1)
    
    for seq in range (1, len(block.components)):
        src2 = block.components[seq].src
        sequence2 = block.components[seq].text
        start2 = block.components[seq].start
        end2 = block.components[seq].end
        sub_begin = None
        sub_end = None
        begin = False
        
        for nt in range(len1_withgap):
            if sequence1[nt] not in '-#$^*?' and sequence2[nt] not in '-#$^*?':  # Not a gap or masked character
                if sequence1[nt].upper() != sequence2[nt].upper():
                    if not(begin):
                        sub_begin = nt
                        begin = True
                    sub_end = nt
                else:
                    if begin:
                        print >> fout, "%s\t%s\t%s" % ( src1, start1+sub_begin-sequence1[0:sub_begin].count('-'), start1+sub_end-sequence1[0:sub_end].count('-') )
                        print >> fout, "%s\t%s\t%s" % ( src2, start2+sub_begin-sequence2[0:sub_begin].count('-'), start2+sub_end-sequence2[0:sub_end].count('-') )
                        begin = False
            else:
                if begin:
                    print >> fout, "%s\t%s\t%s" % ( src1, start1+sub_begin-sequence1[0:sub_begin].count('-'), end1+sub_end-sequence1[0:sub_end].count('-') )
                    print >> fout, "%s\t%s\t%s" % ( src2, start2+sub_begin-sequence2[0:sub_begin].count('-'), end2+sub_end-sequence2[0:sub_end].count('-') )
                    begin = False


def main():
    skipped = 0
    not_pairwise = 0
    try:
        maf_reader = bx.align.maf.Reader( open(inp_file, 'r') )
    except:
        stop_err("Your MAF file appears to be malformed.")
    print >> fout, "#Chr\tStart\tEnd"
    for block in maf_reader:
        if len(block.components) != 2:
            not_pairwise += 1
            continue
        try:
            fetchSubs(block)
        except:
            skipped += 1
    
    if not_pairwise:
        print "Skipped %d non-pairwise blocks" % (not_pairwise)
    if skipped:
        print "Skipped %d blocks" % (skipped)


if __name__ == "__main__":
    main()
