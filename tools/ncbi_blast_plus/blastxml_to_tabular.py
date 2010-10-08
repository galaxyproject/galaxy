#!/usr/bin/env python
"""Convert a BLAST XML file to 12 column tabular output

Takes two command line options, input BLAST XML filename and output tabular
BLAST filename.

The 12 colums output are 'qseqid sseqid pident length mismatch gapopen qstart
qend sstart send evalue bitscore' which mean:
   
 * qseqid   - Query Seq-id
 * sseqid   - Subject Seq-id
 * pident   - Percentage of identical matches
 * length   - Alignment length
 * mismatch - Number of mismatches
 * gapopen  - Number of gap openings
 * qstart   - Start of alignment in query
 * qend     - End of alignment in query
 * sstart   - Start of alignment in subject
 * send     - End of alignment in subject
 * evalue   - Expect value
 * bitscore - Bit score

Most of these fields are given explicitly in the XML file, others some like
the percentage identity and the number of gap openings must be calculated.

This script attempts to produce idential output to what BLAST+ would have done.
However, check this with "diff -b ..." since BLAST+ sometimes includes an extra
space character (probably a bug).
"""
import sys

#Parse Command Line
in_file, out_file = sys.argv[1:]

assert sys.version_info[:2] >= ( 2, 4 )
if sys.version_info[:2] >= ( 2, 5 ):
    import xml.etree.cElementTree as cElementTree
else:
    import cElementTree 

def stop_err( msg ):
    sys.stderr.write("%s\n" % msg)
    sys.exit(1)

tags = ["Hsp_identity",
        "Hsp_align-len",
        "Hsp_gaps",
        "Hsp_query-from",
        "Hsp_query-to",
        "Hsp_hit-from",
        "Hsp_hit-to",
        "Hsp_evalue",
        "Hsp_bit-score"]

# get an iterable
try: 
    context = cElementTree.iterparse(in_file, events=("start", "end"))
except:
    stop_err("Invalid data format.")
# turn it into an iterator
context = iter(context)
# get the root element
try:
    event, root = context.next()
except:
    stop_err( "Invalid data format." )

outfile = open(out_file, 'w')
for event, elem in context:
    # for every <Iteration> tag
    if event == "end" and elem.tag == "Iteration":
        qseqid = elem.findtext("Iteration_query-def").split(None,1)[0]
        # for every <Hit> within <Iteration>
        for hit in elem.findall("Iteration_hits/Hit/"):
            sseqid = hit.findtext("Hit_id").split(None,1)[0]
            # for every <Hsp> within <Hit>
            for hsp in hit.findall("Hit_hsps/Hsp"):
                identity = hsp.findtext("Hsp_identity")
                length = hsp.findtext("Hsp_align-len")
                pident = "%0.2f" % (100*float(identity)/float(length))

                q_seq = hsp.findtext("Hsp_qseq")
                h_seq = hsp.findtext("Hsp_hseq")
                assert len(q_seq) == len(h_seq) == int(length)
                gapopen = str(len(q_seq.replace('-', ' ').split())-1  + \
                              len(h_seq.replace('-', ' ').split())-1)
                mismatch = str(len(q_seq) - sum(1 for q,h in zip(q_seq, h_seq) \
                                                if q == h or q == "-" or h == "-"))
                assert int(identity) == sum(1 for q,h in zip(q_seq, h_seq) if q == h)

                evalue = hsp.findtext("Hsp_evalue")
                if evalue == "0":
                    evalue = "0.0"
                else:
                    evalue = "%0.0e" % float(evalue)
                
                bitscore = float(hsp.findtext("Hsp_bit-score"))
                if bitscore < 100:
                    #Seems to show one decimal place for lower scores
                    bitscore = "%0.1f" % bitscore
                else:
                    #Note BLAST does not round to nearest int, it truncates
                    bitscore = "%i" % bitscore

                values = [qseqid,
                          sseqid,
                          pident,
                          length, #hsp.findtext("Hsp_align-len")
                          mismatch,
                          gapopen,
                          hsp.findtext("Hsp_query-from"), #qstart,
                          hsp.findtext("Hsp_query-to"), #qend,
                          hsp.findtext("Hsp_hit-from"), #sstart,
                          hsp.findtext("Hsp_hit-to"), #send,
                          evalue, #hsp.findtext("Hsp_evalue") in scientific notation
                          bitscore, #hsp.findtext("Hsp_bit-score") rounded
                          ]
                #print "\t".join(values) 
                outfile.write("\t".join(values) + "\n")
        # prevents ElementTree from growing large datastructure
        root.clear()
        elem.clear()
outfile.close()
