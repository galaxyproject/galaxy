#!/usr/bin/env python
# Guruprasad Ananda
# Refactored 2011 to use numpy instead of rpy, Kanwei Li
"""
This tool provides the SQL "group by" functionality.
Arguments:
    1 output file name
    2 input file name
    3 grouping column
    4 ignore case (1/0)
    5 ascii to delete (comma separated list)
    6... op,col,do_round,default
"""
from __future__ import print_function

import random
import subprocess
import sys
import tempfile
from itertools import groupby

import numpy


def float_wdefault(s, d, c):
    """
    convert list of strings s into list of floats
    non convertable entries are replaced by d if d is not None (otherwise error)
    """
    for i in range(len(s)):
        try:
            s[i] = float(s[i])
        except ValueError:
            if d is not None:
                s[i] = d
            else:
                stop_err("non float value '%s' found in colum %d" % (s[i], c))
    return s


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit(1)


def mode(data):
    counts = {}
    for x in data:
        counts[x] = counts.get(x, 0) + 1
    maxcount = max(counts.values())
    modelist = []
    for x in counts:
        if counts[x] == maxcount:
            modelist.append(str(x))
    return ",".join(modelist)


def main():
    inputfile = sys.argv[2]
    ignorecase = int(sys.argv[4])
    ops = []
    cols = []
    round_val = []
    default_val = []

    # remove comment lines
    if sys.argv[5] != "None":
        asciitodelete = sys.argv[5]
        if asciitodelete:
            newinputfile = "input_cleaned.tsv"
            with open(inputfile) as oldfile, open(newinputfile, "w") as newfile:
                asciitodelete = {chr(int(_)) for _ in asciitodelete.split(",")}
                for line in oldfile:
                    if line[0] not in asciitodelete:
                        newfile.write(line)
            inputfile = newinputfile

    # get operations and options in separate arrays
    for var in sys.argv[6:]:
        op, col, do_round, default = var.split(",")
        ops.append(op)
        cols.append(col)
        round_val.append(do_round)
        default_val.append(float(default) if default != "" else None)

    # At this point, ops, cols and rounds will look something like this:
    # ops:  ['mean', 'min', 'c']
    # cols: ['1', '3', '4']
    # round_val: ['no', 'yes' 'no']
    # default_val: [0, 1, None]

    try:
        group_col = int(sys.argv[3]) - 1
    except Exception:
        stop_err("Group column not specified.")

    # sort file into a temporary file
    tmpfile = tempfile.NamedTemporaryFile(mode="r")
    try:
        """
        The -k option for the Posix sort command is as follows:
        -k, --key=POS1[,POS2]
        start a key at POS1, end it at POS2 (origin 1)
        In other words, column positions start at 1 rather than 0, so
        we need to add 1 to group_col.
        if POS2 is not specified, the newer versions of sort will consider the entire line for sorting. To prevent this, we set POS2=POS1.
        """
        group_col_str = str(group_col + 1)
        command_line = ["sort", "-t", "\t", "-k%s,%s" % (group_col_str, group_col_str), "-o", tmpfile.name, inputfile]
        if ignorecase == 1:
            command_line.append("-f")
    except Exception as exc:
        stop_err("Initialization error -> %s" % str(exc))

    try:
        subprocess.check_output(command_line, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        stop_err("Sorting input dataset resulted in error: %s: %s" % (e.returncode, e.output.decode()))

    def is_new_item(line):
        try:
            item = line.rstrip("\r\n").split("\t")[group_col]
        except IndexError:
            stop_err("The following line didn't have %s columns: %s" % (group_col + 1, line))
        if ignorecase == 1:
            return item.lower()
        return item

    with open(sys.argv[1], "w") as fout:
        for key, line_list in groupby(tmpfile, key=is_new_item):
            op_vals = [[] for _ in ops]
            out_str = key

            for line in line_list:
                fields = line.split("\t")
                for i, col in enumerate(cols):
                    col = int(col) - 1  # cXX from galaxy is 1-based
                    try:
                        val = fields[col].strip()
                        op_vals[i].append(val)
                    except IndexError:
                        sys.stderr.write(
                            'Could not access the value for column %s on line: "%s". Make sure file is tab-delimited.\n'
                            % (col + 1, line)
                        )
                        sys.exit(1)

            # Generate string for each op for this group
            for i, op in enumerate(ops):
                data = op_vals[i]
                rval = ""
                if op == "mode":
                    rval = mode(data)
                elif op == "length":
                    rval = len(data)
                elif op == "random":
                    rval = random.choice(data)
                elif op in ["cat", "cat_uniq"]:
                    if op == "cat_uniq":
                        data = numpy.unique(data)
                    rval = ",".join(data)
                elif op == "unique":
                    rval = len(numpy.unique(data))
                else:
                    # some kind of numpy fn
                    try:
                        data = float_wdefault(data, default_val[i], col + 1)
                    except ValueError:
                        sys.stderr.write("Operation %s expected number values but got %s instead.\n" % (op, data))
                        sys.exit(1)
                    rval = getattr(numpy, op)(data)
                    if round_val[i] == "yes":
                        rval = int(round(rval))
                    else:
                        rval = "%g" % rval
                out_str += "\t%s" % rval

            fout.write(out_str + "\n")

    tmpfile.close()

    # Generate a useful info message.
    msg = "--Group by c%d: " % (group_col + 1)
    for i, op in enumerate(ops):
        if op == "cat":
            op = "concat"
        elif op == "cat_uniq":
            op = "concat_distinct"
        elif op == "length":
            op = "count"
        elif op == "unique":
            op = "count_distinct"
        elif op == "random":
            op = "randomly_pick"

        msg += op + "[c" + cols[i] + "] "

    print(msg)


if __name__ == "__main__":
    main()
