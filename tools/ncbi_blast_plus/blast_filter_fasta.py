#!/usr/bin/env python
"""Filter a FASTA file using tabular output, e.g. from BLAST.

Takes five command line options, tabular BLAST filename, ID column number
(using one based counting), input FASTA filename, and two output FASTA
filenames (for records with and without any BLAST hits).

In the default NCBI BLAST+ tabular output, the query sequence ID is in column
one, and the ID of the match from the database is in column two.
"""
import sys
from galaxy_utils.sequence.fasta import fastaReader, fastaWriter

#Parse Command Line
blast_file, blast_col, in_file, out_positive_file, out_negative_file = sys.argv[1:]
blast_col = int(blast_col)-1
assert blast_col >= 0

#Read tabular BLAST file and record all queries with hit(s)
ids = set()
blast_handle = open(blast_file, "rU")  
for line in blast_handle:
    ids.add(line.split("\t")[blast_col])
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
