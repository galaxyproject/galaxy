#!/usr/bin/env python
"""Filter a FASTA file using tabular BLAST output.

Takes four command line options, tabular BLAST filename, input FASTA filename,
and two output FASTA filenames (for records with and without any BLAST hits).
"""
#TODO - Option to define which column to use for ID?

import sys
from galaxy_utils.sequence.fasta import fastaReader, fastaWriter

#Parse Command Line
blast_file, in_file, out_positive_file, out_negative_file = sys.argv[1:]

#Read tabular BLAST file and record all queries with hit(s)
ids = set()
blast_handle = open(blast_file, "rU")  
for line in blast_handle:
    ids.add(line.split("\t")[0])
blast_handle.close()

#Write filtered FASTA file based on IDs from BLAST file
reader = fastaReader(open(in_file, "rU"))
positive_writer = fastaWriter(open(out_positive_file, "w"))
negative_writer = fastaWriter(open(out_negative_file, "w"))
for record in reader:
    #The [1:] is because the fastaReader leaves the > on the identifer.
    if record.identifier and record.identifier.split()[0][1:] in ids:
        positive_writer.write(record)
    else:
        negative_writer.write(record)
positive_writer.close()
negative_writer.close()
reader.close()
