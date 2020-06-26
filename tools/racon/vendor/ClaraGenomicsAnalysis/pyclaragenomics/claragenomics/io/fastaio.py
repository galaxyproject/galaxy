#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

"""
Functions for FASTA file I/O
"""
import gzip


def write_fasta(seqs, filepath, gzip_compressed=False):
    """Writes a fasta file for sequences.

    Args:
      seqs: list of 2-tuples containnig sequnces and their names, e.g [('seq1', 'ACGTC...'), ('seq2', 'TTGGC...'), ...]]
      filepath: path to file for writing out FASTA.
      gzip_compressed bool: If True then the read component of the sequence has been compressed with gzip

    Returns:
      None.
    """

    with open(filepath, 'w') as f:
        for s in seqs:
            fasta_string = ">{}\n".format(s[0])

            if gzip_compressed:
                read = str(gzip.decompress(s[1]), "utf-8")
            else:
                read = s[1]

            lines = [read[n * 80:(n + 1) * 80] for n in range((len(read) // 80) + 1)]

            fasta_string += "\n".join(lines)
            if fasta_string[-1] != "\n":
                fasta_string += "\n"

            f.write(fasta_string)
