#!/usr/bin/env python

import argparse
import sys
from json import dumps
from textwrap import (
    indent,
    wrap,
)
from typing import List

from galaxy.tool_util.upgrade import (
    Advice,
    advise_on_upgrade,
    latest_supported_version,
)

LEVEL_TO_STRING = {
    "must_fix": "❌",
    "ready": "✅",
    "consider": "🤔",
    "info": "ℹ️",
}
DESCRIPTION = f"""
A small utility to check for potential problems and provide advice when upgrading a tool's
profile version. This version of the script can provide advice for upgrading tools through
{latest_supported_version}.
"""


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("xml_file")
    parser.add_argument(
        "-p",
        "--profile-version",
        dest="profile_version",
        default=latest_supported_version,
        help="Provide upgrade advice up to this Galaxy tool profile version.",
    )
    parser.add_argument(
        "-j",
        "--json",
        default=False,
        action="store_true",
        help="Output aadvice as JSON.",
    )
    parser.add_argument(
        "-n",
        "--niche",
        default=False,
        action="store_true",
        help="Include advice about niche features that may not be relevant for most tools - including the use of 'galaxy.json' and writing global state in the $HOME directory.",
    )
    return parser


def _print_advice(advice: Advice):
    message = "\n".join(wrap(advice.advice_code_message, initial_indent="", subsequent_indent="    "))
    level = advice.level
    level_str = LEVEL_TO_STRING[level]
    url = advice.url
    print(f"- {level_str}{message}\n")
    if advice.message:
        print(indent(advice.message, "    "))
        print("")
    if url:
        print(f"    More information at {url}")


def _print_advice_list(advice_list: List[Advice]):
    for advice in advice_list:
        _print_advice(advice)


def advise(xml_file: str, version: str, json: bool, niche: bool):
    advice_list = advise_on_upgrade(xml_file, version)
    if not niche:
        advice_list = [a for a in advice_list if not a.niche]
    if json:
        print(dumps(a.to_dict() for a in advice_list))
    else:
        _print_advice_list(advice_list)


def main(argv=None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    args = arg_parser().parse_args(argv)
    advise(args.xml_file, args.profile_version, args.json, args.niche)


if __name__ == "__main__":
    main()
