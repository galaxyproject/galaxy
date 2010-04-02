#!/usr/bin/env python
#guruprasad Ananda
"""
Estimates substitution rates from pairwise alignments using JC69 model.
"""

from galaxy import eggs
from galaxy.tools.util.galaxyops import *
from galaxy.tools.util import maf_utilities
import bx.align.maf
import sys, fileinput

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

if len(sys.argv) < 3:
        stop_err("Incorrect number of arguments.")    
    
inp_file = sys.argv[1]
out_file = sys.argv[2]
fout = open(out_file, 'w')
int_file = sys.argv[3]
if int_file != "None":     #The user has specified an interval file
    dbkey_i = sys.argv[4]
    chr_col_i, start_col_i, end_col_i, strand_col_i = parse_cols_arg( sys.argv[5] )


def rateEstimator(block):
    global alignlen, mismatches

    src1 = block.components[0].src
    sequence1 = block.components[0].text
    start1 = block.components[0].start
    end1 = block.components[0].end
    len1 = int(end1)-int(start1)
    len1_withgap = len(sequence1)
    mismatch = 0.0
    
    for seq in range (1,len(block.components)):
        src2 = block.components[seq].src
        sequence2 = block.components[seq].text
        start2 = block.components[seq].start
        end2 = block.components[seq].end
        len2 = int(end2)-int(start2)
        for nt in range(len1_withgap):
            if sequence1[nt] not in '-#$^*?' and sequence2[nt] not in '-#$^*?': #Not a gap or masked character
                if sequence1[nt].upper() != sequence2[nt].upper():
                    mismatch += 1
    
    if int_file == "None":  
        p = mismatch/min(len1,len2)
        print >>fout, "%s\t%s\t%s\t%s\t%s\t%s\t%d\t%d\t%.4f" %(src1,start1,end1,src2,start2,end2,min(len1,len2),mismatch,p)
    else:
        mismatches += mismatch
        alignlen += min(len1,len2)
              
def main():
    skipped = 0
    not_pairwise = 0
    
    if int_file == "None":
        try:
            maf_reader = bx.align.maf.Reader( open(inp_file, 'r') )
        except:
            stop_err("Your MAF file appears to be malformed.")
        print >>fout, "#Seq1\tStart1\tEnd1\tSeq2\tStart2\tEnd2\tL\tN\tp"
        for block in maf_reader:
            if len(block.components) != 2:
                not_pairwise += 1
                continue
            try:
                rateEstimator(block)
            except:
                skipped += 1
    else:
        index, index_filename = maf_utilities.build_maf_index( inp_file, species = [dbkey_i] )
        if index is None:
            print >> sys.stderr, "Your MAF file appears to be malformed."
            sys.exit()
        win = NiceReaderWrapper( fileinput.FileInput( int_file ),
                                chrom_col=chr_col_i,
                                start_col=start_col_i,
                                end_col=end_col_i,
                                strand_col=strand_col_i,
                                fix_strand=True)
        species=None
        mincols = 0
        global alignlen, mismatches
        
        for interval in win:
            alignlen = 0
            mismatches = 0.0
            src = "%s.%s" % ( dbkey_i, interval.chrom )
            for block in maf_utilities.get_chopped_blocks_for_region( index, src, interval, species, mincols ):
                if len(block.components) != 2:
                    not_pairwise += 1
                    continue
                try:
                    rateEstimator(block)
                except:
                    skipped += 1
            if alignlen:
                p = mismatches/alignlen
            else:
                p = 'NA'
            interval.fields.append(str(alignlen))
            interval.fields.append(str(mismatches))
            interval.fields.append(str(p))
            print >>fout, "\t".join(interval.fields)    
            #num_blocks += 1
    
    if not_pairwise:
        print "Skipped %d non-pairwise blocks" %(not_pairwise)
    if skipped:
        print "Skipped %d blocks as invalid" %(skipped)
if __name__ == "__main__":
    main()
