#!/usr/bin/env python

from __future__ import print_function

import subprocess
import sys


def main():
    input_name = sys.argv[1]
    output_name = sys.argv[2]
    column_names = sys.argv[3:]
    chrom1Col = 0
    start1Col = 0
    end1Col = 0
    chrom2Col = 0
    start2Col = 0
    end2Col = 0
    col_line = False
    for line in open(input_name, 'r'):
        if not line.startswith('#'):
            break
        if line.startswith('#columns:'):
            col_line = True
            column_names = line.strip('\n\r').split()[1:]
            break
    for i, name in enumerate(column_names):
        if name == 'chr' or name == 'chr1':
            chrom1Col = i + 1
        elif name == 'pos' or name == 'pos1':
            start1Col = i + 1
            end1Col = i + 1
        elif name == 'start' or name == 'start1':
            start1Col = i + 1
        elif name == 'end' or name == 'end1':
            end1Col = i + 1
        elif name == 'chr2':
            chrom2Col = i + 1
        elif name == 'pos2':
            start2Col = i + 1
            end2Col = i + 1
        elif name == 'start2':
            start2Col = i + 1
        elif name == 'end2':
            end2Col = i + 1
    col_line = False
    for line in open(input_name, 'r'):
        if not line.startswith('#'):
            break
        if line.startswith('#columns:'):
            col_line = True
            break
    if not col_line and min(chrom1Col, start1Col, end1Col, chrom2Col, start2Col, end2Col) == 0:
        print("Not all of the required column information is present", file=sys.stderr)
        return
    if col_line:
        P0 = subprocess.Popen("(grep ^'#' %s; grep -v ^'#' %s)" % (input_name, input_name),
                              stdout=subprocess.PIPE, shell=True)
    else:
        P0 = subprocess.Popen(["(echo", "'#columns: %s';" % column_names, "grep", "^'#'", "%s;" % input_name,
                               "grep", "-v", "^'#'", input_name],
                              stdout=subprocess.PIPE, shell=True)
    P1 = subprocess.Popen(["sort", "-k%i,%i" % (chrom1Col, chrom1Col), "-k%i,%i" % (chrom2Col, chrom2Col),
                           "-k%i,%in" % (start1Col, start1Col), "-k%i,%in" % (start2Col, start2Col)],
                          stdin=P0.stdout, stdout=subprocess.PIPE)
    subprocess.Popen("bgzip > %s" % output_name, stdin=P1.stdout, shell=True)


if __name__ == "__main__":
    main()
