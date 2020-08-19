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
Utility functions for I/O of custom files.
"""


def read_poa_group_file(file_path, num_windows=0):
    """
    Parses data file containing POA groups.

    Args:
        file_path : Path to POA group file.
        num_windows : Number of windows to extract from
                      file. If requested is more than available
                      in file, windows are repoeated in a circular
                      loop like fashion.
                      0 (default) implies using only those windows
                      available in file.

    File format is as follows -
    <num sequences>
    seq 1...
    seq 2...
    <num sequences>
    seq 1...
    seq 2...
    seq 3...
    """
    with open(file_path, "r") as window_file:
        num_seqs_in_group = 0
        group_list = []
        current_seq_list = []
        first_seq = True

        for line in window_file:
            line = line.strip()

            # First line is num sequences in group
            if (num_seqs_in_group == 0):
                if first_seq:
                    first_seq = False
                else:
                    group_list.append(current_seq_list)
                    current_seq_list = []
                num_seqs_in_group = int(line)
            else:
                current_seq_list.append(line)
                num_seqs_in_group = num_seqs_in_group - 1

        if (num_windows > 0):
            if (num_windows < len(group_list)):
                group_list = group_list[:num_windows]
            else:
                original_num_windows = len(group_list)
                num_windows_to_add = num_windows - original_num_windows
                for i in range(num_windows_to_add):
                    group_list.append(group_list[i % original_num_windows])

        return group_list
