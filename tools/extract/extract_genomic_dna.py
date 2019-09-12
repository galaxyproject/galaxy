#!/usr/bin/env python
"""
usage: %prog $input $out_file1
    -1, --cols=N,N,N,N,N: Columns for start, end, strand in input file
    -d, --dbkey=N: Genome build of input file
    -o, --output_format=N: the data type of the output file
    -g, --GALAXY_DATA_INDEX_DIR=N: the directory containing alignseq.loc or twobit.loc
    -I, --interpret_features: if true, complete features are interpreted when input is GFF
    -F, --fasta=<genomic_sequences>: genomic sequences to use for extraction
    -G, --gff: input and output file, when it is interval, coordinates are treated as GFF format (1-based, half-open) rather than 'traditional' 0-based, closed format.
"""
from __future__ import print_function

import os
import subprocess
import sys
import tempfile

import bx.seq.nib
import bx.seq.twobit
from bx.cookbook import doc_optparse
from bx.intervals.io import Comment, Header

from galaxy.datatypes.util import gff_util
from galaxy.tools.util.galaxyops import parse_cols_arg


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def reverse_complement(s):
    complement_dna = {"A": "T", "T": "A", "C": "G", "G": "C", "a": "t", "t": "a", "c": "g", "g": "c", "N": "N", "n": "n"}
    reversed_s = []
    for i in s:
        reversed_s.append(complement_dna[i])
    reversed_s.reverse()
    return "".join(reversed_s)


def check_seq_file(dbkey, GALAXY_DATA_INDEX_DIR):
    # Checks for the presence of *.nib files matching the dbkey within alignseq.loc
    seq_file = "%s/alignseq.loc" % GALAXY_DATA_INDEX_DIR
    for line in open(seq_file):
        line = line.rstrip('\r\n')
        if line and not line.startswith("#") and line.startswith('seq'):
            fields = line.split('\t')
            if len(fields) >= 3 and fields[1] == dbkey:
                print("Using *.nib genomic reference files")
                return fields[2].strip()

    # If no entry in aligseq.loc was found, check for the presence of a *.2bit file in twobit.loc
    seq_file = "%s/twobit.loc" % GALAXY_DATA_INDEX_DIR
    for line in open(seq_file):
        line = line.rstrip('\r\n')
        if line and not line.startswith("#") and line.endswith('.2bit'):
            fields = line.split('\t')
            if len(fields) >= 2 and fields[0] == dbkey:
                print("Using a *.2bit genomic reference file")
                return fields[1].strip()

    return ''


def __main__():
    #
    # Parse options, args.
    #
    options, args = doc_optparse.parse(__doc__)
    try:
        if len(options.cols.split(',')) == 5:
            # BED file
            chrom_col, start_col, end_col, strand_col, name_col = parse_cols_arg(options.cols)
        else:
            # gff file
            chrom_col, start_col, end_col, strand_col = parse_cols_arg(options.cols)
            name_col = False
        dbkey = options.dbkey
        output_format = options.output_format
        gff_format = options.gff
        interpret_features = options.interpret_features
        GALAXY_DATA_INDEX_DIR = options.GALAXY_DATA_INDEX_DIR
        fasta_file = options.fasta
        input_filename, output_filename = args
    except Exception:
        doc_optparse.exception()

    includes_strand_col = strand_col >= 0
    strand = None
    nibs = {}

    #
    # Set path to sequence data.
    #
    if fasta_file:
        # Need to create 2bit file from fasta file.
        try:
            seq_path = tempfile.NamedTemporaryFile(dir=".").name
            cmd = "faToTwoBit %s %s" % (fasta_file, seq_path)

            tmp_name = tempfile.NamedTemporaryFile(dir=".").name
            tmp_stderr = open(tmp_name, 'wb')
            proc = subprocess.Popen(args=cmd, shell=True, stderr=tmp_stderr.fileno())
            returncode = proc.wait()
            tmp_stderr.close()

            # Get stderr, allowing for case where it's very large.
            tmp_stderr = open(tmp_name, 'rb')
            stderr = ''
            buffsize = 1048576
            try:
                while True:
                    stderr += tmp_stderr.read(buffsize)
                    if not stderr or len(stderr) % buffsize != 0:
                        break
            except OverflowError:
                pass
            tmp_stderr.close()

            # Error checking.
            if returncode != 0:
                raise Exception(stderr)
        except Exception as e:
            stop_err('Error running faToTwoBit. ' + str(e))
    else:
        seq_path = check_seq_file(dbkey, GALAXY_DATA_INDEX_DIR)
        if not os.path.exists(seq_path):
            # If this occurs, we need to fix the metadata validator.
            stop_err("No sequences are available for '%s', request them by reporting this error." % dbkey)

    #
    # Fetch sequences.
    #

    # Get feature's line(s).
    def get_lines(feature):
        if isinstance(feature, gff_util.GFFFeature):
            return feature.lines()
        else:
            return [feature.rstrip('\r\n')]

    skipped_lines = 0
    first_invalid_line = 0
    invalid_lines = []
    fout = open(output_filename, "w")
    warnings = []
    warning = ''
    twobitfile = None
    file_iterator = open(input_filename)
    if gff_format and interpret_features:
        file_iterator = gff_util.GFFReaderWrapper(file_iterator, fix_strand=False)
    line_count = 1
    for feature in file_iterator:
        # Ignore comments, headers.
        if isinstance(feature, (Header, Comment)):
            line_count += 1
            continue

        name = ""
        if gff_format and interpret_features:
            # Processing features.
            gff_util.convert_gff_coords_to_bed(feature)
            chrom = feature.chrom
            start = feature.start
            end = feature.end
            strand = feature.strand
        else:
            # Processing lines, either interval or GFF format.
            line = feature.rstrip('\r\n')
            if line and not line.startswith("#"):
                fields = line.split('\t')
                try:
                    chrom = fields[chrom_col]
                    start = int(fields[start_col])
                    end = int(fields[end_col])
                    if name_col:
                        name = fields[name_col]
                    if gff_format:
                        start, end = gff_util.convert_gff_coords_to_bed([start, end])
                    if includes_strand_col:
                        strand = fields[strand_col]
                except Exception:
                    warning = "Invalid chrom, start or end column values. "
                    warnings.append(warning)
                    if not invalid_lines:
                        invalid_lines = get_lines(feature)
                        first_invalid_line = line_count
                    skipped_lines += len(invalid_lines)
                    continue
                if start > end:
                    warning = "Invalid interval, start '%d' > end '%d'.  " % (start, end)
                    warnings.append(warning)
                    if not invalid_lines:
                        invalid_lines = get_lines(feature)
                        first_invalid_line = line_count
                    skipped_lines += len(invalid_lines)
                    continue

                if strand not in ['+', '-']:
                    strand = '+'
                sequence = ''
            else:
                continue

        # Open sequence file and get sequence for feature/interval.
        if seq_path and os.path.exists("%s/%s.nib" % (seq_path, chrom)):
            # TODO: improve support for GFF-nib interaction.
            if chrom in nibs:
                nib = nibs[chrom]
            else:
                nibs[chrom] = nib = bx.seq.nib.NibFile(open("%s/%s.nib" % (seq_path, chrom)))
            try:
                sequence = nib.get(start, end - start)
            except Exception:
                warning = "Unable to fetch the sequence from '%d' to '%d' for build '%s'. " % (start, end - start, dbkey)
                warnings.append(warning)
                if not invalid_lines:
                    invalid_lines = get_lines(feature)
                    first_invalid_line = line_count
                skipped_lines += len(invalid_lines)
                continue
        elif seq_path and os.path.isfile(seq_path):
            if not(twobitfile):
                twobitfile = bx.seq.twobit.TwoBitFile(open(seq_path))
            try:
                if options.gff and interpret_features:
                    # Create sequence from intervals within a feature.
                    sequence = ''
                    for interval in feature.intervals:
                        sequence += twobitfile[interval.chrom][interval.start:interval.end]
                else:
                    sequence = twobitfile[chrom][start:end]
            except Exception:
                warning = "Unable to fetch the sequence from '%d' to '%d' for chrom '%s'. " % (start, end - start, chrom)
                warnings.append(warning)
                if not invalid_lines:
                    invalid_lines = get_lines(feature)
                    first_invalid_line = line_count
                skipped_lines += len(invalid_lines)
                continue
        else:
            warning = "Chromosome by name '%s' was not found for build '%s'. " % (chrom, dbkey)
            warnings.append(warning)
            if not invalid_lines:
                invalid_lines = get_lines(feature)
                first_invalid_line = line_count
            skipped_lines += len(invalid_lines)
            continue
        if sequence == '':
            warning = "Chrom: '%s', start: '%s', end: '%s' is either invalid or not present in build '%s'. " % \
                (chrom, start, end, dbkey)
            warnings.append(warning)
            if not invalid_lines:
                invalid_lines = get_lines(feature)
                first_invalid_line = line_count
            skipped_lines += len(invalid_lines)
            continue
        if includes_strand_col and strand == "-":
            sequence = reverse_complement(sequence)

        if output_format == "fasta":
            l = len(sequence)
            c = 0
            if gff_format:
                start, end = gff_util.convert_bed_coords_to_gff([start, end])
            fields = [dbkey, str(chrom), str(start), str(end), strand]
            meta_data = "_".join(fields)
            if name.strip():
                fout.write(">%s %s\n" % (meta_data, name))
            else:
                fout.write(">%s\n" % meta_data)
            while c < l:
                b = min(c + 50, l)
                fout.write("%s\n" % str(sequence[c:b]))
                c = b
        else:  # output_format == "interval"
            if gff_format and interpret_features:
                # TODO: need better GFF Reader to capture all information needed
                # to produce this line.
                meta_data = "\t".join(
                    [feature.chrom, "galaxy_extract_genomic_dna", "interval",
                    str(feature.start), str(feature.end), feature.score, feature.strand,
                    ".", gff_util.gff_attributes_to_str(feature.attributes, "GTF")])
            else:
                meta_data = "\t".join(fields)
            if gff_format:
                format_str = "%s seq \"%s\";\n"
            else:
                format_str = "%s\t%s\n"
            fout.write(format_str % (meta_data, str(sequence)))

        # Update line count.
        if isinstance(feature, gff_util.GFFFeature):
            line_count += len(feature.intervals)
        else:
            line_count += 1

    fout.close()

    if warnings:
        warn_msg = "%d warnings, 1st is: " % len(warnings)
        warn_msg += warnings[0]
        print(warn_msg)
    if skipped_lines:
        # Error message includes up to the first 10 skipped lines.
        print('Skipped %d invalid lines, 1st is #%d, "%s"' % (skipped_lines, first_invalid_line, '\n'.join(invalid_lines[:10])))

    # Clean up temp file.
    if fasta_file:
        os.remove(seq_path)
        os.remove(tmp_name)


if __name__ == "__main__":
    __main__()
