"""Script to parse timings out of a Galaxy log and summarize."""

import re
from argparse import ArgumentParser

import numpy

DESCRIPTION = ""

TIMING_LINE_PATTERN = re.compile(r"\((\d+.\d+) ms\)")


def main(argv=None):
    """Entry point for script."""
    arg_parser = ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("--file", default="galaxy.log")
    arg_parser.add_argument("--print_lines", default=False, action="store_true")
    arg_parser.add_argument("--pattern", default=None)

    args = arg_parser.parse_args(argv)
    print_lines = args.print_lines
    pattern_str = args.pattern
    filter_pattern = re.compile(pattern_str) if pattern_str is not None else None
    times = []
    for line in open(args.file):
        if filter_pattern and not filter_pattern.search(line):
            continue

        match = TIMING_LINE_PATTERN.search(line)
        if not match:
            continue

        times.append(float(match.group(1)))
        if print_lines:
            print(line.strip())

    template = "Summary (ms) - Mean: %f, Median: %f, Max: %f, Min: %f, StdDev: %f"
    message = template % (numpy.mean(times), numpy.median(times), numpy.max(times), numpy.min(times), numpy.std(times))
    print(message)


if __name__ == "__main__":
    main()
