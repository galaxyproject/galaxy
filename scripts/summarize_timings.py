from __future__ import print_function

try:
    from argparse import ArgumentParser
except ImportError:
    ArgumentParser = None
import re

import numpy


DESCRIPTION = ""

TIMING_LINE_PATTERN = re.compile("\((\d+.\d+) ms\)")


def main(argv=None):
    if ArgumentParser is None:
        raise Exception("Test requires Python 2.7")
    arg_parser = ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("--file", default="paster.log")
    arg_parser.add_argument("--print_lines", default=False, action="store_true")
    arg_parser.add_argument("--pattern")

    args = arg_parser.parse_args(argv)
    print_lines = args.print_lines
    filter_pattern = re.compile(args.pattern)
    times = []
    for line in open(args.file, "r"):
        if not filter_pattern.search(line):
            continue

        match = TIMING_LINE_PATTERN.search(line)
        if not match:
            continue

        times.append(float(match.group(1)))
        if print_lines:
            print(line.strip())

    template = "Summary (ms) - Mean: %f, Median: %f, Max: %f, Min: %f, StdDev: %f"
    message = template % (
        numpy.mean(times),
        numpy.median(times),
        numpy.max(times),
        numpy.min(times),
        numpy.std(times)
    )
    print(message)

if __name__ == "__main__":
    main()
