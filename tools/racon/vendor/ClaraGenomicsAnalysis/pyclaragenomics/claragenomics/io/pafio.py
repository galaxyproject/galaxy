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
Functions for PAF I/O
"""

import collections

Overlap = collections.namedtuple("Overlap", ["query_sequence_name",
                                             "query_sequence_length",
                                             "query_start",
                                             "query_end",
                                             "relative_strand",
                                             "target_sequence_name",
                                             "target_sequence_length",
                                             "target_start",
                                             "target_end",
                                             "num_residue_matches",
                                             "alignment_block_length",
                                             "mapping_quality"])


def read_paf(filepath):
    """ Read a PAF file

    Args:
      filepath (str): Path to read PAF file from.

    Returns:
        list of Overlap objects. Overlap is a named tuple with the following fields:

        * query_sequence_name
        * query_sequence_length
        * query_start
        * query_end
        * relative_strand
        * target_sequence_name
        * target_sequence_length
        * target_start
        * target_end
        * num_residue_matches
        * alignment_block_length
        * mapping_quality
    """
    overlaps = []
    with open(filepath) as f:
        for paf_entry in f.readlines():
            paf_entry = paf_entry.replace('\n', '')
            paf_entry = paf_entry.split('\t')
            paf_entry_sanitised = [int(x) if x.isdigit() else x for x in paf_entry]
            paf_entry_sanitised[0] = str(paf_entry_sanitised[0])
            paf_entry_sanitised[5] = str(paf_entry_sanitised[5])
            overlaps.append(Overlap(*paf_entry_sanitised[:12]))
    return overlaps


def write_paf(overlaps, filepath):
    """Writes a PAF file for sequences.

    Args:
      filepath (str): Path to write PAF file too.
      overlaps: a list of overlaps, named tuple objects with the following fields:

        * query_sequence_name
        * query_sequence_length
        * query_start
        * query_end
        * relative_strand
        * target_sequence_name
        * target_sequence_length
        * target_start
        * target_end
        * num_residue_matches
        * alignment_block_length
        * mapping_quality

    The [PAF format](https://github.com/lh3/miniasm/blob/master/PAF.md) is defined as follows:

    Col Type    Description
    1	string	Query sequence name
    2	int	Query sequence length
    3	int	Query start (0-based; BED-like; closed)
    4	int	Query end (0-based; BED-like; open)
    5	char	Relative strand: "+" or "-"
    6	string	Target sequence name
    7	int	Target sequence length
    8	int	Target start on original strand (0-based)
    9	int	Target end on original strand (0-based)
    10	int	Number of residue matches
    11	int	Alignment block length
    12	int	Mapping quality (0-255; 255 for missing)
    """
    with open(filepath, 'w') as f:
        for overlap in overlaps:
            paf_string = "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
                overlap.query_sequence_name,
                overlap.query_sequence_length,
                overlap.query_start,
                overlap.query_end,
                overlap.relative_strand,
                overlap.target_sequence_name,
                overlap.target_sequence_length,
                overlap.target_start,
                overlap.target_end,
                overlap.num_residue_matches,
                overlap.alignment_block_length,
                overlap.mapping_quality
            )
            f.write(paf_string)
