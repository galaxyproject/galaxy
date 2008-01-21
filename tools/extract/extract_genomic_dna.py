#!/usr/bin/env python2.4
"""
to do:
1. more error situation/message: BED format and strand
5. ask what other stuff needs to be done
----
use bx-python, only runs through galaxy
functions from other programs
usage: %this_prog.py $input $out_file1 $input_chromCol $input_startCol $input_endCol $input_strandCol $dbkey 
by Wen-Yu Chung
"""
import sys, string, os, re

import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse
import bx.seq.nib
import bx.seq.twobit

# location
NIB_LOC = "/depot/data2/galaxy/alignseq.loc"
TWOBIT_LOC = "/depot/data2/galaxy/twobit.loc"        # did not use at all

def reverse_complement(s):
    complement_dna = {"A":"T", "T":"A", "C":"G", "G":"C", "a":"t", "t":"a", "c":"g", "g":"c" }
    reversed_s = []
    for i in s:
        reversed_s.append(complement_dna[i])
    reversed_s.reverse()
    
    return "".join(reversed_s)

def check_nib_loc(dbkey):
    nib_path_true = ''
    nibs = {}
    
    for line in open(NIB_LOC):
        line.strip('\r\n')
        fields = line.split()    # seperate by space
        if (fields[0] == 'seq'):
            nibs[(fields[1])] = fields[2]
    if nibs.has_key(dbkey):
        nib_path_true = nibs[(dbkey)]
                
    return nib_path_true 

def check_twobit_loc(dbkey):
    twobit_path_true = ''
    twobits = {}
    
    for line in open(TWOBIT_LOC):
        #line.strip('\r\n')
        if line.startswith("#"): 
            continue
        fields = line.split()
        twobits[(fields[0])] = fields[1]

    if twobits.has_key(dbkey):
        twobit_path_true = twobits[(dbkey)]
    
    return twobit_path_true 

def print_wrapped( fields, s, fout, output_format ):
    l = len( s )        
    c = 0
    
    if (output_format == "0"): # fasta
        meta_data = "_".join(fields)
        print >> fout, ">%s" %meta_data    #chrom, start, end
        while c < l:
            b = min( c + 50, l )
            print >> fout, s[c:b]    #print s[c:b]
            c = b
    else: # interval
        meta_data = "\t".join(fields)
        print >> fout, meta_data, "\t", s
        
def __main__():

    """
    options, args = doc_optparse.parse( __doc__ )    # what are options?
    
    for i in args:
        print i
    """

    # assign parameters to new variable names
    input_filename = sys.argv[1]                # input: bed format
    output_filename = sys.argv[2]                # output: fasta format
    input_chrom_col = int(sys.argv[3]) - 1        # chromosomal
    input_start_col = int(sys.argv[4]) - 1        # start location
    input_end_col = int(sys.argv[5]) - 1            # end location
    input_strand_col = int(sys.argv[6]) - 1         # strand
    dbkey = sys.argv[7]
    output_format = sys.argv[8]                # 0: fasta; 1: interval
    
    # some simple check
    if dbkey == "?":     #if (re.search("?", dbkey)): 
        print >> sys.stderr, "Please specify genome build by clicking on pencil icon in the original dataset"
        
    if (re.search("^mm\d$", dbkey)): dbkey = "musMus"+dbkey[-1]
    if (re.search("^rn\d$", dbkey)): dbkey = "ratNor"+dbkey[-1]
    
    #if (input_strand_col < 0): input_strand_col = 1000000        #??
       
    # search both types
    nib_path = check_nib_loc(dbkey)
    twobit_path = check_twobit_loc(dbkey)
    
    #if len(nib_path) > 0: print >> sys.stdout, "NIB", nib_path
    #if len(twobit_path) > 0: print >> sys.stdout, "2Bit", twobit_path

    if (not (os.path.exists(nib_path)) and not (os.path.exists(twobit_path))): 
        print >> stderr, "No sequences are available for %s. Request them by reporting this error" % dbkey
         
    # open the input bed file, extract genomic dna sequence one by one (line)
    fout = open(output_filename,"w")
    nibs = {}
    twobits = {}
    for line in open(input_filename):
        if not (line.startswith("#")):
            line = line.strip('\r\n')
            fields = line.split('\t')        # chr7  127475281  127475310  NM_000230  0  +
            chrom, start, end, strand = fields[input_chrom_col], int( fields[input_start_col] ), int( fields[input_end_col] ), fields[input_strand_col]
            
            
            """
            # check whether chrom is words
            if not (start.isdigit() and end.isdigit()):
                print >> stderr, "Bad BED fields: ", start, end
            """
            
            if ((strand != "+") and (strand != "-")): strand = "+"            
            
            # for nibs
            s = ''
            if (os.path.exists("%s/%s.nib" % (nib_path, chrom))): #if (os.path.exists(nib_path)):
                if chrom in nibs:
                    nib = nibs[chrom]
                else:
                    nibs[chrom] = nib = bx.seq.nib.NibFile( file( "%s/%s.nib" % ( nib_path, chrom ) ) )
                s = nib.get( start , end - start )
            #elif (os.path.exists(twobit_path)):
            #elif (os.path.exists("%s/%s.2bit" % (nib_path, chrom))):
            elif (len(os.listdir(nib_path)) > 0):
                twobit_path = nib_path + "/" + os.listdir(nib_path)[0]
                # for twobit
                if chrom in twobits:
                    t = twobits[chrom]
                else:
                    twobits[chrom] = t = bx.seq.twobit.TwoBitFile(open(twobit_path))
                    #t = bx.seq.twobit.TwoBitFile( open( twobit_path ) )
                s = t[chrom][start:end]
            else:
                print >> sys.stderr, "Sequence %s was not found for genome build %s" % (chrom, dbkey)
                print >> sys.stderr, "Most likely your data lists wrong chromosome number for this organism"
                print >> sys.stderr, "Check your genome build selection"
            
            # some post process check
            if len(s) <= 0: 
                print >> sys.stderr, '%s_%s_%s is either invalid or not present in the specified genome.' %(chrom,start,end) 
                   
            # reverse if necessary
            if ((input_strand_col >= 0) and (strand == "-")):
                s = reverse_complement(s)
        
            if (output_format == "0"): # fasta
                fields = [dbkey, str(chrom), str(start), str(end), strand]
                
            print_wrapped( fields, s, fout, output_format )
                
    fout.close()
                
if __name__ == "__main__": __main__()