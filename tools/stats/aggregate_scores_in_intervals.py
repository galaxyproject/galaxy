#!/usr/bin/env python
# Greg Von Kuster
"""
usage: %prog score_file interval_file chrom start stop [out_file] [options]
    -b, --binned: 'score_file' is actually a directory of binned array files
    -m, --mask=FILE: bed file containing regions not to consider valid
    -c, --chrom_buffer=INT: number of chromosomes (default is 3) to keep in memory when using a user supplied score file
"""

from __future__ import division, print_function

import os
import os.path
import struct
import sys
import tempfile
from collections import Mapping
from math import isnan

import bx.wiggle
from bx.binned_array import BinnedArray, FileBinnedArray
from bx.bitset_builders import binned_bitsets_from_file
from bx.cookbook import doc_optparse

from galaxy.util.ucsc import UCSCLimitException, UCSCOutWrapper


class PositionalScoresOnDisk(object):
    fmt = 'f'
    fmt_size = struct.calcsize(fmt)
    default_value = float('nan')

    def __init__(self):
        self.file = tempfile.TemporaryFile('w+b')
        self.length = 0

    def __getitem__(self, i):
        if i < 0:
            i = self.length + i
        if i < 0 or i >= self.length:
            return self.default_value
        try:
            self.file.seek(i * self.fmt_size)
            return struct.unpack(self.fmt, self.file.read(self.fmt_size))[0]
        except Exception as e:
            raise IndexError(e)

    def __setitem__(self, i, value):
        if i < 0:
            i = self.length + i
        if i < 0:
            raise IndexError('Negative assignment index out of range')
        if i >= self.length:
            self.file.seek(self.length * self.fmt_size)
            self.file.write(struct.pack(self.fmt, self.default_value) * (i - self.length))
            self.length = i + 1
        self.file.seek(i * self.fmt_size)
        self.file.write(struct.pack(self.fmt, value))

    def __len__(self):
        return self.length

    def __repr__(self):
        i = 0
        repr = "[ "
        for i in range(self.length):
            repr = "%s %s," % (repr, self[i])
        return "%s ]" % (repr)


class FileBinnedArrayDir(Mapping):
    """
    Adapter that makes a directory of FileBinnedArray files look like
    a regular dict of BinnedArray objects.
    """
    def __init__(self, dir):
        self.dir = dir
        self.cache = dict()

    def __getitem__(self, key):
        value = None
        if key in self.cache:
            value = self.cache[key]
        else:
            fname = os.path.join(self.dir, "%s.ba" % key)
            if os.path.exists(fname):
                with open(fname) as fh:
                    value = FileBinnedArray(fh)
                self.cache[key] = value
        if value is None:
            raise KeyError("File does not exist: " + fname)
        return value

    def __iter__(self):
        raise NotImplementedError()

    def __len__(self):
        raise NotImplementedError()


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def load_scores_wiggle(fname, chrom_buffer_size=3):
    """
    Read a wiggle file and return a dict of BinnedArray objects keyed
    by chromosome.
    """
    scores_by_chrom = dict()
    try:
        for chrom, pos, val in bx.wiggle.Reader(UCSCOutWrapper(open(fname))):
            if chrom not in scores_by_chrom:
                if chrom_buffer_size:
                    scores_by_chrom[chrom] = BinnedArray()
                    chrom_buffer_size -= 1
                else:
                    scores_by_chrom[chrom] = PositionalScoresOnDisk()
            scores_by_chrom[chrom][pos] = val
    except UCSCLimitException:
        # Wiggle data was truncated, at the very least need to warn the user.
        print('Encountered message from UCSC: "Reached output limit of 100000 data values", so be aware your data was truncated.')
    except IndexError:
        stop_err('Data error: one or more column data values is missing in "%s"' % fname)
    except ValueError:
        stop_err('Data error: invalid data type for one or more values in "%s".' % fname)
    return scores_by_chrom


def load_scores_ba_dir(dir):
    """
    Return a dict-like object (keyed by chromosome) that returns
    FileBinnedArray objects created from "key.ba" files in `dir`
    """
    return FileBinnedArrayDir(dir)


def main():

    # Parse command line
    options, args = doc_optparse.parse(__doc__)

    try:
        score_fname = args[0]
        interval_fname = args[1]
        chrom_col = args[2]
        start_col = args[3]
        stop_col = args[4]
        if len(args) > 5:
            out_file = open(args[5], 'w')
        else:
            out_file = sys.stdout
        binned = bool(options.binned)
        mask_fname = options.mask
    except Exception:
        doc_optparse.exit()

    if score_fname == 'None':
        stop_err('This tool works with data from genome builds hg16, hg17 or hg18.  Click the pencil icon in your history item to set the genome build if appropriate.')

    try:
        chrom_col = int(chrom_col) - 1
        start_col = int(start_col) - 1
        stop_col = int(stop_col) - 1
    except Exception:
        stop_err('Chrom, start & end column not properly set, click the pencil icon in your history item to set these values.')

    if chrom_col < 0 or start_col < 0 or stop_col < 0:
        stop_err('Chrom, start & end column not properly set, click the pencil icon in your history item to set these values.')

    if binned:
        scores_by_chrom = load_scores_ba_dir(score_fname)
    else:
        try:
            chrom_buffer = int(options.chrom_buffer)
        except Exception:
            chrom_buffer = 3
        scores_by_chrom = load_scores_wiggle(score_fname, chrom_buffer)

    if mask_fname:
        masks = binned_bitsets_from_file(open(mask_fname))
    else:
        masks = None

    skipped_lines = 0
    first_invalid_line = 0
    invalid_line = ''

    for i, line in enumerate(open(interval_fname)):
        valid = True
        line = line.rstrip('\r\n')
        if line and not line.startswith('#'):
            fields = line.split()

            try:
                chrom, start, stop = fields[chrom_col], int(fields[start_col]), int(fields[stop_col])
            except Exception:
                valid = False
                skipped_lines += 1
                if not invalid_line:
                    first_invalid_line = i + 1
                    invalid_line = line
            if valid:
                total = 0
                count = 0
                min_score = 100000000
                max_score = -100000000
                for j in range(start, stop):
                    if chrom in scores_by_chrom:
                        try:
                            # Skip if base is masked
                            if masks and chrom in masks:
                                if masks[chrom][j]:
                                    continue
                            # Get the score, only count if not 'nan'
                            score = scores_by_chrom[chrom][j]
                            if not isnan(score):
                                total += score
                                count += 1
                                max_score = max(score, max_score)
                                min_score = min(score, min_score)
                        except Exception:
                            continue
                if count > 0:
                    avg = total / count
                else:
                    avg = "nan"
                    min_score = "nan"
                    max_score = "nan"

                # Build the resulting line of data
                out_line = []
                for k in range(0, len(fields)):
                    out_line.append(fields[k])
                out_line.append(avg)
                out_line.append(min_score)
                out_line.append(max_score)

                print("\t".join(map(str, out_line)), file=out_file)
            else:
                skipped_lines += 1
                if not invalid_line:
                    first_invalid_line = i + 1
                    invalid_line = line
        elif line.startswith('#'):
            # We'll save the original comments
            print(line, file=out_file)

    out_file.close()

    if skipped_lines > 0:
        print('Data issue: skipped %d invalid lines starting at line #%d which is "%s"' % (skipped_lines, first_invalid_line, invalid_line))
        if skipped_lines == i:
            print('Consider changing the metadata for the input dataset by clicking on the pencil icon in the history item.')


if __name__ == "__main__":
    main()
