#!/usr/bin/env python2.4
#Guru
"""
Reads an interval file containing genome co-ordinates of unassembled/partially assembled genomes and 
returns a fasta file containing the corresponding sequence/s.
"""

import sys, os, tempfile, string, math

#Used to reverse compliment DNA
DNA_COMP = string.maketrans( "ACGTacgt", "TGCAtgca" )
def reverse_complement(text):
    comp = [ch for ch in text.translate(DNA_COMP)]
    comp.reverse()
    return "".join(comp)

if len(sys.argv) != 9:
    print "USAGE: prog input out_file input_chromCol input_startCol input_endCol input_strandCol input_dbkey loc_file"
    sys.exit()

infile = sys.argv[1]
outfile = sys.argv[2]
chr_col = sys.argv[3]
start_col = sys.argv[4]
end_col = sys.argv[5]
strand_col = sys.argv[6]
dbkey = sys.argv[7]
loc_file = sys.argv[8]

#ensure dbkey is set
if dbkey == "?": 
    print >>sys.stderr, "You must specify a proper build in order to extract sequences."
    sys.exit()

#ensure dbkey is present in the twobit loc file
filepath = None
try:
    for line in open(loc_file):
        if line[0:1] == "#":
            continue
        fields = line.split('\t')
        try:
            build = fields[0]
            if dbkey == build:
                filepath = fields[1]
                break
            else:
                continue
        except:
            pass
except Exception, exc:
    print >>sys.stdout, 'twoBitToFa_wrapper.py initialization error -> %s' % exc 

if filepath == None:
    print "Sequences for the specified genome are unavailable. You may want to try the 'Extract genomic DNA corresponding to query coordinates' tool"
else:
    try:
        fout = open(outfile, "w")
        for line in open(infile):
            if line[0:1] == "#":
                continue
            fields = line.split('\t')
            try:
                name = fields[int(chr_col)-1]
                start = fields[int(start_col)-1]
                end = fields[int(end_col)-1]
                #Run twoBitToFa program
                tmpfile = tempfile.NamedTemporaryFile()
                cmdline = "tools/extract/twoBitToFa " + filepath.strip() + " " + tmpfile.name + " -seq=" + name + " -start=" + start + " -end=" + end 
                os.system(cmdline)
                header = tmpfile.readline()
                seq = tmpfile.read()
                if strand_col != 0 and fields[int(strand_col)-1] == "-":    # for negative strand
                    print >>fout, header.strip()
                    revcompseq = reverse_complement(seq.replace("\n","").replace("\r",""))
                    i = 0
                    while i < len (revcompseq):        
                        print >>fout, revcompseq[i:i+50]    #print 50 nucleotides per line of the fasta output
                        i += 50 
                    #print >>fout, reverse_complement(seq.replace("\n","").replace("\r",""))    
                else:    # for positive strand
                    print >>fout, header.strip()
                    print >>fout, seq                    
            except:
                pass    #skip invalid lines
        fout.close()
        print "Genomic DNA corresponding to query co-ordinates"
    except Exception, exc:
        print >>sys.stdout, exc 

  
    
