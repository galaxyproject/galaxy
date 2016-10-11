"""CLI helpers for mulled command-line tools."""

import argparse


def arg_parser(argv, globals):
    """Build an argparser for this CLI tool."""
    doc = globals["__doc__"]
    description, epilog = doc.split("\n", 1)
    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    return parser

__all__ = [
    "arg_parser"
]
