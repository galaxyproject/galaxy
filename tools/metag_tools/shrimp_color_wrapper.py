#!/usr/bin/env python
"""
SHRiMP wrapper : Color space
"""

import os
import os.path
import re
import sys
import tempfile

assert sys.version_info[:2] >= (2, 4)


def stop_err(msg):
    sys.stderr.write("%s\n" % msg)
    sys.exit()


def __main__():
    # SHRiMP path
    shrimp = "rmapper-cs"

    # I/O
    input_target_file = sys.argv[1]  # fasta
    input_query_file = sys.argv[2]
    shrimp_outfile = sys.argv[3]  # shrimp output

    # SHRiMP parameters
    spaced_seed = "1111001111"
    seed_matches_per_window = "2"
    seed_hit_taboo_length = "4"
    seed_generation_taboo_length = "0"
    seed_window_length = "115.0"
    max_hits_per_read = "100"
    max_read_length = "1000"
    kmer = "-1"
    sw_match_value = "100"
    sw_mismatch_value = "-150"
    sw_gap_open_ref = "-400"
    sw_gap_open_query = "-400"
    sw_gap_ext_ref = "-70"
    sw_gap_ext_query = "-70"
    sw_crossover_penalty = "-140"
    sw_full_hit_threshold = "68.0"
    sw_vector_hit_threshold = "60.0"

    # TODO: put the threshold on each of these parameters
    if len(sys.argv) > 4:
        try:
            if sys.argv[4].isdigit():
                spaced_seed = sys.argv[4]
            else:
                stop_err("Error in assigning parameter: Spaced seed.")
        except Exception:
            stop_err("Spaced seed must be a combination of 1s and 0s.")

        seed_matches_per_window = sys.argv[5]
        seed_hit_taboo_length = sys.argv[6]
        seed_generation_taboo_length = sys.argv[7]
        seed_window_length = sys.argv[8]
        max_hits_per_read = sys.argv[9]
        max_read_length = sys.argv[10]
        kmer = sys.argv[11]
        sw_match_value = sys.argv[12]
        sw_mismatch_value = sys.argv[13]
        sw_gap_open_ref = sys.argv[14]
        sw_gap_open_query = sys.argv[15]
        sw_gap_ext_ref = sys.argv[16]
        sw_gap_ext_query = sys.argv[17]
        sw_crossover_penalty = sys.argv[18]
        sw_full_hit_threshold = sys.argv[19]
        sw_vector_hit_threshold = sys.argv[20]

    # temp file for shrimp log file
    shrimp_log = tempfile.NamedTemporaryFile().name

    # SHRiMP command
    command = " ".join(
        (
            shrimp,
            "-s",
            spaced_seed,
            "-n",
            seed_matches_per_window,
            "-t",
            seed_hit_taboo_length,
            "-9",
            seed_generation_taboo_length,
            "-w",
            seed_window_length,
            "-o",
            max_hits_per_read,
            "-r",
            max_read_length,
            "-d",
            kmer,
            "-m",
            sw_match_value,
            "-i",
            sw_mismatch_value,
            "-g",
            sw_gap_open_ref,
            "-q",
            sw_gap_open_query,
            "-e",
            sw_gap_ext_ref,
            "-f",
            sw_gap_ext_query,
            "-x",
            sw_crossover_penalty,
            "-h",
            sw_full_hit_threshold,
            "-v",
            sw_vector_hit_threshold,
            input_query_file,
            input_target_file,
            ">",
            shrimp_outfile,
            "2>",
            shrimp_log,
        )
    )

    try:
        os.system(command)
    except Exception as e:
        stop_err(str(e))

    # check SHRiMP output: count number of lines
    num_hits = 0
    if shrimp_outfile:
        for line in open(shrimp_outfile):
            line = line.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            try:
                line.split()
                num_hits += 1
            except Exception as e:
                stop_err(str(e))

    if num_hits == 0:  # no hits generated
        err_msg = ""
        if shrimp_log:
            for line in open(shrimp_log):
                if line.startswith("error"):  # deal with memory error:
                    err_msg += line  # error: realloc failed: Cannot allocate memory
                if re.search("Reads Matched", line):  # deal with zero hits
                    if int(line[8:].split()[2]) == 0:
                        err_msg = "Zero hits found.\n"
        stop_err("SHRiMP Failed due to:\n" + err_msg)

    # remove temp. files
    if os.path.exists(shrimp_log):
        os.remove(shrimp_log)


if __name__ == "__main__":
    __main__()
