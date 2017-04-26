#!/usr/bin/env python

"""
Adds Manually created builds and chrom info to Galaxy's info tables

Usage:
python add_manual_builds.py input_file builds.txt chrom_length_dir
"""

import os
import sys


def add_manual_builds(input_file, build_file, chr_dir):
    # determine existing builds, so as to not overwrite
    existing_builds = []
    for line in open(build_file):
        try:
            if line.startswith("#"):
                continue
            existing_builds.append(line.replace("\n", "").replace("\r", "").split("\t")[0])
        except:
            continue
    build_file_out = open(build_file, 'a')
    for line in open(input_file):
        try:
            fields = line.replace("\n", "").replace("\r", "").split("\t")
            build = fields.pop(0)
            if build in existing_builds:
                continue  # if build exists, leave alone
            name = fields.pop(0)
            try:  # get chrom lens if included in file, otherwise still add build
                chrs = fields.pop(0).split(",")
            except:
                chrs = []
            print>>build_file_out, build + "\t" + name + " (" + build + ")"
            if chrs:  # create len file if provided chrom lens
                chr_len_out = open(os.path.join(chr_dir, build + ".len"), 'w')
                for chr in chrs:
                    print>>chr_len_out, chr.replace("=", "\t")
                chr_len_out.close()
        except:
            continue
    build_file_out.close()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit("USAGE: python add_manual_builds.py input_file builds.txt chrom_length_dir")
    input_file = sys.argv[1]
    build_file = sys.argv[2]
    chr_dir = sys.argv[3]
    add_manual_builds(input_file, build_file, chr_dir)
