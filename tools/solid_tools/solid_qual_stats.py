#!/usr/bin/env python
# Guruprasad Ananda
from __future__ import print_function

import sys
import tempfile
import zipfile

QUAL_UPPER_BOUND = 41
QUAL_LOWER_BOUND = 1


def stop_err(msg):
    sys.stderr.write("%s\n" % msg)
    sys.exit()


def unzip(filename):
    zip_file = zipfile.ZipFile(filename, 'r')
    tmpfilename = tempfile.NamedTemporaryFile().name
    for name in zip_file.namelist():
        open(tmpfilename, 'a').write(zip_file.read(name))
    zip_file.close()
    return tmpfilename


def __main__():
    infile_score_name = sys.argv[1].strip()
    with open(sys.argv[2].strip(), 'w') as fout:

        if zipfile.is_zipfile(infile_score_name):
            infile_name = unzip(infile_score_name)
        else:
            infile_name = infile_score_name

        readlen = None
        invalid_lines = 0
        j = 0
        with open(infile_name) as fin:
            for line in fin:
                line = line.strip()
                if not(line) or line.startswith("#") or line.startswith(">"):
                    continue
                elems = line.split()
                try:
                    for item in elems:
                        int(item)
                    if not readlen:
                        readlen = len(elems)
                    if len(elems) != readlen:
                        print("Note: Reads in the input dataset are of variable lengths.")
                    j += 1
                except ValueError:
                    invalid_lines += 1
                if j > 10:
                    break

            position_dict = {}
            print("column\tcount\tmin\tmax\tsum\tmean\tQ1\tmed\tQ3\tIQR\tlW\trW", file=fout)
            for k, line in enumerate(open(infile_name)):
                line = line.strip()
                if not(line) or line.startswith("#") or line.startswith(">"):
                    continue
                elems = line.split()
                if position_dict == {}:
                    for pos in range(readlen):
                        position_dict[pos] = [0] * QUAL_UPPER_BOUND
                if len(elems) != readlen:
                    invalid_lines += 1
                    continue
                for ind, item in enumerate(elems):
                    try:
                        item = int(item)
                        position_dict[ind][item] += 1
                    except Exception:
                        pass

            invalid_positions = 0
            for pos in position_dict:
                carr = position_dict[pos]  # count array for position pos
                total = sum(carr)  # number of bases found in this column.
                med_elem = int(round(total / 2.0))
                lowest = None   # Lowest quality score value found in this column.
                highest = None  # Highest quality score value found in this column.
                median = None   # Median quality score value found in this column.
                qsum = 0.0      # Sum of quality score values for this column.
                q1 = None       # 1st quartile quality score.
                q3 = None       # 3rd quartile quality score.
                q1_elem = int(round((total + 1) / 4.0))
                q3_elem = int(round((total + 1) * 3 / 4.0))

                try:
                    for ind, cnt in enumerate(carr):
                        qsum += ind * cnt

                        if cnt != 0:
                            highest = ind

                        if lowest is None and cnt != 0:  # first non-zero count
                            lowest = ind

                        if q1 is None:
                            if sum(carr[:ind + 1]) >= q1_elem:
                                q1 = ind

                        if median is None:
                            if sum(carr[:ind + 1]) < med_elem:
                                continue
                            median = ind
                            if total % 2 == 0:  # even number of elements
                                median2 = median
                                if sum(carr[:ind + 1]) < med_elem + 1:
                                    for ind2, elem in enumerate(carr[ind + 1:]):
                                        if elem != 0:
                                            median2 = ind + ind2 + 1
                                            break
                                median = (median + median2) / 2.0

                        if q3 is None:
                            if sum(carr[:ind + 1]) >= q3_elem:
                                q3 = ind

                    mean = qsum / total  # Mean quality score value for this column.
                    iqr = q3 - q1
                    left_whisker = max(q1 - 1.5 * iqr, lowest)
                    right_whisker = min(q3 + 1.5 * iqr, highest)

                    print("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (pos + 1, total, lowest, highest, qsum, mean, q1, median, q3, iqr, left_whisker, right_whisker), file=fout)
                except Exception:
                    invalid_positions += 1
                    nullvals = ['NA'] * 11
                    print("%s\t%s" % (pos + 1, '\t'.join(nullvals)), file=fout)

    if invalid_lines:
        print("Skipped %d reads as invalid." % invalid_lines)
    if invalid_positions:
        print("Skipped stats computation for %d read positions." % invalid_positions)


if __name__ == "__main__":
    __main__()
