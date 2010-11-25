#!/usr/bin/env python
"""Convert a BLAST XML file to 12 column tabular output

Takes three command line options, input BLAST XML filename, output tabular
BLAST filename, output format (std for standard 12 columns, or x22 for the
extended 22 columns offered in the BLAST+ wrappers).

The 12 colums output are 'qseqid sseqid pident length mismatch gapopen qstart
qend sstart send evalue bitscore' which mean:
   
====== ========= ============================================
Column NCBI name Description
------ --------- --------------------------------------------
     1 qseqid    Query Seq-id (ID of your sequence)
     2 sseqid    Subject Seq-id (ID of the database hit)
     3 pident    Percentage of identical matches
     4 length    Alignment length
     5 mismatch  Number of mismatches
     6 gapopen   Number of gap openings
     7 qstart    Start of alignment in query
     8 qend      End of alignment in query
     9 sstart    Start of alignment in subject (database hit)
    10 send      End of alignment in subject (database hit)
    11 evalue    Expectation value (E-value)
    12 bitscore  Bit score
====== ========= ============================================

The additional columns are:

====== ============= ===========================================
Column NCBI name     Description
------ ------------- -------------------------------------------
    13 sallseqid     All subject Seq-id(s), separated by a ';'
    14 score         Raw score
    15 nident        Number of identical matches
    16 positive      Number of positive-scoring matches
    17 gaps          Total number of gaps
    18 ppos          Percentage of positive-scoring matches
    19 qframe        Query frame
    20 sframe        Subject frame
    21 qseq          Aligned part of query sequence
    22 sseq          Aligned part of subject sequence
====== ============= ===========================================

Most of these fields are given explicitly in the XML file, others some like
the percentage identity and the number of gap openings must be calculated.

This script attempts to produce idential output to what BLAST+ would have done.
However, check this with "diff -b ..." since BLAST+ sometimes includes an extra
space character (probably a bug).

Beware that if using the extended output, the XML file contains the original
aligned sequences, but the tabular output direct from BLAST+ may use XXXX
masking on regions of low complexity (columns 21 and 22).
"""
import sys

assert sys.version_info[:2] >= ( 2, 4 )
if sys.version_info[:2] >= ( 2, 5 ):
    import xml.etree.cElementTree as cElementTree
else:
    import cElementTree 

def stop_err( msg ):
    sys.stderr.write("%s\n" % msg)
    sys.exit(1)

#Parse Command Line
try:
    in_file, out_file, out_fmt = sys.argv[1:]
except:
    stop_err("Expect 3 arguments: input BLAST XML file, output tabular file, out format (std or x22)")

if out_fmt == "std":
    extended = False
elif out_fmt == "x22":
    extended = True
else:
    stop_err("Format argument should be std (12 column) or x22 (extended 22 column)")


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
blast_program = None
for event, elem in context:
    if event == "end" and elem.tag == "BlastOutput_program":
        blast_program = elem.text
    # for every <Iteration> tag
    if event == "end" and elem.tag == "Iteration":
        qseqid = elem.findtext("Iteration_query-def").split(None,1)[0]
        # for every <Hit> within <Iteration>
        for hit in elem.findall("Iteration_hits/Hit/"):
            sseqid = hit.findtext("Hit_id").split(None,1)[0]
            # for every <Hsp> within <Hit>
            for hsp in hit.findall("Hit_hsps/Hsp"):
                nident = hsp.findtext("Hsp_identity")
                length = hsp.findtext("Hsp_align-len")
                pident = "%0.2f" % (100*float(nident)/float(length))

                q_seq = hsp.findtext("Hsp_qseq")
                h_seq = hsp.findtext("Hsp_hseq")
                m_seq = hsp.findtext("Hsp_midline")
                assert len(q_seq) == len(h_seq) == len(m_seq) == int(length)
                gapopen = str(len(q_seq.replace('-', ' ').split())-1  + \
                              len(h_seq.replace('-', ' ').split())-1)

                mismatch = m_seq.count(' ') + m_seq.count('+') \
                         - q_seq.count('-') - h_seq.count('-')
                #TODO - Remove this alternative mismatch calculation and test
                #once satisifed there are no problems
                expected_mismatch = len(q_seq) \
                                  - sum(1 for q,h in zip(q_seq, h_seq) \
                                        if q == h or q == "-" or h == "-")
                assert expected_mismatch - q_seq.count("X") <= int(mismatch) <= expected_mismatch, \
                       "%s vs %s mismatches, expected %i <= %i <= %i" \
                       % (qseqid, sseqid, expected_mismatch - q_seq.count("X"), int(mismatch), expected_mismatch)

                #TODO - Remove this alternative identity calculation and test
                #once satisifed there are no problems
                expected_idendity = sum(1 for q,h in zip(q_seq, h_seq) if q == h)
                assert expected_idendity <= int(nident) <= expected_idendity + q_seq.count("X"), \
                       "%s vs %s identities, expected %i <= %i <= %i" \
                       % (qseqid, sseqid, expected_idendity, int(identity), expected_idendity + q_seq.count("X"))
                

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
                          str(mismatch),
                          gapopen,
                          hsp.findtext("Hsp_query-from"), #qstart,
                          hsp.findtext("Hsp_query-to"), #qend,
                          hsp.findtext("Hsp_hit-from"), #sstart,
                          hsp.findtext("Hsp_hit-to"), #send,
                          evalue, #hsp.findtext("Hsp_evalue") in scientific notation
                          bitscore, #hsp.findtext("Hsp_bit-score") rounded
                          ]

                if extended:
                    hit_def = sseqid + " " + hit.findtext("Hit_def")
                    sallseqid = ":".join(name.split(None,1)[0] for name in hit_def.split(">"))
                    #print hit_def, "-->", sallseqid
                    positive = hsp.findtext("Hsp_positive")
                    ppos = "%0.2f" % (100*float(positive)/float(length))
                    qframe = hsp.findtext("Hsp_query-frame")
                    sframe = hsp.findtext("Hsp_hit-frame")
                    if blast_program == "blastp":
                        #Probably a bug in BLASTP that they use 0 or 1 depending on format
                        if qframe == "0": qframe = "1"
                        if sframe == "0": sframe = "1"
                    values.extend([sallseqid,
                                   hsp.findtext("Hsp_score"), #score,
                                   nident,
                                   positive,
                                   hsp.findtext("Hsp_gaps"), #gaps,
                                   ppos,
                                   qframe,
                                   sframe,
                                   #NOTE - for blastp, XML shows original seq, tabular uses XXX masking
                                   q_seq,
                                   h_seq])
                #print "\t".join(values) 
                outfile.write("\t".join(values) + "\n")
        # prevents ElementTree from growing large datastructure
        root.clear()
        elem.clear()
outfile.close()
