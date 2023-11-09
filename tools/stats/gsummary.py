#!/usr/bin/env python
from __future__ import print_function

import re
import sys
import tempfile

try:
    from rpy2.rpy_classic import (
        BASIC_CONVERSION,
        NO_CONVERSION,
        r,
        RException,
        set_default_mode,
    )
except ImportError:
    # RPy isn't maintained, and doesn't work with R>3.0, use it as a fallback
    from rpy import (
        BASIC_CONVERSION,
        NO_CONVERSION,
        r,
        RException,
        set_default_mode,
    )


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit(1)


def S3_METHODS(all="key"):
    Group_Math = [
        "abs",
        "sign",
        "sqrt",
        "floor",
        "ceiling",
        "trunc",
        "round",
        "signif",
        "exp",
        "log",
        "cos",
        "sin",
        "tan",
        "acos",
        "asin",
        "atan",
        "cosh",
        "sinh",
        "tanh",
        "acosh",
        "asinh",
        "atanh",
        "lgamma",
        "gamma",
        "gammaCody",
        "digamma",
        "trigamma",
        "cumsum",
        "cumprod",
        "cummax",
        "cummin",
        "c",
    ]
    Group_Ops = [
        "+",
        "-",
        "*",
        "/",
        "^",
        "%%",
        "%/%",
        "&",
        "|",
        "!",
        "==",
        "!=",
        "<",
        "<=",
        ">=",
        ">",
        "(",
        ")",
        "~",
        ",",
    ]
    if all == "key":
        return {"Math": Group_Math, "Ops": Group_Ops}


def main():
    try:
        datafile = sys.argv[1]
        outfile_name = sys.argv[2]
        expression = sys.argv[3]
    except Exception:
        stop_err("Usage: python gsummary.py input_file ouput_file expression")

    math_allowed = S3_METHODS()["Math"]
    ops_allowed = S3_METHODS()["Ops"]

    # Check for invalid expressions
    for word in re.compile("[a-zA-Z]+").findall(expression):
        if word and word not in math_allowed:
            stop_err("Invalid expression '%s': term '%s' is not recognized or allowed" % (expression, word))
    symbols = set()
    for symbol in re.compile(r"[^a-z0-9\s]+").findall(expression):
        if symbol and symbol not in ops_allowed:
            stop_err("Invalid expression '%s': operator '%s' is not recognized or allowed" % (expression, symbol))
        else:
            symbols.add(symbol)
    if len(symbols) == 1 and "," in symbols:
        # User may have entered a comma-separated list r_data_frame columns
        stop_err("Invalid columns '%s': this tool requires a single column or expression" % expression)

    # Find all column references in the expression
    cols = []
    for col in re.compile("c[0-9]+").findall(expression):
        try:
            cols.append(int(col[1:]) - 1)
        except Exception:
            pass

    tmp_file = tempfile.NamedTemporaryFile("w+")
    # Write the R header row to the temporary file
    hdr_str = "\t".join("c%s" % str(col + 1) for col in cols)
    tmp_file.write("%s\n" % hdr_str)
    skipped_lines = 0
    first_invalid_line = 0
    i = 0
    for i, line in enumerate(open(datafile)):
        line = line.rstrip("\r\n")
        if line and not line.startswith("#"):
            valid = True
            fields = line.split("\t")
            # Write the R data row to the temporary file
            for col in cols:
                try:
                    float(fields[col])
                except Exception:
                    skipped_lines += 1
                    if not first_invalid_line:
                        first_invalid_line = i + 1
                    valid = False
                    break
            if valid:
                data_str = "\t".join(fields[col] for col in cols)
                tmp_file.write("%s\n" % data_str)
    tmp_file.flush()

    if skipped_lines == i + 1:
        stop_err(
            "Invalid column or column data values invalid for computation.  See tool tips and syntax for data requirements."
        )
    else:
        # summary function and return labels
        set_default_mode(NO_CONVERSION)
        summary_func = r(
            "function( x ) { c( sum=sum( as.numeric( x ), na.rm=T ), mean=mean( as.numeric( x ), na.rm=T ), stdev=sd( as.numeric( x ), na.rm=T ), quantile( as.numeric( x ), na.rm=TRUE ) ) }"
        )
        headings = ["sum", "mean", "stdev", "0%", "25%", "50%", "75%", "100%"]
        headings_str = "\t".join(headings)

        r_data_frame = r.read_table(tmp_file.name, header=True, sep="\t")

        outfile = open(outfile_name, "w")

        for col in re.compile("c[0-9]+").findall(expression):
            r.assign(col, r["$"](r_data_frame, col))
        try:
            summary = summary_func(r(expression))
        except RException as s:
            outfile.close()
            stop_err("Computation resulted in the following error: %s" % str(s))
        summary = summary.as_py(BASIC_CONVERSION)
        outfile.write("#%s\n" % headings_str)
        if isinstance(summary, dict):
            # using rpy
            outfile.write("%s\n" % "\t".join("%g" % summary[k] for k in headings))
        else:
            # using rpy2
            outfile.write("%s\n" % "\t".join("%g" % k for k in summary))
        outfile.close()

        if skipped_lines:
            print(
                "Skipped %d invalid lines beginning with line #%d.  See tool tips for data requirements."
                % (skipped_lines, first_invalid_line)
            )


if __name__ == "__main__":
    main()
