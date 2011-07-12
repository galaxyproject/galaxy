#!/usr/bin/env python
"""Convert a BLAST XML file to 12 column tabular output

Takes three command line options, input BLAST XML filename, output tabular
BLAST filename, output format (std for standard 12 columns, or ext for the
extended 24 columns offered in the BLAST+ wrappers).

The 12 columns output are 'qseqid sseqid pident length mismatch gapopen qstart
qend sstart send evalue bitscore' or 'std' at the BLAST+ command line, which
mean:
   
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

The additional columns offered in the Galaxy BLAST+ wrappers are:

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
    23 qlen          Query sequence length
    24 slen          Subject sequence length
====== ============= ===========================================

Most of these fields are given explicitly in the XML file, others some like
the percentage identity and the number of gap openings must be calculated.

Be aware that the sequence in the extended tabular output or XML direct from
BLAST+ may or may not use XXXX masking on regions of low complexity. This
can throw the off the calculation of percentage identity and gap openings.
[In fact, both BLAST 2.2.24+ and 2.2.25+ have a subtle bug in this regard,
with these numbers changing depending on whether or not the low complexity
filter is used.]

This script attempts to produce identical output to what BLAST+ would have done.
However, check this with "diff -b ..." since BLAST+ sometimes includes an extra
space character (probably a bug).
"""
import sys
import re

if sys.version_info[:2] >= ( 2, 5 ):
    import xml.etree.cElementTree as ElementTree
else:
    from galaxy import eggs
    import pkg_resources; pkg_resources.require( "elementtree" )
    from elementtree import ElementTree

def stop_err( msg ):
    sys.stderr.write("%s\n" % msg)
    sys.exit(1)

#Parse Command Line
try:
    in_file, out_file, out_fmt = sys.argv[1:]
except:
    stop_err("Expect 3 arguments: input BLAST XML file, output tabular file, out format (std or ext)")

if out_fmt == "std":
    extended = False
elif out_fmt == "x22":
    stop_err("Format argument x22 has been replaced with ext (extended 24 columns)")
elif out_fmt == "ext":
    extended = True
else:
    stop_err("Format argument should be std (12 column) or ext (extended 24 columns)")


# get an iterable
try: 
    context = ElementTree.iterparse(in_file, events=("start", "end"))
except:
    stop_err("Invalid data format.")
# turn it into an iterator
context = iter(context)
# get the root element
try:
    event, root = context.next()
except:
    stop_err( "Invalid data format." )


re_default_query_id = re.compile("^Query_\d+$")
assert re_default_query_id.match("Query_101")
assert not re_default_query_id.match("Query_101a")
assert not re_default_query_id.match("MyQuery_101")
re_default_subject_id = re.compile("^Subject_\d+$")
assert re_default_subject_id.match("Subject_1")
assert not re_default_subject_id.match("Subject_")
assert not re_default_subject_id.match("Subject_12a")
assert not re_default_subject_id.match("TheSubject_1")


outfile = open(out_file, 'w')
blast_program = None
for event, elem in context:
    if event == "end" and elem.tag == "BlastOutput_program":
        blast_program = elem.text
    # for every <Iteration> tag
    if event == "end" and elem.tag == "Iteration":
        #Expecting either this, from BLAST 2.2.25+ using FASTA vs FASTA
        # <Iteration_query-ID>sp|Q9BS26|ERP44_HUMAN</Iteration_query-ID>
        # <Iteration_query-def>Endoplasmic reticulum resident protein 44 OS=Homo sapiens GN=ERP44 PE=1 SV=1</Iteration_query-def>
        # <Iteration_query-len>406</Iteration_query-len>
        # <Iteration_hits></Iteration_hits>
        #
        #Or, from BLAST 2.2.24+ run online
        # <Iteration_query-ID>Query_1</Iteration_query-ID>
        # <Iteration_query-def>Sample</Iteration_query-def>
        # <Iteration_query-len>516</Iteration_query-len>
        # <Iteration_hits>...
        qseqid = elem.findtext("Iteration_query-ID")
        if re_default_query_id.match(qseqid):
            #Place holder ID, take the first word of the query definition
            qseqid = elem.findtext("Iteration_query-def").split(None,1)[0]
        qlen = int(elem.findtext("Iteration_query-len"))
                                        
        # for every <Hit> within <Iteration>
        for hit in elem.findall("Iteration_hits/Hit"):
            #Expecting either this,
            # <Hit_id>gi|3024260|sp|P56514.1|OPSD_BUFBU</Hit_id>
            # <Hit_def>RecName: Full=Rhodopsin</Hit_def>
            # <Hit_accession>P56514</Hit_accession>
            #or,
            # <Hit_id>Subject_1</Hit_id>
            # <Hit_def>gi|57163783|ref|NP_001009242.1| rhodopsin [Felis catus]</Hit_def>
            # <Hit_accession>Subject_1</Hit_accession>
            #
            #apparently depending on the parse_deflines switch
            sseqid = hit.findtext("Hit_id").split(None,1)[0]
            hit_def = sseqid + " " + hit.findtext("Hit_def")
            if re_default_subject_id.match(sseqid) \
            and sseqid == hit.findtext("Hit_accession"):
                #Place holder ID, take the first word of the subject definition
                hit_def = hit.findtext("Hit_def")
                sseqid = hit_def.split(None,1)[0]
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
                xx = sum(1 for q,h in zip(q_seq, h_seq) if q=="X" and h=="X")
                if not (expected_mismatch - q_seq.count("X") <= int(mismatch) <= expected_mismatch + xx):
                    stop_err("%s vs %s mismatches, expected %i <= %i <= %i" \
                             % (qseqid, sseqid, expected_mismatch - q_seq.count("X"),
                                int(mismatch), expected_mismatch))

                #TODO - Remove this alternative identity calculation and test
                #once satisifed there are no problems
                expected_identity = sum(1 for q,h in zip(q_seq, h_seq) if q == h)
                if not (expected_identity - xx <= int(nident) <= expected_identity + q_seq.count("X")):
                    stop_err("%s vs %s identities, expected %i <= %i <= %i" \
                             % (qseqid, sseqid, expected_identity, int(nident),
                                expected_identity + q_seq.count("X")))
                

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
                    sallseqid = ";".join(name.split(None,1)[0] for name in hit_def.split(">"))
                    #print hit_def, "-->", sallseqid
                    positive = hsp.findtext("Hsp_positive")
                    ppos = "%0.2f" % (100*float(positive)/float(length))
                    qframe = hsp.findtext("Hsp_query-frame")
                    sframe = hsp.findtext("Hsp_hit-frame")
                    if blast_program == "blastp":
                        #Probably a bug in BLASTP that they use 0 or 1 depending on format
                        if qframe == "0": qframe = "1"
                        if sframe == "0": sframe = "1"
                    slen = int(hit.findtext("Hit_len"))
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
                                   h_seq,
                                   str(qlen),
                                   str(slen),
                                   ])
                #print "\t".join(values) 
                outfile.write("\t".join(values) + "\n")
        # prevents ElementTree from growing large datastructure
        root.clear()
        elem.clear()
outfile.close()
